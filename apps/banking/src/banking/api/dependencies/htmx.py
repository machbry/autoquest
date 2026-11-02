"""Whether a request comes from htmx, which then wants a page fragment."""

from typing import Annotated

from fastapi import Depends, Request


def is_htmx(request: Request) -> bool:
    """True if htmx sent the request (it sets `HX-Request`)."""
    return request.headers.get("hx-request") == "true"


HtmxDep = Annotated[bool, Depends(is_htmx)]
