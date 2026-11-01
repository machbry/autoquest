"""Table of banks."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import Base, Timestamps


class BankModel(Timestamps, Base):
    """Row of `banks`."""

    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
