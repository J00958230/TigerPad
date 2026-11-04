"""
Overall function:
This file defines Pydantic schemas for TigerPad academic programs and the
student-program relationships that connect a student to a major, minor,
concentration, certificate, or other approved JSU program.

These schemas support program search, safe program responses, and student
program assignment. They do not allow a client to submit student_profile_id;
the authenticated backend assigns ownership from the JWT user.

Security and data-integrity rules:
- IDs must be positive integers.
- Search text and display values are normalized and length-limited.
- A program cannot be marked as a primary program unless its relationship is
  active.
- Completion dates cannot occur before start dates.
- Extra request fields are rejected through AuthSchema.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from TP_App.schemas.auth import AuthSchema


StudentProgramStatus = Literal["active", "completed", "withdrawn"]


def _normalize_optional_text(
    value: str | None,
    field_name: str,
    max_length: int,
) -> str | None:
    """Normalize optional text and enforce its maximum length."""

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


def _validate_date_order(
    start_date: date | None,
    completion_date: date | None,
) -> None:
    """Ensure completion occurs on or after the start date."""

    if (
        start_date is not None
        and completion_date is not None
        and completion_date < start_date
    ):
        raise ValueError(
            "Completion date cannot be earlier than the start date."
        )


class AcademicProgramSearchRequest(AuthSchema):
    """Filters for searching approved JSU academic programs."""

    search_text: str | None = Field(default=None, max_length=100)
    department_id: int | None = Field(default=None, gt=0)
    program_type: str | None = Field(default=None, max_length=30)
    degree_level: str | None = Field(default=None, max_length=30)
    active_only: bool = True
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)

    @field_validator("search_text")
    @classmethod
    def normalize_search_text(cls, value: str | None) -> str | None:
        """Normalize optional search text."""

        return _normalize_optional_text(value, "Search text", 100)

    @field_validator("program_type")
    @classmethod
    def normalize_program_type(cls, value: str | None) -> str | None:
        """Normalize the optional program-type filter."""

        return _normalize_optional_text(value, "Program type", 30)

    @field_validator("degree_level")
    @classmethod
    def normalize_degree_level(cls, value: str | None) -> str | None:
        """Normalize the optional degree-level filter."""

        return _normalize_optional_text(value, "Degree level", 30)


class AcademicProgramResponse(AuthSchema):
    """Complete academic-program information returned by the API."""

    program_id: int = Field(..., gt=0)
    department_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=150)
    program_code: str = Field(..., min_length=1, max_length=30)
    program_type: str = Field(..., min_length=1, max_length=30)
    degree_level: str = Field(..., min_length=1, max_length=30)
    degree_abbreviation: str | None = Field(default=None, max_length=20)
    description: str | None = None
    catalog_url: str | None = Field(default=None, max_length=500)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AcademicProgramSummary(AuthSchema):
    """Compact academic-program information for student selections."""

    program_id: int = Field(..., gt=0)
    department_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=150)
    program_code: str = Field(..., min_length=1, max_length=30)
    program_type: str = Field(..., min_length=1, max_length=30)
    degree_level: str = Field(..., min_length=1, max_length=30)
    degree_abbreviation: str | None = Field(default=None, max_length=20)


class StudentProgramCreateRequest(AuthSchema):
    """Assign an approved academic program to the current student."""

    program_id: int = Field(..., gt=0)
    is_primary: bool = False
    status: StudentProgramStatus = "active"
    start_date: date | None = None
    completion_date: date | None = None

    @model_validator(mode="after")
    def validate_program_relationship(self) -> "StudentProgramCreateRequest":
        """Validate primary-program and date rules."""

        if self.is_primary and self.status != "active":
            raise ValueError(
                "Only an active academic program can be primary."
            )

        _validate_date_order(
            self.start_date,
            self.completion_date,
        )

        return self


class StudentProgramUpdateRequest(AuthSchema):
    """Update an existing academic-program relationship."""

    is_primary: bool | None = None
    status: StudentProgramStatus | None = None
    start_date: date | None = None
    completion_date: date | None = None

    @model_validator(mode="after")
    def require_an_update(self) -> "StudentProgramUpdateRequest":
        """Prevent an empty update request."""

        if not self.model_dump(exclude_unset=True):
            raise ValueError(
                "At least one academic-program field must be provided."
            )

        _validate_date_order(
            self.start_date,
            self.completion_date,
        )

        return self


class StudentProgramResponse(AuthSchema):
    """Student-program relationship with program display details."""

    student_program_id: int = Field(..., gt=0)
    student_profile_id: int = Field(..., gt=0)
    program_id: int = Field(..., gt=0)
    program_name: str = Field(..., min_length=1, max_length=150)
    program_code: str = Field(..., min_length=1, max_length=30)
    program_type: str = Field(..., min_length=1, max_length=30)
    degree_level: str = Field(..., min_length=1, max_length=30)
    degree_abbreviation: str | None = Field(default=None, max_length=20)
    is_primary: bool
    status: StudentProgramStatus
    start_date: date | None = None
    completion_date: date | None = None
    created_at: datetime
    updated_at: datetime


class StudentProgramSummary(AuthSchema):
    """Compact student-program data for dashboards and recommendations."""

    student_program_id: int = Field(..., gt=0)
    program_id: int = Field(..., gt=0)
    program_name: str = Field(..., min_length=1, max_length=150)
    program_code: str = Field(..., min_length=1, max_length=30)
    program_type: str = Field(..., min_length=1, max_length=30)
    degree_level: str = Field(..., min_length=1, max_length=30)
    degree_abbreviation: str | None = Field(default=None, max_length=20)
    is_primary: bool
    status: StudentProgramStatus


__all__ = [
    "AcademicProgramResponse",
    "AcademicProgramSearchRequest",
    "AcademicProgramSummary",
    "StudentProgramCreateRequest",
    "StudentProgramResponse",
    "StudentProgramStatus",
    "StudentProgramSummary",
    "StudentProgramUpdateRequest",
]