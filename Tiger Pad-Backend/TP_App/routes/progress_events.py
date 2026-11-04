"""
Overall function:
This file provides TigerPad API endpoints for viewing and creating student
progress events. Progress events create a timeline of milestones such as
adding skills, completing recommendations, calculating readiness scores,
adding projects, and finishing certifications.

Students can view only their own visible progress events. Student-created
events are always stored with source_type="user" so users cannot impersonate
system, AI, or faculty-generated events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.career_path import CareerPath
from TP_App.models.progress_event import ProgressEvent
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.progress import (
    ProgressEventCreate,
    ProgressEventResponse,
)


router = APIRouter(
    prefix="/students/me/progress",
    tags=["Student Progress"],
)


def get_student_profile(
    current_user: dict[str, Any],
    db: Session,
) -> StudentProfile:
    """Return the authenticated student's profile or raise a 404 error."""

    user_id = current_user.get("user_id")

    student_profile = db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == user_id
        )
    ).scalar_one_or_none()

    if student_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create a student profile before using progress events.",
        )

    return student_profile


@router.get(
    "",
    response_model=list[ProgressEventResponse],
    summary="List the student's progress events",
)
def list_progress_events(
    career_path_id: int | None = Query(
        default=None,
        ge=1,
        description="Optional career path filter.",
    ),
    event_type: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
        description="Optional progress event type filter.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of events to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of events to skip.",
    ),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[ProgressEvent]:
    """Return visible progress events for the authenticated student."""

    student_profile = get_student_profile(current_user, db)

    statement = select(ProgressEvent).where(
        ProgressEvent.student_profile_id
        == student_profile.student_profile_id,
        ProgressEvent.is_visible_to_student == 1,
    )

    if career_path_id is not None:
        statement = statement.where(
            ProgressEvent.career_path_id == career_path_id
        )

    if event_type is not None:
        statement = statement.where(
            ProgressEvent.event_type == event_type
        )

    statement = (
        statement.order_by(
            desc(ProgressEvent.occurred_at),
            desc(ProgressEvent.progress_event_id),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(db.execute(statement).scalars().all())


@router.post(
    "",
    response_model=ProgressEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student progress event",
)
def create_progress_event(
    payload: ProgressEventCreate,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> ProgressEvent:
    """
    Create a student-submitted progress event.

    The route forces source_type to ``user`` regardless of request content.
    """

    student_profile = get_student_profile(current_user, db)

    if payload.career_path_id is not None:
        career_path = db.execute(
            select(CareerPath).where(
                CareerPath.career_path_id == payload.career_path_id
            )
        ).scalar_one_or_none()

        if career_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The selected career path was not found.",
            )

    occurred_at = payload.occurred_at

    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

    progress_event = ProgressEvent(
        student_profile_id=student_profile.student_profile_id,
        career_path_id=payload.career_path_id,
        event_type=payload.event_type.value,
        title=payload.title.strip(),
        description=(
            payload.description.strip()
            if payload.description
            else None
        ),
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        event_data_json=payload.event_data_json,
        source_type="user",
        is_visible_to_student=(
            1 if payload.is_visible_to_student else 0
        ),
        occurred_at=occurred_at,
    )

    db.add(progress_event)
    db.commit()
    db.refresh(progress_event)

    return progress_event