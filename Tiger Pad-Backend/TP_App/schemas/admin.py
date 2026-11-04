"""
Overall function:
This file defines request and response schemas for TigerPad administrator
features.

Administrators can manage account status, review safe user summaries, assign
faculty program permissions, and view system counts. Sensitive values such as
password hashes and authentication tokens are never included in administrator
API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from TP_App.schemas.faculty import FacultyAccessLevel


class AdminUserStatusUpdateRequest(BaseModel):
    """Validate an administrator account-status update."""

    is_active: bool = Field(
        description="Whether the user account should be active.",
    )


class AdminUserRoleUpdateRequest(BaseModel):
    """Validate an administrator role update."""

    role_id: int = Field(
        ge=1,
        le=3,
        description="Role identifier: student, faculty, or admin.",
    )


class AdminUserResponse(BaseModel):
    """Represent safe user information for administrator management."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    role_id: int
    role: str
    jsu_email: str
    first_name: str
    last_name: str
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminFacultyAccessCreateRequest(BaseModel):
    """Validate a faculty program-access assignment."""

    faculty_profile_id: int = Field(
        ge=1,
    )

    program_id: int = Field(
        ge=1,
    )

    access_level: FacultyAccessLevel = (
        FacultyAccessLevel.viewer
    )

    expires_at: datetime | None = None


class AdminFacultyAccessUpdateRequest(BaseModel):
    """Validate a faculty program-access update."""

    access_level: FacultyAccessLevel | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class AdminOverviewResponse(BaseModel):
    """Represent safe administrative system counts."""

    total_users: int
    active_users: int
    inactive_users: int
    student_users: int
    faculty_users: int
    administrator_users: int
    total_student_profiles: int
    total_faculty_profiles: int
    total_active_programs: int
    total_active_career_paths: int
    total_active_skills: int


class AdminAuditLogResponse(BaseModel):
    """Represent a safe audit-log record for administrator review."""

    model_config = ConfigDict(from_attributes=True)

    audit_log_id: int
    user_id: int | None
    event_category: str
    action: str
    entity_type: str | None
    entity_id: int | None
    description: str | None
    status: str
    severity_level: str
    request_id: str | None
    ip_address: str | None
    user_agent: str | None
    old_values_json: Any | None
    new_values_json: Any | None
    occurred_at: datetime
    created_at: datetime
