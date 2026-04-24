"""`python -m src kill` writes .kill_switch sentinel; `run` cleans stale.

ADR 0022 sub-decision 5.
"""
from __future__ import annotations

import os

import pytest


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


def test_cmd_kill_atomic_no_partial_on_simulated_error(tmp_path, monkeypatch):
    """If write raises mid-call, sentinel file must NOT exist (no partial-write).

    Atomicity contract: os.replace is the commit point. If the write to tmp
    file raises, sentinel must not be created at the final path.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))

    real_replace = os.replace

    def _boom(_src, _dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr("src.__main__.os.replace", _boom)

    from src.__main__ import main

    with pytest.raises(OSError, match="simulated rename failure"):
        main(["kill"])

    sentinel = tmp_path / ".kill_switch"
    assert not sentinel.exists(), "sentinel must NOT exist when atomic rename fails"
    # tmp file MUST be cleaned up even on failure
    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    assert not tmp.exists(), "tmp file must be cleaned up in finally"

    # restore — not strictly needed under monkeypatch, but explicit
    monkeypatch.setattr("src.__main__.os.replace", real_replace)


def test_cmd_kill_uses_atomic_write(tmp_path, monkeypatch):
    """Happy path: sentinel exists with empty content, no leftover .tmp file."""
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

    sentinel = tmp_path / ".kill_switch"
    assert sentinel.exists()
    assert sentinel.read_bytes() == b""

    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    assert not tmp.exists(), "tmp file must not linger after successful os.replace"
