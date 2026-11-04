"""
Shared audit-event helpers for TigerPad.

Audit records intentionally contain operational metadata and before/after
values only. Callers must never pass passwords, bearer tokens, refresh tokens,
or uploaded résumé contents to this helper.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from TP_App.models.audit_log import AuditLog


def record_audit_event(
    database: Session,
    *,
    user_id: int | None,
    event_category: str,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    description: str | None = None,
    status: str = "success",
    severity_level: str = "info",
    request: Request | None = None,
    old_values: Any | None = None,
    new_values: Any | None = None,
) -> AuditLog:
    """Add one safe audit record to the current database transaction."""

    request_id = None
    ip_address = None
    user_agent = None

    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        if request.client is not None:
            ip_address = request.client.host
        user_agent = request.headers.get("user-agent")

    audit_log = AuditLog(
        user_id=user_id,
        event_category=event_category[:30],
        action=action[:60],
        entity_type=entity_type[:50] if entity_type else None,
        entity_id=entity_id,
        description=description[:1000] if description else None,
        status=status[:20],
        severity_level=severity_level[:20],
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
        old_values_json=old_values,
        new_values_json=new_values,
    )
    database.add(audit_log)
    return audit_log


__all__ = ["record_audit_event"]
