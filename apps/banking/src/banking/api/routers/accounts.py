"""Account pages: list, declare, edit, close and delete."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.services import AccountServiceDep, BankServiceDep
from banking.api.rendering import render, validate
from banking.api.schemas.accounts import AccountForm, CloseForm
from banking.api.schemas.common import Id
from banking.databases.models import Account, AccountType
from banking.services.accounts.account_service import AccountFields
from banking.services.banks.bank_service import BankService
from banking.services.errors import InvalidError

router = APIRouter(prefix="/accounts")

TYPE_LABELS = {
    AccountType.CURRENT: "Current",
    AccountType.SAVINGS: "Savings",
    AccountType.PEA: "PEA",
    AccountType.LIFE_INSURANCE: "Life insurance",
}


def _render_form(
    request: Request,
    banks: BankService,
    account: Account | None = None,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    return render(
        request,
        "accounts/form.html",
        status_code,
        account=account,
        banks=banks.list(),
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


@router.get("", response_class=HTMLResponse)
def list_accounts(request: Request, accounts: AccountServiceDep) -> HTMLResponse:
    """Every account, open ones first; closed accounts stay listed."""
    return render(
        request,
        "accounts/list.html",
        accounts=accounts.list(),
        type_labels=TYPE_LABELS,
    )


@router.get("/new", response_class=HTMLResponse)
def new_account(request: Request, banks: BankServiceDep) -> HTMLResponse:
    """Form to declare an account."""
    return _render_form(request, banks)


@router.post("")
def create_account(
    request: Request,
    accounts: AccountServiceDep,
    banks: BankServiceDep,
    data: FormDep,
) -> Response:
    """Declare an account; re-render the form with errors if invalid."""
    form, errors = validate(AccountForm, data)
    if form is not None:
        try:
            account = accounts.create(AccountFields(**form.model_dump()))
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse(f"/accounts/{account.id}", status_code=303)
    return _render_form(request, banks, None, 422, values=data, errors=errors)


@router.get("/{account_id}", response_class=HTMLResponse)
def show_account(
    request: Request, accounts: AccountServiceDep, account_id: Id
) -> HTMLResponse:
    """An account's details, with the close form while it is open."""
    return _render_detail(
        request, accounts.get(account_id), closed_on=date.today().isoformat()
    )


@router.get("/{account_id}/edit", response_class=HTMLResponse)
def edit_account(
    request: Request, accounts: AccountServiceDep, banks: BankServiceDep, account_id: Id
) -> HTMLResponse:
    """Form to edit an account, prefilled with its current values."""
    account = accounts.get(account_id)
    return _render_form(request, banks, account, values=account)


@router.post("/{account_id}")
def update_account(
    request: Request,
    accounts: AccountServiceDep,
    banks: BankServiceDep,
    data: FormDep,
    account_id: Id,
) -> Response:
    """Edit an account; re-render the form with errors if invalid."""
    form, errors = validate(AccountForm, data)
    if form is not None:
        try:
            accounts.update(account_id, AccountFields(**form.model_dump()))
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse(f"/accounts/{account_id}", status_code=303)
    account = accounts.get(account_id)
    return _render_form(request, banks, account, 422, values=data, errors=errors)


@router.post("/{account_id}/close")
def close_account(
    request: Request, accounts: AccountServiceDep, data: FormDep, account_id: Id
) -> Response:
    """Close an account; re-render its page with errors if invalid."""
    form, errors = validate(CloseForm, data)
    if form is not None:
        try:
            accounts.close(account_id, form.closed_on)
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse(f"/accounts/{account_id}", status_code=303)
    account = accounts.get(account_id)
    closed_on = data.get("closed_on", "")
    return _render_detail(request, account, 422, closed_on=closed_on, errors=errors)


@router.post("/{account_id}/delete")
def delete_account(accounts: AccountServiceDep, account_id: Id) -> Response:
    """Delete an account and all its history."""
    accounts.delete(account_id)
    return RedirectResponse("/accounts", status_code=303)
