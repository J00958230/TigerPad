"""
Overall function:
This file defines the request and response schemas for TigerPad mock
interviews. It validates interview session settings, interview questions,
student responses, scores, and feedback.

These schemas support behavioral, technical, situational, case, panel, and
general interview practice for students from all JSU academic disciplines.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterviewType(str, Enum):
    """Supported TigerPad interview formats."""

    behavioral = "behavioral"
    technical = "technical"
    case = "case"
    situational = "situational"
    panel = "panel"
    general = "general"


class InterviewDifficulty(str, Enum):
    """Supported interview difficulty levels."""

    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class InterviewStatus(str, Enum):
    """Possible interview session states."""

    created = "created"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class InterviewQuestionType(str, Enum):
    """Supported interview question categories."""

    behavioral = "behavioral"
    technical = "technical"
    situational = "situational"
    case = "case"
    general = "general"
    follow_up = "follow_up"


class InterviewSessionCreateRequest(BaseModel):
    """Validate a request to create a mock interview session."""

    career_path_id: int | None = Field(default=None, ge=1)
    resume_id: int | None = Field(default=None, ge=1)

    title: str = Field(
        default="TigerPad Mock Interview",
        min_length=1,
        max_length=200,
    )

    interview_type: InterviewType = InterviewType.behavioral
    difficulty_level: InterviewDifficulty = InterviewDifficulty.beginner

    question_count: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    settings_json: dict[str, Any] | None = None


class InterviewSessionResponse(BaseModel):
    """Represent a mock interview session returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    interview_session_id: int
    student_profile_id: int
    career_path_id: int | None
    resume_id: int | None
    title: str
    interview_type: str
    difficulty_level: str
    status: str
    question_count: int
    settings_json: dict[str, Any] | None
    overall_score: float | None
    feedback_summary: str | None
    model_name: str | None
    prompt_version: str | None
    duration_seconds: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InterviewResponseCreateRequest(BaseModel):
    """Validate a new interview question and optional answer."""

    question_number: int = Field(ge=1, le=100)
    question_type: InterviewQuestionType = (
        InterviewQuestionType.general
    )

    question_text: str = Field(
        min_length=1,
        max_length=10000,
    )

    evaluation_criteria_json: dict[str, Any] | None = None

    student_response: str | None = Field(
        default=None,
        max_length=20000,
    )

    is_follow_up: bool = False

    response_duration_seconds: int = Field(
        default=0,
        ge=0,
        le=7200,
    )


class InterviewResponseUpdateRequest(BaseModel):
    """
    Validate an update to an existing interview response.

    Question information is optional so an existing question can be replaced
    without creating a duplicate question number.
    """

    question_type: InterviewQuestionType | None = None

    question_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
    )

    evaluation_criteria_json: dict[str, Any] | None = None

    student_response: str = Field(
        min_length=1,
        max_length=20000,
    )

    is_follow_up: bool | None = None

    response_duration_seconds: int = Field(
        default=0,
        ge=0,
        le=7200,
    )


class InterviewResponseResponse(BaseModel):
    """Represent one interview question and student response."""

    model_config = ConfigDict(from_attributes=True)

    interview_response_id: int
    interview_session_id: int
    question_number: int
    question_type: str
    question_text: str
    evaluation_criteria_json: dict[str, Any] | None
    student_response: str | None
    response_score: float | None
    feedback: str | None
    strengths_json: list[Any] | dict[str, Any] | None
    improvements_json: list[Any] | dict[str, Any] | None
    is_follow_up: bool
    response_duration_seconds: int
    asked_at: datetime
    answered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InterviewSessionDetailResponse(InterviewSessionResponse):
    """Represent an interview session with all recorded responses."""

    responses: list[InterviewResponseResponse] = Field(
        default_factory=list,
    )