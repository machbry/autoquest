"""FastAPI entry point: `uvicorn banking.main:app`."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from banking.admin import create_admin
from banking.api.routers import health, imports
from banking.config import get_settings
from banking.databases.engine import get_engine
from banking.databases.repositories.base import ConstraintViolation
from banking.domains.errors import NotFoundError

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# No header: not a browser (tests, scripts). "none": typed or bookmarked by the user.
ALLOWED_FETCH_SITES = {None, "same-origin", "none"}


def hide_private_request_data(record: logging.LogRecord) -> bool:
    """Keep only method, path and status in uvicorn's access log.

    Searches and filters put descriptions and amounts in the query.
    """
    _, method, path, version, status = cast(tuple[Any, ...], record.args)
    record.args = ("-", method, path.partition("?")[0], version, status)
    return True


logging.getLogger("uvicorn.access").addFilter(hide_private_request_data)


def create_app(admin_sessions: sessionmaker[Session] | None = None) -> FastAPI:
    """Build the app; fails fast if the configuration is invalid.

    `admin_sessions` makes the admin's sessions (tests bind them to their own).
    """
    settings = get_settings()
    app = FastAPI(title="banking", docs_url=None, redoc_url=None, openapi_url=None)
    for module in (health, imports):
        app.include_router(module.router)
    sessions = admin_sessions or sessionmaker(get_engine(), expire_on_commit=False)
    create_admin(sessions, settings.secret_key.get_secret_value()).mount_to(app)

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        """Send visitors to the Import page, where the monthly routine starts."""
        return RedirectResponse("/imports")

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

    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, exc: NotFoundError) -> Response:
        """Answer 404 for an item that doesn't exist."""
        return PlainTextResponse("Not found", status_code=404)

    # Postgres messages quote the values at fault (names, account numbers), which must
    # never reach the logs: database errors are logged by code only.
    @app.exception_handler(ConstraintViolation)
    async def unexpected_constraint(
        request: Request, exc: ConstraintViolation
    ) -> Response:
        """Log a constraint no service expected by its name only."""
        logger.error("constraint %s broken on %s", exc.constraint, request.url.path)
        return PlainTextResponse("Database error", status_code=500)

    @app.exception_handler(DBAPIError)
    async def database_error(request: Request, exc: DBAPIError) -> Response:
        """Log a database error by its SQLSTATE code only."""
        sqlstate = getattr(exc.orig, "sqlstate", None)
        logger.error(
            "database error %s on %s %s", sqlstate, request.method, request.url.path
        )
        return PlainTextResponse("Database error", status_code=500)

    return app


app = create_app()
