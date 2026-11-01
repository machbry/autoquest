"""Generic repository and the error it raises when a constraint is broken."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from banking.databases.models import Base


class ConstraintViolation(Exception):
    """A write broke a named database constraint (unique, foreign key, check)."""

    def __init__(self, constraint: str) -> None:
        """Keep the name of the broken constraint."""
        super().__init__(constraint)
        self.constraint = constraint


class Repository[M: Base]:
    """Data access to one model; writes are flushed, the caller commits."""

    model: type[M]

    def __init__(self, session: Session) -> None:
        """Work within the caller's session (and transaction)."""
        self.session = session

    def get(self, item_id: int) -> M | None:
        """The item with this id, if any."""
        return self.session.get(self.model, item_id)

    def add(self, item: M) -> M:
        """Insert or update an item."""
        self.session.add(item)
        self.flush()
        return item

    def delete(self, item: M) -> None:
        """Delete an item."""
        self.session.delete(item)
        self.flush()

    def flush(self) -> None:
        """Send pending writes; a broken constraint rolls back and is raised by name.

        Raises:
            ConstraintViolation: a write broke a named constraint. The transaction is
                rolled back, since Postgres refuses any further statement in it.
        """
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            diag = getattr(exc.orig, "diag", None)
            constraint = getattr(diag, "constraint_name", None)
            if constraint is None:
                raise
            raise ConstraintViolation(constraint) from exc
