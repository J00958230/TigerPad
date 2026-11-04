"""
Overall function:
This file defines the SQLAlchemy Role model for TigerPad.

The model maps directly to the existing roles table in the MySQL database.
Roles determine the main permission category assigned to each TigerPad user.

The initial TigerPad roles are:
- student
- faculty
- admin

Each role can be assigned to multiple users, while each user has one role.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.user import User


class Role(Base):
    """
    Represent a TigerPad user role.

    This model maps to the existing MySQL roles table.
    """

    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="name_UNIQUE",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    role_id: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
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

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="role",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return a developer-friendly representation of the role."""

        return (
            f"Role(role_id={self.role_id!r}, "
            f"name={self.name!r})"
        )
