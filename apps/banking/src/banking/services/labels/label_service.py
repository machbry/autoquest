"""Labels: giving operations a category, or taking it away, in bulk."""

import logging
from collections.abc import Collection, Sequence

from sqlalchemy.orm import Session

from banking.databases.repositories.category_repository import CategoryRepository
from banking.databases.repositories.label_repository import LabelRepository
from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.errors import InvalidError, NotFoundError
from banking.domains.operation import Operation
from banking.services.constraints import invalid_on

logger = logging.getLogger(__name__)

SAVE_ERRORS = {
    "fk_labels_category_id": ("category_id", "This category no longer exists.")
}
NEW_CATEGORY_ERRORS = {
    "uq_categories_name": ("new_category", "Another category already has this name.")
}


class LabelService:
    """Use cases on labels; each write is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.labels = LabelRepository(session)
        self.operations = OperationRepository(session)
        self.categories = CategoryRepository(session)

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

    def _operations(self, operation_ids: Collection[int]) -> Sequence[Operation]:
        """The operations with these ids; NotFoundError if one doesn't exist."""
        operations = self.operations.list_by_ids(set(operation_ids))
        if len(operations) != len(set(operation_ids)):
            raise NotFoundError
        return operations

    def _existing(self, operation_ids: Collection[int]) -> list[int]:
        return [operation.id for operation in self._operations(operation_ids)]
