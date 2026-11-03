"""Validation shared by the routers."""

from typing import Annotated

from fastapi import Path, Query

# Ids are INTEGER: a larger value would make Postgres fail instead of finding nothing.
MAX_ID = 2**31 - 1
Id = Annotated[int, Path(ge=1, le=MAX_ID)]
# The same bounds, for an optional id in the query.
OptionalQueryId = Annotated[int | None, Query(ge=1, le=MAX_ID)]
