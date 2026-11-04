"""
Overall function:
This file defines request and response schemas for the TigerPad resource
catalog.

Resources may include JSU career services, résumé support, interview
workshops, mentoring, internships, graduate-school preparation, community
programs, and other career-readiness opportunities for students from every
academic discipline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResourceCreateRequest(BaseModel):
    """Validate creation of a TigerPad resource."""

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    resource_type: str = Field(
        min_length=1,
        max_length=40,
    )

    description: str = Field(
        min_length=1,
        max_length=10000,
    )

    provider_name: str | None = Field(
        default=None,
        max_length=200,
    )

    resource_url: str | None = Field(
        default=None,
        max_length=500,
    )

    location: str | None = Field(
        default=None,
        max_length=200,
    )

    contact_email: str | None = Field(
        default=None,
        max_length=255,
    )

    delivery_method: str = Field(
        default="online",
        min_length=1,
        max_length=20,
    )

    audience_type: str = Field(
        default="all_students",
        min_length=1,
        max_length=30,
    )

    eligibility_notes: str | None = Field(
        default=None,
        max_length=10000,
    )

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    is_jsu_resource: bool = True
    is_active: bool = True


class ResourceUpdateRequest(BaseModel):
    """Validate updates to a TigerPad resource."""

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    resource_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=40,
    )

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
    )

    provider_name: str | None = Field(
        default=None,
        max_length=200,
    )

    resource_url: str | None = Field(
        default=None,
        max_length=500,
    )

    location: str | None = Field(
        default=None,
        max_length=200,
    )

    contact_email: str | None = Field(
        default=None,
        max_length=255,
    )

    delivery_method: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    audience_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    eligibility_notes: str | None = Field(
        default=None,
        max_length=10000,
    )

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    is_jsu_resource: bool | None = None
    is_active: bool | None = None


class ResourceProgramAttachRequest(BaseModel):
    """Validate connecting a resource to an academic program."""

    program_id: int = Field(
        ge=1,
    )

    relevance_level: str = Field(
        default="related",
        min_length=1,
        max_length=20,
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
    )


class ResourceResponse(BaseModel):
    """Represent a resource returned by the TigerPad API."""

    model_config = ConfigDict(from_attributes=True)

    resource_id: int
    title: str
    resource_type: str
    description: str
    provider_name: str | None
    resource_url: str | None
    location: str | None
    contact_email: str | None
    delivery_method: str
    audience_type: str
    eligibility_notes: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    is_jsu_resource: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceProgramResponse(BaseModel):
    """Represent a resource-to-program connection."""

    model_config = ConfigDict(from_attributes=True)

    resource_program_id: int
    resource_id: int
    program_id: int
    relevance_level: str
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceDetailResponse(ResourceResponse):
    """Represent a resource with its connected academic programs."""

    programs: list[ResourceProgramResponse] = Field(
        default_factory=list,
    )