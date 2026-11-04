"""
Overall function:
This file defines the SQLAlchemy model for the resources table.

The resources table stores career-development resources available to TigerPad
students. Resources may include workshops, events, advising services,
scholarships, internships, career guides, tutoring, professional-development
programs, and other JSU or external opportunities.

The table records how a resource is delivered, its intended audience,
eligibility requirements, location, contact information, availability dates,
and whether it is an official JSU resource.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column

from TP_App.database.base import Base


class Resource(Base):
    """
    Represent a career-readiness resource available through TigerPad.

    Resources are not owned by one student. They can be displayed to all
    students or connected to particular academic programs through the
    resource_programs table.
    """

    __tablename__ = "resources"

    __table_args__ = (
        Index(
            "idx_resources_type_active",
            "resource_type",
            "is_active",
        ),
        Index(
            "idx_resources_jsu_active",
            "is_jsu_resource",
            "is_active",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    resource_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    resource_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    provider_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    resource_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    delivery_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="online",
        server_default=text("'online'"),
    )

    audience_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="all_students",
        server_default=text("'all_students'"),
    )

    eligibility_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    starts_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    ends_at: Mapped[datetime | None] = mapped_column(
        DATETIME,
        nullable=True,
    )

    is_jsu_resource: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    is_active: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=1,
        server_default=text("1"),
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

    @property
    def resource_type_description(self) -> str:
        """Return the resource type in a user-friendly format."""

        resource_types = {
            "workshop": "Workshop",
            "event": "Event",
            "career_advising": "Career Advising",
            "academic_support": "Academic Support",
            "internship": "Internship Opportunity",
            "scholarship": "Scholarship",
            "career_guide": "Career Guide",
            "resume_support": "Résumé Support",
            "interview_support": "Interview Support",
            "professional_development": "Professional Development",
            "mentoring": "Mentoring",
            "tutoring": "Tutoring",
            "other": "Other Resource",
        }

        return resource_types.get(
            self.resource_type,
            self.resource_type.replace("_", " ").title(),
        )

    @property
    def delivery_method_description(self) -> str:
        """Return the delivery method in a user-friendly format."""

        delivery_methods = {
            "online": "Online",
            "in_person": "In person",
            "hybrid": "Online and in person",
        }

        return delivery_methods.get(
            self.delivery_method,
            self.delivery_method.replace("_", " ").title(),
        )

    @property
    def audience_description(self) -> str:
        """Return the intended audience in a user-friendly format."""

        audiences = {
            "all_students": "All JSU students",
            "undergraduate": "Undergraduate students",
            "graduate": "Graduate students",
            "first_year": "First-year students",
            "sophomore": "Sophomore students",
            "junior": "Junior students",
            "senior": "Senior students",
            "alumni": "JSU alumni",
            "specific_programs": "Selected academic programs",
        }

        return audiences.get(
            self.audience_type,
            self.audience_type.replace("_", " ").title(),
        )

    @property
    def jsu_resource(self) -> bool:
        """Return whether this is an official JSU resource."""

        return bool(self.is_jsu_resource)

    @property
    def active(self) -> bool:
        """Return whether the resource is enabled in TigerPad."""

        return bool(self.is_active)

    @property
    def has_resource_link(self) -> bool:
        """Return whether an online resource link is available."""

        return bool(self.resource_url)

    @property
    def is_currently_available(self) -> bool:
        """Return whether the resource is active and within its date range."""

        if not self.active:
            return False

        current_time = datetime.now()

        if self.starts_at and current_time < self.starts_at:
            return False

        if self.ends_at and current_time > self.ends_at:
            return False

        return True

    @property
    def availability_description(self) -> str:
        """Return a readable description of resource availability."""

        current_time = datetime.now()

        if not self.active:
            return "Inactive"

        if self.starts_at and current_time < self.starts_at:
            return f"Available starting {self.starts_at.isoformat()}"

        if self.ends_at and current_time > self.ends_at:
            return "Availability ended"

        if self.ends_at:
            return f"Available until {self.ends_at.isoformat()}"

        return "Currently available"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<Resource("
            f"resource_id={self.resource_id}, "
            f"title={self.title!r}, "
            f"resource_type={self.resource_type!r}, "
            f"delivery_method={self.delivery_method!r}, "
            f"audience_type={self.audience_type!r}, "
            f"is_jsu_resource={self.jsu_resource}, "
            f"is_active={self.active}"
            ")>"
        )
