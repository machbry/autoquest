"""Import of an export file into an account, from the account's page."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from banking.api.dependencies.forms import UploadDep
from banking.api.dependencies.services import (
    AccountServiceDep,
    ImportServiceDep,
    OperationServiceDep,
)
from banking.api.routers.accounts import render_account_page
from banking.api.schemas.common import Id
from banking.domains.errors import InvalidError

router = APIRouter(prefix="/accounts/{account_id}/imports")


@router.post("")
def create_import(
    request: Request,
    accounts: AccountServiceDep,
    imports: ImportServiceDep,
    operations: OperationServiceDep,
    content: UploadDep,
    account_id: Id,
) -> Response:
    """Import an export; show its summary on the account's page, or why it failed."""
    try:
        imported = imports.create(account_id, content)
    except InvalidError as exc:
        return render_account_page(
            request,
            accounts,
            imports,
            operations,
            account_id,
            422,
            errors={exc.field: exc.message},
        )
    return RedirectResponse(
        f"/accounts/{account_id}?import_id={imported.id}", status_code=303
    )
