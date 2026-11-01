"""Turning broken database constraints into domain errors."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from banking.databases.repositories.base import ConstraintViolation
from banking.domains.errors import InvalidError

# Constraint name → (field at fault, message).
ConstraintErrors = Mapping[str, tuple[str, str]]


@contextmanager
def invalid_on(errors: ConstraintErrors) -> Iterator[None]:
    """Raise `InvalidError` for a listed constraint; other violations pass through."""
    try:
        yield
    except ConstraintViolation as exc:
        if exc.constraint not in errors:
            raise
        raise InvalidError(*errors[exc.constraint]) from exc
