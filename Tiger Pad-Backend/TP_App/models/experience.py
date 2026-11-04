"""
Overall function:
This file defines the SQLAlchemy model for the experiences table.

The experiences table stores a TigerPad student's professional and practical
experiences, including employment, internships, volunteer work, leadership,
research, campus involvement, and other career-related activities.

TigerPad can use these experiences when building résumés, evaluating career
readiness, identifying demonstrated skills, and generating recommendations
based on the student's selected career path.
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
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.student_profile import StudentProfile


class Experience(Base):
    """
    Represent a professional or career-related student experience.

    Every experience belongs to one student profile. Removing the student
    profile will also remove its associated experience records.
    """

    __tablename__ = "experiences"

    __table_args__ = (
        Index(
            "fk_experiences_student_profile_idx",
            "student_profile_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    experience_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_experiences_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    experience_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    organization_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    position_title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    start_date: Mapped[date] = mapped_column(
        DATE,
        nullable=False,
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
    def experience_type_description(self) -> str:
        """Return the experience type in a user-friendly format."""

        experience_types = {
            "employment": "Employment",
            "internship": "Internship",
            "volunteer": "Volunteer Experience",
            "leadership": "Leadership Experience",
            "research": "Research Experience",
            "campus_activity": "Campus Activity",
            "clinical": "Clinical Experience",
            "student_teaching": "Student Teaching",
            "military": "Military Experience",
            "other": "Other Experience",
        }

        return experience_types.get(
            self.experience_type,
            self.experience_type.replace("_", " ").title(),
        )

    @property
    def current(self) -> bool:
        """Return whether the student currently holds this position."""

        return bool(self.is_current)

    @property
    def featured(self) -> bool:
        """Return whether this experience should be featured."""

        return bool(self.is_featured)

    @property
    def display_end_date(self) -> str:
        """Return Present or the stored ending date."""

        if self.current:
            return "Present"

        if self.end_date is None:
            return "Not provided"

        return self.end_date.isoformat()

    @property
    def duration_in_months(self) -> int:
        """
        Estimate the number of months spent in the experience.

        Current experiences use today's date as the ending date.
        """

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
            "<Experience("
            f"experience_id={self.experience_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"experience_type={self.experience_type!r}, "
            f"organization_name={self.organization_name!r}, "
            f"position_title={self.position_title!r}, "
            f"is_current={self.current}"
            ")>"
        )
