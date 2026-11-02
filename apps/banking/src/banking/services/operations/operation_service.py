"""Operations: read the stored operations of an account."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import NotFoundError
from banking.domains.operation import Operation


class OperationService:
    """Use cases on operations."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.operations = OperationRepository(session)

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
