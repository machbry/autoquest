"""Labels: what an operation was for."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from banking.domains.category import Category
from banking.domains.operation import Operation


class LabelSource(StrEnum):
    """How a label was set; the share of suggestions accepted is a success metric."""

    SUGGESTION = "suggestion"
    MANUAL = "manual"


@dataclass(frozen=True)
class LabelFields:
    """What creating or updating a label sets; the source is decided by the service."""

    category_id: int
    tags: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class Label:
    """An operation's label: its category, free-text tags and an optional note."""

    operation_id: int
    category: Category
    tags: tuple[str, ...]
    note: str | None
    source: LabelSource


@dataclass(frozen=True)
class PastLabel:
    """A labelled operation, as the "same as last time" rule reads it."""

    operation_id: int
    operation_date: date
    description: str
    category_id: int
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Suggestion:
    """Last time's category and tags, from the operation dated `from_date`."""

    category_id: int
    tags: tuple[str, ...]
    from_date: date


@dataclass(frozen=True)
class QueueFilter:
    """Narrows the queue to an account and to a month (its first day); None is all."""

    account_id: int | None = None
    month: date | None = None


@dataclass(frozen=True)
class Queue:
    """The oldest unlabelled operation, if any, and what helps label it."""

    operation: Operation | None
    remaining: int
    suggestion: Suggestion | None
    # The other unlabelled operations of the queue that match the first one.
    similar_ids: tuple[int, ...]
