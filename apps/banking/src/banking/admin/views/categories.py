"""Categories: add, rename, merge; one in use can't be deleted, only merged."""

import html
import logging

import anyio.to_thread
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette_admin import action, flash
from starlette_admin.actions import ActionSelection
from starlette_admin.exceptions import ActionFailed

from banking.admin.views.base import NamedView, ids, valid_id
from banking.databases.models import CategoryModel, OperationModel

logger = logging.getLogger(__name__)


def category_select(request: Request, name: str) -> str:
    """The form of a category action: a select of every category, by name."""
    rows = request.state.session.query(CategoryModel).order_by(CategoryModel.name)
    options = "".join(
        f'<option value="{row.id}">{html.escape(row.name)}</option>' for row in rows
    )
    return (
        f'<form><select class="form-select mt-3" name="{name}" required>'
        f'<option value="">Choose a category</option>{options}</select></form>'
    )


async def form_id(request: Request, name: str) -> int | None:
    """A category id the action's form sent; None if left empty.

    Raises:
        ActionFailed: the id is not a valid one.
    """
    raw = (await request.form()).get(name)
    if not raw:
        return None
    if (category_id := valid_id(raw)) is None:
        raise ActionFailed("Unknown category.")
    return category_id


class CategoryView(NamedView):
    """Categories: add, rename, merge; one in use can't be deleted, only merged."""

    key = "categories"
    menu_label = "Categories"
    display_name = "Category"
    actions = ["merge", "delete"]
    save_errors = {
        "uq_categories_name": ("name", "Another category already has this name.")
    }
    delete_errors = {
        "fk_operations_category_id": "Operations still use this category: merge it."
    }

    @action(
        name="merge",
        text="Merge into…",
        confirmation="Move the selected categories' operations to this category, "
        "then delete them:",
        submit_btn_text="Merge",
        form=lambda request: category_select(request, "target_id"),
        modal_size="md",
    )
    async def merge(self, request: Request, selection: ActionSelection) -> None:
        """Move the selected categories' operations to another, then delete them."""
        target_id = await form_id(request, "target_id")
        if target_id is None:
            raise ActionFailed("Choose the category to merge into.")
        sources = [pk for pk in ids(await selection.pks()) if pk != target_id]
        session: Session = request.state.session

        def merge() -> int:
            session.execute(
                update(OperationModel)
                .where(OperationModel.category_id.in_(sources))
                .values(category_id=target_id)
            )
            deleted = session.execute(
                delete(CategoryModel).where(CategoryModel.id.in_(sources))
            )
            return int(deleted.rowcount)  # type: ignore[attr-defined]

        try:
            merged = await anyio.to_thread.run_sync(merge)
        except IntegrityError as exc:
            raise ActionFailed("Unknown category.") from exc
        logger.info("%d categories merged into %s", merged, target_id)
        flash(request, f"{merged} categories merged.", "success")
