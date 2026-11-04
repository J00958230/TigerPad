
"""
Overall function:
This file defines shared FastAPI dependencies used throughout TigerPad.
It provides application settings, MySQL sessions, authenticated-user
loading from JWT bearer tokens, and role-based permission checks.

Security rules:
- Database sessions close after every request.
- Database errors trigger a rollback.
- JWTs are validated centrally.
- Password hashes and token values are never returned.
- Disabled accounts cannot access protected endpoints.
- Students, faculty, and administrators have separate permissions.

Swagger authentication:
- Uses HTTPBearer instead of OAuth2PasswordBearer.
- Swagger accepts an access token from POST /api/auth/login.
- The existing JSON login endpoint remains unchanged.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from TP_App.config import Settings, get_settings, settings
from TP_App.database.connection import SessionLocal
from TP_App.models.role import Role
from TP_App.models.user import User
from TP_App.security.tokens import (
    TokenValidationError,
    decode_access_token,
)


CurrentUser = dict[str, Any]


# HTTPBearer allows Swagger to accept a JWT access token directly.
# auto_error=False lets TigerPad provide its own authentication errors
# and preserves support for secure-cookie authentication.
oauth2_scheme = HTTPBearer(
    scheme_name="HTTPBearer",
    description=(
        "Enter the access token returned by POST /api/auth/login. "
        "Use the token without quotation marks or the Bearer prefix."
    ),
    auto_error=False,
)


def get_app_settings() -> Settings:
    """Provide TigerPad configuration settings to API routes."""
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy database session per request."""
    database = SessionLocal()

    try:
        yield database

    except SQLAlchemyError:
        database.rollback()
        raise

    finally:
        database.close()


def _authentication_exception() -> HTTPException:
    """Build the standard response for missing or invalid credentials."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication is required to access "
            "this TigerPad endpoint."
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )


def _load_user_from_token(
    token: str,
    database: Session,
) -> CurrentUser:
    """Decode a JWT and load its active user from MySQL."""

    try:
        claims = decode_access_token(token)

    except (TokenValidationError, RuntimeError):
        raise _authentication_exception() from None

    subject = claims.get("sub")

    try:
        user_id = int(subject)

    except (TypeError, ValueError):
        raise _authentication_exception() from None

    if user_id <= 0:
        raise _authentication_exception()

    statement = (
        select(User, Role.name)
        .join(Role, Role.role_id == User.role_id)
        .where(User.user_id == user_id)
    )

    try:
        result = database.execute(statement).one_or_none()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "TigerPad user authentication is temporarily "
                "unavailable."
            ),
        ) from None

    if result is None:
        raise _authentication_exception()

    user, role_name = result

    if not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This TigerPad account is inactive.",
        )

    normalized_role = str(role_name).strip().lower()

    if claims.get("role") != normalized_role:
        raise _authentication_exception()

    return {
        "user_id": user.user_id,
        "role_id": user.role_id,
        "role": normalized_role,
        "jsu_email": user.jsu_email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": bool(user.is_active),
    }


def _get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    """
    Extract the token from HTTPBearer credentials.

    Reject unsupported authorization schemes rather than treating
    them as valid bearer tokens.
    """

    if credentials is None:
        return None

    if credentials.scheme.lower() != "bearer":
        raise _authentication_exception()

    token = credentials.credentials.strip()

    if not token:
        raise _authentication_exception()

    return token


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        oauth2_scheme
    ),
    database: Session = Depends(get_db),
) -> CurrentUser:
    """
    Return the active user represented by a bearer token
    or a secure authentication cookie.
    """

    token = _get_bearer_token(credentials)

    if not token and settings.COOKIE_AUTH_ENABLED:
        token = request.cookies.get("tigerpad_access_token")

    if not token:
        raise _authentication_exception()

    return _load_user_from_token(token, database)


def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        oauth2_scheme
    ),
    database: Session = Depends(get_db),
) -> CurrentUser | None:
    """
    Return the authenticated user when a token is supplied.

    Public endpoints can use this dependency when authentication
    is optional.
    """

    token = _get_bearer_token(credentials)

    if not token and settings.COOKIE_AUTH_ENABLED:
        token = request.cookies.get("tigerpad_access_token")

    if not token:
        return None

    return _load_user_from_token(token, database)


def require_student(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Allow only authenticated student accounts."""

    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access is required.",
        )

    return current_user


def require_faculty(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Allow authenticated faculty members and administrators."""

    if current_user.get("role") not in {"faculty", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty access is required.",
        )

    return current_user


def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Allow only authenticated administrators."""

    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )

    return current_user


def require_faculty_or_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Provide a clear dependency for faculty/admin endpoints."""
    return require_faculty(current_user)


__all__ = [
    "CurrentUser",
    "get_app_settings",
    "get_current_user",
    "get_db",
    "get_optional_current_user",
    "oauth2_scheme",
    "require_admin",
    "require_faculty",
    "require_faculty_or_admin",
    "require_student",
]
