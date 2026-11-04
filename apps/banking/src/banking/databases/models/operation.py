"""Table of operations."""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from banking.databases.models.account import AccountModel
from banking.databases.models.base import Base, Timestamps
from banking.databases.models.category import CategoryModel


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
    # The account, date, description and amount are never edited: the
    # `operations_bank_fields_unchanged` trigger refuses it (a CHECK can't see the old
    # values). Later corrections get their own columns, so they can't break duplicate
    # detection.
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id", ondelete="CASCADE"))
    operation_date: Mapped[date]
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    occurrence: Mapped[int]
    # None until labelled. RESTRICT: a category in use can't be deleted, only merged
    # into another. Indexed for those checks and the category filter.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )

    # One-way, as `AccountModel.bank`: the admin shows and edits them.
    account: Mapped[AccountModel] = relationship()
    category: Mapped[CategoryModel | None] = relationship()
