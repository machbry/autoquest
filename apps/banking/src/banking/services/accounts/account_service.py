"""Accounts: declare, edit, close (keeps the history) and delete them; freshness."""

import logging
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date

from sqlalchemy.orm import Session

from banking.databases.repositories.account_repository import AccountRepository
from banking.databases.repositories.import_repository import ImportRepository
from banking.domains.account import Account, AccountFields, Freshness
from banking.domains.errors import ConflictError, NotFoundError
from banking.services.accounts.freshness import freshness
from banking.services.constraints import invalid_on

logger = logging.getLogger(__name__)

CLOSED_AFTER_OPENED = "ck_accounts_closed_after_opened"
SAVE_ERRORS = {
    "uq_accounts_name": ("name", "Another account already has this name."),
    "uq_accounts_account_number": (
        "account_number",
        "Another account already has this number.",
    ),
    "fk_accounts_bank_id": ("bank_id", "Unknown bank."),
    CLOSED_AFTER_OPENED: ("opened_on", "The account was closed before this date."),
}
CLOSE_ERRORS = {
    CLOSED_AFTER_OPENED: ("closed_on", "An account can't close before it opened."),
}


class AccountService:
    """Use cases on accounts; each write is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.accounts = AccountRepository(session)
        self.imports = ImportRepository(session)

    def list(self) -> Sequence[Account]:
        """Every account with its bank, open ones first; closed ones stay listed."""
        return self.accounts.list()

    def list_with_freshness(self) -> Sequence[tuple[Account, Freshness]]:
        """Every account (as `list`), with how fresh its imported data is."""
        latest, today = self.imports.latest_export_dates(), date.today()
        return [
            (account, freshness(latest.get(account.id), today))
            for account in self.accounts.list()
        ]

    def get_freshness(self, account_id: int) -> Freshness:
        """How fresh an account's imported data is."""
        latest = self.imports.latest_export_dates().get(account_id)
        return freshness(latest, date.today())

    def get(self, account_id: int) -> Account:
        """The account with this id.

        Raises:
            NotFoundError: no such account.
        """
        if (account := self.accounts.get(account_id)) is None:
            raise NotFoundError
        return account

    def create(self, fields: AccountFields) -> Account:
        """Declare an account.

        Raises:
            InvalidError: a field breaks a rule (name or number taken, unknown bank).
        """
        with invalid_on(SAVE_ERRORS):
            account = self.accounts.create(asdict(fields))
        self.session.commit()
        logger.info("account %s created", account.id)
        return account

    def update(self, account_id: int, fields: AccountFields) -> Account:
        """Edit an account; its closing date can't be changed this way.

        Raises:
            NotFoundError: no such account.
            InvalidError: a field breaks a rule (as for `create`, or opened after it
                was closed).
        """
        with invalid_on(SAVE_ERRORS):
            account = self.accounts.update(account_id, asdict(fields))
        if account is None:
            raise NotFoundError
        self.session.commit()
        logger.info("account %s updated", account_id)
        return account

    def close(self, account_id: int, closed_on: date) -> Account:
        """Close an open account; there is no reopening.

        Raises:
            NotFoundError: no such account.
            ConflictError: the account is already closed.
            InvalidError: it would close before it opened.
        """
        if self.get(account_id).closed_on is not None:
            raise ConflictError("Account already closed")
        with invalid_on(CLOSE_ERRORS):
            account = self.accounts.update(account_id, {"closed_on": closed_on})
        if account is None:
            raise NotFoundError
        self.session.commit()
        logger.info("account %s closed", account_id)
        return account

    def delete(self, account_id: int) -> None:
        """Delete an account and, through the database's cascades, all its history.

        Raises:
            NotFoundError: no such account.
        """
        if not self.accounts.delete(account_id):
            raise NotFoundError
        self.session.commit()
        logger.info("account %s deleted", account_id)
