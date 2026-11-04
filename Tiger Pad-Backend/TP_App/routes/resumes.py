"""
Overall function:
This file provides authenticated résumé routes for TigerPad.
Students can create résumé metadata, upload PDF or DOCX résumés, update
résumé information, list active résumés, preview uploaded résumé files,
select a primary résumé, and soft-delete résumé records.
Uploaded files are protected by:
- Extension validation
- MIME-type validation
- File-signature validation
- Maximum-size validation
- SHA-256 hashing
- Generated storage names
- Path-traversal protection
- Atomic file storage
- Cleanup after database failures
- Optional malware scanning
"""
from __future__ import annotations
import hashlib
import os
import logging
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from TP_App.config import settings
from TP_App.dependencies import get_db, require_student
from TP_App.models.career_path import CareerPath
from TP_App.models.resume import Resume
from TP_App.models.student_profile import StudentProfile
from TP_App.schemas.resume import (
    ResumeCreateRequest,
    ResumeFileMetadata,
    ResumeResponse,
    ResumeUpdateRequest,
)
router = APIRouter(
    prefix="/students/me/resumes",
    tags=["Student Résumés"],
)
_ALLOWED_RESUME_TYPES = {
    "general",
    "career_targeted",
    "academic",
    "internship",
    "graduate_school",
}
_EXPECTED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}
def _get_upload_root() -> Path:
    """Return the resolved upload directory used by TigerPad."""
    return Path(settings.UPLOAD_DIRECTORY).expanduser().resolve()
def _get_resume_directory() -> Path:
    """Create and return the protected résumé directory."""
    upload_root = _get_upload_root()
    resume_directory = (upload_root / "resumes").resolve()
    try:
        resume_directory.relative_to(upload_root)
    except ValueError as error:
        raise RuntimeError(
            "The configured résumé directory is outside the upload directory."
        ) from error
    resume_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    return resume_directory
def _safe_storage_path(storage_key: str) -> Path:
    """Resolve a résumé storage key without allowing path traversal."""
    upload_root = _get_upload_root()
    candidate_path = (upload_root / storage_key).resolve()
    try:
        candidate_path.relative_to(upload_root)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The résumé storage path is invalid.",
        ) from error
    return candidate_path
def _remove_file(path: Path | None) -> None:
    """Remove a temporary or newly created file safely."""
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass

logger = logging.getLogger(__name__)

def _r2_enabled() -> bool:
    """Require complete credentials before enabling remote storage."""
    fields = [settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY]
    return bool(
        all(item is not None and item.get_secret_value().strip() for item in fields)
        and settings.R2_BUCKET_NAME.strip()
        and settings.R2_ENDPOINT_URL.strip()
    )

def _r2_client():
    if not _r2_enabled():
        raise HTTPException(status_code=503, detail="Résumé object storage is not configured.")
    if not settings.R2_ENDPOINT_URL.startswith("https://"):
        raise HTTPException(status_code=503, detail="Résumé object storage endpoint must use HTTPS.")
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL.strip(),
        region_name=settings.R2_REGION or "auto",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID.get_secret_value(),
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"},
                      connect_timeout=10, read_timeout=30),
    )

def _remove_uploaded_object(metadata: dict[str, Any]) -> None:
    """Compensate for a failed DB transaction without exposing secrets."""
    if metadata.get("storage_backend") == "r2":
        try:
            _r2_client().delete_object(Bucket=settings.R2_BUCKET_NAME, Key=metadata["storage_key"])
        except (BotoCoreError, ClientError, OSError):
            logger.exception("Could not remove orphaned résumé object after DB failure")
    else:
        _remove_file(metadata.get("storage_path"))

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
            detail="Create a student profile before managing résumés.",
        )
    return student_profile
def _get_owned_resume(
    db: Session,
    user_id: int,
    resume_id: int,
) -> Resume:
    """Return an active résumé owned by the authenticated student."""
    resume = db.scalar(
        select(Resume)
        .join(
            StudentProfile,
            Resume.student_profile_id
            == StudentProfile.student_profile_id,
        )
        .where(
            Resume.resume_id == resume_id,
            StudentProfile.user_id == user_id,
            Resume.is_active.is_(True),
        )
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested résumé was not found.",
        )
    return resume
def _validate_career_path(
    db: Session,
    career_path_id: int | None,
) -> None:
    """Confirm that an optional career path exists and is active."""
    if career_path_id is None:
        return
    career_path = db.scalar(
        select(CareerPath).where(
            CareerPath.career_path_id == career_path_id,
            CareerPath.is_active.is_(True),
        )
    )
    if career_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected career path does not exist or is inactive.",
        )
def _demote_other_primary_resumes(
    db: Session,
    student_profile_id: int,
    current_resume_id: int | None = None,
) -> None:
    """Ensure that a student has no more than one primary résumé."""
    query = update(Resume).where(
        Resume.student_profile_id == student_profile_id,
        Resume.is_primary.is_(True),
    )
    if current_resume_id is not None:
        query = query.where(
            Resume.resume_id != current_resume_id,
        )
    db.execute(
        query.values(is_primary=False),
    )
def _normalize_original_filename(filename: str | None) -> str:
    """Validate the original filename without allowing path traversal."""
    original_file_name = (filename or "").strip()
    if not original_file_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A résumé filename is required.",
        )
    if len(original_file_name) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The résumé filename is too long.",
        )
    if original_file_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The résumé filename is invalid.",
        )
    if "/" in original_file_name or "\\" in original_file_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The résumé filename cannot contain a path.",
        )
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in original_file_name
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The résumé filename contains invalid characters.",
        )
    return original_file_name
def _allowed_extensions() -> set[str]:
    """Return normalized résumé extensions allowed by application settings."""
    configured_extensions = settings.get_allowed_resume_extensions()
    return {
        extension
        if extension.startswith(".")
        else f".{extension}"
        for extension in configured_extensions
    }
def _validate_extension(
    original_file_name: str,
) -> str:
    """Validate and return the résumé file extension."""
    file_extension = Path(original_file_name).suffix.lower()
    allowed_extensions = _allowed_extensions()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported résumé file type. Allowed types are: "
                f"{', '.join(sorted(allowed_extensions))}."
            ),
        )
    if file_extension not in _EXPECTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The résumé file type is not supported.",
        )
    return file_extension
def _validate_declared_mime_type(
    uploaded_file: UploadFile,
    file_extension: str,
) -> str:
    """
    Validate the client-declared MIME type.
    application/octet-stream is accepted only because some browsers use it
    for DOCX/PDF uploads. The file signature is still checked separately.
    """
    expected_mime_type = _EXPECTED_MIME_TYPES[file_extension]
    declared_mime_type = (
        (uploaded_file.content_type or "")
        .split(";", 1)[0]
        .strip()
        .lower()
    )
    if declared_mime_type not in {
        "",
        expected_mime_type,
        "application/octet-stream",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded résumé MIME type is not supported.",
        )
    return expected_mime_type
def _validate_pdf_signature(file_path: Path) -> None:
    """Confirm that a PDF begins with a valid PDF signature."""
    with file_path.open("rb") as stored_file:
        header = stored_file.read(5)
    if header != b"%PDF-":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file is not a valid PDF.",
        )
def _validate_docx_container(file_path: Path) -> None:
    """
    Confirm that a DOCX is a safe ZIP-based Office document.
    This rejects path-traversal entries, encrypted entries, malformed ZIP
    files, and archives whose uncompressed contents are excessively large.
    """
    maximum_uncompressed_size = max(
        settings.max_upload_size_bytes * 10,
        50 * 1024 * 1024,
    )
    total_uncompressed_size = 0
    required_entries = {
        "[Content_Types].xml",
        "word/document.xml",
    }
    try:
        with zipfile.ZipFile(file_path) as archive:
            entries = set()
            for info in archive.infolist():
                normalized_name = info.filename.replace("\\", "/")
                if (
                    normalized_name.startswith("/")
                    or any(
                        part == ".."
                        for part in normalized_name.split("/")
                    )
                ):
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="The DOCX archive contains an unsafe path.",
                    )
                if info.flag_bits & 0x1:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Encrypted résumé archives are not supported.",
                    )
                total_uncompressed_size += info.file_size
                if total_uncompressed_size > maximum_uncompressed_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="The DOCX archive expands beyond the safe limit.",
                    )
                entries.add(normalized_name)
            if not required_entries.issubset(entries):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="The uploaded file is not a valid DOCX résumé.",
                )
    except HTTPException:
        raise
    except (OSError, zipfile.BadZipFile) as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file is not a valid DOCX résumé.",
        ) from error
def _validate_file_signature(
    file_path: Path,
    file_extension: str,
) -> None:
    """Validate file contents instead of trusting the filename alone."""
    if file_extension == ".pdf":
        _validate_pdf_signature(file_path)
        return
    if file_extension == ".docx":
        _validate_docx_container(file_path)
        return
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="The résumé file signature is not supported.",
    )
def _scan_uploaded_file(file_path: Path) -> str:
    """
    Optionally scan an uploaded résumé with ClamAV.
    When scanning is disabled for local development, the database receives
    scan_status='not_required'. When enabled, the upload fails closed if
    ClamAV is unavailable or reports an error.
    """
    if not settings.FILE_SCANNING_ENABLED:
        return "not_required"
    configured_scanner = getattr(
        settings,
        "FILE_SCANNER_COMMAND",
        "clamdscan",
    )
    scanner_name = str(configured_scanner).strip() or "clamdscan"
    scanner_path = shutil.which(scanner_name)
    if scanner_path is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Résumé malware scanning is enabled, but the configured "
                "scanner is unavailable."
            ),
        )
    try:
        result = subprocess.run(
            [
                scanner_path,
                "--no-summary",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Résumé malware scanning timed out.",
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Résumé malware scanning could not be started.",
        ) from error
    if result.returncode == 0:
        return "clean"
    if result.returncode == 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The résumé did not pass the malware scan.",
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Résumé malware scanning failed.",
    )
def _save_uploaded_resume(uploaded_file: UploadFile) -> dict[str, Any]:
    """Validate locally, then persist in private R2 or local development storage."""
    original_file_name = _normalize_original_filename(uploaded_file.filename)
    file_extension = _validate_extension(original_file_name)
    mime_type = _validate_declared_mime_type(uploaded_file, file_extension)
    storage_key = f"resumes/{uuid4().hex}{file_extension}"
    file_hash = hashlib.sha256()
    file_size_bytes = 0
    # A short-lived local file is needed for signature and optional malware checks.
    resume_directory = _get_resume_directory()
    temporary_path = resume_directory / f".{uuid4().hex}.part"
    final_path = _safe_storage_path(storage_key)
    remote = _r2_enabled()
    if not remote and settings.is_production:
        raise HTTPException(status_code=503, detail="Persistent résumé storage is not configured.")
    try:
        uploaded_file.file.seek(0)
        with temporary_path.open("xb") as stored_file:
            while chunk := uploaded_file.file.read(1024 * 1024):
                file_size_bytes += len(chunk)
                if file_size_bytes > settings.max_upload_size_bytes:
                    raise HTTPException(status_code=413, detail=f"The résumé exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.")
                file_hash.update(chunk)
                stored_file.write(chunk)
        if file_size_bytes == 0:
            raise HTTPException(status_code=422, detail="The uploaded résumé file is empty.")
        _validate_file_signature(temporary_path, file_extension)
        os.chmod(temporary_path, 0o600)
        scan_status = _scan_uploaded_file(temporary_path)
        validated_metadata = ResumeFileMetadata(
            original_file_name=original_file_name, file_extension=file_extension,
            mime_type=mime_type, file_size_bytes=file_size_bytes,
            sha256_hash=file_hash.hexdigest(), scan_status=scan_status,
        )
        if remote:
            with temporary_path.open("rb") as source:
                _r2_client().upload_fileobj(
                    source, settings.R2_BUCKET_NAME, storage_key,
                    ExtraArgs={"ContentType": mime_type},
                )
        else:
            os.replace(temporary_path, final_path)
        return {
            **validated_metadata.model_dump(), "storage_key": storage_key,
            "storage_path": None if remote else final_path,
            "storage_backend": "r2" if remote else "local",
        }
    except HTTPException:
        raise
    except (BotoCoreError, ClientError, OSError) as error:
        logger.exception("Résumé storage failed")
        raise HTTPException(status_code=503, detail="The résumé could not be stored securely.") from error
    except Exception as error:
        logger.exception("Résumé upload failed")
        raise HTTPException(status_code=500, detail="The résumé upload could not be completed.") from error
    finally:
        _remove_file(temporary_path)

@router.get(
    "",
    response_model=list[ResumeResponse],
    summary="List the authenticated student's résumés",
)
def list_resumes(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[Resume]:
    """Return active résumés belonging to the authenticated student."""
    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )
    query = (
        select(Resume)
        .where(
            Resume.student_profile_id
            == student_profile.student_profile_id,
            Resume.is_active.is_(True),
        )
        .order_by(
            Resume.is_primary.desc(),
            Resume.updated_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(query).all())
@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get one student résumé",
)
def get_resume(
    resume_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Resume:
    """Return one active résumé owned by the authenticated student."""
    return _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )
@router.get(
    "/{resume_id}/file",
    summary="Preview an uploaded résumé file",
)
def preview_resume_file(
    resume_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Stream a private object only after verifying student ownership."""
    resume = _get_owned_resume(db, int(current_user["user_id"]), resume_id)
    if not resume.storage_key:
        raise HTTPException(status_code=404, detail="This résumé does not contain an uploaded file.")
    if resume.scan_status not in {"clean", "not_required"}:
        raise HTTPException(status_code=403, detail="This résumé file is not available for preview.")
    original_filename = _normalize_original_filename(resume.original_file_name)
    # Keep support for pre-migration local files when running locally.
    if not _r2_enabled():
        if settings.is_production:
            raise HTTPException(status_code=503, detail="Persistent résumé storage is not configured.")
        file_path = _safe_storage_path(resume.storage_key)
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="The résumé file could not be found.")
        return FileResponse(path=file_path, media_type=resume.mime_type or "application/octet-stream",
                            filename=original_filename, content_disposition_type="inline")
    # Validate keys before passing them to the object-store API.
    _safe_storage_path(resume.storage_key)
    try:
        result = _r2_client().get_object(Bucket=settings.R2_BUCKET_NAME, Key=resume.storage_key)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        if code in {"NoSuchKey", "404", "NotFound"}:
            raise HTTPException(status_code=404, detail="The résumé file could not be found.") from error
        logger.exception("Could not retrieve private résumé object")
        raise HTTPException(status_code=503, detail="Résumé storage is temporarily unavailable.") from error
    except (BotoCoreError, OSError) as error:
        logger.exception("Could not retrieve private résumé object")
        raise HTTPException(status_code=503, detail="Résumé storage is temporarily unavailable.") from error
    body = result["Body"]
    def chunks():
        try:
            for chunk in body.iter_chunks(chunk_size=1024 * 1024):
                if chunk:
                    yield chunk
        finally:
            body.close()
    from urllib.parse import quote
    safe_name = quote(original_filename, safe="")
    return StreamingResponse(
        chunks(), media_type=resume.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{safe_name}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create résumé metadata",
)
def create_resume(
    payload: ResumeCreateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Resume:
    """Create a generated or structured résumé record."""
    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )
    _validate_career_path(
        db=db,
        career_path_id=payload.career_path_id,
    )
    resume = Resume(
        student_profile_id=student_profile.student_profile_id,
        career_path_id=payload.career_path_id,
        title=payload.title,
        resume_type=payload.resume_type,
        source_type="generated",
        template_name=payload.template_name,
        content_json=payload.content_json,
        scan_status="not_required",
        is_primary=False,
        is_active=True,
    )
    db.add(resume)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The résumé could not be created.",
        ) from error
    db.refresh(resume)
    return resume
@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or DOCX résumé",
)
def upload_resume(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=150),
    career_path_id: int | None = Form(default=None),
    resume_type: str = Form(default="general", max_length=30),
    template_name: str | None = Form(default=None, max_length=100),
    is_primary: bool = Form(default=False),
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Resume:
    """Upload and securely store a student's résumé file."""
    cleaned_title = " ".join(title.strip().split())
    if not cleaned_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A résumé title is required.",
        )
    cleaned_resume_type = resume_type.strip() or "general"
    if cleaned_resume_type not in _ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid résumé type. Allowed values are: "
                f"{', '.join(sorted(_ALLOWED_RESUME_TYPES))}."
            ),
        )
    cleaned_template_name = (
        " ".join(template_name.strip().split())
        if template_name and template_name.strip()
        else None
    )
    student_profile = _get_student_profile(
        db=db,
        user_id=int(current_user["user_id"]),
    )
    _validate_career_path(
        db=db,
        career_path_id=career_path_id,
    )
    file_metadata = _save_uploaded_resume(file)
    if is_primary:
        _demote_other_primary_resumes(
            db=db,
            student_profile_id=student_profile.student_profile_id,
        )
    resume = Resume(
        student_profile_id=student_profile.student_profile_id,
        career_path_id=career_path_id,
        title=cleaned_title,
        resume_type=cleaned_resume_type,
        source_type="uploaded",
        template_name=cleaned_template_name,
        original_file_name=file_metadata["original_file_name"],
        storage_key=file_metadata["storage_key"],
        file_extension=file_metadata["file_extension"],
        mime_type=file_metadata["mime_type"],
        file_size_bytes=file_metadata["file_size_bytes"],
        sha256_hash=file_metadata["sha256_hash"],
        scan_status=file_metadata["scan_status"],
        version_number=1,
        is_primary=is_primary,
        is_active=True,
    )
    db.add(resume)
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        _remove_uploaded_object(file_metadata)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The résumé could not be uploaded.",
        ) from error
    db.refresh(resume)
    return resume
@router.patch(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Update résumé metadata",
)
def update_resume(
    resume_id: int,
    payload: ResumeUpdateRequest,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> Resume:
    """Update metadata for a résumé owned by the student."""
    resume = _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )
    update_values = payload.model_dump(
        exclude_unset=True,
    )
    if "career_path_id" in update_values:
        _validate_career_path(
            db=db,
            career_path_id=update_values["career_path_id"],
        )
    if update_values.get("is_primary") is True:
        _demote_other_primary_resumes(
            db=db,
            student_profile_id=resume.student_profile_id,
            current_resume_id=resume.resume_id,
        )
    for field_name, field_value in update_values.items():
        setattr(resume, field_name, field_value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The résumé could not be updated.",
        ) from error
    db.refresh(resume)
    return resume
@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a student résumé",
)
def delete_resume(
    resume_id: int,
    current_user: dict[str, Any] = Depends(require_student),
    db: Session = Depends(get_db),
) -> None:
    """
    Soft-delete a résumé owned by the student.
    The database record and stored file remain available for audit and
    recovery, but the résumé is removed from active résumé results.
    """
    resume = _get_owned_resume(
        db=db,
        user_id=int(current_user["user_id"]),
        resume_id=resume_id,
    )
    resume.is_active = False
    resume.is_primary = False
    db.commit()                                                                                                                                                                                          
