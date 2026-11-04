"""
Overall function:
This file defines Pydantic schemas for TigerPad student profiles. It validates
academic information, professional profile content, GPA values, profile
visibility, and safe profile responses.

Security and data-integrity rules:
- The authenticated user's ID is assigned by the backend.
- Profile completion is calculated by the service layer.
- GPA values must remain between 0.00 and 4.00.
- External profile links must use HTTP or HTTPS.
- Extra request fields are rejected.

The student's major and academic program relationships are stored through the
student_programs table and will be handled by their own schemas.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from TP_App.schemas.auth import AuthSchema


ProfileVisibility = Literal["private", "campus", "public"]


def _normalize_optional_text(
    value: str | None,
    field_name: str,
    max_length: int,
) -> str | None:
    """Normalize optional text and enforce its length."""

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


def _normalize_long_text(
    value: str | None,
    field_name: str,
    max_length: int,
) -> str | None:
    """Normalize biography text while preserving meaningful lines."""

    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be blank.")

    if len(normalized) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed {max_length} characters."
        )

    return normalized


def _validate_profile_url(
    value: str | None,
    field_name: str,
) -> str | None:
    """Accept only absolute HTTP or HTTPS profile URLs."""

    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be blank.")

    if not normalized.startswith(("https://", "http://")):
        raise ValueError(
            f"{field_name} must begin with http:// or https://."
        )

    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} cannot contain whitespace.")

    return normalized


def _validate_gpa(value: Decimal | None) -> Decimal | None:
    """Validate GPA using the database DECIMAL(3,2) range."""

    if value is None:
        return None

    if value < Decimal("0.00") or value > Decimal("4.00"):
        raise ValueError("GPA must be between 0.00 and 4.00.")

    decimal_places = abs(value.as_tuple().exponent)

    if decimal_places > 2:
        raise ValueError(
            "GPA cannot contain more than two decimal places."
        )

    return value.quantize(Decimal("0.01"))


class StudentProfileCreateRequest(AuthSchema):
    """Fields a student may provide when creating a profile."""

    preferred_name: str | None = Field(default=None, max_length=100)
    academic_level: str | None = Field(default=None, max_length=30)
    expected_graduation_date: date | None = None
    gpa: Decimal | None = Field(default=None, ge=0, le=4)
    professional_headline: str | None = Field(
        default=None,
        max_length=255,
    )
    bio: str | None = None
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    profile_visibility: ProfileVisibility = "private"

    @field_validator("preferred_name")
    @classmethod
    def normalize_preferred_name(cls, value: str | None) -> str | None:
        """Normalize the preferred name."""

        return _normalize_optional_text(value, "Preferred name", 100)

    @field_validator("academic_level")
    @classmethod
    def normalize_academic_level(cls, value: str | None) -> str | None:
        """Normalize academic-level text."""

        return _normalize_optional_text(value, "Academic level", 30)

    @field_validator("professional_headline")
    @classmethod
    def normalize_headline(cls, value: str | None) -> str | None:
        """Normalize the professional headline."""

        return _normalize_optional_text(
            value,
            "Professional headline",
            255,
        )

    @field_validator("bio")
    @classmethod
    def normalize_bio(cls, value: str | None) -> str | None:
        """Normalize the profile biography."""

        return _normalize_long_text(value, "Bio", 10000)

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        """Validate an optional LinkedIn URL."""

        return _validate_profile_url(value, "LinkedIn URL")

    @field_validator("portfolio_url")
    @classmethod
    def validate_portfolio_url(cls, value: str | None) -> str | None:
        """Validate an optional portfolio URL."""

        return _validate_profile_url(value, "Portfolio URL")

    @field_validator("gpa")
    @classmethod
    def validate_gpa(cls, value: Decimal | None) -> Decimal | None:
        """Validate GPA range and precision."""

        return _validate_gpa(value)


class StudentProfileUpdateRequest(StudentProfileCreateRequest):
    """Fields a student may update on an existing profile."""

    @model_validator(mode="after")
    def require_an_update(self) -> "StudentProfileUpdateRequest":
        """Prevent an empty profile update request."""

        values = self.model_dump(exclude_unset=True)

        if not values:
            raise ValueError(
                "At least one profile field must be provided for an update."
            )

        return self


class StudentProfileResponse(AuthSchema):
    """Complete safe student-profile response."""

    student_profile_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    preferred_name: str | None = None
    academic_level: str | None = None
    expected_graduation_date: date | None = None
    gpa: Decimal | None = Field(default=None, ge=0, le=4)
    professional_headline: str | None = None
    bio: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    profile_visibility: ProfileVisibility
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("gpa")
    @classmethod
    def validate_response_gpa(cls, value: Decimal | None) -> Decimal | None:
        """Ensure database GPA values remain valid in responses."""

        return _validate_gpa(value)


class StudentProfileSummary(AuthSchema):
    """Compact profile information for dashboards and navigation."""

    student_profile_id: int = Field(..., gt=0)
    preferred_name: str | None = None
    academic_level: str | None = None
    professional_headline: str | None = None
    profile_visibility: ProfileVisibility
    is_profile_complete: bool


__all__ = [
    "ProfileVisibility",
    "StudentProfileCreateRequest",
    "StudentProfileResponse",
    "StudentProfileSummary",
    "StudentProfileUpdateRequest",
]