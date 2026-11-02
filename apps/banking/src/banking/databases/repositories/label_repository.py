"""Data access to labels."""

from collections.abc import Collection, Mapping

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from banking.databases.models import CategoryModel, LabelModel, OperationModel
from banking.databases.repositories.base import Repository
from banking.domains.category import Category
from banking.domains.label import Label


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

    def upsert_many(self, operation_ids: Collection[int], category_id: int) -> None:
        """Give operations a category.

        A label already in this category is left as is, its creation time kept.

        Raises:
            ConstraintViolation: the values break a named constraint.
        """
        if not operation_ids:
            return
        statement = insert(LabelModel).values(
            [{"operation_id": id_, "category_id": category_id} for id_ in operation_ids]
        )
        self._execute(
            statement.on_conflict_do_update(
                index_elements=[LabelModel.operation_id],
                # ON CONFLICT doesn't run the ORM's `onupdate`: set it here.
                set_={
                    "category_id": statement.excluded.category_id,
                    "updated_at": func.now(),
                },
                where=LabelModel.category_id != statement.excluded.category_id,
            )
        )

    def delete_many(self, operation_ids: Collection[int]) -> int:
        """Delete the labels of these operations; return how many there were."""
        statement = delete(LabelModel).where(LabelModel.operation_id.in_(operation_ids))
        return self._execute(statement).rowcount

    def reassign_category(self, from_id: int, to_id: int) -> int:
        """Move every label of a category to another; return how many moved."""
        statement = (
            update(LabelModel)
            .where(LabelModel.category_id == from_id)
            .values(category_id=to_id)
        )
        return self._execute(statement).rowcount
