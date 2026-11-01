import pytest
from pydantic import ValidationError

from banking.config import get_settings
from banking.main import create_app


@pytest.fixture(autouse=True)
def fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_app_refuses_to_start_without_db_url(monkeypatch):
    monkeypatch.delenv("BANKING_DB_URL")

    with pytest.raises(ValidationError, match="db_url"):
        create_app()


def test_app_refuses_a_non_postgres_db_url(monkeypatch):
    monkeypatch.setenv("BANKING_DB_URL", "sqlite:///banking.db")

    with pytest.raises(ValidationError, match="db_url"):
        create_app()
