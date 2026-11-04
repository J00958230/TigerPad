
"""
===============================================================================
TigerPad - Faculty Review Model
File: TP_App/models/faculty_review.py
===============================================================================

Overall Description:
--------------------
This file defines the FacultyReview SQLAlchemy database model for TigerPad,
Jackson State University's career-readiness website.

The FacultyReview model allows authorized faculty members to provide
structured evaluations and written feedback on student career-readiness
materials.

Faculty members can review:
    1. Student resumes
    2. Student skills
    3. Student projects
    4. Student certifications
    5. Overall career readiness

Each faculty review records:
    - The faculty member submitting the review
    - The student receiving the review
    - The associated resume, when applicable
    - The type of review
    - An optional overall score
    - Written faculty feedback
    - The review status
    - Creation and modification timestamps

Review Status Options:
----------------------
    reviewed:
        The faculty member has completed the evaluation.

    approved:
        The faculty member has approved the reviewed material.

    needs_revision:
        The student needs to make improvements based on faculty feedback.

Database Information:
---------------------
Database: tigerpad
Table: faculty_reviews
Primary Key: faculty_review_id

Foreign Key Relationships:
--------------------------
    faculty_profile_id -> faculty_profiles.faculty_profile_id
    student_profile_id -> student_profiles.student_profile_id
    resume_id          -> resumes.resume_id

Security and Access:
--------------------
This model only defines the database structure.

Faculty authorization, student visibility, program-based permissions,
and review ownership must be enforced by the API service/router layer.

This file does not create API endpoints or bypass access restrictions.

===============================================================================
"""

# =============================================================================
# SECTION 1: IMPORTS
# =============================================================================

# SQLAlchemy column definitions, database constraints, and SQL functions.
from sqlalchemy import (
    Column,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
    ForeignKey,
    Index,
    CheckConstraint,
    func,
)

# MySQL-specific integer type.
#
# TigerPad uses INT UNSIGNED for its primary and foreign key identifiers.
# Using this type ensures that the SQLAlchemy model matches the existing
# MySQL database table.
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# SQLAlchemy relationships allow the application to navigate between
# faculty reviews and their associated faculty, students, and resumes.
from sqlalchemy.orm import relationship

# Import TigerPad's shared SQLAlchemy declarative base.
from TP_App.database.base import Base


# =============================================================================
# SECTION 2: FACULTY REVIEW DATABASE MODEL
# =============================================================================

class FacultyReview(Base):
    """
    Represents a faculty evaluation of a student's career-readiness material.

    Each record belongs to:
        - One faculty profile
        - One student profile
        - Optionally, one student resume

    Multiple reviews may be associated with the same faculty member,
    student, or resume.

    Reviews are stored independently so TigerPad can maintain a history
    of faculty feedback over time.
    """

    # -------------------------------------------------------------------------
    # Database Table Name
    # -------------------------------------------------------------------------

    __tablename__ = "faculty_reviews"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------

    # Unique identifier assigned to each faculty review.
    faculty_review_id = Column(
        MySQLInteger(unsigned=True),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Foreign Keys
    # -------------------------------------------------------------------------

    # Identifies the faculty member responsible for submitting the review.
    #
    # If the faculty profile is deleted, its associated reviews are deleted
    # according to the database's ON DELETE CASCADE constraint.
    faculty_profile_id = Column(
        MySQLInteger(unsigned=True),
        ForeignKey(
            "faculty_profiles.faculty_profile_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_faculty_reviews_faculty",
        ),
        nullable=False,
    )

    # Identifies the student whose career-readiness material is reviewed.
    #
    # The student profile must exist before a review can be submitted.
    student_profile_id = Column(
        MySQLInteger(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_faculty_reviews_student",
        ),
        nullable=False,
    )

    # Optional resume association.
    #
    # Resume reviews can reference a specific resume.
    # Reviews of skills, projects, certifications, or career readiness
    # do not require a resume_id.
    #
    # If a resume is deleted, the review remains in the database and
    # its resume_id becomes NULL.
    resume_id = Column(
        MySQLInteger(unsigned=True),
        ForeignKey(
            "resumes.resume_id",
            ondelete="SET NULL",
            onupdate="CASCADE",
            name="fk_faculty_reviews_resume",
        ),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Review Information
    # -------------------------------------------------------------------------

    # Specifies which category of student material is being evaluated.
    #
    # Supported values:
    #   resume
    #   skills
    #   projects
    #   certifications
    #   career_readiness
    review_type = Column(
        String(30),
        nullable=False,
    )

    # Optional numeric evaluation score.
    #
    # Valid range: 0.00 through 100.00.
    #
    # Faculty members may submit written feedback without assigning
    # a numerical score.
    overall_score = Column(
        DECIMAL(5, 2),
        nullable=True,
    )

    # Faculty member's written evaluation.
    #
    # This field stores recommendations, identified weaknesses,
    # suggested improvements, and other career-readiness feedback.
    feedback = Column(
        Text,
        nullable=False,
    )

    # Current evaluation status.
    #
    # Supported values:
    #   reviewed
    #   approved
    #   needs_revision
    #
    # New reviews default to "reviewed" unless another valid status
    # is explicitly provided.
    review_status = Column(
        String(30),
        nullable=False,
        default="reviewed",
        server_default="reviewed",
    )

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------

    # Automatically records when the review is first created.
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    # Automatically records when the review is created or last modified.
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )

    # -------------------------------------------------------------------------
    # SQLAlchemy Relationships
    # -------------------------------------------------------------------------

    # Provides access to the FacultyProfile associated with this review.
    faculty = relationship(
        "FacultyProfile",
    )

    # Provides access to the StudentProfile receiving the review.
    student = relationship(
        "StudentProfile",
    )

    # Provides access to the associated Resume, if one exists.
    resume = relationship(
        "Resume",
    )

    # -------------------------------------------------------------------------
    # Database Indexes and Validation Constraints
    # -------------------------------------------------------------------------

    __table_args__ = (

        # Speeds up queries retrieving reviews submitted by a faculty member.
        Index(
            "idx_faculty_reviews_faculty",
            "faculty_profile_id",
        ),

        # Speeds up queries retrieving reviews received by a student.
        Index(
            "idx_faculty_reviews_student",
            "student_profile_id",
        ),

        # Speeds up queries retrieving reviews for a particular resume.
        Index(
            "idx_faculty_reviews_resume",
            "resume_id",
        ),

        # Supports chronological review history queries.
        Index(
            "idx_faculty_reviews_created",
            "created_at",
        ),

        # Prevents numeric scores outside the allowed 0-100 range.
        CheckConstraint(
            "overall_score IS NULL OR "
            "overall_score BETWEEN 0 AND 100",
            name="chk_faculty_reviews_score",
        ),

        # Restricts reviews to supported career-readiness categories.
        CheckConstraint(
            "review_type IN ("
            "'resume', "
            "'skills', "
            "'projects', "
            "'certifications', "
            "'career_readiness'"
            ")",
            name="chk_faculty_reviews_type",
        ),

        # Restricts review statuses to supported workflow states.
        CheckConstraint(
            "review_status IN ("
            "'reviewed', "
            "'approved', "
            "'needs_revision'"
            ")",
            name="chk_faculty_reviews_status",
        ),
    )

    # -------------------------------------------------------------------------
    # Model Representation
    # -------------------------------------------------------------------------

    def __repr__(self):
        """
        Return a readable representation of the faculty review.

        Useful when inspecting SQLAlchemy objects during development
        and debugging.
        """

        return (
            f"<FacultyReview("
            f"faculty_review_id={self.faculty_review_id}, "
            f"faculty_profile_id={self.faculty_profile_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"review_type={self.review_type!r}, "
            f"review_status={self.review_status!r}"
            f")>"
        )
