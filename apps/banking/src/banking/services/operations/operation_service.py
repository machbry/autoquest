"""Operations: the operations table, and each account's monthly recap."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.operation import (
    MonthRecap,
    OperationFilter,
    OperationRow,
    OperationSort,
)
from banking.services.labels.matching import similar_ids


class OperationService:
    """Use cases on operations."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.operations = OperationRepository(session)

    def list(
        self, operation_filter: OperationFilter, sort: OperationSort
    ) -> Sequence[OperationRow]:
        """The operations table: the operations the filter keeps, sorted."""
        return self.operations.list_filtered(operation_filter, sort)

    def recap(self, account_id: int) -> Sequence[MonthRecap]:
        """An account's months, latest first: operations, labelled and unlabelled."""
        return self.operations.count_by_month(account_id)

    @staticmethod
    def similar_ids(rows: Sequence[OperationRow], operation_id: int) -> Sequence[int]:
        """The rows similar to this one (same payee), itself included.

        Only among the rows given, so nothing hidden by the filters is picked; none if
        the operation isn't among them.
        """
        operations = [row.operation for row in rows]
        operation = next((op for op in operations if op.id == operation_id), None)
        return [] if operation is None else similar_ids(operation, operations)
