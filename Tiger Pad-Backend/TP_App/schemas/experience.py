"""
Overall function:
This file defines Pydantic schemas for student experience records.

Experiences can include employment, internships, research, volunteer work,
leadership, campus activities, and other professional-development activities.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperienceCreateRequest(BaseModel):
    """Validate a new student experience."""

    experience_type: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Examples: work, internship, research, volunteer, leadership.",
    )
    organization_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
    )
    position_title: str = Field(
        ...,
        min_length=1,
        max_length=150,
    )
    location: str | None = Field(
        default=None,
        max_length=150,
    )
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    is_featured: bool = False

    @field_validator(
        "experience_type",
        "organization_name",
        "position_title",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Trim required text and reject blank values."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("This field cannot be blank.")

        return cleaned_value

    @field_validator("location", "description")
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


class ExperienceUpdateRequest(BaseModel):
    """Validate updates to an existing student experience."""

    experience_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )
    organization_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    position_title: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    location: str | None = Field(
        default=None,
        max_length=150,
    )
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    is_featured: bool | None = None

    @field_validator(
        "experience_type",
        "organization_name",
        "position_title",
    )
    @classmethod
    def validate_optional_required_text(
        cls,
        value: str | None,
    ) -> str | None:
        """Trim optional text values and reject blanks."""

        if value is None:
            return None

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("This field cannot be blank.")

        return cleaned_value

    @field_validator("location", "description")
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


class ExperienceResponse(BaseModel):
    """Return a complete student experience record."""

    model_config = ConfigDict(from_attributes=True)

    experience_id: int
    student_profile_id: int
    experience_type: str
    organization_name: str
    position_title: str
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool
    description: str | None = None
    is_featured: bool
    created_at: datetime
    updated_at: datetime


class ExperienceSummary(BaseModel):
    """Return a compact experience record for profile summaries."""

    model_config = ConfigDict(from_attributes=True)

    experience_id: int
    experience_type: str
    organization_name: str
    position_title: str
    start_date: date
    end_date: date | None = None
    is_current: bool
    is_featured: bool
