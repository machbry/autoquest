"""Data access to accounts."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from banking.databases.models import Account
from banking.databases.repositories.base import Repository


class AccountRepository(Repository[Account]):
    """Accounts, with their bank."""

    model = Account

    def list(self) -> Sequence[Account]:
        """Every account with its bank, open ones first, then by name."""
        return self.session.scalars(
            select(Account)
            .options(joinedload(Account.bank))
            .order_by(Account.closed_on.is_not(None), Account.name)
        ).all()
