
"""
TigerPad - Central Configuration

Jackson State University Career Accelerator

This module loads and validates configuration for:
- FastAPI
- MySQL
- Groq AI
- JWT authentication
- Frontend and CORS
- Resume uploads
- Rate limiting
- Production deployment

Real credentials belong in the private .env file.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


# ============================================================
# APPLICATION SETTINGS
# ============================================================

class Settings(BaseSettings):
    """
    Central configuration for the TigerPad backend.

    Configuration is loaded from environment variables
    and the private project .env file.
    """

    # --------------------------------------------------------
    # APPLICATION
    # --------------------------------------------------------

    APP_NAME: str = "TigerPad"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "JSU Career Accelerator Backend API"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # --------------------------------------------------------
    # MYSQL DATABASE
    # --------------------------------------------------------

    DATABASE_HOST: str = "127.0.0.1"
    DATABASE_PORT: int = 3306
    DATABASE_NAME: str = "tigerpad"
    DATABASE_USER: str = "tigerpad_web"

    DATABASE_PASSWORD: SecretStr

    DATABASE_DRIVER: str = "mysql+pymysql"
    DATABASE_CHARSET: str = "utf8mb4"

    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_ECHO: bool = False

    # --------------------------------------------------------
    # GROQ AI
    # --------------------------------------------------------

    GROQ_API_KEY: SecretStr

    GROQ_MODEL: str = "openai/gpt-oss-20b"

    AI_FEATURES_ENABLED: bool = True
    AI_TEMPERATURE: float = 0.2
    AI_MAX_TOKENS: int = 1500
    AI_MAX_INPUT_CHARACTERS: int = 12000

    # --------------------------------------------------------
    # AI SCOPE RESTRICTIONS
    # --------------------------------------------------------

    AI_OUT_OF_SCOPE_MESSAGE: str = (
        "I can only assist with TigerPad career-readiness "
        "topics, including resumes, skills, projects, "
        "certifications, career paths, interview preparation, "
        "professional development, and JSU career resources."
    )

    AI_ALLOWED_TOPICS: str = (
        "resume writing,resume analysis,career paths,"
        "career readiness,skills,skill gaps,projects,"
        "certifications,work experience,"
        "interview preparation,professional development,"
        "academic programs,student career goals,"
        "JSU career resources"
    )

    AI_BLOCKED_TOPICS: str = (
        "illegal activity,malware creation,credential theft,"
        "academic cheating,violent wrongdoing,"
        "sexual content,unrelated entertainment,"
        "unrelated general conversation"
    )

    # --------------------------------------------------------
    # JWT AUTHENTICATION
    # --------------------------------------------------------

    JWT_SECRET_KEY: SecretStr

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --------------------------------------------------------
    # ACCOUNT SECURITY
    # --------------------------------------------------------

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    MINIMUM_PASSWORD_LENGTH: int = 12

    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    ALLOWED_EMAIL_DOMAINS: str = "jsums.edu"

    EXPOSE_DEVELOPMENT_SECURITY_TOKENS: bool = False

    # --------------------------------------------------------
    # FRONTEND AND CORS
    # --------------------------------------------------------

    FRONTEND_URL: str = "http://localhost:5173"

    ALLOWED_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    # --------------------------------------------------------
    # RESUME UPLOADS
    # --------------------------------------------------------

    UPLOAD_DIRECTORY: Path = Path("TP_App/uploads")

    MAX_UPLOAD_SIZE_MB: int = 10

    ALLOWED_RESUME_EXTENSIONS: str = ".pdf,.docx"

    FILE_SCANNING_ENABLED: bool = False
    FILE_SCANNER_COMMAND: str = "clamdscan"

    # --------------------------------------------------------
    # RATE LIMITING
    # --------------------------------------------------------

    RATE_LIMIT_ENABLED: bool = True

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    AUTH_RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_MAX_KEYS: int = 10000

    # --------------------------------------------------------
    # DEPLOYMENT
    # --------------------------------------------------------

    DEPLOYMENT_PLATFORM: str = "local"

    REQUIRE_HTTPS: bool = False
    SECURE_COOKIES: bool = False
    COOKIE_AUTH_ENABLED: bool = False

    # --------------------------------------------------------
    # ENVIRONMENT LOADING
    # --------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ========================================================
    # DATABASE URL
    # ========================================================

    @property
    def database_url(self) -> URL:
        """
        Construct the MySQL connection URL safely.

        SQLAlchemy URL.create handles special characters
        in passwords without manual URL encoding.
        """

        return URL.create(
            drivername=self.DATABASE_DRIVER,
            username=self.DATABASE_USER,
            password=(
                self.DATABASE_PASSWORD.get_secret_value()
            ),
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
            query={
                "charset": self.DATABASE_CHARSET
            },
        )

    # ========================================================
    # CORS ORIGINS
    # ========================================================

    def get_allowed_origins(self) -> list[str]:
        """
        Convert comma-separated origins into a list.
        """

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    # ========================================================
    # ENVIRONMENT CHECK
    # ========================================================

    @property
    def is_production(self) -> bool:
        """
        Determine whether production settings apply.
        """

        return (
            self.ENVIRONMENT.strip().lower()
            in {"production", "prod"}
        )

    # ========================================================
    # SECURITY VALIDATION
    # ========================================================

    def validate_security_settings(self) -> list[str]:
        """
        Identify potentially unsafe configurations.

        Returns warnings without exposing secrets.
        """

        warnings: list[str] = []

        origins = self.get_allowed_origins()

        if not self.JWT_SECRET_KEY.get_secret_value().strip():
            warnings.append(
                "JWT_SECRET_KEY must not be empty."
            )

        if self.MINIMUM_PASSWORD_LENGTH < 12:
            warnings.append(
                "Minimum password length should be at least 12."
            )

        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            warnings.append(
                "Access token expiration must be positive."
            )

        if self.REFRESH_TOKEN_EXPIRE_DAYS <= 0:
            warnings.append(
                "Refresh token expiration must be positive."
            )

        if self.MAX_UPLOAD_SIZE_MB <= 0:
            warnings.append(
                "Maximum upload size must be positive."
            )

        if self.RATE_LIMIT_REQUESTS <= 0:
            warnings.append(
                "Rate limit requests must be positive."
            )

        if self.RATE_LIMIT_WINDOW_SECONDS <= 0:
            warnings.append(
                "Rate limit window must be positive."
            )

        if self.AUTH_RATE_LIMIT_REQUESTS <= 0:
            warnings.append(
                "Authentication rate limit must be positive."
            )

        if self.is_production:

            if self.DEBUG:
                warnings.append(
                    "DEBUG must be false in production."
                )

            if "*" in origins:
                warnings.append(
                    "Wildcard CORS origins are not allowed "
                    "in production."
                )

            if not self.REQUIRE_HTTPS:
                warnings.append(
                    "REQUIRE_HTTPS should be true "
                    "in production."
                )

            if not self.RATE_LIMIT_ENABLED:
                warnings.append(
                    "Rate limiting must be enabled "
                    "in production."
                )

            if not self.FILE_SCANNING_ENABLED:
                warnings.append(
                    "Uploaded-file malware scanning "
                    "should be enabled in production."
                )

            if self.EXPOSE_DEVELOPMENT_SECURITY_TOKENS:
                warnings.append(
                    "Development security tokens must "
                    "be disabled in production."
                )

            if self.COOKIE_AUTH_ENABLED and not self.SECURE_COOKIES:
                warnings.append(
                    "Cookie authentication requires "
                    "secure cookies in production."
                )

            if self.DATABASE_ECHO:
                warnings.append(
                    "DATABASE_ECHO should be false "
                    "in production."
                )

            if not self.JWT_SECRET_KEY.get_secret_value().strip():
                warnings.append(
                    "A valid JWT secret is required."
                )

        return warnings

    # ========================================================
    # RESUME EXTENSIONS
    # ========================================================

    def get_allowed_resume_extensions(self) -> set[str]:
        """
        Return approved resume extensions.
        """

        return {
            extension.strip().lower()
            for extension in (
                self.ALLOWED_RESUME_EXTENSIONS.split(",")
            )
            if extension.strip()
        }

    # ========================================================
    # AI ALLOWED TOPICS
    # ========================================================

    def get_ai_allowed_topics(self) -> set[str]:
        """
        Return approved TigerPad AI topics.
        """

        return {
            topic.strip().lower()
            for topic in self.AI_ALLOWED_TOPICS.split(",")
            if topic.strip()
        }

    # ========================================================
    # AI BLOCKED TOPICS
    # ========================================================

    def get_ai_blocked_topics(self) -> set[str]:
        """
        Return blocked AI topic categories.
        """

        return {
            topic.strip().lower()
            for topic in self.AI_BLOCKED_TOPICS.split(",")
            if topic.strip()
        }

    # ========================================================
    # UPLOAD SIZE
    # ========================================================

    @property
    def max_upload_size_bytes(self) -> int:
        """
        Convert the upload limit from MB to bytes.
        """

        return (
            self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        )

    # ========================================================
    # GROQ CONFIGURATION
    # ========================================================

    @property
    def groq_is_configured(self) -> bool:
        """
        Determine whether Groq AI is configured.
        """

        api_key = (
            self.GROQ_API_KEY
            .get_secret_value()
            .strip()
        )

        return bool(
            self.AI_FEATURES_ENABLED
            and api_key
            and self.GROQ_MODEL
            and self.GROQ_MODEL != "MODEL_NAME_PENDING"
        )

    # ========================================================
    # DATABASE CONFIGURATION
    # ========================================================

    @property
    def database_is_configured(self) -> bool:
        """
        Determine whether required MySQL settings exist.
        """

        password = (
            self.DATABASE_PASSWORD
            .get_secret_value()
            .strip()
        )

        return bool(
            self.DATABASE_HOST
            and self.DATABASE_PORT
            and self.DATABASE_NAME
            and self.DATABASE_USER
            and password
        )


# ============================================================
# SETTINGS CACHE
# ============================================================

@lru_cache
def get_settings() -> Settings:
    """
    Load and cache application settings.
    """

    return Settings()


# ============================================================
# SHARED SETTINGS INSTANCE
# ============================================================

settings = get_settings()
