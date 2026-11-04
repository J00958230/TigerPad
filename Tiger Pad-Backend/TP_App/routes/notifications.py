
"""
===============================================================================
TigerPad - Student Notification Routes
File: TP_App/routes/notifications.py
===============================================================================

Overall Description:
--------------------
This file provides authenticated student notification endpoints for
TigerPad, Jackson State University's career-readiness website.

Students can:
    1. View their own notifications.
    2. Filter notifications by read status, type, and priority.
    3. View faculty feedback notifications.
    4. Check their unread notification count.
    5. Mark individual notifications as read or unread.
    6. Mark all their notifications as read.

Faculty Review Integration:
---------------------------
When authorized faculty submit or update student reviews, the faculty
backend creates notification records in the existing notifications table.

This router retrieves those notifications and makes them available to
the student dashboard.

Faculty feedback notifications use:
    notification_type = "faculty_feedback"

Security Rules:
---------------
1. All endpoints require an authenticated student account.
2. Students can access only notifications belonging to their user ID.
3. Notification ownership is determined from authentication.
4. Students cannot create notifications through these endpoints.
5. Students cannot change notification messages or recipients.
6. Students may change only the read/unread status.
7. Database errors return safe responses without exposing SQL details.

Database Table:
---------------
notifications

===============================================================================
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: IMPORTS
# =============================================================================

from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.notification import Notification

from TP_App.schemas.notification import (
    NotificationMarkAllReadResponse,
    NotificationResponse,
    NotificationUpdateRequest,
)


# =============================================================================
# SECTION 2: ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(
    prefix="/students/me/notifications",
    tags=["Notifications"],
)


# =============================================================================
# SECTION 3: TIME AND SECURITY HELPERS
# =============================================================================

def _utc_now() -> datetime:
    """
    Return a timezone-naive UTC datetime for MySQL DATETIME columns.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_owned_notification(
    db: Session,
    user_id: int,
    notification_id: int,
) -> Notification:
    """
    Retrieve a notification belonging to the authenticated student.

    A notification belonging to another user is treated as not found.
    """

    notification = db.scalar(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == user_id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested notification was not found.",
        )

    return notification


def _active_notification_condition():
    """
    Build a condition that excludes expired notifications.

    Notifications without an expiration date remain active.
    """

    return or_(
        Notification.expires_at.is_(None),
        Notification.expires_at > _utc_now(),
    )


def _notification_order():
    """
    Return a consistent notification display order.

    Unread notifications appear first. Within each read-status group,
    newer notifications appear before older ones.

    Higher numeric priority values indicate greater priority.
    """

    return (
        Notification.is_read.asc(),
        Notification.priority_level.desc(),
        desc(Notification.created_at),
        Notification.notification_id.desc(),
    )


# =============================================================================
# SECTION 4: LIST STUDENT NOTIFICATIONS
# =============================================================================

@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List the student's notifications",
)
def list_notifications(
    is_read: bool | None = Query(
        default=None,
        description="Filter by read status.",
    ),
    notification_type: str | None = Query(
        default=None,
        max_length=40,
        description="Filter by notification type.",
    ),
    priority_level: int | None = Query(
        default=None,
        ge=1,
        le=5,
        description="Filter by priority level.",
    ),
    include_expired: bool = Query(
        default=False,
        description="Whether expired notifications should be included.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Notification]:
    """
    Retrieve notifications belonging to the authenticated student.

    Supports filtering, sorting, and pagination.
    """

    user_id = int(current_user["user_id"])

    try:
        query = select(Notification).where(
            Notification.user_id == user_id,
        )

        if is_read is not None:
            query = query.where(
                Notification.is_read == int(is_read),
            )

        if notification_type is not None:
            query = query.where(
                Notification.notification_type == notification_type,
            )

        if priority_level is not None:
            query = query.where(
                Notification.priority_level == priority_level,
            )

        if not include_expired:
            query = query.where(
                _active_notification_condition()
            )

        query = (
            query
            .order_by(*_notification_order())
            .offset(offset)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load your notifications.",
        ) from None


# =============================================================================
# SECTION 5: LIST FACULTY FEEDBACK NOTIFICATIONS
# =============================================================================

@router.get(
    "/faculty-feedback",
    response_model=list[NotificationResponse],
    summary="List faculty feedback notifications",
)
def list_faculty_feedback_notifications(
    unread_only: bool = Query(
        default=False,
        description="Return only unread faculty feedback notifications.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Notification]:
    """
    Retrieve faculty feedback notifications for the current student.

    These notifications are created when faculty submit or update
    a review.

    The student cannot access notifications belonging to other users.
    """

    user_id = int(current_user["user_id"])

    try:
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.notification_type == "faculty_feedback",
            _active_notification_condition(),
        )

        if unread_only:
            query = query.where(
                Notification.is_read == 0,
            )

        query = (
            query
            .order_by(*_notification_order())
            .offset(offset)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "TigerPad could not load your faculty "
                "feedback notifications."
            ),
        ) from None


# =============================================================================
# SECTION 6: COUNT UNREAD STUDENT NOTIFICATIONS
# =============================================================================

@router.get(
    "/unread-count",
    summary="Count the student's unread notifications",
)
def unread_notification_count(
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """
    Return the number of active unread notifications.

    This endpoint can power a notification badge on the student dashboard.
    """

    user_id = int(current_user["user_id"])

    try:
        unread_count = db.scalar(
            select(
                func.count(Notification.notification_id)
            ).where(
                Notification.user_id == user_id,
                Notification.is_read == 0,
                _active_notification_condition(),
            )
        )

        return {
            "unread_count": int(unread_count or 0),
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not count your notifications.",
        ) from None


# =============================================================================
# SECTION 7: MARK ALL STUDENT NOTIFICATIONS AS READ
# =============================================================================

@router.post(
    "/mark-all-read",
    response_model=NotificationMarkAllReadResponse,
    summary="Mark all notifications as read",
)
def mark_all_notifications_read(
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> NotificationMarkAllReadResponse:
    """
    Mark all unread notifications belonging to the student as read.

    Other users' notifications are not affected.
    """

    user_id = int(current_user["user_id"])
    now = _utc_now()

    try:
        result = db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == 0,
            )
            .values(
                is_read=1,
                read_at=now,
            )
        )

        updated_count = int(result.rowcount or 0)

        db.commit()

        return NotificationMarkAllReadResponse(
            success=True,
            updated_count=updated_count,
            message="All TigerPad notifications were marked as read.",
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not update your notifications.",
        ) from None


# =============================================================================
# SECTION 8: UPDATE INDIVIDUAL NOTIFICATION READ STATUS
# =============================================================================

@router.patch(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Update notification read status",
)
def update_notification(
    notification_id: int,
    payload: NotificationUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Notification:
    """
    Mark one notification as read or unread.

    The notification must belong to the authenticated student.
    Only read tracking fields are modified.
    """

    user_id = int(current_user["user_id"])

    try:
        notification = _get_owned_notification(
            db=db,
            user_id=user_id,
            notification_id=notification_id,
        )

        notification.is_read = int(payload.is_read)
        notification.read_at = (
            _utc_now()
            if payload.is_read
            else None
        )

        db.commit()
        db.refresh(notification)

        return notification

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not update this notification.",
        ) from None


# =============================================================================
# SECTION 9: PUBLIC ROUTER EXPORT
# =============================================================================

__all__ = ["router"]
