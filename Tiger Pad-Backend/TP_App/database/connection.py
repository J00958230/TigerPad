"""
Overall function:
This file creates and manages the connection between the TigerPad FastAPI
backend and the MySQL database.

It builds the SQLAlchemy engine using the secure database settings loaded
from .env, creates reusable database sessions, safely closes sessions after
use, rolls back failed transactions, and provides a health-check function
that confirms whether MySQL is available.

The database password is never stored directly in this file.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from TP_App.config import settings


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
    Create and provide a database session.

    FastAPI dependencies will use this generator whenever an endpoint
    needs to communicate with MySQL. The session is automatically closed
    when the request finishes.

    If an error occurs during a database operation, the current
    transaction is rolled back before the exception is raised again.
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

    The SELECT 1 statement performs a lightweight connection test
    without changing any database information.

    Returns:
        True if the database connection succeeds.
        False if the database connection fails.
    """

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar_one() == 1

    except SQLAlchemyError:
        return False


def get_database_name() -> str:
    """Return the configured TigerPad database name."""

    return settings.DATABASE_NAME


def dispose_database_engine() -> None:
    """
    Close all pooled database connections.

    This function is called when the TigerPad backend shuts down.
    """

    engine.dispose()