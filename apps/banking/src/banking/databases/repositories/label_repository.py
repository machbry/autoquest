"""Data access to labels."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, select, update

from banking.databases.models import CategoryModel, LabelModel, OperationModel
from banking.databases.repositories.base import Repository
from banking.domains.category import Category
from banking.domains.label import Label, PastLabel


class LabelRepository(Repository[LabelModel, Label]):
    """Labels of the operations, keyed by their operation's id."""

    model = LabelModel

    def to_domain(self, row: LabelModel) -> Label:
        """Convert a row to its domain object."""
        # Usually from the identity map: the listing below loads the categories.
        category = self.session.get_one(CategoryModel, row.category_id)
        return Label(
            operation_id=row.operation_id,
            category=Category(id=category.id, name=category.name),
            source=row.source,
        )

    def list_for_account(self, account_id: int) -> Mapping[int, Label]:
        """An account's labels, by operation id."""
        rows = self.session.execute(
            select(LabelModel, CategoryModel)
            .join(CategoryModel, CategoryModel.id == LabelModel.category_id)
            .join(OperationModel, OperationModel.id == LabelModel.operation_id)
            .where(OperationModel.account_id == account_id)
        )
        return {label.operation_id: self.to_domain(label) for label, _ in rows}

    def list_history(self) -> Sequence[PastLabel]:
        """Every labelled operation, for the "same as last time" rule."""
        rows = self.session.execute(
            select(
                OperationModel.id,
                OperationModel.operation_date,
                OperationModel.description,
                LabelModel.category_id,
            ).join(LabelModel, LabelModel.operation_id == OperationModel.id)
        )
        return [PastLabel(*row) for row in rows]

    def create_many(self, values: Iterable[Mapping[str, Any]]) -> None:
        """Insert labels.

        Raises:
            ConstraintViolation: the values break a named constraint.
        """
        self.session.add_all(self.model(**row) for row in values)
        self._flush()

    def reassign_category(self, from_id: int, to_id: int) -> int:
        """Move every label of a category to another; return how many moved."""
        # An UPDATE returns a CursorResult, though `execute` is typed as `Result`.
        result = cast(
            CursorResult[Any],
            self.session.execute(
                update(LabelModel)
                .where(LabelModel.category_id == from_id)
                .values(category_id=to_id)
            ),
        )
        return result.rowcount
