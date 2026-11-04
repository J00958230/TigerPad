"""
Overall function:
This file defines the request and response schemas for TigerPad progress
events. Progress events represent student milestones such as profile updates,
skill additions, résumé analysis, readiness calculations, projects,
certifications, and completed recommendations.

The schemas validate data before it reaches the database and control which
progress information is returned through the API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProgressEventType(str, Enum):
    """Approved categories for TigerPad student progress events."""

    profile_created = "profile_created"
    profile_updated = "profile_updated"
    program_added = "program_added"
    career_goal_created = "career_goal_created"
    skill_added = "skill_added"
    experience_added = "experience_added"
    project_added = "project_added"
    certification_added = "certification_added"
    resume_created = "resume_created"
    resume_analyzed = "resume_analyzed"
    readiness_calculated = "readiness_calculated"
    recommendation_completed = "recommendation_completed"
    interview_completed = "interview_completed"
    milestone_completed = "milestone_completed"


class ProgressEventSourceType(str, Enum):
    """Sources allowed to create or generate progress events."""

    system = "system"
    user = "user"
    ai = "ai"
    faculty = "faculty"


class ProgressEventCreate(BaseModel):
    """
    Validate a progress event submitted by an authenticated student.

    Student-created events are always stored by the route as source_type
    ``user``. Students cannot impersonate system, AI, or faculty events.
    """

    career_path_id: int | None = Field(
        default=None,
        ge=1,
        description="Optional career path connected to this event.",
    )

    event_type: ProgressEventType = Field(
        description="Category of the progress event.",
    )

    title: str = Field(
        min_length=1,
        max_length=200,
        description="Short title displayed in the progress timeline.",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional explanation of the milestone.",
    )

    related_entity_type: str | None = Field(
        default=None,
        max_length=40,
        description="Optional related table or entity type.",
    )

    related_entity_id: int | None = Field(
        default=None,
        ge=1,
        description="Optional identifier of the related entity.",
    )

    event_data_json: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured event details.",
    )

    is_visible_to_student: bool = Field(
        default=True,
        description="Whether the event appears in the student's timeline.",
    )

    occurred_at: datetime | None = Field(
        default=None,
        description="When the milestone occurred.",
    )


class ProgressEventResponse(BaseModel):
    """Represent a progress event returned by the TigerPad API."""

    model_config = ConfigDict(from_attributes=True)

    progress_event_id: int
    student_profile_id: int
    career_path_id: int | None
    event_type: str
    title: str
    description: str | None
    related_entity_type: str | None
    related_entity_id: int | None
    event_data_json: dict[str, Any] | None
    source_type: str
    is_visible_to_student: bool
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime