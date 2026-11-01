"""FastAPI entry point: `uvicorn banking.main:app`."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.exc import DBAPIError

from banking.api.routers import accounts, banks, health
from banking.config import get_settings
from banking.databases.repositories.base import ConstraintViolation
from banking.domains.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# No header: not a browser (tests, scripts). "none": typed or bookmarked by the user.
ALLOWED_FETCH_SITES = {None, "same-origin", "none"}


def create_app() -> FastAPI:
    """Build the app; fails fast if the configuration is invalid."""
    get_settings()
    app = FastAPI(title="banking", docs_url=None, redoc_url=None, openapi_url=None)
    for module in (accounts, banks, health):
        app.include_router(module.router)

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        """Send visitors to the accounts list."""
        return RedirectResponse("/accounts")

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

    @app.exception_handler(ConflictError)
    async def conflict(request: Request, exc: ConflictError) -> Response:
        """Answer 409 when a router didn't handle a conflict itself."""
        return PlainTextResponse(exc.message, status_code=409)

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
