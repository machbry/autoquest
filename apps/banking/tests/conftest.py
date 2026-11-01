"""Shared fixtures; integration tests need the local Postgres running."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from banking.databases.models import BankModel

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


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Session whose writes, commits included, are rolled back after the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(session: Session) -> TestClient:
    """Client of an app whose requests all use the test session."""
    # Imported late: the app reads its settings, set above, at import time.
    from banking.api.dependencies.database import get_session
    from banking.main import create_app

    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def bank(session: Session) -> BankModel:
    """A bank to attach accounts to."""
    bank = BankModel(name="Test bank")
    session.add(bank)
    session.commit()
    return bank
