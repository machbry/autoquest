"""Generic repository and the error it raises when a constraint is broken."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from banking.databases.models import Base


class ConstraintViolation(Exception):
    """A write broke a named database constraint (unique, foreign key, check)."""

    def __init__(self, constraint: str) -> None:
        """Keep the name of the broken constraint."""
        super().__init__(constraint)
        self.constraint = constraint


class Repository[M: Base, D]:
    """Data access to one model; takes and returns domain objects, never rows.

    Writes are flushed, so constraints are checked; the caller (a service) commits.
    """

    model: type[M]

    def __init__(self, session: Session) -> None:
        """Work within the caller's session (and transaction)."""
        self.session = session

    def to_domain(self, row: M) -> D:
        """Convert a row to its domain object."""
        raise NotImplementedError

    def get(self, item_id: int) -> D | None:
        """The item with this id, if any."""
        row = self.session.get(self.model, item_id)
        return None if row is None else self.to_domain(row)

    def create(self, values: Mapping[str, Any]) -> D:
        """Insert an item.

        Raises:
            ConstraintViolation: the values break a named constraint.
        """
        row = self.model(**values)
        self.session.add(row)
        self._flush()
        return self.to_domain(row)

    def _flush(self) -> None:
        """Send pending writes.

        Raises:
            ConstraintViolation: a write breaks a named constraint.
        """
        with self._constraints():
            self.session.flush()

    @contextmanager
    def _constraints(self) -> Iterator[None]:
        """Raise a broken constraint by name, after rolling back.

        The transaction is rolled back because Postgres refuses any further statement
        in it.
        """
        try:
            yield
        except IntegrityError as exc:
            self.session.rollback()
            diag = getattr(exc.orig, "diag", None)
            constraint = getattr(diag, "constraint_name", None)
            if constraint is None:
                raise
            raise ConstraintViolation(constraint) from exc
