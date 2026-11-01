"""Declarative base shared by every model of the `banking` schema."""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from banking.databases.engine import SCHEMA

# Named constraints, so a violation can be mapped back to the form field that caused it.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """Base class of every banking model."""

    metadata = MetaData(schema=SCHEMA, naming_convention=NAMING_CONVENTION)
    # Timestamps are stored in UTC; business dates are plain `date` columns.
    type_annotation_map = {datetime: DateTime(timezone=True)}


class Timestamps:
    """`created_at` and `updated_at`, set by the database."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
