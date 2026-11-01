"""Shared fixtures; integration tests need the local Postgres running."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine

# Default to the docker-compose database, before the app reads its settings.
# 127.0.0.1, not localhost: on Windows localhost tries IPv6 first and hangs.
os.environ.setdefault(
    "BANKING_DB_URL", "postgresql+psycopg://banking:banking@127.0.0.1:5432/banking"
)

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Engine on a database migrated to the latest revision."""
    command.upgrade(Config(ALEMBIC_INI), "head")
    engine = create_engine(os.environ["BANKING_DB_URL"])
    yield engine
    engine.dispose()
