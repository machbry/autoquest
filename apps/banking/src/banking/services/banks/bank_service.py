"""Banks: add, rename and delete them; a bank in use can't be deleted."""

import logging
from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.models import Bank
from banking.databases.repositories.bank_repository import BankRepository
from banking.databases.repositories.base import ConstraintViolation
from banking.services.errors import ConflictError, InvalidError, NotFoundError

logger = logging.getLogger(__name__)


class BankService:
    """Use cases on banks; each write is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.banks = BankRepository(session)

    def list(self) -> Sequence[Bank]:
        """Every bank, by name."""
        return self.banks.list()

    def list_with_account_counts(self) -> Sequence[tuple[Bank, int]]:
        """Every bank by name, with how many accounts use it."""
        return self.banks.list_with_account_counts()

    def get(self, bank_id: int) -> Bank:
        """The bank with this id.

        Raises:
            NotFoundError: no such bank.
        """
        if (bank := self.banks.get(bank_id)) is None:
            raise NotFoundError
        return bank

    def add(self, name: str) -> Bank:
        """Add a bank.

        Raises:
            InvalidError: another bank has this name.
        """
        bank = self._save(Bank(name=name))
        logger.info("bank %s added", bank.id)
        return bank

    def rename(self, bank_id: int, name: str) -> Bank:
        """Rename a bank.

        Raises:
            NotFoundError: no such bank.
            InvalidError: another bank has this name.
        """
        bank = self.get(bank_id)
        bank.name = name
        self._save(bank)
        logger.info("bank %s renamed", bank.id)
        return bank

    def delete(self, bank_id: int) -> None:
        """Delete a bank.

        Raises:
            NotFoundError: no such bank.
            ConflictError: an account still uses it.
        """
        try:
            self.banks.delete(self.get(bank_id))
        except ConstraintViolation as exc:
            if exc.constraint != "fk_accounts_bank_id":
                raise
            raise ConflictError("Accounts still use this bank.") from exc
        self.session.commit()
        logger.info("bank %s deleted", bank_id)

    def _save(self, bank: Bank) -> Bank:
        try:
            self.banks.add(bank)
        except ConstraintViolation as exc:
            if exc.constraint != "uq_banks_name":
                raise
            raise InvalidError("name", "Another bank already has this name.") from exc
        self.session.commit()
        return bank
