"""Submitted form data and uploaded files."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from starlette.datastructures import UploadFile

from banking.services.imports.import_service import MAX_FILE_BYTES

# Refused before the body is read; smaller bodies are cut, so the service can tell the
# user their file is too large.
MAX_UPLOAD_BYTES = 2 * MAX_FILE_BYTES


async def form_data(request: Request) -> dict[str, Any]:
    """Read the submitted form.

    Reading a form is async; doing it in a dependency lets the handlers stay sync, so
    FastAPI runs their blocking database calls in a thread, off the event loop.
    """
    data = dict(await request.form())
    # Postgres text can't hold NUL: refuse it here rather than fail on insert.
    if any("\x00" in value for value in data.values() if isinstance(value, str)):
        raise HTTPException(status_code=422, detail="NUL characters are not allowed")
    return data


async def uploaded_file(request: Request) -> bytes:
    """The `file` field's content, cut one byte past what an import accepts.

    Empty if no file was sent.
    """
    if int(request.headers.get("content-length") or 0) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    form = await request.form(max_files=1, max_fields=1)
    file = form.get("file")
    if not isinstance(file, UploadFile):
        return b""
    return await file.read(MAX_FILE_BYTES + 1)


FormDep = Annotated[dict[str, Any], Depends(form_data)]
UploadDep = Annotated[bytes, Depends(uploaded_file)]
