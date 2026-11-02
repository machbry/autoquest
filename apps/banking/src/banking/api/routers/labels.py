"""Labels: the operations table's bulk actions on the selected operations."""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.pages import OperationsPage, OperationsPageDep
from banking.api.dependencies.services import LabelServiceDep
from banking.api.rendering import Errors, validate
from banking.api.schemas.labels import CategorizeForm, SelectionForm
from banking.api.schemas.operations import TableForm
from banking.domains.errors import InvalidError

router = APIRouter(prefix="/labels")


def _back_to_table(form: SelectionForm, notice: str, count: int) -> RedirectResponse:
    """Back to the same view of the table, saying what the action did."""
    return RedirectResponse(
        form.url(("notice", notice), ("count", count)), status_code=303
    )


def _render_table(
    request: Request, page: OperationsPage, data: dict[str, Any], errors: Errors
) -> HTMLResponse:
    """The table again, as posted (filters, ticks, fields), with the errors."""
    query, query_errors = validate(TableForm, data)
    return page.render(
        request,
        query or TableForm(),
        422,
        values=data,
        errors=query_errors | errors,
    )


@router.post("")
def create_label(
    request: Request, labels: LabelServiceDep, page: OperationsPageDep, data: FormDep
) -> Response:
    """Set a category on the selected operations: an existing one, or a new one."""
    form, errors = validate(CategorizeForm, data)
    if form is not None:
        try:
            count = labels.set_category(form.id, form.category_id, form.new_category)
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return _back_to_table(form, "set", count)
    return _render_table(request, page, data, errors)


@router.post("/delete")
def delete_labels(
    request: Request, labels: LabelServiceDep, page: OperationsPageDep, data: FormDep
) -> Response:
    """Remove the category of the selected operations: back to unlabelled."""
    form, errors = validate(SelectionForm, data)
    if form is None:
        return _render_table(request, page, data, errors)
    return _back_to_table(form, "removed", labels.delete_many(form.id))
