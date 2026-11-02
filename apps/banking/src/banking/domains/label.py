"""Labels: what an operation was for."""

from dataclasses import dataclass

from banking.domains.category import Category


@dataclass(frozen=True)
class Label:
    """An operation's label: its category."""

    operation_id: int
    category: Category
