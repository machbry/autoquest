"""Accounts: declare, edit and close them (closing keeps their history)."""

import logging
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from banking.db import get_session
from banking.models import Account, AccountType, Bank
from banking.web import templates

logger = logging.getLogger(__name__)
router = APIRouter()

BANK_LABELS = {
    Bank.BANQUE_POSTALE: "La Banque Postale",
    Bank.CFCAL: "CFCAL",
    Bank.FORTUNEO: "Fortuneo",
    Bank.GOODVEST: "Goodvest",
}
TYPE_LABELS = {
    AccountType.CURRENT: "Current",
    AccountType.SAVINGS: "Savings",
    AccountType.PEA: "PEA",
    AccountType.LIFE_INSURANCE: "Life insurance",
}

# Database constraints a form can break, mapped to the field to blame.
Constraints = dict[str, tuple[str, str]]
CLOSED_AFTER_OPENED = "ck_accounts_closed_after_opened"
ACCOUNT_CONSTRAINTS: Constraints = {
    "uq_accounts_name": ("name", "Another account already has this name."),
    "uq_accounts_account_number": (
        "account_number",
        "Another account already has this number.",
    ),
    CLOSED_AFTER_OPENED: ("opened_on", "The account was closed before this date."),
}
CLOSE_CONSTRAINTS: Constraints = {
    CLOSED_AFTER_OPENED: ("closed_on", "An account can't close before it opened."),
}

Errors = dict[str, str]
SessionDep = Annotated[Session, Depends(get_session)]
# Ids are INTEGER: a larger value would make Postgres fail instead of finding nothing.
AccountId = Annotated[int, Path(ge=1, le=2**31 - 1)]


class AccountForm(BaseModel):
    """Fields of the create and edit forms."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    bank: Bank
    type: AccountType
    account_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{1,34}$")
    opened_on: date

    @field_validator("account_number", mode="before")
    @classmethod
    def normalize_account_number(cls, value: Any) -> Any:
        """Drop spaces and uppercase, so formatting never hides a duplicate."""
        if isinstance(value, str):
            value = value.replace(" ", "").upper()
            return value or None
        return value


class CloseForm(BaseModel):
    """Fields of the close form."""

    closed_on: date


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


def _validate[T: BaseModel](
    model: type[T], data: dict[str, Any]
) -> tuple[T | None, Errors]:
    """Validate form data, returning field errors instead of raising."""
    try:
        return model.model_validate(data), {}
    except ValidationError as exc:
        return None, {str(error["loc"][0]): error["msg"] for error in exc.errors()}


def _commit(session: Session, constraints: Constraints) -> Errors:
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


def _render(
    request: Request, template: str, status_code: int = 200, **context: Any
) -> HTMLResponse:
    defaults: dict[str, Any] = {"account": None, "values": {}, "errors": {}}
    return templates.TemplateResponse(
        request,
        template,
        {"bank_labels": BANK_LABELS, "type_labels": TYPE_LABELS, **defaults, **context},
        status_code=status_code,
    )


def _get_account(session: Session, account_id: int) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def _save_form(
    request: Request,
    session: Session,
    account: Account | None,
    data: dict[str, Any],
) -> Response:
    """Validate and store a create or edit form; re-render it with errors if invalid."""
    form, errors = _validate(AccountForm, data)
    if form is not None:
        target = account or Account()
        for field, value in form.model_dump().items():
            setattr(target, field, value)
        session.add(target)
        errors = _commit(session, ACCOUNT_CONSTRAINTS)
        if not errors:
            logger.info("account %s %s", target.id, "updated" if account else "created")
            return RedirectResponse(f"/accounts/{target.id}", status_code=303)
    return _render(
        request,
        "accounts/form.html",
        status_code=422,
        account=account,
        values=data,
        errors=errors,
    )


@router.get("/", response_class=HTMLResponse)
def list_accounts(request: Request, session: SessionDep) -> HTMLResponse:
    """Every account, open ones first; closed accounts stay listed."""
    accounts = session.scalars(
        select(Account).order_by(Account.closed_on.is_not(None), Account.name)
    ).all()
    return _render(request, "accounts/list.html", accounts=accounts)


@router.get("/accounts/new", response_class=HTMLResponse)
def new_account(request: Request) -> HTMLResponse:
    """Form to declare an account."""
    return _render(request, "accounts/form.html")


@router.post("/accounts")
def create_account(request: Request, session: SessionDep, data: FormDep) -> Response:
    """Declare an account."""
    return _save_form(request, session, None, data)


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
def show_account(
    request: Request, session: SessionDep, account_id: AccountId
) -> HTMLResponse:
    """An account's details, with the close form while it is open."""
    return _render(
        request,
        "accounts/detail.html",
        account=_get_account(session, account_id),
        closed_on=date.today().isoformat(),
    )


@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse)
def edit_account(
    request: Request, session: SessionDep, account_id: AccountId
) -> HTMLResponse:
    """Form to edit an account, prefilled with its current values."""
    account = _get_account(session, account_id)
    return _render(request, "accounts/form.html", account=account, values=account)


@router.post("/accounts/{account_id}")
def update_account(
    request: Request, session: SessionDep, data: FormDep, account_id: AccountId
) -> Response:
    """Edit an account; its closing date can't be changed."""
    return _save_form(request, session, _get_account(session, account_id), data)


@router.post("/accounts/{account_id}/close")
def close_account(
    request: Request, session: SessionDep, data: FormDep, account_id: AccountId
) -> Response:
    """Close an open account. There is no reopening."""
    account = _get_account(session, account_id)
    if account.closed_on is not None:
        raise HTTPException(status_code=409, detail="Account already closed")
    form, errors = _validate(CloseForm, data)
    if form is not None:
        account.closed_on = form.closed_on
        errors = _commit(session, CLOSE_CONSTRAINTS)
        if not errors:
            logger.info("account %s closed", account.id)
            return RedirectResponse(f"/accounts/{account.id}", status_code=303)
    return _render(
        request,
        "accounts/detail.html",
        status_code=422,
        account=account,
        closed_on=data.get("closed_on", ""),
        errors=errors,
    )
