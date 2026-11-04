"""
Overall function:
This file provides authenticated API routes for student experience records.

Students can list, create, update, and remove employment, internships,
research, volunteer work, leadership activities, and other experiences.
Every record is restricted to the authenticated student's profile.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.experience import Experience
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.experience import (
    ExperienceCreateRequest,
    ExperienceResponse,
    ExperienceUpdateRequest,
)


router = APIRouter(
    prefix="/students/me/experiences",
    tags=["Student Experiences"],
)


def _get_student_profile(
    db: Session,
    user_id: int,
) -> StudentProfile:
    """Return the student profile belonging to the authenticated user."""

    student_profile = db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == user_id,
        )
    )

    if student_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Create a student profile before managing experiences."
            ),
        )

    return student_profile


def _get_owned_experience(
    db: Session,
    user_id: int,
    experience_id: int,
) -> Experience:
    """Return an experience only when it belongs to the current student."""

    experience = db.scalar(
        select(Experience)
        .join(
            StudentProfile,
            Experience.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            Experience.experience_id == experience_id,
            StudentProfile.user_id == user_id,
        )
    )

    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested experience was not found.",
        )

    return experience


def _validate_experience_dates(
    start_date: date,
    end_date: date | None,
    is_current: bool,
) -> None:
    """Ensure experience dates are logically ordered."""

    if end_date is not None and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The end date cannot be before the start date.",
        )

    if is_current and end_date is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A current experience should not have an end date."
            ),
        )


@router.get(
    "",
    response_model=list[ExperienceResponse],
    summary="List the authenticated student's experiences",
)
def list_experiences(
    featured_only: bool = Query(
        default=False,
        description="Return only experiences marked as featured.",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Experience]:
    """Return experiences belonging to the authenticated student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = select(Experience).where(
        Experience.student_profile_id
        == student_profile.student_profile_id,
    )

    if featured_only:
        query = query.where(
            Experience.is_featured.is_(True),
        )

    query = query.order_by(
        Experience.is_current.desc(),
        Experience.start_date.desc(),
        Experience.created_at.desc(),
    ).offset(offset).limit(limit)

    return list(db.scalars(query).all())


@router.post(
    "",
    response_model=ExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student experience",
)
def create_experience(
    payload: ExperienceCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Experience:
    """Create an experience for the authenticated student."""

    _validate_experience_dates(
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
    )

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    experience = Experience(
        student_profile_id=student_profile.student_profile_id,
        experience_type=payload.experience_type,
        organization_name=payload.organization_name,
        position_title=payload.position_title,
        location=payload.location,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        description=payload.description,
        is_featured=payload.is_featured,
    )

    db.add(experience)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The experience could not be created.",
        ) from error

    db.refresh(experience)
    return experience


@router.patch(
    "/{experience_id}",
    response_model=ExperienceResponse,
    summary="Update a student experience",
)
def update_experience(
    experience_id: int,
    payload: ExperienceUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Experience:
    """Update an experience owned by the authenticated student."""

    experience = _get_owned_experience(
        db=db,
        user_id=int(current_user["user_id"]),
        experience_id=experience_id,
    )

    update_values = payload.model_dump(exclude_unset=True)

    final_start_date = update_values.get(
        "start_date",
        experience.start_date,
    )
    final_end_date = update_values.get(
        "end_date",
        experience.end_date,
    )
    final_is_current = update_values.get(
        "is_current",
        experience.is_current,
    )

    _validate_experience_dates(
        start_date=final_start_date,
        end_date=final_end_date,
        is_current=final_is_current,
    )

    for field_name, field_value in update_values.items():
        setattr(experience, field_name, field_value)

    db.commit()
    db.refresh(experience)

    return experience


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a student experience",
)
def delete_experience(
    experience_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> None:
    """Remove an experience owned by the authenticated student."""

    experience = _get_owned_experience(
        db=db,
        user_id=int(current_user["user_id"]),
        experience_id=experience_id,
    )

    db.delete(experience)
    db.commit()
