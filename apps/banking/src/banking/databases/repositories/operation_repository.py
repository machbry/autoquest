"""Data access to operations."""

from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, func, select

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
    if operation_filter.bank_ids:
        criteria.append(AccountModel.bank_id.in_(operation_filter.bank_ids))
    if operation_filter.account_ids:
        criteria.append(OperationModel.account_id.in_(operation_filter.account_ids))
    if operation_filter.category_ids:
        criteria.append(LabelModel.category_id.in_(operation_filter.category_ids))
    if operation_filter.labelled is not None:
        labelled = LabelModel.operation_id.is_not(None)
        criteria.append(labelled if operation_filter.labelled else ~labelled)
    if operation_filter.first is not None:
        criteria.append(OperationModel.operation_date >= operation_filter.first)
    if operation_filter.last is not None:
        criteria.append(OperationModel.operation_date <= operation_filter.last)
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

    def list_for_account(self, account_id: int) -> Sequence[Operation]:
        """An account's operations, newest first."""
        rows = self.session.scalars(
            select(OperationModel)
            .filter_by(account_id=account_id)
            .order_by(OperationModel.operation_date.desc(), OperationModel.id.desc())
        )
        return [self.to_domain(row) for row in rows]

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
                    source=label.source,
                ),
            )
            for operation, account_name, label, category in rows
        ]

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
