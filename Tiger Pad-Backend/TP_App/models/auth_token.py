"""
Overall function:
This file defines the SQLAlchemy AuthToken model for TigerPad.

The model maps directly to the existing auth_tokens table in MySQL. It stores
securely hashed authentication tokens used for actions such as refreshing a
login session, verifying an email address, or resetting a password.

TigerPad must never store a raw authentication token in this table. Only the
SHA-256 hash of the token is stored. Each token belongs to one user, while
one user may have multiple authentication tokens.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import CHAR, DATETIME, INTEGER, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.user import User


class AuthToken(Base):
    """
    Represent a secure TigerPad authentication token.

    Raw token values must be sent to the user only when they are
    created. Only a one-way hash of each token is stored in MySQL.
    """

    __tablename__ = "auth_tokens"

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="token_hash_UNIQUE",
        ),
        Index(
            "fk_auth_tokens_user_idx",
            "user_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    token_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "users.user_id",
            name="fk_auth_tokens_user",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
    )

    token_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DATETIME,
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
        default=None,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    @property
    def is_expired(self) -> bool:
        """Return True when the token has passed its expiration time."""

        return datetime.now() >= self.expires_at

    @property
    def is_used(self) -> bool:
        """Return True when the token has already been used."""

        return self.used_at is not None

    @property
    def is_revoked(self) -> bool:
        """Return True when the token has been revoked."""

        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        """
        Return True when the token can still be used.

        A valid token must not be expired, used, or revoked.
        """

        return not (
            self.is_expired
            or self.is_used
            or self.is_revoked
        )

    def __repr__(self) -> str:
        """
        Return a safe developer representation of the token.

        The token hash is intentionally excluded.
        """

        return (
            f"AuthToken(token_id={self.token_id!r}, "
            f"user_id={self.user_id!r}, "
            f"token_type={self.token_type!r}, "
            f"expires_at={self.expires_at!r})"
        )
