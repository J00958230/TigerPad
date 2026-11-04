"""
Overall function:
This file defines the SQLAlchemy model for the audit_logs table.

The audit_logs table stores security, administrative, authentication, and
data-change events that occur within the TigerPad website. Audit records help
the cybersecurity and administration teams investigate activity, monitor
important actions, identify failures, and maintain accountability.

Audit logs may record the responsible user, affected entity, action status,
severity, request identifier, network information, and before-and-after
values. Sensitive values such as passwords, authentication tokens, API keys,
and résumé file contents must never be stored in audit logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.mysql import (
    BIGINT,
    CHAR,
    DATETIME,
    INTEGER,
    JSON,
    TIMESTAMP,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.user import User


class AuditLog(Base):
    """
    Represent a security or activity event recorded by TigerPad.

    The user relationship is optional because some events can occur before
    authentication or may remain after the associated user is removed.
    """

    __tablename__ = "audit_logs"

    __table_args__ = (
        Index(
            "idx_audit_logs_user_occurred",
            "user_id",
            "occured_at",
        ),
        Index(
            "idx_audit_logs_entity",
            "entity_type",
            "entity_id",
        ),
        Index(
            "idx_audit_logs_action_occurred",
            "action",
            "occured_at",
        ),
        Index(
            "idx_audit_logs_request_id",
            "request_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    audit_log_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "users.user_id",
            name="fk_audit_logs_user",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    event_category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    entity_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        server_default=text("'success'"),
    )

    severity_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="info",
        server_default=text("'info'"),
    )

    request_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    old_values_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    new_values_json: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        "occured_at",
        DATETIME,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped["User | None"] = relationship(
        "User",
        lazy="joined",
    )

    @property
    def event_category_description(self) -> str:
        """Return the event category in a user-friendly format."""

        categories = {
            "authentication": "Authentication",
            "authorization": "Authorization",
            "user_management": "User Management",
            "profile": "Profile Activity",
            "resume": "Résumé Activity",
            "database": "Database Activity",
            "security": "Security Event",
            "administration": "Administrative Activity",
            "ai": "AI Activity",
            "file": "File Activity",
        }

        return categories.get(
            self.event_category,
            self.event_category.replace("_", " ").title(),
        )

    @property
    def action_description(self) -> str:
        """Return the action in a user-friendly format."""

        return self.action.replace("_", " ").title()

    @property
    def status_description(self) -> str:
        """Return the audit status in a user-friendly format."""

        statuses = {
            "success": "Successful",
            "failure": "Failed",
            "denied": "Denied",
            "warning": "Completed with warning",
        }

        return statuses.get(
            self.status,
            self.status.replace("_", " ").title(),
        )

    @property
    def severity_description(self) -> str:
        """Return the severity level in a user-friendly format."""

        severity_levels = {
            "debug": "Debug",
            "info": "Informational",
            "warning": "Warning",
            "error": "Error",
            "critical": "Critical",
        }

        return severity_levels.get(
            self.severity_level,
            self.severity_level.replace("_", " ").title(),
        )

    @property
    def successful(self) -> bool:
        """Return whether the recorded action succeeded."""

        return self.status == "success"

    @property
    def security_relevant(self) -> bool:
        """Return whether the event requires security attention."""

        return (
            self.event_category in {
                "authentication",
                "authorization",
                "security",
            }
            or self.severity_level in {
                "warning",
                "error",
                "critical",
            }
        )

    @property
    def has_entity_reference(self) -> bool:
        """Return whether the event references a TigerPad record."""

        return bool(
            self.entity_type
            and self.entity_id is not None
        )

    @property
    def entity_reference(self) -> str | None:
        """Return a readable reference to the affected record."""

        if not self.has_entity_reference:
            return None

        entity_name = self.entity_type.replace(
            "_",
            " ",
        ).title()

        return f"{entity_name} #{self.entity_id}"

    @property
    def contains_change_data(self) -> bool:
        """Return whether before-or-after data was recorded."""

        return bool(
            self.old_values_json is not None
            or self.new_values_json is not None
        )

    def __repr__(self) -> str:
        """
        Return a safe developer representation of this audit record.

        Network data, user-agent data, descriptions, and changed values
        are intentionally excluded.
        """

        return (
            "<AuditLog("
            f"audit_log_id={self.audit_log_id}, "
            f"user_id={self.user_id}, "
            f"event_category={self.event_category!r}, "
            f"action={self.action!r}, "
            f"status={self.status!r}, "
            f"severity_level={self.severity_level!r}, "
            f"occurred_at={self.occurred_at!r}"
            ")>"
        )
