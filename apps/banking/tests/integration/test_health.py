from fastapi.testclient import TestClient
from sqlalchemy import inspect

from banking.databases.engine import SCHEMA
from banking.main import create_app


def test_migrations_create_the_banking_schema(engine):
    assert SCHEMA in inspect(engine).get_schema_names()


def test_healthz_reaches_the_database(engine):
    response = TestClient(create_app()).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
