"""Tests для _cmd_monitor CLI subcommand (Sprint 11 A scope, read-only per C2)."""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_cmd_monitor_outputs_state_snapshot(tmp_path: Path, capsys) -> None:
    """_cmd_monitor reads current state + recent trades, prints JSON snapshot."""
    from src import __main__ as cli

    db_path = tmp_path / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE execution_state (
            symbol TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            halt_reason TEXT,
            last_reconcile_at TEXT,
            updated_at TEXT
        );
        INSERT INTO execution_state VALUES ('BTCUSDT', 'FLAT', NULL, '2026-04-25T11:59:00+00:00', '2026-04-25T12:00:00+00:00');
        CREATE TABLE trade_history (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, entry_signal_id TEXT, entry_ts TEXT, exit_ts TEXT,
            qty TEXT, entry_price TEXT, exit_price TEXT, pnl_quote TEXT,
            pnl_pct TEXT, fees_paid TEXT, reason_code TEXT,
            kelly_phase INTEGER, recorded_at TEXT
        );
    """)
    conn.commit()
    conn.close()

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_monitor)

    with patch("src.__main__.Settings") as mock_settings_class:
        mock_settings = MagicMock()
        mock_settings.db_path = db_path
        mock_settings_class.return_value = mock_settings

        exit_code = cli._cmd_monitor(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "BTCUSDT" in captured.out
        assert "FLAT" in captured.out


def test_cmd_monitor_does_not_write_to_db(tmp_path: Path) -> None:
    """C2 invariant: _cmd_monitor MUST NOT write к DB (WAL contention prevention)."""
    from src import __main__ as cli

    db_path = tmp_path / "readonly.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE execution_state (symbol TEXT PRIMARY KEY, state TEXT, halt_reason TEXT, last_reconcile_at TEXT, updated_at TEXT);
        CREATE TABLE trade_history (trade_id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, entry_signal_id TEXT, entry_ts TEXT, exit_ts TEXT, qty TEXT, entry_price TEXT, exit_price TEXT, pnl_quote TEXT, pnl_pct TEXT, fees_paid TEXT, reason_code TEXT, kelly_phase INTEGER, recorded_at TEXT);
        INSERT INTO execution_state VALUES ('BTCUSDT', 'FLAT', NULL, '2026-04-25T11:59:00+00:00', '2026-04-25T12:00:00+00:00');
    """)
    conn.commit()
    conn.close()

    mtime_before = os.path.getmtime(db_path)

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_monitor)

    with patch("src.__main__.Settings") as mock_settings_class:
        mock_settings = MagicMock()
        mock_settings.db_path = db_path
        mock_settings_class.return_value = mock_settings

        cli._cmd_monitor(args)

    mtime_after = os.path.getmtime(db_path)
    assert mtime_before == mtime_after  # No mtime change = no writes
