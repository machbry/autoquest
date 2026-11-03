"""The admin's views: operations to label; accounts, categories and banks to edit.

They write the tables directly, not through the services: the database constraints
hold the invariants, and broken ones are shown to the user by name. Closing an account
is the exception: it reuses the account service's rules.
"""

import html
import logging
import re
from collections.abc import Sequence
from datetime import date
from typing import Any

import anyio.to_thread
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette_admin import (
    DateField,
    DecimalField,
    EnumField,
    HasOne,
    IntegerField,
    StringField,
    action,
    flash,
    row_action,
)
from starlette_admin.actions import ActionSelection
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import ActionFailed, FormValidationError
from starlette_admin.filters import FilterRegistry as BaseFilterRegistry

from banking.admin.filters import FilterRegistry
from banking.databases.models import (
    AccountModel,
    BankModel,
    CategoryModel,
    OperationModel,
)
from banking.domains.account import AccountType, normalize_account_number
from banking.domains.errors import ConflictError, InvalidError, NotFoundError
from banking.services.accounts.account_service import AccountService

logger = logging.getLogger(__name__)

# Broken constraint → (field at fault, message), for a create or an edit.
SAVE_ERRORS = {
    "uq_banks_name": ("name", "Another bank already has this name."),
    "uq_categories_name": ("name", "Another category already has this name."),
    "uq_accounts_name": ("name", "Another account already has this name."),
    "uq_accounts_account_number": (
        "account_number",
        "Another account already has this number.",
    ),
    "ck_accounts_closed_after_opened": (
        "opened_on",
        "The account was closed before this date.",
    ),
}
# Broken constraint → message, for a delete.
DELETE_ERRORS = {
    "fk_accounts_bank_id": "Accounts still use this bank.",
    "fk_operations_category_id": "Operations still use this category: merge it.",
}
ACCOUNT_TYPES = [
    (AccountType.CURRENT.value, "Current"),
    (AccountType.SAVINGS.value, "Savings"),
    (AccountType.PEA.value, "PEA"),
    (AccountType.LIFE_INSURANCE.value, "Life insurance"),
]
MAX_ID = 2**31 - 1  # largest INTEGER
# Spaces dropped and uppercased first; the longest number is an IBAN.
ACCOUNT_NUMBER = re.compile(r"[A-Z0-9]{1,34}")


def _constraint(exc: IntegrityError) -> str | None:
    """The name of the constraint a write broke, if Postgres gave it."""
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)


def _ids(pks: Sequence[Any]) -> list[int]:
    return [int(pk) for pk in pks]


def _valid_id(raw: Any) -> int | None:
    """The id `raw` names, if it is one an INTEGER column can hold; else None."""
    if not isinstance(raw, str | int) or not str(raw).isdigit():
        return None
    return int(raw) if 1 <= int(raw) <= MAX_ID else None


class View(ModelView):
    """A view whose records show by name, and whose broken constraints say why."""

    page_size = 50
    page_size_options = [50, 100, 500]

    def get_filter_registry(self) -> BaseFilterRegistry:
        """starlette-admin's filters, plus "is one of" on relations."""
        return FilterRegistry()

    async def repr(self, obj: Any, request: Request) -> str:
        """A record shows by its name (in relations, pickers and messages)."""
        return str(obj.name)

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        """The record with this id; None for an invalid one, rather than failing."""
        # Regression: a non-numeric id in the address answered 500.
        if (record_id := _valid_id(pk)) is None:
            return None
        return await super().find_by_pk(request, record_id)

    async def handle_exception(self, request: Request, exc: Exception) -> None:
        """Show a known broken constraint next to its field; raise anything else."""
        if isinstance(exc, IntegrityError) and _constraint(exc) in SAVE_ERRORS:
            field, message = SAVE_ERRORS[_constraint(exc)]  # type: ignore[index]
            raise FormValidationError({field: message}) from exc
        raise exc

    async def delete(self, request: Request, pks: list[Any]) -> int | None:
        """Delete records; refuse, saying why, those still in use."""
        try:
            return await super().delete(request, pks)
        except IntegrityError as exc:
            if (message := DELETE_ERRORS.get(_constraint(exc) or "")) is None:
                raise
            raise ActionFailed(message) from exc


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
        form=lambda request: _category_select(request, "category_id"),
        modal_size="md",
    )
    async def set_category(self, request: Request, selection: ActionSelection) -> None:
        """Give the selected operations a category."""
        category_id = await _form_id(request, "category_id")
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


class NamedView(View):
    """Records with a name: trimmed, required, as long as its column allows."""

    fields = [StringField("name")]
    fields_default_sort = ["name"]

    async def validate(self, request: Request, data: dict[str, Any]) -> None:
        """Trim the name, refusing it blank or too long (with the field's error).

        Raises:
            FormValidationError: the name is blank or too long.
        """
        name = str(data.get("name") or "").strip()
        limit = self.model.__table__.c.name.type.length
        if not name:
            raise FormValidationError({"name": "Enter a name."})
        # Postgres text can't hold NUL: refused here rather than failing on insert.
        if "\x00" in name:
            raise FormValidationError({"name": "Invalid character."})
        if len(name) > limit:
            raise FormValidationError({"name": f"{limit} characters at most."})
        data["name"] = name


class CategoryView(NamedView):
    """Categories: add, rename, merge; one in use can't be deleted, only merged."""

    key = "categories"
    menu_label = "Categories"
    display_name = "Category"
    actions = ["merge", "delete"]

    @action(
        name="merge",
        text="Merge into…",
        confirmation="Move the selected categories' operations to this category, "
        "then delete them:",
        submit_btn_text="Merge",
        form=lambda request: _category_select(request, "target_id"),
        modal_size="md",
    )
    async def merge(self, request: Request, selection: ActionSelection) -> None:
        """Move the selected categories' operations to another, then delete them."""
        target_id = await _form_id(request, "target_id")
        if target_id is None:
            raise ActionFailed("Choose the category to merge into.")
        sources = [pk for pk in _ids(await selection.pks()) if pk != target_id]
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


class BankView(NamedView):
    """Banks: add, rename; one an account uses can't be deleted."""

    key = "banks"
    menu_label = "Banks"
    display_name = "Bank"


class AccountView(NamedView):
    """Accounts: declare, edit, close (keeps the history) or delete (removes it)."""

    key = "accounts"
    menu_label = "Accounts"
    display_name = "Account"
    fields = [
        StringField("name", required=True),
        HasOne("bank", key="banks", required=True),
        EnumField("type", choices=ACCOUNT_TYPES, required=True),
        StringField("account_number", label="Account number"),
        DateField("opened_on", label="Opened on", required=True),
        DateField("closed_on", label="Closed on"),
    ]
    # Closing has its own action, which checks the account is still open.
    exclude_fields_from_create = ["closed_on"]
    exclude_fields_from_edit = ["closed_on"]
    searchable_fields = ["name", "bank", "type", "account_number"]
    sortable_fields = ["name", "bank", "type", "opened_on", "closed_on"]
    sortable_field_mapping = {"bank": BankModel.name}
    # Postgres sorts NULLs first when descending: open accounts by name, then closed.
    fields_default_sort = [("closed_on", True), "name"]
    row_actions = ["view", "edit", "close", "delete"]

    async def validate(self, request: Request, data: dict[str, Any]) -> None:
        """Check the name and type; store the number normalized, or none if empty.

        Raises:
            FormValidationError: the name, the type or the number is invalid.
        """
        await super().validate(request, data)
        if data.get("type") not in set(AccountType):
            raise FormValidationError({"type": "Choose a type."})
        number = normalize_account_number(str(data.get("account_number") or ""))
        if number and not ACCOUNT_NUMBER.fullmatch(number):
            raise FormValidationError(
                {"account_number": "Letters and digits only, 34 at most."}
            )
        data["account_number"] = number or None

    async def is_row_action_allowed_for_obj(
        self, request: Request, name: str, obj: Any
    ) -> bool:
        """A closed account can't be closed again."""
        if name == "close" and obj.closed_on is not None:
            return False
        return await super().is_row_action_allowed_for_obj(request, name, obj)

    @row_action(
        name="close",
        text="Close",
        confirmation="Close this account? Its history stays; it can't be reopened.",
        submit_btn_text="Close account",
        icon_class="fa fa-lock",
        form=lambda request, obj: _close_form(),
        modal_size="md",
    )
    async def close(self, request: Request, pk: Any) -> None:
        """Close the account on the date the form sent."""
        try:
            closed_on = date.fromisoformat(str((await request.form()).get("closed_on")))
        except ValueError:
            raise ActionFailed("Enter the closing date.") from None
        if (account_id := _valid_id(pk)) is None:
            raise ActionFailed("Unknown account.")
        accounts = AccountService(request.state.session)
        try:
            await anyio.to_thread.run_sync(accounts.close, account_id, closed_on)
        except (InvalidError, ConflictError) as exc:
            raise ActionFailed(exc.message) from exc
        except NotFoundError as exc:
            raise ActionFailed("Unknown account.") from exc
        flash(request, "Account closed.", "success")

    @action(
        name="delete",
        text="Delete",
        confirmation="Delete the selected accounts and all their history (imports, "
        "operations)? To keep the history, close them instead.",
        submit_btn_text="Delete with their history",
        submit_btn_class="action.modal_confirm_button_delete",
    )
    async def delete_action(self, request: Request, selection: ActionSelection) -> None:
        """Delete the selected accounts, warning that their history goes too."""
        await super().delete_action(request, selection)

    @row_action(
        name="delete",
        text="Delete",
        confirmation="Delete this account and all its history (imports, operations)? "
        "To keep the history, close it instead.",
        icon_class="default_actions.delete",
        submit_btn_text="Delete with its history",
        submit_btn_class="action.modal_confirm_button_delete",
        action_btn_class="action.row_item_delete",
    )
    async def row_action_3_delete(self, request: Request, pk: Any) -> None:
        """Delete the account, warning that its history goes too."""
        await super().row_action_3_delete(request, pk)

    async def delete(self, request: Request, pks: list[Any]) -> int | None:
        """Delete accounts and, through the database's cascades, their history."""
        deleted = await super().delete(request, pks)
        logger.info("accounts %s deleted", ", ".join(map(str, _ids(pks))))
        return deleted


def _close_form() -> str:
    """The close action's form: the closing date, today by default."""
    return (
        '<form><label class="form-label mt-3" for="closed_on">Closed on</label>'
        '<input class="form-control" type="date" id="closed_on" name="closed_on" '
        f'value="{date.today().isoformat()}" required></form>'
    )


def _category_select(request: Request, name: str) -> str:
    """The form of a category action: a select of every category, by name."""
    rows = request.state.session.query(CategoryModel).order_by(CategoryModel.name)
    options = "".join(
        f'<option value="{row.id}">{html.escape(row.name)}</option>' for row in rows
    )
    return (
        f'<form><select class="form-select mt-3" name="{name}" required>'
        f'<option value="">Choose a category</option>{options}</select></form>'
    )


async def _form_id(request: Request, name: str) -> int | None:
    """A category id the action's form sent; None if left empty."""
    raw = (await request.form()).get(name)
    if not raw:
        return None
    if (category_id := _valid_id(raw)) is None:
        raise ActionFailed("Unknown category.")
    return category_id


async def _set_category(
    request: Request, selection: ActionSelection, category_id: int | None
) -> None:
    """Set (or, with None, remove) the category of the selected operations."""
    ids = _ids(await selection.pks())
    session: Session = request.state.session

    def set_category() -> None:
        session.execute(
            update(OperationModel)
            .where(OperationModel.id.in_(ids))
            .values(category_id=category_id)
        )
        session.flush()

    try:
        await anyio.to_thread.run_sync(set_category)
    except IntegrityError as exc:
        raise ActionFailed("Unknown category.") from exc
    logger.info("%d operations labelled with category %s", len(ids), category_id)
    flash(request, f"{len(ids)} operations updated.", "success")
