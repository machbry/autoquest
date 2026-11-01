"""Data access to banks."""

from collections.abc import Sequence

from sqlalchemy import func, select

from banking.databases.models import AccountModel, BankModel
from banking.databases.repositories.base import Repository
from banking.domains.bank import Bank


def to_bank(row: BankModel) -> Bank:
    """Convert a bank row to its domain object."""
    return Bank(id=row.id, name=row.name)


class BankRepository(Repository[BankModel, Bank]):
    """Banks."""

    model = BankModel

    def to_domain(self, row: BankModel) -> Bank:
        """Convert a row to its domain object."""
        return to_bank(row)

    def list(self) -> Sequence[Bank]:
        """Every bank, by name."""
        rows = self.session.scalars(select(BankModel).order_by(BankModel.name))
        return [to_bank(row) for row in rows]

    def list_with_account_counts(self) -> Sequence[tuple[Bank, int]]:
        """Every bank by name, with how many accounts use it."""
        rows = self.session.execute(
            select(BankModel, func.count(AccountModel.id))
            .outerjoin(AccountModel, AccountModel.bank_id == BankModel.id)
            .group_by(BankModel.id)
            .order_by(BankModel.name)
        )
        return [(to_bank(row), count) for row, count in rows]
