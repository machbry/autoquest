"""Submitted form data."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request


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


FormDep = Annotated[dict[str, Any], Depends(form_data)]
