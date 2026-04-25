"""Tests для _cmd_reconcile_only DI wiring (Sprint 11 P0)."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch


def _patch_settings_mock() -> MagicMock:
    s = MagicMock()
    s.bybit_api_key = "test_key_12345"
    s.bybit_api_secret = "test_secret_12345"
    s.testnet = True
    s.db_path = "/tmp/test.db"
    return s


def test_cmd_reconcile_only_invokes_bootstrap_then_exits() -> None:
    """_cmd_reconcile_only wires Coordinator.bootstrap then exits cleanly без main loop."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_reconcile_only)

    with patch("src.__main__.Coordinator") as mock_coord_class, \
         patch("src.__main__.Settings", return_value=_patch_settings_mock()), \
         patch("src.__main__.init_db"), \
         patch("src.__main__.connect"), \
         patch("src.__main__.BybitRESTClient"), \
         patch("src.__main__.BybitMarketAdapter"), \
         patch("src.__main__.Reconciler"), \
         patch("src.__main__.ExecutionStateRepo"):

        mock_coord = MagicMock()
        mock_coord_class.return_value = mock_coord

        exit_code = cli._cmd_reconcile_only(args)
        assert exit_code == 0
        mock_coord.bootstrap.assert_called_once()


def test_cmd_reconcile_only_returns_one_on_bootstrap_failure() -> None:
    """Bootstrap exception → exit 1 + stderr message."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_reconcile_only)

    with patch("src.__main__.Coordinator") as mock_coord_class, \
         patch("src.__main__.Settings", return_value=_patch_settings_mock()), \
         patch("src.__main__.init_db"), \
         patch("src.__main__.connect"), \
         patch("src.__main__.BybitRESTClient"), \
         patch("src.__main__.BybitMarketAdapter"), \
         patch("src.__main__.Reconciler"), \
         patch("src.__main__.ExecutionStateRepo"):

        mock_coord = MagicMock()
        mock_coord.bootstrap.side_effect = RuntimeError("simulated reconcile divergence")
        mock_coord_class.return_value = mock_coord

        exit_code = cli._cmd_reconcile_only(args)
        assert exit_code == 1
