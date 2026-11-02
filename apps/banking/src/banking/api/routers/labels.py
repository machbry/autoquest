"""Label pages: the labelling queue, and editing a label, in place with htmx.

Every htmx interaction is also a plain link or form: without JavaScript, the same
routes answer with full pages and redirects.
"""

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.htmx import HtmxDep
from banking.api.dependencies.services import (
    AccountServiceDep,
    CategoryServiceDep,
    LabelServiceDep,
    OperationServiceDep,
)
from banking.api.rendering import Errors, render, validate
from banking.api.schemas.common import Id
from banking.api.schemas.labels import LabelForm, QueueFilterForm, QueueLabelForm
from banking.domains.errors import InvalidError
from banking.domains.label import Label, QueueFilter
from banking.domains.operation import Operation
from banking.services.accounts.account_service import AccountService
from banking.services.categories.category_service import CategoryService
from banking.services.labels.label_service import LabelService

router = APIRouter(prefix="/labels")

FILTER_FIELDS = ("account_id", "month")


def _form_values(
    category_id: int, tags: Sequence[str], note: str | None
) -> dict[str, Any]:
    """A label as the form's fields: one input per tag."""
    tag_1, tag_2, tag_3 = [*tags, "", "", ""][:3]
    return {
        "category_id": category_id,
        "tag_1": tag_1,
        "tag_2": tag_2,
        "tag_3": tag_3,
        "note": note or "",
    }


def _filter_values(data: Mapping[str, Any]) -> dict[str, str]:
    return {field: str(data.get(field) or "") for field in FILTER_FIELDS}


def _queue_url(filter_values: Mapping[str, str]) -> str:
    query = urlencode({field: value for field, value in filter_values.items() if value})
    return f"/labels/new?{query}" if query else "/labels/new"


def _row_url(operation: Operation) -> str:
    """The operation's row on its account page."""
    return f"/accounts/{operation.account_id}#operation-{operation.id}"


def _render_queue(
    request: Request,
    labels: LabelService,
    categories: CategoryService,
    accounts: AccountService,
    queue_filter: QueueFilter,
    filter_values: Mapping[str, str],
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    queue = labels.queue(queue_filter)
    account_list = accounts.list()
    if "values" not in context and queue.suggestion is not None:
        suggestion = queue.suggestion
        context["values"] = _form_values(suggestion.category_id, suggestion.tags, None)
    return render(
        request,
        "labels/form.html",
        status_code,
        queue=queue,
        filter_values=filter_values,
        accounts=account_list,
        account_names={account.id: account.name for account in account_list},
        categories=categories.list(),
        tags=labels.list_tags(),
        **context,
    )


def _render_form(
    request: Request,
    labels: LabelService,
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
        tags=labels.list_tags(),
        **context,
    )
    response.headers["Vary"] = "HX-Request"
    return response


def _render_row(request: Request, operation: Operation, label: Label) -> HTMLResponse:
    """The operation's row on the account page; focus goes back to its Edit link."""
    response = render(
        request, "labels/row.html", operation=operation, label=label, focus=True
    )
    response.headers["Vary"] = "HX-Request"
    return response


@router.get("/new", response_class=HTMLResponse)
def new_label(
    request: Request,
    labels: LabelServiceDep,
    categories: CategoryServiceDep,
    accounts: AccountServiceDep,
) -> HTMLResponse:
    """The queue: the oldest unlabelled operation, last time's label suggested."""
    filter_values = _filter_values(request.query_params)
    form, errors = validate(QueueFilterForm, filter_values)
    if form is None:
        return _render_queue(
            request, labels, categories, accounts, QueueFilter(), {}, 422, errors=errors
        )
    return _render_queue(
        request, labels, categories, accounts, form.to_filter(), filter_values
    )


@router.post("")
def create_label(
    request: Request,
    labels: LabelServiceDep,
    categories: CategoryServiceDep,
    accounts: AccountServiceDep,
    data: FormDep,
) -> Response:
    """Label the queue's operation, or all the similar ones; back to the same queue."""
    filter_values = _filter_values(data)
    filter_form, filter_errors = validate(QueueFilterForm, filter_values)
    queue_filter = QueueFilter() if filter_form is None else filter_form.to_filter()
    form, errors = validate(QueueLabelForm, data)
    if form is not None and filter_form is not None:
        fields = form.to_fields()
        try:
            if form.scope == "similar":
                labels.create_for_similar(form.operation_id, fields, queue_filter)
            else:
                labels.create(form.operation_id, fields)
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse(_queue_url(filter_values), status_code=303)
    all_errors: Errors = errors | filter_errors
    return _render_queue(
        request,
        labels,
        categories,
        accounts,
        queue_filter,
        filter_values if filter_form is not None else {},
        422,
        values=data,
        errors=all_errors,
    )


@router.get("/{operation_id}/edit", response_class=HTMLResponse)
def edit_label(
    request: Request,
    labels: LabelServiceDep,
    categories: CategoryServiceDep,
    operations: OperationServiceDep,
    htmx: HtmxDep,
    operation_id: Id,
) -> HTMLResponse:
    """Form to edit a label, prefilled with its current values."""
    label = labels.get(operation_id)
    values = _form_values(label.category.id, label.tags, label.note)
    operation = operations.get(operation_id)
    return _render_form(request, labels, categories, operation, htmx, values=values)


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
    """Edit a label: the updated row for htmx, else back to the account page."""
    labels.get(operation_id)
    operation = operations.get(operation_id)
    form, errors = validate(LabelForm, data)
    if form is not None:
        try:
            label = labels.update(operation_id, form.to_fields())
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            if htmx:
                return _render_row(request, operation, label)
            return RedirectResponse(_row_url(operation), status_code=303)
    return _render_form(
        request, labels, categories, operation, htmx, 422, values=data, errors=errors
    )


@router.get("/{operation_id}")
def show_label(
    request: Request,
    labels: LabelServiceDep,
    operations: OperationServiceDep,
    htmx: HtmxDep,
    operation_id: Id,
) -> Response:
    """A label's row, for htmx (the edit's Cancel); else back to the account page."""
    label = labels.get(operation_id)
    operation = operations.get(operation_id)
    if not htmx:
        return RedirectResponse(_row_url(operation), status_code=303)
    return _render_row(request, operation, label)
