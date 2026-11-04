"""
Overall function:
This file is the main entry point for the TigerPad FastAPI website backend.
It configures the application, checks startup services, creates upload
directories, enables frontend communication, registers all API route groups,
and applies baseline security middleware.

TigerPad is a JSU career-readiness website for students across all academic
disciplines.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from TP_App import models as _models
from TP_App.config import settings
from TP_App.database.connection import (
    check_database_connection,
    dispose_database_engine,
)

from TP_App.routes.academic_programs import (
    academic_program_router,
    student_program_router,
)
from TP_App.routes.admin import router as admin_router
from TP_App.routes.auth import router as auth_router
from TP_App.routes.career import (
    career_path_router,
    student_career_router,
)
from TP_App.routes.certifications import (
    router as certifications_router,
)
from TP_App.routes.experiences import router as experiences_router
from TP_App.routes.faculty import router as faculty_router
from TP_App.routes.interviews import router as interviews_router
from TP_App.routes.notifications import (
    router as notifications_router,
)
from TP_App.routes.progress_events import (
    router as progress_events_router,
)
from TP_App.routes.projects import router as projects_router
from TP_App.routes.readiness import router as readiness_router
from TP_App.routes.recommendations import (
    router as recommendations_router,
)
from TP_App.routes.resources import router as resources_router
from TP_App.routes.resume_analysis import (
    router as resume_analysis_router,
)
from TP_App.routes.resumes import router as resumes_router
from TP_App.routes.skills import (
    skill_router,
    student_skill_router,
)
from TP_App.routes.student_profiles import (
    router as student_profiles_router,
)
from TP_App.security.hardening import (
    InMemoryRateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)


logger = logging.getLogger("tigerpad")


@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncGenerator[None, None]:
    """
    Run startup and shutdown operations for TigerPad.

    Startup creates upload directories, verifies the MySQL connection,
    and reports whether the Groq AI configuration is available.
    """

    upload_directory = Path(settings.UPLOAD_DIRECTORY)
    resume_directory = upload_directory / "resumes"
    temporary_directory = upload_directory / "temporary"

    upload_directory.mkdir(parents=True, exist_ok=True)
    resume_directory.mkdir(parents=True, exist_ok=True)
    temporary_directory.mkdir(parents=True, exist_ok=True)

    logger.info("%s backend is starting.", settings.APP_NAME)
    logger.info("Environment: %s", settings.ENVIRONMENT)

    try:
        if check_database_connection():
            logger.info(
                "TigerPad successfully connected to MySQL database '%s'.",
                settings.DATABASE_NAME,
            )
        else:
            logger.warning(
                "TigerPad could not verify the MySQL database connection."
            )
    except Exception:
        logger.exception(
            "TigerPad database startup verification failed."
        )

    if settings.groq_is_configured:
        logger.info(
            "Groq AI is configured with model '%s'.",
            settings.GROQ_MODEL,
        )
    else:
        logger.warning(
            "Groq AI is not fully configured. AI features may be limited."
        )

    logger.info(
        "Rate limiting enabled: %s",
        settings.RATE_LIMIT_ENABLED,
    )

    for security_warning in settings.validate_security_settings():
        logger.warning("Security configuration warning: %s", security_warning)

    if settings.is_production and not check_database_connection():
        raise RuntimeError("TigerPad production startup requires MySQL.")

    try:
        yield
    finally:
        dispose_database_engine()
        logger.info("%s backend is shutting down.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    enabled=settings.RATE_LIMIT_ENABLED,
    auth_requests=settings.AUTH_RATE_LIMIT_REQUESTS,
    max_keys=settings.RATE_LIMIT_MAX_KEYS,
)

app.add_middleware(RequestIdMiddleware)

if settings.REQUIRE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    SecurityHeadersMiddleware,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
    ],
)



@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Distinguish missing resources from unknown API endpoints."""

    detail = getattr(exception, "detail", "Not Found")

    if detail == "Not Found":
        message = "The requested TigerPad endpoint was not found."
    else:
        message = str(detail)

    logger.warning(
        "404 response for %s: %s",
        request.url.path,
        message,
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "message": message,
            "path": request.url.path,
        },
    )


@app.exception_handler(500)
async def internal_server_error_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """
    Return a safe response for unexpected server errors.

    Internal exception details are kept out of responses so sensitive
    implementation details are not exposed to website users.
    """

    logger.exception(
        "Unexpected server error while processing %s.",
        request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected TigerPad server error occurred.",
        },
    )


@app.get(
    "/",
    tags=["System"],
    summary="TigerPad API welcome page",
)
async def root() -> dict[str, str]:
    """Return basic public information about the TigerPad backend."""

    return {
        "application": settings.APP_NAME,
        "description": settings.APP_DESCRIPTION,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "documentation": "/docs",
    }


@app.get(
    "/health",
    tags=["System"],
    summary="Check backend health",
)
async def health_check() -> dict[str, object]:
    """
    Confirm that the TigerPad website backend and connected services
    are available.
    """

    try:
        database_available = check_database_connection()
    except Exception:
        database_available = False

    response = {
        "success": database_available,
        "application": settings.APP_NAME,
        "status": "healthy" if database_available else "degraded",
        "services": {
            "api": "available",
            "database": (
                "available"
                if database_available
                else "unavailable"
            ),
            "groq": (
                "configured"
                if settings.groq_is_configured
                else "pending"
            ),
            "authentication": "available",
            "rate_limiting": (
                "enabled"
                if settings.RATE_LIMIT_ENABLED
                else "disabled_for_development"
            ),
            "file_scanning": (
                "enabled"
                if settings.FILE_SCANNING_ENABLED
                else "disabled_for_development"
            ),
            "https_enforcement": (
                "enabled"
                if settings.REQUIRE_HTTPS
                else "disabled_for_development"
            ),
        },
    }
    return JSONResponse(
        status_code=200 if database_available else 503,
        content=response,
    )


@app.get(
    f"{settings.API_PREFIX}/information",
    tags=["System"],
    summary="Get application information",
)
async def application_information() -> dict[str, object]:
    """Return public configuration information about TigerPad."""

    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "environment": settings.ENVIRONMENT,
        "api_prefix": settings.API_PREFIX,
        "deployment_platform": settings.DEPLOYMENT_PLATFORM,
        "ai_features_enabled": settings.AI_FEATURES_ENABLED,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
    }


# ---------------------------------------------------------
# API route registration
# ---------------------------------------------------------

app.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    student_profiles_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    academic_program_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    student_program_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    career_path_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    student_career_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    skill_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    student_skill_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    experiences_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    projects_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    certifications_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    resumes_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    resume_analysis_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    readiness_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    recommendations_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    progress_events_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    notifications_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    interviews_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    faculty_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    admin_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    resources_router,
    prefix=settings.API_PREFIX,
)
