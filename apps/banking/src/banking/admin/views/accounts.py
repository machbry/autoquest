"""Accounts: declare, edit, close (keeps the history) or delete (removes it)."""

import logging
import re
from datetime import date
from typing import Any

import anyio.to_thread
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from starlette_admin import (
    DateField,
    EnumField,
    HasOne,
    StringField,
    action,
    flash,
    row_action,
)
from starlette_admin.actions import ActionSelection
from starlette_admin.exceptions import ActionFailed, FormValidationError

from banking.admin.views.base import NamedView, constraint, ids
from banking.databases.models import BankModel
from banking.domains.account import AccountType, normalize_account_number

logger = logging.getLogger(__name__)

ACCOUNT_TYPES = [
    (AccountType.CURRENT.value, "Current"),
    (AccountType.SAVINGS.value, "Savings"),
    (AccountType.PEA.value, "PEA"),
    (AccountType.LIFE_INSURANCE.value, "Life insurance"),
]
# Spaces dropped and uppercased first; the longest number is an IBAN.
ACCOUNT_NUMBER = re.compile(r"[A-Z0-9]{1,34}")


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
    save_errors = {
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
        """Close the account on the date the form sent; there is no reopening."""
        try:
            closed_on = date.fromisoformat(str((await request.form()).get("closed_on")))
        except ValueError:
            raise ActionFailed("Enter the closing date.") from None
        if (account := await self.find_by_pk(request, pk)) is None:
            raise ActionFailed("Unknown account.")
        if account.closed_on is not None:
            raise ActionFailed("Account already closed.")
        account.closed_on = closed_on
        try:
            await anyio.to_thread.run_sync(request.state.session.flush)
        except IntegrityError as exc:
            if constraint(exc) != "ck_accounts_closed_after_opened":
                raise
            raise ActionFailed("An account can't close before it opened.") from exc
        logger.info("account %s closed", account.id)
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
        logger.info("accounts %s deleted", ", ".join(map(str, ids(pks))))
        return deleted


def _close_form() -> str:
    """The close action's form: the closing date, today by default."""
    return (
        '<form><label class="form-label mt-3" for="closed_on">Closed on</label>'
        '<input class="form-control" type="date" id="closed_on" name="closed_on" '
        f'value="{date.today().isoformat()}" required></form>'
    )
