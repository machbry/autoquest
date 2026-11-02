"""The admin's filters: a relation column filters on its records, picked by name."""

from collections.abc import Sequence
from functools import cache
from typing import Any

from sqlalchemy import select
from starlette.requests import Request
from starlette_admin.contrib.sqla.filters import (
    IsNotNullFilter,
    IsNullFilter,
    SqlaFilterRegistry,
)
from starlette_admin.fields import BaseField, RelationField
from starlette_admin.filters import (
    FilterApplyContext,
    FilterDataType,
    FilterValidationError,
    filters,
)
from starlette_admin.filters.base import BaseFilter

from banking.databases.models import AccountModel, CategoryModel

# Ids are INTEGER: a larger value would make Postgres fail instead of finding nothing.
MAX_ID = 2**31 - 1
Named = type[AccountModel] | type[CategoryModel]
# The admin view key of each relation the filters offer → its model, listed by name.
RELATED: dict[str, Named] = {"accounts": AccountModel, "categories": CategoryModel}


def parse_ids(raw: Any) -> list[int]:
    """Ids from the filter builder (a list) or a hand-written URL (comma-separated).

    Raises:
        FilterValidationError: no id, or a value that isn't one.
    """
    values = raw if isinstance(raw, list | tuple) else str(raw).split(",")
    values = [str(value).strip() for value in values if str(value).strip()]
    if not values or not all(
        value.isdigit() and 0 < int(value) <= MAX_ID for value in values
    ):
        raise FilterValidationError("Pick at least one record.")
    return [int(value) for value in values]


@cache
def one_of(model: Named) -> type[BaseFilter]:
    """An "is one of" filter on a relation to `model`, offering its records by name."""

    class OneOf(BaseFilter):
        name = "in"
        label = "Is one of"
        data_type = FilterDataType.ENUM

        def parse_value(self, raw: Any) -> list[int]:
            return parse_ids(raw)

        def get_choices(self, request: Request) -> Sequence[tuple[Any, str]]:
            # Accounts and categories are few: a short query, on the request's
            # session, where the admin asks for them.
            rows = request.state.session.execute(
                select(model.id, model.name).order_by(model.name)
            )
            return [(row.id, row.name) for row in rows]

        def apply(self, ctx: FilterApplyContext) -> Any:
            relation = getattr(ctx.view.model, ctx.field_name)  # type: ignore[union-attr]
            return relation.has(model.id.in_(ctx.value))

    return OneOf


class FilterRegistry(SqlaFilterRegistry):
    """starlette-admin's filters, plus "is one of" on accounts and categories."""

    @filters(RelationField)
    def relation_filters(self, field: BaseField) -> list[type[BaseFilter]]:
        """Null checks, and a pick among the related records when they are named."""
        model = RELATED.get(getattr(field, "key", None) or "")
        named = [] if model is None else [one_of(model)]
        return [*named, IsNullFilter, IsNotNullFilter]
