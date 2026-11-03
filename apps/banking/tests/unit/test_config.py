import pytest
from pydantic import ValidationError

from banking.config import Settings, get_settings
from banking.main import create_app


@pytest.fixture(autouse=True)
def fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_read_variables_prefixed_with_the_app_name():
    assert Settings.model_config["env_prefix"] == "BANKING_"


def test_app_refuses_to_start_without_db_url(monkeypatch):
    monkeypatch.delenv("BANKING_DB_URL")

    with pytest.raises(ValidationError, match="db_url"):
        create_app()


def test_app_refuses_a_short_secret_key(monkeypatch):
    monkeypatch.setenv("BANKING_SECRET_KEY", "too short")

    with pytest.raises(ValidationError, match="secret_key"):
        create_app()


def test_app_refuses_a_non_postgres_db_url(monkeypatch):
    monkeypatch.setenv("BANKING_DB_URL", "sqlite:///banking.db")

    with pytest.raises(ValidationError, match="db_url"):
        create_app()
