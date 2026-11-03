"""What every view shares: records by name, broken constraints shown by their cause."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from starlette_admin import StringField
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import ActionFailed, FormValidationError
from starlette_admin.filters import FilterRegistry as BaseFilterRegistry

from banking.admin.filters import FilterRegistry

MAX_ID = 2**31 - 1  # largest INTEGER


def constraint(exc: IntegrityError) -> str | None:
    """The name of the constraint a write broke, if Postgres gave it."""
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)


def ids(pks: Sequence[Any]) -> list[int]:
    """The selected records' ids, as integers."""
    return [int(pk) for pk in pks]


def valid_id(raw: Any) -> int | None:
    """The id `raw` names, if it is one an INTEGER column can hold; else None."""
    if not isinstance(raw, str | int) or not str(raw).isdigit():
        return None
    return int(raw) if 1 <= int(raw) <= MAX_ID else None


class View(ModelView):
    """A view whose records show by name, and whose broken constraints say why."""

    page_size = 50
    page_size_options = [50, 100, 500]
    # Broken constraint → (field at fault, message), for a create or an edit.
    save_errors: dict[str, tuple[str, str]] = {}
    # Broken constraint → message, for a delete.
    delete_errors: dict[str, str] = {}

    def get_filter_registry(self) -> BaseFilterRegistry:
        """starlette-admin's filters, plus "is one of" on relations."""
        return FilterRegistry()

    async def repr(self, obj: Any, request: Request) -> str:
        """A record shows by its name (in relations, pickers and messages)."""
        return str(obj.name)

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        """The record with this id; None for an invalid one, rather than failing."""
        # Regression: a non-numeric id in the address answered 500.
        if (record_id := valid_id(pk)) is None:
            return None
        return await super().find_by_pk(request, record_id)

    async def handle_exception(self, request: Request, exc: Exception) -> None:
        """Show a known broken constraint next to its field; raise anything else."""
        if isinstance(exc, IntegrityError) and constraint(exc) in self.save_errors:
            field, message = self.save_errors[constraint(exc)]  # type: ignore[index]
            raise FormValidationError({field: message}) from exc
        raise exc

    async def delete(self, request: Request, pks: list[Any]) -> int | None:
        """Delete records; refuse, saying why, those still in use."""
        try:
            return await super().delete(request, pks)
        except IntegrityError as exc:
            if (message := self.delete_errors.get(constraint(exc) or "")) is None:
                raise
            raise ActionFailed(message) from exc


class NamedView(View):
    """Records with a name: trimmed, required, as long as its column allows."""

    fields = [StringField("name")]
    fields_default_sort = ["name"]

    async def validate(self, request: Request, data: dict[str, Any]) -> None:
        """Trim the name, refusing it blank or too long (with the field's error).

        Raises:
            FormValidationError: the name is blank or too long.
        """
        name = str(data.get("name") or "").strip()
        limit = self.model.__table__.c.name.type.length
        if not name:
            raise FormValidationError({"name": "Enter a name."})
        # Postgres text can't hold NUL: refused here rather than failing on insert.
        if "\x00" in name:
            raise FormValidationError({"name": "Invalid character."})
        if len(name) > limit:
            raise FormValidationError({"name": f"{limit} characters at most."})
        data["name"] = name
