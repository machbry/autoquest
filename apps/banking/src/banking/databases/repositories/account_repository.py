"""Data access to accounts."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from banking.databases.models import AccountModel
from banking.databases.repositories.bank_repository import to_bank
from banking.databases.repositories.base import Repository
from banking.domains.account import Account


class AccountRepository(Repository[AccountModel, Account]):
    """Accounts, with their bank."""

    model = AccountModel

    def to_domain(self, row: AccountModel) -> Account:
        """Convert a row, and its bank, to the domain object."""
        return Account(
            id=row.id,
            name=row.name,
            bank=to_bank(row.bank),
            type=row.type,
            account_number=row.account_number,
            opened_on=row.opened_on,
            closed_on=row.closed_on,
        )

    def list(self) -> Sequence[Account]:
        """Every account with its bank, open ones first, then by name."""
        rows = self.session.scalars(
            select(AccountModel)
            .options(joinedload(AccountModel.bank))
            .order_by(AccountModel.closed_on.is_not(None), AccountModel.name)
        )
        return [self.to_domain(row) for row in rows]
