"""Data access to categories."""

from collections.abc import Sequence

from sqlalchemy import func, select

from banking.databases.models import CategoryModel, LabelModel
from banking.databases.repositories.base import Repository
from banking.domains.category import Category


class CategoryRepository(Repository[CategoryModel, Category]):
    """Categories."""

    model = CategoryModel

    def to_domain(self, row: CategoryModel) -> Category:
        """Convert a row to its domain object."""
        return Category(id=row.id, name=row.name)

    def list(self) -> Sequence[Category]:
        """Every category, by name."""
        rows = self.session.scalars(select(CategoryModel).order_by(CategoryModel.name))
        return [self.to_domain(row) for row in rows]

    def list_with_label_counts(self) -> Sequence[tuple[Category, int]]:
        """Every category by name, with how many labels use it."""
        rows = self.session.execute(
            select(CategoryModel, func.count(LabelModel.operation_id))
            .outerjoin(LabelModel, LabelModel.category_id == CategoryModel.id)
            .group_by(CategoryModel.id)
            .order_by(CategoryModel.name)
        )
        return [(self.to_domain(row), count) for row, count in rows]
