"""
Overall function:
This file provides authenticated TigerPad mock-interview endpoints.

Students can create interview sessions, generate questions, submit answers,
replace questions, evaluate responses with Groq, review feedback, and complete
interview sessions. Completing an interview creates a progress event and an
in-app notification.

TigerPad supports students from every JSU academic discipline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.career_path import CareerPath
from TP_App.models.interview_response import InterviewResponse
from TP_App.models.interview_session import InterviewSession
from TP_App.models.notification import Notification
from TP_App.models.progress_event import ProgressEvent
from TP_App.models.resume import Resume
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.interview import (
    InterviewResponseCreateRequest,
    InterviewResponseResponse,
    InterviewResponseUpdateRequest,
    InterviewSessionCreateRequest,
    InterviewSessionDetailResponse,
    InterviewSessionResponse,
)
from TP_App.services.interview_ai import (
    evaluate_interview_response,
    generate_interview_question,
)


router = APIRouter(
    prefix="/students/me/interviews",
    tags=["Mock Interviews"],
)


def _utc_now() -> datetime:
    """Return a timezone-naive UTC datetime for MySQL DATETIME columns."""

    return datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)


def _get_student_profile(
    db: Session,
    user_id: int,
) -> StudentProfile:
    """Return the authenticated student's profile."""

    student_profile = db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == user_id,
        )
    )

    if student_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Create a student profile before using mock interviews."
            ),
        )

    return student_profile


def _get_owned_session(
    db: Session,
    user_id: int,
    interview_session_id: int,
) -> InterviewSession:
    """Return an interview session owned by the authenticated student."""

    interview_session = db.scalar(
        select(InterviewSession)
        .join(
            StudentProfile,
            InterviewSession.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            InterviewSession.interview_session_id
            == interview_session_id,
            StudentProfile.user_id == user_id,
        )
    )

    if interview_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested interview session was not found.",
        )

    return interview_session


def _get_owned_response(
    db: Session,
    user_id: int,
    interview_session_id: int,
    interview_response_id: int,
) -> InterviewResponse:
    """Return an interview response owned by the authenticated student."""

    interview_response = db.scalar(
        select(InterviewResponse)
        .join(
            InterviewSession,
            InterviewResponse.interview_session_id
            == InterviewSession.interview_session_id,
        )
        .join(
            StudentProfile,
            InterviewSession.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            InterviewResponse.interview_response_id
            == interview_response_id,
            InterviewResponse.interview_session_id
            == interview_session_id,
            StudentProfile.user_id == user_id,
        )
    )

    if interview_response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested interview response was not found.",
        )

    return interview_response


def _get_career_context(
    db: Session,
    career_path_id: int | None,
) -> tuple[str | None, str | None]:
    """Return the selected career path name and description."""

    if career_path_id is None:
        return None, None

    career_path = db.scalar(
        select(CareerPath).where(
            CareerPath.career_path_id == career_path_id,
        )
    )

    if career_path is None:
        return None, None

    return career_path.name, career_path.description


def _next_response_id(db: Session) -> int:
    """Return the next interview-response identifier."""

    next_id = db.scalar(
        select(
            func.coalesce(
                func.max(InterviewResponse.interview_response_id),
                0,
            )
            + 1
        )
    )

    return int(next_id or 1)


def _calculate_overall_score(
    db: Session,
    session: InterviewSession,
) -> float | None:
    """Calculate the average score for all evaluated responses."""

    responses = list(
        db.scalars(
            select(InterviewResponse).where(
                InterviewResponse.interview_session_id
                == session.interview_session_id,
            )
        ).all()
    )

    scores = [
        float(response.response_score)
        for response in responses
        if response.response_score is not None
    ]

    if not scores:
        return None

    overall_score = round(sum(scores) / len(scores), 2)
    session.overall_score = overall_score

    return overall_score


def _session_detail(
    session: InterviewSession,
    responses: list[InterviewResponse],
) -> InterviewSessionDetailResponse:
    """Build a session response with all recorded responses."""

    session_response = InterviewSessionResponse.model_validate(session)

    response_items = [
        InterviewResponseResponse.model_validate(response)
        for response in responses
    ]

    return InterviewSessionDetailResponse(
        **session_response.model_dump(),
        responses=response_items,
    )


def _create_completion_records(
    db: Session,
    user_id: int,
    session: InterviewSession,
    completed_at: datetime,
) -> None:
    """Create progress and notification records after completion."""

    existing_event = db.scalar(
        select(ProgressEvent).where(
            ProgressEvent.student_profile_id
            == session.student_profile_id,
            ProgressEvent.related_entity_type == "interview_sessions",
            ProgressEvent.related_entity_id
            == session.interview_session_id,
        )
    )

    if existing_event is None:
        db.add(
            ProgressEvent(
                student_profile_id=session.student_profile_id,
                career_path_id=session.career_path_id,
                event_type="interview_completed",
                title="Completed mock interview",
                description=(
                    f"Completed the TigerPad mock interview "
                    f"'{session.title}'."
                ),
                related_entity_type="interview_sessions",
                related_entity_id=session.interview_session_id,
                event_data_json={
                    "interview_type": session.interview_type,
                    "difficulty_level": session.difficulty_level,
                    "overall_score": (
                        float(session.overall_score)
                        if session.overall_score is not None
                        else None
                    ),
                },
                source_type="system",
                is_visible_to_student=1,
                occurred_at=completed_at,
            )
        )

    existing_notification = db.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.notification_type == "interview",
            Notification.related_entity_type == "interview_sessions",
            Notification.related_entity_id
            == session.interview_session_id,
        )
    )

    if existing_notification is None:
        db.add(
            Notification(
                user_id=user_id,
                notification_type="interview",
                title="Mock interview completed",
                message=(
                    f"Your TigerPad mock interview '{session.title}' "
                    "has been completed."
                ),
                action_url=None,
                related_entity_type="interview_sessions",
                related_entity_id=session.interview_session_id,
                priority_level=3,
                delivery_channel="in_app",
                delivery_status="sent",
                is_read=0,
                sent_at=completed_at,
            )
        )


@router.post(
    "",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mock interview session",
)
def create_interview_session(
    payload: InterviewSessionCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewSession:
    """Create a new mock interview session."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    if payload.career_path_id is not None:
        career_path = db.scalar(
            select(CareerPath).where(
                CareerPath.career_path_id == payload.career_path_id,
            )
        )

        if career_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The selected career path was not found.",
            )

    if payload.resume_id is not None:
        resume = db.scalar(
            select(Resume).where(
                Resume.resume_id == payload.resume_id,
                Resume.student_profile_id
                == student_profile.student_profile_id,
            )
        )

        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "The selected résumé was not found in your profile."
                ),
            )

    interview_session = InterviewSession(
        student_profile_id=student_profile.student_profile_id,
        career_path_id=payload.career_path_id,
        resume_id=payload.resume_id,
        title=payload.title.strip(),
        interview_type=payload.interview_type.value,
        difficulty_level=payload.difficulty_level.value,
        status="created",
        question_count=payload.question_count,
        settings_json=payload.settings_json,
    )

    db.add(interview_session)
    db.commit()
    db.refresh(interview_session)

    return interview_session


@router.get(
    "",
    response_model=list[InterviewSessionResponse],
    summary="List mock interview sessions",
)
def list_interview_sessions(
    interview_status: str | None = Query(
        default=None,
        alias="status",
        max_length=20,
    ),
    career_path_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[InterviewSession]:
    """Return interview sessions belonging to the student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = select(InterviewSession).where(
        InterviewSession.student_profile_id
        == student_profile.student_profile_id,
    )

    if interview_status is not None:
        query = query.where(
            InterviewSession.status == interview_status,
        )

    if career_path_id is not None:
        query = query.where(
            InterviewSession.career_path_id == career_path_id,
        )

    query = (
        query.order_by(desc(InterviewSession.created_at))
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(query).all())


@router.get(
    "/{interview_session_id}",
    response_model=InterviewSessionDetailResponse,
    summary="View a mock interview session",
)
def get_interview_session(
    interview_session_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewSessionDetailResponse:
    """Return an interview session and all its responses."""

    session = _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    responses = list(
        db.scalars(
            select(InterviewResponse)
            .where(
                InterviewResponse.interview_session_id
                == interview_session_id,
            )
            .order_by(InterviewResponse.question_number.asc())
        ).all()
    )

    return _session_detail(
        session=session,
        responses=responses,
    )


@router.post(
    "/{interview_session_id}/start",
    response_model=InterviewSessionResponse,
    summary="Start a mock interview",
)
def start_interview_session(
    interview_session_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewSession:
    """Start a created interview session."""

    session = _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A completed interview cannot be started again.",
        )

    if session.status == "abandoned":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An abandoned interview cannot be started again.",
        )

    if session.status == "created":
        session.status = "in_progress"
        session.started_at = _utc_now()

        db.commit()
        db.refresh(session)

    return session


@router.post(
    "/{interview_session_id}/generate-question",
    response_model=InterviewResponseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an interview question",
)
def generate_question(
    interview_session_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Generate and save the next question for an active interview."""

    session = _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Start the interview before generating questions.",
        )

    existing_responses = list(
        db.scalars(
            select(InterviewResponse)
            .where(
                InterviewResponse.interview_session_id
                == interview_session_id,
            )
            .order_by(InterviewResponse.question_number.asc())
        ).all()
    )

    if len(existing_responses) >= session.question_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The configured interview question count is complete.",
        )

    next_question_number = (
        max(
            (
                response.question_number
                for response in existing_responses
            ),
            default=0,
        )
        + 1
    )

    career_path_name, career_path_description = _get_career_context(
        db=db,
        career_path_id=session.career_path_id,
    )

    generated_question = generate_interview_question(
        interview_type=session.interview_type,
        difficulty_level=session.difficulty_level,
        career_path_name=career_path_name,
        career_path_description=career_path_description,
        question_number=next_question_number,
        question_count=session.question_count,
        previous_questions=[
            response.question_text
            for response in existing_responses
        ],
    )

    generated_text = str(
        generated_question["question_text"]
    ).strip()

    if not generated_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="TigerPad could not generate an interview question.",
        )

    now = _utc_now()

    interview_response = InterviewResponse(
        interview_response_id=_next_response_id(db),
        interview_session_id=interview_session_id,
        question_number=next_question_number,
        question_type=generated_question["question_type"],
        question_text=generated_text,
        evaluation_criteria_json=(
            generated_question["evaluation_criteria_json"]
        ),
        student_response=None,
        is_follow_up=(
            1 if generated_question["is_follow_up"] else 0
        ),
        response_duration_seconds=0,
        asked_at=now,
    )

    model_name = generated_question.get("model_name")

    if model_name:
        session.model_name = model_name

    session.prompt_version = generated_question.get(
        "prompt_version",
        session.prompt_version,
    )

    db.add(interview_response)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The generated interview question could not be saved.",
        ) from error

    db.refresh(interview_response)

    return interview_response


@router.get(
    "/{interview_session_id}/responses",
    response_model=list[InterviewResponseResponse],
    summary="List interview responses",
)
def list_interview_responses(
    interview_session_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[InterviewResponse]:
    """Return all responses for an owned interview session."""

    _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    responses = db.scalars(
        select(InterviewResponse)
        .where(
            InterviewResponse.interview_session_id
            == interview_session_id,
        )
        .order_by(InterviewResponse.question_number.asc())
    ).all()

    return list(responses)


@router.post(
    "/{interview_session_id}/responses",
    response_model=InterviewResponseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an interview question and response",
)
def create_interview_response(
    interview_session_id: int,
    payload: InterviewResponseCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Save one interview question and optional student response."""

    session = _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Start the interview before submitting responses.",
        )

    existing_response = db.scalar(
        select(InterviewResponse).where(
            InterviewResponse.interview_session_id
            == interview_session_id,
            InterviewResponse.question_number
            == payload.question_number,
        )
    )

    if existing_response is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A response already exists for this interview question."
            ),
        )

    question_text = payload.question_text.strip()

    if not question_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The interview question cannot be blank.",
        )

    student_response = (
        payload.student_response.strip()
        if payload.student_response
        else None
    )

    interview_response = InterviewResponse(
        interview_response_id=_next_response_id(db),
        interview_session_id=interview_session_id,
        question_number=payload.question_number,
        question_type=payload.question_type.value,
        question_text=question_text,
        evaluation_criteria_json=payload.evaluation_criteria_json,
        student_response=student_response,
        is_follow_up=1 if payload.is_follow_up else 0,
        response_duration_seconds=(
            payload.response_duration_seconds
        ),
        answered_at=_utc_now() if student_response else None,
    )

    db.add(interview_response)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The interview response could not be saved.",
        ) from error

    db.refresh(interview_response)

    return interview_response


@router.patch(
    "/{interview_session_id}/responses/{interview_response_id}",
    response_model=InterviewResponseResponse,
    summary="Replace an interview question or update its response",
)
def update_interview_response(
    interview_session_id: int,
    interview_response_id: int,
    payload: InterviewResponseUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Replace an existing question and update its answer."""

    session = _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an active interview can be updated.",
        )

    interview_response = _get_owned_response(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
        interview_response_id=interview_response_id,
    )

    if payload.question_type is not None:
        interview_response.question_type = (
            payload.question_type.value
        )

    if payload.question_text is not None:
        question_text = payload.question_text.strip()

        if not question_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The interview question cannot be blank.",
            )

        interview_response.question_text = question_text

    if payload.evaluation_criteria_json is not None:
        interview_response.evaluation_criteria_json = (
            payload.evaluation_criteria_json
        )

    if payload.is_follow_up is not None:
        interview_response.is_follow_up = (
            1 if payload.is_follow_up else 0
        )

    student_response = payload.student_response.strip()

    if not student_response:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The interview response cannot be blank.",
        )

    interview_response.student_response = student_response
    interview_response.response_duration_seconds = (
        payload.response_duration_seconds
    )
    interview_response.answered_at = _utc_now()

    db.commit()
    db.refresh(interview_response)

    return interview_response


@router.post(
    "/{interview_session_id}/responses/{interview_response_id}/evaluate",
    response_model=InterviewResponseResponse,
    summary="Evaluate an interview response with AI",
)
def evaluate_response(
    interview_session_id: int,
    interview_response_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Evaluate a submitted interview response with Groq or fallback rules."""

    session = _get_owned_session(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
    )

    if session.status not in {"in_progress", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only an active or completed interview response can "
                "be evaluated."
            ),
        )

    interview_response = _get_owned_response(
        db=db,
        user_id=int(current_user["user_id"]),
        interview_session_id=interview_session_id,
        interview_response_id=interview_response_id,
    )

    if not interview_response.student_response:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submit an answer before requesting evaluation.",
        )

    career_path_name, career_path_description = _get_career_context(
        db=db,
        career_path_id=session.career_path_id,
    )

    evaluation = evaluate_interview_response(
        interview_type=session.interview_type,
        difficulty_level=session.difficulty_level,
        career_path_name=career_path_name,
        career_path_description=career_path_description,
        question_text=interview_response.question_text,
        evaluation_criteria=(
            interview_response.evaluation_criteria_json
        ),
        student_response=interview_response.student_response,
    )

    interview_response.response_score = evaluation["response_score"]
    interview_response.feedback = evaluation["feedback"]
    interview_response.strengths_json = evaluation["strengths_json"]
    interview_response.improvements_json = (
        evaluation["improvements_json"]
    )

    if evaluation.get("model_name"):
        session.model_name = evaluation["model_name"]

    session.prompt_version = evaluation.get(
        "prompt_version",
        session.prompt_version,
    )

    if session.status == "completed":
        overall_score = _calculate_overall_score(
            db=db,
            session=session,
        )

        if overall_score is not None:
            session.feedback_summary = (
                "Interview completed with an average response "
                f"score of {overall_score:.2f}."
            )

    db.commit()
    db.refresh(interview_response)

    return interview_response


@router.post(
    "/{interview_session_id}/complete",
    response_model=InterviewSessionResponse,
    summary="Complete a mock interview",
)
def complete_interview_session(
    interview_session_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> InterviewSession:
    """Complete an interview session and calculate its current score."""

    user_id = int(current_user["user_id"])

    session = _get_owned_session(
        db=db,
        user_id=user_id,
        interview_session_id=interview_session_id,
    )

    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an active interview can be completed.",
        )

    responses = list(
        db.scalars(
            select(InterviewResponse).where(
                InterviewResponse.interview_session_id
                == interview_session_id,
            )
        ).all()
    )

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Submit at least one interview response before "
                "completing the session."
            ),
        )

    completed_at = _utc_now()

    overall_score = _calculate_overall_score(
        db=db,
        session=session,
    )

    session.status = "completed"
    session.completed_at = completed_at

    if session.started_at is not None:
        session.duration_seconds = max(
            0,
            int(
                (
                    completed_at - session.started_at
                ).total_seconds()
            ),
        )

    if overall_score is not None:
        session.feedback_summary = (
            "Interview completed with an average response "
            f"score of {overall_score:.2f}."
        )
    else:
        session.feedback_summary = (
            "Interview completed. Evaluate each response to receive "
            "detailed TigerPad feedback."
        )

    _create_completion_records(
        db=db,
        user_id=user_id,
        session=session,
        completed_at=completed_at,
    )

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The interview session could not be completed.",
        ) from error

    db.refresh(session)

    return session