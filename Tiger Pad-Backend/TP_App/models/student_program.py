"""
Overall function:
This file defines the SQLAlchemy StudentProgram model for TigerPad.

The model maps directly to the existing student_programs table in MySQL.
It connects a student profile to an academic program and records whether
the program is the student's primary program, the student's status in the
program, the start date, and the completion date.

This table allows TigerPad students to have more than one academic program,
such as a major, minor, concentration, certificate, or additional degree.
The student's programs help TigerPad personalize résumé guidance, skills,
career paths, recommendations, and JSU resources.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import DATE, INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.academic_program import AcademicProgram
    from TP_App.models.student_profile import StudentProfile


class StudentProgram(Base):
    """
    Represent a connection between a student and an academic program.

    A student can have multiple academic programs, but the same
    program cannot be assigned to the same student more than once.
    """

    __tablename__ = "student_programs"

    __table_args__ = (
        UniqueConstraint(
            "student_profile_id",
            "program_id",
            name="uq_student_programs_student_program",
        ),
        Index(
            "fk_student_programs_program_idx",
            "program_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    student_program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_student_programs_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "academic_programs.program_id",
            name="fk_student_programs_program",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    is_primary: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        server_default=text("0"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
    )

    start_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
        default=None,
    )

    completion_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
        default=None,
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

    academic_program: Mapped["AcademicProgram"] = relationship(
        "AcademicProgram",
        lazy="joined",
    )

    @property
    def primary(self) -> bool:
        """Return whether this is the student's primary program."""

        return bool(self.is_primary)

    @property
    def active(self) -> bool:
        """Return whether the student-program record is active."""

        return self.status.lower() == "active"

    @property
    def completed(self) -> bool:
        """
        Return whether the student has completed the program.

        A program is treated as completed when its status is completed
        or when a completion date has been recorded.
        """

        return (
            self.status.lower() == "completed"
            or self.completion_date is not None
        )

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the record.
        """

        return (
            f"StudentProgram("
            f"student_program_id={self.student_program_id!r}, "
            f"student_profile_id={self.student_profile_id!r}, "
            f"program_id={self.program_id!r}, "
            f"is_primary={self.is_primary!r}, "
            f"status={self.status!r})"
        )
