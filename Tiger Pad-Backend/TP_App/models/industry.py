"""
Overall function:
This file defines the SQLAlchemy Industry model for TigerPad.

The model maps directly to the existing industries table in MySQL. It stores
broad career industries—such as technology, healthcare, education, business,
finance, engineering, government, media, and public service.

TigerPad uses industries to organize generalized career paths. Each industry
can contain multiple career paths, allowing students from every JSU academic
program to explore careers that align with their education, skills, interests,
and professional goals.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint, text
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath


class Industry(Base):
    """
    Represent a broad TigerPad career industry.

    Industries group related generalized career paths without storing
    live job postings.
    """

    __tablename__ = "industries"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="name_UNIQUE",
        ),
        UniqueConstraint(
            "industry_code",
            name="industry_code_UNIQUE",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    industry_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    industry_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
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

    career_paths: Mapped[list["CareerPath"]] = relationship(
        "CareerPath",
        back_populates="industry",
        lazy="selectin",
    )

    @property
    def active(self) -> bool:
        """Return the industry status as a Python Boolean value."""

        return bool(self.is_active)

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the industry.
        """

        return (
            f"Industry(industry_id={self.industry_id!r}, "
            f"name={self.name!r}, "
            f"industry_code={self.industry_code!r})"
        )
