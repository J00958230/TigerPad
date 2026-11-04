"""
Overall function:
This file defines Pydantic schemas for TigerPad user accounts. It validates
student registration, administrator-created accounts, profile name updates,
account status changes, and safe user responses.

Security rules:
- Public registration cannot choose faculty or administrator roles.
- Password hashes are never accepted from or returned to API clients.
- Failed-login counters and lockout values are not exposed normally.
- Extra request fields are rejected.
- Exact JSU email-domain enforcement remains a cybersecurity decision
  for Cell, the Cybersecurity Lead.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from TP_App.schemas.auth import (
    AuthRole,
    AuthSchema,
    _normalize_email,
    _validate_new_password,
    _validate_secret_is_present,
)


StudentRegistrationRole = Literal["student"]
AdministratorManagedRole = Literal["student", "faculty", "admin"]


def _validate_person_name(value: str, field_name: str) -> str:
    """Normalize a person's name and reject unsafe blank values."""

    normalized = " ".join(value.strip().split())

    if not normalized:
        raise ValueError(f"{field_name} cannot be blank.")

    if any(character in normalized for character in "\r\n\t"):
        raise ValueError(f"{field_name} contains invalid whitespace.")

    return normalized


class UserRegistrationRequest(AuthSchema):
    """Public student-registration request."""

    jsu_email: str = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: SecretStr
    confirm_password: SecretStr
    accepted_terms: bool
    role: StudentRegistrationRole = "student"

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize the registration email."""

        return _normalize_email(value)

    @field_validator("first_name")
    @classmethod
    def normalize_first_name(cls, value: str) -> str:
        """Normalize the first name."""

        return _validate_person_name(value, "First name")

    @field_validator("last_name")
    @classmethod
    def normalize_last_name(cls, value: str) -> str:
        """Normalize the last name."""

        return _validate_person_name(value, "Last name")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Apply the configured password policy."""

        return _validate_new_password(value)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, value: SecretStr) -> SecretStr:
        """Require a nonblank password confirmation."""

        return _validate_secret_is_present(value)

    @field_validator("accepted_terms")
    @classmethod
    def require_terms_acceptance(cls, value: bool) -> bool:
        """Require the student to accept TigerPad terms."""

        if not value:
            raise ValueError(
                "TigerPad terms must be accepted before registration."
            )

        return value

    @model_validator(mode="after")
    def passwords_must_match(self) -> "UserRegistrationRequest":
        """Ensure submitted password values match."""

        if (
            self.password.get_secret_value()
            != self.confirm_password.get_secret_value()
        ):
            raise ValueError("Password values must match.")

        return self


class AdminUserCreateRequest(AuthSchema):
    """Account-creation request restricted to administrator routes."""

    jsu_email: str = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: AdministratorManagedRole
    temporary_password: SecretStr
    confirm_temporary_password: SecretStr

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize the managed account email."""

        return _normalize_email(value)

    @field_validator("first_name")
    @classmethod
    def normalize_first_name(cls, value: str) -> str:
        """Normalize the first name."""

        return _validate_person_name(value, "First name")

    @field_validator("last_name")
    @classmethod
    def normalize_last_name(cls, value: str) -> str:
        """Normalize the last name."""

        return _validate_person_name(value, "Last name")

    @field_validator("temporary_password")
    @classmethod
    def validate_temporary_password(cls, value: SecretStr) -> SecretStr:
        """Apply the configured password policy."""

        return _validate_new_password(value)

    @field_validator("confirm_temporary_password")
    @classmethod
    def validate_confirmation(cls, value: SecretStr) -> SecretStr:
        """Require a nonblank password confirmation."""

        return _validate_secret_is_present(value)

    @model_validator(mode="after")
    def temporary_passwords_must_match(
        self,
    ) -> "AdminUserCreateRequest":
        """Ensure temporary password values match."""

        if (
            self.temporary_password.get_secret_value()
            != self.confirm_temporary_password.get_secret_value()
        ):
            raise ValueError("Temporary password values must match.")

        return self


class UserSelfUpdateRequest(AuthSchema):
    """Allowed account-name updates for the authenticated user."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    @field_validator("first_name")
    @classmethod
    def normalize_first_name(cls, value: str | None) -> str | None:
        """Normalize an optional first-name update."""

        if value is None:
            return None

        return _validate_person_name(value, "First name")

    @field_validator("last_name")
    @classmethod
    def normalize_last_name(cls, value: str | None) -> str | None:
        """Normalize an optional last-name update."""

        if value is None:
            return None

        return _validate_person_name(value, "Last name")

    @model_validator(mode="after")
    def require_an_update(self) -> "UserSelfUpdateRequest":
        """Prevent an empty update request."""

        if self.first_name is None and self.last_name is None:
            raise ValueError(
                "At least one account field must be provided for an update."
            )

        return self


class AdminUserUpdateRequest(AuthSchema):
    """Administrator-only account status and role update."""

    role: AuthRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_an_update(self) -> "AdminUserUpdateRequest":
        """Prevent an empty administrator update request."""

        if self.role is None and self.is_active is None:
            raise ValueError(
                "At least one administrative field must be provided."
            )

        return self


class UserResponse(AuthSchema):
    """Safe account information returned to an authenticated user."""

    user_id: int = Field(..., gt=0)
    role: AuthRole
    jsu_email: str = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool
    email_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize response email values."""

        return _normalize_email(value)


class UserSummary(AuthSchema):
    """Minimal safe user information for related records and dashboards."""

    user_id: int = Field(..., gt=0)
    role: AuthRole
    display_name: str = Field(..., min_length=1, max_length=201)


class AdminUserResponse(UserResponse):
    """Safe account information returned from admin endpoints."""

    last_login_at: datetime | None = None


__all__ = [
    "AdminUserCreateRequest",
    "AdminUserResponse",
    "AdminUserUpdateRequest",
    "UserRegistrationRequest",
    "UserResponse",
    "UserSelfUpdateRequest",
    "UserSummary",
]