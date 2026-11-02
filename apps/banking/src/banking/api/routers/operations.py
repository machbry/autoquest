"""The operations table: filter, sort and select operations to label in bulk."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from banking.api.dependencies.forms import QueryDep
from banking.api.dependencies.pages import OperationsPageDep
from banking.api.rendering import validate
from banking.api.schemas.operations import TableForm

router = APIRouter(prefix="/operations")


@router.get("", response_class=HTMLResponse)
def list_operations(
    request: Request, page: OperationsPageDep, query: QueryDep
) -> HTMLResponse:
    """The operations the filters keep, sorted, with the rows ticked so far."""
    form, errors = validate(TableForm, query)
    if form is None:
        return page.render(request, TableForm(), 422, errors=errors)
    return page.render(request, form)
