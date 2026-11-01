"""Table of accounts."""

from datetime import date

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from banking.databases.models.bank import BankModel
from banking.databases.models.base import Base, Timestamps
from banking.domains.account import AccountType


class AccountModel(Timestamps, Base):
    """Row of `accounts`."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("closed_on >= opened_on", name="closed_after_opened"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id", ondelete="RESTRICT"))
    # Stored as its value in a VARCHAR, with a CHECK listing the values.
    type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            name="type",
            native_enum=False,
            create_constraint=True,
            length=14,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    # Optional: some accounts (life insurance) have none.
    account_number: Mapped[str | None] = mapped_column(String(34), unique=True)
    opened_on: Mapped[date]
    closed_on: Mapped[date | None]

    # One-way on purpose: with a BankModel.accounts collection, deleting a bank would
    # make the ORM null the accounts' bank_id instead of letting the FK refuse it.
    bank: Mapped[BankModel] = relationship()
