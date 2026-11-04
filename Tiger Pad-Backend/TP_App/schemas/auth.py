"""
Overall function:
This file defines Pydantic schemas for TigerPad authentication.

It validates registration, login, logout, token refresh, password changes,
password resets, email verification, token responses, and safe user data.

Security rules:
- Passwords are accepted only in request bodies.
- Passwords and token values are never returned.
- Password hashes are never exposed.
- Extra request fields are rejected.
- Passwords follow the configured minimum length.
- New public registrations always create student accounts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from TP_App.config import settings


AuthRole = Literal["student", "faculty", "admin"]


class AuthSchema(BaseModel):
    """Shared validation settings for authentication schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


def _normalize_email(value: str) -> str:
    """Normalize and validate a JSU email value."""

    normalized = value.strip().lower()

    if len(normalized) > 255:
        raise ValueError(
            "Email address cannot exceed 255 characters."
        )

    if normalized.count("@") != 1:
        raise ValueError("Enter a valid email address.")

    local_part, domain = normalized.split("@")

    if not local_part or not domain or "." not in domain:
        raise ValueError("Enter a valid email address.")

    return normalized


def _validate_name(value: str) -> str:
    """Validate a person's first or last name."""

    normalized = value.strip()

    if not normalized:
        raise ValueError("Name cannot be blank.")

    if any(ord(character) < 32 for character in normalized):
        raise ValueError("Name contains invalid control characters.")

    return normalized


def _validate_secret_is_present(value: SecretStr) -> SecretStr:
    """Reject blank secrets without exposing their contents."""

    secret_value = value.get_secret_value()

    if not secret_value or not secret_value.strip():
        raise ValueError("This value cannot be blank.")

    return value


def _validate_new_password(value: SecretStr) -> SecretStr:
    """Validate a new password against TigerPad's password policy."""

    value = _validate_secret_is_present(value)
    password = value.get_secret_value()

    if len(password) < settings.MINIMUM_PASSWORD_LENGTH:
        raise ValueError(
            "Password does not meet the configured minimum length."
        )

    if any(character.isspace() for character in password):
        raise ValueError(
            "Password cannot contain whitespace characters."
        )

    return value


class RegisterRequest(AuthSchema):
    """Information required to create a new TigerPad student account."""

    jsu_email: str = Field(..., max_length=255)
    password: SecretStr
    confirm_password: SecretStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize the registration email."""

        return _normalize_email(value)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, value: str) -> str:
        """Validate registration names."""

        return _validate_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Validate the requested password."""

        return _validate_new_password(value)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """Require a nonblank password confirmation."""

        return _validate_secret_is_present(value)

    @model_validator(mode="after")
    def passwords_must_match(self) -> "RegisterRequest":
        """Ensure the password and confirmation match."""

        if (
            self.password.get_secret_value()
            != self.confirm_password.get_secret_value()
        ):
            raise ValueError("Password values must match.")

        return self


class LoginRequest(AuthSchema):
    """Credentials submitted when a user signs in."""

    jsu_email: str = Field(..., max_length=255)
    password: SecretStr
    remember_me: bool = False

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize the login email."""

        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Require a nonblank password."""

        return _validate_secret_is_present(value)


class RefreshTokenRequest(AuthSchema):
    """Request a new access token using a refresh token."""

    refresh_token: SecretStr

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, value: SecretStr) -> SecretStr:
        """Reject an empty refresh token."""

        return _validate_secret_is_present(value)


class LogoutRequest(AuthSchema):
    """Options submitted when a user signs out."""

    all_sessions: bool = False
    refresh_token: SecretStr | None = None

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        """Validate an optional refresh token."""

        if value is None:
            return None

        return _validate_secret_is_present(value)


class PasswordChangeRequest(AuthSchema):
    """Change a password for an authenticated user."""

    current_password: SecretStr
    new_password: SecretStr
    confirm_password: SecretStr

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, value: SecretStr) -> SecretStr:
        """Require the current password."""

        return _validate_secret_is_present(value)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: SecretStr) -> SecretStr:
        """Validate the replacement password."""

        return _validate_new_password(value)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """Require a nonblank password confirmation."""

        return _validate_secret_is_present(value)

    @model_validator(mode="after")
    def passwords_must_match(self) -> "PasswordChangeRequest":
        """Ensure the replacement passwords match."""

        if (
            self.new_password.get_secret_value()
            != self.confirm_password.get_secret_value()
        ):
            raise ValueError("New password values must match.")

        if (
            self.current_password.get_secret_value()
            == self.new_password.get_secret_value()
        ):
            raise ValueError(
                "New password must be different from the current password."
            )

        return self


class PasswordResetRequest(AuthSchema):
    """Request a password-reset message."""

    jsu_email: str = Field(..., max_length=255)

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize the password-reset email."""

        return _normalize_email(value)


class PasswordResetConfirm(AuthSchema):
    """Submit a reset token and replacement password."""

    reset_token: SecretStr
    new_password: SecretStr
    confirm_password: SecretStr

    @field_validator("reset_token")
    @classmethod
    def validate_reset_token(cls, value: SecretStr) -> SecretStr:
        """Reject an empty reset token."""

        return _validate_secret_is_present(value)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: SecretStr) -> SecretStr:
        """Validate the replacement password."""

        return _validate_new_password(value)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """Require a nonblank confirmation."""

        return _validate_secret_is_present(value)

    @model_validator(mode="after")
    def passwords_must_match(self) -> "PasswordResetConfirm":
        """Ensure the replacement passwords match."""

        if (
            self.new_password.get_secret_value()
            != self.confirm_password.get_secret_value()
        ):
            raise ValueError("New password values must match.")

        return self


class EmailVerificationRequest(AuthSchema):
    """Submit an email-verification token."""

    verification_token: SecretStr

    @field_validator("verification_token")
    @classmethod
    def validate_verification_token(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """Reject an empty verification token."""

        return _validate_secret_is_present(value)


class AuthenticatedUser(AuthSchema):
    """Safe user information returned after authentication."""

    user_id: int = Field(..., gt=0)
    role: AuthRole
    jsu_email: str = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    email_verified_at: datetime | None = None

    @field_validator("jsu_email")
    @classmethod
    def normalize_jsu_email(cls, value: str) -> str:
        """Normalize the response email."""

        return _normalize_email(value)


class TokenResponse(AuthSchema):
    """Tokens returned after successful authentication."""

    access_token: str = Field(..., min_length=1)
    refresh_token: str | None = Field(
        default=None,
        min_length=1,
    )
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(..., gt=0)


class LoginResponse(AuthSchema):
    """Successful login response returned to the frontend."""

    success: bool = True
    message: str = "Login successful."
    tokens: TokenResponse
    user: AuthenticatedUser


class AuthMessageResponse(AuthSchema):
    """Safe response for actions without token data."""

    success: bool = True
    message: str = Field(..., min_length=1, max_length=500)


class AccessTokenClaims(AuthSchema):
    """Internal claims used by the JWT service."""

    subject: str = Field(..., min_length=1, max_length=255)
    user_id: int = Field(..., gt=0)
    role: AuthRole
    token_type: Literal["access", "refresh"]
    issued_at: int = Field(..., gt=0)
    expires_at: int = Field(..., gt=0)
    token_id: str = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def expiration_must_follow_issue(self) -> "AccessTokenClaims":
        """Ensure expiration follows token issuance."""

        if self.expires_at <= self.issued_at:
            raise ValueError(
                "Token expiration must be later than token issuance."
            )

        return self


__all__ = [
    "AccessTokenClaims",
    "AuthMessageResponse",
    "AuthenticatedUser",
    "EmailVerificationRequest",
    "LoginRequest",
    "LoginResponse",
    "LogoutRequest",
    "PasswordChangeRequest",
    "PasswordResetConfirm",
    "PasswordResetRequest",
    "RefreshTokenRequest",
    "RegisterRequest",
    "TokenResponse",
]