"""Category pages: list, create, update (rename), merge and delete."""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from banking.api.dependencies.forms import FormDep
from banking.api.dependencies.services import CategoryServiceDep
from banking.api.rendering import Errors, render, validate
from banking.api.schemas.categories import CategoryForm, MergeForm
from banking.api.schemas.common import Id
from banking.domains.category import CategoryFields
from banking.domains.errors import ConflictError, InvalidError
from banking.services.categories.category_service import CategoryService

router = APIRouter(prefix="/categories")


def _render_list(
    request: Request,
    categories: CategoryService,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    return render(
        request,
        "categories/list.html",
        status_code,
        categories=categories.list_with_label_counts(),
        **context,
    )


def _render_form(
    request: Request,
    categories: CategoryService,
    category_id: int,
    status_code: int = 200,
    errors: Errors | None = None,
    **context: Any,
) -> HTMLResponse:
    category = categories.get(category_id)
    context.setdefault("values", category)
    return render(
        request,
        "categories/form.html",
        status_code,
        category=category,
        others=[other for other in categories.list() if other.id != category_id],
        errors=errors or {},
        **context,
    )


@router.get("", response_class=HTMLResponse)
def list_categories(request: Request, categories: CategoryServiceDep) -> HTMLResponse:
    """Every category with how many labels use it, and the form to create one."""
    return _render_list(request, categories)


@router.post("")
def create_category(
    request: Request, categories: CategoryServiceDep, data: FormDep
) -> Response:
    """Create a category; re-render the list (holding its form) with errors."""
    form, errors = validate(CategoryForm, data)
    if form is not None:
        try:
            categories.create(CategoryFields(**form.model_dump()))
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse("/categories", status_code=303)
    return _render_list(request, categories, 422, values=data, errors=errors)


@router.get("/{category_id}/edit", response_class=HTMLResponse)
def edit_category(
    request: Request, categories: CategoryServiceDep, category_id: Id
) -> HTMLResponse:
    """Forms to rename a category, prefilled, and to merge it into another."""
    return _render_form(request, categories, category_id)


@router.post("/{category_id}")
def update_category(
    request: Request, categories: CategoryServiceDep, data: FormDep, category_id: Id
) -> Response:
    """Update (rename) a category; re-render the form with errors if invalid."""
    form, errors = validate(CategoryForm, data)
    if form is not None:
        try:
            categories.update(category_id, CategoryFields(**form.model_dump()))
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse("/categories", status_code=303)
    return _render_form(request, categories, category_id, 422, errors, values=data)


@router.post("/{category_id}/merge")
def merge_category(
    request: Request, categories: CategoryServiceDep, data: FormDep, category_id: Id
) -> Response:
    """Merge a category into another; re-render the form with errors if invalid."""
    form, errors = validate(MergeForm, data)
    if form is not None:
        try:
            categories.merge(category_id, form.into_id)
        except InvalidError as exc:
            errors = {exc.field: exc.message}
        else:
            return RedirectResponse("/categories", status_code=303)
    return _render_form(request, categories, category_id, 422, errors)


@router.post("/{category_id}/delete")
def delete_category(
    request: Request, categories: CategoryServiceDep, category_id: Id
) -> Response:
    """Delete a category; refused (409) while a label uses it."""
    try:
        categories.delete(category_id)
    except ConflictError as exc:
        return _render_list(
            request,
            categories,
            409,
            errors={"delete": exc.message},
            failed_id=category_id,
        )
    return RedirectResponse("/categories", status_code=303)
