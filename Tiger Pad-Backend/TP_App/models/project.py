"""
Overall function:
This file defines the SQLAlchemy model for the projects table.

The projects table stores academic, professional, creative, research,
community-service, business, engineering, and personal projects completed
by TigerPad students.

TigerPad can use project information to strengthen student résumés, demonstrate
skills and accomplishments, evaluate career readiness, and provide career-path
recommendations for students across every JSU major.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATE,
    INTEGER,
    SMALLINT,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.student_profile import StudentProfile


class Project(Base):
    """
    Represent a project completed or currently being completed by a student.

    Every project belongs to one student profile. Removing the student profile
    will also remove its associated project records.
    """

    __tablename__ = "projects"

    __table_args__ = (
        Index(
            "fk_projects_student_profiles_idx",
            "student_profile_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    project_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_projects_student_profiles",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    project_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    role_title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    organization_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    start_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
    )

    end_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
    )

    is_current: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    outcome: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    project_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    team_size: Mapped[int | None] = mapped_column(
        SMALLINT(unsigned=True),
        nullable=True,
    )

    is_featured: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
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

    @property
    def project_type_description(self) -> str:
        """Return the project type in a user-friendly format."""

        project_types = {
            "academic": "Academic Project",
            "professional": "Professional Project",
            "personal": "Personal Project",
            "research": "Research Project",
            "creative": "Creative Project",
            "engineering": "Engineering Project",
            "business": "Business Project",
            "community_service": "Community-Service Project",
            "clinical": "Clinical Project",
            "capstone": "Capstone Project",
            "other": "Other Project",
        }

        return project_types.get(
            self.project_type,
            self.project_type.replace("_", " ").title(),
        )

    @property
    def current(self) -> bool:
        """Return whether the project is currently in progress."""

        return bool(self.is_current)

    @property
    def featured(self) -> bool:
        """Return whether the project should be featured."""

        return bool(self.is_featured)

    @property
    def has_project_link(self) -> bool:
        """Return whether a project website or portfolio link exists."""

        return bool(self.project_url)

    @property
    def is_team_project(self) -> bool:
        """Return whether more than one person worked on the project."""

        return bool(
            self.team_size is not None
            and self.team_size > 1
        )

    @property
    def display_end_date(self) -> str:
        """Return Present or the project's stored ending date."""

        if self.current:
            return "Present"

        if self.end_date is None:
            return "Not provided"

        return self.end_date.isoformat()

    @property
    def duration_in_months(self) -> int | None:
        """
        Estimate the project's duration in months.

        None is returned when the student did not provide a start date.
        Current projects use today's date as their ending date.
        """

        if self.start_date is None:
            return None

        effective_end_date = (
            date.today()
            if self.current or self.end_date is None
            else self.end_date
        )

        months = (
            (effective_end_date.year - self.start_date.year) * 12
            + effective_end_date.month
            - self.start_date.month
        )

        if effective_end_date.day < self.start_date.day:
            months -= 1

        return max(months, 0)

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<Project("
            f"project_id={self.project_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"project_type={self.project_type!r}, "
            f"title={self.title!r}, "
            f"is_current={self.current}, "
            f"is_featured={self.featured}"
            ")>"
        )
