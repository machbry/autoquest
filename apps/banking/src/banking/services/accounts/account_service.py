"""Accounts: declare, edit, close (keeps the history) and delete them."""

import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date

from sqlalchemy.orm import Session

from banking.databases.models import Account, AccountType
from banking.databases.repositories.account_repository import AccountRepository
from banking.databases.repositories.base import ConstraintViolation
from banking.services.errors import ConflictError, InvalidError, NotFoundError

logger = logging.getLogger(__name__)

CLOSED_AFTER_OPENED = "ck_accounts_closed_after_opened"
# Constraints a declare or edit can break: the field at fault and why.
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


@dataclass(frozen=True)
class AccountFields:
    """What declaring or editing an account sets (its closing date excluded)."""

    name: str
    bank_id: int
    type: AccountType
    account_number: str | None
    opened_on: date


class AccountService:
    """Use cases on accounts; each write is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.accounts = AccountRepository(session)

    def list(self) -> Sequence[Account]:
        """Every account with its bank, open ones first; closed ones stay listed."""
        return self.accounts.list()

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
        account = self._save(Account(**asdict(fields)), SAVE_ERRORS)
        logger.info("account %s created", account.id)
        return account

    def update(self, account_id: int, fields: AccountFields) -> Account:
        """Edit an account; its closing date can't be changed this way.

        Raises:
            NotFoundError: no such account.
            InvalidError: a field breaks a rule (as for `create`, or opened after it
                was closed).
        """
        account = self.get(account_id)
        for field, value in asdict(fields).items():
            setattr(account, field, value)
        self._save(account, SAVE_ERRORS)
        logger.info("account %s updated", account.id)
        return account

    def close(self, account_id: int, closed_on: date) -> Account:
        """Close an open account; there is no reopening.

        Raises:
            NotFoundError: no such account.
            ConflictError: the account is already closed.
            InvalidError: it would close before it opened.
        """
        account = self.get(account_id)
        if account.closed_on is not None:
            raise ConflictError("Account already closed")
        account.closed_on = closed_on
        self._save(account, CLOSE_ERRORS)
        logger.info("account %s closed", account.id)
        return account

    def delete(self, account_id: int) -> None:
        """Delete an account and, through the database's cascades, all its history.

        Raises:
            NotFoundError: no such account.
        """
        self.accounts.delete(self.get(account_id))
        self.session.commit()
        logger.info("account %s deleted", account_id)

    def _save(self, account: Account, errors: dict[str, tuple[str, str]]) -> Account:
        try:
            self.accounts.add(account)
        except ConstraintViolation as exc:
            if exc.constraint not in errors:
                raise
            raise InvalidError(*errors[exc.constraint]) from exc
        self.session.commit()
        return account
