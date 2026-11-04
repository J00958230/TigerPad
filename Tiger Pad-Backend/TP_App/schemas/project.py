"""
Overall function:
This file defines Pydantic schemas for student project records.

Projects allow TigerPad students to showcase classwork, senior projects,
research, personal projects, software projects, community work, and other
portfolio evidence.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreateRequest(BaseModel):
    """Validate a new student project."""

    project_type: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Examples: academic, personal, research, senior_project.",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )
    role_title: str | None = Field(
        default=None,
        max_length=150,
    )
    organization_name: str | None = Field(
        default=None,
        max_length=150,
    )
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    outcome: str | None = Field(
        default=None,
        max_length=5000,
    )
    project_url: str | None = Field(
        default=None,
        max_length=500,
    )
    team_size: int | None = Field(
        default=None,
        ge=1,
        le=10000,
    )
    is_featured: bool = False

    @field_validator("project_type", "title")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Trim required text and reject blank values."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("This field cannot be blank.")

        return cleaned_value

    @field_validator(
        "role_title",
        "organization_name",
        "description",
        "outcome",
        "project_url",
    )
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


class ProjectUpdateRequest(BaseModel):
    """Validate updates to an existing student project."""

    project_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    role_title: str | None = Field(
        default=None,
        max_length=150,
    )
    organization_name: str | None = Field(
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
    outcome: str | None = Field(
        default=None,
        max_length=5000,
    )
    project_url: str | None = Field(
        default=None,
        max_length=500,
    )
    team_size: int | None = Field(
        default=None,
        ge=1,
        le=10000,
    )
    is_featured: bool | None = None

    @field_validator("project_type", "title")
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

    @field_validator(
        "role_title",
        "organization_name",
        "description",
        "outcome",
        "project_url",
    )
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


class ProjectResponse(BaseModel):
    """Return a complete student project record."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int
    student_profile_id: int
    project_type: str
    title: str
    role_title: str | None = None
    organization_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool
    description: str | None = None
    outcome: str | None = None
    project_url: str | None = None
    team_size: int | None = None
    is_featured: bool
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    """Return a compact project record for dashboards and résumés."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int
    project_type: str
    title: str
    role_title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool
    project_url: str | None = None
    is_featured: bool