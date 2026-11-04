"""
Overall function:
This file defines the SQLAlchemy CareerPathProgram model for TigerPad.

The model maps directly to the existing career_path_programs table in MySQL.
It connects generalized career paths to the Jackson State University academic
programs that prepare students for those careers.

The relevance level explains how strongly an academic program relates to a
career path. This mapping helps TigerPad recommend career possibilities based
on each student's major, minor, concentration, certificate, or degree program.
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
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.academic_program import AcademicProgram
    from TP_App.models.career_path import CareerPath


class CareerPathProgram(Base):
    """
    Represent a relationship between a career path and academic program.

    The same career path and academic program combination can only
    appear once.
    """

    __tablename__ = "career_path_programs"

    __table_args__ = (
        UniqueConstraint(
            "career_path_id",
            "program_id",
            name="uq_career_path_programs_path_program",
        ),
        Index(
            "fk_career_path_programs_program_idx",
            "program_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    career_path_program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    career_path_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_career_path_programs_path",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "academic_programs.program_id",
            name="fk_career_path_programs_program",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    relevance_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'related'"),
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
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

    career_path: Mapped["CareerPath"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    academic_program: Mapped["AcademicProgram"] = relationship(
        "AcademicProgram",
        lazy="joined",
    )

    @property
    def active(self) -> bool:
        """Return the mapping status as a Python Boolean value."""

        return bool(self.is_active)

    @property
    def high_relevance(self) -> bool:
        """
        Return whether the program has a strong career-path connection.
        """

        return self.relevance_level.lower() in {
            "primary",
            "high",
            "highly_related",
        }

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the mapping.
        """

        return (
            f"CareerPathProgram("
            f"career_path_program_id="
            f"{self.career_path_program_id!r}, "
            f"career_path_id={self.career_path_id!r}, "
            f"program_id={self.program_id!r}, "
            f"relevance_level={self.relevance_level!r})"
        )
