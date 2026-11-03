"""Uploaded files."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from starlette.datastructures import UploadFile

from banking.services.imports.import_service import MAX_FILE_BYTES

# Refused before the body is read; smaller bodies are cut, so the service can tell the
# user their file is too large.
MAX_UPLOAD_BYTES = 2 * MAX_FILE_BYTES


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


UploadDep = Annotated[bytes, Depends(uploaded_file)]
