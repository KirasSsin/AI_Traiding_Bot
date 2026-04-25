"""Tests для _cmd_wfa CLI subcommand (Sprint 11 P0)."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch


def test_cmd_wfa_invokes_walk_forward_runner_returns_zero_on_pass() -> None:
    """_cmd_wfa wires WindowSplitter + WalkForwardRunner + reporter. Exit 0 on pass."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__.WalkForwardRunner") as mock_runner_class, \
         patch("src.__main__.WindowSplitter"), \
         patch("src.__main__.format_wfa_report") as mock_reporter, \
         patch("src.__main__.evaluate_acceptance_gate") as mock_gate, \
         patch("src.__main__.run_replay"), \
         patch("src.__main__.sign_flip_p_value", return_value=0.03), \
         patch("src.__main__._load_ohlcv") as mock_loader, \
         patch("src.__main__.Settings") as mock_settings_class:

        mock_settings = MagicMock()
        mock_settings_class.return_value = mock_settings

        # Non-empty df с data
        mock_df = MagicMock()
        mock_df.empty = False
        mock_loader.return_value = mock_df

        mock_runner = MagicMock()
        # Provide non-empty oos_trades_df к trigger MC sign-flip path
        oos_df = MagicMock()
        oos_df.empty = False
        oos_df.__getitem__ = MagicMock(return_value=MagicMock(astype=MagicMock(return_value=MagicMock(to_numpy=MagicMock(return_value=[0.01, 0.02])))))
        mock_runner.run.return_value = {
            "folds": [{"oos_is_sharpe_ratio": 0.8}],
            "aggregate": {"oos_trades_df": oos_df, "k_folds": 5, "fold_oos_sharpes": [1.0]},
        }
        mock_runner_class.return_value = mock_runner

        mock_gate.return_value = {"passed": True}
        mock_reporter.return_value = {"acceptance_gate": {"passed": True}, "k_folds": 5, "mc_p_value": 0.03}

        exit_code = cli._cmd_wfa(args)
        assert exit_code == 0
        mock_runner.run.assert_called_once()


def test_cmd_wfa_returns_nonzero_on_gate_failure() -> None:
    """Gate fail → exit 2 (для CI integration)."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__.WalkForwardRunner") as mock_runner_class, \
         patch("src.__main__.WindowSplitter"), \
         patch("src.__main__.format_wfa_report") as mock_reporter, \
         patch("src.__main__.evaluate_acceptance_gate") as mock_gate, \
         patch("src.__main__.run_replay"), \
         patch("src.__main__.sign_flip_p_value", return_value=0.5), \
         patch("src.__main__._load_ohlcv") as mock_loader, \
         patch("src.__main__.Settings"):

        mock_df = MagicMock()
        mock_df.empty = False
        mock_loader.return_value = mock_df

        mock_runner = MagicMock()
        oos_df = MagicMock()
        oos_df.empty = False
        oos_df.__getitem__ = MagicMock(return_value=MagicMock(astype=MagicMock(return_value=MagicMock(to_numpy=MagicMock(return_value=[0.01])))))
        mock_runner.run.return_value = {
            "folds": [{"oos_is_sharpe_ratio": 0.5}],
            "aggregate": {"oos_trades_df": oos_df, "k_folds": 5, "fold_oos_sharpes": [0.5]},
        }
        mock_runner_class.return_value = mock_runner

        mock_gate.return_value = {"passed": False}
        mock_reporter.return_value = {"acceptance_gate": {"passed": False}, "k_folds": 5, "mc_p_value": 0.5}

        exit_code = cli._cmd_wfa(args)
        assert exit_code == 2


def test_cmd_wfa_returns_one_on_empty_data() -> None:
    """Empty OHLCV loader result → exit 1 (S12 will integrate real data path)."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__._load_ohlcv") as mock_loader, \
         patch("src.__main__.Settings"):

        mock_df = MagicMock()
        mock_df.empty = True
        mock_loader.return_value = mock_df

        exit_code = cli._cmd_wfa(args)
        assert exit_code == 1
