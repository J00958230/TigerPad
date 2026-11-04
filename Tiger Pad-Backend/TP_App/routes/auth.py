"""
Overall function:
This file defines TigerPad's authentication API routes. It handles student
registration, login, JWT access-token creation, opaque refresh-token rotation,
logout, current-user lookup, and authenticated password changes.

Security rules:
- Public registration always creates a student account; clients cannot choose
  the faculty or administrator role.
- Only configured JSU email domains can register through this endpoint.
- Passwords are verified or hashed with the shared password security module.
- Access tokens are short-lived JWTs and refresh tokens are random opaque
  values. Only refresh-token hashes are stored in MySQL.
- Failed logins trigger a temporary account lockout.
- Error responses never reveal whether a submitted email belongs to an
  account, and sensitive values are never logged or returned.

Temporary configuration values in this file are intentionally conservative
fallbacks until Cell and the team approve the final security settings in
config.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from TP_App.config import settings
from TP_App.dependencies import CurrentUser, get_current_user, get_db
from TP_App.models.auth_token import AuthToken
from TP_App.models.role import Role
from TP_App.models.user import User
from TP_App.schemas.auth import (
    AuthMessageResponse,
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from TP_App.security.passwords import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from TP_App.security.tokens import (
    create_access_token,
    create_opaque_token,
    hash_opaque_token,
    verify_opaque_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ---------------------------------------------------------------------------
# Temporary security defaults
# ---------------------------------------------------------------------------
# TODO (Cell): Move these approved values into config.py after the security
# review. getattr() lets the route work with the current configuration while
# still allowing the final settings to override these development defaults.
DEFAULT_MAX_FAILED_LOGIN_ATTEMPTS = 5
DEFAULT_ACCOUNT_LOCKOUT_MINUTES = 15
DEFAULT_REFRESH_TOKEN_DAYS = 7
DEFAULT_REMEMBERED_REFRESH_TOKEN_DAYS = 30


def _configured_positive_int(
    setting_name: str,
    default: int,
    maximum: int,
) -> int:
    """Read a bounded positive integer from settings safely."""

    raw_value = getattr(settings, setting_name, default)

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default

    if value < 1 or value > maximum:
        return default

    return value


def _now_naive_utc() -> datetime:
    """
    Return the current UTC time without timezone information.

    MySQL DATETIME columns in TigerPad do not contain timezone metadata.
    Keeping these values naive and UTC-based avoids aware/naive comparison
    errors with the existing SQLAlchemy models.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _allowed_email_domains() -> set[str]:
    """
    Return the configured JSU email domains.

    The current project configuration may expose this as a comma-separated
    string, a list, or a tuple. The fallback keeps development registration
    restricted to JSUMS addresses until the final configuration is supplied.
    """

    configured = getattr(settings, "ALLOWED_EMAIL_DOMAINS", "jsums.edu")

    if isinstance(configured, str):
        values = configured.split(",")
    else:
        try:
            values = list(configured)
        except TypeError:
            values = ["jsums.edu"]

    return {
        str(value).strip().lower().lstrip("@")
        for value in values
        if str(value).strip()
    }


def _is_allowed_jsu_email(email: str) -> bool:
    """Return True when an email belongs to a configured JSU domain."""

    if "@" not in email:
        return False

    domain = email.rsplit("@", 1)[1].strip().lower()
    allowed_domains = _allowed_email_domains()

    return any(
        domain == allowed_domain
        or domain.endswith(f".{allowed_domain}")
        for allowed_domain in allowed_domains
    )


def _generic_login_error() -> HTTPException:
    """Return one non-enumerating error for all failed login attempts."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid JSU email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _safe_role_name(role_name: Any) -> str:
    """Normalize a database role and reject unsupported role values."""

    normalized = str(role_name).strip().lower()

    if normalized not in {"student", "faculty", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad account roles are temporarily unavailable.",
        )

    return normalized


def _user_response(
    user: User,
    role_name: str,
) -> AuthenticatedUser:
    """Convert a User model into a safe authentication response."""

    return AuthenticatedUser(
        user_id=user.user_id,
        role=_safe_role_name(role_name),
        jsu_email=user.jsu_email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=bool(user.is_active),
        email_verified_at=user.email_verified_at,
    )


def _issue_token_pair(
    database: Session,
    user: User,
    role_name: str,
    refresh_days: int,
) -> TokenResponse:
    """Create an access token and persist one hashed refresh token."""

    normalized_role = _safe_role_name(role_name)
    raw_refresh_token = create_opaque_token()
    now = _now_naive_utc()

    refresh_record = AuthToken(
        user_id=user.user_id,
        token_hash=hash_opaque_token(raw_refresh_token),
        token_type="refresh",
        expires_at=now + timedelta(days=refresh_days),
    )

    database.add(refresh_record)

    try:
        access_token = create_access_token(
            subject=user.user_id,
            role=normalized_role,
        )
    except (RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad authentication is not configured correctly.",
        ) from error

    expires_minutes = _configured_positive_int(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        30,
        24 * 60,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        expires_in=expires_minutes * 60,
    )


def _load_user_and_role(
    database: Session,
    user_id: int,
) -> tuple[User, str] | None:
    """Load one user and its role from MySQL."""

    statement = (
        select(User, Role.name)
        .join(Role, Role.role_id == User.role_id)
        .where(User.user_id == user_id)
    )

    result = database.execute(statement).one_or_none()

    if result is None:
        return None

    user, role_name = result
    return user, _safe_role_name(role_name)


@router.post(
    "/register",
    response_model=AuthenticatedUser,
    status_code=status.HTTP_201_CREATED,
    summary="Create a JSU student account",
)
def register_student(
    request: RegisterRequest,
    database: Session = Depends(get_db),
) -> AuthenticatedUser:
    """
    Create a student account using a JSU email address.

    Faculty and administrator accounts are intentionally excluded from this
    public endpoint and must be provisioned through an approved admin process.
    """

    if not _is_allowed_jsu_email(request.jsu_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration requires an approved JSU email address.",
        )

    try:
        student_role = database.scalar(
            select(Role).where(Role.name == "student")
        )

        if student_role is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The TigerPad student role is not configured.",
            )

        existing_user = database.scalar(
            select(User).where(User.jsu_email == request.jsu_email)
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists for this JSU email.",
            )

        user = User(
            role_id=student_role.role_id,
            jsu_email=request.jsu_email,
            password_hash=hash_password(
                request.password.get_secret_value()
            ),
            first_name=request.first_name,
            last_name=request.last_name,
        )

        database.add(user)
        database.flush()
        database.commit()
        database.refresh(user)

        return _user_response(user, "student")

    except HTTPException:
        database.rollback()
        raise

    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this JSU email.",
        ) from None

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not create the account right now.",
        ) from None


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Sign in to TigerPad",
)
def login(
    request: LoginRequest,
    database: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a user and return an access/refresh token pair."""

    now = _now_naive_utc()

    try:
        loaded = database.execute(
            select(User, Role.name)
            .join(Role, Role.role_id == User.role_id)
            .where(User.jsu_email == request.jsu_email)
        ).one_or_none()

        if loaded is None:
            raise _generic_login_error()

        user, role_name = loaded
        normalized_role = _safe_role_name(role_name)

        if not bool(user.is_active):
            raise _generic_login_error()

        if user.locked_until is not None and user.locked_until > now:
            raise _generic_login_error()

        # Reset an expired lockout before evaluating a fresh attempt.
        if user.locked_until is not None and user.locked_until <= now:
            user.locked_until = None
            user.failed_login_attempts = 0

        plain_password = request.password.get_secret_value()
        password_valid = verify_password(
            plain_password,
            user.password_hash,
        )

        if not password_valid:
            max_attempts = _configured_positive_int(
                "MAX_FAILED_LOGIN_ATTEMPTS",
                DEFAULT_MAX_FAILED_LOGIN_ATTEMPTS,
                100,
            )
            lockout_minutes = _configured_positive_int(
                "ACCOUNT_LOCKOUT_MINUTES",
                DEFAULT_ACCOUNT_LOCKOUT_MINUTES,
                24 * 60,
            )
            attempts = int(user.failed_login_attempts or 0) + 1

            if attempts >= max_attempts:
                user.failed_login_attempts = 0
                user.locked_until = now + timedelta(
                    minutes=lockout_minutes
                )
            else:
                user.failed_login_attempts = attempts

            database.commit()
            raise _generic_login_error()

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(plain_password)

        refresh_days = (
            DEFAULT_REMEMBERED_REFRESH_TOKEN_DAYS
            if request.remember_me
            else DEFAULT_REFRESH_TOKEN_DAYS
        )
        refresh_days = _configured_positive_int(
            "REMEMBERED_REFRESH_TOKEN_EXPIRE_DAYS"
            if request.remember_me
            else "REFRESH_TOKEN_EXPIRE_DAYS",
            refresh_days,
            365,
        )

        tokens = _issue_token_pair(
            database,
            user,
            normalized_role,
            refresh_days,
        )

        database.commit()

        return LoginResponse(
            success=True,
            message="Login successful.",
            tokens=tokens,
            user=_user_response(user, normalized_role),
        )

    except HTTPException:
        database.rollback()
        raise

    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not complete the login session.",
        ) from None

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad authentication is temporarily unavailable.",
        ) from None


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an access token",
)
def refresh_access_token(
    request: RefreshTokenRequest,
    database: Session = Depends(get_db),
) -> TokenResponse:
    """Rotate a valid refresh token and issue a new token pair."""

    raw_refresh_token = request.refresh_token.get_secret_value()
    token_hash = hash_opaque_token(raw_refresh_token)
    now = _now_naive_utc()

    try:
        statement = (
            select(AuthToken, User, Role.name)
            .join(User, User.user_id == AuthToken.user_id)
            .join(Role, Role.role_id == User.role_id)
            .where(
                AuthToken.token_hash == token_hash,
                AuthToken.token_type == "refresh",
            )
            .with_for_update(of=AuthToken)
        )
        loaded = database.execute(statement).one_or_none()

        if loaded is None:
            raise _generic_login_error()

        stored_token, user, role_name = loaded
        normalized_role = _safe_role_name(role_name)

        if not verify_opaque_token(
            raw_refresh_token,
            stored_token.token_hash,
        ):
            raise _generic_login_error()

        if (
            stored_token.used_at is not None
            or stored_token.revoked_at is not None
            or stored_token.expires_at <= now
            or not bool(user.is_active)
            or (
                user.locked_until is not None
                and user.locked_until > now
            )
        ):
            raise _generic_login_error()

        stored_token.used_at = now
        refresh_days = _configured_positive_int(
            "REFRESH_TOKEN_EXPIRE_DAYS",
            DEFAULT_REFRESH_TOKEN_DAYS,
            365,
        )
        tokens = _issue_token_pair(
            database,
            user,
            normalized_role,
            refresh_days,
        )
        database.commit()

        return tokens

    except HTTPException:
        database.rollback()
        raise

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not refresh the login session.",
        ) from None


@router.get(
    "/me",
    response_model=AuthenticatedUser,
    summary="Get the current authenticated user",
)
def current_user(
    authenticated_user: CurrentUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Return safe information for the current bearer-token user."""

    # CurrentUser intentionally contains internal authorization data such as
    # role_id. Build the public schema explicitly so private fields cannot be
    # returned and Pydantic's extra-field protection remains enabled.
    return AuthenticatedUser(
        user_id=int(authenticated_user["user_id"]),
        role=_safe_role_name(authenticated_user["role"]),
        jsu_email=str(authenticated_user["jsu_email"]),
        first_name=str(authenticated_user["first_name"]),
        last_name=str(authenticated_user["last_name"]),
        is_active=bool(authenticated_user["is_active"]),
        email_verified_at=authenticated_user.get("email_verified_at"),
    )


@router.post(
    "/logout",
    response_model=AuthMessageResponse,
    summary="Sign out of TigerPad",
)
def logout(
    request: LogoutRequest | None = None,
    authenticated_user: CurrentUser = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> AuthMessageResponse:
    """
    Revoke one refresh token or all refresh sessions for the user.

    The short-lived JWT cannot be erased server-side by this table design,
    so it naturally expires. Refresh-token revocation prevents new access
    tokens from being issued after logout.
    """

    request = request or LogoutRequest()
    now = _now_naive_utc()
    user_id = int(authenticated_user["user_id"])

    try:
        if request.all_sessions or request.refresh_token is None:
            database.execute(
                update(AuthToken)
                .where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_type == "refresh",
                    AuthToken.revoked_at.is_(None),
                    AuthToken.used_at.is_(None),
                )
                .values(revoked_at=now)
            )
        else:
            raw_refresh_token = request.refresh_token.get_secret_value()
            token_hash = hash_opaque_token(raw_refresh_token)
            stored_token = database.scalar(
                select(AuthToken).where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_hash == token_hash,
                    AuthToken.token_type == "refresh",
                    AuthToken.revoked_at.is_(None),
                    AuthToken.used_at.is_(None),
                )
            )

            if stored_token is not None and verify_opaque_token(
                raw_refresh_token,
                stored_token.token_hash,
            ):
                stored_token.revoked_at = now

        database.commit()

        return AuthMessageResponse(
            success=True,
            message="TigerPad logout completed.",
        )

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not complete logout.",
        ) from None


@router.post(
    "/change-password",
    response_model=AuthMessageResponse,
    summary="Change the authenticated user's password",
)
def change_password(
    request: PasswordChangeRequest,
    authenticated_user: CurrentUser = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> AuthMessageResponse:
    """Verify and replace the password for the current user."""

    user_id = int(authenticated_user["user_id"])

    try:
        user = database.scalar(
            select(User).where(User.user_id == user_id)
        )

        if user is None or not bool(user.is_active):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required.",
            )

        if not verify_password(
            request.current_password.get_secret_value(),
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The current password is incorrect.",
            )

        user.password_hash = hash_password(
            request.new_password.get_secret_value()
        )
        user.failed_login_attempts = 0
        user.locked_until = None

        database.execute(
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.token_type == "refresh",
                AuthToken.revoked_at.is_(None),
                AuthToken.used_at.is_(None),
            )
            .values(revoked_at=_now_naive_utc())
        )

        database.commit()

        return AuthMessageResponse(
            success=True,
            message=(
                "Password changed successfully. Please sign in again "
                "on your other TigerPad sessions."
            ),
        )

    except HTTPException:
        database.rollback()
        raise

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not change the password right now.",
        ) from None


__all__ = ["router"]
