import logging

from fastapi.testclient import TestClient
from sqlalchemy import text

from banking.db import get_engine
from banking.main import create_app


def test_database_errors_are_logged_without_the_values_at_fault(engine, caplog):
    # Regression: a failed query logged its parameters and Postgres' message, which
    # quotes the values at fault (names, account numbers).
    app = create_app()

    @app.get("/fail")
    def fail():
        with get_engine().connect() as connection:
            connection.execute(
                text("SELECT CAST(:value AS integer)"), {"value": "secret"}
            )

    with caplog.at_level(logging.ERROR):
        response = TestClient(app, raise_server_exceptions=False).get("/fail")

    assert response.status_code == 500
    assert "22P02" in caplog.text  # invalid_text_representation, logged by code
    assert "secret" not in caplog.text
