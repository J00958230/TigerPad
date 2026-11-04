"""
Overall function:
This file defines the SQLAlchemy StudentProfile model for TigerPad.

The model maps directly to the existing student_profiles table in MySQL.
It stores student-specific information that does not belong in the general
users table, including academic level, expected graduation date, GPA,
professional headline, biography, professional links, profile visibility,
and profile-completion status.

Each student profile belongs to exactly one TigerPad user. The unique user_id
constraint prevents one user from having multiple student profiles.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import DATE, INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.user import User


class StudentProfile(Base):
    """
    Represent a TigerPad student profile.

    This model contains student-specific academic and professional
    information connected to a general TigerPad user account.
    """

    __tablename__ = "student_profiles"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="user_id_UNIQUE",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "users.user_id",
            name="fk_student_profiles_user",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    preferred_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )

    academic_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        default=None,
    )

    expected_graduation_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
        default=None,
    )

    gpa: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=3,
            scale=2,
        ),
        nullable=True,
        default=None,
    )

    professional_headline: Mapped[str | None] = mapped_column(
        String(255),
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

    portfolio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    profile_visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'private'"),
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

    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    @property
    def complete(self) -> bool:
        """Return profile-completion status as a Boolean value."""

        return bool(self.is_profile_complete)

    @property
    def publicly_visible(self) -> bool:
        """Return whether the student profile is publicly visible."""

        return self.profile_visibility.lower() == "public"

    @property
    def display_name(self) -> str:
        """
        Return the student's preferred name when one is available.

        Otherwise, return the complete name from the connected user
        account.
        """

        if self.preferred_name:
            return self.preferred_name

        return self.user.full_name

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the profile.
        """

        return (
            f"StudentProfile("
            f"student_profile_id={self.student_profile_id!r}, "
            f"user_id={self.user_id!r}, "
            f"academic_level={self.academic_level!r})"
        )
