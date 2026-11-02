"""Categories: create, rename, merge and delete; a category in use is never deleted."""

import logging
from collections.abc import Sequence
from dataclasses import asdict

from sqlalchemy.orm import Session

from banking.databases.repositories.base import ConstraintViolation
from banking.databases.repositories.category_repository import CategoryRepository
from banking.databases.repositories.label_repository import LabelRepository
from banking.domains.category import Category, CategoryFields
from banking.domains.errors import ConflictError, InvalidError, NotFoundError
from banking.services.constraints import invalid_on

logger = logging.getLogger(__name__)

SAVE_ERRORS = {
    "uq_categories_name": ("name", "Another category already has this name.")
}


class CategoryService:
    """Use cases on categories; each write is one transaction."""

    def __init__(self, session: Session) -> None:
        """Work within this session."""
        self.session = session
        self.categories = CategoryRepository(session)
        self.labels = LabelRepository(session)

    def list(self) -> Sequence[Category]:
        """Every category, by name."""
        return self.categories.list()

    def list_with_label_counts(self) -> Sequence[tuple[Category, int]]:
        """Every category by name, with how many labels use it."""
        return self.categories.list_with_label_counts()

    def get(self, category_id: int) -> Category:
        """The category with this id.

        Raises:
            NotFoundError: no such category.
        """
        if (category := self.categories.get(category_id)) is None:
            raise NotFoundError
        return category

    def create(self, fields: CategoryFields) -> Category:
        """Create a category.

        Raises:
            InvalidError: another category has this name.
        """
        with invalid_on(SAVE_ERRORS):
            category = self.categories.create(asdict(fields))
        self.session.commit()
        logger.info("category %s created", category.id)
        return category

    def update(self, category_id: int, fields: CategoryFields) -> Category:
        """Update (rename) a category; its labels follow, since they hold its id.

        Raises:
            NotFoundError: no such category.
            InvalidError: another category has this name.
        """
        with invalid_on(SAVE_ERRORS):
            category = self.categories.update(category_id, asdict(fields))
        if category is None:
            raise NotFoundError
        self.session.commit()
        logger.info("category %s updated", category_id)
        return category

    def delete(self, category_id: int) -> None:
        """Delete a category.

        Raises:
            NotFoundError: no such category.
            ConflictError: a label still uses it.
        """
        try:
            deleted = self.categories.delete(category_id)
        except ConstraintViolation as exc:
            if exc.constraint != "fk_labels_category_id":
                raise
            raise ConflictError(
                "Labels still use this category: merge it into another instead."
            ) from exc
        if not deleted:
            raise NotFoundError
        self.session.commit()
        logger.info("category %s deleted", category_id)

    def merge(self, category_id: int, into_id: int) -> None:
        """Move every label of a category to another, then delete it.

        Raises:
            NotFoundError: no such category.
            InvalidError: the target is the category itself, or doesn't exist.
        """
        self.get(category_id)
        if into_id == category_id:
            raise InvalidError("into_id", "Pick another category to merge into.")
        if self.categories.get(into_id) is None:
            raise InvalidError("into_id", "This category no longer exists.")
        moved = self.labels.reassign_category(category_id, into_id)
        self.categories.delete(category_id)
        self.session.commit()
        logger.info(
            "category %s merged into %s: %d labels moved", category_id, into_id, moved
        )
