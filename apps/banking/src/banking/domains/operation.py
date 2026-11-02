"""Operations: the lines of a bank statement, and the table listing them."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from banking.domains.label import Label, Suggestion

# Operations one bulk action (or selection) takes at most.
MAX_SELECTION = 500
# Choices one filter (banks, accounts, categories) takes at most.
MAX_CHOICES = 100


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


@dataclass(frozen=True)
class OperationFilter:
    """Narrows the operations table; an empty tuple or None filters nothing.

    The criteria combine (AND); the ids of one criterion are alternatives (OR).
    """

    bank_ids: tuple[int, ...] = ()
    account_ids: tuple[int, ...] = ()
    category_ids: tuple[int, ...] = ()
    labelled: bool | None = None
    first: date | None = None
    last: date | None = None


class SortColumn(StrEnum):
    """Columns the operations table sorts on."""

    DATE = "date"
    ACCOUNT = "account"
    DESCRIPTION = "description"
    AMOUNT = "amount"
    CATEGORY = "category"


@dataclass(frozen=True)
class OperationSort:
    """The table's order: a column, then newest first to break ties."""

    column: SortColumn = SortColumn.DATE
    descending: bool = True


@dataclass(frozen=True)
class OperationRow:
    """A row of the operations table; only unlabelled rows get a suggestion."""

    operation: Operation
    account_name: str
    label: Label | None
    suggestion: Suggestion | None = None
