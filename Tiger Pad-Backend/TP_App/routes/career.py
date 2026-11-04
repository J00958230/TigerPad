"""
Overall function:
This file defines TigerPad's generalized career-path and student-career-goal
API routes.

TigerPad does not scrape or return live job postings through these routes.
Instead, it explains broad career paths such as Cybersecurity Analyst,
Healthcare Administrator, Teacher, Business Operations Analyst, or Research
Scientist. Career paths are matched to a student's active academic programs
through the career_path_programs table.

Students can browse active career paths, view paths related to their own
programs, and save career goals for future readiness and recommendation
features.

Security and data-integrity rules:
- Only active career paths are returned to normal students.
- Student ownership comes from the authenticated JWT.
- Students cannot submit student_profile_id values.
- A student may have one primary goal at a time.
- Career paths are reference data and cannot be changed through these routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from TP_App.dependencies import CurrentUser, get_db, require_student
from TP_App.models.career_goal import CareerGoal
from TP_App.models.career_path import CareerPath
from TP_App.models.career_path_program import CareerPathProgram
from TP_App.models.student_profile import StudentProfile
from TP_App.models.student_program import StudentProgram
from TP_App.schemas.career import (
    CareerGoalCreateRequest,
    CareerGoalResponse,
    CareerGoalUpdateRequest,
    CareerPathResponse,
    CareerPathSearchRequest,
)


career_path_router = APIRouter(
    prefix="/career-paths",
    tags=["Career Paths"],
)

student_career_router = APIRouter(
    prefix="/students/me",
    tags=["Student Career Guidance"],
)


def _career_path_response(
    career_path: CareerPath,
) -> CareerPathResponse:
    """Convert a career-path model into a safe API response."""

    return CareerPathResponse(
        career_path_id=career_path.career_path_id,
        industry_id=career_path.industry_id,
        name=career_path.name,
        career_path_code=career_path.career_path_code,
        description=career_path.description,
        typical_education_level=career_path.typical_education_level,
        is_active=bool(career_path.is_active),
        created_at=career_path.created_at,
        updated_at=career_path.updated_at,
    )


def _career_goal_response(
    career_goal: CareerGoal,
) -> CareerGoalResponse:
    """Convert a career-goal model into a safe API response."""

    return CareerGoalResponse(
        career_goal_id=career_goal.career_goal_id,
        student_profile_id=career_goal.student_profile_id,
        career_path_id=career_goal.career_path_id,
        goal_type=career_goal.goal_type,
        status=career_goal.status,
        target_date=career_goal.target_date,
        notes=career_goal.notes,
        created_at=career_goal.created_at,
        updated_at=career_goal.updated_at,
    )


def _get_student_profile(
    database: Session,
    user_id: int,
) -> StudentProfile | None:
    """Load the profile owned by the authenticated student."""

    return database.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )


def _clear_other_primary_goals(
    database: Session,
    student_profile_id: int,
    exclude_career_goal_id: int | None = None,
) -> None:
    """Change other active primary goals to secondary goals."""

    statement = select(CareerGoal).where(
        CareerGoal.student_profile_id == student_profile_id,
        CareerGoal.goal_type == "primary",
        CareerGoal.status == "active",
    )

    if exclude_career_goal_id is not None:
        statement = statement.where(
            CareerGoal.career_goal_id != exclude_career_goal_id
        )

    existing_primary_goals = database.scalars(statement).all()

    for existing_goal in existing_primary_goals:
        existing_goal.goal_type = "secondary"


@career_path_router.get(
    "",
    response_model=list[CareerPathResponse],
    summary="List generalized TigerPad career paths",
)
def list_career_paths(
    search_text: str | None = Query(default=None, max_length=100),
    industry_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=10000),
    database: Session = Depends(get_db),
) -> list[CareerPathResponse]:
    """Search active generalized career paths."""

    try:
        filters = CareerPathSearchRequest(
            search_text=search_text,
            industry_id=industry_id,
            active_only=True,
            limit=limit,
            offset=offset,
        )

        statement = select(CareerPath)

        # Public catalog never exposes unpublished career paths.
        statement = statement.where(CareerPath.is_active == 1)

        if filters.industry_id is not None:
            statement = statement.where(
                CareerPath.industry_id == filters.industry_id
            )

        if filters.search_text is not None:
            search_pattern = f"%{filters.search_text}%"

            statement = statement.where(
                or_(
                    CareerPath.name.ilike(search_pattern),
                    CareerPath.career_path_code.ilike(search_pattern),
                    CareerPath.description.ilike(search_pattern),
                )
            )

        statement = (
            statement.order_by(CareerPath.name.asc())
            .offset(filters.offset)
            .limit(filters.limit)
        )

        career_paths = database.scalars(statement).all()

        return [
            _career_path_response(career_path)
            for career_path in career_paths
        ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load career paths.",
        ) from None


@career_path_router.get(
    "/{career_path_id}",
    response_model=CareerPathResponse,
    summary="Get one generalized career path",
)
def get_career_path(
    career_path_id: int,
    database: Session = Depends(get_db),
) -> CareerPathResponse:
    """Return one active generalized career path."""

    if career_path_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Career-path ID must be positive.",
        )

    try:
        career_path = database.scalar(
            select(CareerPath).where(
                CareerPath.career_path_id == career_path_id,
                CareerPath.is_active == 1,
            )
        )

        if career_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested career path was not found.",
            )

        return _career_path_response(career_path)

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load the career path.",
        ) from None


@student_career_router.get(
    "/career-paths",
    response_model=list[CareerPathResponse],
    summary="Recommend career paths from student programs",
)
def recommend_my_career_paths(
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> list[CareerPathResponse]:
    """
    Return generalized career paths connected to the student's active
    academic programs.
    """

    try:
        profile = _get_student_profile(
            database,
            int(authenticated_user["user_id"]),
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Create a student profile before viewing "
                    "recommendations."
                ),
            )

        statement = (
            select(CareerPath)
            .join(
                CareerPathProgram,
                CareerPathProgram.career_path_id
                == CareerPath.career_path_id,
            )
            .join(
                StudentProgram,
                StudentProgram.program_id
                == CareerPathProgram.program_id,
            )
            .where(
                StudentProgram.student_profile_id
                == profile.student_profile_id,
                StudentProgram.status == "active",
                CareerPathProgram.is_active == 1,
                CareerPath.is_active == 1,
            )
            .distinct()
            .order_by(CareerPath.name.asc())
        )

        career_paths = database.scalars(statement).all()

        return [
            _career_path_response(career_path)
            for career_path in career_paths
        ]

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not build career-path recommendations.",
        ) from None


@student_career_router.get(
    "/career-goals",
    response_model=list[CareerGoalResponse],
    summary="List the current student's career goals",
)
def list_my_career_goals(
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> list[CareerGoalResponse]:
    """Return career goals owned by the authenticated student."""

    try:
        profile = _get_student_profile(
            database,
            int(authenticated_user["user_id"]),
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Create a student profile before adding career goals."
                ),
            )

        statement = (
            select(CareerGoal)
            .where(
                CareerGoal.student_profile_id
                == profile.student_profile_id
            )
            .order_by(
                CareerGoal.goal_type.asc(),
                CareerGoal.created_at.desc(),
            )
        )

        goals = database.scalars(statement).all()

        return [_career_goal_response(goal) for goal in goals]

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load career goals.",
        ) from None


@student_career_router.post(
    "/career-goals",
    response_model=CareerGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student career goal",
)
def create_my_career_goal(
    request: CareerGoalCreateRequest,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> CareerGoalResponse:
    """Create a goal for an active generalized career path."""

    try:
        profile = _get_student_profile(
            database,
            int(authenticated_user["user_id"]),
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Create a student profile before adding career goals."
                ),
            )

        career_path = database.scalar(
            select(CareerPath).where(
                CareerPath.career_path_id == request.career_path_id,
                CareerPath.is_active == 1,
            )
        )

        if career_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested career path was not found.",
            )

        existing_goal = database.scalar(
            select(CareerGoal).where(
                CareerGoal.student_profile_id
                == profile.student_profile_id,
                CareerGoal.career_path_id == request.career_path_id,
            )
        )

        if existing_goal is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This career path is already one of your goals.",
            )

        if request.goal_type == "primary":
            _clear_other_primary_goals(
                database,
                profile.student_profile_id,
            )

        career_goal = CareerGoal(
            student_profile_id=profile.student_profile_id,
            career_path_id=career_path.career_path_id,
            goal_type=request.goal_type,
            status="active",
            target_date=request.target_date,
            notes=request.notes,
        )

        database.add(career_goal)
        database.flush()
        database.commit()
        database.refresh(career_goal)

        return _career_goal_response(career_goal)

    except HTTPException:
        database.rollback()
        raise

    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This career path is already one of your goals.",
        ) from None

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not create the career goal.",
        ) from None


@student_career_router.patch(
    "/career-goals/{career_goal_id}",
    response_model=CareerGoalResponse,
    summary="Update the current student's career goal",
)
def update_my_career_goal(
    career_goal_id: int,
    request: CareerGoalUpdateRequest,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> CareerGoalResponse:
    """Update an owned career goal."""

    if career_goal_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Career-goal ID must be positive.",
        )

    try:
        profile = _get_student_profile(
            database,
            int(authenticated_user["user_id"]),
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The student profile was not found.",
            )

        career_goal = database.scalar(
            select(CareerGoal).where(
                CareerGoal.career_goal_id == career_goal_id,
                CareerGoal.student_profile_id
                == profile.student_profile_id,
            )
        )

        if career_goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested career goal was not found.",
            )

        update_values = request.model_dump(exclude_unset=True)

        new_goal_type = update_values.get(
            "goal_type",
            career_goal.goal_type,
        )

        if new_goal_type == "primary":
            _clear_other_primary_goals(
                database,
                profile.student_profile_id,
                exclude_career_goal_id=career_goal.career_goal_id,
            )

        for field_name, field_value in update_values.items():
            setattr(career_goal, field_name, field_value)

        database.commit()
        database.refresh(career_goal)

        return _career_goal_response(career_goal)

    except HTTPException:
        database.rollback()
        raise

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not update the career goal.",
        ) from None


@student_career_router.delete(
    "/career-goals/{career_goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove one of the current student's career goals",
)
def delete_my_career_goal(
    career_goal_id: int,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> None:
    """Delete only a career goal belonging to the authenticated student."""

    if career_goal_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Career-goal ID must be positive.",
        )

    try:
        profile = _get_student_profile(
            database,
            int(authenticated_user["user_id"]),
        )
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The student profile was not found.",
            )

        career_goal = database.scalar(
            select(CareerGoal).where(
                CareerGoal.career_goal_id == career_goal_id,
                CareerGoal.student_profile_id == profile.student_profile_id,
            )
        )
        if career_goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested career goal was not found.",
            )

        database.delete(career_goal)
        database.commit()
        return None

    except HTTPException:
        database.rollback()
        raise
    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not remove the career goal.",
        ) from None


__all__ = [
    "career_path_router",
    "student_career_router",
]