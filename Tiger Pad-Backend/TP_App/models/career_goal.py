"""
Overall function:
This file defines the SQLAlchemy model for the career_goals table.

The career_goals table connects a TigerPad student profile to a career path
the student wants to pursue. It records whether the career path is the
student's primary or secondary goal, the goal's current status, an optional
target date, and personal notes.

TigerPad can use career goals to personalize readiness scores, skill-gap
analysis, résumé recommendations, and career-development guidance.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATE,
    INTEGER,
    TIMESTAMP,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.student_profile import StudentProfile


class CareerGoal(Base):
    """
    Represent a career path selected as a goal by a TigerPad student.

    A student may select multiple career paths, but the same career path
    cannot be assigned to the same student more than once.
    """

    __tablename__ = "career_goals"

    __table_args__ = (
        UniqueConstraint(
            "student_profile_id",
            "career_path_id",
            name="uq_career_goals_student_path",
        ),
        Index(
            "fk_career_goals_career_path_idx",
            "career_path_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    career_goal_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_career_goals_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_career_goals_career_path",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    goal_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="primary",
        server_default=text("'primary'"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )

    target_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        lazy="joined",
    )

    career_path: Mapped["CareerPath"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    @property
    def goal_type_description(self) -> str:
        """Return the goal type in a user-friendly format."""

        goal_types = {
            "primary": "Primary career goal",
            "secondary": "Secondary career goal",
            "exploring": "Career path being explored",
        }

        return goal_types.get(
            self.goal_type,
            self.goal_type.replace("_", " ").title(),
        )

    @property
    def status_description(self) -> str:
        """Return the goal status in a user-friendly format."""

        return self.status.replace("_", " ").title()

    @property
    def is_primary(self) -> bool:
        """Return whether this is the student's primary career goal."""

        return self.goal_type == "primary"

    @property
    def is_active(self) -> bool:
        """Return whether the career goal is currently active."""

        return self.status == "active"

    @property
    def is_completed(self) -> bool:
        """Return whether the student completed the career goal."""

        return self.status == "completed"

    @property
    def is_overdue(self) -> bool:
        """Return whether an active career goal has passed its target date."""

        return bool(
            self.target_date
            and self.is_active
            and self.target_date < date.today()
        )

    @property
    def days_until_target(self) -> int | None:
        """
        Return the number of days remaining before the target date.

        A negative value means the target date has passed. None means
        the student did not provide a target date.
        """

        if self.target_date is None:
            return None

        return (self.target_date - date.today()).days

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<CareerGoal("
            f"career_goal_id={self.career_goal_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"career_path_id={self.career_path_id}, "
            f"goal_type={self.goal_type!r}, "
            f"status={self.status!r}"
            ")>"
        )
