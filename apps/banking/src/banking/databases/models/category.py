"""Table of categories."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import Base, Timestamps


class CategoryModel(Timestamps, Base):
    """Row of `categories`."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
