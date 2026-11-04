"""
Overall function:
This file defines the SQLAlchemy model for the career_path_skills table.

The career_path_skills table connects career paths with the skills that
students should develop for those careers. It records how important each
skill is, the recommended proficiency level, and whether the skill is
required for the selected career path.

This model represents a many-to-many relationship between career_paths
and skills. Deleting either the connected career path or skill will also
remove its career-path skill records from this table.
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
    from TP_App.models.career_path import CareerPath
    from TP_App.models.skill import Skill


class CareerPathSkill(Base):
    """
    Connect a TigerPad career path with a recommended skill.

    Each career path can require multiple skills, and each skill can
    belong to multiple career paths. The unique database constraint
    prevents the same skill from being assigned to the same career
    path more than once.
    """

    __tablename__ = "career_path_skills"

    __table_args__ = (
        UniqueConstraint(
            "career_path_id",
            "skill_id",
            name="uq_career_path_skills_path_skills",
        ),
        Index(
            "fk_career_path_skills_skill_idx",
            "skill_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    career_path_skill_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    career_path_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_career_path_skills_path",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    skill_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "skills.skill_id",
            name="fk_career_path_skills_skill",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    importance_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=3,
        server_default=text("3"),
    )

    target_proficiency_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=3,
        server_default=text("3"),
    )

    is_required: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
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

    career_path: Mapped["CareerPath"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    skill: Mapped["Skill"] = relationship(
        "Skill",
        lazy="joined",
    )

    @property
    def required(self) -> bool:
        """Return whether this skill is required for the career path."""
        return bool(self.is_required)

    @property
    def active(self) -> bool:
        """Return whether this career-path skill connection is active."""
        return bool(self.is_active)

    @property
    def importance_description(self) -> str:
        """Return a readable description of the importance level."""

        importance_levels = {
            1: "Low",
            2: "Moderate",
            3: "Important",
            4: "High",
            5: "Critical",
        }

        return importance_levels.get(
            self.importance_level,
            "Unknown",
        )

    @property
    def target_proficiency_description(self) -> str:
        """Return a readable description of the target proficiency."""

        proficiency_levels = {
            1: "Beginner",
            2: "Developing",
            3: "Intermediate",
            4: "Advanced",
            5: "Expert",
        }

        return proficiency_levels.get(
            self.target_proficiency_level,
            "Unknown",
        )

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<CareerPathSkill("
            f"career_path_skill_id={self.career_path_skill_id}, "
            f"career_path_id={self.career_path_id}, "
            f"skill_id={self.skill_id}, "
            f"importance_level={self.importance_level}, "
            f"is_required={self.required}"
            ")>"
        )
