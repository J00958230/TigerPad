"""
Overall function:
This file defines the shared SQLAlchemy base class and metadata registry
used by every TigerPad database model.

All TigerPad models—including users, profiles, academic programs, career
paths, skills, résumés, recommendations, and administrative records—will
inherit from the Base class in this file. SQLAlchemy uses the shared metadata
to understand how the Python model classes correspond to the existing MySQL
tables and relationships.

This file does not create, delete, or modify the existing MySQL database.
The database built in MySQL Workbench remains the authoritative database
structure.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------
# Database constraint naming convention
# ---------------------------------------------------------

# Consistent names make foreign keys, indexes, primary keys, and
# other constraints easier to identify and manage through Alembic.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": (
        "fk_%(table_name)s_%(column_0_name)s_"
        "%(referred_table_name)s"
    ),
    "pk": "pk_%(table_name)s",
}


# ---------------------------------------------------------
# Shared SQLAlchemy metadata
# ---------------------------------------------------------

metadata = MetaData(
    naming_convention=NAMING_CONVENTION,
)


# ---------------------------------------------------------
# Shared declarative model base
# ---------------------------------------------------------

class Base(DeclarativeBase):
    """
    Base class inherited by every TigerPad SQLAlchemy model.

    Using one shared base ensures that SQLAlchemy registers all models
    in the same metadata collection.
    """

    metadata = metadata


# ---------------------------------------------------------
# Metadata helper functions
# ---------------------------------------------------------

def get_registered_table_names() -> list[str]:
    """
    Return the names of all tables currently registered by the
    imported TigerPad SQLAlchemy models.

    Models must be imported before their table names will appear
    in this list.
    """

    return sorted(Base.metadata.tables.keys())


def is_table_registered(table_name: str) -> bool:
    """
    Check whether a table has been registered in SQLAlchemy metadata.

    Args:
        table_name: Name of the MySQL table to check.

    Returns:
        True when the table is registered.
        False when the table is not registered.
    """

    return table_name in Base.metadata.tables