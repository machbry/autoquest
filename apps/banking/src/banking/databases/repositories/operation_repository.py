"""Data access to operations."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select

from banking.databases.models import OperationModel
from banking.databases.repositories.base import Repository
from banking.domains.operation import Operation, OperationFields


class OperationRepository(Repository[OperationModel, Operation]):
    """Operations of the accounts."""

    model = OperationModel

    def to_domain(self, row: OperationModel) -> Operation:
        """Convert a row to its domain object."""
        return Operation(
            id=row.id,
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
