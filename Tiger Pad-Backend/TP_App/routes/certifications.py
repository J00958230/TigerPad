"""
Overall function:
This file provides authenticated API routes for student certifications and
credentials.

Students can list, create, update, and remove certifications, licenses,
certificates, badges, and other career-related credentials.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.certification import Certification
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.certification import (
    CertificationCreateRequest,
    CertificationResponse,
    CertificationUpdateRequest,
)


router = APIRouter(
    prefix="/students/me/certifications",
    tags=["Student Certifications"],
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
                "Create a student profile before managing certifications."
            ),
        )

    return student_profile


def _get_owned_certification(
    db: Session,
    user_id: int,
    certification_id: int,
) -> Certification:
    """Return a certification only when it belongs to the current student."""

    certification = db.scalar(
        select(Certification)
        .join(
            StudentProfile,
            Certification.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            Certification.certification_id == certification_id,
            StudentProfile.user_id == user_id,
        )
    )

    if certification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested certification was not found.",
        )

    return certification


def _validate_certification_dates(
    issue_date: date | None,
    expiration_date: date | None,
    does_not_expire: bool,
) -> None:
    """Ensure certification dates are logically ordered."""

    if (
        issue_date is not None
        and expiration_date is not None
        and expiration_date < issue_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The expiration date cannot be before the issue date."
            ),
        )

    if does_not_expire and expiration_date is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A non-expiring certification cannot have an expiration date."
            ),
        )


@router.get(
    "",
    response_model=list[CertificationResponse],
    summary="List the authenticated student's certifications",
)
def list_certifications(
    featured_only: bool = Query(
        default=False,
        description="Return only certifications marked as featured.",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Certification]:
    """Return certifications belonging to the authenticated student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = select(Certification).where(
        Certification.student_profile_id
        == student_profile.student_profile_id,
    )

    if featured_only:
        query = query.where(
            Certification.is_featured.is_(True),
        )

    query = query.order_by(
        Certification.issue_date.desc(),
        Certification.created_at.desc(),
    ).offset(offset).limit(limit)

    return list(db.scalars(query).all())


@router.post(
    "",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student certification",
)
def create_certification(
    payload: CertificationCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Certification:
    """Create a certification for the authenticated student."""

    _validate_certification_dates(
        issue_date=payload.issue_date,
        expiration_date=payload.expiration_date,
        does_not_expire=payload.does_not_expire,
    )

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    certification = Certification(
        student_profile_id=student_profile.student_profile_id,
        credential_type=payload.credential_type,
        name=payload.name,
        issuing_organization=payload.issuing_organization,
        credential_id=payload.credential_id,
        credential_url=payload.credential_url,
        issue_date=payload.issue_date,
        expiration_date=payload.expiration_date,
        does_not_expire=payload.does_not_expire,
        description=payload.description,
        is_featured=payload.is_featured,
    )

    db.add(certification)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The certification could not be created.",
        ) from error

    db.refresh(certification)
    return certification


@router.patch(
    "/{certification_id}",
    response_model=CertificationResponse,
    summary="Update a student certification",
)
def update_certification(
    certification_id: int,
    payload: CertificationUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Certification:
    """Update a certification owned by the authenticated student."""

    certification = _get_owned_certification(
        db=db,
        user_id=int(current_user["user_id"]),
        certification_id=certification_id,
    )

    update_values = payload.model_dump(exclude_unset=True)

    final_issue_date = update_values.get(
        "issue_date",
        certification.issue_date,
    )
    final_expiration_date = update_values.get(
        "expiration_date",
        certification.expiration_date,
    )
    final_does_not_expire = update_values.get(
        "does_not_expire",
        certification.does_not_expire,
    )

    _validate_certification_dates(
        issue_date=final_issue_date,
        expiration_date=final_expiration_date,
        does_not_expire=final_does_not_expire,
    )

    for field_name, field_value in update_values.items():
        setattr(certification, field_name, field_value)

    db.commit()
    db.refresh(certification)

    return certification


@router.delete(
    "/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a student certification",
)
def delete_certification(
    certification_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> None:
    """Remove a certification owned by the authenticated student."""

    certification = _get_owned_certification(
        db=db,
        user_id=int(current_user["user_id"]),
        certification_id=certification_id,
    )

    db.delete(certification)
    db.commit()