"""Account forms."""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from banking.api.schemas.common import MAX_ID
from banking.databases.models import AccountType


class AccountForm(BaseModel):
    """Fields of the declare and edit forms."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    bank_id: int = Field(ge=1, le=MAX_ID)
    type: AccountType
    account_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{1,34}$")
    opened_on: date

    @field_validator("account_number", mode="before")
    @classmethod
    def normalize_account_number(cls, value: Any) -> Any:
        """Drop spaces and uppercase, so formatting never hides a duplicate."""
        if isinstance(value, str):
            value = value.replace(" ", "").upper()
            return value or None
        return value


class CloseForm(BaseModel):
    """Fields of the close form."""

    closed_on: date
