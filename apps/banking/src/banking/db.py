"""Database engine and sessions."""

from collections.abc import Iterator
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from banking.config import get_settings

SCHEMA = "banking"


@cache
def get_engine() -> Engine:
    """Return the app-wide engine, created on first use."""
    # Hidden parameters keep personal data (names, amounts) out of logged DB errors.
    return create_engine(
        str(get_settings().db_url), pool_pre_ping=True, hide_parameters=True
    )


def get_session() -> Iterator[Session]:
    """Yield a session for one request (FastAPI dependency)."""
    with Session(get_engine()) as session:
        yield session
