"""Settings read from `BANKING_*` environment variables, validated at startup."""

from functools import cache

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Banking app settings."""

    model_config = SettingsConfigDict(env_prefix="BANKING_")

    db_url: PostgresDsn
    # Signs the admin's CSRF and flash cookies; the same on every instance.
    secret_key: SecretStr = Field(min_length=32)


@cache
def get_settings() -> Settings:
    """Return the settings, loaded once from the environment."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
