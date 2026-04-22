"""Tests for Settings (pydantic-settings v2) per ADR 0016."""

import pytest
from pydantic import ValidationError
from src.platform.config import Settings


def test_defaults_load_testnet_keys() -> None:
    """Testnet keys are hardcoded defaults per user directive 2026-04-21."""
    s = Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )
    assert s.bybit_api_key == "VjRb6cNnpbJ9lPOtw2"
    assert s.bybit_api_secret.startswith("QnMRFSKNDsn7zkpBN04wh9")
    assert s.testnet is True
    assert s.trading_enabled is False
    assert s.live_trading is False


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env vars override hardcoded defaults."""
    monkeypatch.setenv("BYBIT_API_KEY", "override_key")
    monkeypatch.setenv("BYBIT_API_SECRET", "override_secret")
    monkeypatch.setenv("TESTNET", "false")
    monkeypatch.setenv("TRADING_ENABLED", "true")
    s = Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )
    assert s.bybit_api_key == "override_key"
    assert s.bybit_api_secret == "override_secret"
    assert s.testnet is False


def test_live_trading_requires_mainnet() -> None:
    """live_trading=True requires testnet=False (safety invariant)."""
    with pytest.raises(ValidationError, match="live_trading requires testnet=False"):
        Settings(
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            trading_enabled=True,
            live_trading=True,
            testnet=True,
        )


def test_live_trading_requires_trading_enabled() -> None:
    """live_trading=True requires trading_enabled=True."""
    with pytest.raises(ValidationError, match="live_trading requires trading_enabled"):
        Settings(
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            trading_enabled=False,
            live_trading=True,
            testnet=False,
        )


def test_settings_strategy_params_defaults() -> None:
    """Strategy params defaults from trading/strategies/ema-crossover-adx-rsi.md v0.1."""
    from decimal import Decimal

    s = Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )
    assert s.strategy_ema_fast == 12
    assert s.strategy_ema_slow == 26
    assert s.strategy_adx_period == 14
    assert s.strategy_adx_threshold == Decimal("25")
    assert s.strategy_rsi_period == 14
    assert s.strategy_rsi_oversold == Decimal("30")
    assert s.strategy_rsi_overbought == Decimal("70")
    assert s.strategy_atr_period == 14
