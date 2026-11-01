"""Accounts and their types."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from banking.domains.bank import Bank


class AccountType(StrEnum):
    """Kinds of account; fixed, because the analysis relies on them."""

    CURRENT = "current"
    SAVINGS = "savings"
    PEA = "pea"
    LIFE_INSURANCE = "life_insurance"


@dataclass(frozen=True)
class Account:
    """A bank account; closing it keeps its history, deleting it removes it."""

    id: int
    name: str
    bank: Bank
    type: AccountType
    account_number: str | None
    opened_on: date
    closed_on: date | None

    @property
    def bank_id(self) -> int:
        """Id of the account's bank, as the forms name it."""
        return self.bank.id


@dataclass(frozen=True)
class AccountFields:
    """What declaring or editing an account sets (its closing date excluded)."""

    name: str
    bank_id: int
    type: AccountType
    account_number: str | None
    opened_on: date
