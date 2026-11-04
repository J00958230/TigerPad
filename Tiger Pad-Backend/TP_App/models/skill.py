"""
Overall function:
This file defines the SQLAlchemy Skill model for TigerPad.

The model maps directly to the existing skills table in MySQL. It stores
professional, technical, creative, communication, leadership, research,
business, healthcare, education, and other career-readiness skills.

TigerPad uses this diverse skill catalog for students from every JSU academic
program. Skills can be connected to career paths, student profiles, skill-gap
results, résumé analysis, readiness scores, and personalized recommendations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint, text
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from TP_App.database.base import Base


class Skill(Base):
    """
    Represent a professional or career-readiness skill in TigerPad.

    Skills are grouped by category and can be connected to both
    students and generalized career paths.
    """

    __tablename__ = "skills"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="name_UNIQUE",
        ),
        UniqueConstraint(
            "skill_code",
            name="skill_code_UNIQUE",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    skill_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    skill_code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
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

    @property
    def active(self) -> bool:
        """Return the skill status as a Python Boolean value."""

        return bool(self.is_active)

    @property
    def display_name(self) -> str:
        """
        Return the skill name with its category.

        Example:
            Project Management — Business
        """

        return f"{self.name} — {self.category}"

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the skill.
        """

        return (
            f"Skill(skill_id={self.skill_id!r}, "
            f"name={self.name!r}, "
            f"skill_code={self.skill_code!r}, "
            f"category={self.category!r})"
        )
