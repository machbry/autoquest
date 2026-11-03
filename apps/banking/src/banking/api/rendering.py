"""HTML pages: templates, and the links they build."""

from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def operations_url(account_id: int, month: date, unlabelled: bool = False) -> str:
    """The admin's operations table, filtered on an account's month."""
    last = month.replace(day=monthrange(month.year, month.month)[1])
    rules = [f"account__in={account_id}", f"operation_date__between={month}..{last}"]
    if unlabelled:
        rules.append("category__is_null")
    return "/admin/operations/list?" + urlencode({"filter": " AND ".join(rules)})


templates.env.globals["operations_url"] = operations_url


def render(
    request: Request, template: str, status_code: int = 200, **context: Any
) -> HTMLResponse:
    """Render a page; `errors` (field → message) defaults to empty for the forms."""
    return templates.TemplateResponse(
        request,
        template,
        {"errors": {}, **context},
        status_code=status_code,
    )
