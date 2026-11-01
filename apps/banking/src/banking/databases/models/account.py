"""Accounts and their types."""

from datetime import date
from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from banking.databases.models.bank import Bank
from banking.databases.models.base import Base, Timestamps


class AccountType(StrEnum):
    """Kinds of account; fixed, because the analysis relies on them."""

    CURRENT = "current"
    SAVINGS = "savings"
    PEA = "pea"
    LIFE_INSURANCE = "life_insurance"


class Account(Timestamps, Base):
    """A bank account; closing it keeps its history, deleting it removes it."""

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

    # One-way on purpose: with a Bank.accounts collection, deleting a bank would make
    # the ORM null the accounts' bank_id instead of letting the FK refuse the delete.
    bank: Mapped[Bank] = relationship()
