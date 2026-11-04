"""
Overall function:
This file defines the SQLAlchemy model for the resume_analysis table.

The resume_analysis table stores the results of TigerPad résumé evaluations.
It records overall and category-specific scores, identified strengths,
recommended improvements, section-level feedback, analysis status, AI model
information, and processing timestamps.

A résumé analysis can optionally target a particular career path, allowing
TigerPad to determine how well a student's résumé aligns with the expectations
of a specific field while still supporting general résumé evaluations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import (
    CHAR,
    DATETIME,
    DECIMAL,
    INTEGER,
    JSON,
    TIMESTAMP,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.resume import Resume


class ResumeAnalysis(Base):
    """
    Represent an analysis performed on a TigerPad résumé.

    Every analysis belongs to one résumé. The career path is optional because
    TigerPad can perform either general or career-specific résumé evaluations.
    """

    __tablename__ = "resume_analysis"

    __table_args__ = (
        Index(
            "fk_resume_analyses_resume_idx",
            "resume_id",
        ),
        Index(
            "fk_resume_analyses_career_path_idx",
            "career_path_id",
        ),
        Index(
            "idx_resume_analyses_status",
            "analysis_status",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    resume_analysis_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    resume_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "resumes.resume_id",
            name="fk_resume_analyses_resume",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_resume_analyses_career_path",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    analysis_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    analysis_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="hybrid",
        server_default=text("'hybrid'"),
    )

    overall_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    content_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    format_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    impact_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    career_alignment_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    strengths_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    improvements_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    section_feedback_json: Mapped[
        list[Any] | dict[str, Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    input_sha256_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
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

    resume: Mapped["Resume"] = relationship(
        "Resume",
        lazy="joined",
    )

    career_path: Mapped["CareerPath | None"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    @property
    def status_description(self) -> str:
        """Return the analysis status in a user-friendly format."""

        statuses = {
            "pending": "Waiting to begin",
            "processing": "Analysis in progress",
            "completed": "Analysis completed",
            "failed": "Analysis failed",
        }

        return statuses.get(
            self.analysis_status,
            self.analysis_status.replace("_", " ").title(),
        )

    @property
    def method_description(self) -> str:
        """Return the analysis method in a user-friendly format."""

        methods = {
            "rules": "Rules-based analysis",
            "ai": "AI analysis",
            "hybrid": "Rules-based and AI analysis",
            "manual": "Manual review",
        }

        return methods.get(
            self.analysis_method,
            self.analysis_method.replace("_", " ").title(),
        )

    @property
    def is_pending(self) -> bool:
        """Return whether the analysis is waiting to begin."""

        return self.analysis_status == "pending"

    @property
    def is_processing(self) -> bool:
        """Return whether the analysis is currently running."""

        return self.analysis_status == "processing"

    @property
    def is_completed(self) -> bool:
        """Return whether the résumé analysis completed successfully."""

        return self.analysis_status == "completed"

    @property
    def is_failed(self) -> bool:
        """Return whether the résumé analysis failed."""

        return self.analysis_status == "failed"

    @property
    def is_career_specific(self) -> bool:
        """Return whether the analysis targets a career path."""

        return self.career_path_id is not None

    @property
    def processing_time_seconds(self) -> float | None:
        """Return the analysis processing time in seconds."""

        if self.started_at is None or self.completed_at is None:
            return None

        return round(
            (self.completed_at - self.started_at).total_seconds(),
            3,
        )

    @property
    def has_feedback(self) -> bool:
        """Return whether any résumé feedback is available."""

        return bool(
            self.summary
            or self.strengths_json
            or self.improvements_json
            or self.section_feedback_json
        )

    @property
    def score_description(self) -> str:
        """Return a readable description of the overall résumé score."""

        if self.overall_score is None:
            return "Not scored"

        score = float(self.overall_score)

        if score >= 90:
            return "Excellent"
        if score >= 80:
            return "Strong"
        if score >= 70:
            return "Good"
        if score >= 60:
            return "Developing"

        return "Needs improvement"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<ResumeAnalysis("
            f"resume_analysis_id={self.resume_analysis_id}, "
            f"resume_id={self.resume_id}, "
            f"career_path_id={self.career_path_id}, "
            f"analysis_status={self.analysis_status!r}, "
            f"analysis_method={self.analysis_method!r}, "
            f"overall_score={self.overall_score}"
            ")>"
        )
