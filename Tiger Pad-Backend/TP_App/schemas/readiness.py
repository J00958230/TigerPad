"""
Overall function:
This file defines Pydantic schemas for TigerPad readiness scores and skill
gaps.

Readiness scores summarize how prepared a student is for a selected
generalized career path. Skill gaps identify specific abilities that need
additional development.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReadinessCalculationRequest(BaseModel):
    """Validate a readiness-score calculation request."""

    career_path_id: int = Field(..., gt=0)


class SkillGapResponse(BaseModel):
    """Return one skill gap for a readiness calculation."""

    model_config = ConfigDict(from_attributes=True)

    skill_gap_id: int
    readiness_score_id: int
    career_path_skill_id: int
    student_skill_id: int | None = None
    current_proficiency_level: int
    target_proficiency_level: int
    importance_level: int
    gap_size: int
    priority_score: Decimal
    gap_status: str
    recommend_action: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReadinessScoreResponse(BaseModel):
    """Return one readiness score."""

    model_config = ConfigDict(from_attributes=True)

    readiness_score_id: int
    student_profile_id: int
    career_path_id: int
    resume_analysis_id: int | None = None
    overall_score: Decimal
    academic_score: Decimal
    skill_score: Decimal
    experience_score: Decimal
    project_score: Decimal
    certification_score: Decimal
    resume_score: Decimal
    calculation_version: str
    weights_json: dict[str, Any]
    score_details_json: dict[str, Any] | None = None
    profile_snapshot_hash: str
    is_current: bool
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime


class ReadinessScoreDetailResponse(ReadinessScoreResponse):
    """Return a readiness score together with its skill gaps."""

    skill_gaps: list[SkillGapResponse] = []


class ReadinessDashboardResponse(BaseModel):
    """Return a compact readiness dashboard response."""

    readiness_score: ReadinessScoreResponse
    skill_gaps: list[SkillGapResponse]