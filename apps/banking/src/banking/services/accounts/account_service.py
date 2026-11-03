"""Accounts: their freshness, and closing them (keeps the history).

The admin declares, edits and deletes them; closing has rules the database can't hold.
"""

import logging
from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from banking.databases.repositories.account_repository import AccountRepository
from banking.databases.repositories.import_repository import ImportRepository
from banking.domains.account import Account, Freshness
from banking.domains.errors import ConflictError, NotFoundError
from banking.services.accounts.freshness import freshness
from banking.services.constraints import invalid_on

logger = logging.getLogger(__name__)

CLOSE_ERRORS = {
    "ck_accounts_closed_after_opened": (
        "closed_on",
        "An account can't close before it opened.",
    ),
}


class AccountService:
    """Use cases on accounts; each write is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.accounts = AccountRepository(session)
        self.imports = ImportRepository(session)

    def list_with_freshness(self) -> Sequence[tuple[Account, Freshness]]:
        """Every account, open ones first, with how fresh its imported data is."""
        latest, today = self.imports.latest_export_dates(), date.today()
        return [
            (account, freshness(latest.get(account.id), today))
            for account in self.accounts.list()
        ]

    def get_freshness(self, account_id: int) -> Freshness:
        """How fresh an account's imported data is."""
        return freshness(self.imports.latest_export_date(account_id), date.today())

    def get(self, account_id: int) -> Account:
        """The account with this id.

        Raises:
            NotFoundError: no such account.
        """
        if (account := self.accounts.get(account_id)) is None:
            raise NotFoundError
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
