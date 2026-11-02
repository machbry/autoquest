"""Data access to operations."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import Date, func, select

from banking.databases.models import OperationModel
from banking.databases.repositories.base import Repository
from banking.domains.operation import MonthRecap, Operation, OperationFields


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
            category_id=row.category_id,
        )

    def count_by_month(self, account_id: int) -> Sequence[MonthRecap]:
        """An account's operations and labelled ones, counted by month, latest first."""
        month = func.date_trunc("month", OperationModel.operation_date).cast(Date)
        rows = self.session.execute(
            select(month, func.count(), func.count(OperationModel.category_id))
            .where(OperationModel.account_id == account_id)
            .group_by(month)
            .order_by(month.desc())
        )
        return [MonthRecap(*row) for row in rows]

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
