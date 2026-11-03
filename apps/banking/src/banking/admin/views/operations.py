"""Operations: label them, one cell at a time or in bulk; the rest is the bank's."""

import logging
from typing import Any

import anyio.to_thread
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette_admin import (
    DateField,
    DecimalField,
    HasOne,
    IntegerField,
    StringField,
    action,
    flash,
)
from starlette_admin.actions import ActionSelection
from starlette_admin.exceptions import ActionFailed

from banking.admin.views.base import View, ids
from banking.admin.views.categories import category_select, form_id
from banking.databases.models import AccountModel, CategoryModel, OperationModel

logger = logging.getLogger(__name__)


class OperationView(View):
    """Operations: label them, one cell at a time or in bulk; the rest is the bank's."""

    key = "operations"
    menu_label = "Operations"
    display_name = "Operation"
    fields = [
        DateField("operation_date", label="Date"),
        HasOne("account", key="accounts"),
        StringField("description"),
        DecimalField("amount"),
        HasOne("category", key="categories"),
        IntegerField("id", label="Id"),
    ]
    # Imports add operations and account deletes remove them: only labels change.
    exclude_fields_from_edit = ["operation_date", "account", "description", "amount"]
    exclude_fields_from_list = ["id"]
    inline_editable_fields = ["category"]
    # Searchable fields are also the filterable ones.
    searchable_fields = [
        "operation_date",
        "account",
        "description",
        "amount",
        "category",
    ]
    sortable_fields = ["operation_date", "description", "amount", "account", "category"]
    sortable_field_mapping = {
        "account": AccountModel.name,
        "category": CategoryModel.name,
    }
    fields_default_sort = [("operation_date", True), ("id", True)]
    actions = ["set_category", "remove_category"]

    def can_create(self, request: Request) -> bool:
        """Operations come from imports only."""
        return False

    def can_delete(self, request: Request) -> bool:
        """An operation goes only with its account."""
        return False

    async def repr(self, obj: Any, request: Request) -> str:
        """An operation shows by its date and description."""
        return f"{obj.operation_date} {obj.description}"

    @action(
        name="set_category",
        text="Set category",
        confirmation="Set this category on the selected operations:",
        submit_btn_text="Set category",
        form=lambda request: category_select(request, "category_id"),
        modal_size="md",
    )
    async def set_category(self, request: Request, selection: ActionSelection) -> None:
        """Give the selected operations a category."""
        category_id = await form_id(request, "category_id")
        if category_id is None:
            raise ActionFailed("Choose a category.")
        await _set_category(request, selection, category_id)

    @action(
        name="remove_category",
        text="Remove category",
        confirmation="Remove the category of the selected operations?",
        submit_btn_text="Remove category",
    )
    async def remove_category(
        self, request: Request, selection: ActionSelection
    ) -> None:
        """Take the selected operations back to unlabelled."""
        await _set_category(request, selection, None)


async def _set_category(
    request: Request, selection: ActionSelection, category_id: int | None
) -> None:
    """Set (or, with None, remove) the category of the selected operations."""
    operation_ids = ids(await selection.pks())
    session: Session = request.state.session

    def set_category() -> None:
        session.execute(
            update(OperationModel)
            .where(OperationModel.id.in_(operation_ids))
            .values(category_id=category_id)
        )
        session.flush()

    try:
        await anyio.to_thread.run_sync(set_category)
    except IntegrityError as exc:
        raise ActionFailed("Unknown category.") from exc
    logger.info(
        "%d operations labelled with category %s", len(operation_ids), category_id
    )
    flash(request, f"{len(operation_ids)} operations updated.", "success")
