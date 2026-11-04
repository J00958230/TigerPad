
"""
TigerPad Administrator API.

Provides user management, role changes, faculty program
permissions, dashboard statistics, and audit logs.

All endpoints require administrator authentication.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_admin
from TP_App.models.user import User
from TP_App.models.role import Role
from TP_App.models.audit_log import AuditLog
from TP_App.models.student_profile import StudentProfile
from TP_App.models.faculty_profile import FacultyProfile
from TP_App.models.faculty_program_access import FacultyProgramAccess
from TP_App.models.academic_program import AcademicProgram
from TP_App.models.career_path import CareerPath
from TP_App.models.industry import Industry
from TP_App.models.skill import Skill

from TP_App.schemas.admin import (
    AdminUserStatusUpdateRequest,
    AdminUserRoleUpdateRequest,
    AdminFacultyAccessCreateRequest,
    AdminFacultyAccessUpdateRequest,
)


router = APIRouter(
    prefix="/admin",
    tags=["Administrator"],
    dependencies=[Depends(require_admin)],
)


# ============================================================
# SHARED HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def admin_id(current_user):
    return int(current_user["user_id"])


def save_changes(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Database constraint conflict.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database operation failed.",
        ) from None


def audit_change(
    db,
    actor_id,
    action,
    entity_type,
    entity_id,
    old_values=None,
    new_values=None,
):
    db.add(
        AuditLog(
            user_id=actor_id,
            event_category="administration",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=f"Administrator performed {action}",
            status="success",
            severity_level="info",
            old_values_json=old_values,
            new_values_json=new_values,
            occurred_at=utc_now(),
        )
    )


def user_data(user, role_name):
    return {
        "user_id": user.user_id,
        "role_id": user.role_id,
        "role": role_name,
        "jsu_email": user.jsu_email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": bool(user.is_active),
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until,
        "email_verified_at": user.email_verified_at,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def record_count(db, model, condition=None):
    statement = select(func.count()).select_from(model)

    if condition is not None:
        statement = statement.where(condition)

    return db.scalar(statement) or 0


def get_required_role(db, role_id):
    role = db.get(Role, role_id)

    if role is None or role.name not in {
        "student", "faculty", "admin"
    }:
        raise HTTPException(
            status_code=404,
            detail="Valid role not found.",
        )

    return role


# ============================================================
# USER MANAGEMENT
# ============================================================

@router.get("/users")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(User, Role.name)
        .join(Role, User.role_id == Role.role_id)
        .order_by(User.user_id)
        .offset(skip)
        .limit(limit)
    ).all()

    return [
        user_data(user, role)
        for user, role in rows
    ]


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(User, Role.name)
        .join(Role, User.role_id == Role.role_id)
        .where(User.user_id == user_id)
    ).one_or_none()

    if row is None:
        raise HTTPException(404, "User not found.")

    user, role = row
    return user_data(user, role)


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    user = db.execute(
        select(User)
        .where(User.user_id == user_id)
        .with_for_update()
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(404, "User not found.")

    if user_id == admin_id(current_admin) and not payload.is_active:
        raise HTTPException(
            400,
            "You cannot deactivate your own account.",
        )

    previous = bool(user.is_active)
    requested = bool(payload.is_active)

    if previous != requested:
        user.is_active = int(requested)

        audit_change(
            db,
            admin_id(current_admin),
            "user_status_updated",
            "user",
            user_id,
            old_values={"is_active": previous},
            new_values={"is_active": requested},
        )

        save_changes(db)
    else:
        db.rollback()

    return {
        "message": "User status processed successfully.",
        "user_id": user_id,
        "is_active": requested,
    }


# ============================================================
# SAFE USER ROLE MANAGEMENT
# ============================================================

@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: AdminUserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    """
    Change a user's role without deleting profile data.

    Student and faculty roles require an existing matching
    profile. Admin accounts do not require a separate profile.

    Existing JWT access tokens will fail role validation
    after a role change because authentication checks the
    current role against the token.
    """

    if user_id == admin_id(current_admin):
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own administrator role.",
        )

    user = db.execute(
        select(User)
        .where(User.user_id == user_id)
        .with_for_update()
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(404, "User not found.")

    new_role = get_required_role(db, payload.role_id)
    old_role = get_required_role(db, user.role_id)

    if old_role.role_id == new_role.role_id:
        db.rollback()
        return {
            "message": "User already has this role.",
            "user_id": user_id,
            "role_id": new_role.role_id,
            "role": new_role.name,
        }

    if new_role.name == "student":
        profile = db.scalar(
            select(StudentProfile).where(
                StudentProfile.user_id == user_id
            )
        )

        if profile is None:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "This user does not have a student profile. "
                    "Create the required student profile before "
                    "assigning the student role."
                ),
            )

    if new_role.name == "faculty":
        profile = db.scalar(
            select(FacultyProfile).where(
                FacultyProfile.user_id == user_id
            )
        )

        if profile is None:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "This user does not have a faculty profile. "
                    "Create the required faculty profile before "
                    "assigning the faculty role."
                ),
            )

    # Prevent demoting the final active administrator.
    if old_role.name == "admin" and new_role.name != "admin":
        active_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role_id == old_role.role_id,
                User.is_active == 1,
            )
        ) or 0

        if bool(user.is_active) and active_admins <= 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Cannot demote the last active administrator.",
            )

    previous_role_id = user.role_id
    user.role_id = new_role.role_id

    audit_change(
        db,
        admin_id(current_admin),
        "user_role_updated",
        "user",
        user_id,
        old_values={
            "role_id": previous_role_id,
            "role": old_role.name,
        },
        new_values={
            "role_id": new_role.role_id,
            "role": new_role.name,
        },
    )

    save_changes(db)

    return {
        "message": "User role updated successfully.",
        "user_id": user_id,
        "previous_role": old_role.name,
        "role_id": new_role.role_id,
        "role": new_role.name,
        "requires_new_login": True,
    }


# ============================================================
# ADMINISTRATOR OVERVIEW
# ============================================================

@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
):
    def count_role(role_name):
        return db.scalar(
            select(func.count())
            .select_from(User)
            .join(Role, User.role_id == Role.role_id)
            .where(Role.name == role_name)
        ) or 0

    return {
        "total_users": record_count(db, User),
        "active_users": record_count(
            db, User, User.is_active == 1
        ),
        "inactive_users": record_count(
            db, User, User.is_active == 0
        ),
        "student_users": count_role("student"),
        "faculty_users": count_role("faculty"),
        "administrator_users": count_role("admin"),
        "total_student_profiles": record_count(
            db, StudentProfile
        ),
        "total_faculty_profiles": record_count(
            db, FacultyProfile
        ),
        "total_active_programs": record_count(
            db, AcademicProgram,
            AcademicProgram.is_active == 1,
        ),
        "total_active_career_paths": record_count(
            db, CareerPath,
            CareerPath.is_active == 1,
        ),
        "total_active_skills": record_count(
            db, Skill,
            Skill.is_active == 1,
        ),
    }


# ============================================================
# FACULTY PROGRAM ACCESS
# ============================================================

@router.get("/faculty-access")
def list_faculty_access(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    records = db.scalars(
        select(FacultyProgramAccess)
        .order_by(
            FacultyProgramAccess.faculty_program_access_id
        )
        .offset(skip)
        .limit(limit)
    ).all()

    return [
        {
            "faculty_program_access_id":
                record.faculty_program_access_id,
            "faculty_profile_id": record.faculty_profile_id,
            "program_id": record.program_id,
            "access_level": record.access_level,
            "expires_at": record.expires_at,
            "is_active": bool(record.is_active),
            "access_is_valid": record.access_is_valid,
        }
        for record in records
    ]


@router.post("/faculty-access", status_code=201)
def create_faculty_access(
    payload: AdminFacultyAccessCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    faculty = db.get(
        FacultyProfile, payload.faculty_profile_id
    )

    if faculty is None:
        raise HTTPException(404, "Faculty profile not found.")

    program = db.get(
        AcademicProgram, payload.program_id
    )

    if program is None:
        raise HTTPException(404, "Academic program not found.")

    if not bool(program.is_active):
        raise HTTPException(
            400,
            "Cannot assign an inactive academic program.",
        )

    if payload.expires_at is not None:
        expiry = payload.expires_at

        if expiry.tzinfo is not None:
            expiry = expiry.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

        if expiry <= utc_now():
            raise HTTPException(
                400,
                "Expiration must be in the future.",
            )
    else:
        expiry = None

    existing = db.scalar(
        select(FacultyProgramAccess).where(
            FacultyProgramAccess.faculty_profile_id
            == payload.faculty_profile_id,
            FacultyProgramAccess.program_id
            == payload.program_id,
        )
    )

    if existing is not None:
        raise HTTPException(
            409,
            "This faculty program assignment already exists.",
        )

    record = FacultyProgramAccess(
        faculty_profile_id=payload.faculty_profile_id,
        program_id=payload.program_id,
        access_level=payload.access_level.value,
        expires_at=expiry,
        is_active=1,
    )

    db.add(record)
    db.flush()

    access_id = record.faculty_program_access_id

    audit_change(
        db,
        admin_id(current_admin),
        "faculty_access_created",
        "faculty_program_access",
        access_id,
        new_values={
            "faculty_profile_id": payload.faculty_profile_id,
            "program_id": payload.program_id,
            "access_level": payload.access_level.value,
        },
    )

    save_changes(db)

    return {
        "message": "Faculty program access created.",
        "faculty_program_access_id": access_id,
    }


@router.patch("/faculty-access/{access_id}")
def update_faculty_access(
    access_id: int,
    payload: AdminFacultyAccessUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    record = db.execute(
        select(FacultyProgramAccess)
        .where(
            FacultyProgramAccess.faculty_program_access_id
            == access_id
        )
        .with_for_update()
    ).scalar_one_or_none()

    if record is None:
        raise HTTPException(
            404,
            "Faculty access assignment not found.",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        db.rollback()
        raise HTTPException(400, "No changes provided.")

    old_values = {
        "access_level": record.access_level,
        "is_active": bool(record.is_active),
        "expires_at": (
            record.expires_at.isoformat()
            if record.expires_at else None
        ),
    }

    if "access_level" in changes:
        if changes["access_level"] is None:
            raise HTTPException(
                422,
                "Access level cannot be null.",
            )
        record.access_level = changes["access_level"].value

    if "is_active" in changes:
        if changes["is_active"] is None:
            raise HTTPException(
                422,
                "Active status cannot be null.",
            )
        record.is_active = int(changes["is_active"])

    if "expires_at" in changes:
        expiry = changes["expires_at"]

        if expiry is not None and expiry.tzinfo is not None:
            expiry = expiry.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

        if expiry is not None and expiry <= utc_now():
            raise HTTPException(
                400,
                "Expiration must be in the future.",
            )

        record.expires_at = expiry

    new_values = {
        "access_level": record.access_level,
        "is_active": bool(record.is_active),
        "expires_at": (
            record.expires_at.isoformat()
            if record.expires_at else None
        ),
    }

    if old_values == new_values:
        db.rollback()
        return {
            "message": "Faculty access is unchanged.",
            "faculty_program_access_id": access_id,
        }

    audit_change(
        db,
        admin_id(current_admin),
        "faculty_access_updated",
        "faculty_program_access",
        access_id,
        old_values=old_values,
        new_values=new_values,
    )

    save_changes(db)

    return {
        "message": "Faculty access updated.",
        "faculty_program_access_id": access_id,
    }


# ============================================================
# AUDIT LOGS
# ============================================================

@router.get("/audit-logs")
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    records = db.scalars(
        select(AuditLog)
        .order_by(AuditLog.audit_log_id.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return [
        {
            "audit_log_id": log.audit_log_id,
            "user_id": log.user_id,
            "event_category": log.event_category,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "description": log.description,
            "status": log.status,
            "severity_level": log.severity_level,
            "old_values_json": log.old_values_json,
            "new_values_json": log.new_values_json,
            "occurred_at": log.occurred_at,
        }
        for log in records
    ]


# ============================================================
# FACULTY REVIEW PERMISSION MANAGEMENT
# ============================================================

@router.patch("/faculty/{faculty_profile_id}/review-permission")
def update_faculty_review_permission(
    faculty_profile_id: int,
    can_review_students: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    """
    Allow an administrator to enable or disable a faculty
    member's student-review permission.

    Faculty must also have an active reviewer or manager
    program assignment to access student information.
    """

    profile = db.execute(
        select(FacultyProfile)
        .where(
            FacultyProfile.faculty_profile_id
            == faculty_profile_id
        )
        .with_for_update()
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Faculty profile not found.",
        )

    old_permission = bool(profile.can_review_students)
    new_permission = bool(can_review_students)

    if old_permission == new_permission:
        db.rollback()
        return {
            "message": "Faculty review permission is unchanged.",
            "faculty_profile_id": faculty_profile_id,
            "can_review_students": new_permission,
        }

    profile.can_review_students = int(new_permission)

    audit_change(
        db,
        admin_id(current_admin),
        "faculty_review_permission_updated",
        "faculty_profile",
        faculty_profile_id,
        old_values={
            "can_review_students": old_permission
        },
        new_values={
            "can_review_students": new_permission
        },
    )

    save_changes(db)

    return {
        "message": "Faculty review permission updated.",
        "faculty_profile_id": faculty_profile_id,
        "can_review_students": new_permission,
    }


# ============================================================
# CAREER PATH CONTENT MANAGEMENT
# ============================================================

class CareerPathCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    industry_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)
    career_path_code: str = Field(min_length=1, max_length=40)
    description: str | None = None
    typical_education_level: str | None = Field(default=None, max_length=50)


class CareerPathEditPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    industry_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    career_path_code: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = None
    typical_education_level: str | None = Field(default=None, max_length=50)


class CareerPathPublicationPayload(BaseModel):
    is_active: bool


def career_path_data(path):
    return {
        "career_path_id": path.career_path_id,
        "industry_id": path.industry_id,
        "name": path.name,
        "career_path_code": path.career_path_code,
        "description": path.description,
        "typical_education_level": path.typical_education_level,
        "is_active": bool(path.is_active),
        "created_at": path.created_at,
        "updated_at": path.updated_at,
    }


def require_active_industry(db, industry_id):
    industry = db.get(Industry, industry_id)
    if industry is None or not bool(industry.is_active):
        raise HTTPException(422, "Choose an existing active industry.")
    return industry


@router.get("/industries")
def list_admin_industries(db: Session = Depends(get_db)):
    return [
        {"industry_id": i.industry_id, "name": i.name, "industry_code": i.industry_code}
        for i in db.scalars(select(Industry).where(Industry.is_active == 1).order_by(Industry.name)).all()
    ]


@router.get("/career-paths")
def list_admin_career_paths(db: Session = Depends(get_db)):
    paths = db.scalars(select(CareerPath).order_by(CareerPath.name)).all()
    return [career_path_data(path) for path in paths]


@router.post("/career-paths", status_code=201)
def create_admin_career_path(
    payload: CareerPathCreatePayload,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    require_active_industry(db, payload.industry_id)
    data = payload.model_dump()
    data["name"] = data["name"].strip()
    data["career_path_code"] = data["career_path_code"].strip().upper()
    if not data["name"] or not data["career_path_code"]:
        raise HTTPException(422, "Name and career path code cannot be blank.")
    path = CareerPath(**data, is_active=0)  # Never auto-publish new content.
    db.add(path)
    try:
        db.flush()
        audit_change(db, admin_id(current_admin), "career_path_draft_created", "career_path", path.career_path_id,
                     new_values={**data, "is_active": False})
        save_changes(db)
        db.refresh(path)
    except Exception:
        db.rollback()
        raise
    return career_path_data(path)


@router.patch("/career-paths/{career_path_id}")
def edit_admin_career_path(
    career_path_id: int,
    payload: CareerPathEditPayload,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    path = db.scalar(select(CareerPath).where(CareerPath.career_path_id == career_path_id).with_for_update())
    if path is None:
        raise HTTPException(404, "Career path not found.")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No changes supplied.")
    for field in ("name", "career_path_code"):
        if field in updates:
            if updates[field] is None or not updates[field].strip():
                raise HTTPException(422, f"{field} cannot be empty.")
            updates[field] = updates[field].strip()
    if "career_path_code" in updates:
        updates["career_path_code"] = updates["career_path_code"].upper()
    if "industry_id" in updates:
        require_active_industry(db, updates["industry_id"])
    before = {key: getattr(path, key) for key in updates}
    for key, value in updates.items():
        setattr(path, key, value)
    audit_change(db, admin_id(current_admin), "career_path_updated", "career_path", career_path_id,
                 old_values=before, new_values=updates)
    save_changes(db)
    db.refresh(path)
    return career_path_data(path)


@router.patch("/career-paths/{career_path_id}/publication")
def set_career_path_publication(
    career_path_id: int,
    payload: CareerPathPublicationPayload,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
):
    path = db.scalar(select(CareerPath).where(CareerPath.career_path_id == career_path_id).with_for_update())
    if path is None:
        raise HTTPException(404, "Career path not found.")
    old_status = bool(path.is_active)
    if old_status != payload.is_active:
        if payload.is_active:
            require_active_industry(db, path.industry_id)
        path.is_active = int(payload.is_active)
        audit_change(db, admin_id(current_admin),
                     "career_path_published" if payload.is_active else "career_path_unpublished",
                     "career_path", career_path_id,
                     old_values={"is_active": old_status},
                     new_values={"is_active": payload.is_active})
        save_changes(db)
    else:
        db.rollback()
    db.refresh(path)
    return career_path_data(path)