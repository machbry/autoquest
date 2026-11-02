"""Label forms and the queue filter."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from banking.api.schemas.common import MAX_ID
from banking.domains.label import QueueFilter


class LabelForm(BaseModel):
    """Fields of the label form (queue and edit): the category."""

    category_id: int = Field(ge=1, le=MAX_ID)


class QueueLabelForm(LabelForm):
    """The queue's label form: which operation, and whether to label the similar."""

    operation_id: int = Field(ge=1, le=MAX_ID)
    scope: Literal["one", "similar"] = "one"


class QueueFilterForm(BaseModel):
    """The queue filter: an account and a month (`YYYY-MM`), both optional."""

    account_id: int | None = Field(default=None, ge=1, le=MAX_ID)
    month: date | None = None

    @field_validator("account_id", mode="before")
    @classmethod
    def blank_is_none(cls, value: Any) -> Any:
        """An empty field filters nothing."""
        return value or None

    @field_validator("month", mode="before")
    @classmethod
    def parse_month(cls, value: Any) -> Any:
        """`YYYY-MM`, as `<input type="month">` sends it, is the month's first day."""
        if not value:
            return None
        if isinstance(value, str):
            year, _, month = value.partition("-")
            if not (len(year) == 4 and len(month) == 2):
                raise ValueError("Use the format YYYY-MM.")
            return f"{value}-01"
        return value

    def to_filter(self) -> QueueFilter:
        """The filter for the service."""
        return QueueFilter(self.account_id, self.month)
