"""FastAPI entry point: `uvicorn banking.main:app`."""

from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from banking.config import get_settings
from banking.db import get_session


def create_app() -> FastAPI:
    """Build the app; fails fast if the configuration is invalid."""
    get_settings()
    app = FastAPI(title="banking", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    def healthz(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        """Report that the app is up and the database answers."""
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
