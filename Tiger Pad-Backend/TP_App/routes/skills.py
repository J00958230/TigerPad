"""
Overall function:
This file provides TigerPad API routes for the shared skill catalog and
student-owned skills.

Students can browse available skills, add skills to their profile, update
their proficiency and evidence, and remove skills they no longer want listed.
Only active catalog skills can be added.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_student
from TP_App.models.skill import Skill
from TP_App.models.student_profile import StudentProfile
from TP_App.models.student_skill import StudentSkill
from TP_App.schemas.skills import (
    SkillResponse,
    StudentSkillCreateRequest,
    StudentSkillResponse,
    StudentSkillUpdateRequest,
)


skill_router = APIRouter(
    prefix="/skills",
    tags=["Skills"],
)


student_skill_router = APIRouter(
    prefix="/students/me/skills",
    tags=["Student Skills"],
)


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
                "Create a student profile before managing your skills."
            ),
        )

    return student_profile


def _get_owned_student_skill(
    db: Session,
    user_id: int,
    student_skill_id: int,
) -> StudentSkill:
    """Return a student skill only when it belongs to the current student."""

    student_skill = db.scalar(
        select(StudentSkill)
        .join(
            StudentProfile,
            StudentSkill.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            StudentSkill.student_skill_id == student_skill_id,
            StudentProfile.user_id == user_id,
        )
    )

    if student_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested student skill was not found.",
        )

    return student_skill


@skill_router.get(
    "",
    response_model=list[SkillResponse],
    summary="List TigerPad skills",
)
def list_skills(
    search_text: str | None = Query(
        default=None,
        max_length=100,
        description="Search skill names, codes, categories, or descriptions.",
    ),
    category: str | None = Query(
        default=None,
        max_length=50,
        description="Filter skills by category.",
    ),
    include_inactive: bool = Query(
        default=False,
        description="Administrators may later use this to view inactive skills.",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Skill]:
    """
    Return skills from the TigerPad catalog.

    Inactive skills are excluded by default.
    """

    query = select(Skill)

    if not include_inactive:
        query = query.where(Skill.is_active.is_(True))

    if search_text:
        search_pattern = f"%{search_text.strip()}%"

        query = query.where(
            Skill.name.ilike(search_pattern)
            | Skill.skill_code.ilike(search_pattern)
            | Skill.category.ilike(search_pattern)
            | Skill.description.ilike(search_pattern)
        )

    if category:
        query = query.where(
            Skill.category.ilike(category.strip())
        )

    query = query.order_by(
        Skill.category.asc(),
        Skill.name.asc(),
    ).offset(offset).limit(limit)

    return list(db.scalars(query).all())


@skill_router.get(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Get one TigerPad skill",
)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
) -> Skill:
    """Return one active skill from the TigerPad catalog."""

    skill = db.scalar(
        select(Skill).where(
            Skill.skill_id == skill_id,
            Skill.is_active.is_(True),
        )
    )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested skill was not found.",
        )

    return skill


@student_skill_router.get(
    "",
    response_model=list[StudentSkillResponse],
    summary="List the authenticated student's skills",
)
def list_student_skills(
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[StudentSkill]:
    """Return all skills connected to the authenticated student."""

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    query = (
        select(StudentSkill)
        .where(
            StudentSkill.student_profile_id
            == student_profile.student_profile_id,
        )
        .order_by(
            StudentSkill.proficiency_level.desc(),
            StudentSkill.created_at.desc(),
        )
    )

    return list(db.scalars(query).all())


@student_skill_router.post(
    "",
    response_model=StudentSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill to the authenticated student's profile",
)
def create_student_skill(
    payload: StudentSkillCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> StudentSkill:
    """
    Add an active catalog skill to the authenticated student's profile.

    New skills begin as self-reported. Verification must be performed by
    an approved TigerPad workflow or faculty reviewer.
    """

    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )

    skill = db.scalar(
        select(Skill).where(
            Skill.skill_id == payload.skill_id,
            Skill.is_active.is_(True),
        )
    )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected skill does not exist or is inactive.",
        )

    existing_skill = db.scalar(
        select(StudentSkill).where(
            StudentSkill.student_profile_id
            == student_profile.student_profile_id,
            StudentSkill.skill_id == payload.skill_id,
        )
    )

    if existing_skill is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This skill is already connected to your profile.",
        )

    student_skill = StudentSkill(
        student_profile_id=student_profile.student_profile_id,
        skill_id=payload.skill_id,
        proficiency_level=payload.proficiency_level,
        years_experience=payload.years_experience,
        verification_status="self_reported",
        evidence_description=payload.evidence_description,
        evidence_url=payload.evidence_url,
    )

    db.add(student_skill)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This skill could not be added to your profile.",
        ) from error

    db.refresh(student_skill)
    return student_skill


@student_skill_router.patch(
    "/{student_skill_id}",
    response_model=StudentSkillResponse,
    summary="Update a student skill",
)
def update_student_skill(
    student_skill_id: int,
    payload: StudentSkillUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> StudentSkill:
    """Update an authenticated student's proficiency or evidence."""

    student_skill = _get_owned_student_skill(
        db=db,
        user_id=int(current_user["user_id"]),
        student_skill_id=student_skill_id,
    )

    update_values = payload.model_dump(exclude_unset=True)

    for field_name, field_value in update_values.items():
        setattr(student_skill, field_name, field_value)

    db.commit()
    db.refresh(student_skill)

    return student_skill


@student_skill_router.delete(
    "/{student_skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a skill from a student profile",
)
def delete_student_skill(
    student_skill_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> None:
    """Remove an authenticated student's skill record."""

    student_skill = _get_owned_student_skill(
        db=db,
        user_id=int(current_user["user_id"]),
        student_skill_id=student_skill_id,
    )

    db.delete(student_skill)
    db.commit()