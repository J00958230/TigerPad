"""
Overall function:
This file defines the SQLAlchemy FacultyProgramAccess model for TigerPad.

The model maps directly to the existing faculty_program_access table in
MySQL. It connects faculty profiles to the academic programs they are
authorized to view, review, or manage within TigerPad.

The record stores the faculty member's access level, optional expiration
date, activation status, and timestamps. A faculty member cannot receive
duplicate access records for the same academic program.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import DATETIME, INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.academic_program import AcademicProgram
    from TP_App.models.faculty_profile import FacultyProfile


class FacultyProgramAccess(Base):
    """
    Represent a faculty member's access to an academic program.

    Access levels may be used to distinguish viewing, reviewing,
    and administrative program permissions.
    """

    __tablename__ = "faculty_program_access"

    __table_args__ = (
        UniqueConstraint(
            "faculty_profile_id",
            "program_id",
            name="uq_faculty_program_access_faculty_program",
        ),
        Index(
            "fk_faculty_program_access_program_idx",
            "program_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    faculty_program_access_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    faculty_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "faculty_profiles.faculty_profile_id",
            name="fk_faculty_program_access_faculty",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "academic_programs.program_id",
            name="fk_faculty_program_access_program",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    access_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'viewer'"),
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
        default=None,
    )

    is_active: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        server_default=text("1"),
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

    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile",
        lazy="joined",
    )

    academic_program: Mapped["AcademicProgram"] = relationship(
        "AcademicProgram",
        lazy="joined",
    )

    @property
    def active(self) -> bool:
        """Return the stored activation status as a Boolean value."""

        return bool(self.is_active)

    @property
    def expired(self) -> bool:
        """
        Return whether the faculty access period has expired.

        An access record without an expiration date does not expire
        automatically.
        """

        if self.expires_at is None:
            return False

        return datetime.now() >= self.expires_at

    @property
    def access_is_valid(self) -> bool:
        """
        Return whether the faculty member can currently use this access.

        Access must be active and must not be expired.
        """

        return self.active and not self.expired

    @property
    def can_manage(self) -> bool:
        """
        Return whether the access level permits program management.
        """

        return (
            self.access_is_valid
            and self.access_level.lower() in {"manager", "admin"}
        )

    @property
    def can_review(self) -> bool:
        """
        Return whether the access level permits student review.
        """

        return (
            self.access_is_valid
            and self.access_level.lower()
            in {"reviewer", "manager", "admin"}
        )

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the access record.
        """

        return (
            f"FacultyProgramAccess("
            f"faculty_program_access_id="
            f"{self.faculty_program_access_id!r}, "
            f"faculty_profile_id={self.faculty_profile_id!r}, "
            f"program_id={self.program_id!r}, "
            f"access_level={self.access_level!r})"
        )
