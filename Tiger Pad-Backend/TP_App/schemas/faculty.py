
"""
===============================================================================
TigerPad - Faculty Request and Response Schemas
File: TP_App/schemas/faculty.py
===============================================================================

Overall Description:
--------------------
This file defines the Pydantic request and response schemas used by
TigerPad's faculty features.

Faculty members can:
    1. Create and update their faculty profiles.
    2. Receive access to authorized academic programs.
    3. View student career-readiness information.
    4. Submit structured faculty reviews.
    5. Provide written feedback and optional evaluation scores.
    6. Assign review statuses.
    7. Retrieve their submitted review history.

Administrators use the faculty profile and program access schemas when
managing faculty permissions.

The Faculty Review schemas support evaluations of:
    - Student resumes
    - Student skills
    - Student projects
    - Student certifications
    - Overall student career readiness

Review statuses:
    reviewed:
        The faculty evaluation has been completed.

    approved:
        The reviewed material has been approved.

    needs_revision:
        The student should make improvements based on faculty feedback.

Security:
---------
These schemas validate incoming and outgoing API data.

They do not authorize faculty access to students.

Faculty authorization, program permissions, student visibility,
review ownership, and resume ownership must be verified in the
API router or service layer.

Database:
---------
The Faculty Review schemas correspond to the faculty_reviews table
defined by TP_App/models/faculty_review.py.

===============================================================================
"""


# =============================================================================
# SECTION 1: IMPORTS
# =============================================================================

from __future__ import annotations

# Datetime values are used for faculty records, access expiration,
# and faculty review timestamps.
from datetime import datetime

# Enumerations restrict certain fields to supported values.
from enum import Enum

# Any supports the existing structured student detail collections.
from typing import Any

# Pydantic provides request validation and response serialization.
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# =============================================================================
# SECTION 2: FACULTY ACCESS LEVELS
# =============================================================================

class FacultyAccessLevel(str, Enum):
    """
    Define supported faculty program access levels.

    viewer:
        May view authorized student information.

    reviewer:
        May view authorized students and submit faculty reviews.

    manager:
        May manage permitted faculty review workflows, subject to
        additional authorization checks in the API.
    """

    viewer = "viewer"
    reviewer = "reviewer"
    manager = "manager"


# =============================================================================
# SECTION 3: FACULTY PROFILE REQUEST SCHEMAS
# =============================================================================

class FacultyProfileCreateRequest(BaseModel):
    """
    Validate information submitted when creating a faculty profile.

    Faculty members can provide professional and departmental details
    associated with their TigerPad account.
    """

    department_id: int | None = Field(
        default=None,
        ge=1,
    )

    job_title: str | None = Field(
        default=None,
        max_length=100,
    )

    office_location: str | None = Field(
        default=None,
        max_length=100,
    )

    phone_number: str | None = Field(
        default=None,
        max_length=25,
    )

    bio: str | None = Field(
        default=None,
        max_length=10000,
    )

    linkedin_url: str | None = Field(
        default=None,
        max_length=500,
    )


class FacultyProfileUpdateRequest(BaseModel):
    """
    Validate changes made to an existing faculty profile.

    Optional fields allow faculty members to update selected profile
    information without resubmitting the entire profile.
    """

    department_id: int | None = Field(
        default=None,
        ge=1,
    )

    job_title: str | None = Field(
        default=None,
        max_length=100,
    )

    office_location: str | None = Field(
        default=None,
        max_length=100,
    )

    phone_number: str | None = Field(
        default=None,
        max_length=25,
    )

    bio: str | None = Field(
        default=None,
        max_length=10000,
    )

    linkedin_url: str | None = Field(
        default=None,
        max_length=500,
    )


# =============================================================================
# SECTION 4: FACULTY PROFILE RESPONSE SCHEMA
# =============================================================================

class FacultyProfileResponse(BaseModel):
    """
    Represent a faculty profile returned by the TigerPad API.

    from_attributes=True allows Pydantic to serialize SQLAlchemy
    faculty profile objects.
    """

    model_config = ConfigDict(from_attributes=True)

    faculty_profile_id: int
    user_id: int | None
    department_id: int | None
    job_title: str | None
    office_location: str | None
    phone_number: str | None
    bio: str | None
    linkedin_url: str | None
    can_review_students: bool
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# SECTION 5: FACULTY PROGRAM ACCESS REQUEST SCHEMAS
# =============================================================================

class FacultyProgramAccessCreateRequest(BaseModel):
    """
    Validate an administrator's assignment of academic program access.

    Faculty members can only review students in programs for which
    they have the required active permissions.
    """

    faculty_profile_id: int = Field(
        ge=1,
    )

    program_id: int = Field(
        ge=1,
    )

    access_level: FacultyAccessLevel = (
        FacultyAccessLevel.viewer
    )

    expires_at: datetime | None = None


class FacultyProgramAccessUpdateRequest(BaseModel):
    """
    Validate changes to an existing faculty program access record.

    Administrators can update the access level, expiration date,
    or active status of an assignment.
    """

    access_level: FacultyAccessLevel | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


# =============================================================================
# SECTION 6: FACULTY PROGRAM ACCESS RESPONSE SCHEMA
# =============================================================================

class FacultyProgramAccessResponse(BaseModel):
    """
    Represent a faculty member's access to an academic program.
    """

    model_config = ConfigDict(from_attributes=True)

    faculty_program_access_id: int
    faculty_profile_id: int
    program_id: int
    access_level: str
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# SECTION 7: FACULTY STUDENT SUMMARY SCHEMA
# =============================================================================

class FacultyStudentSummaryResponse(BaseModel):
    """
    Represent basic student information visible to authorized faculty.

    This schema is used when displaying students in faculty-facing
    lists and search results.
    """

    student_profile_id: int
    user_id: int
    first_name: str
    last_name: str
    academic_level: str | None
    expected_graduation_date: str | None
    professional_headline: str | None
    profile_visibility: str
    is_profile_complete: bool


# =============================================================================
# SECTION 8: FACULTY STUDENT DETAIL SCHEMA
# =============================================================================

class FacultyStudentDetailResponse(FacultyStudentSummaryResponse):
    """
    Represent a student's authorized career-readiness detail view.

    This extends FacultyStudentSummaryResponse with additional
    student profile and career development information.

    The API router determines which student information the
    requesting faculty member is authorized to access.
    """

    preferred_name: str | None = None
    gpa: str | None = None
    bio: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    programs: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    skills: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    experiences: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    projects: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    certifications: list[dict[str, Any]] = Field(
        default_factory=list,
    )


# =============================================================================
# SECTION 9: FACULTY REVIEW ENUMERATIONS
# =============================================================================

class FacultyReviewType(str, Enum):
    """
    Define the types of career-readiness materials faculty can review.

    These values match the CHECK constraint in the MySQL
    faculty_reviews table.
    """

    resume = "resume"
    skills = "skills"
    projects = "projects"
    certifications = "certifications"
    career_readiness = "career_readiness"


class FacultyReviewStatus(str, Enum):
    """
    Define the supported faculty review workflow statuses.

    These values match the CHECK constraint in the MySQL
    faculty_reviews table.
    """

    reviewed = "reviewed"
    approved = "approved"
    needs_revision = "needs_revision"


# =============================================================================
# SECTION 10: FACULTY REVIEW CREATION SCHEMA
# =============================================================================

class FacultyReviewCreateRequest(BaseModel):
    """
    Validate a new faculty review submission.

    A faculty member can submit a review for an authorized student.

    The faculty_profile_id is intentionally excluded because the
    backend must identify the faculty member using the authenticated
    account rather than trusting a client-supplied faculty ID.

    The backend must also verify that:
        - The faculty member has review permission.
        - The student belongs to an authorized program.
        - The student profile is accessible.
        - Any supplied resume belongs to that student.
    """

    student_profile_id: int = Field(
        ge=1,
        description="Student profile receiving the review.",
    )

    resume_id: int | None = Field(
        default=None,
        ge=1,
        description="Optional resume associated with the review.",
    )

    review_type: FacultyReviewType = Field(
        description="Career-readiness material being evaluated.",
    )

    overall_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        allow_inf_nan=False,
        description="Optional evaluation score between 0 and 100.",
    )

    feedback: str = Field(
        min_length=1,
        max_length=10000,
        description="Written feedback from the faculty reviewer.",
    )

    review_status: FacultyReviewStatus = Field(
        default=FacultyReviewStatus.reviewed,
        description="Current status of the faculty review.",
    )

    # -------------------------------------------------------------------------
    # Feedback Validation
    # -------------------------------------------------------------------------

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, value: str) -> str:
        """
        Remove unnecessary surrounding whitespace.

        Reject submissions containing only spaces or blank lines.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "Faculty review feedback cannot be empty."
            )

        return cleaned_value

    # -------------------------------------------------------------------------
    # Resume Association Validation
    # -------------------------------------------------------------------------

    @model_validator(mode="after")
    def validate_resume_association(self):
        """
        Require a resume ID for reviews specifically targeting a resume.

        Other review types may omit the resume ID.

        The API must separately verify actual resume ownership.
        """

        if (
            self.review_type == FacultyReviewType.resume
            and self.resume_id is None
        ):
            raise ValueError(
                "A resume_id is required for a resume review."
            )

        return self


# =============================================================================
# SECTION 11: FACULTY REVIEW UPDATE SCHEMA
# =============================================================================

class FacultyReviewUpdateRequest(BaseModel):
    """
    Validate updates to an existing faculty review.

    Faculty members may update:
        - The evaluation score
        - Written feedback
        - The review status

    The faculty member, student, resume, and review category are
    not editable through this schema.

    The API must verify review ownership and authorization before
    accepting any changes.
    """

    overall_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        allow_inf_nan=False,
    )

    feedback: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
    )

    review_status: FacultyReviewStatus | None = None

    @field_validator("feedback")
    @classmethod
    def validate_updated_feedback(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normalize updated feedback and reject blank strings.

        A missing feedback field means the existing feedback should
        remain unchanged.
        """

        if value is None:
            return None

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "Faculty review feedback cannot be empty."
            )

        return cleaned_value


# =============================================================================
# SECTION 12: FACULTY REVIEW RESPONSE SCHEMA
# =============================================================================

class FacultyReviewResponse(BaseModel):
    """
    Represent a faculty review returned by the TigerPad API.

    This response can be used for:
        - Faculty review submission confirmation
        - Faculty review history
        - Student feedback history
        - Review detail pages

    Access to individual reviews must be checked by the API.
    """

    model_config = ConfigDict(from_attributes=True)

    faculty_review_id: int

    faculty_profile_id: int

    student_profile_id: int

    resume_id: int | None

    review_type: FacultyReviewType

    overall_score: float | None

    feedback: str

    review_status: FacultyReviewStatus

    created_at: datetime

    updated_at: datetime


# =============================================================================
# SECTION 13: FACULTY REVIEW LIST RESPONSE SCHEMA
# =============================================================================

class FacultyReviewListResponse(BaseModel):
    """
    Represent a collection of faculty reviews.

    Used when retrieving review history for an authorized faculty
    member or the student who received the feedback.
    """

    reviews: list[FacultyReviewResponse] = Field(
        default_factory=list,
    )

    total: int = Field(
        ge=0,
        description="Total number of reviews in the result.",
    )


# =============================================================================
# SECTION 14: FACULTY REVIEW SUMMARY SCHEMA
# =============================================================================

class FacultyReviewSummaryResponse(BaseModel):
    """
    Provide a summarized view of faculty review activity.

    This schema supports future faculty dashboard statistics.

    Example statistics:
        - Total submitted reviews
        - Approved reviews
        - Reviews requiring revision
        - Completed reviews
    """

    total_reviews: int = Field(
        default=0,
        ge=0,
    )

    reviewed_count: int = Field(
        default=0,
        ge=0,
    )

    approved_count: int = Field(
        default=0,
        ge=0,
    )

    needs_revision_count: int = Field(
        default=0,
        ge=0,
    )
