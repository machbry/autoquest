"""Accounts: declare, edit, close (keeps the history) and delete them."""

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from banking.models import Account, AccountType, Bank
from banking.web import (
    Constraints,
    FormDep,
    Id,
    SessionDep,
    commit,
    not_found,
    render,
    validate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

TYPE_LABELS = {
    AccountType.CURRENT: "Current",
    AccountType.SAVINGS: "Savings",
    AccountType.PEA: "PEA",
    AccountType.LIFE_INSURANCE: "Life insurance",
}
CLOSED_AFTER_OPENED = "ck_accounts_closed_after_opened"
ACCOUNT_CONSTRAINTS: Constraints = {
    "uq_accounts_name": ("name", "Another account already has this name."),
    "uq_accounts_account_number": (
        "account_number",
        "Another account already has this number.",
    ),
    "fk_accounts_bank_id": ("bank_id", "Unknown bank."),
    CLOSED_AFTER_OPENED: ("opened_on", "The account was closed before this date."),
}
CLOSE_CONSTRAINTS: Constraints = {
    CLOSED_AFTER_OPENED: ("closed_on", "An account can't close before it opened."),
}


class AccountForm(BaseModel):
    """Fields of the create and edit forms."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    bank_id: int = Field(ge=1, le=2**31 - 1)
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


def _render_form(
    request: Request,
    session: Session,
    account: Account | None = None,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    return render(
        request,
        "accounts/form.html",
        status_code,
        account=account,
        banks=session.scalars(select(Bank).order_by(Bank.name)).all(),
        type_labels=TYPE_LABELS,
        **context,
    )


def _render_detail(
    request: Request, account: Account, status_code: int = 200, **context: Any
) -> HTMLResponse:
    return render(
        request,
        "accounts/detail.html",
        status_code,
        account=account,
        type_labels=TYPE_LABELS,
        **context,
    )


def _save_form(
    request: Request,
    session: Session,
    account: Account | None,
    data: dict[str, Any],
) -> Response:
    """Validate and store a create or edit form; re-render it with errors if invalid."""
    form, errors = validate(AccountForm, data)
    if form is not None:
        target = account or Account()
        for field, value in form.model_dump().items():
            setattr(target, field, value)
        session.add(target)
        errors = commit(session, ACCOUNT_CONSTRAINTS)
        if not errors:
            logger.info("account %s %s", target.id, "updated" if account else "created")
            return RedirectResponse(f"/accounts/{target.id}", status_code=303)
    return _render_form(request, session, account, 422, values=data, errors=errors)


@router.get("/", response_class=HTMLResponse)
def list_accounts(request: Request, session: SessionDep) -> HTMLResponse:
    """Every account, open ones first; closed accounts stay listed."""
    accounts = session.scalars(
        select(Account)
        .options(joinedload(Account.bank))
        .order_by(Account.closed_on.is_not(None), Account.name)
    ).all()
    return render(
        request, "accounts/list.html", accounts=accounts, type_labels=TYPE_LABELS
    )


@router.get("/accounts/new", response_class=HTMLResponse)
def new_account(request: Request, session: SessionDep) -> HTMLResponse:
    """Form to declare an account."""
    return _render_form(request, session)


@router.post("/accounts")
def create_account(request: Request, session: SessionDep, data: FormDep) -> Response:
    """Declare an account."""
    return _save_form(request, session, None, data)


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
def show_account(request: Request, session: SessionDep, account_id: Id) -> HTMLResponse:
    """An account's details, with the close form while it is open."""
    account = not_found(session.get(Account, account_id))
    return _render_detail(request, account, closed_on=date.today().isoformat())


@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse)
def edit_account(request: Request, session: SessionDep, account_id: Id) -> HTMLResponse:
    """Form to edit an account, prefilled with its current values."""
    account = not_found(session.get(Account, account_id))
    return _render_form(request, session, account, values=account)


@router.post("/accounts/{account_id}")
def update_account(
    request: Request, session: SessionDep, data: FormDep, account_id: Id
) -> Response:
    """Edit an account; its closing date can't be changed."""
    account = not_found(session.get(Account, account_id))
    return _save_form(request, session, account, data)


@router.post("/accounts/{account_id}/close")
def close_account(
    request: Request, session: SessionDep, data: FormDep, account_id: Id
) -> Response:
    """Close an open account. There is no reopening."""
    account = not_found(session.get(Account, account_id))
    if account.closed_on is not None:
        raise HTTPException(status_code=409, detail="Account already closed")
    form, errors = validate(CloseForm, data)
    if form is not None:
        account.closed_on = form.closed_on
        errors = commit(session, CLOSE_CONSTRAINTS)
        if not errors:
            logger.info("account %s closed", account.id)
            return RedirectResponse(f"/accounts/{account.id}", status_code=303)
    return _render_detail(
        request, account, 422, closed_on=data.get("closed_on", ""), errors=errors
    )


@router.post("/accounts/{account_id}/delete")
def delete_account(session: SessionDep, account_id: Id) -> Response:
    """Delete an account and, through the database's cascades, all its history."""
    session.delete(not_found(session.get(Account, account_id)))
    session.commit()
    logger.info("account %s deleted", account_id)
    return RedirectResponse("/", status_code=303)
