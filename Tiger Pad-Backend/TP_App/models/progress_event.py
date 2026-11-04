"""
Overall function:
This file defines the SQLAlchemy model for the progress_events table.

The progress_events table stores important actions, milestones, and changes
in a TigerPad student's career-readiness journey. Examples include completing
a profile, adding a project, improving a readiness score, resolving a skill
gap, completing a recommendation, or updating a résumé.

These events allow TigerPad to build a student progress timeline, display
recent achievements, measure engagement, and provide faculty members with
appropriate progress information.
"""

from __future__ import annotations

from datetime import datetime
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
    INTEGER,
    JSON,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.student_profile import StudentProfile


class ProgressEvent(Base):
    """
    Represent an event in a student's TigerPad progress timeline.

    Every event belongs to one student profile. A career path is optional
    because some events apply to the student's overall TigerPad progress.
    """

    __tablename__ = "progress_events"

    __table_args__ = (
        Index(
            "idx_progress_events_student_occurred",
            "student_profile_id",
            "occurred_at",
        ),
        Index(
            "fk_progress_events_career_path_idx",
            "career_path_id",
        ),
        Index(
            "idx_progress_events_event_type",
            "event_type",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    progress_event_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_progress_events_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_progress_events_career_path",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    related_entity_type: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    related_entity_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    event_data_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="system",
        server_default=text("'system'"),
    )

    is_visible_to_student: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DATETIME,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DATETIME,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DATETIME,
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

    @property
    def event_type_description(self) -> str:
        """Return the event type in a user-friendly format."""

        event_types = {
            "profile_completed": "Profile Completed",
            "profile_updated": "Profile Updated",
            "resume_created": "Résumé Created",
            "resume_uploaded": "Résumé Uploaded",
            "resume_analyzed": "Résumé Analyzed",
            "skill_added": "Skill Added",
            "skill_improved": "Skill Improved",
            "skill_gap_resolved": "Skill Gap Resolved",
            "project_added": "Project Added",
            "experience_added": "Experience Added",
            "certification_added": "Certification Added",
            "career_goal_added": "Career Goal Added",
            "readiness_score_updated": "Readiness Score Updated",
            "recommendation_completed": "Recommendation Completed",
            "interview_completed": "Interview Practice Completed",
        }

        return event_types.get(
            self.event_type,
            self.event_type.replace("_", " ").title(),
        )

    @property
    def source_description(self) -> str:
        """Return the event source in a user-friendly format."""

        sources = {
            "system": "TigerPad system",
            "student": "Student activity",
            "faculty": "Faculty activity",
            "admin": "Administrator activity",
            "ai": "TigerPad AI",
        }

        return sources.get(
            self.source_type,
            self.source_type.replace("_", " ").title(),
        )

    @property
    def visible_to_student(self) -> bool:
        """Return whether the event can appear on the student's timeline."""

        return bool(self.is_visible_to_student)

    @property
    def is_career_specific(self) -> bool:
        """Return whether the event is connected to a career path."""

        return self.career_path_id is not None

    @property
    def has_related_entity(self) -> bool:
        """Return whether the event references another TigerPad record."""

        return bool(
            self.related_entity_type
            and self.related_entity_id is not None
        )

    @property
    def related_entity_reference(self) -> str | None:
        """Return a readable reference to the related TigerPad record."""

        if not self.has_related_entity:
            return None

        entity_name = self.related_entity_type.replace(
            "_",
            " ",
        ).title()

        return f"{entity_name} #{self.related_entity_id}"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<ProgressEvent("
            f"progress_event_id={self.progress_event_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"career_path_id={self.career_path_id}, "
            f"event_type={self.event_type!r}, "
            f"occurred_at={self.occurred_at!r}, "
            f"is_visible_to_student={self.visible_to_student}"
            ")>"
        )
