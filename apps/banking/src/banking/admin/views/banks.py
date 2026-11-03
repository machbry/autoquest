"""Banks: add, rename; one an account uses can't be deleted."""

from banking.admin.views.base import NamedView


class BankView(NamedView):
    """Banks: add, rename; one an account uses can't be deleted."""

    key = "banks"
    menu_label = "Banks"
    display_name = "Bank"
    save_errors = {"uq_banks_name": ("name", "Another bank already has this name.")}
    delete_errors = {"fk_accounts_bank_id": "Accounts still use this bank."}
