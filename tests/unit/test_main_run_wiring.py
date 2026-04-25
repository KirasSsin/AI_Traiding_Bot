"""Tests для _cmd_run DI wiring — Sprint 11 P0 (closes S8a T20 STUB).

Per pre-s11-backlog.md C1: architecture-reviewer mandatory post-impl.
"""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch


def _patch_settings_mock() -> MagicMock:
    """Build Settings mock с required fields for DI wiring.

    Note: Settings does NOT have trading_symbol / base_coin — symbol comes from
    CLI args (--symbol BTCUSDT default), base_coin is derived from symbol suffix
    (BTCUSDT → BTC, mirrors Reconciler._derive_base_coin convention).
    """
    s = MagicMock()
    s.bybit_api_key = "test_key_12345"
    s.bybit_api_secret = "test_secret_12345"
    s.testnet = True
    s.runtime_kill_switch_path = "/tmp/.kill_switch"
    s.db_path = "/tmp/test.db"
    return s


def test_cmd_run_wires_runtime_manager_returns_zero_on_clean_exit() -> None:
    """_cmd_run no longer returns 1 (STUB error). Wires RuntimeManager and runs."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    with patch("src.__main__.RuntimeManager") as mock_rm_class, \
         patch("src.__main__.Settings", return_value=_patch_settings_mock()), \
         patch("src.__main__.init_db"), \
         patch("src.__main__.connect"), \
         patch("src.__main__.BybitRESTClient"), \
         patch("src.__main__.BybitMarketAdapter"), \
         patch("src.__main__.BybitFilters"), \
         patch("src.__main__.Reconciler"), \
         patch("src.__main__.Coordinator"), \
         patch("src.__main__.ExecutionStateRepo"), \
         patch("src.__main__.BarSource"), \
         patch("src.__main__.EmaCrossoverAdxRsiStrategy"), \
         patch("src.__main__.RiskManager"), \
         patch("src.__main__.BybitPrivateWSConsumer"):

        mock_rm = MagicMock()
        mock_rm.run.return_value = None
        mock_rm_class.return_value = mock_rm

        exit_code = cli._cmd_run(args)
        assert exit_code == 0
        mock_rm.run.assert_called_once()


def test_cmd_run_propagates_keyboard_interrupt_returns_130() -> None:
    """Ctrl+C exits cleanly с code 130 (SIGINT convention)."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    with patch("src.__main__.RuntimeManager") as mock_rm_class, \
         patch("src.__main__.Settings", return_value=_patch_settings_mock()), \
         patch("src.__main__.init_db"), \
         patch("src.__main__.connect"), \
         patch("src.__main__.BybitRESTClient"), \
         patch("src.__main__.BybitMarketAdapter"), \
         patch("src.__main__.BybitFilters"), \
         patch("src.__main__.Reconciler"), \
         patch("src.__main__.Coordinator"), \
         patch("src.__main__.ExecutionStateRepo"), \
         patch("src.__main__.BarSource"), \
         patch("src.__main__.EmaCrossoverAdxRsiStrategy"), \
         patch("src.__main__.RiskManager"), \
         patch("src.__main__.BybitPrivateWSConsumer"):

        mock_rm = MagicMock()
        mock_rm.run.side_effect = KeyboardInterrupt()
        mock_rm_class.return_value = mock_rm

        exit_code = cli._cmd_run(args)
        assert exit_code == 130


def test_cmd_run_returns_one_on_runtime_crash() -> None:
    """Generic Exception during run() returns exit 1 (crash)."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    with patch("src.__main__.RuntimeManager") as mock_rm_class, \
         patch("src.__main__.Settings", return_value=_patch_settings_mock()), \
         patch("src.__main__.init_db"), \
         patch("src.__main__.connect"), \
         patch("src.__main__.BybitRESTClient"), \
         patch("src.__main__.BybitMarketAdapter"), \
         patch("src.__main__.BybitFilters"), \
         patch("src.__main__.Reconciler"), \
         patch("src.__main__.Coordinator"), \
         patch("src.__main__.ExecutionStateRepo"), \
         patch("src.__main__.BarSource"), \
         patch("src.__main__.EmaCrossoverAdxRsiStrategy"), \
         patch("src.__main__.RiskManager"), \
         patch("src.__main__.BybitPrivateWSConsumer"):

        mock_rm = MagicMock()
        mock_rm.run.side_effect = RuntimeError("simulated crash")
        mock_rm_class.return_value = mock_rm

        exit_code = cli._cmd_run(args)
        assert exit_code == 1
