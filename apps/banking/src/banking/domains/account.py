"""Accounts and their types."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from banking.domains.bank import Bank


def normalize_account_number(value: str) -> str:
    """Drop spaces and uppercase, so formatting never hides a match or a duplicate."""
    return value.replace(" ", "").upper()


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


class FreshnessStatus(StrEnum):
    """How old an account's data is, against the bank's 90-day export window."""

    NEVER = "never"
    OK = "ok"
    WARNING = "warning"
    ALERT = "alert"


@dataclass(frozen=True)
class Freshness:
    """Status, and days since the export date of the account's latest export."""

    status: FreshnessStatus
    days: int | None
