"""Tests для _cmd_wfa CLI subcommand (Sprint 11 P0)."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest


def test_cmd_wfa_invokes_walk_forward_runner_returns_zero_on_pass() -> None:
    """_cmd_wfa wires WindowSplitter + WalkForwardRunner + reporter. Exit 0 on pass."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__.WalkForwardRunner") as mock_runner_class, \
         patch("src.__main__.WindowSplitter"), \
         patch("src.__main__.format_wfa_report"), \
         patch("src.__main__.evaluate_acceptance_gate") as mock_gate, \
         patch("src.__main__.run_replay"), \
         patch("src.__main__.sign_flip_p_value", return_value=0.03), \
         patch("src.__main__._load_ohlcv") as mock_loader, \
         patch("src.__main__.extract_trade_records", return_value=[]), \
         patch("src.__main__.compute_dsr", return_value=0.75) as mock_dsr, \
         patch("src.__main__.compute_t1_t6_metrics") as mock_metrics, \
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
            "folds": [{"oos_is_sharpe_ratio": 0.8, "oos_trades_df": None}],
            "aggregate": {"oos_trades_df": oos_df, "k_folds": 5, "fold_oos_sharpes": [1.0]},
        }
        mock_runner_class.return_value = mock_runner

        mock_gate.return_value = {"passed": True}
        # All T1-T6 criteria pass → verdict = PASS
        mock_metrics.return_value = {
            "t1_sharpe_oos": 1.2,
            "t2_sortino_oos": 1.8,
            "t3_max_drawdown": 0.15,
            "t4_win_rate": 0.50,
            "t4_avg_rr": 1.8,
            "t5_mean_pnl_pct": 0.01,
            "t5_t_stat": 2.5,
            "t5_n_trades": 150,
            "t6_oos_is_sharpe_ratio_mean": 0.8,
        }

        exit_code = cli._cmd_wfa(args)
        assert exit_code == 0
        mock_runner.run.assert_called_once()
        mock_dsr.assert_called_once()


def test_cmd_wfa_returns_nonzero_on_gate_failure() -> None:
    """Metrics fail → exit 2 (per Q7 ESC-1=c defer pattern)."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__.WalkForwardRunner") as mock_runner_class, \
         patch("src.__main__.WindowSplitter"), \
         patch("src.__main__.format_wfa_report"), \
         patch("src.__main__.evaluate_acceptance_gate") as mock_gate, \
         patch("src.__main__.run_replay"), \
         patch("src.__main__.sign_flip_p_value", return_value=0.5), \
         patch("src.__main__._load_ohlcv") as mock_loader, \
         patch("src.__main__.extract_trade_records", return_value=[]), \
         patch("src.__main__.compute_dsr", return_value=float("nan")), \
         patch("src.__main__.compute_t1_t6_metrics") as mock_metrics, \
         patch("src.__main__.Settings"):

        mock_df = MagicMock()
        mock_df.empty = False
        mock_loader.return_value = mock_df

        mock_runner = MagicMock()
        oos_df = MagicMock()
        oos_df.empty = False
        oos_df.__getitem__ = MagicMock(return_value=MagicMock(astype=MagicMock(return_value=MagicMock(to_numpy=MagicMock(return_value=[0.01])))))
        mock_runner.run.return_value = {
            "folds": [{"oos_is_sharpe_ratio": 0.5, "oos_trades_df": None}],
            "aggregate": {"oos_trades_df": oos_df, "k_folds": 5, "fold_oos_sharpes": [0.5]},
        }
        mock_runner_class.return_value = mock_runner

        mock_gate.return_value = {"passed": False}
        # T1 fails (< 1.0) → verdict = FAIL
        mock_metrics.return_value = {
            "t1_sharpe_oos": 0.5,
            "t2_sortino_oos": float("nan"),
            "t3_max_drawdown": 0.30,
            "t4_win_rate": 0.40,
            "t4_avg_rr": float("nan"),
            "t5_mean_pnl_pct": float("nan"),
            "t5_t_stat": float("nan"),
            "t5_n_trades": 50,
            "t6_oos_is_sharpe_ratio_mean": 0.5,
        }

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


def test_resolve_symbols_uses_symbols_when_set() -> None:
    """S15 ADR 0030: --symbols overrides --symbol."""
    import argparse
    from src.__main__ import _resolve_symbols
    args = argparse.Namespace(symbol="BTCUSDT", symbols="BTCUSDT,ETHUSDT,SOLUSDT")
    assert _resolve_symbols(args) == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_resolve_symbols_falls_back_to_symbol_when_no_symbols() -> None:
    """Backward-compat: --symbols not set → use single --symbol."""
    import argparse
    from src.__main__ import _resolve_symbols
    args = argparse.Namespace(symbol="ETHUSDT", symbols=None)
    assert _resolve_symbols(args) == ["ETHUSDT"]


def test_resolve_symbols_default_btcusdt_when_neither_set() -> None:
    """No --symbols, no --symbol → default BTCUSDT."""
    import argparse
    from src.__main__ import _resolve_symbols
    args = argparse.Namespace()
    assert _resolve_symbols(args) == ["BTCUSDT"]


def test_resolve_symbols_strips_whitespace_and_uppercases() -> None:
    """Whitespace tolerated, case normalized."""
    import argparse
    from src.__main__ import _resolve_symbols
    args = argparse.Namespace(symbol=None, symbols=" btcusdt , ethusdt , solusdt ")
    assert _resolve_symbols(args) == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_load_ohlcv_calls_data_collector_with_config_dict(tmp_path):
    """T2 — _load_ohlcv translates CLI args → data_collector config dict."""
    import pandas as pd
    from src import __main__ as cli

    fake_df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h"),
        "open": [100, 101, 102], "high": [105, 106, 107],
        "low": [99, 100, 101], "close": [103, 104, 105],
        "volume": [1.0, 2.0, 3.0],
    })

    parquet_file = tmp_path / "BTCUSDT_1h.parquet"
    fake_df.to_parquet(parquet_file)

    # Patch data_collector module load_market_data
    with patch("src.__main__.load_market_data") as mock_loader:  # noqa: SIM117
        mock_loader.return_value = fake_df
        result = cli._load_ohlcv(
            symbol="BTCUSDT", start="2024-01-01", end="2024-01-02"
        )

    assert not result.empty
    mock_loader.assert_called_once()
    config_arg = mock_loader.call_args[0][0]
    assert config_arg["data"]["source"] == "parquet"
    assert config_arg["data"]["start_date"] == "2024-01-01"
    assert config_arg["data"]["end_date"] == "2024-01-02"


def test_load_ohlcv_raises_helpful_error_when_parquet_missing():
    """T2 — Parquet missing → FileNotFoundError с operator-friendly message."""
    from src import __main__ as cli

    with patch("src.__main__.load_market_data", side_effect=FileNotFoundError("no such file")), \
         pytest.raises(FileNotFoundError, match="python -m src backfill"):
        cli._load_ohlcv(
            symbol="BTCUSDT", start="2024-01-01", end="2024-01-02"
        )
