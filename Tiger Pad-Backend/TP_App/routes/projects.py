"""
Overall function:
This file provides authenticated API routes for student project records.

Students can list, create, update, and remove academic, personal, research,
senior, software, community, and portfolio projects.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.project import Project
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)


router = APIRouter(
    prefix="/students/me/projects",
    tags=["Student Projects"],
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
            detail="Create a student profile before managing projects.",
        )

    return student_profile


def _get_owned_project(
    db: Session,
    user_id: int,
    project_id: int,
) -> Project:
    """Return a project only when it belongs to the current student."""

    project = db.scalar(
        select(Project)
        .join(
            StudentProfile,
            Project.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            Project.project_id == project_id,
            StudentProfile.user_id == user_id,
        )
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested project was not found.",
        )

    return project


def _validate_project_dates(
    start_date: date | None,
    end_date: date | None,
    is_current: bool,
) -> None:
    """Ensure project dates are logically ordered."""

    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The end date cannot be before the start date.",
        )

    if is_current and end_date is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A current project should not have an end date.",
        )


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List the authenticated student's projects",
)
def list_projects(
    featured_only: bool = Query(
        default=False,
        description="Return only projects marked as featured.",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Project]:
    """Return projects belonging to the authenticated student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = select(Project).where(
        Project.student_profile_id
        == student_profile.student_profile_id,
    )

    if featured_only:
        query = query.where(
            Project.is_featured.is_(True),
        )

    query = query.order_by(
        Project.is_current.desc(),
        Project.start_date.desc(),
        Project.created_at.desc(),
    ).offset(offset).limit(limit)

    return list(db.scalars(query).all())


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student project",
)
def create_project(
    payload: ProjectCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Project:
    """Create a project for the authenticated student."""

    _validate_project_dates(
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
    )

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    project = Project(
        student_profile_id=student_profile.student_profile_id,
        project_type=payload.project_type,
        title=payload.title,
        role_title=payload.role_title,
        organization_name=payload.organization_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        description=payload.description,
        outcome=payload.outcome,
        project_url=payload.project_url,
        team_size=payload.team_size,
        is_featured=payload.is_featured,
    )

    db.add(project)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The project could not be created.",
        ) from error

    db.refresh(project)
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a student project",
)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Project:
    """Update a project owned by the authenticated student."""

    project = _get_owned_project(
        db=db,
        user_id=int(current_user["user_id"]),
        project_id=project_id,
    )

    update_values = payload.model_dump(exclude_unset=True)

    final_start_date = update_values.get(
        "start_date",
        project.start_date,
    )
    final_end_date = update_values.get(
        "end_date",
        project.end_date,
    )
    final_is_current = update_values.get(
        "is_current",
        project.is_current,
    )

    _validate_project_dates(
        start_date=final_start_date,
        end_date=final_end_date,
        is_current=final_is_current,
    )

    for field_name, field_value in update_values.items():
        setattr(project, field_name, field_value)

    db.commit()
    db.refresh(project)

    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a student project",
)
def delete_project(
    project_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> None:
    """Remove a project owned by the authenticated student."""

    project = _get_owned_project(
        db=db,
        user_id=int(current_user["user_id"]),
        project_id=project_id,
    )

    db.delete(project)
    db.commit()