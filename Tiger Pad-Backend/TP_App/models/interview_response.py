"""
Overall function:
This file defines the SQLAlchemy model for the interview_responses table.

The interview_responses table stores each question and student response from
a TigerPad mock interview session. It includes evaluation criteria, the
student's answer, response score, feedback, strengths, improvement areas,
response duration, and question timing.

Each interview session can contain multiple responses, but a question number
can appear only once within the same interview session.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATETIME,
    DECIMAL,
    INTEGER,
    JSON,
    SMALLINT,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.interview_session import InterviewSession


class InterviewResponse(Base):
    """
    Represent one question and response in a mock interview session.

    Every response belongs to one interview session. The unique constraint
    prevents the same question number from being stored more than once in
    the same session.
    """

    __tablename__ = "interview_responses"

    __table_args__ = (
        UniqueConstraint(
            "interview_session_id",
            "question_number",
            name="uq_interview_responses_session_question",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    interview_response_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    interview_session_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "interview_sessions.interview_session_id",
            name="fk_interview_responses_session",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    question_number: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True),
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evaluation_criteria_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    student_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    response_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=5,
            scale=2,
            unsigned=True,
        ),
        nullable=True,
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    strengths_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    improvements_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    is_follow_up: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    response_duration_seconds: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
        default=0,
        server_default=text("0"),
    )

    asked_at: Mapped[datetime] = mapped_column(
        DATETIME,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    answered_at: Mapped[datetime | None] = mapped_column(
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

    interview_session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        lazy="joined",
    )

    @property
    def question_type_description(self) -> str:
        """Return the question type in a user-friendly format."""

        question_types = {
            "behavioral": "Behavioral Question",
            "technical": "Technical Question",
            "situational": "Situational Question",
            "case": "Case Question",
            "general": "General Question",
            "follow_up": "Follow-up Question",
        }

        return question_types.get(
            self.question_type,
            self.question_type.replace("_", " ").title(),
        )

    @property
    def follow_up(self) -> bool:
        """Return whether this is a follow-up question."""

        return bool(self.is_follow_up)

    @property
    def has_response(self) -> bool:
        """Return whether the student submitted a response."""

        return bool(
            self.student_response
            and self.student_response.strip()
        )

    @property
    def is_answered(self) -> bool:
        """Return whether the question has been answered."""

        return bool(
            self.has_response
            or self.answered_at is not None
        )

    @property
    def has_evaluation(self) -> bool:
        """Return whether evaluation results are available."""

        return bool(
            self.response_score is not None
            or self.feedback
            or self.strengths_json
            or self.improvements_json
        )

    @property
    def score_description(self) -> str:
        """Return a readable description of the response score."""

        if self.response_score is None:
            return "Not scored"

        score = float(self.response_score)

        if score >= 90:
            return "Excellent response"

        if score >= 80:
            return "Strong response"

        if score >= 70:
            return "Good response"

        if score >= 60:
            return "Developing response"

        return "Needs more practice"

    @property
    def duration_description(self) -> str:
        """Return the response duration in minutes and seconds."""

        if self.response_duration_seconds is None:
            return "Duration not available"

        minutes, seconds = divmod(
            self.response_duration_seconds,
            60,
        )

        return f"{minutes}m {seconds}s"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<InterviewResponse("
            f"interview_response_id={self.interview_response_id}, "
            f"interview_session_id={self.interview_session_id}, "
            f"question_number={self.question_number}, "
            f"question_type={self.question_type!r}, "
            f"response_score={self.response_score}, "
            f"is_follow_up={self.follow_up}"
            ")>"
        )
