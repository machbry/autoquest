"""Banks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bank:
    """A bank; it can't be deleted while an account uses it."""

    id: int
    name: str


@dataclass(frozen=True)
class BankFields:
    """What creating or updating a bank sets."""

    name: str
