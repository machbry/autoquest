"""SQLAlchemy models of the `banking` schema; migrations are generated from them."""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from banking.db import SCHEMA

# Named constraints, so a violation can be mapped back to the form field that caused it.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """Base class of every banking model."""

    metadata = MetaData(schema=SCHEMA, naming_convention=NAMING_CONVENTION)
    # Timestamps are stored in UTC; business dates are plain `date` columns.
    type_annotation_map = {datetime: DateTime(timezone=True)}


class Bank(StrEnum):
    """Banks the app knows."""

    BANQUE_POSTALE = "banque_postale"
    CFCAL = "cfcal"
    FORTUNEO = "fortuneo"
    GOODVEST = "goodvest"


class AccountType(StrEnum):
    """Kinds of account."""

    CURRENT = "current"
    SAVINGS = "savings"
    PEA = "pea"
    LIFE_INSURANCE = "life_insurance"


def _check_enum(enum: type[StrEnum], name: str) -> Enum:
    """Store an enum as its value in a VARCHAR, with a CHECK listing the values."""
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(member.value) for member in enum),
        values_callable=lambda members: [member.value for member in members],
    )


class Account(Base):
    """A bank account; closing it keeps its history."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("closed_on >= opened_on", name="closed_after_opened"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    bank: Mapped[Bank] = mapped_column(_check_enum(Bank, "bank"))
    type: Mapped[AccountType] = mapped_column(_check_enum(AccountType, "type"))
    # Optional: some accounts (life insurance) have none.
    account_number: Mapped[str | None] = mapped_column(String(34), unique=True)
    opened_on: Mapped[date]
    closed_on: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
