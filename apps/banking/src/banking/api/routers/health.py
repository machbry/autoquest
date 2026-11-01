"""Health check."""

from fastapi import APIRouter
from sqlalchemy import text

from banking.api.dependencies.database import SessionDep

router = APIRouter()


@router.get("/healthz")
def healthz(session: SessionDep) -> dict[str, str]:
    """Report that the app is up and the database answers."""
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
