"""The operations table's query: filters, sort, selection and result notice."""

from datetime import date
from typing import Annotated, Any, Literal
from urllib.parse import urlencode

from pydantic import BaseModel, BeforeValidator, Field, ValidationInfo, field_validator

from banking.api.schemas.common import BoundedId, OptionalId, blank_to_none
from banking.domains.operation import (
    MAX_CHOICES,
    MAX_SELECTION,
    OperationFilter,
    OperationSort,
    SortColumn,
)


def _as_list(value: Any) -> Any:
    """A repeated field: one value is a list of one; blanks are dropped."""
    values = value if isinstance(value, list) else [value]
    return [item for item in values if item not in ("", None)]


Ids = Annotated[list[BoundedId], BeforeValidator(_as_list)]
# The category filter's choice for operations without a category.
NONE = "none"
DEFAULT_SORT = OperationSort()


class OperationFilterForm(BaseModel):
    """Which operations the table shows, and in which order; all optional.

    It travels in the page address (and as hidden fields of the table's forms), so a
    reload or a bookmark keeps it.
    """

    bank: Ids = Field(default=[], max_length=MAX_CHOICES)
    account: Ids = Field(default=[], max_length=MAX_CHOICES)
    category: Annotated[
        list[Literal["none"] | BoundedId], BeforeValidator(_as_list)
    ] = Field(default=[], max_length=MAX_CHOICES + 1)
    from_: Annotated[date | None, BeforeValidator(blank_to_none)] = Field(
        default=None, alias="from"
    )
    to: Annotated[date | None, BeforeValidator(blank_to_none)] = None
    sort: SortColumn = DEFAULT_SORT.column
    order: Literal["asc", "desc"] = "desc"

    @field_validator("to")
    @classmethod
    def not_before_from(cls, value: date | None, info: ValidationInfo) -> date | None:
        """The period can't end before it starts."""
        first = info.data.get("from_")
        if value is not None and first is not None and value < first:
            raise ValueError("The end date can't be before the start date.")
        return value

    def to_filter(self) -> OperationFilter:
        """The filter for the service."""
        return OperationFilter(
            bank_ids=tuple(self.bank),
            account_ids=tuple(self.account),
            category_ids=tuple(item for item in self.category if isinstance(item, int)),
            uncategorized=NONE in self.category,
            first=self.from_,
            last=self.to,
        )

    def to_sort(self) -> OperationSort:
        """The order for the service."""
        return OperationSort(self.sort, self.order == "desc")

    def params(self, **overrides: Any) -> list[tuple[str, str]]:
        """The query's parameters, defaults left out; `overrides` replace some."""
        values: dict[str, Any] = {
            "bank": self.bank,
            "account": self.account,
            "category": self.category,
            "from": self.from_,
            "to": self.to,
            "sort": self.sort,
            "order": self.order,
        } | overrides
        defaults = {"sort": DEFAULT_SORT.column, "order": "desc"}
        return [
            (name, str(item))
            for name, value in values.items()
            if value not in (None, []) and defaults.get(name) != value
            for item in (value if isinstance(value, list) else [value])
        ]

    def url(self, *extra: tuple[str, str | int], **overrides: Any) -> str:
        """The table's address with this query, plus `extra` parameters."""
        query = urlencode([*self.params(**overrides), *extra])
        return f"/operations?{query}" if query else "/operations"


class TableForm(OperationFilterForm):
    """The table page's query: filters, ticked rows, and what to select or report.

    `select=all` ticks every row shown, `similar_to` the rows similar to one; both
    keep the rows already ticked. `notice` reports the last action's count.
    """

    id: Ids = Field(default=[], max_length=MAX_SELECTION)
    select: Literal["all"] | None = None
    similar_to: OptionalId = None
    notice: Literal["set", "removed"] | None = None
    count: int = Field(default=0, ge=0, le=MAX_SELECTION)
