"""
Overall function:
This file defines the SQLAlchemy Department model for TigerPad.

The model maps directly to the existing departments table in MySQL. It stores
Jackson State University departments and connects each department to its
parent college.

Departments help TigerPad organize academic programs, faculty profiles, and
major-specific career guidance. One college can contain many departments,
while each department belongs to one college.
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
    from TP_App.models.college import College


class Department(Base):
    """
    Represent a Jackson State University academic department.

    This model maps directly to the MySQL departments table.
    """

    __tablename__ = "departments"

    __table_args__ = (
        UniqueConstraint(
            "department_code",
            name="department_code_UNIQUE",
        ),
        UniqueConstraint(
            "college_id",
            "name",
            name="uq_departments_college_name",
        ),
        Index(
            "fk_departments_colleges_idx",
            "college_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    department_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    college_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "colleges.college_id",
            name="fk_departments_colleges",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    department_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(45),
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

    college: Mapped["College"] = relationship(
        "College",
        back_populates="departments",
        lazy="joined",
    )

    @property
    def active(self) -> bool:
        """Return the department status as a Python Boolean value."""

        return bool(self.is_active)

    def __repr__(self) -> str:
        """Return a developer-friendly representation of the department."""

        return (
            f"Department(department_id={self.department_id!r}, "
            f"name={self.name!r}, "
            f"department_code={self.department_code!r}, "
            f"college_id={self.college_id!r})"
        )
