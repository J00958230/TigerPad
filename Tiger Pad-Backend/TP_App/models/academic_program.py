"""
Overall function:
This file defines the SQLAlchemy AcademicProgram model for TigerPad.

The model maps directly to the existing academic_programs table in MySQL.
It stores Jackson State University majors and other academic programs,
including each program's department, program type, degree level, degree
abbreviation, description, and catalog link.

TigerPad uses academic programs to connect a student's major or other field
of study to appropriate career paths, skills, resources, résumé guidance,
and faculty support.
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


class AcademicProgram(Base):
    """
    Represent a Jackson State University academic program.

    Academic programs may represent majors or other program types
    stored in TigerPad's MySQL database.
    """

    __tablename__ = "academic_programs"

    __table_args__ = (
        UniqueConstraint(
            "program_code",
            name="program_code_UNIQUE",
        ),
        UniqueConstraint(
            "department_id",
            "name",
            "program_type",
            "degree_level",
            name="uq_programs_department_name_type",
        ),
        Index(
            "fk_academic_programs_departments_idx",
            "department_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    department_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "departments.department_id",
            name="fk_academic_programs_departments",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    program_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    program_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    degree_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    degree_abbreviation: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    catalog_url: Mapped[str | None] = mapped_column(
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

    department: Mapped["Department"] = relationship(
        "Department",
        lazy="joined",
    )

    @property
    def active(self) -> bool:
        """Return the program status as a Python Boolean value."""

        return bool(self.is_active)

    @property
    def display_name(self) -> str:
        """
        Return the program name with its degree abbreviation.

        Example:
            Computer Science (BS)
        """

        if self.degree_abbreviation:
            return (
                f"{self.name} "
                f"({self.degree_abbreviation})"
            )

        return self.name

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the program.
        """

        return (
            f"AcademicProgram(program_id={self.program_id!r}, "
            f"name={self.name!r}, "
            f"program_code={self.program_code!r}, "
            f"department_id={self.department_id!r})"
        )
