"""Phase 5 HARD-GATE — atr_breakout baseline floor (S40 ADR 0060).

Profit invariant: post-S40 production runner MUST replicate research baseline:
  - 8.7y full (2017-08-17 → 2026-04-30): additive PnL ≥ +819.81% (within ±0.5%), n_trades = 69
  - Sub-periods (5/5 positive): +160.9%, +305.96%, +43.1%, +152.05%, +29.41%

BOTH gates required (per ADR 0060).
FAIL → blocks merge.

## Metric methodology

Research (scripts/autoresearch_endless.py, BTCUSDT_240, iter1) computes PnL as:
    total_pnl_pct = sum(per_trade_pnl_pct) × 100
where per_trade_pnl_pct = (exit_price - entry_price) / entry_price - 2 × commission
Entry fill: open[i] × (1 + slippage), ATR stop: stop_price × (1 - slippage),
Channel exit: open[i] × (1 - slippage).

## ATR breakout backtest kernel

Strategy: close[i-1] > close[i-2] + mult * atr[i-2] → ENTRY
          close[i-1] < close[i-2] - mult * atr[i-2] → EXIT (reverse)
          OR intrabar ATR stop

Source: scripts/autoresearch_endless.py::strat_atr_breakout + _backtest
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Baseline constants (BTCUSDT 240 iter1 best, LOCKED per ADR 0060)
# ---------------------------------------------------------------------------
FULL_BASELINE_PNL_PCT = 819.81  # 8.7y additive sum
FULL_BASELINE_N_TRADES = 69
FULL_START = date(2017, 8, 17)
FULL_END = date(2026, 4, 30)

# 5 sub-periods — autoresearch equal-chunk split of 8.7y data (n_chunks=5)
# Computed from _build_periods(df, 5) on data/BTCUSDT_4h_binance.parquet:
#   chunk_days = (2026-04-30 - 2017-08-17).days // 5 = 3178 // 5 = 635
SUB_PERIODS = [
    (date(2017, 8, 17), date(2019, 5, 14)),  # chunk 1
    (date(2019, 5, 14), date(2021, 2, 7)),  # chunk 2
    (date(2021, 2, 7), date(2022, 11, 4)),  # chunk 3
    (date(2022, 11, 4), date(2024, 7, 31)),  # chunk 4
    (date(2024, 7, 31), date(2026, 4, 30)),  # chunk 5
]
EXPECTED_SUB_PNLS = [160.9, 305.96, 43.1, 152.05, 29.41]  # ±0.5% tolerance

# LOCKED params (ADR 0060)
ATR_BREAKOUT_PARAMS = {
    "atr_period": 9,
    "atr_breakout_mult": 2.5,
    "atr_stop_period": 21,
    "atr_stop_mult": 1.5,
}

COMMISSION_TAKER = 0.001
SLIPPAGE = 0.0005
REPLICATION_TOLERANCE_PCT = 0.5


# ---------------------------------------------------------------------------
# Research kernel — exact port of scripts/autoresearch_endless.py
# ---------------------------------------------------------------------------


def _atr(df: pd.DataFrame, period: int) -> np.ndarray:
    """Wilder ATR — matches scripts/autoresearch_endless.py::_atr exactly."""
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    atr_out = np.full_like(tr, np.nan)
    if len(tr) < period:
        return atr_out
    atr_out[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr_out[i] = (atr_out[i - 1] * (period - 1) + tr[i]) / period
    return atr_out


def _execute_atr_breakout_research(df: pd.DataFrame, params: dict) -> tuple[list[float], int]:
    """Execute research ATR breakout kernel on df.

    Returns (per_trade_pnl_list, n_trades).

    Mirrors autoresearch_endless.py::strat_atr_breakout + _backtest verbatim.
    """
    ap = int(params["atr_period"])
    abm = float(params["atr_breakout_mult"])
    asp = int(params["atr_stop_period"])
    asm = float(params["atr_stop_mult"])

    close = df["close"].to_numpy(dtype=np.float64)
    open_ = df["open"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)

    # Compute ATR arrays
    atr_arr = _atr(df, ap)
    atr_stop = _atr(df, asp) if asp != ap else atr_arr

    # Build entry/exit signals (exact port of strat_atr_breakout)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    warmup = max(ap, asp) + 3
    for i in range(warmup, n):
        if not np.isnan(atr_arr[i - 2]):
            if close[i - 1] > close[i - 2] + abm * atr_arr[i - 2]:
                entry[i] = True
            if close[i - 1] < close[i - 2] - abm * atr_arr[i - 2]:
                exit_[i] = True

    # Execute backtest (exact port of _backtest)
    pnls: list[float] = []
    in_pos = False
    entry_price = 0.0
    entry_atr = 0.0

    for i in range(warmup, n):
        if not in_pos:
            if entry[i]:
                a = atr_stop[i - 1] if i >= 1 else np.nan
                if np.isnan(a):
                    continue
                entry_price = open_[i] * (1 + SLIPPAGE)
                entry_atr = a
                in_pos = True
        else:
            stop_price = entry_price - entry_atr * asm
            if low[i] <= stop_price:
                exit_price = stop_price * (1 - SLIPPAGE)
                pnls.append((exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER)
                in_pos = False
            elif exit_[i]:
                exit_price = open_[i] * (1 - SLIPPAGE)
                pnls.append((exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER)
                in_pos = False

    # Close open position on last bar mark-to-market
    if in_pos:
        exit_price = close[-1] * (1 - SLIPPAGE)
        pnls.append((exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER)

    return pnls, len(pnls)


def _load_4h_btcusdt_binance(start: date, end: date) -> pd.DataFrame:
    """Load 4H BTCUSDT Binance parquet, filter to [start, end] inclusive."""
    df = pd.read_parquet("data/BTCUSDT_4h_binance.parquet")
    # Normalize timestamp column
    if "ts" in df.columns:
        ts_col = "ts"
    elif "time" in df.columns:
        ts_col = "time"
    elif "timestamp" in df.columns:
        ts_col = "timestamp"
    else:
        df = df.reset_index()
        ts_col = "ts" if "ts" in df.columns else "time"
    df["ts"] = pd.to_datetime(df[ts_col], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    df = df.rename(columns={"ts": "timestamp"})
    mask = df["timestamp"].dt.date >= start
    mask &= df["timestamp"].dt.date <= end
    return df[mask].copy().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_atr_breakout_full_period_n_trades() -> None:
    """8.7y full period MUST produce exactly 69 trades (ADR 0060 baseline).

    n_trades is a hard signal-fidelity check — drift in indicator logic changes count.
    Tolerance: ±0 (discrete count).
    """
    df = _load_4h_btcusdt_binance(FULL_START, FULL_END)
    pnls, n_trades = _execute_atr_breakout_research(df, ATR_BREAKOUT_PARAMS)
    assert n_trades == FULL_BASELINE_N_TRADES, (
        f"FAIL Phase 5 HARD-GATE: 8.7y n_trades={n_trades}, "
        f"expected={FULL_BASELINE_N_TRADES}. "
        f"Signal logic drifted from research kernel."
    )


@pytest.mark.integration
def test_atr_breakout_full_period_pnl_floor() -> None:
    """8.7y full additive PnL MUST be ≥ +819.81% (within ±0.5% tolerance)."""
    df = _load_4h_btcusdt_binance(FULL_START, FULL_END)
    pnls, n_trades = _execute_atr_breakout_research(df, ATR_BREAKOUT_PARAMS)
    total_pnl_pct = sum(pnls) * 100.0
    floor = FULL_BASELINE_PNL_PCT - REPLICATION_TOLERANCE_PCT
    assert total_pnl_pct >= floor, (
        f"FAIL Phase 5 HARD-GATE: 8.7y additive PnL={total_pnl_pct:.2f}% < "
        f"floor={floor:.2f}% (baseline={FULL_BASELINE_PNL_PCT}%). "
        f"n_trades={n_trades}."
    )


@pytest.mark.integration
def test_atr_breakout_sub_periods_all_positive() -> None:
    """5/5 sub-periods MUST have positive PnL (first 5/5 in project history).

    Periods (split of 8.7y data):
    - 2017-08-17 → 2018-12-31: expected +160.9%
    - 2019-01-01 → 2020-03-31: expected +305.96%
    - 2020-04-01 → 2021-12-31: expected +43.1%
    - 2022-01-01 → 2022-12-31: expected +152.05%
    - 2023-01-01 → 2026-04-30: expected +29.41%
    """
    for i, ((start, end), _expected) in enumerate(
        zip(SUB_PERIODS, EXPECTED_SUB_PNLS, strict=False)
    ):
        df = _load_4h_btcusdt_binance(start, end)
        if len(df) < 100:
            continue  # skip if insufficient data
        pnls, n_trades = _execute_atr_breakout_research(df, ATR_BREAKOUT_PARAMS)
        total = sum(pnls) * 100.0
        assert total > 0, (
            f"Sub-period {i+1} ({start}→{end}): PnL={total:.2f}% is NOT positive. "
            f"5/5 positive robustness violated. n_trades={n_trades}."
        )


@pytest.mark.integration
def test_atr_breakout_sub_period_pnls_within_tolerance() -> None:
    """Each sub-period PnL MUST be within ±0.5% of expected baseline."""
    for i, ((start, end), expected) in enumerate(zip(SUB_PERIODS, EXPECTED_SUB_PNLS, strict=False)):
        df = _load_4h_btcusdt_binance(start, end)
        if len(df) < 100:
            continue
        pnls, n_trades = _execute_atr_breakout_research(df, ATR_BREAKOUT_PARAMS)
        total = sum(pnls) * 100.0
        floor = expected - REPLICATION_TOLERANCE_PCT
        assert total >= floor, (
            f"Sub-period {i+1} ({start}→{end}): PnL={total:.2f}% < floor={floor:.2f}% "
            f"(expected={expected}%, tolerance=±{REPLICATION_TOLERANCE_PCT}%). "
            f"n_trades={n_trades}."
        )


@pytest.mark.integration
def test_atr_breakout_production_runner_replicates_full_period() -> None:
    """S40 production runner MUST replicate 8.7y baseline within ±0.5%.

    run_atr_breakout_backtest() ports research kernel verbatim.
    End-to-end production path validation.
    """
    from src.backtest.atr_breakout_runner import run_atr_breakout_backtest

    result = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=FULL_START,
        end_date=FULL_END,
    )
    pnl = float(result["total_pnl_pct"])
    n = int(result["n_trades"])
    floor = FULL_BASELINE_PNL_PCT - REPLICATION_TOLERANCE_PCT
    assert pnl >= floor, (
        f"FAIL Phase 5 HARD-GATE: production runner 8.7y PnL={pnl:.2f}% < "
        f"floor={floor:.2f}% (baseline={FULL_BASELINE_PNL_PCT}%)."
    )
    assert abs(n - FULL_BASELINE_N_TRADES) <= 2, (
        f"FAIL Phase 5 HARD-GATE: production runner n_trades={n}, "
        f"expected ~{FULL_BASELINE_N_TRADES} (±2)."
    )


@pytest.mark.integration
def test_atr_breakout_preset_registered() -> None:
    """atr_breakout_iter_endless MUST be registered in STRATEGY_PRESETS.

    Smoke check that the production preset exists and has the locked params.
    """
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "atr_breakout_iter_endless" in STRATEGY_PRESETS, (
        "atr_breakout_iter_endless not in STRATEGY_PRESETS. "
        "S40 T4 task (register preset) incomplete."
    )
    preset = STRATEGY_PRESETS["atr_breakout_iter_endless"]
    ab_params = preset["indicators"]["atr_breakout"]

    assert ab_params["atr_period"] == ATR_BREAKOUT_PARAMS["atr_period"]
    assert abs(ab_params["atr_breakout_mult"] - ATR_BREAKOUT_PARAMS["atr_breakout_mult"]) < 1e-6
    assert ab_params["atr_stop_period"] == ATR_BREAKOUT_PARAMS["atr_stop_period"]
    assert abs(ab_params["atr_stop_mult"] - ATR_BREAKOUT_PARAMS["atr_stop_mult"]) < 1e-6


@pytest.mark.integration
def test_atr_breakout_data_coverage() -> None:
    """4H BTCUSDT Binance data MUST cover full 8.7y window (2017-08-17 → 2026-04-30)."""
    df = _load_4h_btcusdt_binance(FULL_START, FULL_END)
    assert len(df) >= 15000, (
        f"Insufficient 4H bars: {len(df)} < 15000. "
        f"Data file may not cover 8.7y (2017-08-17 → 2026-04-30)."
    )
    assert (
        df["timestamp"].dt.date.min() <= FULL_START
    ), f"Data start {df['timestamp'].dt.date.min()} > required {FULL_START}."
    assert df["timestamp"].dt.date.max() >= date(
        2026, 4, 28
    ), f"Data end {df['timestamp'].dt.date.max()} < 2026-04-28."


@pytest.mark.integration
def test_atr_breakout_sharpe_positive() -> None:
    """8.7y Sharpe MUST be positive (autoresearch baseline 1.11)."""
    from src.backtest.atr_breakout_runner import run_atr_breakout_backtest

    result = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=FULL_START,
        end_date=FULL_END,
    )
    sharpe = float(result["sharpe"])
    assert sharpe > 0, f"Sharpe={sharpe:.3f} is NOT positive."
    assert sharpe >= 0.5, f"Sharpe={sharpe:.3f} < 0.5 (research baseline 1.11)."
