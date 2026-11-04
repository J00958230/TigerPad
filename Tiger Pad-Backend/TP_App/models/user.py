"""
Overall function:
This file defines the SQLAlchemy User model for TigerPad.

The model maps directly to the users table in MySQL. It stores the user's
role, JSU email address, secured password hash, name, account status,
login-security information, email-verification status, and timestamps.

Plain-text passwords must never be stored or returned.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import (
    DATETIME,
    INTEGER,
    SMALLINT,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.role import Role


class User(Base):
    """Represent a TigerPad website user."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "jsu_email",
            name="jsu_email_UNIQUE",
        ),
        Index(
            "fk_users_roles_idx",
            "role_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    role_id: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        ForeignKey(
            "roles.role_id",
            name="fk_users_role",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    jsu_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    is_active: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        server_default=text("1"),
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True),
        nullable=False,
        server_default=text("0"),
    )

    # This now matches the corrected MySQL column name.
    locked_until: Mapped[datetime | None] = mapped_column(
        "locked_until",
        DATETIME,
        nullable=True,
        default=None,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
        default=None,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
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

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users",
        lazy="joined",
    )

    @property
    def full_name(self) -> str:
        """Return the user's complete name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def account_is_active(self) -> bool:
        """Return whether the account is active."""
        return bool(self.is_active)

    @property
    def account_is_locked(self) -> bool:
        """Return whether the account is currently locked."""

        if self.locked_until is None:
            return False

        return self.locked_until > datetime.now()

    def __repr__(self) -> str:
        """Return a safe representation without exposing the password hash."""

        return (
            f"User(user_id={self.user_id!r}, "
            f"jsu_email={self.jsu_email!r}, "
            f"role_id={self.role_id!r})"
        )