"""Alembic environment: runs migrations online against `BANKING_DB_URL`."""

from alembic import context
from sqlalchemy import create_engine, text

from banking.config import get_settings
from banking.db import SCHEMA


def run_migrations() -> None:
    """Create the schema if needed, then apply migrations inside it."""
    engine = create_engine(str(get_settings().db_url))
    with engine.connect() as connection:
        # The version table lives in the schema, so the schema must exist first.
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table_schema=SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
