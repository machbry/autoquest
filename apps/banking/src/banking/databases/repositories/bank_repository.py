"""Data access to banks."""

from collections.abc import Sequence

from sqlalchemy import func, select

from banking.databases.models import Account, Bank
from banking.databases.repositories.base import Repository


class BankRepository(Repository[Bank]):
    """Banks."""

    model = Bank

    def list(self) -> Sequence[Bank]:
        """Every bank, by name."""
        return self.session.scalars(select(Bank).order_by(Bank.name)).all()

    def list_with_account_counts(self) -> Sequence[tuple[Bank, int]]:
        """Every bank by name, with how many accounts use it."""
        rows = self.session.execute(
            select(Bank, func.count(Account.id))
            .outerjoin(Account, Account.bank_id == Bank.id)
            .group_by(Bank.id)
            .order_by(Bank.name)
        ).all()
        return [(bank, count) for bank, count in rows]
