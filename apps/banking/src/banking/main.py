"""FastAPI entry point: `uvicorn banking.main:app`."""

import logging
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from banking import accounts, banks
from banking.config import get_settings
from banking.db import get_session

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# No header: not a browser (tests, scripts). "none": typed or bookmarked by the user.
ALLOWED_FETCH_SITES = {None, "same-origin", "none"}


def create_app() -> FastAPI:
    """Build the app; fails fast if the configuration is invalid."""
    get_settings()
    app = FastAPI(title="banking", docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(accounts.router)
    app.include_router(banks.router)

    @app.middleware("http")
    async def refuse_cross_site(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Refuse state-changing requests a browser sent from another site.

        Until access control exists (#14), this stops any web page from making my
        browser post forms to the app.
        """
        if (
            request.method not in SAFE_METHODS
            and request.headers.get("sec-fetch-site") not in ALLOWED_FETCH_SITES
        ):
            return PlainTextResponse("Cross-site request refused", status_code=403)
        return await call_next(request)

    @app.exception_handler(DBAPIError)
    async def database_error(request: Request, exc: DBAPIError) -> Response:
        """Log a database error by its SQLSTATE code only.

        Postgres messages quote the values at fault (names, account numbers), which
        must never reach the logs.
        """
        sqlstate = getattr(exc.orig, "sqlstate", None)
        logger.error(
            "database error %s on %s %s", sqlstate, request.method, request.url.path
        )
        return PlainTextResponse("Database error", status_code=500)

    @app.get("/healthz")
    def healthz(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        """Report that the app is up and the database answers."""
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
