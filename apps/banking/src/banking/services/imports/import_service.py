"""Imports: store an export's operations once, keeping identical same-day ones."""

import logging
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict

from sqlalchemy.orm import Session

from banking.databases.repositories.account_repository import AccountRepository
from banking.databases.repositories.import_repository import ImportRepository
from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import InvalidError, NotFoundError
from banking.domains.import_ import Import
from banking.domains.operation import OperationFields
from banking.services.imports import banque_postale_csv

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 1024 * 1024


def new_occurrences(
    operations: Iterable[OperationFields], known: Mapping[OperationFields, int]
) -> list[tuple[OperationFields, int]]:
    """The operations to add, each with its occurrence number.

    Identical operations on the same day are real, so they can't simply be dropped:
    with `n` copies of an operation in the file and `m` already stored, the copies
    `m + 1 … n` are new.
    """
    return [
        (operation, occurrence)
        for operation, copies in Counter(operations).items()
        for occurrence in range(known.get(operation, 0) + 1, copies + 1)
    ]


class ImportService:
    """Use cases on imports; each import is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.accounts = AccountRepository(session)
        self.imports = ImportRepository(session)
        self.operations = OperationRepository(session)

    def list_for_account(self, account_id: int) -> Sequence[Import]:
        """An account's imports, latest export first."""
        return self.imports.list_for_account(account_id)

    def create(self, account_id: int, content: bytes) -> Import:
        """Import a Banque Postale CSV export; a rejected file writes nothing.

        Raises:
            NotFoundError: no such account.
            InvalidError: the file is too large, malformed, or another account's.
        """
        # Locked until the commit: two imports into one account would count the same
        # stored operations, and both add the same new ones.
        if (account := self.accounts.get_for_update(account_id)) is None:
            raise NotFoundError
        if len(content) > MAX_FILE_BYTES:
            raise InvalidError("file", "The file is over 1 MB.")
        export = banque_postale_csv.parse(content)
        if account.account_number is None:
            raise InvalidError("file", "Set this account's number before importing.")
        if export.account_number.replace(" ", "").upper() != account.account_number:
            raise InvalidError("file", "This file is another account's export.")

        dates = [operation.operation_date for operation in export.operations]
        known = (
            self.operations.count_by_key(account_id, min(dates), max(dates))
            if dates
            else {}
        )
        new = new_occurrences(export.operations, known)
        imported = self.imports.create(
            {
                "account_id": account_id,
                "export_date": export.export_date,
                "balance": export.balance,
                "first_operation_on": min(dates, default=None),
                "last_operation_on": max(dates, default=None),
                "rows_in_file": len(export.operations),
                "rows_new": len(new),
            }
        )
        self.operations.create_many(
            {
                "account_id": account_id,
                "import_id": imported.id,
                "occurrence": occurrence,
                **asdict(operation),
            }
            for operation, occurrence in new
        )
        self.session.commit()
        logger.info(
            "import %s created: %d rows, %d new",
            imported.id,
            imported.rows_in_file,
            imported.rows_new,
        )
        return imported
