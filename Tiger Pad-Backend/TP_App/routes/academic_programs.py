"""
Overall function:
This file defines TigerPad's academic-program and student-program API routes.
It lets the website display approved JSU academic programs and lets an
authenticated student connect one or more programs to their own student
profile.

Academic programs represent majors, minors, concentrations, certificates,
and other approved program records from the academic_programs table. The
student_programs table stores the student's relationship to those programs.
Those relationships later help TigerPad match students to generalized career
paths, skills, résumé guidance, and readiness recommendations.

Security and data-integrity rules:
- Program reference data is read-only through these endpoints.
- Student ownership is assigned from the authenticated JWT and never from a
  request body.
- A student may have multiple program records but no more than one active
  primary program.
- Program assignments can be marked withdrawn instead of being deleted.
- Inactive academic programs cannot be newly assigned.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from TP_App.dependencies import CurrentUser, get_db, require_student
from TP_App.models.academic_program import AcademicProgram
from TP_App.models.student_profile import StudentProfile
from TP_App.models.student_program import StudentProgram
from TP_App.schemas.academic_program import (
    AcademicProgramResponse,
    AcademicProgramSearchRequest,
    AcademicProgramSummary,
    StudentProgramCreateRequest,
    StudentProgramResponse,
    StudentProgramSummary,
    StudentProgramUpdateRequest,
)


academic_program_router = APIRouter(
    prefix="/academic-programs",
    tags=["Academic Programs"],
)

student_program_router = APIRouter(
    prefix="/students/me/programs",
    tags=["Student Programs"],
)


def _program_summary(
    program: AcademicProgram,
) -> AcademicProgramSummary:
    """Convert an academic-program model into a safe summary."""

    return AcademicProgramSummary(
        program_id=program.program_id,
        department_id=program.department_id,
        name=program.name,
        program_code=program.program_code,
        program_type=program.program_type,
        degree_level=program.degree_level,
        degree_abbreviation=program.degree_abbreviation,
    )


def _program_response(
    program: AcademicProgram,
) -> AcademicProgramResponse:
    """Convert an academic-program model into a complete response."""

    return AcademicProgramResponse(
        program_id=program.program_id,
        department_id=program.department_id,
        name=program.name,
        program_code=program.program_code,
        program_type=program.program_type,
        degree_level=program.degree_level,
        degree_abbreviation=program.degree_abbreviation,
        description=program.description,
        catalog_url=program.catalog_url,
        is_active=bool(program.is_active),
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


def _student_program_response(
    student_program: StudentProgram,
    program: AcademicProgram,
) -> StudentProgramResponse:
    """Convert a student-program join into a safe API response."""

    return StudentProgramResponse(
        student_program_id=student_program.student_program_id,
        student_profile_id=student_program.student_profile_id,
        program_id=student_program.program_id,
        program_name=program.name,
        program_code=program.program_code,
        program_type=program.program_type,
        degree_level=program.degree_level,
        degree_abbreviation=program.degree_abbreviation,
        is_primary=bool(student_program.is_primary),
        status=student_program.status,
        start_date=student_program.start_date,
        completion_date=student_program.completion_date,
        created_at=student_program.created_at,
        updated_at=student_program.updated_at,
    )


def _get_student_profile(
    database: Session,
    user_id: int,
) -> StudentProfile | None:
    """Load the authenticated student's profile."""

    return database.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )


def _validate_combined_dates(
    start_date: date | None,
    completion_date: date | None,
) -> None:
    """Validate dates after combining request and stored values."""

    if (
        start_date is not None
        and completion_date is not None
        and completion_date < start_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Completion date cannot be earlier than the start date.",
        )


def _clear_other_primary_programs(
    database: Session,
    student_profile_id: int,
    exclude_student_program_id: int | None = None,
) -> None:
    """Clear active-primary status from a student's other programs."""

    statement = select(StudentProgram).where(
        StudentProgram.student_profile_id == student_profile_id,
        StudentProgram.is_primary == 1,
        StudentProgram.status == "active",
    )

    if exclude_student_program_id is not None:
        statement = statement.where(
            StudentProgram.student_program_id
            != exclude_student_program_id
        )

    existing_primary_programs = database.scalars(statement).all()

    for existing_program in existing_primary_programs:
        existing_program.is_primary = 0


@academic_program_router.get(
    "",
    response_model=list[AcademicProgramSummary],
    summary="List approved JSU academic programs",
)
def list_academic_programs(
    search_text: str | None = Query(default=None, max_length=100),
    department_id: int | None = Query(default=None, gt=0),
    program_type: str | None = Query(default=None, max_length=30),
    degree_level: str | None = Query(default=None, max_length=30),
    active_only: bool = True,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    database: Session = Depends(get_db),
) -> list[AcademicProgramSummary]:
    """Search the approved academic-program reference data."""

    try:
        filters = AcademicProgramSearchRequest(
            search_text=search_text,
            department_id=department_id,
            program_type=program_type,
            degree_level=degree_level,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

        statement = select(AcademicProgram)

        if filters.active_only:
            statement = statement.where(AcademicProgram.is_active == 1)

        if filters.department_id is not None:
            statement = statement.where(
                AcademicProgram.department_id == filters.department_id
            )

        if filters.program_type is not None:
            statement = statement.where(
                AcademicProgram.program_type == filters.program_type
            )

        if filters.degree_level is not None:
            statement = statement.where(
                AcademicProgram.degree_level == filters.degree_level
            )

        if filters.search_text is not None:
            search_pattern = f"%{filters.search_text}%"

            statement = statement.where(
                or_(
                    AcademicProgram.name.ilike(search_pattern),
                    AcademicProgram.program_code.ilike(search_pattern),
                    AcademicProgram.description.ilike(search_pattern),
                )
            )

        statement = (
            statement.order_by(AcademicProgram.name.asc())
            .offset(filters.offset)
            .limit(filters.limit)
        )

        programs = database.scalars(statement).all()

        return [
            _program_summary(program)
            for program in programs
        ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load academic programs.",
        ) from None


@academic_program_router.get(
    "/{program_id}",
    response_model=AcademicProgramResponse,
    summary="Get one approved academic program",
)
def get_academic_program(
    program_id: int,
    database: Session = Depends(get_db),
) -> AcademicProgramResponse:
    """Return one active academic program by identifier."""

    if program_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Program ID must be positive.",
        )

    try:
        program = database.scalar(
            select(AcademicProgram).where(
                AcademicProgram.program_id == program_id,
                AcademicProgram.is_active == 1,
            )
        )

        if program is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested academic program was not found.",
            )

        return _program_response(program)

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load the academic program.",
        ) from None


@student_program_router.get(
    "",
    response_model=list[StudentProgramResponse],
    summary="List the current student's academic programs",
)
def list_my_programs(
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> list[StudentProgramResponse]:
    """Return all academic programs connected to the current student."""

    try:
        profile = _get_student_profile(
            database,
            int(authenticated_user["user_id"]),
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Create a student profile before adding programs.",
            )

        statement = (
            select(StudentProgram, AcademicProgram)
            .join(
                AcademicProgram,
                AcademicProgram.program_id == StudentProgram.program_id,
            )
            .where(
                StudentProgram.student_profile_id
                == profile.student_profile_id
            )
            .order_by(
                StudentProgram.is_primary.desc(),
                AcademicProgram.name.asc(),
            )
        )

        rows = database.execute(statement).all()

        return [
            _student_program_response(student_program, program)
            for student_program, program in rows
        ]

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load the student's programs.",
        ) from None


@student_program_router.post(
    "",
    response_model=StudentProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an academic program to the current student",
)
def add_my_program(
    request: StudentProgramCreateRequest,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> StudentProgramResponse:
    """Connect an approved academic program to the current student."""

    user_id = int(authenticated_user["user_id"])

    try:
        profile = _get_student_profile(database, user_id)

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Create a student profile before adding programs.",
            )

        program = database.scalar(
            select(AcademicProgram).where(
                AcademicProgram.program_id == request.program_id,
                AcademicProgram.is_active == 1,
            )
        )

        if program is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested academic program was not found.",
            )

        existing_relationship = database.scalar(
            select(StudentProgram).where(
                StudentProgram.student_profile_id
                == profile.student_profile_id,
                StudentProgram.program_id == request.program_id,
            )
        )

        if existing_relationship is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This academic program is already connected to you.",
            )

        if request.is_primary:
            _clear_other_primary_programs(
                database,
                profile.student_profile_id,
            )

        student_program = StudentProgram(
            student_profile_id=profile.student_profile_id,
            program_id=program.program_id,
            is_primary=int(request.is_primary),
            status=request.status,
            start_date=request.start_date,
            completion_date=request.completion_date,
        )

        database.add(student_program)
        database.flush()
        database.commit()
        database.refresh(student_program)

        return _student_program_response(student_program, program)

    except HTTPException:
        database.rollback()
        raise

    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This academic program is already connected to you.",
        ) from None

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not add the academic program.",
        ) from None


@student_program_router.patch(
    "/{student_program_id}",
    response_model=StudentProgramResponse,
    summary="Update the current student's academic program",
)
def update_my_program(
    student_program_id: int,
    request: StudentProgramUpdateRequest,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> StudentProgramResponse:
    """Update an owned academic-program relationship."""

    if student_program_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Student-program ID must be positive.",
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

        statement = (
            select(StudentProgram, AcademicProgram)
            .join(
                AcademicProgram,
                AcademicProgram.program_id == StudentProgram.program_id,
            )
            .where(
                StudentProgram.student_program_id == student_program_id,
                StudentProgram.student_profile_id
                == profile.student_profile_id,
            )
        )

        loaded = database.execute(statement).one_or_none()

        if loaded is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested student-program record was not found.",
            )

        student_program, program = loaded
        update_values = request.model_dump(exclude_unset=True)

        new_status = update_values.get(
            "status",
            student_program.status,
        )

        requested_primary = update_values.get(
            "is_primary",
            bool(student_program.is_primary),
        )

        if new_status != "active":
            if update_values.get("is_primary") is True:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Only an active academic program can be primary."
                    ),
                )

            requested_primary = False

        new_start_date = update_values.get(
            "start_date",
            student_program.start_date,
        )

        new_completion_date = update_values.get(
            "completion_date",
            student_program.completion_date,
        )

        _validate_combined_dates(
            new_start_date,
            new_completion_date,
        )

        if requested_primary:
            _clear_other_primary_programs(
                database,
                profile.student_profile_id,
                exclude_student_program_id=(
                    student_program.student_program_id
                ),
            )

        for field_name, field_value in update_values.items():
            setattr(student_program, field_name, field_value)

        student_program.is_primary = int(requested_primary)

        database.commit()
        database.refresh(student_program)

        return _student_program_response(student_program, program)

    except HTTPException:
        database.rollback()
        raise

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not update the academic program.",
        ) from None


@student_program_router.delete(
    "/{student_program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an academic program from the current student",
)
def delete_my_program(
    student_program_id: int,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> None:
    """Remove only an academic-program assignment owned by this student.

    The approved AcademicProgram catalog record is never deleted.
    Removing the student's primary program may affect career recommendations.
    """

    if student_program_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Student-program ID must be positive.",
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

        student_program = database.scalar(
            select(StudentProgram).where(
                StudentProgram.student_program_id == student_program_id,
                StudentProgram.student_profile_id == profile.student_profile_id,
            )
        )
        if student_program is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested student-program record was not found.",
            )

        database.delete(student_program)
        database.commit()
        return None

    except HTTPException:
        database.rollback()
        raise

    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This academic program cannot be removed because it is in use.",
        ) from None

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not remove the academic program.",
        ) from None


__all__ = [
    "academic_program_router",
    "student_program_router",
]