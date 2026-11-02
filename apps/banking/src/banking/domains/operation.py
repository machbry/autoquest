"""Operations: the lines of a bank statement."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class OperationFields:
    """What the bank says about an operation; also the key that spots duplicates."""

    operation_date: date
    description: str
    amount: Decimal


@dataclass(frozen=True)
class Operation:
    """A stored operation; identical ones on the same day are distinct operations."""

    id: int
    account_id: int
    operation_date: date
    description: str
    amount: Decimal
    category_id: int | None


@dataclass(frozen=True)
class MonthRecap:
    """An account's month: how many operations, and how many of them are labelled."""

    month: date  # its first day
    operations: int
    labelled: int

    @property
    def unlabelled(self) -> int:
        """Operations of the month still without a category."""
        return self.operations - self.labelled
