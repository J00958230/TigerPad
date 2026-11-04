"""
Overall function:
This file defines Pydantic schemas for TigerPad resumes and resume analysis.
It validates resume metadata, generated-resume requests, upload information,
security scan results, career alignment, career-match suggestions, and
analysis scores.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from TP_App.config import settings
from TP_App.schemas.auth import AuthSchema


ResumeType = Literal[
    "general",
    "career_targeted",
    "academic",
    "internship",
    "graduate_school",
]

ResumeSourceType = Literal[
    "uploaded",
    "generated",
]

AnalysisMethod = Literal[
    "rules",
    "ai",
    "hybrid",
]

ResumeScanStatus = Literal[
    "not_required",
    "pending",
    "clean",
    "quarantined",
    "failed",
]

AnalysisStatus = Literal[
    "pending",
    "processing",
    "completed",
    "failed",
]


def _normalize_title(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.strip().split())

    if not normalized:
        raise ValueError(
            "Resume title cannot be blank."
        )

    return normalized


def _validate_sha256(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()

    if len(normalized) != 64:
        raise ValueError(
            "SHA-256 hashes must contain 64 hexadecimal characters."
        )

    if any(
        character not in "0123456789abcdef"
        for character in normalized
    ):
        raise ValueError(
            "SHA-256 hash contains invalid characters."
        )

    return normalized


def _normalize_extension(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()

    if not normalized.startswith("."):
        normalized = f".{normalized}"

    if normalized not in settings.get_allowed_resume_extensions():
        raise ValueError(
            "Resume file type is not allowed by application settings."
        )

    return normalized


def _validate_mime_type(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()

    allowed_mime_types = {
        "application/pdf",
        (
            "application/"
            "vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    }

    if normalized not in allowed_mime_types:
        raise ValueError(
            "Resume MIME type is not supported."
        )

    return normalized


def _validate_score(
    value: Decimal | None,
) -> Decimal | None:
    if value is None:
        return None

    if value < Decimal("0.00") or value > Decimal("100.00"):
        raise ValueError(
            "Scores must be between 0.00 and 100.00."
        )

    if abs(value.as_tuple().exponent) > 2:
        raise ValueError(
            "Scores cannot contain more than two decimal places."
        )

    return value.quantize(Decimal("0.01"))


class ResumeCreateRequest(AuthSchema):
    title: str = Field(
        ...,
        min_length=1,
        max_length=150,
    )
    career_path_id: int | None = Field(
        default=None,
        gt=0,
    )
    resume_type: ResumeType = "general"
    template_name: str | None = Field(
        default=None,
        max_length=100,
    )
    content_json: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = _normalize_title(value)

        if normalized is None:
            raise ValueError(
                "Resume title is required."
            )

        return normalized

    @field_validator("template_name")
    @classmethod
    def normalize_template_name(
        cls,
        value: str | None,
    ) -> str | None:
        return _normalize_title(value)


class ResumeUpdateRequest(AuthSchema):
    title: str | None = Field(
        default=None,
        max_length=150,
    )
    career_path_id: int | None = Field(
        default=None,
        gt=0,
    )
    resume_type: ResumeType | None = None
    template_name: str | None = Field(
        default=None,
        max_length=100,
    )
    content_json: dict[str, Any] | None = None
    is_primary: bool | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(
        cls,
        value: str | None,
    ) -> str | None:
        return _normalize_title(value)

    @field_validator("template_name")
    @classmethod
    def normalize_template_name(
        cls,
        value: str | None,
    ) -> str | None:
        return _normalize_title(value)

    @model_validator(mode="after")
    def require_an_update(self) -> "ResumeUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError(
                "At least one resume field must be provided for an update."
            )

        return self


class ResumeFileMetadata(AuthSchema):
    original_file_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    file_extension: str
    mime_type: str
    file_size_bytes: int = Field(
        ...,
        ge=1,
        le=settings.max_upload_size_bytes,
    )
    sha256_hash: str
    scan_status: ResumeScanStatus = "pending"

    @field_validator("original_file_name")
    @classmethod
    def validate_original_file_name(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Original file name cannot be blank."
            )

        if any(
            character in normalized
            for character in "/\\\r\n\t"
        ):
            raise ValueError(
                "Original file name cannot contain a path."
            )

        return normalized

    @field_validator("file_extension")
    @classmethod
    def validate_file_extension(
        cls,
        value: str,
    ) -> str:
        normalized = _normalize_extension(value)

        if normalized is None:
            raise ValueError(
                "Resume file extension is required."
            )

        return normalized

    @field_validator("mime_type")
    @classmethod
    def validate_file_mime_type(
        cls,
        value: str,
    ) -> str:
        normalized = _validate_mime_type(value)

        if normalized is None:
            raise ValueError(
                "Resume MIME type is required."
            )

        return normalized

    @field_validator("sha256_hash")
    @classmethod
    def validate_file_hash(
        cls,
        value: str,
    ) -> str:
        normalized = _validate_sha256(value)

        if normalized is None:
            raise ValueError(
                "Resume SHA-256 hash is required."
            )

        return normalized

    @model_validator(mode="after")
    def extension_must_match_mime_type(
        self,
    ) -> "ResumeFileMetadata":
        expected_mime_types = {
            ".pdf": "application/pdf",
            ".docx": (
                "application/"
                "vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        }

        expected_mime = expected_mime_types.get(
            self.file_extension
        )

        if expected_mime != self.mime_type:
            raise ValueError(
                "Resume extension and MIME type do not match."
            )

        return self


class ResumeResponse(AuthSchema):
    resume_id: int = Field(..., gt=0)
    student_profile_id: int = Field(..., gt=0)
    career_path_id: int | None = Field(
        default=None,
        gt=0,
    )
    title: str
    resume_type: ResumeType
    source_type: ResumeSourceType
    template_name: str | None = None
    content_json: dict[str, Any] | None = None
    original_file_name: str | None = None
    file_extension: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = Field(
        default=None,
        ge=1,
    )
    scan_status: ResumeScanStatus
    version_number: int = Field(
        ...,
        ge=1,
    )
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("file_extension")
    @classmethod
    def validate_response_extension(
        cls,
        value: str | None,
    ) -> str | None:
        return _normalize_extension(value)

    @field_validator("mime_type")
    @classmethod
    def validate_response_mime_type(
        cls,
        value: str | None,
    ) -> str | None:
        return _validate_mime_type(value)


class ResumeAnalysisRequest(AuthSchema):
    career_path_id: int | None = Field(
        default=None,
        gt=0,
    )
    analysis_method: AnalysisMethod = "hybrid"


class CareerMatchRequest(AuthSchema):
    analysis_method: AnalysisMethod = "hybrid"
    limit: int = Field(
        default=3,
        ge=3,
        le=5,
    )


class CareerMatchSelectionRequest(AuthSchema):
    career_path_id: int = Field(
        ...,
        gt=0,
    )


class CareerMatchResponse(AuthSchema):
    career_path_id: int = Field(
        ...,
        gt=0,
    )
    career_path_code: str = Field(
        ...,
        min_length=1,
        max_length=40,
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
    )
    primary_focus: str = Field(
        ...,
        min_length=1,
    )
    typical_education_level: str | None = None
    confidence_score: Decimal = Field(
        ...,
        ge=0,
        le=100,
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(
        cls,
        value: Decimal,
    ) -> Decimal:
        normalized = _validate_score(value)

        if normalized is None:
            raise ValueError(
                "Career-match confidence is required."
            )

        return normalized


class CareerMatchSelectionResponse(AuthSchema):
    resume_id: int = Field(
        ...,
        gt=0,
    )
    career_path_id: int = Field(
        ...,
        gt=0,
    )
    career_path_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
    )
    message: str = Field(
        ...,
        min_length=1,
    )


class ResumeAnalysisResponse(AuthSchema):
    resume_analysis_id: int = Field(
        ...,
        gt=0,
    )
    resume_id: int = Field(
        ...,
        gt=0,
    )
    career_path_id: int | None = Field(
        default=None,
        gt=0,
    )
    analysis_status: AnalysisStatus
    analysis_method: AnalysisMethod
    overall_score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    content_score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    format_score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    impact_score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    career_alignment_score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    summary: str | None = None
    strengths_json: list[Any] | dict[str, Any] | None = None
    improvements_json: list[Any] | dict[str, Any] | None = None
    section_feedback_json: list[Any] | dict[str, Any] | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "overall_score",
        "content_score",
        "format_score",
        "impact_score",
        "career_alignment_score",
    )
    @classmethod
    def validate_analysis_score(
        cls,
        value: Decimal | None,
    ) -> Decimal | None:
        return _validate_score(value)


__all__ = [
    "AnalysisMethod",
    "AnalysisStatus",
    "CareerMatchRequest",
    "CareerMatchResponse",
    "CareerMatchSelectionRequest",
    "CareerMatchSelectionResponse",
    "ResumeAnalysisRequest",
    "ResumeAnalysisResponse",
    "ResumeCreateRequest",
    "ResumeFileMetadata",
    "ResumeResponse",
    "ResumeScanStatus",
    "ResumeSourceType",
    "ResumeType",
    "ResumeUpdateRequest",
]