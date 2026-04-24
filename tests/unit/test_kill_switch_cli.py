"""`python -m src kill` writes .kill_switch sentinel; `run` cleans stale.

ADR 0022 sub-decision 5.
"""
from __future__ import annotations


def test_cmd_kill_writes_sentinel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))

    from src.__main__ import main

    rc = main(["kill"])
    assert rc == 0
    assert (tmp_path / ".kill_switch").exists()


def test_cmd_kill_writes_to_configured_path(tmp_path, monkeypatch):
    custom = tmp_path / "subdir" / ".my_kill"
    custom.parent.mkdir(parents=True)
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_KILL_SWITCH_PATH", str(custom))

    from src.__main__ import main

    rc = main(["kill"])
    assert rc == 0
    assert custom.exists()
