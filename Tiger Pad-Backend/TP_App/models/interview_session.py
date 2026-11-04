"""
Overall function:
This file defines the SQLAlchemy model for the interview_sessions table.

The interview_sessions table stores mock interview practice sessions completed
through TigerPad. A session can be general or tailored to a career path and
can optionally use one of the student's résumés to create more relevant
interview questions.

The table records interview type, difficulty, question count, settings,
overall score, feedback, AI model information, duration, and session status.
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
    DATETIME,
    DECIMAL,
    INTEGER,
    JSON,
    SMALLINT,
    TIMESTAMP,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.resume import Resume
    from TP_App.models.student_profile import StudentProfile


class InterviewSession(Base):
    """
    Represent a TigerPad mock interview practice session.

    Every session belongs to one student profile. Career path and résumé
    relationships are optional because TigerPad can also provide general
    interview practice.
    """

    __tablename__ = "interview_sessions"

    __table_args__ = (
        Index(
            "fk_interview_sessions_student_profile_idx",
            "student_profile_id",
        ),
        Index(
            "fk_interview_sessions_career_path_idx",
            "career_path_id",
        ),
        Index(
            "fk_interview_sessions_resume_idx",
            "resume_id",
        ),
        Index(
            "idx_interview_sessions_status",
            "status",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    interview_session_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_interview_sessions_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_interview_sessions_career_path",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    resume_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "resumes.resume_id",
            name="fk_interview_sessions_resume",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    interview_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="behavioral",
        server_default=text("'behavioral'"),
    )

    difficulty_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="beginner",
        server_default=text("'beginner'"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="created",
        server_default=text("'created'"),
    )

    question_count: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True),
        nullable=False,
        default=5,
        server_default=text("5"),
    )

    settings_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    overall_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    feedback_summary: Mapped[str | None] = mapped_column(
        Text,
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

    duration_seconds: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
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

    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        lazy="joined",
    )

    career_path: Mapped["CareerPath | None"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    resume: Mapped["Resume | None"] = relationship(
        "Resume",
        lazy="joined",
    )

    @property
    def interview_type_description(self) -> str:
        """Return the interview type in a user-friendly format."""

        interview_types = {
            "behavioral": "Behavioral Interview",
            "technical": "Technical Interview",
            "case": "Case Interview",
            "situational": "Situational Interview",
            "panel": "Panel Interview Practice",
            "general": "General Interview",
        }

        return interview_types.get(
            self.interview_type,
            self.interview_type.replace("_", " ").title(),
        )

    @property
    def difficulty_description(self) -> str:
        """Return the difficulty level in a user-friendly format."""

        return self.difficulty_level.replace("_", " ").title()

    @property
    def status_description(self) -> str:
        """Return the session status in a user-friendly format."""

        statuses = {
            "created": "Ready to begin",
            "in_progress": "In progress",
            "completed": "Completed",
            "abandoned": "Not completed",
            "failed": "Unable to complete",
        }

        return statuses.get(
            self.status,
            self.status.replace("_", " ").title(),
        )

    @property
    def is_created(self) -> bool:
        """Return whether the session is ready to begin."""

        return self.status == "created"

    @property
    def is_in_progress(self) -> bool:
        """Return whether the interview is currently in progress."""

        return self.status == "in_progress"

    @property
    def is_completed(self) -> bool:
        """Return whether the interview session is complete."""

        return (
            self.status == "completed"
            or self.completed_at is not None
        )

    @property
    def is_career_specific(self) -> bool:
        """Return whether the interview targets a career path."""

        return self.career_path_id is not None

    @property
    def uses_resume(self) -> bool:
        """Return whether the interview uses a student résumé."""

        return self.resume_id is not None

    @property
    def score_description(self) -> str:
        """Return a readable description of the interview score."""

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

        return "Needs more practice"

    @property
    def duration_description(self) -> str:
        """Return the session duration in minutes and seconds."""

        if self.duration_seconds is None:
            return "Duration not available"

        minutes, seconds = divmod(
            self.duration_seconds,
            60,
        )

        return f"{minutes}m {seconds}s"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<InterviewSession("
            f"interview_session_id={self.interview_session_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"career_path_id={self.career_path_id}, "
            f"interview_type={self.interview_type!r}, "
            f"difficulty_level={self.difficulty_level!r}, "
            f"status={self.status!r}, "
            f"overall_score={self.overall_score}"
            ")>"
        )
