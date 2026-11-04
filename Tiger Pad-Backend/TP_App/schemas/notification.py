
"""
Overall function:
This file defines the request and response schemas for TigerPad
notifications. Notifications inform students about recommendations,
readiness-score updates, résumé-analysis results, completed milestones,
interview feedback, and other TigerPad activity.

Students can read or mark notifications as read, but notification creation
will be handled by trusted backend services.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    """Common notification categories used by TigerPad."""

    recommendation = "recommendation"
    readiness = "readiness"
    resume_analysis = "resume_analysis"
    milestone = "milestone"
    interview = "interview"
    profile = "profile"
    system = "system"
    faculty_feedback = "faculty_feedback"


class NotificationUpdateRequest(BaseModel):
    """Validate a student's request to change notification read status."""

    is_read: bool = Field(
        description="Whether the notification has been read.",
    )


class NotificationResponse(BaseModel):
    """Represent a notification returned by the TigerPad API."""

    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    action_url: str | None
    related_entity_type: str | None
    related_entity_id: int | None
    priority_level: int
    delivery_channel: str
    delivery_status: str
    is_read: bool
    read_at: datetime | None
    scheduled_for: datetime | None
    sent_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationMarkAllReadResponse(BaseModel):
    """Return the result of marking unread notifications as read."""

    success: bool
    updated_count: int
    message: str
