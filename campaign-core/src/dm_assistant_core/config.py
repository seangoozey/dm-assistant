"""Typed process configuration loaded only at the application boundary."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Campaign Core runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="CAMPAIGN_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    database_url: PostgresDsn
    environment: Literal["development", "test", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = "info"
    run_migrations: bool = True
    cors_origins: str = ""

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        for origin in (item.strip() for item in value.split(",") if item.strip()):
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
            ):
                raise ValueError("CORS origins must be absolute HTTP(S) origins without a path")
        return value

    @property
    def database_dsn(self) -> str:
        """Return the validated DSN for the PostgreSQL adapter."""

        return str(self.database_url)

    @property
    def allowed_cors_origins(self) -> tuple[str, ...]:
        return tuple(
            item.strip().rstrip("/")
            for item in self.cors_origins.split(",")
            if item.strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Load and cache process settings."""

    return Settings()  # type: ignore[call-arg]
