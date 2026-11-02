"""Labels: suggestions, and labelling operations one by one or in bulk."""

import logging
from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from banking.databases.repositories.base import ConstraintViolation
from banking.databases.repositories.category_repository import CategoryRepository
from banking.databases.repositories.label_repository import LabelRepository
from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import ConflictError, InvalidError, NotFoundError
from banking.domains.label import (
    AcceptResult,
    Label,
    LabelFields,
    LabelSource,
    Suggestion,
)
from banking.domains.operation import Operation
from banking.services.constraints import invalid_on
from banking.services.labels.matching import (
    latest_by_key,
    match_key,
    source_of,
    suggest,
)

logger = logging.getLogger(__name__)

SAVE_ERRORS = {
    "fk_labels_category_id": ("category_id", "This category no longer exists.")
}
NEW_CATEGORY_ERRORS = {
    "uq_categories_name": ("new_category", "Another category already has this name.")
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
    return {**asdict(fields), "source": source}


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
        self.categories = CategoryRepository(session)

    def get(self, operation_id: int) -> Label:
        """The label of this operation.

        Raises:
            NotFoundError: no such label.
        """
        if (label := self.labels.get(operation_id)) is None:
            raise NotFoundError
        return label

    def find(self, operation_id: int) -> Label | None:
        """The label of this operation; None if it has none yet."""
        return self.labels.get(operation_id)

    def suggestion_for(self, operation_id: int) -> Suggestion | None:
        """Last time's label for this operation, if a past one matches.

        Raises:
            NotFoundError: no such operation.
        """
        operation = self._operation(operation_id)
        return suggest(self.labels.list_history(), operation.description)

    def list_for_account(self, account_id: int) -> Mapping[int, Label]:
        """An account's labels, by operation id."""
        return self.labels.list_for_account(account_id)

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

    def update(self, operation_id: int, fields: LabelFields) -> Label:
        """Change a label; it becomes manual if its category changes.

        Raises:
            NotFoundError: no such label.
            InvalidError: the category no longer exists.
        """
        current = self.get(operation_id)
        unchanged = fields.category_id == current.category.id
        source = current.source if unchanged else LabelSource.MANUAL
        with _save_errors():
            label = self.labels.update(operation_id, _values(fields, source))
        if label is None:
            raise NotFoundError
        self.session.commit()
        logger.info("label %s updated", operation_id)
        return label

    def set_category(
        self,
        operation_ids: Collection[int],
        category_id: int | None,
        new_name: str | None = None,
    ) -> int:
        """Give operations a category, by hand (`manual`); count them.

        `new_name` creates the category first, in the same transaction: if the name is
        refused, nothing is labelled. Labels already in the category are left as they
        are.

        Raises:
            NotFoundError: one of the operations doesn't exist.
            InvalidError: no category given, the category no longer exists, or another
                category has the new name.
        """
        ids = self._existing(operation_ids)
        if new_name is not None:
            with invalid_on(NEW_CATEGORY_ERRORS):
                category_id = self.categories.create({"name": new_name}).id
            logger.info("category %s created", category_id)
        if category_id is None:
            raise InvalidError("category_id", "Choose a category, or name a new one.")
        with invalid_on(SAVE_ERRORS):
            self.labels.upsert_many(ids, category_id, LabelSource.MANUAL)
        self.session.commit()
        logger.info("category %s set on %d operations", category_id, len(ids))
        return len(ids)

    def accept_suggestions(self, operation_ids: Collection[int]) -> AcceptResult:
        """Label each unlabelled operation with last time's category (`suggestion`).

        Operations without a suggestion, or already labelled, are left as they are.

        Raises:
            NotFoundError: one of the operations doesn't exist.
        """
        operations = self._operations(operation_ids)
        suggestions = latest_by_key(self.labels.list_history())
        values = [
            {
                "operation_id": operation.id,
                "category_id": suggestion.category_id,
                "source": LabelSource.SUGGESTION,
            }
            for operation in operations
            if (suggestion := suggestions.get(match_key(operation.description)))
        ]
        accepted = self.labels.create_missing(values)
        self.session.commit()
        logger.info("suggestions accepted on %d operations", accepted)
        return AcceptResult(accepted, len(operations) - accepted)

    def delete_many(self, operation_ids: Collection[int]) -> int:
        """Remove the labels of operations (back to unlabelled); count those removed.

        Raises:
            NotFoundError: one of the operations doesn't exist.
        """
        deleted = self.labels.delete_many(self._existing(operation_ids))
        self.session.commit()
        logger.info("labels deleted on %d operations", deleted)
        return deleted

    def _operation(self, operation_id: int) -> Operation:
        if (operation := self.operations.get(operation_id)) is None:
            raise NotFoundError
        return operation

    def _operations(self, operation_ids: Collection[int]) -> Sequence[Operation]:
        """The operations with these ids; NotFoundError if one doesn't exist."""
        operations = self.operations.list_by_ids(set(operation_ids))
        if len(operations) != len(set(operation_ids)):
            raise NotFoundError
        return operations

    def _existing(self, operation_ids: Collection[int]) -> list[int]:
        return [operation.id for operation in self._operations(operation_ids)]

    def _source(self, operation: Operation, fields: LabelFields) -> LabelSource:
        return source_of(fields, self.suggestion_for(operation.id))
