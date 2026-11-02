"""HTML pages: templates, and the form validation errors they display."""

from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError

from banking.domains.account import AccountType

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["type_labels"] = {
    AccountType.CURRENT: "Current",
    AccountType.SAVINGS: "Savings",
    AccountType.PEA: "PEA",
    AccountType.LIFE_INSURANCE: "Life insurance",
}


def operations_url(account_id: int, month: date, unlabelled: bool = False) -> str:
    """The admin's operations table, filtered on an account's month."""
    last = month.replace(day=monthrange(month.year, month.month)[1])
    rules = [f"account__in={account_id}", f"operation_date__between={month}..{last}"]
    if unlabelled:
        rules.append("category__is_null")
    return "/admin/operations/list?" + urlencode({"filter": " AND ".join(rules)})


templates.env.globals["operations_url"] = operations_url

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
