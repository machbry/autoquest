"""Request logs hold no personal data: only a real server writes them."""

import logging
import socket
import time
from collections.abc import Iterator
from threading import Thread

import httpx
import pytest
import uvicorn

from banking.main import create_app

LIST = "/admin/operations/list"


@pytest.fixture
def served(engine, caplog) -> Iterator[httpx.Client]:
    """A client of the app behind a real uvicorn, its logs in `caplog`."""
    # The test's own client logs the addresses it requests: only the server counts.
    for client_logger in ("httpx", "httpcore"):
        caplog.set_level(logging.WARNING, logger=client_logger)
    # Last: this also sets the level of caplog's handler.
    caplog.set_level(logging.DEBUG)
    # No log configuration: uvicorn's records propagate up to caplog.
    server = uvicorn.Server(uvicorn.Config(create_app(), log_config=None))
    with socket.create_server(("127.0.0.1", 0)) as listener:
        thread = Thread(target=server.run, kwargs={"sockets": [listener]})
        thread.start()
        while not server.started:
            time.sleep(0.01)
        port = listener.getsockname()[1]
        with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
            yield client
        server.should_exit = True
        thread.join()


@pytest.mark.parametrize(
    ("params", "secret", "status"),
    [
        ({"q": "SECRETSEARCH"}, "SECRETSEARCH", 200),
        (
            {"filter": "description__contains=SECRETFILTER"},
            "SECRETFILTER",
            200,
        ),
        ({"filter": "amount__gt=4321.77"}, "4321.77", 200),
        ({"filter": "amount__eq=notanumber4321"}, "notanumber4321", 400),
    ],
)
def test_request_logs_keep_method_path_and_status_only(
    served, caplog, params, secret, status
):
    assert served.get(LIST, params=params).status_code == status

    assert secret not in caplog.text
    access = [
        record.getMessage()
        for record in caplog.records
        if record.name == "uvicorn.access"
    ]
    assert access == [f'- - "GET {LIST} HTTP/1.1" {status}']
