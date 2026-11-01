"""Bank pages: list, create, update (rename) and delete."""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.services import BankServiceDep
from banking.api.rendering import render, validate
from banking.api.schemas.banks import BankForm
from banking.api.schemas.common import Id
from banking.domains.bank import BankFields
from banking.domains.errors import ConflictError, InvalidError
from banking.services.banks.bank_service import BankService

router = APIRouter(prefix="/banks")


def _render_list(
    request: Request, banks: BankService, status_code: int = 200, **context: Any
) -> HTMLResponse:
    return render(
        request,
        "banks/list.html",
        status_code,
        banks=banks.list_with_account_counts(),
        **context,
    )


@router.get("", response_class=HTMLResponse)
def list_banks(request: Request, banks: BankServiceDep) -> HTMLResponse:
    """Every bank with how many accounts use it, and the form to create one."""
    return _render_list(request, banks)


@router.post("")
def create_bank(request: Request, banks: BankServiceDep, data: FormDep) -> Response:
    """Create a bank; re-render the list (holding its form) with errors if invalid."""
    form, errors = validate(BankForm, data)
    if form is not None:
        try:
            banks.create(BankFields(**form.model_dump()))
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse("/banks", status_code=303)
    return _render_list(request, banks, 422, values=data, errors=errors)


@router.get("/{bank_id}/edit", response_class=HTMLResponse)
def edit_bank(request: Request, banks: BankServiceDep, bank_id: Id) -> HTMLResponse:
    """Form to update (rename) a bank, prefilled with its current name."""
    bank = banks.get(bank_id)
    return render(request, "banks/form.html", bank=bank, values=bank)


@router.post("/{bank_id}")
def update_bank(
    request: Request, banks: BankServiceDep, data: FormDep, bank_id: Id
) -> Response:
    """Update (rename) a bank; re-render the form with errors if invalid."""
    form, errors = validate(BankForm, data)
    if form is not None:
        try:
            banks.update(bank_id, BankFields(**form.model_dump()))
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse("/banks", status_code=303)
    bank = banks.get(bank_id)
    return render(
        request, "banks/form.html", 422, bank=bank, values=data, errors=errors
    )


@router.post("/{bank_id}/delete")
def delete_bank(request: Request, banks: BankServiceDep, bank_id: Id) -> Response:
    """Delete a bank; refused (409) while an account uses it."""
    try:
        banks.delete(bank_id)
    except ConflictError as exc:
        return _render_list(
            request, banks, 409, errors={"delete": exc.message}, failed_id=bank_id
        )
    return RedirectResponse("/banks", status_code=303)
