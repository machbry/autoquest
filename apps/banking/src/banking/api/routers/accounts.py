"""Account pages: list, declare, show, edit, close and delete."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.services import (
    AccountServiceDep,
    BankServiceDep,
    ImportServiceDep,
    OperationServiceDep,
)
from banking.api.rendering import render, validate
from banking.api.schemas.accounts import AccountForm, CloseForm
from banking.api.schemas.common import MAX_ID, Id
from banking.domains.account import Account, AccountFields, AccountType
from banking.domains.errors import InvalidError
from banking.services.accounts.account_service import AccountService
from banking.services.banks.bank_service import BankService
from banking.services.imports.import_service import ImportService
from banking.services.operations.operation_service import OperationService

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


def render_account_page(
    request: Request,
    accounts: AccountService,
    imports: ImportService,
    operations: OperationService,
    account_id: int,
    status_code: int = 200,
    summary_id: int | None = None,
    **context: Any,
) -> HTMLResponse:
    """An account's page: details, freshness, import form and history, operations.

    `summary_id` is an import of the account to show the summary of.
    """
    account = accounts.get(account_id)
    history = imports.list_for_account(account_id)
    context.setdefault("closed_on", date.today().isoformat())
    return render(
        request,
        "accounts/detail.html",
        status_code,
        account=account,
        type_labels=TYPE_LABELS,
        freshness=accounts.get_freshness(account_id),
        imports=history,
        summary=next((item for item in history if item.id == summary_id), None),
        operations=operations.list_for_account(account_id),
        **context,
    )


@router.get("", response_class=HTMLResponse)
def list_accounts(request: Request, accounts: AccountServiceDep) -> HTMLResponse:
    """Every account with its freshness, open ones first; closed ones stay listed."""
    return render(
        request,
        "accounts/list.html",
        accounts=accounts.list_with_freshness(),
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
    request: Request,
    accounts: AccountServiceDep,
    imports: ImportServiceDep,
    operations: OperationServiceDep,
    account_id: Id,
    import_id: Annotated[int | None, Query(ge=1, le=MAX_ID)] = None,
) -> HTMLResponse:
    """An account's page; `import_id` shows the summary of one of its imports."""
    return render_account_page(
        request, accounts, imports, operations, account_id, summary_id=import_id
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
    request: Request,
    accounts: AccountServiceDep,
    imports: ImportServiceDep,
    operations: OperationServiceDep,
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
    return render_account_page(
        request,
        accounts,
        imports,
        operations,
        account_id,
        422,
        closed_on=data.get("closed_on", ""),
        errors=errors,
    )


@router.post("/{account_id}/delete")
def delete_account(accounts: AccountServiceDep, account_id: Id) -> Response:
    """Delete an account and all its history."""
    accounts.delete(account_id)
    return RedirectResponse("/accounts", status_code=303)
