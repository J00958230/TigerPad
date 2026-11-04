"""
Overall function:
This file defines the SQLAlchemy model for the certifications table.

The certifications table stores certifications, licenses, certificates,
awards, badges, and other credentials earned by TigerPad students.

TigerPad can use credential information to strengthen résumés, demonstrate
qualifications, evaluate career readiness, verify student achievements, and
recommend credentials that may help students prepare for their career goals.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import (
    DATE,
    INTEGER,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.student_profile import StudentProfile


class Certification(Base):
    """
    Represent a certification or credential earned by a student.

    Every certification belongs to one student profile. Removing the student
    profile will also remove its associated certification records.
    """

    __tablename__ = "certifications"

    __table_args__ = (
        Index(
            "fk_certifications_student_profile_idx",
            "student_profile_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    certification_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_certifications_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    credential_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="certification",
        server_default=text("'certification'"),
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    issuing_organization: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    credential_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    credential_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    issue_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
    )

    expiration_date: Mapped[date | None] = mapped_column(
        DATE,
        nullable=True,
    )

    does_not_expire: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_featured: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
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

    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        lazy="joined",
    )

    @property
    def credential_type_description(self) -> str:
        """Return the credential type in a user-friendly format."""

        credential_types = {
            "certification": "Certification",
            "license": "Professional License",
            "certificate": "Certificate",
            "award": "Award",
            "badge": "Digital Badge",
            "training": "Training Credential",
            "other": "Other Credential",
        }

        return credential_types.get(
            self.credential_type,
            self.credential_type.replace("_", " ").title(),
        )

    @property
    def non_expiring(self) -> bool:
        """Return whether the credential does not expire."""

        return bool(self.does_not_expire)

    @property
    def featured(self) -> bool:
        """Return whether the credential should be featured."""

        return bool(self.is_featured)

    @property
    def has_verification_link(self) -> bool:
        """Return whether a credential verification link exists."""

        return bool(self.credential_url)

    @property
    def is_expired(self) -> bool:
        """Return whether the credential has expired."""

        return bool(
            not self.non_expiring
            and self.expiration_date
            and self.expiration_date < date.today()
        )

    @property
    def is_active(self) -> bool:
        """Return whether the credential is currently valid."""

        return not self.is_expired

    @property
    def days_until_expiration(self) -> int | None:
        """
        Return the number of days before the credential expires.

        None is returned when the credential does not expire or when no
        expiration date was provided. A negative value means it has expired.
        """

        if self.non_expiring or self.expiration_date is None:
            return None

        return (self.expiration_date - date.today()).days

    @property
    def expiration_description(self) -> str:
        """Return a readable description of the expiration status."""

        if self.non_expiring:
            return "Does not expire"

        if self.expiration_date is None:
            return "Expiration date not provided"

        if self.is_expired:
            return f"Expired on {self.expiration_date.isoformat()}"

        return f"Expires on {self.expiration_date.isoformat()}"

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<Certification("
            f"certification_id={self.certification_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"credential_type={self.credential_type!r}, "
            f"name={self.name!r}, "
            f"issuing_organization={self.issuing_organization!r}, "
            f"is_featured={self.featured}"
            ")>"
        )
