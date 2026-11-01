"""Banks."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import Base, Timestamps


class Bank(Timestamps, Base):
    """A bank; it can't be deleted while an account uses it."""

    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
