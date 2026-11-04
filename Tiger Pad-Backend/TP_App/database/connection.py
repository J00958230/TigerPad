
"""
Overall function:

This file creates and manages the connection between the TigerPad FastAPI
backend and the MySQL database.

It builds the SQLAlchemy engine using database settings loaded from the
environment, creates reusable database sessions, safely closes sessions,
rolls back failed transactions, and provides a database health check.

For production on Render, it uses Aiven's CA certificate to establish
an encrypted, certificate-verified MySQL connection.

The database password is never stored directly in this file.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from TP_App.config import settings


# ---------------------------------------------------------
# Production MySQL TLS configuration
# ---------------------------------------------------------

database_connect_args = {}

if settings.ENVIRONMENT.lower() == "production":
    ca_certificate = Path("/etc/secrets/ca.pem")

    if not ca_certificate.is_file():
        raise RuntimeError(
            "Production MySQL CA certificate not found at "
            "/etc/secrets/ca.pem"
        )

    database_connect_args = {
        "ssl": {
            "ca": str(ca_certificate),
            "check_hostname": True,
        }
    }


# ---------------------------------------------------------
# SQLAlchemy MySQL engine
# ---------------------------------------------------------

engine = create_engine(
    settings.database_url,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    connect_args=database_connect_args,
)


# ---------------------------------------------------------
# Database session factory
# ---------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_database_session() -> Generator[Session, None, None]:
    """
    Provide a database session and close it after use.

    Roll back the transaction if an error occurs.
    """

    database_session = SessionLocal()

    try:
        yield database_session

    except Exception:
        database_session.rollback()
        raise

    finally:
        database_session.close()


def check_database_connection() -> bool:
    """
    Check whether TigerPad can communicate with MySQL.

    SELECT 1 performs a lightweight, read-only connection test.
    """

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar_one() == 1

    except SQLAlchemyError:
        return False
