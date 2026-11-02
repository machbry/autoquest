"""Data access to labels."""

from typing import Any, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.orm import Session

from banking.databases.models import LabelModel


class LabelRepository:
    """Labels of the operations.

    Bulk writes only for now; it becomes a `Repository` once labels are read and
    written one by one (#13, labelling queue).
    """

    def __init__(self, session: Session) -> None:
        """Work within the caller's session (and transaction)."""
        self.session = session

    def reassign_category(self, from_id: int, to_id: int) -> int:
        """Move every label of a category to another; return how many moved."""
        # An UPDATE returns a CursorResult, though `execute` is typed as `Result`.
        result = cast(
            CursorResult[Any],
            self.session.execute(
                update(LabelModel)
                .where(LabelModel.category_id == from_id)
                .values(category_id=to_id)
            ),
        )
        return result.rowcount
