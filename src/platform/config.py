"""Application settings loaded from environment / .env."""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime-configuration. Все значения из env или .env файла."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Binance
    binance_api_key: str = Field(..., min_length=1)
    binance_api_secret: str = Field(..., min_length=1)
    binance_env: Literal["testnet", "mainnet"] = "testnet"

    # Runtime flags
    trading_enabled: bool = False
    live_trading: bool = False

    # Paths
    data_dir: Path
    log_dir: Path
    db_path: Path
    parquet_dir: Path

    # Observability
    sentry_dsn: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _live_requires_trading(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading=true requires trading_enabled=true")
        return self
