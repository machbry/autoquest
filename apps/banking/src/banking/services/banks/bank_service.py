"""Banks: create, update (rename) and delete them; a bank in use can't be deleted."""

import logging
from collections.abc import Sequence
from dataclasses import asdict

from sqlalchemy.orm import Session

from banking.databases.repositories.bank_repository import BankRepository
from banking.databases.repositories.base import ConstraintViolation
from banking.domains.bank import Bank, BankFields
from banking.domains.errors import ConflictError, NotFoundError
from banking.services.constraints import invalid_on

logger = logging.getLogger(__name__)

SAVE_ERRORS = {"uq_banks_name": ("name", "Another bank already has this name.")}


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

    def create(self, fields: BankFields) -> Bank:
        """Create a bank.

        Raises:
            InvalidError: another bank has this name.
        """
        with invalid_on(SAVE_ERRORS):
            bank = self.banks.create(asdict(fields))
        self.session.commit()
        logger.info("bank %s created", bank.id)
        return bank

    def update(self, bank_id: int, fields: BankFields) -> Bank:
        """Update (rename) a bank.

        Raises:
            NotFoundError: no such bank.
            InvalidError: another bank has this name.
        """
        with invalid_on(SAVE_ERRORS):
            bank = self.banks.update(bank_id, asdict(fields))
        if bank is None:
            raise NotFoundError
        self.session.commit()
        logger.info("bank %s updated", bank_id)
        return bank

    def delete(self, bank_id: int) -> None:
        """Delete a bank.

        Raises:
            NotFoundError: no such bank.
            ConflictError: an account still uses it.
        """
        try:
            deleted = self.banks.delete(bank_id)
        except ConstraintViolation as exc:
            if exc.constraint != "fk_accounts_bank_id":
                raise
            raise ConflictError("Accounts still use this bank.") from exc
        if not deleted:
            raise NotFoundError
        self.session.commit()
        logger.info("bank %s deleted", bank_id)
