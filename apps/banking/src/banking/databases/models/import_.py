"""Table of imports: one row per imported export file."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import Base


class ImportModel(Base):
    """Row of `imports`; never updated, so it has no `updated_at`."""

    __tablename__ = "imports"
    __table_args__ = (
        CheckConstraint("rows_new BETWEEN 0 AND rows_in_file", name="rows_new_in_file"),
        CheckConstraint(
            "last_operation_on >= first_operation_on", name="first_before_last"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    export_date: Mapped[date]
    # The export's header balance, kept for the balance check to come.
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # None when the file holds no operation.
    first_operation_on: Mapped[date | None]
    last_operation_on: Mapped[date | None]
    rows_in_file: Mapped[int]
    rows_new: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
