"""Operations: read the stored operations of an account."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.operation import Operation


class OperationService:
    """Use cases on operations."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.operations = OperationRepository(session)

    def list_for_account(self, account_id: int) -> Sequence[Operation]:
        """An account's operations, newest first; a closed account keeps them."""
        return self.operations.list_for_account(account_id)
