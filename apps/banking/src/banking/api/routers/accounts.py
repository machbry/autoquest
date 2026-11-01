"""Account pages: list, declare, show, edit, close and delete."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.pages import AccountPageDep
from banking.api.dependencies.services import AccountServiceDep, BankServiceDep
from banking.api.rendering import render, validate
from banking.api.schemas.accounts import AccountForm, CloseForm
from banking.api.schemas.common import MAX_ID, Id
from banking.domains.account import Account, AccountFields
from banking.domains.errors import InvalidError
from banking.services.banks.bank_service import BankService

router = APIRouter(prefix="/accounts")


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
        **context,
    )


@router.get("", response_class=HTMLResponse)
def list_accounts(request: Request, accounts: AccountServiceDep) -> HTMLResponse:
    """Every account with its freshness, open ones first; closed ones stay listed."""
    return render(
        request, "accounts/list.html", accounts=accounts.list_with_freshness()
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
    request: Request,
    page: AccountPageDep,
    account_id: Id,
    import_id: Annotated[int | None, Query(ge=1, le=MAX_ID)] = None,
) -> HTMLResponse:
    """An account's page; `import_id` shows the summary of one of its imports."""
    return page.render(request, account_id, summary_id=import_id)


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
    request: Request,
    accounts: AccountServiceDep,
    page: AccountPageDep,
    data: FormDep,
    account_id: Id,
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
    closed_on = data.get("closed_on", "")
    return page.render(request, account_id, 422, closed_on=closed_on, errors=errors)


@router.post("/{account_id}/delete")
def delete_account(accounts: AccountServiceDep, account_id: Id) -> Response:
    """Delete an account and all its history."""
    accounts.delete(account_id)
    return RedirectResponse("/accounts", status_code=303)
