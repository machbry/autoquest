"""Data access to banks; the admin creates and edits them."""

from collections.abc import Sequence

from sqlalchemy import select

from banking.databases.models import BankModel
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
