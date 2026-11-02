"""Operations: each account's monthly recap; the admin lists and labels them."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.operation import MonthRecap


class OperationService:
    """Use cases on operations."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.operations = OperationRepository(session)

    def recap(self, account_id: int) -> Sequence[MonthRecap]:
        """An account's months, latest first: operations, labelled and unlabelled."""
        return self.operations.count_by_month(account_id)
