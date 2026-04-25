"""Tests for Settings (pydantic-settings v2) per ADR 0016 + 0018 sub-dec 9."""

import pytest
from pydantic import ValidationError
from src.platform.config import Settings

# Test fixtures — all required fields. Per ADR 0018 sub-decision 9 (Sprint 4
# security audit C1/CWE-798), Bybit credentials and the override HMAC key
# have NO defaults committed to git; tests must provide them explicitly.
_TEST_API_KEY = "test_api_key_value"
_TEST_API_SECRET = "test_api_secret_value"  # noqa: S105 — test fixture, not a real secret
_TEST_HMAC_KEY = "x" * 32  # 32 chars, satisfies min_length

_BASE = dict(
    data_dir="/tmp/data",
    log_dir="/tmp/logs",
    db_path="/tmp/data/bot.db",
    parquet_dir="/tmp/data/parquet",
    bybit_api_key=_TEST_API_KEY,
    bybit_api_secret=_TEST_API_SECRET,
    risk_override_hmac_key=_TEST_HMAC_KEY,
)


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bybit API key is REQUIRED — no committed default (audit C1, CWE-798)."""
    monkeypatch.delenv("BYBIT_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="bybit_api_key"):
        Settings(
            _env_file=None,
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            bybit_api_secret=_TEST_API_SECRET,
            risk_override_hmac_key=_TEST_HMAC_KEY,
        )


def test_missing_api_secret_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bybit API secret is REQUIRED — no committed default (audit C1, CWE-798)."""
    monkeypatch.delenv("BYBIT_API_SECRET", raising=False)
    with pytest.raises(ValidationError, match="bybit_api_secret"):
        Settings(
            _env_file=None,
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            bybit_api_key=_TEST_API_KEY,
            risk_override_hmac_key=_TEST_HMAC_KEY,
        )


def test_missing_hmac_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """risk_override_hmac_key is REQUIRED — separate from API secret (audit H2)."""
    monkeypatch.delenv("RISK_OVERRIDE_HMAC_KEY", raising=False)
    with pytest.raises(ValidationError, match="risk_override_hmac_key"):
        Settings(
            _env_file=None,
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            bybit_api_key=_TEST_API_KEY,
            bybit_api_secret=_TEST_API_SECRET,
        )


def test_short_hmac_key_raises() -> None:
    """HMAC key shorter than 32 chars rejected (entropy floor)."""
    with pytest.raises(ValidationError, match="risk_override_hmac_key"):
        Settings(**{**_BASE, "risk_override_hmac_key": "short"})


def test_explicit_creds_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit creds are accepted and stored verbatim."""
    # Isolate from .env pollution (operator demo validation may set TRADING_ENABLED=true).
    # pydantic-settings reads .env via env_file= config; pass _env_file=None to disable that source.
    monkeypatch.delenv("TRADING_ENABLED", raising=False)
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    s = Settings(_env_file=None, **_BASE)
    assert s.bybit_api_key == _TEST_API_KEY
    assert s.bybit_api_secret == _TEST_API_SECRET
    assert s.risk_override_hmac_key == _TEST_HMAC_KEY
    assert s.testnet is True
    assert s.trading_enabled is False
    assert s.live_trading is False


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env vars override constructor args."""
    monkeypatch.setenv("BYBIT_API_KEY", "override_key")
    monkeypatch.setenv("BYBIT_API_SECRET", "override_secret_value")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "y" * 32)
    monkeypatch.setenv("TESTNET", "false")
    monkeypatch.setenv("TRADING_ENABLED", "true")
    s = Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )
    assert s.bybit_api_key == "override_key"
    assert s.bybit_api_secret == "override_secret_value"
    assert s.testnet is False


def test_live_trading_requires_mainnet() -> None:
    """live_trading=True requires testnet=False (safety invariant)."""
    with pytest.raises(ValidationError, match="live_trading requires testnet=False"):
        Settings(**{**_BASE, "trading_enabled": True, "live_trading": True, "testnet": True})


def test_live_trading_requires_trading_enabled() -> None:
    """live_trading=True requires trading_enabled=True."""
    with pytest.raises(ValidationError, match="live_trading requires trading_enabled"):
        Settings(
            **{**_BASE, "trading_enabled": False, "live_trading": True, "testnet": False}
        )


def test_settings_strategy_params_defaults() -> None:
    """Strategy params defaults from trading/strategies/ema-crossover-adx-rsi.md v0.1."""
    from decimal import Decimal

    s = Settings(**_BASE)
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


# ---------------------------------------------------------------------------
# ADR 0018 sub-decision 9 — config_hash allowlist (audit H1 / CWE-532)
# ---------------------------------------------------------------------------


def test_config_hash_excludes_bybit_secret() -> None:
    """Rotating the API secret MUST NOT invalidate active risk overrides."""
    s1 = Settings(**_BASE)
    s2 = Settings(**{**_BASE, "bybit_api_secret": "completely_different_secret_value"})
    assert s1.config_hash() == s2.config_hash()


def test_config_hash_excludes_bybit_key() -> None:
    """Rotating the API key MUST NOT invalidate active risk overrides."""
    s1 = Settings(**_BASE)
    s2 = Settings(**{**_BASE, "bybit_api_key": "rotated_key_value"})
    assert s1.config_hash() == s2.config_hash()


def test_config_hash_excludes_hmac_key() -> None:
    """HMAC key is a separate secret — not part of risk-decision hash."""
    s1 = Settings(**_BASE)
    s2 = Settings(**{**_BASE, "risk_override_hmac_key": "z" * 64})
    assert s1.config_hash() == s2.config_hash()


def test_config_hash_excludes_paths_and_observability() -> None:
    """Path / log-level / sentry changes do not invalidate overrides."""
    s1 = Settings(**_BASE)
    s2 = Settings(
        **{**_BASE, "log_level": "DEBUG", "sentry_dsn": "https://example/1"}
    )
    assert s1.config_hash() == s2.config_hash()


# ---------------------------------------------------------------------------
# Sprint 7 — heal_max_age_seconds + require_mainnet_gate_passed (ADR 0021 sub-dec 4+8)
# ---------------------------------------------------------------------------


def test_settings_defaults_heal_and_mainnet_gate() -> None:
    """ADR 0021 sub-decisions 4+8 — defaults for HEAL staleness + mainnet gate."""
    s = Settings(**_BASE)
    assert s.heal_max_age_seconds == 3600  # 1 bar period (v0.1 strategy = 1H)
    assert s.require_mainnet_gate_passed is True


def test_settings_heal_overridable_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """heal_max_age_seconds is env-overridable."""
    monkeypatch.setenv("HEAL_MAX_AGE_SECONDS", "1800")
    s = Settings(**_BASE)
    assert s.heal_max_age_seconds == 1800
