"""Settings read from `BANKING_*` environment variables, validated at startup."""

from functools import cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Banking app settings."""

    model_config = SettingsConfigDict(env_prefix="BANKING_")

    db_url: PostgresDsn


@cache
def get_settings() -> Settings:
    """Return the settings, loaded once from the environment."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
