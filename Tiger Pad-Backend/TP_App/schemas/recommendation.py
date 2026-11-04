"""
Overall function:
This file defines Pydantic schemas for TigerPad student recommendations.

Recommendations are generated from readiness scores and skill gaps. They give
students clear actions for improving skills, résumés, projects, experience,
and career readiness.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RecommendationStatus = Literal[
    "active",
    "completed",
    "dismissed",
    "expired",
]


class RecommendationUpdateRequest(BaseModel):
    """Validate a student's recommendation status update."""

    status: RecommendationStatus


class RecommendationResponse(BaseModel):
    """Return one TigerPad recommendation."""

    model_config = ConfigDict(from_attributes=True)

    recommendation_id: int
    student_profile_id: int
    career_path_id: int | None = None
    readiness_score_id: int | None = None
    skill_gap_id: int | None = None
    recommendation_type: str
    title: str
    description: str
    action_text: str | None = None
    action_url: str | None = None
    priority_level: int
    source_type: str
    status: RecommendationStatus
    due_date: date | None = None
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None
    expired_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RecommendationSummary(BaseModel):
    """Return a compact recommendation for a dashboard."""

    model_config = ConfigDict(from_attributes=True)

    recommendation_id: int
    recommendation_type: str
    title: str
    action_text: str | None = None
    priority_level: int
    status: RecommendationStatus
    due_date: date | None = None