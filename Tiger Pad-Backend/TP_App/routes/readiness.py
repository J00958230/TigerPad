"""
Overall function:
This file calculates and returns TigerPad readiness scores.

The calculation combines academic progress, career-path skills, experiences,
projects, certifications, and résumé analysis. It also creates skill-gap
records that explain which target skills need additional development.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.career_path import CareerPath
from TP_App.models.career_path_skill import CareerPathSkill
from TP_App.models.certification import Certification
from TP_App.models.experience import Experience
from TP_App.models.project import Project
from TP_App.models.readiness_score import ReadinessScore
from TP_App.models.resume import Resume
from TP_App.models.resume_analysis import ResumeAnalysis
from TP_App.models.skill import Skill
from TP_App.models.skill_gap import SkillGap
from TP_App.models.student_profile import StudentProfile
from TP_App.models.student_skill import StudentSkill
from TP_App.schemas.readiness import (
    ReadinessCalculationRequest,
    ReadinessScoreDetailResponse,
    ReadinessScoreResponse,
)


router = APIRouter(
    prefix="/students/me/readiness",
    tags=["Readiness"],
)


CALCULATION_VERSION = "readiness-v1"

WEIGHTS: dict[str, float] = {
    "academic_score": 0.15,
    "skill_score": 0.25,
    "experience_score": 0.15,
    "project_score": 0.15,
    "certification_score": 0.10,
    "resume_score": 0.20,
}


def _utc_now() -> datetime:
    """Return a timezone-naive UTC datetime for MySQL DATETIME columns."""

    return datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)


def _decimal_score(value: float) -> Decimal:
    """Convert a numeric score to a two-decimal database value."""

    bounded_value = max(0.0, min(100.0, value))
    return Decimal(f"{bounded_value:.2f}")


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
                "Create a student profile before calculating readiness."
            ),
        )

    return student_profile


def _get_career_path(
    db: Session,
    career_path_id: int,
) -> CareerPath:
    """Return an active generalized career path."""

    career_path = db.scalar(
        select(CareerPath).where(
            CareerPath.career_path_id == career_path_id,
            CareerPath.is_active.is_(True),
        )
    )

    if career_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected career path was not found.",
        )

    return career_path


def _get_owned_readiness_score(
    db: Session,
    user_id: int,
    readiness_score_id: int,
) -> ReadinessScore:
    """Return a readiness score only when it belongs to the student."""

    readiness_score = db.scalar(
        select(ReadinessScore)
        .join(
            StudentProfile,
            ReadinessScore.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            ReadinessScore.readiness_score_id == readiness_score_id,
            StudentProfile.user_id == user_id,
        )
    )

    if readiness_score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested readiness score was not found.",
        )

    return readiness_score


def _calculate_academic_score(
    student_profile: StudentProfile,
) -> float:
    """Calculate the academic component from the student's GPA."""

    if student_profile.gpa is None:
        return 0.0

    return min(
        100.0,
        max(0.0, float(student_profile.gpa) / 4.0 * 100.0),
    )


def _calculate_count_score(
    item_count: int,
    first_threshold: int,
    second_threshold: int,
) -> float:
    """Convert a record count into a readiness percentage."""

    if item_count <= 0:
        return 0.0

    if item_count < first_threshold:
        return 40.0

    if item_count < second_threshold:
        return 70.0

    return 100.0


def _build_detail_response(
    readiness_score: ReadinessScore,
    skill_gaps: list[SkillGap],
) -> dict[str, Any]:
    """Build a readiness response containing its skill gaps."""

    return {
        "readiness_score_id": readiness_score.readiness_score_id,
        "student_profile_id": readiness_score.student_profile_id,
        "career_path_id": readiness_score.career_path_id,
        "resume_analysis_id": readiness_score.resume_analysis_id,
        "overall_score": readiness_score.overall_score,
        "academic_score": readiness_score.academic_score,
        "skill_score": readiness_score.skill_score,
        "experience_score": readiness_score.experience_score,
        "project_score": readiness_score.project_score,
        "certification_score": readiness_score.certification_score,
        "resume_score": readiness_score.resume_score,
        "calculation_version": readiness_score.calculation_version,
        "weights_json": readiness_score.weights_json,
        "score_details_json": readiness_score.score_details_json,
        "profile_snapshot_hash": readiness_score.profile_snapshot_hash,
        "is_current": readiness_score.is_current,
        "calculated_at": readiness_score.calculated_at,
        "created_at": readiness_score.created_at,
        "updated_at": readiness_score.updated_at,
        "skill_gaps": skill_gaps,
    }


@router.post(
    "/calculate",
    response_model=ReadinessScoreDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate readiness for a career path",
)
def calculate_readiness(
    payload: ReadinessCalculationRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Calculate and store a readiness score for a generalized career path.

    A new calculation becomes the current score for that student and path.
    """

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    career_path = _get_career_path(
        db=db,
        career_path_id=payload.career_path_id,
    )

    career_path_skills = list(
        db.scalars(
            select(CareerPathSkill).where(
                CareerPathSkill.career_path_id
                == career_path.career_path_id,
                CareerPathSkill.is_active.is_(True),
            )
        ).all()
    )

    student_skills = list(
        db.scalars(
            select(StudentSkill).where(
                StudentSkill.student_profile_id
                == student_profile.student_profile_id,
            )
        ).all()
    )

    experiences = list(
        db.scalars(
            select(Experience).where(
                Experience.student_profile_id
                == student_profile.student_profile_id,
            )
        ).all()
    )

    projects = list(
        db.scalars(
            select(Project).where(
                Project.student_profile_id
                == student_profile.student_profile_id,
            )
        ).all()
    )

    certifications = list(
        db.scalars(
            select(Certification).where(
                Certification.student_profile_id
                == student_profile.student_profile_id,
            )
        ).all()
    )

    # The student's active résumé is the existing primary résumé. Never
    # substitute analysis from a different résumé for this career.
    active_resume = db.scalar(
        select(Resume).where(
            Resume.student_profile_id == student_profile.student_profile_id,
            Resume.is_active.is_(True),
            Resume.is_primary.is_(True),
        )
    )

    latest_resume_analysis = db.scalar(
        select(ResumeAnalysis)
        .join(
            Resume,
            ResumeAnalysis.resume_id == Resume.resume_id,
        )
        .where(
            Resume.student_profile_id
            == student_profile.student_profile_id,
            Resume.is_active.is_(True),
            Resume.resume_id == (active_resume.resume_id if active_resume else -1),
            ResumeAnalysis.career_path_id
            == career_path.career_path_id,
            ResumeAnalysis.analysis_status == "completed",
        )
        .order_by(
            ResumeAnalysis.completed_at.desc(),
            ResumeAnalysis.created_at.desc(),
        )
        .limit(1)
    )

    skills_by_id = {
        student_skill.skill_id: student_skill
        for student_skill in student_skills
    }

    target_skill_ids = {
        career_path_skill.skill_id
        for career_path_skill in career_path_skills
    }

    target_skills_by_id: dict[int, Skill] = {}

    if target_skill_ids:
        target_skills = list(
            db.scalars(
                select(Skill).where(
                    Skill.skill_id.in_(target_skill_ids),
                )
            ).all()
        )

        target_skills_by_id = {
            skill.skill_id: skill
            for skill in target_skills
        }

    weighted_skill_total = 0.0
    total_importance = 0.0
    skill_gap_values: list[dict[str, Any]] = []

    for career_path_skill in career_path_skills:
        target_level = career_path_skill.target_proficiency_level
        importance_level = career_path_skill.importance_level

        student_skill = skills_by_id.get(
            career_path_skill.skill_id,
        )

        current_level = (
            student_skill.proficiency_level
            if student_skill is not None
            else 0
        )

        if target_level > 0:
            proficiency_ratio = min(
                1.0,
                current_level / target_level,
            )
        else:
            proficiency_ratio = 1.0

        weighted_skill_total += (
            proficiency_ratio * importance_level
        )
        total_importance += importance_level

        gap_size = max(
            0,
            target_level - current_level,
        )

        priority_score = _decimal_score(
            min(
                100.0,
                gap_size * importance_level * 4.0,
            )
        )

        skill = target_skills_by_id.get(
            career_path_skill.skill_id,
        )

        skill_name = (
            skill.name
            if skill is not None
            else "this target skill"
        )

        if gap_size == 0:
            gap_status = "resolved"
            recommendation = (
                f"Maintain your current proficiency in {skill_name}."
            )
        else:
            gap_status = "open"
            recommendation = (
                f"Build proficiency in {skill_name} through coursework, "
                "projects, certifications, or practical experience."
            )

        skill_gap_values.append(
            {
                "career_path_skill_id": (
                    career_path_skill.career_path_skill_id
                ),
                "student_skill_id": (
                    student_skill.student_skill_id
                    if student_skill is not None
                    else None
                ),
                "current_proficiency_level": current_level,
                "target_proficiency_level": target_level,
                "importance_level": importance_level,
                "gap_size": gap_size,
                "priority_score": priority_score,
                "gap_status": gap_status,
                "recommend_action": recommendation,
            }
        )

    skill_score = (
        weighted_skill_total / total_importance * 100.0
        if total_importance > 0
        else 0.0
    )

    academic_score = _calculate_academic_score(
        student_profile,
    )

    experience_score = _calculate_count_score(
        item_count=len(experiences),
        first_threshold=2,
        second_threshold=4,
    )

    project_score = _calculate_count_score(
        item_count=len(projects),
        first_threshold=2,
        second_threshold=4,
    )

    certification_score = _calculate_count_score(
        item_count=len(certifications),
        first_threshold=1,
        second_threshold=3,
    )

    resume_score = (
        float(latest_resume_analysis.overall_score)
        if latest_resume_analysis is not None
        and latest_resume_analysis.overall_score is not None
        else 0.0
    )

    overall_score = (
        academic_score * WEIGHTS["academic_score"]
        + skill_score * WEIGHTS["skill_score"]
        + experience_score * WEIGHTS["experience_score"]
        + project_score * WEIGHTS["project_score"]
        + certification_score * WEIGHTS["certification_score"]
        + resume_score * WEIGHTS["resume_score"]
    )

    snapshot_data = {
        "student_profile_id": student_profile.student_profile_id,
        "gpa": str(student_profile.gpa),
        "career_path_id": career_path.career_path_id,
        "student_skill_ids": sorted(
            skill.student_skill_id
            for skill in student_skills
        ),
        "experience_ids": sorted(
            experience.experience_id
            for experience in experiences
        ),
        "project_ids": sorted(
            project.project_id
            for project in projects
        ),
        "certification_ids": sorted(
            certification.certification_id
            for certification in certifications
        ),
        "active_resume_id": active_resume.resume_id if active_resume else None,
        "resume_analysis_id": (
            latest_resume_analysis.resume_analysis_id
            if latest_resume_analysis is not None
            else None
        ),
    }

    profile_snapshot_hash = hashlib.sha256(
        json.dumps(
            snapshot_data,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()

    score_details = {
        "active_resume_id": active_resume.resume_id if active_resume else None,
        "resume_analysis_available": latest_resume_analysis is not None,
        "career_path_name": career_path.name,
        "career_path_code": career_path.career_path_code,
        "student_skill_count": len(student_skills),
        "target_skill_count": len(career_path_skills),
        "experience_count": len(experiences),
        "project_count": len(projects),
        "certification_count": len(certifications),
        "skill_gap_count": sum(
            1
            for gap in skill_gap_values
            if gap["gap_size"] > 0
        ),
    }

    db.execute(
        update(ReadinessScore)
        .where(
            ReadinessScore.student_profile_id
            == student_profile.student_profile_id,
            ReadinessScore.career_path_id
            == career_path.career_path_id,
            ReadinessScore.is_current.is_(True),
        )
        .values(is_current=False)
    )

    readiness_score = ReadinessScore(
        student_profile_id=student_profile.student_profile_id,
        career_path_id=career_path.career_path_id,
        resume_analysis_id=(
            latest_resume_analysis.resume_analysis_id
            if latest_resume_analysis is not None
            else None
        ),
        overall_score=_decimal_score(overall_score),
        academic_score=_decimal_score(academic_score),
        skill_score=_decimal_score(skill_score),
        experience_score=_decimal_score(experience_score),
        project_score=_decimal_score(project_score),
        certification_score=_decimal_score(certification_score),
        resume_score=_decimal_score(resume_score),
        calculation_version=CALCULATION_VERSION,
        weights_json=WEIGHTS,
        score_details_json=score_details,
        profile_snapshot_hash=profile_snapshot_hash,
        is_current=True,
        calculated_at=_utc_now(),
    )

    db.add(readiness_score)
    db.flush()

    for gap_values in skill_gap_values:
        db.add(
            SkillGap(
                readiness_score_id=readiness_score.readiness_score_id,
                career_path_skill_id=gap_values[
                    "career_path_skill_id"
                ],
                student_skill_id=gap_values[
                    "student_skill_id"
                ],
                current_proficiency_level=gap_values[
                    "current_proficiency_level"
                ],
                target_proficiency_level=gap_values[
                    "target_proficiency_level"
                ],
                importance_level=gap_values[
                    "importance_level"
                ],
                gap_size=gap_values["gap_size"],
                priority_score=gap_values["priority_score"],
                gap_status=gap_values["gap_status"],
                recommend_action=gap_values[
                    "recommend_action"
                ],
            )
        )

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The readiness score could not be saved.",
        ) from error

    db.refresh(readiness_score)

    saved_skill_gaps = list(
        db.scalars(
            select(SkillGap).where(
                SkillGap.readiness_score_id
                == readiness_score.readiness_score_id,
            )
        ).all()
    )

    return _build_detail_response(
        readiness_score=readiness_score,
        skill_gaps=saved_skill_gaps,
    )


@router.get(
    "",
    response_model=list[ReadinessScoreResponse],
    summary="List student readiness scores",
)
def list_readiness_scores(
    career_path_id: int | None = Query(default=None, gt=0),
    current_only: bool = Query(default=True),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[ReadinessScore]:
    """Return readiness scores belonging to the authenticated student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = select(ReadinessScore).where(
        ReadinessScore.student_profile_id
        == student_profile.student_profile_id,
    )

    if career_path_id is not None:
        query = query.where(
            ReadinessScore.career_path_id == career_path_id,
        )

    if current_only:
        query = query.where(
            ReadinessScore.is_current.is_(True),
        )

    query = query.order_by(
        ReadinessScore.calculated_at.desc(),
    )

    return list(db.scalars(query).all())


@router.get(
    "/{readiness_score_id}",
    response_model=ReadinessScoreDetailResponse,
    summary="Get a readiness score and skill gaps",
)
def get_readiness_score(
    readiness_score_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return one readiness score and its associated skill gaps."""

    readiness_score = _get_owned_readiness_score(
        db=db,
        user_id=int(current_user["user_id"]),
        readiness_score_id=readiness_score_id,
    )

    skill_gaps = list(
        db.scalars(
            select(SkillGap).where(
                SkillGap.readiness_score_id
                == readiness_score.readiness_score_id,
            )
        ).all()
    )

    return _build_detail_response(
        readiness_score=readiness_score,
        skill_gaps=skill_gaps,
    )