"""Table of banks."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import TRIMMED_NAME, Base, Timestamps


class BankModel(Timestamps, Base):
    """Row of `banks`."""

    __tablename__ = "banks"
    __table_args__ = (CheckConstraint(TRIMMED_NAME, name="name_trimmed"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
