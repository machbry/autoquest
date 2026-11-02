"""Submitted form data and uploaded files."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from starlette.datastructures import ImmutableMultiDict, UploadFile

from banking.services.imports.import_service import MAX_FILE_BYTES

# Refused before the body is read; smaller bodies are cut, so the service can tell the
# user their file is too large.
MAX_UPLOAD_BYTES = 2 * MAX_FILE_BYTES
# Fields of one form: the account form has the most.
MAX_FORM_FIELDS = 20


def _values(data: ImmutableMultiDict[str, Any]) -> dict[str, Any]:
    """Each field's value; a repeated field (checkboxes) gives the list of its values.

    Postgres text can't hold NUL: it is refused here rather than failing on insert.
    """
    values = {key: data.getlist(key) for key in data}
    if any(
        "\x00" in value
        for items in values.values()
        for value in items
        if isinstance(value, str)
    ):
        raise HTTPException(status_code=422, detail="NUL characters are not allowed")
    return {
        key: items[0] if len(items) == 1 else items for key, items in values.items()
    }


async def form_data(request: Request) -> dict[str, Any]:
    """Read the submitted form.

    Reading a form is async; doing it in a dependency lets the handlers stay sync, so
    FastAPI runs their blocking database calls in a thread, off the event loop.
    """
    return _values(await request.form(max_fields=MAX_FORM_FIELDS))


async def uploaded_file(request: Request) -> bytes:
    """The `file` field's content, cut one byte past what an import accepts.

    Empty if no file was sent. The body's declared length is required: without it (a
    chunked upload), the form parser would spool any size to disk. Browsers always
    send it with a form.
    """
    try:
        length = int(request.headers["content-length"])
    except KeyError:
        raise HTTPException(status_code=411, detail="Length required") from None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid length") from None
    if length > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    form = await request.form(max_files=1, max_fields=1)
    file = form.get("file")
    if not isinstance(file, UploadFile):
        return b""
    return await file.read(MAX_FILE_BYTES + 1)


FormDep = Annotated[dict[str, Any], Depends(form_data)]
UploadDep = Annotated[bytes, Depends(uploaded_file)]
