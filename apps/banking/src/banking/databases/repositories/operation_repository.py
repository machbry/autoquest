"""Data access to operations."""

from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import ColumnElement, Date, func, select

from banking.databases.models import (
    AccountModel,
    CategoryModel,
    LabelModel,
    OperationModel,
)
from banking.databases.repositories.base import Repository
from banking.domains.category import Category
from banking.domains.label import Label
from banking.domains.operation import (
    MonthRecap,
    Operation,
    OperationFields,
    OperationFilter,
    OperationRow,
    OperationSort,
    SortColumn,
)

SORT_COLUMNS = {
    SortColumn.DATE: OperationModel.operation_date,
    SortColumn.ACCOUNT: AccountModel.name,
    SortColumn.DESCRIPTION: OperationModel.description,
    SortColumn.AMOUNT: OperationModel.amount,
    SortColumn.CATEGORY: CategoryModel.name,
}


def _criteria(operation_filter: OperationFilter) -> list[ColumnElement[bool]]:
    """What the filter keeps, as conditions to combine."""
    criteria: list[ColumnElement[bool]] = []
    if operation_filter.bank_id is not None:
        criteria.append(AccountModel.bank_id == operation_filter.bank_id)
    if operation_filter.account_id is not None:
        criteria.append(OperationModel.account_id == operation_filter.account_id)
    if operation_filter.category_id is not None:
        criteria.append(LabelModel.category_id == operation_filter.category_id)
    if operation_filter.uncategorized:
        criteria.append(LabelModel.operation_id.is_(None))
    if (month := operation_filter.month) is not None:
        next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        criteria.append(OperationModel.operation_date >= month)
        criteria.append(OperationModel.operation_date < next_month)
    return criteria


class OperationRepository(Repository[OperationModel, Operation]):
    """Operations of the accounts."""

    model = OperationModel

    def to_domain(self, row: OperationModel) -> Operation:
        """Convert a row to its domain object."""
        return Operation(
            id=row.id,
            account_id=row.account_id,
            operation_date=row.operation_date,
            description=row.description,
            amount=row.amount,
        )

    def list_filtered(
        self, operation_filter: OperationFilter, sort: OperationSort
    ) -> Sequence[OperationRow]:
        """The operations the filter keeps, with their account and label, sorted.

        Ties, and rows without a category when sorting on it (always last), are newest
        first.
        """
        column = SORT_COLUMNS[sort.column]
        order = column.desc() if sort.descending else column.asc()
        query = (
            select(OperationModel, AccountModel.name, LabelModel, CategoryModel)
            .join(AccountModel, AccountModel.id == OperationModel.account_id)
            .outerjoin(LabelModel, LabelModel.operation_id == OperationModel.id)
            .outerjoin(CategoryModel, CategoryModel.id == LabelModel.category_id)
            .order_by(
                order.nulls_last(),
                OperationModel.operation_date.desc(),
                OperationModel.id.desc(),
            )
        )
        rows = self.session.execute(query.where(*_criteria(operation_filter)))
        return [
            OperationRow(
                operation=self.to_domain(operation),
                account_name=account_name,
                label=None
                if label is None
                else Label(
                    operation_id=label.operation_id,
                    category=Category(id=category.id, name=category.name),
                ),
            )
            for operation, account_name, label, category in rows
        ]

    def count_by_month(self, account_id: int) -> Sequence[MonthRecap]:
        """An account's operations and labels counted by month, latest first."""
        month = func.date_trunc("month", OperationModel.operation_date).cast(Date)
        rows = self.session.execute(
            select(month, func.count(), func.count(LabelModel.operation_id))
            .outerjoin(LabelModel, LabelModel.operation_id == OperationModel.id)
            .where(OperationModel.account_id == account_id)
            .group_by(month)
            .order_by(month.desc())
        )
        return [MonthRecap(*row) for row in rows]

    def list_by_ids(self, operation_ids: Collection[int]) -> Sequence[Operation]:
        """The operations with these ids; unknown ids are left out."""
        rows = self.session.scalars(
            select(OperationModel).where(OperationModel.id.in_(operation_ids))
        )
        return [self.to_domain(row) for row in rows]

    def count_by_key(
        self, account_id: int, first: date, last: date
    ) -> Mapping[OperationFields, int]:
        """How many copies of each operation an account holds between two dates."""
        key = (
            OperationModel.operation_date,
            OperationModel.description,
            OperationModel.amount,
        )
        rows = self.session.execute(
            select(*key, func.count())
            .filter_by(account_id=account_id)
            .where(OperationModel.operation_date.between(first, last))
            .group_by(*key)
        )
        return {
            OperationFields(operation_date, description, amount): count
            for operation_date, description, amount, count in rows
        }

    def create_many(self, values: Iterable[Mapping[str, Any]]) -> None:
        """Insert operations.

        Raises:
            ConstraintViolation: the values break a named constraint.
        """
        self.session.add_all(self.model(**row) for row in values)
        self._flush()
