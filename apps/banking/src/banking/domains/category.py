"""Categories: the type of an expense or income."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """A category; it can't be deleted while a label uses it, only merged."""

    id: int
    name: str


@dataclass(frozen=True)
class CategoryFields:
    """What creating or updating (renaming) a category sets."""

    name: str
