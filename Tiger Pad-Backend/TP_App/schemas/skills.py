"""
Overall function:
This file defines Pydantic schemas for TigerPad skills, career-path skill
requirements, student skills, and skill-gap information.

The schemas validate user-submitted skill information, preserve compatibility
with the existing schema package, and format skill-related API responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SkillVerificationStatus = Literal[
    "self_reported",
    "pending",
    "verified",
    "rejected",
]

VerificationStatus = SkillVerificationStatus


SkillGapStatus = Literal[
    "open",
    "in_progress",
    "resolved",
    "dismissed",
]


class SkillResponse(BaseModel):
    """Return one skill from the TigerPad skill catalog."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    skill_code: str
    category: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SkillCreateRequest(BaseModel):
    """Validate creation of a catalog skill."""

    name: str = Field(..., min_length=1, max_length=150)
    skill_code: str = Field(..., min_length=1, max_length=40)
    category: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=5000)


class SkillUpdateRequest(BaseModel):
    """Validate updates to a catalog skill."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    skill_code: str | None = Field(default=None, min_length=1, max_length=40)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class StudentSkillCreateRequest(BaseModel):
    """Validate a student's new skill submission."""

    skill_id: int = Field(..., gt=0)
    proficiency_level: int = Field(default=1, ge=1, le=5)
    years_experience: Decimal | None = Field(
        default=None,
        ge=0,
        le=99.9,
        decimal_places=1,
    )
    evidence_description: str | None = Field(
        default=None,
        max_length=500,
    )
    evidence_url: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("evidence_description", "evidence_url")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """Trim optional text and convert blanks to null."""

        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class StudentSkillUpdateRequest(BaseModel):
    """Validate changes to an existing student skill."""

    proficiency_level: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    years_experience: Decimal | None = Field(
        default=None,
        ge=0,
        le=99.9,
        decimal_places=1,
    )
    evidence_description: str | None = Field(
        default=None,
        max_length=500,
    )
    evidence_url: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("evidence_description", "evidence_url")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """Trim optional text and convert blanks to null."""

        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class StudentSkillResponse(BaseModel):
    """Return one skill connected to a student profile."""

    model_config = ConfigDict(from_attributes=True)

    student_skill_id: int
    student_profile_id: int
    skill_id: int
    proficiency_level: int
    years_experience: Decimal | None = None
    verification_status: VerificationStatus
    evidence_description: str | None = None
    evidence_url: str | None = None
    created_at: datetime
    updated_at: datetime


class StudentSkillSummary(BaseModel):
    """Return a compact student skill record."""

    model_config = ConfigDict(from_attributes=True)

    student_skill_id: int
    skill_id: int
    proficiency_level: int
    years_experience: Decimal | None = None
    verification_status: VerificationStatus


class CareerPathSkillCreateRequest(BaseModel):
    """Validate a skill requirement assigned to a career path."""

    career_path_id: int = Field(..., gt=0)
    skill_id: int = Field(..., gt=0)
    importance_level: int = Field(default=3, ge=1, le=5)
    target_proficiency_level: int = Field(default=3, ge=1, le=5)
    is_required: bool = False
    notes: str | None = Field(default=None, max_length=500)


class CareerPathSkillUpdateRequest(BaseModel):
    """Validate updates to a career-path skill requirement."""

    importance_level: int | None = Field(default=None, ge=1, le=5)
    target_proficiency_level: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    is_required: bool | None = None
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class CareerPathSkillResponse(BaseModel):
    """Return one skill requirement for a generalized career path."""

    model_config = ConfigDict(from_attributes=True)

    career_path_skill_id: int
    career_path_id: int
    skill_id: int
    importance_level: int
    target_proficiency_level: int
    is_required: bool
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CareerPathSkillSummary(BaseModel):
    """Return a compact career-path skill requirement."""

    model_config = ConfigDict(from_attributes=True)

    career_path_skill_id: int
    skill_id: int
    importance_level: int
    target_proficiency_level: int
    is_required: bool


class SkillGapResponse(BaseModel):
    """Return one calculated gap between student and target proficiency."""

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
    gap_status: SkillGapStatus
    recommend_action: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SkillGapSummary(BaseModel):
    """Return a compact skill-gap record."""

    model_config = ConfigDict(from_attributes=True)

    skill_gap_id: int
    career_path_skill_id: int
    current_proficiency_level: int
    target_proficiency_level: int
    gap_size: int
    priority_score: Decimal
    gap_status: SkillGapStatus


class SkillCategorySummary(BaseModel):
    """Return a skill category and its number of skills."""

    category: str
    skill_count: int


class SkillSearchRequest(BaseModel):
    """Validate optional skill-catalog search values."""

    search_text: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)