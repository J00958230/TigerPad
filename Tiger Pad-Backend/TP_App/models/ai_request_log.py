"""
Overall function:
This file defines the SQLAlchemy model for the ai_request_logs table.

The ai_request_logs table records requests made to AI providers for TigerPad
features such as résumé analysis, career recommendations, skill-gap guidance,
and interview practice.

The table tracks request status, provider and model information, token usage,
latency, estimated cost, content hashes, safety flags, failures, and blocked
requests. Raw prompts and AI responses are intentionally not stored here,
which reduces the risk of exposing private student information.
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
    BIGINT,
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
    from TP_App.models.user import User


class AIRequestLog(Base):
    """
    Represent a logged AI request made through TigerPad.

    The user relationship is optional because some requests may be generated
    by system operations or may remain after an associated user is removed.
    """

    __tablename__ = "ai_request_logs"

    __table_args__ = (
        Index(
            "request_id_UNIQUE",
            "request_id",
            unique=True,
        ),
        Index(
            "idx_ai_request_logs_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "idx_ai_request_logs_status_created",
            "status",
            "created_at",
        ),
        Index(
            "idx_ai_request_logs_feature_created",
            "feature_type",
            "created_at",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    ai_request_log_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "users.user_id",
            name="fk_ai_request_logs_user",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    request_id: Mapped[str] = mapped_column(
        CHAR(36),
        nullable=False,
    )

    feature_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="groq",
        server_default=text("'groq'"),
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    input_token_count: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    output_token_count: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        DECIMAL(
            precision=10,
            scale=6,
            unsigned=True,
        ),
        nullable=True,
    )

    input_sha256_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    output_sha256_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    safety_flags_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    blocked_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DATETIME,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
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

    user: Mapped["User | None"] = relationship(
        "User",
        lazy="joined",
    )

    @property
    def feature_description(self) -> str:
        """Return the AI feature type in a user-friendly format."""

        features = {
            "resume_analysis": "Résumé Analysis",
            "resume_generation": "Résumé Generation",
            "career_recommendation": "Career Recommendation",
            "skill_gap_analysis": "Skill-Gap Analysis",
            "interview_question": "Interview Question Generation",
            "interview_feedback": "Interview Feedback",
            "profile_guidance": "Profile Guidance",
        }

        return features.get(
            self.feature_type,
            self.feature_type.replace("_", " ").title(),
        )

    @property
    def status_description(self) -> str:
        """Return the request status in a user-friendly format."""

        statuses = {
            "pending": "Waiting to begin",
            "processing": "Processing",
            "completed": "Completed",
            "failed": "Failed",
            "blocked": "Blocked by safety controls",
            "cancelled": "Cancelled",
        }

        return statuses.get(
            self.status,
            self.status.replace("_", " ").title(),
        )

    @property
    def is_pending(self) -> bool:
        """Return whether the request is waiting to begin."""

        return self.status == "pending"

    @property
    def is_completed(self) -> bool:
        """Return whether the AI request completed successfully."""

        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Return whether the AI request failed."""

        return self.status == "failed"

    @property
    def is_blocked(self) -> bool:
        """Return whether TigerPad blocked the AI request."""

        return self.status == "blocked"

    @property
    def has_safety_flags(self) -> bool:
        """Return whether the request produced any safety flags."""

        return bool(self.safety_flags_json)

    @property
    def total_token_count(self) -> int:
        """Return the combined input and output token count."""

        return (
            (self.input_token_count or 0)
            + (self.output_token_count or 0)
        )

    @property
    def latency_seconds(self) -> float | None:
        """Convert the stored latency from milliseconds to seconds."""

        if self.latency_ms is None:
            return None

        return round(
            self.latency_ms / 1000,
            3,
        )

    @property
    def processing_time_seconds(self) -> float | None:
        """Return the measured processing time from the timestamps."""

        if self.completed_at is None:
            return None

        return round(
            (self.completed_at - self.started_at).total_seconds(),
            3,
        )

    @property
    def has_input_hash(self) -> bool:
        """Return whether the request input was hashed."""

        return bool(self.input_sha256_hash)

    @property
    def has_output_hash(self) -> bool:
        """Return whether the AI output was hashed."""

        return bool(self.output_sha256_hash)

    def __repr__(self) -> str:
        """
        Return a safe developer representation of the AI request.

        Input hashes, output hashes, safety details, and blocked reasons
        are intentionally excluded.
        """

        return (
            "<AIRequestLog("
            f"ai_request_log_id={self.ai_request_log_id}, "
            f"user_id={self.user_id}, "
            f"request_id={self.request_id!r}, "
            f"feature_type={self.feature_type!r}, "
            f"provider_name={self.provider_name!r}, "
            f"model_name={self.model_name!r}, "
            f"status={self.status!r}"
            ")>"
        )
