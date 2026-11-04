"""
Overall function:
This file defines the SQLAlchemy model for the resumes table.

The resumes table stores résumés created or uploaded by TigerPad students.
A résumé can be general or tailored toward a specific career path. The table
supports generated résumé content, uploaded file information, file-integrity
verification, security scan results, version tracking, and primary-résumé
selection.

TigerPad can use this information to build personalized résumés, analyze
career readiness, recommend improvements, and maintain multiple résumé
versions for different career paths.
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
    INTEGER,
    JSON,
    SMALLINT,
    TIMESTAMP,
    TINYINT,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from TP_App.database.base import Base


if TYPE_CHECKING:
    from TP_App.models.career_path import CareerPath
    from TP_App.models.student_profile import StudentProfile


class Resume(Base):
    """
    Represent a résumé created or uploaded by a TigerPad student.

    Every résumé belongs to one student profile. A résumé can optionally
    connect to a career path when it is tailored for a particular field.
    """

    __tablename__ = "resumes"

    __table_args__ = (
        Index(
            "storage_key_UNIQUE",
            "storage_key",
            unique=True,
        ),
        Index(
            "fk_resumes_student_profile_idx",
            "student_profile_id",
        ),
        Index(
            "fk_resumes_career_path_idx",
            "career_path_id",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )

    resume_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "student_profiles.student_profile_id",
            name="fk_resumes_student_profile",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    career_path_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey(
            "career_paths.career_path_id",
            name="fk_resumes_career_path",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    resume_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="general",
        server_default=text("'general'"),
    )

    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="generated",
        server_default=text("'generated'"),
    )

    template_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    content_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    original_file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    storage_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    file_extension: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        nullable=True,
    )

    sha256_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    scan_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_required",
        server_default=text("'not_required'"),
    )

    version_number: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True),
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    is_primary: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
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

    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        lazy="joined",
    )

    career_path: Mapped["CareerPath | None"] = relationship(
        "CareerPath",
        lazy="joined",
    )

    @property
    def primary(self) -> bool:
        """Return whether this is the student's primary résumé."""

        return bool(self.is_primary)

    @property
    def active(self) -> bool:
        """Return whether this résumé version is active."""

        return bool(self.is_active)

    @property
    def is_uploaded(self) -> bool:
        """Return whether the résumé originated from a file upload."""

        return self.source_type == "uploaded"

    @property
    def is_generated(self) -> bool:
        """Return whether TigerPad generated the résumé."""

        return self.source_type == "generated"

    @property
    def is_career_specific(self) -> bool:
        """Return whether the résumé targets a particular career path."""

        return self.career_path_id is not None

    @property
    def has_stored_file(self) -> bool:
        """Return whether a stored résumé file is associated with the record."""

        return bool(self.storage_key)

    @property
    def passed_security_scan(self) -> bool:
        """Return whether the uploaded résumé passed its security scan."""

        return self.scan_status in {
            "clean",
            "not_required",
        }

    @property
    def file_size_megabytes(self) -> float | None:
        """Convert the stored file size from bytes to megabytes."""

        if self.file_size_bytes is None:
            return None

        return round(
            self.file_size_bytes / (1024 * 1024),
            2,
        )

    @property
    def resume_type_description(self) -> str:
        """Return the résumé type in a user-friendly format."""

        resume_types = {
            "general": "General Résumé",
            "career_specific": "Career-Specific Résumé",
            "internship": "Internship Résumé",
            "graduate_school": "Graduate School Résumé",
            "federal": "Federal Résumé",
            "academic": "Academic Résumé",
        }

        return resume_types.get(
            self.resume_type,
            self.resume_type.replace("_", " ").title(),
        )

    def __repr__(self) -> str:
        """Return a safe developer representation of this record."""

        return (
            "<Resume("
            f"resume_id={self.resume_id}, "
            f"student_profile_id={self.student_profile_id}, "
            f"career_path_id={self.career_path_id}, "
            f"title={self.title!r}, "
            f"resume_type={self.resume_type!r}, "
            f"version_number={self.version_number}, "
            f"is_primary={self.primary}"
            ")>"
        )
