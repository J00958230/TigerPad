"""
Overall function:
This file provides TigerPad's JSU resource-catalog endpoints.

Students and visitors can view active career-readiness resources. Administrators
can create, update, activate, deactivate, and connect resources to academic
programs.

Resources support all JSU students and may include career services, résumé
support, interview preparation, mentoring, internships, graduate school,
workshops, and community opportunities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from TP_App.dependencies import get_db, require_admin
from TP_App.models.academic_program import AcademicProgram
from TP_App.models.resource import Resource
from TP_App.models.resource_program import ResourceProgram
from TP_App.schemas.resource import (
    ResourceCreateRequest,
    ResourceDetailResponse,
    ResourceProgramAttachRequest,
    ResourceProgramResponse,
    ResourceResponse,
    ResourceUpdateRequest,
)


router = APIRouter(
    prefix="/resources",
    tags=["Resources"],
)


def _utc_now() -> datetime:
    """Return a timezone-naive UTC datetime for MySQL DATETIME columns."""

    return datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)


def _get_resource(
    db: Session,
    resource_id: int,
    include_inactive: bool = False,
) -> Resource:
    """Return a resource or raise a 404 error."""

    query = select(Resource).where(
        Resource.resource_id == resource_id,
    )

    if not include_inactive:
        query = query.where(
            Resource.is_active == 1,
        )

    resource = db.scalar(query)

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested resource was not found.",
        )

    return resource


def _validate_resource_dates(
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> None:
    """Ensure a resource's end date does not precede its start date."""

    if starts_at is not None and ends_at is not None:
        if ends_at < starts_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The resource end time cannot precede its start time.",
            )


def _resource_detail(
    db: Session,
    resource: Resource,
) -> ResourceDetailResponse:
    """Build a resource response with connected programs."""

    connections = list(
        db.scalars(
            select(ResourceProgram)
            .where(
                ResourceProgram.resource_id == resource.resource_id,
                ResourceProgram.is_active == 1,
            )
            .order_by(
                ResourceProgram.created_at.asc(),
            )
        ).all()
    )

    base_response = ResourceResponse.model_validate(resource)

    program_responses = [
        ResourceProgramResponse.model_validate(connection)
        for connection in connections
    ]

    return ResourceDetailResponse(
        **base_response.model_dump(),
        programs=program_responses,
    )


@router.get(
    "",
    response_model=list[ResourceResponse],
    summary="List active TigerPad resources",
)
def list_resources(
    resource_type: str | None = Query(
        default=None,
        max_length=40,
    ),
    audience_type: str | None = Query(
        default=None,
        max_length=30,
    ),
    program_id: int | None = Query(
        default=None,
        ge=1,
    ),
    search_text: str | None = Query(
        default=None,
        max_length=100,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
) -> list[Resource]:
    """
    Return active resources available to TigerPad students.

    Inactive and expired resources are excluded from the public catalog.
    """

    now = _utc_now()

    query = select(Resource).where(
        Resource.is_active == 1,
        or_(
            Resource.ends_at.is_(None),
            Resource.ends_at > now,
        ),
    )

    if resource_type is not None:
        query = query.where(
            Resource.resource_type == resource_type,
        )

    if audience_type is not None:
        query = query.where(
            or_(
                Resource.audience_type == audience_type,
                Resource.audience_type == "all_students",
            )
        )

    if program_id is not None:
        query = query.join(
            ResourceProgram,
            Resource.resource_id == ResourceProgram.resource_id,
        ).where(
            ResourceProgram.program_id == program_id,
            ResourceProgram.is_active == 1,
        )

    if search_text:
        search_pattern = f"%{search_text.strip()}%"

        query = query.where(
            or_(
                Resource.title.like(search_pattern),
                Resource.description.like(search_pattern),
                Resource.provider_name.like(search_pattern),
                Resource.resource_type.like(search_pattern),
            )
        )

    query = (
        query.distinct()
        .order_by(
            Resource.starts_at.asc(),
            desc(Resource.created_at),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(query).all())


@router.get(
    "/{resource_id}",
    response_model=ResourceDetailResponse,
    summary="View a resource",
)
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
) -> ResourceDetailResponse:
    """Return one active resource and its connected programs."""

    resource = _get_resource(
        db=db,
        resource_id=resource_id,
    )

    return _resource_detail(
        db=db,
        resource=resource,
    )


@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a resource",
)
def create_resource(
    payload: ResourceCreateRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Resource:
    """Create a resource as an administrator."""

    _validate_resource_dates(
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )

    resource = Resource(
        title=payload.title.strip(),
        resource_type=payload.resource_type.strip(),
        description=payload.description.strip(),
        provider_name=(
            payload.provider_name.strip()
            if payload.provider_name
            else None
        ),
        resource_url=(
            payload.resource_url.strip()
            if payload.resource_url
            else None
        ),
        location=(
            payload.location.strip()
            if payload.location
            else None
        ),
        contact_email=(
            payload.contact_email.strip()
            if payload.contact_email
            else None
        ),
        delivery_method=payload.delivery_method.strip(),
        audience_type=payload.audience_type.strip(),
        eligibility_notes=(
            payload.eligibility_notes.strip()
            if payload.eligibility_notes
            else None
        ),
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        is_jsu_resource=1 if payload.is_jsu_resource else 0,
        is_active=1 if payload.is_active else 0,
    )

    db.add(resource)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The resource could not be created.",
        ) from error

    db.refresh(resource)

    return resource


@router.patch(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Update a resource",
)
def update_resource(
    resource_id: int,
    payload: ResourceUpdateRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Resource:
    """Update or deactivate a resource as an administrator."""

    resource = _get_resource(
        db=db,
        resource_id=resource_id,
        include_inactive=True,
    )

    _validate_resource_dates(
        starts_at=payload.starts_at or resource.starts_at,
        ends_at=payload.ends_at or resource.ends_at,
    )

    if payload.title is not None:
        resource.title = payload.title.strip()

    if payload.resource_type is not None:
        resource.resource_type = payload.resource_type.strip()

    if payload.description is not None:
        resource.description = payload.description.strip()

    if payload.provider_name is not None:
        resource.provider_name = payload.provider_name.strip()

    if payload.resource_url is not None:
        resource.resource_url = payload.resource_url.strip()

    if payload.location is not None:
        resource.location = payload.location.strip()

    if payload.contact_email is not None:
        resource.contact_email = payload.contact_email.strip()

    if payload.delivery_method is not None:
        resource.delivery_method = payload.delivery_method.strip()

    if payload.audience_type is not None:
        resource.audience_type = payload.audience_type.strip()

    if payload.eligibility_notes is not None:
        resource.eligibility_notes = (
            payload.eligibility_notes.strip()
        )

    if payload.starts_at is not None:
        resource.starts_at = payload.starts_at

    if payload.ends_at is not None:
        resource.ends_at = payload.ends_at

    if payload.is_jsu_resource is not None:
        resource.is_jsu_resource = (
            1 if payload.is_jsu_resource else 0
        )

    if payload.is_active is not None:
        resource.is_active = 1 if payload.is_active else 0

    db.commit()
    db.refresh(resource)

    return resource


@router.post(
    "/{resource_id}/programs",
    response_model=ResourceProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a resource to an academic program",
)
def attach_resource_to_program(
    resource_id: int,
    payload: ResourceProgramAttachRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ResourceProgram:
    """Connect a resource to an academic program."""

    resource = _get_resource(
        db=db,
        resource_id=resource_id,
        include_inactive=True,
    )

    program = db.scalar(
        select(AcademicProgram).where(
            AcademicProgram.program_id == payload.program_id,
        )
    )

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected academic program was not found.",
        )

    existing_connection = db.scalar(
        select(ResourceProgram).where(
            ResourceProgram.resource_id == resource.resource_id,
            ResourceProgram.program_id == payload.program_id,
        )
    )

    if existing_connection is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This resource is already connected to the academic "
                "program."
            ),
        )

    connection = ResourceProgram(
        resource_id=resource.resource_id,
        program_id=payload.program_id,
        relevance_level=payload.relevance_level.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        is_active=1,
    )

    db.add(connection)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The resource-program connection could not be created.",
        ) from error

    db.refresh(connection)

    return connection


@router.patch(
    "/{resource_id}/programs/{resource_program_id}",
    response_model=ResourceProgramResponse,
    summary="Update a resource-program connection",
)
def update_resource_program_connection(
    resource_id: int,
    resource_program_id: int,
    payload: ResourceUpdateRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ResourceProgram:
    """
    Placeholder protection endpoint for resource-program connections.

    Resource-program updates should be implemented with a dedicated
    connection-update schema before production deployment.
    """

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Resource-program connection updates are not implemented yet."
        ),
    )