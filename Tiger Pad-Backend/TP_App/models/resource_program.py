"""
Overall function:
This file defines the SQLAlchemy model for the resource_programs table.

The resource_programs table connects TigerPad career-development resources
to the JSU academic programs for which they are relevant.

This creates a many-to-many relationship where one resource can support
multiple academic programs and one academic program can have multiple
resources. It also records the relevance level, optional notes, and whether
the connection is currently active.
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
from sqlalchemy.dialects.mysql import (
    INTEGER,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.academic_program import AcademicProgram
    from TP_App.models.resource import Resource


class ResourceProgram(Base):
    """
    Connect a TigerPad resource with a JSU academic program.

    The unique constraint prevents the same resource from being connected
    to the same academic program more than once.
    """

    __tablename__ = "resource_programs"

    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "program_id",
            name="uq_resource_programs_resource_program",
        ),
        Index(
            "fk_resource_programs_program_idx",
            "program_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    resource_program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    resource_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "resources.resource_id",
            name="fk_resource_programs_resource",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    program_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "academic_programs.program_id",
            name="fk_resource_programs_program",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    relevance_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="related",
        server_default=text("'related'"),
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=1,
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

    resource: Mapped["Resource"] = relationship(
        "Resource",
        lazy="joined",
    )

    academic_program: Mapped["AcademicProgram"] = relationship(
        "AcademicProgram",
        lazy="joined",
    )

    @property
    def relevance_description(self) -> str:
        """Return the relevance level in a user-friendly format."""

        relevance_levels = {
            "primary": "Primary resource",
            "high": "Highly relevant",
            "related": "Related resource",
            "supplemental": "Supplemental resource",
        }

        return relevance_levels.get(
            self.relevance_level,
            self.relevance_level.replace("_", " ").title(),
        )

    @property
    def active(self) -> bool:
        """Return whether this resource-program connection is active."""

        return bool(self.is_active)

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<ResourceProgram("
            f"resource_program_id={self.resource_program_id}, "
            f"resource_id={self.resource_id}, "
            f"program_id={self.program_id}, "
            f"relevance_level={self.relevance_level!r}, "
            f"is_active={self.active}"
            ")>"
        )
