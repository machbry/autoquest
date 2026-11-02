"""Validation shared by the routers."""

from typing import Annotated, Any

from fastapi import Path
from pydantic import BeforeValidator, Field


def blank_to_none(value: Any) -> Any:
    """An empty form field is no value."""
    return value or None


# Ids are INTEGER: a larger value would make Postgres fail instead of finding nothing.
MAX_ID = 2**31 - 1
Id = Annotated[int, Path(ge=1, le=MAX_ID)]
# The same bounds, for ids sent in a form or a query.
BoundedId = Annotated[int, Field(ge=1, le=MAX_ID)]
OptionalId = Annotated[BoundedId | None, BeforeValidator(blank_to_none)]
