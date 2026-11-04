"""Accounts: their freshness, on the Import page; the admin edits them."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from banking.databases.repositories.account_repository import AccountRepository
from banking.databases.repositories.import_repository import ImportRepository
from banking.domains.account import Account, Freshness
from banking.domains.errors import NotFoundError
from banking.services.accounts.freshness import freshness


class AccountService:
    """Use cases on accounts."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
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
