"""
Overall function:
This file defines the SQLAlchemy FacultyProfile model for TigerPad.

The model maps directly to the existing faculty_profiles table in MySQL.
It stores faculty and staff information such as department, job title,
office location, phone number, biography, LinkedIn URL, student-review
permission, and profile-completion status.

Each faculty profile can connect to one TigerPad user and one JSU department.
Both connections are optional because the database uses ON DELETE SET NULL.
This preserves the faculty profile if its associated user account or
department is removed.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.department import Department
    from TP_App.models.user import User


class FacultyProfile(Base):
    """
    Represent a TigerPad faculty or staff profile.

    Faculty members may be allowed to review student career-readiness
    information when can_review_students is enabled.
    """

    __tablename__ = "faculty_profiles"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="user_id_UNIQUE",
        ),
        Index(
            "fk_faculty_profiles_department_idx",
            "department_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    faculty_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "users.user_id",
            name="fk_faculty_profiles_user",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
        default=None,
    )

    department_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "departments.department_id",
            name="fk_faculty_profiles_department",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
        default=None,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )

    office_location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(25),
        nullable=True,
        default=None,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    can_review_students: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        server_default=text("0"),
    )

    is_profile_complete: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
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

    user: Mapped["User | None"] = relationship(
        "User",
        lazy="joined",
    )

    department: Mapped["Department | None"] = relationship(
        "Department",
        lazy="joined",
    )

    @property
    def review_permission_enabled(self) -> bool:
        """
        Return whether the faculty member can review students.
        """

        return bool(self.can_review_students)

    @property
    def complete(self) -> bool:
        """Return profile-completion status as a Boolean value."""

        return bool(self.is_profile_complete)

    @property
    def display_name(self) -> str:
        """
        Return the connected user's name when available.

        If the associated user account was removed, return a generic
        faculty label.
        """

        if self.user is not None:
            return self.user.full_name

        return "Former faculty or staff member"

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the profile.
        """

        return (
            f"FacultyProfile("
            f"faculty_profile_id={self.faculty_profile_id!r}, "
            f"user_id={self.user_id!r}, "
            f"department_id={self.department_id!r}, "
            f"job_title={self.job_title!r})"
        )
