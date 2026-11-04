"""
Overall function:
This file defines Pydantic schemas for TigerPad's generalized career-path
guidance. It validates career paths, career goals, readiness scores, and
student recommendations.

TigerPad uses generalized career paths to explain what a role does and how a
student can prepare. These schemas do not represent live job advertisements,
employers, salaries, or job-board postings.

Security and data-integrity rules:
- Student ownership is assigned by the authenticated backend user.
- Readiness scores and recommendation priorities are calculated by services.
- Scores remain between 0 and 100.
- Action URLs must use HTTP or HTTPS.
- Extra request fields are rejected.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from TP_App.schemas.auth import AuthSchema


CareerGoalType = Literal["primary", "secondary", "exploration"]

CareerGoalStatus = Literal[
    "active",
    "completed",
    "paused",
    "archived",
]

RecommendationStatus = Literal[
    "active",
    "completed",
    "dismissed",
    "expired",
]

RecommendationSourceType = Literal["rules", "ai", "hybrid"]


def _normalize_text(
    value: str | None,
    field_name: str,
    max_length: int,
) -> str | None:
    """Normalize optional text and enforce a maximum length."""

    if value is None:
        return None

    normalized = " ".join(value.strip().split())

    if not normalized:
        raise ValueError(f"{field_name} cannot be blank.")

    if len(normalized) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed {max_length} characters."
        )

    return normalized


def _validate_url(value: str | None, field_name: str) -> str | None:
    """Accept only absolute HTTP or HTTPS URLs."""

    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be blank.")

    if not normalized.startswith(("http://", "https://")):
        raise ValueError(
            f"{field_name} must begin with http:// or https://."
        )

    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} cannot contain whitespace.")

    return normalized


def _validate_score(value: Decimal | None) -> Decimal | None:
    """Validate a score on the database 0-to-100 scale."""

    if value is None:
        return None

    if value < Decimal("0.00") or value > Decimal("100.00"):
        raise ValueError("Scores must be between 0.00 and 100.00.")

    if abs(value.as_tuple().exponent) > 2:
        raise ValueError(
            "Scores cannot contain more than two decimal places."
        )

    return value.quantize(Decimal("0.01"))


class IndustryResponse(AuthSchema):
    """Industry information used to group generalized career paths."""

    industry_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=150)
    industry_code: str = Field(..., min_length=1, max_length=30)
    description: str | None = None
    is_active: bool


class CareerPathResponse(AuthSchema):
    """Generalized career-path information returned to students."""

    career_path_id: int = Field(..., gt=0)
    industry_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=150)
    career_path_code: str = Field(..., min_length=1, max_length=40)
    description: str | None = None
    typical_education_level: str | None = Field(
        default=None,
        max_length=50,
    )
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CareerPathSummary(AuthSchema):
    """Compact career-path information for dashboards and selections."""

    career_path_id: int = Field(..., gt=0)
    industry_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=150)
    career_path_code: str = Field(..., min_length=1, max_length=40)
    typical_education_level: str | None = Field(
        default=None,
        max_length=50,
    )


class CareerPathSearchRequest(AuthSchema):
    """Filters used to search generalized career paths."""

    search_text: str | None = Field(default=None, max_length=100)
    industry_id: int | None = Field(default=None, gt=0)
    active_only: bool = True
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10000)

    @field_validator("search_text")
    @classmethod
    def normalize_search_text(cls, value: str | None) -> str | None:
        """Normalize optional search text."""

        return _normalize_text(value, "Search text", 100)


class CareerGoalCreateRequest(AuthSchema):
    """Create a career goal for the authenticated student."""

    career_path_id: int = Field(..., gt=0)
    goal_type: CareerGoalType = "primary"
    target_date: date | None = None
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        """Normalize optional career-goal notes."""

        return _normalize_text(value, "Career goal notes", 5000)


class CareerGoalUpdateRequest(AuthSchema):
    """Update an existing student career goal."""

    goal_type: CareerGoalType | None = None
    status: CareerGoalStatus | None = None
    target_date: date | None = None
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        """Normalize optional career-goal notes."""

        return _normalize_text(value, "Career goal notes", 5000)

    @model_validator(mode="after")
    def require_an_update(self) -> "CareerGoalUpdateRequest":
        """Prevent an empty career-goal update request."""

        if not self.model_dump(exclude_unset=True):
            raise ValueError(
                "At least one career-goal field must be provided."
            )

        return self


class CareerGoalResponse(AuthSchema):
    """Career-goal information returned to the student."""

    career_goal_id: int = Field(..., gt=0)
    student_profile_id: int = Field(..., gt=0)
    career_path_id: int = Field(..., gt=0)
    goal_type: CareerGoalType
    status: CareerGoalStatus
    target_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ReadinessScoreResponse(AuthSchema):
    """Calculated readiness scores for a student and career path."""

    readiness_score_id: int = Field(..., gt=0)
    student_profile_id: int = Field(..., gt=0)
    career_path_id: int = Field(..., gt=0)
    resume_analysis_id: int | None = Field(default=None, gt=0)
    overall_score: Decimal = Field(..., ge=0, le=100)
    academic_score: Decimal = Field(..., ge=0, le=100)
    skill_score: Decimal = Field(..., ge=0, le=100)
    experience_score: Decimal = Field(..., ge=0, le=100)
    project_score: Decimal = Field(..., ge=0, le=100)
    certification_score: Decimal = Field(..., ge=0, le=100)
    resume_score: Decimal = Field(..., ge=0, le=100)
    calculation_version: str = Field(..., min_length=1, max_length=30)
    weights_json: dict[str, Any]
    score_details_json: dict[str, Any] | list[Any] | None = None
    is_current: bool
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "overall_score",
        "academic_score",
        "skill_score",
        "experience_score",
        "project_score",
        "certification_score",
        "resume_score",
    )
    @classmethod
    def validate_score(cls, value: Decimal) -> Decimal:
        """Validate each readiness score."""

        validated = _validate_score(value)

        if validated is None:
            raise ValueError("Readiness score cannot be null.")

        return validated


class RecommendationResponse(AuthSchema):
    """A safe, actionable TigerPad recommendation."""

    recommendation_id: int = Field(..., gt=0)
    student_profile_id: int = Field(..., gt=0)
    career_path_id: int | None = Field(default=None, gt=0)
    readiness_score_id: int | None = Field(default=None, gt=0)
    skill_gap_id: int | None = Field(default=None, gt=0)
    recommendation_type: str = Field(
        ...,
        min_length=1,
        max_length=40,
    )
    title: str = Field(..., min_length=1, max_length=200)
    description: str
    action_text: str | None = Field(default=None, max_length=500)
    action_url: str | None = Field(default=None, max_length=500)
    priority_level: int = Field(..., ge=1, le=5)
    source_type: RecommendationSourceType
    status: RecommendationStatus
    due_date: date | None = None
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None
    expired_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("action_url")
    @classmethod
    def validate_action_url(cls, value: str | None) -> str | None:
        """Validate an optional recommendation URL."""

        return _validate_url(value, "Action URL")


class RecommendationUpdateRequest(AuthSchema):
    """Student action for an existing recommendation."""

    status: Literal["completed", "dismissed"]


__all__ = [
    "CareerGoalCreateRequest",
    "CareerGoalResponse",
    "CareerGoalStatus",
    "CareerGoalType",
    "CareerGoalUpdateRequest",
    "CareerPathResponse",
    "CareerPathSearchRequest",
    "CareerPathSummary",
    "IndustryResponse",
    "ReadinessScoreResponse",
    "RecommendationResponse",
    "RecommendationSourceType",
    "RecommendationStatus",
    "RecommendationUpdateRequest",
]