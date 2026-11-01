"""Alembic environment: runs migrations online against `BANKING_DB_URL`."""

from alembic import context
from sqlalchemy import create_engine, text

from banking.config import get_settings
from banking.db import SCHEMA
from banking.models import Base


def run_migrations() -> None:
    """Create the schema if needed, then apply migrations inside it."""
    # The default search_path ("$user", public) makes `banking` the default schema when
    # the role is named banking, and autogenerate then reports it as None: pin it.
    engine = create_engine(
        str(get_settings().db_url),
        connect_args={"options": "-csearch_path=public"},
        hide_parameters=True,
    )
    with engine.connect() as connection:
        # The version table lives in the schema, so the schema must exist first.
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            # Autogenerate compares the banking schema only.
            include_schemas=True,
            include_name=lambda name, type_, _: type_ != "schema" or name == SCHEMA,
            version_table_schema=SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
