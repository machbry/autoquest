"""Operations: read the stored operations, alone or as the operations table."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import NotFoundError
from banking.domains.operation import (
    Operation,
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

    def get(self, operation_id: int) -> Operation:
        """The operation with this id.

        Raises:
            NotFoundError: no such operation.
        """
        if (operation := self.operations.get(operation_id)) is None:
            raise NotFoundError
        return operation

    def list_for_account(self, account_id: int) -> Sequence[Operation]:
        """An account's operations, newest first; a closed account keeps them."""
        return self.operations.list_for_account(account_id)

    @staticmethod
    def similar_ids(rows: Sequence[OperationRow], operation_id: int) -> Sequence[int]:
        """The rows similar to this one (same payee), itself included.

        Only among the rows given, so nothing hidden by the filters is picked; none if
        the operation isn't among them.
        """
        operations = [row.operation for row in rows]
        operation = next((op for op in operations if op.id == operation_id), None)
        return [] if operation is None else similar_ids(operation, operations)
