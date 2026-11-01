"""Database session of a request."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from banking.databases.engine import get_engine


def get_session() -> Iterator[Session]:
    """Yield a session for one request."""
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
