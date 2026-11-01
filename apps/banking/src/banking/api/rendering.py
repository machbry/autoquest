"""HTML pages: templates, and the form validation errors they display."""

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Field name → message, shown next to the field.
Errors = dict[str, str]


def validate[T: BaseModel](
    schema: type[T], data: dict[str, Any]
) -> tuple[T | None, Errors]:
    """Validate form data, returning field errors instead of raising."""
    try:
        return schema.model_validate(data), {}
    except ValidationError as exc:
        return None, {str(error["loc"][0]): error["msg"] for error in exc.errors()}


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
