"""
Overall function:
This file defines the SQLAlchemy model for the student_skills table.

The student_skills table records the skills that a TigerPad student possesses,
their current proficiency level, years of experience, verification status,
and any evidence supporting the skill.

This information allows TigerPad to compare a student's current abilities
with the skills recommended for a career path. That comparison can later
help identify skill gaps and generate personalized career-readiness
recommendations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import (
    DECIMAL,
    INTEGER,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.skill import Skill
    from TP_App.models.student_profile import StudentProfile


class StudentSkill(Base):
    """
    Represent a skill reported or verified for a TigerPad student.

    Each student can have multiple skills, but the same skill cannot be
    assigned to the same student profile more than once.
    """

    __tablename__ = "student_skills"

    __table_args__ = (
        UniqueConstraint(
            "student_profile_id",
            "skill_id",
            name="uq_student_skills_student_skill",
        ),
        Index(
            "fk_student_skills_skill_idx",
            "skill_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    student_skill_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_student_skills_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    skill_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "skills.skill_id",
            name="fk_student_skills_skill",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    proficiency_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    years_experience: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=4,
            scale=1,
            unsigned=True,
        ),
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="self_reported",
        server_default=text("'self_reported'"),
    )

    evidence_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    evidence_url: Mapped[str | None] = mapped_column(
        String(500),
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

    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        lazy="joined",
    )

    skill: Mapped["Skill"] = relationship(
        "Skill",
        lazy="joined",
    )

    @property
    def proficiency_description(self) -> str:
        """Return a readable description of the proficiency level."""

        proficiency_levels = {
            1: "Beginner",
            2: "Developing",
            3: "Intermediate",
            4: "Advanced",
            5: "Expert",
        }

        return proficiency_levels.get(
            self.proficiency_level,
            "Unknown",
        )

    @property
    def verification_description(self) -> str:
        """Return a readable description of the verification status."""

        verification_statuses = {
            "self_reported": "Self-reported",
            "faculty_verified": "Faculty verified",
            "document_verified": "Document verified",
            "assessment_verified": "Assessment verified",
        }

        return verification_statuses.get(
            self.verification_status,
            self.verification_status.replace("_", " ").title(),
        )

    @property
    def has_evidence(self) -> bool:
        """Return whether evidence was provided for the skill."""

        return bool(
            self.evidence_description
            or self.evidence_url
        )

    @property
    def verified(self) -> bool:
        """Return whether the skill has verification beyond self-reporting."""

        return self.verification_status != "self_reported"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<StudentSkill("
            f"student_skill_id={self.student_skill_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"skill_id={self.skill_id}, "
            f"proficiency_level={self.proficiency_level!r}, "
            f"verification_status={self.verification_status!r}"
            ")>"
        )
