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

    # Risk-module parameters (Sprint 4 Task 2 — locked design)
    risk_max_position_pct_cap: Decimal = Decimal("0.05")
    risk_sl_atr_multiplier: Decimal = Decimal("1.5")
    risk_tp_atr_multiplier: Decimal = Decimal("3.0")
    risk_cb_l1_dd: Decimal = Decimal("0.15")
    risk_cb_l2_dd: Decimal = Decimal("0.22")
    risk_cb_l3_dd: Decimal = Decimal("0.30")
    risk_cb_flash_abs: Decimal = Decimal("0.08")
    risk_cb_flash_atr_mult: Decimal = Decimal("3.0")
    risk_kelly_phase1_cap: Decimal = Decimal("0.01")
    risk_kelly_phase2_cap: Decimal = Decimal("0.02")
    risk_kelly_phase3_cap: Decimal = Decimal("0.03")
    risk_kelly_phase4_cap: Decimal = Decimal("0.05")
    risk_override_path: Path = Path("./state/cb_override.json")

    @model_validator(mode="after")
    def _live_trading_guards(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading requires trading_enabled=True")
        if self.live_trading and self.testnet:
            raise ValueError("live_trading requires testnet=False (mainnet-only)")
        return self

    def config_hash(self) -> str:
        """SHA-256 of canonical JSON dump (sorted keys, Decimals as str)."""
        import hashlib
        import json

        data = self.model_dump(mode="json")
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
