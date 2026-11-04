"""
TigerPad — Authenticated Resume Analysis API Routes
==================================================

Overall function:
    Provides student-only FastAPI endpoints for evaluating resumes,
    reviewing previous analyses, suggesting career matches, and
    previewing a suggested resume draft when requested.

How this file fits into TigerPad:
    - The frontend (App.jsx) calls these routes through /api/students/me/resumes.
    - Authentication uses require_student; students must not access
      another student's resume or analysis records.
    - Resume metadata and analysis results are read from / written to
      the existing MySQL database using SQLAlchemy.
    - TP_App.services.resume_analyzer extracts resume content and
      performs AI or rules-based analysis; this route file orchestrates
      requests, validation, persistence, and API responses.
    - Career paths come from TigerPad's approved career-path records.

Key workflows:
    1. Career matching: suggest relevant approved career paths and
       allow the student to select a target path for their resume.
    2. Analysis: analyze an owned resume and store scores, strengths,
       improvements, and section-specific feedback.
    3. History: list or retrieve previous resume analysis results.
    4. Draft preview: assemble a suggested resume from the student's
       available profile records, without changing an uploaded original.

Important safeguards:
    - Keep ownership checks and require_student on protected routes.
    - Do not fabricate credentials, employment, project results, or skills.
    - Distinguish resume quality scores from career readiness scores.
    - Preserve existing endpoints and their response contracts.
    - Keep these explanatory comments when updating this file.
"""

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.career_path import CareerPath
from TP_App.models.resume import Resume
from TP_App.models.resume_analysis import ResumeAnalysis
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.resume import (
    CareerMatchRequest,
    CareerMatchResponse,
    CareerMatchSelectionRequest,
    CareerMatchSelectionResponse,
    ResumeAnalysisRequest,
    ResumeAnalysisResponse,
)
from TP_App.services.career_matcher import suggest_career_matches
from TP_App.services.resume_analyzer import (
    analyze_resume as run_resume_analysis,
    prepare_resume_input,
)


router = APIRouter(
    prefix="/students/me/resumes",
    tags=["Résumé Analysis"],
)


def _utc_now() -> datetime:
    return datetime.now(
        ZoneInfo("UTC")
    ).replace(
        tzinfo=None
    )


def _get_owned_resume(
    db: Session,
    user_id: int,
    resume_id: int,
) -> Resume:
    resume = db.scalar(
        select(Resume)
        .join(
            StudentProfile,
            Resume.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            Resume.resume_id == resume_id,
            StudentProfile.user_id == user_id,
            Resume.is_active.is_(True),
        )
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested résumé was not found.",
        )

    return resume


def _get_owned_analysis(
    db: Session,
    user_id: int,
    resume_id: int,
    resume_analysis_id: int,
) -> ResumeAnalysis:
    analysis = db.scalar(
        select(ResumeAnalysis)
        .join(
            Resume,
            ResumeAnalysis.resume_id
            == Resume.resume_id,
        )
        .join(
            StudentProfile,
            Resume.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            ResumeAnalysis.resume_analysis_id
            == resume_analysis_id,
            ResumeAnalysis.resume_id == resume_id,
            StudentProfile.user_id == user_id,
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested résumé analysis was not found.",
        )

    return analysis


def _get_career_path(
    db: Session,
    career_path_id: int | None,
) -> CareerPath | None:
    if career_path_id is None:
        return None

    career_path = db.scalar(
        select(CareerPath).where(
            CareerPath.career_path_id == career_path_id,
            CareerPath.is_active.is_(True),
        )
    )

    if career_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "The selected career path does not exist "
                "or is inactive."
            ),
        )

    return career_path


def _fallback_input_hash(
    resume: Resume,
) -> str:
    fallback_text = (
        f"{resume.resume_id}:"
        f"{resume.title}:"
        f"{resume.updated_at.isoformat() if resume.updated_at else ''}"
    )

    return hashlib.sha256(
        fallback_text.encode("utf-8")
    ).hexdigest()




# Student-specific résumé draft preview. This endpoint does not modify the
# uploaded résumé or create a database record until the student chooses to save.
@router.post(
    "/draft-preview",
    summary="Build a fact-grounded résumé draft from the student profile",
)
def build_resume_draft_preview(
    career_path_id: int | None = None,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from TP_App.models.user import User
    from TP_App.models.student_skill import StudentSkill
    from TP_App.models.skill import Skill
    from TP_App.models.experience import Experience
    from TP_App.models.project import Project
    from TP_App.models.certification import Certification

    user_id = int(current_user["user_id"])
    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Create your student profile first.")

    user = db.scalar(select(User).where(User.user_id == user_id))
    career = _get_career_path(db, career_path_id) if career_path_id else None
    profile_id = profile.student_profile_id

    def value(obj: Any, *names: str) -> str:
        for name in names:
            item = getattr(obj, name, None) if obj is not None else None
            if item is not None and str(item).strip():
                return str(item).strip()
        return ""

    name = " ".join(filter(None, [value(user, "first_name"), value(user, "last_name")]))
    skills = []
    for student_skill in db.scalars(
        select(StudentSkill).where(StudentSkill.student_profile_id == profile_id)
    ).all():
        skill = db.scalar(select(Skill).where(Skill.skill_id == student_skill.skill_id))
        label = value(skill, "name")
        if label and label not in skills:
            skills.append(label)

    def records(model: Any, fields: tuple[str, ...], limit: int = 25) -> list[dict[str, Any]]:
        rows = db.scalars(
            select(model).where(model.student_profile_id == profile_id).limit(limit)
        ).all()
        return [
            {field: value(row, field) for field in fields if value(row, field)}
            for row in rows
        ]

    experiences = records(Experience, (
        "job_title", "title", "organization_name", "company_name", "employer",
        "location", "start_date", "end_date", "description", "responsibilities",
        "achievements", "is_current",
    ))
    projects = records(Project, (
        "title", "name", "description", "technologies", "outcome",
        "start_date", "end_date", "project_url", "github_url",
    ))
    certifications = records(Certification, (
        "name", "issuer", "issuing_organization", "issued_date", "expiration_date",
        "credential_id",
    ))

    education = {
        "institution": "Jackson State University",
        "major": value(profile, "major"),
        "academic_level": value(profile, "academic_level"),
        "expected_graduation_date": value(profile, "expected_graduation_date", "expected_grad_date"),
        "gpa": value(profile, "gpa"),
    }
    headline = value(profile, "professional_headline")
    summary = value(profile, "bio") or headline
    if not summary:
        summary = (
            "Student developing experience through the projects, skills, "
            "and activities documented below."
        )

    draft = {
        "name": name or "Name not provided",
        "email": value(user, "jsu_email", "email"),
        "headline": headline,
        "summary": summary,
        "career_focus": career.name if career else "General career readiness",
        "education": education,
        "skills": skills,
        "experiences": experiences,
        "projects": projects,
        "certifications": certifications,
    }
    missing = []
    if not name:
        missing.append("Add your name to your account.")
    if not skills:
        missing.append("Add skills to your student profile.")
    if not experiences:
        missing.append("Add internship, work, volunteer, or leadership experience.")
    if not projects:
        missing.append("Add projects and describe your personal contributions.")
    if not summary or summary.startswith("Student developing"):
        missing.append("Add a professional summary or profile bio.")

    return {
        "draft": draft,
        "missing_information": missing,
        "source": "student_profile",
        "is_ai_generated": False,
        "notice": (
            "This fact-grounded suggested résumé is assembled from your "
            "TigerPad profile. Review it before saving or sharing. "
            "No qualifications or achievements have been invented."
        ),
    }


@router.post(
    "/{resume_id}/career-matches",
    response_model=list[CareerMatchResponse],
    summary="Suggest possible career paths for a résumé",
)
def suggest_resume_career_matches(
    resume_id: int,
    payload: CareerMatchRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[CareerMatchResponse]:
    """
    Return several active career paths for student review.

    The AI only ranks career-path codes supplied by the database. Official
    descriptions and education guidance come from CareerPath rows.
    """

    resume = _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )

    career_paths = list(
        db.scalars(
            select(CareerPath)
            .where(
                CareerPath.is_active.is_(True)
            )
            .order_by(
                CareerPath.name.asc()
            )
        ).all()
    )

    if not career_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No active career paths are available "
                "for matching."
            ),
        )

    try:
        matching_result = suggest_career_matches(
            resume=resume,
            career_paths=career_paths,
            requested_method=payload.analysis_method,
            limit=payload.limit,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "TigerPad could not suggest career paths right now. "
                "Try hybrid matching again later."
            ),
        ) from error

    career_paths_by_code = {
        str(path.career_path_code)
        .strip()
        .upper(): path
        for path in career_paths
    }

    response: list[CareerMatchResponse] = []

    for match in matching_result.get(
        "matches",
        [],
    ):
        code = str(
            match.get(
                "career_path_code",
                "",
            )
        ).strip().upper()

        career_path = career_paths_by_code.get(code)

        if career_path is None:
            continue

        response.append(
            CareerMatchResponse(
                career_path_id=career_path.career_path_id,
                career_path_code=career_path.career_path_code,
                name=career_path.name,
                primary_focus=(
                    career_path.description
                    or (
                        "A generalized career direction "
                        "related to this path."
                    )
                ),
                typical_education_level=(
                    career_path.typical_education_level
                ),
                confidence_score=Decimal(
                    str(
                        match.get(
                            "confidence_score",
                            0,
                        )
                    )
                ),
                reason=str(
                    match.get(
                        "reason",
                        "Review this career option.",
                    )
                ).strip()[:500],
            )
        )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "TigerPad did not return valid "
                "career-path matches."
            ),
        )

    return response


@router.post(
    "/{resume_id}/career-matches/select",
    response_model=CareerMatchSelectionResponse,
    summary="Select a career path for a résumé",
)
def select_resume_career_path(
    resume_id: int,
    payload: CareerMatchSelectionRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> CareerMatchSelectionResponse:
    """
    Save the student's confirmed career-path choice.
    """

    resume = _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )

    career_path = _get_career_path(
        db=db,
        career_path_id=payload.career_path_id,
    )

    if career_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected career path was not found.",
        )

    resume.career_path_id = (
        career_path.career_path_id
    )

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The career path could not be saved "
                "to this résumé."
            ),
        ) from error

    return CareerMatchSelectionResponse(
        resume_id=resume.resume_id,
        career_path_id=career_path.career_path_id,
        career_path_name=career_path.name,
        message=(
            f"{career_path.name} was selected. "
            "You can now analyze this résumé."
        ),
    )


@router.get(
    "/{resume_id}/analyses",
    response_model=list[ResumeAnalysisResponse],
    summary="List résumé analyses",
)
def list_resume_analyses(
    resume_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[ResumeAnalysis]:
    _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )

    query = (
        select(ResumeAnalysis)
        .where(
            ResumeAnalysis.resume_id == resume_id
        )
        .order_by(
            ResumeAnalysis.created_at.desc()
        )
    )

    return list(
        db.scalars(query).all()
    )


@router.post(
    "/{resume_id}/analyze",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a student résumé",
)
def analyze_student_resume(
    resume_id: int,
    payload: ResumeAnalysisRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> ResumeAnalysis:
    resume = _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )

    selected_career_path_id = (
        payload.career_path_id
        if payload.career_path_id is not None
        else resume.career_path_id
    )

    career_path = _get_career_path(
        db=db,
        career_path_id=selected_career_path_id,
    )

    started_at = _utc_now()

    try:
        analysis_result = run_resume_analysis(
            resume=resume,
            career_path_name=(
                career_path.name
                if career_path is not None
                else None
            ),
            career_path_description=(
                career_path.description
                if career_path is not None
                else None
            ),
            requested_method=payload.analysis_method,
        )

        analysis = ResumeAnalysis(
            resume_id=resume.resume_id,
            career_path_id=selected_career_path_id,
            analysis_status="completed",
            analysis_method=(
                analysis_result["analysis_method"]
            ),
            overall_score=Decimal(
                str(
                    analysis_result["overall_score"]
                )
            ),
            content_score=Decimal(
                str(
                    analysis_result["content_score"]
                )
            ),
            format_score=Decimal(
                str(
                    analysis_result["format_score"]
                )
            ),
            impact_score=Decimal(
                str(
                    analysis_result["impact_score"]
                )
            ),
            career_alignment_score=Decimal(
                str(
                    analysis_result[
                        "career_alignment_score"
                    ]
                )
            ),
            summary=analysis_result["summary"],
            strengths_json=analysis_result[
                "strengths_json"
            ],
            improvements_json=analysis_result[
                "improvements_json"
            ],
            section_feedback_json=analysis_result[
                "section_feedback_json"
            ],
            model_name=analysis_result["model_name"],
            prompt_version=analysis_result[
                "prompt_version"
            ],
            input_sha256_hash=analysis_result[
                "input_sha256_hash"
            ],
            error_message=None,
            started_at=started_at,
            completed_at=_utc_now(),
        )

    except Exception as error:
        try:
            _, input_hash = prepare_resume_input(
                resume
            )
        except Exception:
            input_hash = _fallback_input_hash(
                resume
            )

        failed_analysis = ResumeAnalysis(
            resume_id=resume.resume_id,
            career_path_id=selected_career_path_id,
            analysis_status="failed",
            analysis_method=payload.analysis_method,
            input_sha256_hash=input_hash,
            error_message="Résumé analysis failed.",
            started_at=started_at,
            completed_at=_utc_now(),
        )

        db.add(failed_analysis)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "TigerPad could not complete résumé analysis. "
                "Try hybrid analysis or try again later."
            ),
        ) from error

    db.add(analysis)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The résumé analysis could not be saved."
            ),
        ) from error

    db.refresh(analysis)

    return analysis


@router.get(
    "/{resume_id}/analyses/{resume_analysis_id}",
    response_model=ResumeAnalysisResponse,
    summary="Get one résumé analysis",
)
def get_resume_analysis(
    resume_id: int,
    resume_analysis_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> ResumeAnalysis:
    return _get_owned_analysis(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
        resume_analysis_id=resume_analysis_id,
    )