"""
Overall function:
This file defines the SQLAlchemy model for the recommendations table.

The recommendations table stores personalized career-readiness actions
generated for TigerPad students. Recommendations can be based on rules,
AI analysis, faculty guidance, résumé evaluations, readiness scores, or
specific skill gaps.

Recommendations may be general or connected to a career path, readiness
score, or skill gap. TigerPad can track their priority, deadline, completion,
dismissal, and expiration status.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATE,
    DATETIME,
    INTEGER,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.readiness_score import ReadinessScore
    from TP_App.models.skill_gap import SkillGap
    from TP_App.models.student_profile import StudentProfile


class Recommendation(Base):
    """
    Represent a personalized recommendation for a TigerPad student.

    Every recommendation belongs to a student profile. Its career path,
    readiness score, and skill gap relationships are optional because
    TigerPad can also provide general career-readiness recommendations.
    """

    __tablename__ = "recommendations"

    __table_args__ = (
        Index(
            "fk_recommendations_student_profile_idx",
            "student_profile_id",
        ),
        Index(
            "fk_recommendations_career_path_idx",
            "career_path_id",
        ),
        Index(
            "fk_recommendations_readiness_score_idx",
            "readiness_score_id",
        ),
        Index(
            "fk_recommendations_skill_gap_idx",
            "skill_gap_id",
        ),
        Index(
            "idx_recommendations_status_priority",
            "status",
            "priority_level",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    recommendation_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_recommendations_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_recommendations_career_path",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    readiness_score_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "readiness_scores.readiness_score_id",
            name="fk_recommendations_readiness_score",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    skill_gap_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "skill_gaps.skill_gap_id",
            name="fk_recommendations_skill_gap",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    recommendation_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    action_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    priority_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=3,
        server_default=text("3"),
    )

    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="rules",
        server_default=text("'rules'"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )

    due_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    dismissed_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    expired_at: Mapped[datetime | None] = mapped_column(
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

    readiness_score: Mapped["ReadinessScore | None"] = relationship(
        "ReadinessScore",
        lazy="joined",
    )

    skill_gap: Mapped["SkillGap | None"] = relationship(
        "SkillGap",
        lazy="joined",
    )

    @property
    def recommendation_type_description(self) -> str:
        """Return the recommendation type in a user-friendly format."""

        return self.recommendation_type.replace("_", " ").title()

    @property
    def source_description(self) -> str:
        """Return the recommendation source in a user-friendly format."""

        sources = {
            "rules": "TigerPad rules",
            "ai": "TigerPad AI",
            "hybrid": "TigerPad rules and AI",
            "faculty": "Faculty guidance",
            "admin": "Administrator guidance",
        }

        return sources.get(
            self.source_type,
            self.source_type.replace("_", " ").title(),
        )

    @property
    def priority_description(self) -> str:
        """Return a readable description of the priority level."""

        priorities = {
            1: "Very low",
            2: "Low",
            3: "Normal",
            4: "High",
            5: "Critical",
        }

        return priorities.get(
            self.priority_level,
            "Unknown",
        )

    @property
    def status_description(self) -> str:
        """Return the recommendation status in a user-friendly format."""

        return self.status.replace("_", " ").title()

    @property
    def is_active(self) -> bool:
        """Return whether the recommendation is active."""

        return self.status == "active"

    @property
    def is_completed(self) -> bool:
        """Return whether the recommendation has been completed."""

        return (
            self.status == "completed"
            or self.completed_at is not None
        )

    @property
    def is_dismissed(self) -> bool:
        """Return whether the recommendation has been dismissed."""

        return (
            self.status == "dismissed"
            or self.dismissed_at is not None
        )

    @property
    def is_expired(self) -> bool:
        """Return whether the recommendation has expired."""

        return (
            self.status == "expired"
            or self.expired_at is not None
        )

    @property
    def is_overdue(self) -> bool:
        """Return whether an active recommendation is past its due date."""

        return bool(
            self.due_date
            and self.is_active
            and self.due_date < date.today()
        )

    @property
    def has_action(self) -> bool:
        """Return whether an action or action link is available."""

        return bool(
            self.action_text
            or self.action_url
        )

    @property
    def is_career_specific(self) -> bool:
        """Return whether the recommendation targets a career path."""

        return self.career_path_id is not None

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<Recommendation("
            f"recommendation_id={self.recommendation_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"recommendation_type={self.recommendation_type!r}, "
            f"priority_level={self.priority_level}, "
            f"status={self.status!r}"
            ")>"
        )
