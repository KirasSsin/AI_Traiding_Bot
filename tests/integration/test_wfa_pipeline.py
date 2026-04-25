"""End-to-end WFA pipeline integration test.

Sprint 10 — verifies full pipeline:
synthetic OHLCV → run_replay per fold → WindowSplitter → WalkForwardRunner →
DSR aggregate → MC sign-flip → acceptance gate → reporter.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.replay_engine import run_replay
from src.backtest.walk_forward import (
    WalkForwardRunner,
    WindowSplitter,
    evaluate_acceptance_gate,
)
from src.backtest.wfa_reporter import format_wfa_report
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


pytestmark = pytest.mark.integration


def _synthetic_df(n_bars: int = 5500) -> pd.DataFrame:
    """Synthetic 1H OHLCV — mild positive trend для realistic strategy edge."""
    rng = np.random.default_rng(42)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.005, n_bars)))
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": closes * 0.999,
        "high": closes * 1.001,
        "low": closes * 0.998,
        "close": closes,
        "volume": np.ones(n_bars),
    })


def _trades_df_to_traderecords(trades_df: pd.DataFrame) -> list[TradeRecord]:
    """Convert replay_engine trades_df DataFrame к TradeRecord list для DSR."""
    records: list[TradeRecord] = []
    for _, row in trades_df.iterrows():
        entry_price = Decimal(str(row["entry_price"]))
        exit_price = Decimal(str(row["exit_price"]))
        pnl_pct_val = (exit_price / entry_price) - Decimal("1")
        entry_ts = pd.Timestamp(row["timestamp_open"]).to_pydatetime()
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.replace(tzinfo=UTC)
        exit_ts = pd.Timestamp(row["timestamp_close"]).to_pydatetime()
        if exit_ts.tzinfo is None:
            exit_ts = exit_ts.replace(tzinfo=UTC)
        records.append(TradeRecord(
            symbol="BTCUSDT",
            entry_signal_id=uuid4(),
            entry_ts=entry_ts,
            exit_ts=exit_ts,
            qty=Decimal(str(row["qty"])),
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_quote=Decimal(str(row["net_pnl"])),
            pnl_pct=pnl_pct_val,
            fees_paid=Decimal(str(row["entry_fee"] + row["exit_fee"])),
            reason_code=ReasonCode.EXIT_TP_HIT,
            kelly_phase=1,
            recorded_at=datetime.now(UTC),
        ))
    return records


def test_full_wfa_pipeline_produces_complete_report() -> None:
    """End-to-end: synthetic data → replay × K folds → WFA → MC → DSR → gate → report."""
    df = _synthetic_df(n_bars=5500)
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.001,
            "slippage": 0.0005,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 50.0,
            "long_only": True,
        },
        "strategy": {"indicators": {"atr": {"sl_atr_mult": 1.5, "tp_atr_mult": 3.0}}},
    }

    splitter = WindowSplitter()  # ADR 0014 defaults
    runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
    runner_result = runner.run(df=df, config=config)

    oos_trades_df = runner_result["aggregate"]["oos_trades_df"]
    trades_for_dsr = _trades_df_to_traderecords(oos_trades_df) if not oos_trades_df.empty else []

    if oos_trades_df.empty:
        mc_p = math.nan
    else:
        returns_arr = (oos_trades_df["net_pnl"].astype(float).to_numpy() / 10000.0)
        mc_p = sign_flip_p_value(returns_arr, n_iterations=500, seed=42)

    fold_ratios = [f["oos_is_sharpe_ratio"] for f in runner_result["folds"]]
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_ratios,
        mc_p_value=mc_p if not math.isnan(mc_p) else 1.0,
    )

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=mc_p,
        gate_result=gate,
    )

    assert "bar_returns_sharpe_per_fold" in report
    assert "per_trade_sharpe" in report
    assert "display_sharpe" in report
    assert "dsr_aggregate" in report
    assert "mc_p_value" in report
    assert "acceptance_gate" in report
    assert "k_folds" in report
    assert report["k_folds"] == 5
    assert len(report["bar_returns_sharpe_per_fold"]) == 5
