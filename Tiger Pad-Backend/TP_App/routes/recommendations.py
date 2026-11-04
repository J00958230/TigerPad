"""
Overall function:
This file provides authenticated TigerPad recommendation routes.

Recommendations are generated from the student's current readiness score,
career-path skill gaps, résumé score, and development data. Students can view,
complete, or dismiss recommendations that belong to their own profile.

When a recommendation is completed, TigerPad automatically creates:
1. A progress timeline event.
2. An in-app notification.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.career_path_skill import CareerPathSkill
from TP_App.models.notification import Notification
from TP_App.models.progress_event import ProgressEvent
from TP_App.models.readiness_score import ReadinessScore
from TP_App.models.recommendation import Recommendation
from TP_App.models.skill import Skill
from TP_App.models.skill_gap import SkillGap
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.recommendation import (
    RecommendationResponse,
    RecommendationUpdateRequest,
)


router = APIRouter(
    prefix="/students/me/recommendations",
    tags=["Recommendations"],
)


def _utc_now() -> datetime:
    """Return a timezone-naive UTC datetime for MySQL DATETIME columns."""

    return datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)


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
                "Create a student profile before managing recommendations."
            ),
        )

    return student_profile


def _get_owned_recommendation(
    db: Session,
    user_id: int,
    recommendation_id: int,
) -> Recommendation:
    """Return a recommendation only when it belongs to the student."""

    recommendation = db.scalar(
        select(Recommendation)
        .join(
            StudentProfile,
            Recommendation.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            Recommendation.recommendation_id == recommendation_id,
            StudentProfile.user_id == user_id,
        )
    )

    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested recommendation was not found.",
        )

    return recommendation


def _priority_level(priority_score: float) -> int:
    """Convert a skill-gap priority score into a recommendation priority."""

    if priority_score >= 70:
        return 1

    if priority_score >= 40:
        return 2

    return 3


def _completion_event_exists(
    db: Session,
    recommendation: Recommendation,
) -> bool:
    """
    Check whether a progress event already references this recommendation.

    This prevents duplicate progress events when the completion request is
    submitted more than once.
    """

    existing_event = db.scalar(
        select(ProgressEvent).where(
            ProgressEvent.student_profile_id
            == recommendation.student_profile_id,
            ProgressEvent.related_entity_type == "recommendations",
            ProgressEvent.related_entity_id
            == recommendation.recommendation_id,
        )
    )

    return existing_event is not None


def _create_completion_event(
    db: Session,
    recommendation: Recommendation,
    occurred_at: datetime,
) -> None:
    """Create a system-generated progress event."""

    if _completion_event_exists(db, recommendation):
        return

    progress_event = ProgressEvent(
        student_profile_id=recommendation.student_profile_id,
        career_path_id=recommendation.career_path_id,
        event_type="recommendation_completed",
        title=f"Completed {recommendation.title}"[:200],
        description=(
            "Completed a TigerPad recommendation: "
            f"{recommendation.title}."
        ),
        related_entity_type="recommendations",
        related_entity_id=recommendation.recommendation_id,
        event_data_json={
            "recommendation_type": recommendation.recommendation_type,
            "priority_level": recommendation.priority_level,
            "source_type": recommendation.source_type,
        },
        source_type="system",
        is_visible_to_student=1,
        occurred_at=occurred_at,
    )

    db.add(progress_event)


def _completion_notification_exists(
    db: Session,
    user_id: int,
    recommendation: Recommendation,
) -> bool:
    """Check whether a completion notification already exists."""

    existing_notification = db.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.notification_type == "recommendation",
            Notification.related_entity_type == "recommendations",
            Notification.related_entity_id
            == recommendation.recommendation_id,
        )
    )

    return existing_notification is not None


def _create_completion_notification(
    db: Session,
    user_id: int,
    recommendation: Recommendation,
) -> None:
    """Create an in-app notification for a completed recommendation."""

    if _completion_notification_exists(
        db=db,
        user_id=user_id,
        recommendation=recommendation,
    ):
        return

    notification = Notification(
        user_id=user_id,
        notification_type="recommendation",
        title="Recommendation completed",
        message=(
            f"You completed the TigerPad recommendation: "
            f"{recommendation.title}."
        ),
        action_url=None,
        related_entity_type="recommendations",
        related_entity_id=recommendation.recommendation_id,
        priority_level=recommendation.priority_level,
        delivery_channel="in_app",
        delivery_status="sent",
        is_read=0,
    )

    db.add(notification)


@router.get(
    "",
    response_model=list[RecommendationResponse],
    summary="List student recommendations",
)
def list_recommendations(
    recommendation_status: str = Query(
        default="active",
        alias="status",
        max_length=20,
    ),
    career_path_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Recommendation]:
    """Return recommendations belonging to the authenticated student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = select(Recommendation).where(
        Recommendation.student_profile_id
        == student_profile.student_profile_id,
        Recommendation.status == recommendation_status,
    )

    if career_path_id is not None:
        query = query.where(
            Recommendation.career_path_id == career_path_id,
        )

    query = (
        query.order_by(
            Recommendation.priority_level.asc(),
            Recommendation.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(query).all())


@router.post(
    "/generate",
    response_model=list[RecommendationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate recommendations from readiness data",
)
def generate_recommendations(
    career_path_id: int | None = Query(default=None, gt=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Recommendation]:
    """
    Generate recommendations from the student's current readiness score.

    Existing active recommendations for the same readiness score are reused,
    so calling this endpoint repeatedly does not create duplicates.
    """

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    readiness_query = select(ReadinessScore).where(
        ReadinessScore.student_profile_id
        == student_profile.student_profile_id,
        ReadinessScore.is_current.is_(True),
    )

    if career_path_id is not None:
        readiness_query = readiness_query.where(
            ReadinessScore.career_path_id == career_path_id,
        )

    readiness_score = db.scalar(
        readiness_query.order_by(
            ReadinessScore.calculated_at.desc(),
        ).limit(1)
    )

    if readiness_score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Calculate a readiness score before generating "
                "recommendations."
            ),
        )

    skill_gaps = list(
        db.scalars(
            select(SkillGap)
            .where(
                SkillGap.readiness_score_id
                == readiness_score.readiness_score_id,
                SkillGap.gap_status == "open",
            )
            .order_by(
                SkillGap.priority_score.desc(),
            )
        ).all()
    )

    existing_recommendations = list(
        db.scalars(
            select(Recommendation).where(
                Recommendation.student_profile_id
                == student_profile.student_profile_id,
                Recommendation.readiness_score_id
                == readiness_score.readiness_score_id,
                Recommendation.status == "active",
            )
        ).all()
    )

    existing_by_skill_gap = {
        recommendation.skill_gap_id: recommendation
        for recommendation in existing_recommendations
        if recommendation.skill_gap_id is not None
    }

    generated_recommendations = list(existing_recommendations)

    for skill_gap in skill_gaps:
        if skill_gap.skill_gap_id in existing_by_skill_gap:
            continue

        career_path_skill = db.scalar(
            select(CareerPathSkill).where(
                CareerPathSkill.career_path_skill_id
                == skill_gap.career_path_skill_id,
            )
        )

        skill = None

        if career_path_skill is not None:
            skill = db.scalar(
                select(Skill).where(
                    Skill.skill_id == career_path_skill.skill_id,
                )
            )

        skill_name = (
            skill.name
            if skill is not None
            else "the identified target skill"
        )

        priority_score = float(skill_gap.priority_score)

        recommendation = Recommendation(
            student_profile_id=student_profile.student_profile_id,
            career_path_id=readiness_score.career_path_id,
            readiness_score_id=readiness_score.readiness_score_id,
            skill_gap_id=skill_gap.skill_gap_id,
            recommendation_type="skill_gap",
            title=f"Build {skill_name}",
            description=(
                skill_gap.recommend_action
                or (
                    f"Improve your proficiency in {skill_name} "
                    "for your selected career path."
                )
            ),
            action_text=(
                "Add coursework, a project, certification, or experience "
                "that demonstrates this skill."
            ),
            priority_level=_priority_level(priority_score),
            source_type="rules",
            status="active",
        )

        db.add(recommendation)
        generated_recommendations.append(recommendation)

    if float(readiness_score.resume_score) < 70:
        existing_resume_recommendation = db.scalar(
            select(Recommendation).where(
                Recommendation.student_profile_id
                == student_profile.student_profile_id,
                Recommendation.readiness_score_id
                == readiness_score.readiness_score_id,
                Recommendation.recommendation_type
                == "resume_improvement",
                Recommendation.status == "active",
            )
        )

        if existing_resume_recommendation is None:
            resume_recommendation = Recommendation(
                student_profile_id=student_profile.student_profile_id,
                career_path_id=readiness_score.career_path_id,
                readiness_score_id=readiness_score.readiness_score_id,
                recommendation_type="resume_improvement",
                title="Improve your résumé",
                description=(
                    "Your résumé score indicates that additional detail, "
                    "formatting, measurable outcomes, or career alignment "
                    "could improve your readiness."
                ),
                action_text=(
                    "Review your latest résumé analysis and update it."
                ),
                priority_level=2,
                source_type="rules",
                status="active",
            )

            db.add(resume_recommendation)
            generated_recommendations.append(resume_recommendation)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recommendations could not be generated.",
        ) from error

    for recommendation in generated_recommendations:
        db.refresh(recommendation)

    return sorted(
        generated_recommendations,
        key=lambda recommendation: (
            recommendation.priority_level,
            recommendation.created_at,
        ),
    )


@router.patch(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="Update recommendation status",
)
def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Recommendation:
    """
    Mark a recommendation active, completed, dismissed, or expired.

    Completing a recommendation automatically creates a progress event and
    an in-app notification.
    """

    user_id = int(current_user["user_id"])

    recommendation = _get_owned_recommendation(
        db=db,
        user_id=user_id,
        recommendation_id=recommendation_id,
    )

    now = _utc_now()

    recommendation.status = payload.status

    if payload.status == "completed":
        recommendation.completed_at = now
        recommendation.dismissed_at = None
        recommendation.expired_at = None

        _create_completion_event(
            db=db,
            recommendation=recommendation,
            occurred_at=now,
        )

        _create_completion_notification(
            db=db,
            user_id=user_id,
            recommendation=recommendation,
        )

    elif payload.status == "dismissed":
        recommendation.dismissed_at = now
        recommendation.completed_at = None
        recommendation.expired_at = None

    elif payload.status == "expired":
        recommendation.expired_at = now
        recommendation.completed_at = None
        recommendation.dismissed_at = None

    else:
        recommendation.completed_at = None
        recommendation.dismissed_at = None
        recommendation.expired_at = None

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The recommendation update could not be saved.",
        ) from error

    db.refresh(recommendation)

    return recommendation