from pathlib import Path

import pytest
from pydantic import ValidationError
from src.platform.config import Settings


def test_settings_loads_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_API_KEY", "test-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "test-secret")
    monkeypatch.setenv("BINANCE_ENV", "testnet")
    monkeypatch.setenv("TRADING_ENABLED", "false")
    monkeypatch.setenv("LIVE_TRADING", "false")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "oltp.db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "data" / "parquet"))

    s = Settings()

    assert s.binance_api_key == "test-key"
    assert s.binance_env == "testnet"
    assert s.trading_enabled is False
    assert s.live_trading is False
    assert isinstance(s.data_dir, Path)


def test_settings_invalid_env_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_API_SECRET", "s")
    monkeypatch.setenv("BINANCE_ENV", "invalid")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path))

    with pytest.raises(ValidationError):
        Settings()


def test_live_trading_requires_trading_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_API_SECRET", "s")
    monkeypatch.setenv("BINANCE_ENV", "testnet")
    monkeypatch.setenv("TRADING_ENABLED", "false")
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path))

    with pytest.raises(ValidationError, match="live_trading"):
        Settings()
