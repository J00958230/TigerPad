"""
Overall function:
This file defines shared Pydantic schemas used by TigerPad API endpoints.
It standardizes pagination, success messages, errors, health responses, and
public application information returned to the frontend.

Security and consistency rules:
- API responses use predictable field names and types.
- Extra fields are rejected to reduce accidental data exposure.
- Internal exception details are not required in public error responses.
- Request identifiers can be returned safely for support and audit tracing.
- Pagination values are bounded to protect database and API performance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


DataT = TypeVar("DataT")


class TigerPadSchema(BaseModel):
    """Base configuration shared by common TigerPad schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class PaginationRequest(TigerPadSchema):
    """Safe pagination parameters for list endpoints."""

    limit: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Maximum number of records to return.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Number of records to skip before returning results.",
    )


class PaginationMetadata(TigerPadSchema):
    """Pagination information returned with a list response."""

    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=100)
    offset: int = Field(..., ge=0)
    has_more: bool


class PaginatedResponse(TigerPadSchema, Generic[DataT]):
    """Standard response wrapper for a paginated collection."""

    success: bool = True
    items: list[DataT]
    pagination: PaginationMetadata


class APIMessageResponse(TigerPadSchema):
    """Standard response for a successful action without a data payload."""

    success: bool = True
    message: str = Field(..., min_length=1, max_length=500)
    request_id: str | None = Field(default=None, max_length=36)


class APIErrorResponse(TigerPadSchema):
    """Safe public error response for failed API requests."""

    success: bool = False
    message: str = Field(..., min_length=1, max_length=500)
    error_code: str = Field(..., min_length=1, max_length=80)
    request_id: str | None = Field(default=None, max_length=36)
    details: dict[str, Any] | None = None


class ValidationErrorItem(TigerPadSchema):
    """One user-facing validation error returned by an API endpoint."""

    field: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=500)
    code: str | None = Field(default=None, max_length=80)


class ValidationErrorResponse(APIErrorResponse):
    """Structured validation-error response for invalid input."""

    error_code: str = "VALIDATION_ERROR"
    errors: list[ValidationErrorItem] = Field(default_factory=list)


class HealthServiceStatus(TigerPadSchema):
    """Availability status for one TigerPad backend service."""

    api: Literal["available", "unavailable"]
    database: Literal["available", "pending", "unavailable"]
    groq: Literal["configured", "pending", "unavailable"]
    authentication: Literal["available", "pending", "unavailable"]


class HealthResponse(TigerPadSchema):
    """Response returned by the public TigerPad health endpoint."""

    success: bool = True
    application: str = Field(..., min_length=1, max_length=150)
    status: Literal["healthy", "degraded", "unavailable"]
    services: HealthServiceStatus
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ApplicationInformationResponse(TigerPadSchema):
    """Public, non-secret information about the TigerPad application."""

    name: str = Field(..., min_length=1, max_length=150)
    version: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=500)
    environment: Literal[
        "development",
        "testing",
        "staging",
        "production",
    ]
    api_prefix: str = Field(..., min_length=1, max_length=100)
    deployment_platform: str = Field(..., min_length=1, max_length=100)
    ai_features_enabled: bool


class TimestampResponse(TigerPadSchema):
    """Reusable timestamp response for service-status endpoints."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


__all__ = [
    "APIErrorResponse",
    "APIMessageResponse",
    "ApplicationInformationResponse",
    "DataT",
    "HealthResponse",
    "HealthServiceStatus",
    "PaginatedResponse",
    "PaginationMetadata",
    "PaginationRequest",
    "TigerPadSchema",
    "TimestampResponse",
    "ValidationErrorItem",
    "ValidationErrorResponse",
]