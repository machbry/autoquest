"""Table of labels: one per labelled operation."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from banking.databases.models.base import Base, Timestamps


class LabelModel(Timestamps, Base):
    """Row of `labels`; `created_at` dates the labelling, for the time metric."""

    __tablename__ = "labels"

    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), primary_key=True
    )
    # RESTRICT: a category in use can't be deleted, only merged into another.
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
