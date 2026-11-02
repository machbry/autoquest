"""Category forms."""

from pydantic import BaseModel, ConfigDict, Field

from banking.api.schemas.common import MAX_ID


class CategoryForm(BaseModel):
    """Fields of the create and update (rename) forms."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)


class MergeForm(BaseModel):
    """Fields of the merge form: the category that takes over the labels."""

    into_id: int = Field(ge=1, le=MAX_ID)
