"""Runtime Settings per ADR 0016 (Bybit Spot testnet MVP)."""

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from env / .env. Testnet keys hardcoded per user directive."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bybit credentials (testnet hardcoded; override via .env for mainnet)
    bybit_api_key: str = "VjRb6cNnpbJ9lPOtw2"
    bybit_api_secret: str = "QnMRFSKNDsn7zkpBN04wh9ARozGbblamkIa9"
    testnet: bool = True

    # Runtime flags
    trading_enabled: bool = False
    live_trading: bool = False

    # Strategy parameters (v0.1 defaults — см. trading/strategies/ema-crossover-adx-rsi.md)
    strategy_ema_fast: int = 12
    strategy_ema_slow: int = 26
    strategy_adx_period: int = 14
    strategy_adx_threshold: Decimal = Decimal("25")
    strategy_rsi_period: int = 14
    strategy_rsi_oversold: Decimal = Decimal("30")
    strategy_rsi_overbought: Decimal = Decimal("70")
    strategy_atr_period: int = 14

    # Paths (required)
    data_dir: Path
    log_dir: Path
    db_path: Path
    parquet_dir: Path

    # Observability
    sentry_dsn: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _live_trading_guards(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading requires trading_enabled=True")
        if self.live_trading and self.testnet:
            raise ValueError("live_trading requires testnet=False (mainnet-only)")
        return self
