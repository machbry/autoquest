"""Labels: the operations table's bulk actions, and editing one label in place.

Every htmx interaction is also a plain link or form: without JavaScript, the same
routes answer with full pages and redirects.
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.htmx import HtmxDep
from banking.api.dependencies.pages import OperationsPage, OperationsPageDep
from banking.api.dependencies.services import (
    CategoryServiceDep,
    LabelServiceDep,
    OperationServiceDep,
)
from banking.api.rendering import Errors, render, validate
from banking.api.schemas.common import Id
from banking.api.schemas.labels import (
    CategorizeForm,
    LabelForm,
    SelectionForm,
)
from banking.api.schemas.operations import TableForm
from banking.domains.errors import InvalidError
from banking.domains.label import Label, LabelFields
from banking.domains.operation import Operation
from banking.services.categories.category_service import CategoryService

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


def _row_url(operation: Operation) -> str:
    """The operation's row on its account page."""
    return f"/accounts/{operation.account_id}#operation-{operation.id}"


def _render_form(
    request: Request,
    categories: CategoryService,
    operation: Operation,
    htmx: bool,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    """The edit form: a table row for htmx, else a page."""
    response = render(
        request,
        "labels/row_form.html" if htmx else "labels/form.html",
        status_code,
        operation=operation,
        categories=categories.list(),
        **context,
    )
    response.headers["Vary"] = "HX-Request"
    return response


def _render_row(
    request: Request, operation: Operation, label: Label | None
) -> HTMLResponse:
    """The operation's row on the account page; focus goes back to its link."""
    response = render(
        request, "labels/row.html", operation=operation, label=label, focus=True
    )
    response.headers["Vary"] = "HX-Request"
    return response


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


@router.get("/{operation_id}/edit", response_class=HTMLResponse)
def edit_label(
    request: Request,
    labels: LabelServiceDep,
    categories: CategoryServiceDep,
    operations: OperationServiceDep,
    htmx: HtmxDep,
    operation_id: Id,
) -> HTMLResponse:
    """Form to label an operation, prefilled with its label's category."""
    operation = operations.get(operation_id)
    label = labels.find(operation_id)
    values = {} if label is None else {"category_id": label.category.id}
    return _render_form(
        request, categories, operation, htmx, label=label, values=values
    )


@router.post("/{operation_id}")
def update_label(
    request: Request,
    labels: LabelServiceDep,
    categories: CategoryServiceDep,
    operations: OperationServiceDep,
    htmx: HtmxDep,
    data: FormDep,
    operation_id: Id,
) -> Response:
    """Set an operation's label, created if it has none yet.

    Answers the updated row for htmx, else goes back to the account page.
    """
    operation = operations.get(operation_id)
    current = labels.find(operation_id)
    form, errors = validate(LabelForm, data)
    if form is not None:
        fields = LabelFields(form.category_id)
        try:
            if current is None:
                label = labels.create(operation_id, fields)
            else:
                label = labels.update(operation_id, fields)
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            if htmx:
                return _render_row(request, operation, label)
            return RedirectResponse(_row_url(operation), status_code=303)
    return _render_form(
        request,
        categories,
        operation,
        htmx,
        422,
        label=current,
        values=data,
        errors=errors,
    )


@router.get("/{operation_id}")
def show_label(
    request: Request,
    labels: LabelServiceDep,
    operations: OperationServiceDep,
    htmx: HtmxDep,
    operation_id: Id,
) -> Response:
    """An operation's row, for htmx (the form's Cancel); else back to the account."""
    operation = operations.get(operation_id)
    if not htmx:
        return RedirectResponse(_row_url(operation), status_code=303)
    return _render_row(request, operation, labels.find(operation_id))
