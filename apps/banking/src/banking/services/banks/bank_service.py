"""Banks, as the account form offers them; the admin creates and edits them."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.bank_repository import BankRepository
from banking.domains.bank import Bank


class BankService:
    """Use cases on banks."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.banks = BankRepository(session)

    def list(self) -> Sequence[Bank]:
        """Every bank, by name."""
        return self.banks.list()
