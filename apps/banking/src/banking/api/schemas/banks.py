"""Bank forms."""

from pydantic import BaseModel, ConfigDict, Field


class BankForm(BaseModel):
    """Fields of the add and rename forms."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
