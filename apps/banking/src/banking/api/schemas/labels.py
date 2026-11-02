"""Label forms: one operation's label, and the operations table's bulk actions."""

from typing import Annotated

from pydantic import BeforeValidator, Field, ValidationInfo, field_validator

from banking.api.schemas.common import OptionalId
from banking.api.schemas.operations import Ids, OperationFilterForm
from banking.domains.operation import MAX_SELECTION


class SelectionForm(OperationFilterForm):
    """A bulk action's operations: the ticked ones.

    The table's filters come along, so the action goes back to the same view.
    """

    id: Ids = Field(default=[], max_length=MAX_SELECTION, validate_default=True)

    @field_validator("id")
    @classmethod
    def some_selected(cls, value: list[int]) -> list[int]:
        """An action needs operations to act on."""
        if not value:
            raise ValueError("Select at least one operation.")
        return value


def _stripped_or_none(value: object) -> object:
    """A name without its outer spaces; blank is none (the other field is used)."""
    if isinstance(value, str):
        return value.strip() or None
    return value


class CategorizeForm(SelectionForm):
    """Set a category on the selection: an existing one, or a new one by name."""

    category_id: OptionalId = None
    new_category: Annotated[str | None, BeforeValidator(_stripped_or_none)] = Field(
        default=None, max_length=50, validate_default=True
    )

    @field_validator("new_category")
    @classmethod
    def one_category(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Exactly one of the two: a category to pick, or a name to create."""
        chosen = info.data.get("category_id") is not None
        if value is None and not chosen and "category_id" in info.data:
            raise ValueError("Choose a category, or name a new one.")
        if value is not None and chosen:
            raise ValueError("Either choose a category or name a new one, not both.")
        return value
