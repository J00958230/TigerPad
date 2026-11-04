"""
Overall function:
This file provides secure password hashing and verification for TigerPad.
Passwords are hashed before database storage and are never returned to the
frontend or written to application logs.

Security rules:
- Passwords are hashed with bcrypt.
- Plaintext passwords are never stored.
- Passwords must meet the configured minimum length.
- Bcrypt's 72-byte limit is enforced to prevent silent truncation.
- Invalid password hashes fail safely without exposing internal details.
"""

from __future__ import annotations

from typing import Final

from passlib.context import CryptContext

from TP_App.config import settings


PASSWORD_SCHEME: Final[str] = "bcrypt"
MAX_PASSWORD_BYTES: Final[int] = 72


password_context = CryptContext(
    schemes=[PASSWORD_SCHEME],
    deprecated="auto",
)


def validate_password(password: str) -> str:
    """
    Validate a password before hashing.

    The password is returned unchanged so valid spaces or symbols inside
    the password are preserved.
    """

    if not isinstance(password, str):
        raise TypeError("Password must be a string.")

    if not password or not password.strip():
        raise ValueError("Password cannot be empty.")

    if "\x00" in password:
        raise ValueError("Password contains an invalid character.")

    if len(password) < settings.MINIMUM_PASSWORD_LENGTH:
        raise ValueError(
            "Password does not meet the minimum length requirement."
        )

    password_length_bytes = len(password.encode("utf-8"))

    if password_length_bytes > MAX_PASSWORD_BYTES:
        raise ValueError(
            "Password is too long. Bcrypt passwords cannot exceed "
            f"{MAX_PASSWORD_BYTES} UTF-8 bytes."
        )

    return password


def hash_password(password: str) -> str:
    """
    Create a secure bcrypt hash for a plaintext password.

    The plaintext password must never be saved or logged by the caller.
    """

    validated_password = validate_password(password)

    return password_context.hash(validated_password)


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    """
    Check a plaintext password against a stored password hash.

    Invalid inputs return False instead of exposing hashing errors.
    """

    if not isinstance(plain_password, str):
        return False

    if not isinstance(password_hash, str) or not password_hash:
        return False

    try:
        return password_context.verify(
            plain_password,
            password_hash,
        )
    except (TypeError, ValueError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """
    Determine whether an existing password hash should be regenerated.

    This supports future bcrypt configuration changes without forcing
    every user to reset their password immediately.
    """

    if not isinstance(password_hash, str) or not password_hash:
        return False

    try:
        return password_context.needs_update(password_hash)
    except (TypeError, ValueError):
        return False


def get_password_hash_scheme(password_hash: str) -> str | None:
    """Return the algorithm identifier used by a stored password hash."""

    if not isinstance(password_hash, str) or not password_hash:
        return None

    try:
        return password_context.identify(password_hash)
    except (TypeError, ValueError):
        return None


__all__ = [
    "MAX_PASSWORD_BYTES",
    "PASSWORD_SCHEME",
    "get_password_hash_scheme",
    "hash_password",
    "password_context",
    "password_needs_rehash",
    "validate_password",
    "verify_password",
]