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
    operation_date: date
    description: str
    amount: Decimal
