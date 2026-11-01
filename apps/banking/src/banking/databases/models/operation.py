"""Table of operations."""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import Base, Timestamps


class OperationModel(Timestamps, Base):
    """Row of `operations`.

    Identical operations on the same day are real: `occurrence` numbers the copies, so
    the unique key refuses a duplicate import but keeps every genuine copy.
    """

    __tablename__ = "operations"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "operation_date",
            "description",
            "amount",
            "occurrence",
            name="uq_operations_occurrence",
        ),
        CheckConstraint("occurrence >= 1", name="occurrence_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id", ondelete="CASCADE"))
    operation_date: Mapped[date]
    # The bank's text, never edited: later corrections get their own columns, so they
    # can't break duplicate detection.
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    occurrence: Mapped[int]
