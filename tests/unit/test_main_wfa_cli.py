"""Tests для _cmd_wfa CLI subcommand (Sprint 11 P0)."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest


def test_cmd_wfa_invokes_walk_forward_runner_returns_zero_on_pass() -> None:
    """_cmd_wfa wires WindowSplitter + WalkForwardRunner + reporter. Exit 0 on pass."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT",
        start="2024-01-01",
        end="2024-04-01",
        func=cli._cmd_wfa,
    )

    with (
        patch("src.backtest.data_loading.WalkForwardRunner") as mock_runner_class,
        patch("src.backtest.data_loading.WindowSplitter"),
        patch("src.__main__.format_wfa_report"),
        patch("src.__main__.evaluate_acceptance_gate") as mock_gate,
        patch("src.backtest.data_loading.run_replay"),
        patch("src.backtest.data_loading.sign_flip_p_value", return_value=0.03),
        patch("src.__main__._load_ohlcv") as mock_loader,
        patch("src.backtest.data_loading.extract_trade_records", return_value=[]),
        patch("src.__main__.compute_dsr", return_value=0.75) as mock_dsr,
        patch("src.__main__.compute_t1_t6_metrics") as mock_metrics,
        patch("src.__main__.Settings") as mock_settings_class,
    ):
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
        oos_df.__getitem__ = MagicMock(
            return_value=MagicMock(
                astype=MagicMock(
                    return_value=MagicMock(to_numpy=MagicMock(return_value=[0.01, 0.02]))
                )
            )
        )
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
        symbol="BTCUSDT",
        start="2024-01-01",
        end="2024-04-01",
        func=cli._cmd_wfa,
    )

    with (
        patch("src.backtest.data_loading.WalkForwardRunner") as mock_runner_class,
        patch("src.backtest.data_loading.WindowSplitter"),
        patch("src.__main__.format_wfa_report"),
        patch("src.__main__.evaluate_acceptance_gate") as mock_gate,
        patch("src.backtest.data_loading.run_replay"),
        patch("src.backtest.data_loading.sign_flip_p_value", return_value=0.5),
        patch("src.__main__._load_ohlcv") as mock_loader,
        patch("src.backtest.data_loading.extract_trade_records", return_value=[]),
        patch("src.__main__.compute_dsr", return_value=float("nan")),
        patch("src.__main__.compute_t1_t6_metrics") as mock_metrics,
        patch("src.__main__.Settings"),
    ):
        mock_df = MagicMock()
        mock_df.empty = False
        mock_loader.return_value = mock_df

        mock_runner = MagicMock()
        oos_df = MagicMock()
        oos_df.empty = False
        oos_df.__getitem__ = MagicMock(
            return_value=MagicMock(
                astype=MagicMock(return_value=MagicMock(to_numpy=MagicMock(return_value=[0.01])))
            )
        )
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


def test_cmd_wfa_dsr_sigma_uses_real_annualized_oos_sharpes_not_ratios(tmp_path, monkeypatch):
    """S55 QS-2 (ADR 0071): _cmd_wfa DSR sigma_SR must come from REAL annualized OOS
    Sharpes (aggregate.fold_oos_sharpes), de-annualized via annualization_factor and
    namespaced strategy_class — NOT from OOS/IS ratios on the GLOBAL cross-trial pool.

    RED before fix: persisted aggregate = mean of OOS/IS ratios (0.85) under
    strategy_class "unknown", and compute_dsr called WITHOUT annualization_factor.
    """
    import json
    import math

    from src import __main__ as cli

    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    log_path = data_dir / "cross_trial_sharpes.json"
    # _cmd_wfa resolves the pool via default_pool_path() (env-redirectable); point it
    # at this test's seeded log so the persisted-trial assertions below observe it
    # (overrides the autouse _isolate_cross_trial_pool tmp default).
    monkeypatch.setenv("CROSS_TRIAL_LOG_PATH", str(log_path))
    # Seed 2 prior within-class ("wfa_meanrev") REAL OOS Sharpes so the candidate (3rd)
    # yields an admissible within-class sigma_SR (ADR 0056 N>=3 hierarchy).
    log_path.write_text(
        json.dumps(
            {
                "trials": [
                    {
                        "sprint": 11,
                        "symbol": "S1",
                        "strategy_class": "wfa_meanrev",
                        "oos_sharpe": 12.0,
                    },
                    {
                        "sprint": 12,
                        "symbol": "S2",
                        "strategy_class": "wfa_meanrev",
                        "oos_sharpe": -8.0,
                    },
                ]
            }
        )
    )

    args = argparse.Namespace(
        symbol="BTCUSDT",
        symbols=None,
        start="2024-01-01",
        end="2024-04-01",
        interval="60",
        func=cli._cmd_wfa,
    )

    # Real annualized OOS Sharpes (magnitude ~ O(10)) differ markedly from the OOS/IS
    # ratios — proving the DSR sigma_SR consumes the former, the gate/T6 the latter.
    runner_result = {
        "aggregate": {"fold_oos_sharpes": [30.0, -40.0], "oos_trades_df": None, "k_folds": 2},
        "folds": [],
    }
    fold_ratios = [0.8, 0.9]  # OOS/IS ratios — acceptance-gate + T6 input only
    fake_trades = [object(), object()]  # non-empty → cross-trial append fires

    captured: dict = {}

    def _capture_dsr(*_a, **k):
        captured.update(k)
        return 0.9

    with (
        patch(
            "src.__main__._run_wfa_single_symbol",
            return_value=(fake_trades, fold_ratios, runner_result, 0.03),
        ),
        patch("src.__main__._load_ohlcv") as mock_loader,
        patch("src.__main__.compute_dsr", side_effect=_capture_dsr),
        patch("src.__main__.compute_t1_t6_metrics") as mock_metrics,
        patch("src.__main__.evaluate_acceptance_gate", return_value={"failed_criteria": []}),
        patch("src.__main__.Settings"),
        patch.dict("os.environ", {"SPRINT_N": "55"}),
    ):
        mock_df = MagicMock()
        mock_df.empty = False
        mock_loader.return_value = mock_df
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
        cli._cmd_wfa(args)

    # (1) De-annualization factor passed and interval-derived (sqrt(bars_per_year=8760)).
    assert captured.get("annualization_factor") == pytest.approx(math.sqrt(8760))
    # (2) sigma_SR built from REAL OOS Sharpes (class pool [12, -8, mean(30,-40)=-5] → O(10)),
    #     NOT stdev of OOS/IS ratios (~O(0.1)).
    assert captured.get("sigma_sr") is not None
    assert captured["sigma_sr"] > 1.0
    # (3) Persisted trial = REAL aggregate (-5.0) under namespaced class, NOT ratio
    #     (0.85) under "unknown".
    persisted = json.loads(log_path.read_text())["trials"]
    new_entry = [e for e in persisted if e["sprint"] == 55]
    assert len(new_entry) == 1
    assert new_entry[0]["oos_sharpe"] == pytest.approx(-5.0)
    assert new_entry[0]["strategy_class"] == "wfa_meanrev"


def test_cmd_wfa_returns_one_on_empty_data() -> None:
    """Empty OHLCV loader result → exit 1 (S12 will integrate real data path)."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT",
        start="2024-01-01",
        end="2024-04-01",
        func=cli._cmd_wfa,
    )

    with patch("src.__main__._load_ohlcv") as mock_loader, patch("src.__main__.Settings"):
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

    fake_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h"),
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [99, 100, 101],
            "close": [103, 104, 105],
            "volume": [1.0, 2.0, 3.0],
        }
    )

    parquet_file = tmp_path / "BTCUSDT_1h.parquet"
    fake_df.to_parquet(parquet_file)

    # Patch data_collector module load_market_data
    with patch("src.backtest.data_loading.load_market_data") as mock_loader:  # noqa: SIM117
        mock_loader.return_value = fake_df
        result = cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-02")

    assert not result.empty
    mock_loader.assert_called_once()
    config_arg = mock_loader.call_args[0][0]
    assert config_arg["data"]["source"] == "parquet"
    assert config_arg["data"]["start_date"] == "2024-01-01"
    assert config_arg["data"]["end_date"] == "2024-01-02"


def test_load_ohlcv_raises_helpful_error_when_parquet_missing():
    """T2 — Parquet missing → FileNotFoundError с operator-friendly message."""
    from src import __main__ as cli

    with (
        patch(
            "src.backtest.data_loading.load_market_data",
            side_effect=FileNotFoundError("no such file"),
        ),
        pytest.raises(FileNotFoundError, match="python -m src backfill"),
    ):
        cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-02")


@pytest.mark.parametrize(
    "symbol",
    [
        "../../../etc/passwd",  # classic path traversal
        "BTC/../../",  # slash traversal
        "BTCUSDT\n/evil",  # trailing-newline bypass (defeats ^...$ but not \A...\Z)
        "BTCUSDT/evil",  # embedded slash
        "BTCUSDT.parquet",  # dot escapes allowlist
        "btcusdt",  # lowercase bypass attempt
        "",  # empty
        "A" * 21,  # too long
    ],
)
def test_load_ohlcv_rejects_traversal_symbol_before_path_access(symbol):
    """SEC-S55-01 — _load_ohlcv anchored allowlist gate (defense-in-depth).

    _load_ohlcv is reachable from the CLI too (not only /api/backtest), so the
    symbol→parquet-path f-string is guarded here with the SAME anchored regex
    (\\A[A-Z0-9]{1,20}\\Z). Reject BEFORE load_market_data is ever called.
    """
    from src import __main__ as cli

    with patch("src.backtest.data_loading.load_market_data") as mock_loader:
        with pytest.raises(ValueError):
            cli._load_ohlcv(symbol=symbol, start="2024-01-01", end="2024-01-02")
        mock_loader.assert_not_called()


@pytest.mark.parametrize("symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
def test_load_ohlcv_accepts_valid_symbol(symbol):
    """SEC-S55-01 — valid symbols pass the allowlist gate (no false positive)."""
    import pandas as pd
    from src import __main__ as cli

    fake_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h"),
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [99, 100, 101],
            "close": [103, 104, 105],
            "volume": [1.0, 2.0, 3.0],
        }
    )
    with patch("src.backtest.data_loading.load_market_data", return_value=fake_df):
        result = cli._load_ohlcv(symbol=symbol, start="2024-01-01", end="2024-01-02")
    assert not result.empty
