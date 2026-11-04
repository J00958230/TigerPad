"""
Overall function:
This file defines the SQLAlchemy College model for TigerPad.

The model maps directly to the existing colleges table in MySQL. It stores
the colleges and schools associated with Jackson State University so that
departments, academic programs, student majors, and career recommendations
can be organized by academic area.

Each college can contain multiple departments. TigerPad uses these academic
connections to provide career guidance and résumé recommendations that match
a student's field of study.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint, text
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.department import Department


class College(Base):
    """
    Represent a Jackson State University college or school.

    This model maps directly to the MySQL colleges table.
    """

    __tablename__ = "colleges"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="name_UNIQUE",
        ),
        UniqueConstraint(
            "college_code",
            name="college_code_UNIQUE",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    college_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    college_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    website_url: Mapped[str | None] = mapped_column(
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

    departments: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="college",
        lazy="selectin",
    )

    @property
    def active(self) -> bool:
        """Return the college status as a Python Boolean value."""

        return bool(self.is_active)

    def __repr__(self) -> str:
        """Return a developer-friendly representation of the college."""

        return (
            f"College(college_id={self.college_id!r}, "
            f"name={self.name!r}, "
            f"college_code={self.college_code!r})"
        )
