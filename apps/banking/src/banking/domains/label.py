"""Labels: what an operation was for."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from banking.domains.category import Category


class LabelSource(StrEnum):
    """How a label was set; the share of suggestions accepted is a success metric."""

    SUGGESTION = "suggestion"
    MANUAL = "manual"


@dataclass(frozen=True)
class LabelFields:
    """What creating or updating a label sets; the source is decided by the service."""

    category_id: int


@dataclass(frozen=True)
class Label:
    """An operation's label: its category."""

    operation_id: int
    category: Category
    source: LabelSource


@dataclass(frozen=True)
class PastLabel:
    """A labelled operation, as the "same as last time" rule reads it."""

    operation_id: int
    operation_date: date
    description: str
    category_id: int


@dataclass(frozen=True)
class Suggestion:
    """Last time's category, from the operation dated `from_date`."""

    category_id: int
    from_date: date


@dataclass(frozen=True)
class AcceptResult:
    """Suggestions accepted, and operations that had none to accept."""

    accepted: int
    skipped: int
