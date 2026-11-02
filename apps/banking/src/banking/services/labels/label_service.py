"""Labels: giving operations a category, one by one or in bulk."""

import logging
from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict

from sqlalchemy.orm import Session

from banking.databases.repositories.base import ConstraintViolation
from banking.databases.repositories.category_repository import CategoryRepository
from banking.databases.repositories.label_repository import LabelRepository
from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import ConflictError, InvalidError, NotFoundError
from banking.domains.label import Label, LabelFields
from banking.domains.operation import Operation
from banking.services.constraints import invalid_on

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


class LabelService:
    """Use cases on labels; each write is one transaction."""

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
        self._operation(operation_id)
        with _save_errors():
            label = self.labels.create({"operation_id": operation_id, **asdict(fields)})
        self.session.commit()
        logger.info("label %s created", operation_id)
        return label

    def update(self, operation_id: int, fields: LabelFields) -> Label:
        """Change a label's category.

        Raises:
            NotFoundError: no such label.
            InvalidError: the category no longer exists.
        """
        with _save_errors():
            label = self.labels.update(operation_id, asdict(fields))
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
        """Give operations a category; count them.

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
            self.labels.upsert_many(ids, category_id)
        self.session.commit()
        logger.info("category %s set on %d operations", category_id, len(ids))
        return len(ids)

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
