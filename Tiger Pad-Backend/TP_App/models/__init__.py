
"""
===============================================================================
TigerPad - SQLAlchemy Model Registration
File: TP_App/models/__init__.py
===============================================================================

Overall Description:
--------------------
This file registers every SQLAlchemy database model used by the TigerPad
backend.

Importing models through this file ensures that SQLAlchemy recognizes all
34 MySQL-backed models, including their relationships, foreign keys,
indexes, and constraints.

Model registration supports:
    1. SQLAlchemy database metadata management
    2. Database relationship resolution
    3. Application startup and model initialization
    4. Database schema inspection and validation
    5. Future database migration support
    6. Faculty review and feedback functionality

The FacultyReview model is included to support faculty evaluations of
student resumes, skills, projects, certifications, and career readiness.

Only current MySQL-backed models are imported here.

Older files scheduled for removal, including:
    - job.py
    - job_match.py
    - interview.py
    - progress.py

are intentionally excluded from model registration.

Important:
----------
This file registers SQLAlchemy models but does not create database tables
or execute migrations.

The corresponding tables must already exist in the TigerPad MySQL database.

===============================================================================
"""


# =============================================================================
# SECTION 1: ACADEMIC AND UNIVERSITY MODELS
# =============================================================================

# Academic programs available to Jackson State University students.
from TP_App.models.academic_program import AcademicProgram

# University colleges and their associated departments.
from TP_App.models.college import College
from TP_App.models.department import Department


# =============================================================================
# SECTION 2: USERS, ROLES, AND AUTHENTICATION MODELS
# =============================================================================

# Authentication tokens used for secure user sessions.
from TP_App.models.auth_token import AuthToken

# Role-based authorization for students, faculty, and administrators.
from TP_App.models.role import Role

# Core user accounts and authentication information.
from TP_App.models.user import User


# =============================================================================
# SECTION 3: STUDENT PROFILE AND ACADEMIC PROGRAM MODELS
# =============================================================================

# Student profile information and academic details.
from TP_App.models.student_profile import StudentProfile

# Associates students with their enrolled academic programs.
from TP_App.models.student_program import StudentProgram


# =============================================================================
# SECTION 4: FACULTY PROFILES, PROGRAM ACCESS, AND REVIEWS
# =============================================================================

# Faculty profile information and student review permissions.
from TP_App.models.faculty_profile import FacultyProfile

# Defines which academic programs faculty members can access.
from TP_App.models.faculty_program_access import FacultyProgramAccess

# Stores faculty evaluations and feedback on student career readiness.
from TP_App.models.faculty_review import FacultyReview


# =============================================================================
# SECTION 5: CAREER PATHS AND INDUSTRY MODELS
# =============================================================================

# Industry categories used to organize career opportunities.
from TP_App.models.industry import Industry

# Career paths available for student exploration.
from TP_App.models.career_path import CareerPath

# Associates career paths with academic programs.
from TP_App.models.career_path_program import CareerPathProgram

# Associates career paths with recommended skills.
from TP_App.models.career_path_skill import CareerPathSkill

# Student career goals and professional objectives.
from TP_App.models.career_goal import CareerGoal


# =============================================================================
# SECTION 6: STUDENT SKILLS AND PROFESSIONAL EXPERIENCE
# =============================================================================

# Master list of professional and technical skills.
from TP_App.models.skill import Skill

# Tracks skills associated with individual students.
from TP_App.models.student_skill import StudentSkill

# Identifies gaps between student skills and career requirements.
from TP_App.models.skill_gap import SkillGap

# Student work experience and professional background.
from TP_App.models.experience import Experience

# Student projects and practical accomplishments.
from TP_App.models.project import Project

# Professional certifications earned by students.
from TP_App.models.certification import Certification


# =============================================================================
# SECTION 7: RESUME AND CAREER READINESS MODELS
# =============================================================================

# Student resume information and stored resume records.
from TP_App.models.resume import Resume

# AI-generated or rule-based resume evaluations.
from TP_App.models.resume_analysis import ResumeAnalysis

# Career readiness evaluations and scoring information.
from TP_App.models.readiness_score import ReadinessScore

# Career development recommendations generated for students.
from TP_App.models.recommendation import Recommendation


# =============================================================================
# SECTION 8: INTERVIEW PREPARATION MODELS
# =============================================================================

# Stores mock interview sessions.
from TP_App.models.interview_session import InterviewSession

# Stores student interview responses and related evaluations.
from TP_App.models.interview_response import InterviewResponse


# =============================================================================
# SECTION 9: CAREER RESOURCES AND PROGRAM ASSOCIATIONS
# =============================================================================

# Career development and educational resources.
from TP_App.models.resource import Resource

# Associates career resources with academic programs.
from TP_App.models.resource_program import ResourceProgram


# =============================================================================
# SECTION 10: STUDENT PROGRESS AND NOTIFICATIONS
# =============================================================================

# Tracks student career-readiness activities and progress.
from TP_App.models.progress_event import ProgressEvent

# Stores notifications delivered to TigerPad users.
from TP_App.models.notification import Notification


# =============================================================================
# SECTION 11: AI ACTIVITY AND SECURITY AUDITING
# =============================================================================

# Records AI requests for monitoring and troubleshooting.
from TP_App.models.ai_request_log import AIRequestLog

# Records important application actions for security and auditing.
from TP_App.models.audit_log import AuditLog


# =============================================================================
# SECTION 12: PUBLIC MODEL EXPORTS
# =============================================================================

# The __all__ list explicitly identifies the models exported by this package.
#
# Including FacultyReview allows other backend modules to import the model
# through TP_App.models after SQLAlchemy registration.
#
# All existing TigerPad model exports are preserved.

__all__ = [
    "AcademicProgram",
    "AIRequestLog",
    "AuditLog",
    "AuthToken",
    "CareerGoal",
    "CareerPath",
    "CareerPathProgram",
    "CareerPathSkill",
    "Certification",
    "College",
    "Department",
    "Experience",
    "FacultyProfile",
    "FacultyProgramAccess",
    "FacultyReview",
    "Industry",
    "InterviewResponse",
    "InterviewSession",
    "Notification",
    "ProgressEvent",
    "Project",
    "ReadinessScore",
    "Recommendation",
    "Resource",
    "ResourceProgram",
    "Resume",
    "ResumeAnalysis",
    "Role",
    "Skill",
    "SkillGap",
    "StudentProfile",
    "StudentProgram",
    "StudentSkill",
    "User",
]
