"""Shared web pieces: templates, form handling, and DB constraint errors."""

from pathlib import Path as FilePath
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from banking.db import get_session

templates = Jinja2Templates(directory=FilePath(__file__).parent / "templates")

Errors = dict[str, str]
# Database constraints a form can break, mapped to the field to blame and a message.
Constraints = dict[str, tuple[str, str]]
SessionDep = Annotated[Session, Depends(get_session)]
# Ids are INTEGER: a larger value would make Postgres fail instead of finding nothing.
Id = Annotated[int, Path(ge=1, le=2**31 - 1)]


async def form_data(request: Request) -> dict[str, Any]:
    """Read the submitted form.

    Reading a form is async; doing it in a dependency lets the handlers stay sync, so
    FastAPI runs their blocking database calls in a thread, off the event loop.
    """
    data = dict(await request.form())
    # Postgres text can't hold NUL: refuse it here rather than fail on insert.
    if any("\x00" in value for value in data.values() if isinstance(value, str)):
        raise HTTPException(status_code=422, detail="NUL characters are not allowed")
    return data


FormDep = Annotated[dict[str, Any], Depends(form_data)]


def validate[T: BaseModel](
    model: type[T], data: dict[str, Any]
) -> tuple[T | None, Errors]:
    """Validate form data, returning field errors instead of raising."""
    try:
        return model.model_validate(data), {}
    except ValidationError as exc:
        return None, {str(error["loc"][0]): error["msg"] for error in exc.errors()}


def commit(session: Session, constraints: Constraints) -> Errors:
    """Commit, or roll back and blame a field if a known constraint was broken."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        diag = getattr(exc.orig, "diag", None)
        if (error := constraints.get(getattr(diag, "constraint_name", ""))) is None:
            raise
        field, message = error
        return {field: message}
    return {}


def render(
    request: Request, template: str, status_code: int = 200, **context: Any
) -> HTMLResponse:
    """Render a page; `values` and `errors` default to empty for the forms."""
    return templates.TemplateResponse(
        request,
        template,
        {"values": {}, "errors": {}, **context},
        status_code=status_code,
    )


def not_found[T](item: T | None) -> T:
    """Return the item, or answer 404 if it doesn't exist."""
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return item
