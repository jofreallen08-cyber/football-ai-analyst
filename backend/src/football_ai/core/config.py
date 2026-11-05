"""Application settings loaded from environment variables (and an optional ``.env``).

Secrets are typed as :class:`pydantic.SecretStr` so they never appear in
``repr()``, logs or API responses.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every field maps to an upper-case env variable."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Football AI Analyst"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = True

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://football:football@localhost:5432/football_ai"
    database_echo: bool = False

    # AI provider (used from Phase 4). "mock" never performs network calls.
    ai_provider: Literal["anthropic", "mock"] = "mock"
    ai_model: str = "claude-opus-5-5"
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    ai_max_output_tokens: int = Field(default=4000, ge=256, le=32000)
    ai_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    anthropic_api_key: SecretStr | None = None
    ai_daily_call_limit: int = Field(default=100, ge=0)
    ai_daily_token_limit: int = Field(default=500_000, ge=0)
    ai_max_calls_per_analysis: int = Field(default=5, ge=0, le=20)

    # Data providers.
    data_dir: Path = Path(__file__).resolve().parents[3] / "data"
    openfootball_mode: Literal["bundled", "remote"] = "bundled"
    openfootball_base_url: str = (
        "https://raw.githubusercontent.com/openfootball/football.json/master"
    )
    football_data_org_api_key: SecretStr | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string as well as a list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance (override in tests via dependency)."""
    return Settings()
