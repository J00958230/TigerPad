"""
Overall function:
This file defines Pydantic schemas for student certifications and credentials.

TigerPad can store professional certifications, licenses, certificates,
digital badges, and other credentials that support a student's career path.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CertificationCreateRequest(BaseModel):
    """Validate a new student certification."""

    credential_type: str = Field(
        default="certification",
        min_length=1,
        max_length=30,
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )
    issuing_organization: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )
    credential_id: str | None = Field(
        default=None,
        max_length=150,
    )
    credential_url: str | None = Field(
        default=None,
        max_length=500,
    )
    issue_date: date | None = None
    expiration_date: date | None = None
    does_not_expire: bool = False
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    is_featured: bool = False

    @field_validator(
        "credential_type",
        "name",
        "issuing_organization",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Trim required text and reject blank values."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("This field cannot be blank.")

        return cleaned_value

    @field_validator(
        "credential_id",
        "credential_url",
        "description",
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


class CertificationUpdateRequest(BaseModel):
    """Validate updates to an existing certification."""

    credential_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    issuing_organization: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    credential_id: str | None = Field(
        default=None,
        max_length=150,
    )
    credential_url: str | None = Field(
        default=None,
        max_length=500,
    )
    issue_date: date | None = None
    expiration_date: date | None = None
    does_not_expire: bool | None = None
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    is_featured: bool | None = None

    @field_validator(
        "credential_type",
        "name",
        "issuing_organization",
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

    @field_validator(
        "credential_id",
        "credential_url",
        "description",
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


class CertificationResponse(BaseModel):
    """Return a complete student certification record."""

    model_config = ConfigDict(from_attributes=True)

    certification_id: int
    student_profile_id: int
    credential_type: str
    name: str
    issuing_organization: str
    credential_id: str | None = None
    credential_url: str | None = None
    issue_date: date | None = None
    expiration_date: date | None = None
    does_not_expire: bool
    description: str | None = None
    is_featured: bool
    created_at: datetime
    updated_at: datetime


class CertificationSummary(BaseModel):
    """Return a compact certification for dashboards and résumés."""

    model_config = ConfigDict(from_attributes=True)

    certification_id: int
    credential_type: str
    name: str
    issuing_organization: str
    issue_date: date | None = None
    expiration_date: date | None = None
    does_not_expire: bool
    is_featured: bool