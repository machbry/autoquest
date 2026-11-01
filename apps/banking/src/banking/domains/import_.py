"""Bank exports and their imports (`import` is a keyword, hence `import_`)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from banking.domains.operation import OperationFields


@dataclass(frozen=True)
class Export:
    """A bank export file, parsed; the raw file itself is never stored."""

    account_number: str
    export_date: date
    balance: Decimal
    operations: tuple[OperationFields, ...]


@dataclass(frozen=True)
class Import:
    """One imported export: what the file held and how much of it was new."""

    id: int
    account_id: int
    export_date: date
    balance: Decimal
    first_operation_on: date | None
    last_operation_on: date | None
    rows_in_file: int
    rows_new: int
    created_at: datetime

    @property
    def rows_known(self) -> int:
        """Rows of the file that were already stored."""
        return self.rows_in_file - self.rows_new
