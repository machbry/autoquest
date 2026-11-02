"""Label forms and the queue filter."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from banking.api.schemas.common import MAX_ID
from banking.domains.label import LabelFields, QueueFilter


class LabelForm(BaseModel):
    """Fields of the label form (queue and edit): a category, 3 tags and a note."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category_id: int = Field(ge=1, le=MAX_ID)
    tag_1: str = Field(default="", max_length=50)
    tag_2: str = Field(default="", max_length=50)
    tag_3: str = Field(default="", max_length=50)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def blank_note_is_none(cls, value: str | None) -> str | None:
        """An empty note means no note."""
        return value or None

    def to_fields(self) -> LabelFields:
        """The label to save: blank tags dropped, duplicates once, in typed order."""
        tags = dict.fromkeys(tag for tag in (self.tag_1, self.tag_2, self.tag_3) if tag)
        return LabelFields(self.category_id, tuple(tags), self.note)


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
