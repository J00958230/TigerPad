
"""
Overall function:
This file creates and validates TigerPad authentication tokens.

JWT access tokens are short-lived and contain only the claims needed to
identify the authenticated user and role. Refresh, email-verification, and
password-reset tokens use random opaque values; only their SHA-256 hashes
should be stored in the auth_tokens table.

Security rules:
- JWT algorithms are restricted to approved HMAC algorithms.
- Production cannot use temporary or example development secrets.
- Access-token claims are validated after decoding.
- Reserved JWT claims cannot be overwritten by callers.
- Raw opaque tokens must never be stored in the database or logged.
- SecretStr values are safely unwrapped only during token operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import secrets
from typing import Any, Final, Literal, Mapping
from uuid import uuid4

from jose import JWTError, jwt
from pydantic import SecretStr

from TP_App.config import settings


TokenRole = Literal["student", "faculty", "admin"]

ACCESS_TOKEN_TYPE: Final[str] = "access"
OPAQUE_TOKEN_BYTES: Final[int] = 48

SUPPORTED_JWT_ALGORITHMS: Final[frozenset[str]] = frozenset(
    {"HS256", "HS384", "HS512"}
)

RESERVED_CLAIMS: Final[frozenset[str]] = frozenset(
    {"sub", "role", "type", "jti", "iat", "nbf", "exp"}
)


class TokenValidationError(ValueError):
    """Raised when a TigerPad token is missing, invalid, or expired."""


def _jwt_configuration() -> tuple[str, str]:
    """Return the configured JWT secret and approved algorithm."""

    configured_secret = settings.JWT_SECRET_KEY

    if isinstance(configured_secret, SecretStr):
        secret = configured_secret.get_secret_value().strip()
    else:
        secret = str(configured_secret).strip()

    algorithm = settings.JWT_ALGORITHM.strip().upper()

    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    if algorithm not in SUPPORTED_JWT_ALGORITHMS:
        raise RuntimeError(
            "JWT_ALGORITHM must be HS256, HS384, or HS512."
        )

    environment = settings.ENVIRONMENT.strip().lower()

    insecure_secrets = {
        "TEMPORARY_DEVELOPMENT_SECRET",
        "REPLACE_WITH_A_LONG_RANDOM_SECRET",
        "REPLACE_WITH_A_DIFFERENT_RANDOM_SECRET",
        "CHANGE_ME",
    }

    if environment in {"production", "prod"} and (
        secret in insecure_secrets or len(secret) < 32
    ):
        raise RuntimeError(
            "Production requires a unique, strong JWT_SECRET_KEY "
            "of at least 32 characters."
        )

    return secret, algorithm


def _normalize_subject(subject: str | int) -> str:
    """Convert a user identifier into a non-empty JWT subject string."""

    if isinstance(subject, bool):
        raise ValueError("Token subject must be a user identifier.")

    normalized = str(subject).strip()

    if not normalized:
        raise ValueError("Token subject cannot be empty.")

    if len(normalized) > 100:
        raise ValueError("Token subject is too long.")

    return normalized


def _normalize_role(role: str) -> TokenRole:
    """Validate a TigerPad role before placing it in a token."""

    normalized = role.strip().lower()

    if normalized not in {"student", "faculty", "admin"}:
        raise ValueError("Token role is not a valid TigerPad role.")

    return normalized  # type: ignore[return-value]


def create_access_token(
    subject: str | int,
    role: str,
    additional_claims: Mapping[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Create a signed, short-lived JWT access token."""

    secret, algorithm = _jwt_configuration()
    normalized_subject = _normalize_subject(subject)
    normalized_role = _normalize_role(role)

    lifetime_minutes = (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES
        if expires_minutes is None
        else expires_minutes
    )

    if lifetime_minutes <= 0 or lifetime_minutes > 24 * 60:
        raise ValueError(
            "Access-token expiration must be between 1 minute and 24 hours."
        )

    if additional_claims:
        conflicting_claims = RESERVED_CLAIMS.intersection(
            additional_claims.keys()
        )

        if conflicting_claims:
            names = ", ".join(sorted(conflicting_claims))
            raise ValueError(
                "Additional claims cannot overwrite reserved claims: "
                f"{names}."
            )

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=lifetime_minutes)

    payload: dict[str, Any] = {
        "sub": normalized_subject,
        "role": normalized_role,
        "type": ACCESS_TOKEN_TYPE,
        "jti": uuid4().hex,
        "iat": int(issued_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    if additional_claims:
        payload.update(dict(additional_claims))

    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a TigerPad JWT access token."""

    if not isinstance(token, str) or not token.strip():
        raise TokenValidationError("Access token is missing.")

    secret, algorithm = _jwt_configuration()

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={
                "require_exp": True,
                "require_sub": True,
                "require_iat": True,
                "require_nbf": True,
                "require_jti": True,
            },
        )
    except (JWTError, TypeError, ValueError) as error:
        raise TokenValidationError(
            "Access token is invalid or expired."
        ) from error

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenValidationError(
            "Token type is not valid for access."
        )

    subject = payload.get("sub")
    role = payload.get("role")
    token_id = payload.get("jti")

    if not isinstance(subject, str) or not subject.strip():
        raise TokenValidationError(
            "Access token subject is invalid."
        )

    if not isinstance(role, str):
        raise TokenValidationError(
            "Access token role is invalid."
        )

    try:
        _normalize_role(role)
    except ValueError as error:
        raise TokenValidationError(
            "Access token role is invalid."
        ) from error

    if not isinstance(token_id, str) or not token_id.strip():
        raise TokenValidationError(
            "Access token identifier is invalid."
        )

    return payload


def get_access_token_subject(token: str) -> str:
    """Return the authenticated user identifier from an access token."""

    return str(decode_access_token(token)["sub"])


def get_access_token_role(token: str) -> TokenRole:
    """Return the validated role from an access token."""

    role = decode_access_token(token)["role"]
    return _normalize_role(role)


def create_opaque_token() -> str:
    """Create a random token for refresh or verification workflows."""

    return secrets.token_urlsafe(OPAQUE_TOKEN_BYTES)


def hash_opaque_token(token: str) -> str:
    """Hash an opaque token for storage in auth_tokens.token_hash."""

    if not isinstance(token, str) or not token:
        raise ValueError("Opaque token cannot be empty.")

    return sha256(token.encode("utf-8")).hexdigest()


def verify_opaque_token(
    token: str,
    stored_hash: str,
) -> bool:
    """Compare a raw token with its stored SHA-256 hash safely."""

    if not isinstance(token, str) or not token:
        return False

    if not isinstance(stored_hash, str) or len(stored_hash) != 64:
        return False

    calculated_hash = hash_opaque_token(token)

    return hmac.compare_digest(calculated_hash, stored_hash)


__all__ = [
    "ACCESS_TOKEN_TYPE",
    "OPAQUE_TOKEN_BYTES",
    "SUPPORTED_JWT_ALGORITHMS",
    "TokenRole",
    "TokenValidationError",
    "create_access_token",
    "create_opaque_token",
    "decode_access_token",
    "get_access_token_role",
    "get_access_token_subject",
    "hash_opaque_token",
    "verify_opaque_token",
]
