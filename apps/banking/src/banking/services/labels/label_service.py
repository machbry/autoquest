"""Labels: the queue of unlabelled operations, suggestions, and labelling them."""

import logging
from calendar import monthrange
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session

from banking.databases.repositories.base import ConstraintViolation
from banking.databases.repositories.label_repository import LabelRepository
from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import ConflictError, NotFoundError
from banking.domains.label import (
    Label,
    LabelFields,
    LabelSource,
    Queue,
    QueueFilter,
)
from banking.domains.operation import Operation
from banking.services.constraints import invalid_on
from banking.services.labels.matching import match_key, source_of, suggest

logger = logging.getLogger(__name__)

SAVE_ERRORS = {
    "fk_labels_category_id": ("category_id", "This category no longer exists.")
}


@contextmanager
def _save_errors() -> Iterator[None]:
    """Turn the constraints a label write can break into domain errors."""
    try:
        with invalid_on(SAVE_ERRORS):
            yield
    except ConstraintViolation as exc:
        if exc.constraint != "pk_labels":
            raise
        raise ConflictError("This operation already has a label.") from exc


def _values(fields: LabelFields, source: LabelSource) -> dict[str, Any]:
    return {
        "category_id": fields.category_id,
        "tags": list(fields.tags),
        "note": fields.note,
        "source": source,
    }


class LabelService:
    """Use cases on labels; each write is one transaction.

    The source (suggestion accepted or manual) is always decided here, never taken
    from the client.
    """

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.labels = LabelRepository(session)
        self.operations = OperationRepository(session)

    def queue(self, queue_filter: QueueFilter) -> Queue:
        """The oldest unlabelled operation, its suggestion and the similar ones."""
        unlabelled = self._unlabelled(queue_filter)
        if not unlabelled:
            return Queue(None, 0, None, ())
        first = unlabelled[0]
        return Queue(
            operation=first,
            remaining=len(unlabelled),
            suggestion=suggest(self.labels.list_history(), first.description),
            similar_ids=self._similar_ids(first, unlabelled),
        )

    def get(self, operation_id: int) -> Label:
        """The label of this operation.

        Raises:
            NotFoundError: no such label.
        """
        if (label := self.labels.get(operation_id)) is None:
            raise NotFoundError
        return label

    def list_for_account(self, account_id: int) -> Mapping[int, Label]:
        """An account's labels, by operation id."""
        return self.labels.list_for_account(account_id)

    def list_tags(self) -> Sequence[str]:
        """Every tag in use, sorted, for autocompletion."""
        return self.labels.list_tags()

    def create(self, operation_id: int, fields: LabelFields) -> Label:
        """Label an operation.

        Raises:
            NotFoundError: no such operation.
            InvalidError: the category no longer exists.
            ConflictError: the operation already has a label.
        """
        source = self._source(self._operation(operation_id), fields)
        with _save_errors():
            label = self.labels.create(
                {"operation_id": operation_id, **_values(fields, source)}
            )
        self.session.commit()
        logger.info("label %s created", operation_id)
        return label

    def create_for_similar(
        self, operation_id: int, fields: LabelFields, queue_filter: QueueFilter
    ) -> int:
        """Label an operation and the similar ones of the queue alike; count them.

        They share the operation's key, so they share its suggestion and source.

        Raises:
            NotFoundError: no such operation.
            InvalidError: the category no longer exists.
            ConflictError: one of the operations already has a label.
        """
        operation = self._operation(operation_id)
        similar = self._similar_ids(operation, self._unlabelled(queue_filter))
        ids = (operation_id, *similar)
        values = _values(fields, self._source(operation, fields))
        with _save_errors():
            self.labels.create_many({"operation_id": id_, **values} for id_ in ids)
        self.session.commit()
        logger.info("label %s created with %d similar", operation_id, len(similar))
        return len(ids)

    def update(self, operation_id: int, fields: LabelFields) -> Label:
        """Change a label; it becomes manual if its category or tags change.

        Raises:
            NotFoundError: no such label.
            InvalidError: the category no longer exists.
        """
        current = self.get(operation_id)
        unchanged = fields.category_id == current.category.id and set(
            fields.tags
        ) == set(current.tags)
        source = current.source if unchanged else LabelSource.MANUAL
        with _save_errors():
            label = self.labels.update(operation_id, _values(fields, source))
        if label is None:
            raise NotFoundError
        self.session.commit()
        logger.info("label %s updated", operation_id)
        return label

    def _operation(self, operation_id: int) -> Operation:
        if (operation := self.operations.get(operation_id)) is None:
            raise NotFoundError
        return operation

    def _source(self, operation: Operation, fields: LabelFields) -> LabelSource:
        suggestion = suggest(self.labels.list_history(), operation.description)
        return source_of(fields, suggestion)

    def _unlabelled(self, queue_filter: QueueFilter) -> Sequence[Operation]:
        if (month := queue_filter.month) is None:
            return self.operations.list_unlabelled(queue_filter.account_id)
        last = month.replace(day=monthrange(month.year, month.month)[1])
        return self.operations.list_unlabelled(queue_filter.account_id, month, last)

    @staticmethod
    def _similar_ids(
        operation: Operation, unlabelled: Sequence[Operation]
    ) -> tuple[int, ...]:
        """The other unlabelled operations with the operation's key (none if empty)."""
        key = match_key(operation.description)
        return tuple(
            other.id
            for other in unlabelled
            if key and other.id != operation.id and match_key(other.description) == key
        )
