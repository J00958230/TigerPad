"""
Overall function:
This file defines the SQLAlchemy model for the readiness_scores table.

The readiness_scores table stores TigerPad's evaluation of how prepared a
student is for a specific career path. It records an overall readiness score
and separate scores for academics, skills, experience, projects,
certifications, and résumé quality.

The table also stores the scoring weights, detailed calculation information,
the calculation version, and a profile snapshot hash so TigerPad can identify
when a student's profile has changed and a new score should be calculated.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.mysql import (
    CHAR,
    DATETIME,
    DECIMAL,
    INTEGER,
    JSON,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.resume_analysis import ResumeAnalysis
    from TP_App.models.student_profile import StudentProfile


class ReadinessScore(Base):
    """
    Represent a student's readiness score for a selected career path.

    A student can have multiple historical readiness scores. The is_current
    column identifies whether a particular score is the student's current
    score for that career path.
    """

    __tablename__ = "readiness_scores"

    __table_args__ = (
        Index(
            "fk_readiness_scores_student_profile_idx",
            "student_profile_id",
        ),
        Index(
            "fk_readiness_scores_career_path_idx",
            "career_path_id",
        ),
        Index(
            "fk_readiness_scores_resume_analysis_idx",
            "resume_analysis_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    readiness_score_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_readiness_scores_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_readiness_scores_career_path",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    resume_analysis_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "resume_analysis.resume_analysis_id",
            name="fk_readiness_scores_resume_analysis",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    overall_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    academic_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    skill_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    experience_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    project_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    certification_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    resume_score: Mapped[Decimal] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=False,
    )

    calculation_version: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    weights_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    score_details_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    profile_snapshot_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
    )

    is_current: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DATETIME,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
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

    career_path: Mapped["CareerPath"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    resume_analysis: Mapped["ResumeAnalysis | None"] = relationship(
        "ResumeAnalysis",
        lazy="joined",
    )

    @property
    def current(self) -> bool:
        """Return whether this is the current readiness score."""

        return bool(self.is_current)

    @property
    def score_description(self) -> str:
        """Return a readable description of the overall readiness score."""

        score = float(self.overall_score)

        if score >= 90:
            return "Career ready"
        if score >= 80:
            return "Nearly career ready"
        if score >= 70:
            return "Good progress"
        if score >= 60:
            return "Developing readiness"
        if score >= 40:
            return "Early preparation"

        return "Beginning preparation"

    @property
    def strongest_category(self) -> str:
        """Return the category with the student's highest score."""

        category_scores = {
            "Academics": self.academic_score,
            "Skills": self.skill_score,
            "Experience": self.experience_score,
            "Projects": self.project_score,
            "Certifications": self.certification_score,
            "Résumé": self.resume_score,
        }

        return max(
            category_scores,
            key=category_scores.get,
        )

    @property
    def weakest_category(self) -> str:
        """Return the category with the student's lowest score."""

        category_scores = {
            "Academics": self.academic_score,
            "Skills": self.skill_score,
            "Experience": self.experience_score,
            "Projects": self.project_score,
            "Certifications": self.certification_score,
            "Résumé": self.resume_score,
        }

        return min(
            category_scores,
            key=category_scores.get,
        )

    @property
    def category_scores(self) -> dict[str, float]:
        """Return the readiness categories as standard float values."""

        return {
            "academic": float(self.academic_score),
            "skill": float(self.skill_score),
            "experience": float(self.experience_score),
            "project": float(self.project_score),
            "certification": float(self.certification_score),
            "resume": float(self.resume_score),
        }

    @property
    def has_resume_analysis(self) -> bool:
        """Return whether this score uses a résumé analysis."""

        return self.resume_analysis_id is not None

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<ReadinessScore("
            f"readiness_score_id={self.readiness_score_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"career_path_id={self.career_path_id}, "
            f"overall_score={self.overall_score}, "
            f"calculation_version={self.calculation_version!r}, "
            f"is_current={self.current}"
            ")>"
        )
