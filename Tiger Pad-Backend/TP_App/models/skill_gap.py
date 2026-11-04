"""
Overall function:
This file defines the SQLAlchemy model for the skill_gaps table.

The skill_gaps table stores the difference between a student's current skill
level and the skill level recommended for a selected career path. Each record
connects a readiness score, a career-path skill requirement, and, when
available, the student's corresponding skill record.

TigerPad can use this information to prioritize areas for improvement,
recommend specific actions, and track when a student resolves a skill gap.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATETIME,
    DECIMAL,
    INTEGER,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path_skill import CareerPathSkill
    from TP_App.models.readiness_score import ReadinessScore
    from TP_App.models.student_skill import StudentSkill


class SkillGap(Base):
    """
    Represent a gap between a student's current and target skill levels.

    A readiness score can contain multiple skill gaps. Each gap identifies
    the career-path skill being evaluated and can optionally connect to an
    existing student skill.

    If student_skill_id is null, the student has not yet reported that skill.
    """

    __tablename__ = "skill_gaps"

    __table_args__ = (
        UniqueConstraint(
            "readiness_score_id",
            "career_path_skill_id",
            name="uq_skill_gaps_readiness_path_skill",
        ),
        Index(
            "fk_skill_gaps_career_path_skill_idx",
            "career_path_skill_id",
        ),
        Index(
            "fk_skill_gaps_student_skill_idx",
            "student_skill_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    skill_gap_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    readiness_score_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "readiness_scores.readiness_score_id",
            name="fk_skill_gaps_readiness_score",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_skill_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_path_skills.career_path_skill_id",
            name="fk_skill_gaps_career_path_skill",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    student_skill_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_skills.student_skill_id",
            name="fk_skill_gaps_student_skill",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    current_proficiency_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    target_proficiency_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    importance_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    gap_size: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    priority_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    gap_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default=text("'open'"),
    )

    recommend_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
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

    readiness_score: Mapped["ReadinessScore"] = relationship(
        "ReadinessScore",
        lazy="joined",
    )

    career_path_skill: Mapped["CareerPathSkill"] = relationship(
        "CareerPathSkill",
        lazy="joined",
    )

    student_skill: Mapped["StudentSkill | None"] = relationship(
        "StudentSkill",
        lazy="joined",
    )

    @property
    def current_proficiency_description(self) -> str:
        """Return a readable description of the current proficiency level."""

        proficiency_levels = {
            0: "Not demonstrated",
            1: "Beginner",
            2: "Developing",
            3: "Intermediate",
            4: "Advanced",
            5: "Expert",
        }

        return proficiency_levels.get(
            self.current_proficiency_level,
            "Unknown",
        )

    @property
    def target_proficiency_description(self) -> str:
        """Return a readable description of the target proficiency level."""

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
    def status_description(self) -> str:
        """Return the skill-gap status in a user-friendly format."""

        return self.gap_status.replace("_", " ").title()

    @property
    def is_open(self) -> bool:
        """Return whether the skill gap still requires attention."""

        return self.gap_status == "open"

    @property
    def is_resolved(self) -> bool:
        """Return whether the student has resolved the skill gap."""

        return (
            self.gap_status == "resolved"
            or self.resolved_at is not None
        )

    @property
    def student_has_skill(self) -> bool:
        """Return whether the student has a corresponding skill record."""

        return self.student_skill_id is not None

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<SkillGap("
            f"skill_gap_id={self.skill_gap_id}, "
            f"readiness_score_id={self.readiness_score_id}, "
            f"career_path_skill_id={self.career_path_skill_id}, "
            f"gap_size={self.gap_size}, "
            f"gap_status={self.gap_status!r}"
            ")>"
        )
