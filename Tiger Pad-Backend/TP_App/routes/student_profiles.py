
"""
===============================================================================
TigerPad - Student Profile Routes
File: TP_App/routes/student_profile.py
===============================================================================

Overall Description:
--------------------
This file defines authenticated student-profile routes for TigerPad,
Jackson State University's career-readiness website.

Students can:
    1. Create their own student profile.
    2. View their student profile.
    3. View a summary of their profile.
    4. Update their profile information.
    5. Retrieve faculty reviews and feedback associated with their profile.

The backend automatically determines profile ownership using the
authenticated student's account.

Student academic program selections are stored separately in the
student_programs table and are not modified through these endpoints.

Faculty Review Integration:
---------------------------
The faculty review endpoint allows students to see evaluations submitted
by authorized faculty members.

Students can view:
    - Review category
    - Faculty feedback
    - Evaluation score
    - Review status
    - Review creation and update timestamps

Faculty reviews are read-only for students.

Students cannot:
    - Submit faculty reviews
    - Change faculty feedback
    - Modify evaluation scores
    - Approve their own work
    - Access another student's faculty reviews

Security Rules:
---------------
1. Every endpoint requires an authenticated student account.
2. Profile ownership is determined using the authenticated user ID.
3. Clients cannot supply a user ID to access another student.
4. Profile completion is calculated by the backend.
5. Pydantic schemas validate profile and review response data.
6. Database errors return safe messages without exposing SQL details.
7. Faculty reviews are filtered using the student's own profile ID.

Database Tables:
----------------
student_profiles
faculty_reviews

===============================================================================
"""


# =============================================================================
# SECTION 1: IMPORTS
# =============================================================================

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

# Authentication and database dependencies.
from TP_App.dependencies import (
    CurrentUser,
    get_db,
    require_student,
)

# SQLAlchemy models.
from TP_App.models.student_profile import StudentProfile
from TP_App.models.faculty_review import FacultyReview

# Existing student profile schemas.
from TP_App.schemas.student_profile import (
    StudentProfileCreateRequest,
    StudentProfileResponse,
    StudentProfileSummary,
    StudentProfileUpdateRequest,
)

# Faculty review response schemas.
from TP_App.schemas.faculty import (
    FacultyReviewListResponse,
    FacultyReviewResponse,
)


# =============================================================================
# SECTION 2: ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(
    prefix="/students/me/profile",
    tags=["Student Profile"],
)


# =============================================================================
# SECTION 3: STUDENT PROFILE COMPLETION HELPERS
# =============================================================================

def _profile_is_complete(profile: StudentProfile) -> bool:
    """
    Calculate whether the minimum career-ready profile fields are present.

    GPA is intentionally optional because students may choose not to
    share it.

    Academic level, graduation date, professional headline, and bio
    are the initial required fields for TigerPad's profile-completion
    indicator.
    """

    required_values: tuple[Any, ...] = (
        profile.academic_level,
        profile.expected_graduation_date,
        profile.professional_headline,
        profile.bio,
    )

    return all(
        value is not None
        and (
            not isinstance(value, str)
            or bool(value.strip())
        )
        for value in required_values
    )


def _apply_completion_status(profile: StudentProfile) -> None:
    """
    Update the student's profile completion flag.

    Completion is calculated by the backend rather than accepted
    from client input.
    """

    profile.is_profile_complete = int(
        _profile_is_complete(profile)
    )


# =============================================================================
# SECTION 4: STUDENT PROFILE RESPONSE HELPERS
# =============================================================================

def _profile_response(
    profile: StudentProfile,
) -> StudentProfileResponse:
    """
    Convert a StudentProfile SQLAlchemy model into a safe API response.
    """

    return StudentProfileResponse(
        student_profile_id=profile.student_profile_id,
        user_id=profile.user_id,
        preferred_name=profile.preferred_name,
        academic_level=profile.academic_level,
        expected_graduation_date=profile.expected_graduation_date,
        gpa=profile.gpa,
        professional_headline=profile.professional_headline,
        bio=profile.bio,
        linkedin_url=profile.linkedin_url,
        portfolio_url=profile.portfolio_url,
        profile_visibility=profile.profile_visibility,
        is_profile_complete=bool(
            profile.is_profile_complete
        ),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _profile_summary(
    profile: StudentProfile,
) -> StudentProfileSummary:
    """
    Convert a StudentProfile model into a compact dashboard summary.
    """

    return StudentProfileSummary(
        student_profile_id=profile.student_profile_id,
        preferred_name=profile.preferred_name,
        academic_level=profile.academic_level,
        professional_headline=profile.professional_headline,
        profile_visibility=profile.profile_visibility,
        is_profile_complete=bool(
            profile.is_profile_complete
        ),
    )


# =============================================================================
# SECTION 5: STUDENT PROFILE OWNERSHIP HELPER
# =============================================================================

def _get_student_profile(
    database: Session,
    student_user_id: int,
) -> StudentProfile | None:
    """
    Retrieve the profile belonging to one authenticated student.

    This helper prevents student-profile queries from accepting
    arbitrary client-provided ownership identifiers.
    """

    return database.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == student_user_id
        )
    )


# =============================================================================
# SECTION 6: GET CURRENT STUDENT PROFILE
# =============================================================================

@router.get(
    "",
    response_model=StudentProfileResponse,
    summary="Get the current student's profile",
)
def get_my_profile(
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> StudentProfileResponse:
    """
    Return the profile belonging to the authenticated student.
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
                    "A TigerPad student profile has "
                    "not been created yet."
                ),
            )

        return _profile_response(profile)

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load the student profile.",
        ) from None


# =============================================================================
# SECTION 7: GET CURRENT STUDENT PROFILE SUMMARY
# =============================================================================

@router.get(
    "/summary",
    response_model=StudentProfileSummary,
    summary="Get the current student's profile summary",
)
def get_my_profile_summary(
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> StudentProfileSummary:
    """
    Return compact profile information for the student dashboard.
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
                    "A TigerPad student profile has "
                    "not been created yet."
                ),
            )

        return _profile_summary(profile)

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not load the profile summary.",
        ) from None


# =============================================================================
# SECTION 8: CREATE CURRENT STUDENT PROFILE
# =============================================================================

@router.post(
    "",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create the current student's profile",
)
def create_my_profile(
    request: StudentProfileCreateRequest,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> StudentProfileResponse:
    """
    Create one student profile owned by the authenticated student.

    The authenticated account determines ownership.

    A student cannot create multiple profiles for the same account.
    """

    student_user_id = int(
        authenticated_user["user_id"]
    )

    try:
        existing_profile = _get_student_profile(
            database,
            student_user_id,
        )

        if existing_profile is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A TigerPad student profile already exists.",
            )

        profile = StudentProfile(
            user_id=student_user_id,
            **request.model_dump(),
        )

        _apply_completion_status(profile)

        database.add(profile)
        database.flush()
        database.commit()
        database.refresh(profile)

        return _profile_response(profile)

    except HTTPException:
        database.rollback()
        raise

    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A TigerPad student profile already exists.",
        ) from None

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not create the student profile.",
        ) from None


# =============================================================================
# SECTION 9: UPDATE CURRENT STUDENT PROFILE
# =============================================================================

@router.patch(
    "",
    response_model=StudentProfileResponse,
    summary="Update the current student's profile",
)
def update_my_profile(
    request: StudentProfileUpdateRequest,
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> StudentProfileResponse:
    """
    Update only the profile fields supplied by the authenticated student.

    Students cannot modify another student's profile through this route.
    """

    student_user_id = int(
        authenticated_user["user_id"]
    )

    try:
        profile = _get_student_profile(
            database,
            student_user_id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Create a TigerPad student profile "
                    "before updating it."
                ),
            )

        update_values = request.model_dump(
            exclude_unset=True
        )

        for field_name, field_value in update_values.items():
            setattr(
                profile,
                field_name,
                field_value,
            )

        _apply_completion_status(profile)

        database.commit()
        database.refresh(profile)

        return _profile_response(profile)

    except HTTPException:
        database.rollback()
        raise

    except SQLAlchemyError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TigerPad could not update the student profile.",
        ) from None


# =============================================================================
# SECTION 10: GET FACULTY REVIEWS RECEIVED BY CURRENT STUDENT
# =============================================================================

@router.get(
    "/faculty-reviews",
    response_model=FacultyReviewListResponse,
    summary="View faculty feedback received by the current student",
)
def get_my_faculty_reviews(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of reviews to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of reviews to skip.",
    ),
    authenticated_user: CurrentUser = Depends(require_student),
    database: Session = Depends(get_db),
) -> FacultyReviewListResponse:
    """
    Retrieve faculty reviews associated with the authenticated student.

    Security:
        - Requires student authentication.
        - Determines the student profile from the JWT identity.
        - Never accepts a student_profile_id from the client.
        - Returns only reviews belonging to that student's profile.
        - Does not allow students to edit faculty feedback.

    Reviews are returned in reverse chronological order so the
    newest faculty feedback appears first.
    """

    try:
        # ---------------------------------------------------------------------
        # Identify the authenticated student's profile.
        # ---------------------------------------------------------------------

        student_user_id = int(
            authenticated_user["user_id"]
        )

        profile = _get_student_profile(
            database,
            student_user_id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Create a TigerPad student profile "
                    "before viewing faculty feedback."
                ),
            )

        # ---------------------------------------------------------------------
        # Retrieve reviews belonging to this student only.
        # ---------------------------------------------------------------------

        review_query = (
            select(FacultyReview)
            .where(
                FacultyReview.student_profile_id
                == profile.student_profile_id
            )
            .order_by(
                FacultyReview.created_at.desc(),
                FacultyReview.faculty_review_id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        reviews = list(
            database.scalars(review_query).all()
        )

        # ---------------------------------------------------------------------
        # Count all reviews belonging to the authenticated student.
        # ---------------------------------------------------------------------

        from sqlalchemy import func

        total_reviews = database.scalar(
            select(
                func.count(
                    FacultyReview.faculty_review_id
                )
            ).where(
                FacultyReview.student_profile_id
                == profile.student_profile_id
            )
        )

        # ---------------------------------------------------------------------
        # Return validated, read-only faculty feedback.
        # ---------------------------------------------------------------------

        return FacultyReviewListResponse(
            reviews=[
                FacultyReviewResponse.model_validate(review)
                for review in reviews
            ],
            total=int(total_reviews or 0),
        )

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "TigerPad could not load your faculty feedback."
            ),
        ) from None


# =============================================================================
# SECTION 11: PUBLIC ROUTER EXPORT
# =============================================================================

# Export the router for registration in TigerPad's main application.
__all__ = ["router"]
