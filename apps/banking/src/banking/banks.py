"""Banks: add, rename and delete them; a bank in use can't be deleted."""

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from banking.models import Account, Bank
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
router = APIRouter(prefix="/banks")

NAME_CONSTRAINTS: Constraints = {
    "uq_banks_name": ("name", "Another bank already has this name."),
}
DELETE_CONSTRAINTS: Constraints = {
    "fk_accounts_bank_id": ("delete", "Accounts still use this bank."),
}


class BankForm(BaseModel):
    """Fields of the add and rename forms."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)


def _render_list(
    request: Request, session: Session, status_code: int = 200, **context: Any
) -> HTMLResponse:
    """The banks with how many accounts use each, and the add form."""
    banks = session.execute(
        select(Bank, func.count(Account.id))
        .outerjoin(Account, Account.bank_id == Bank.id)
        .group_by(Bank.id)
        .order_by(Bank.name)
    ).all()
    return render(request, "banks/list.html", status_code, banks=banks, **context)


def _save(
    request: Request, session: Session, bank: Bank | None, data: dict[str, Any]
) -> Response:
    """Add or rename a bank; re-render the page it came from with errors if invalid."""
    form, errors = validate(BankForm, data)
    if form is not None:
        target = bank or Bank()
        target.name = form.name
        session.add(target)
        errors = commit(session, NAME_CONSTRAINTS)
        if not errors:
            logger.info("bank %s %s", target.id, "renamed" if bank else "added")
            return RedirectResponse("/banks", status_code=303)
    if bank is None:
        return _render_list(request, session, 422, values=data, errors=errors)
    return render(
        request, "banks/form.html", 422, bank=bank, values=data, errors=errors
    )


@router.get("", response_class=HTMLResponse)
def list_banks(request: Request, session: SessionDep) -> HTMLResponse:
    """Every bank, with the form to add one."""
    return _render_list(request, session)


@router.post("")
def add_bank(request: Request, session: SessionDep, data: FormDep) -> Response:
    """Add a bank."""
    return _save(request, session, None, data)


@router.get("/{bank_id}/edit", response_class=HTMLResponse)
def edit_bank(request: Request, session: SessionDep, bank_id: Id) -> HTMLResponse:
    """Form to rename a bank."""
    bank = not_found(session.get(Bank, bank_id))
    return render(request, "banks/form.html", bank=bank, values=bank)


@router.post("/{bank_id}")
def rename_bank(
    request: Request, session: SessionDep, data: FormDep, bank_id: Id
) -> Response:
    """Rename a bank."""
    return _save(request, session, not_found(session.get(Bank, bank_id)), data)


@router.post("/{bank_id}/delete")
def delete_bank(request: Request, session: SessionDep, bank_id: Id) -> Response:
    """Delete a bank, unless an account still uses it (the database refuses)."""
    session.delete(not_found(session.get(Bank, bank_id)))
    if errors := commit(session, DELETE_CONSTRAINTS):
        return _render_list(request, session, 409, errors=errors, failed_id=bank_id)
    logger.info("bank %s deleted", bank_id)
    return RedirectResponse("/banks", status_code=303)
