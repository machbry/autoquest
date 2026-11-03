"""The Import page: data freshness, and import of an export file into an account."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import UploadDep
from banking.api.dependencies.pages import ImportPageDep
from banking.api.dependencies.services import ImportServiceDep
from banking.api.schemas.common import Id, OptionalQueryId
from banking.domains.errors import InvalidError

router = APIRouter()


@router.get("/imports", response_class=HTMLResponse)
def list_imports(
    request: Request,
    page: ImportPageDep,
    account_id: OptionalQueryId = None,
    import_id: OptionalQueryId = None,
) -> HTMLResponse:
    """Every account's freshness; `account_id` shows its imports, `import_id` one."""
    return page.render(request, account_id, summary_id=import_id)


@router.post("/accounts/{account_id}/imports")
def create_import(
    request: Request,
    imports: ImportServiceDep,
    page: ImportPageDep,
    content: UploadDep,
    account_id: Id,
) -> Response:
    """Import an export; show its summary on the Import page, or why it failed."""
    try:
        imported = imports.create(account_id, content)
    except InvalidError as exc:
        return page.render(request, account_id, 422, errors={exc.field: exc.message})
    return RedirectResponse(
        f"/imports?account_id={account_id}&import_id={imported.id}", status_code=303
    )
