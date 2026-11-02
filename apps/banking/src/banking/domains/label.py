"""Labels: what an operation was for."""

from dataclasses import dataclass

from banking.domains.category import Category


@dataclass(frozen=True)
class LabelFields:
    """What creating or updating a label sets."""

    category_id: int


@dataclass(frozen=True)
class Label:
    """An operation's label: its category."""

    operation_id: int
    category: Category
