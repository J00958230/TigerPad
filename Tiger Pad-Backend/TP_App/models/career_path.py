"""
Overall function:
This file defines the SQLAlchemy CareerPath model for TigerPad.

The model maps directly to the existing career_paths table in MySQL. It stores
generalized career paths rather than live job postings. Each career path
explains a type of professional role, the industry it belongs to, and the
typical education level associated with that role.

TigerPad uses career paths to help students understand career possibilities
that align with their academic programs, skills, experiences, certifications,
projects, and professional goals.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.industry import Industry


class CareerPath(Base):
    """
    Represent a generalized TigerPad career path.

    Career paths describe professional roles and career directions.
    They do not represent individual job advertisements.
    """

    __tablename__ = "career_paths"

    __table_args__ = (
        UniqueConstraint(
            "career_path_code",
            name="career_path_code_UNIQUE",
        ),
        UniqueConstraint(
            "industry_id",
            "name",
            name="uq_career_paths_industry_name",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    career_path_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    industry_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "industries.industry_id",
            name="fk_career_paths_industry",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    career_path_code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    typical_education_level: Mapped[str | None] = mapped_column(
        String(50),
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

    industry: Mapped["Industry"] = relationship(
        "Industry",
        back_populates="career_paths",
        lazy="joined",
    )

    @property
    def active(self) -> bool:
        """Return the career-path status as a Python Boolean value."""

        return bool(self.is_active)

    @property
    def display_name(self) -> str:
        """
        Return a display name that includes the associated industry.
        """

        return f"{self.name} — {self.industry.name}"

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the career path.
        """

        return (
            f"CareerPath("
            f"career_path_id={self.career_path_id!r}, "
            f"name={self.name!r}, "
            f"career_path_code={self.career_path_code!r}, "
            f"industry_id={self.industry_id!r})"
        )
