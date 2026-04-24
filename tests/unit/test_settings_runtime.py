"""Sprint 8a runtime settings — defaults, env override, validator boundaries.

ADR 0022 sub-decisions 11 (5 new fields) + 3 (stall threshold validator).
"""
from __future__ import annotations

import pytest


def test_settings_runtime_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    from src.platform.config import Settings

    s = Settings()
    assert s.runtime_bar_poll_cadence_seconds == 5.0
    assert s.runtime_bar_poll_stall_threshold == 24
    assert s.runtime_kill_switch_path == ".kill_switch"
    assert s.runtime_ws_check_alive_max_silence == 30.0
    assert s.runtime_warmup_bars == 50


def test_settings_runtime_stall_threshold_validator_low(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_BAR_POLL_STALL_THRESHOLD", "5")
    from src.platform.config import Settings

    with pytest.raises(ValueError, match="6 ≤ N ≤ 720"):
        Settings()


def test_settings_runtime_stall_threshold_validator_high(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_BAR_POLL_STALL_THRESHOLD", "721")
    from src.platform.config import Settings

    with pytest.raises(ValueError, match="6 ≤ N ≤ 720"):
        Settings()


def test_settings_runtime_stall_threshold_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_BAR_POLL_STALL_THRESHOLD", "120")
    from src.platform.config import Settings

    s = Settings()
    assert s.runtime_bar_poll_stall_threshold == 120
