"""
Overall function:
This file defines the SQLAlchemy model for the notifications table.

The notifications table stores messages sent to TigerPad users. Notifications
can inform users about résumé feedback, career recommendations, skill gaps,
upcoming events, interview practice, profile updates, security activity,
faculty feedback, and administrative announcements.

The table supports notification priority, delivery channels, delivery status,
scheduled delivery, read tracking, expiration, action links, and optional
references to related TigerPad records.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATETIME,
    INTEGER,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.user import User


class Notification(Base):
    """
    Represent a notification sent to a TigerPad user.

    Every notification belongs to one user. Removing a user will also remove
    that user's notification records.
    """

    __tablename__ = "notifications"

    __table_args__ = (
        Index(
            "idx_notifications_user_read_created",
            "user_id",
            "is_read",
            "created_at",
        ),
        Index(
            "idx_notifications_delivery_scheduled",
            "delivery_status",
            "scheduled_for",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    notification_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "users.user_id",
            name="fk_notifications_user",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    related_entity_type: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    related_entity_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    priority_level: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=3,
        server_default=text("3"),
    )

    delivery_channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_app",
        server_default=text("'in_app'"),
    )

    delivery_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    is_read: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    @property
    def notification_type_description(self) -> str:
        """Return the notification type in a user-friendly format."""

        return self.notification_type.replace("_", " ").title()

    @property
    def priority_description(self) -> str:
        """Return a readable description of the priority level."""

        priorities = {
            1: "Very low",
            2: "Low",
            3: "Normal",
            4: "High",
            5: "Critical",
        }

        return priorities.get(
            self.priority_level,
            "Unknown",
        )

    @property
    def delivery_channel_description(self) -> str:
        """Return the delivery channel in a user-friendly format."""

        channels = {
            "in_app": "TigerPad website",
            "email": "Email",
            "both": "TigerPad website and email",
        }

        return channels.get(
            self.delivery_channel,
            self.delivery_channel.replace("_", " ").title(),
        )

    @property
    def delivery_status_description(self) -> str:
        """Return the delivery status in a user-friendly format."""

        statuses = {
            "pending": "Pending delivery",
            "scheduled": "Scheduled",
            "sent": "Sent",
            "failed": "Delivery failed",
            "cancelled": "Cancelled",
        }

        return statuses.get(
            self.delivery_status,
            self.delivery_status.replace("_", " ").title(),
        )

    @property
    def read(self) -> bool:
        """Return whether the user has read the notification."""

        return bool(self.is_read)

    @property
    def sent(self) -> bool:
        """Return whether the notification was sent."""

        return bool(
            self.delivery_status == "sent"
            or self.sent_at is not None
        )

    @property
    def expired(self) -> bool:
        """Return whether the notification has expired."""

        return bool(
            self.expires_at
            and self.expires_at < datetime.now()
        )

    @property
    def ready_for_delivery(self) -> bool:
        """Return whether the notification can currently be delivered."""

        if self.delivery_status not in {
            "pending",
            "scheduled",
        }:
            return False

        if self.expired:
            return False

        if (
            self.scheduled_for
            and self.scheduled_for > datetime.now()
        ):
            return False

        return True

    @property
    def has_action(self) -> bool:
        """Return whether the notification contains an action link."""

        return bool(self.action_url)

    @property
    def has_related_entity(self) -> bool:
        """Return whether the notification references another record."""

        return bool(
            self.related_entity_type
            and self.related_entity_id is not None
        )

    @property
    def related_entity_reference(self) -> str | None:
        """Return a readable reference to the related TigerPad record."""

        if not self.has_related_entity:
            return None

        entity_name = self.related_entity_type.replace(
            "_",
            " ",
        ).title()

        return f"{entity_name} #{self.related_entity_id}"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<Notification("
            f"notification_id={self.notification_id}, "
            f"user_id={self.user_id}, "
            f"notification_type={self.notification_type!r}, "
            f"priority_level={self.priority_level}, "
            f"delivery_status={self.delivery_status!r}, "
            f"is_read={self.read}"
            ")>"
        )
