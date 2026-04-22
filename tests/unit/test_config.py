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


# ---------------------------------------------------------------------------
# Task 2 — Risk-module fields + config_hash()
# ---------------------------------------------------------------------------

_BASE = dict(
    data_dir="/tmp/data",
    log_dir="/tmp/logs",
    db_path="/tmp/data/bot.db",
    parquet_dir="/tmp/data/parquet",
)


def test_risk_fields_defaults() -> None:
    """All risk-module fields exist with correct default values (Task 2 locked design)."""
    from decimal import Decimal
    from pathlib import Path

    s = Settings(**_BASE)

    assert s.risk_max_position_pct_cap == Decimal("0.05")
    assert s.risk_sl_atr_multiplier == Decimal("1.5")
    assert s.risk_tp_atr_multiplier == Decimal("3.0")
    assert s.risk_cb_l1_dd == Decimal("0.15")
    assert s.risk_cb_l2_dd == Decimal("0.22")
    assert s.risk_cb_l3_dd == Decimal("0.30")
    assert s.risk_cb_flash_abs == Decimal("0.08")
    assert s.risk_cb_flash_atr_mult == Decimal("3.0")
    assert s.risk_kelly_phase1_cap == Decimal("0.01")
    assert s.risk_kelly_phase2_cap == Decimal("0.02")
    assert s.risk_kelly_phase3_cap == Decimal("0.03")
    assert s.risk_kelly_phase4_cap == Decimal("0.05")
    assert isinstance(s.risk_override_path, Path)


def test_config_hash_returns_64_char_hex() -> None:
    """config_hash() returns a 64-character hex string (SHA-256)."""
    s = Settings(**_BASE)
    h = s.config_hash()
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_config_hash_is_deterministic() -> None:
    """Same Settings instance produces the same hash on repeated calls."""
    s = Settings(**_BASE)
    assert s.config_hash() == s.config_hash()


def test_config_hash_same_for_equal_settings() -> None:
    """Two independently constructed Settings with identical values hash identically."""
    s1 = Settings(**_BASE)
    s2 = Settings(**_BASE)
    assert s1.config_hash() == s2.config_hash()


def test_config_hash_changes_on_risk_field_mutation() -> None:
    """Hash changes when any risk field is modified."""
    from decimal import Decimal

    s1 = Settings(**_BASE)
    s2 = Settings(**_BASE, risk_sl_atr_multiplier=Decimal("2.0"))
    assert s1.config_hash() != s2.config_hash()
