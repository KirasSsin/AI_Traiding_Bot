"""S50 T3 (CC4, ADR 0067 Q4): held-out date split for autoresearch_endless.

Verifies physical train/held-out separation to prevent champion-bias (Bailey 2014)
when the endless loop sweeps parameters and picks a per-combo winner. The sweep must
read TRAIN only (< HELDOUT_START); held-out evaluation is a separate single call on
the winning combo.

Timestamp convention: `_normalize_df` produces a COLUMN named `ts` (tz-aware UTC),
not an index. Tests construct DataFrames matching that convention.
"""

from __future__ import annotations

import pandas as pd
from scripts.autoresearch_endless import (
    HELDOUT_END,
    HELDOUT_START,
    eval_heldout_once,
    split_train_heldout,
)


def _make_daily_df(start: str, end: str) -> pd.DataFrame:
    """Build a daily OHLCV df with a tz-aware `ts` column (matches _normalize_df)."""
    ts = pd.date_range(start=start, end=end, freq="D", tz="UTC")
    n = len(ts)
    # Deterministic mild uptrend so indicators/backtest have something to chew on.
    close = pd.Series(range(n), dtype="float64") * 0.5 + 100.0
    return pd.DataFrame(
        {
            "ts": ts,
            "open": close.to_numpy(),
            "high": close.to_numpy() + 1.0,
            "low": close.to_numpy() - 1.0,
            "close": close.to_numpy(),
            "volume": [1000.0] * n,
        }
    )


def test_heldout_constants() -> None:
    assert HELDOUT_START == "2025-06-01"
    assert HELDOUT_END == "2026-05-01"


def test_split_train_excludes_heldout() -> None:
    df = _make_daily_df("2024-01-01", "2026-05-01")
    train, heldout = split_train_heldout(df)

    start = pd.Timestamp(HELDOUT_START, tz="UTC")
    end = pd.Timestamp(HELDOUT_END, tz="UTC")

    # train strictly before HELDOUT_START
    assert len(train) > 0
    assert train["ts"].max() < start

    # heldout within [START, END]
    assert len(heldout) > 0
    assert heldout["ts"].min() >= start
    assert heldout["ts"].max() <= end

    # no overlap, and partition is exhaustive over [first_bar, END]
    assert train["ts"].max() < heldout["ts"].min()
    assert len(train) + len(heldout) == len(df)


def test_split_empty_heldout_when_data_all_before_start() -> None:
    df = _make_daily_df("2023-01-01", "2024-12-31")
    train, heldout = split_train_heldout(df)
    assert len(train) == len(df)
    assert len(heldout) == 0


def test_split_index_reset() -> None:
    df = _make_daily_df("2024-01-01", "2026-05-01")
    train, heldout = split_train_heldout(df)
    # both slices must have a clean 0..n-1 RangeIndex for downstream positional logic
    assert list(train.index) == list(range(len(train)))
    assert list(heldout.index) == list(range(len(heldout)))


def test_eval_heldout_once_returns_metrics() -> None:
    df = _make_daily_df("2024-01-01", "2026-05-01")
    _train, heldout = split_train_heldout(df)
    combo = {
        "strategy": "ema_cross",
        "params": {"fast": 5, "slow": 21, "atr_period": 14},
        "atr_stop_mult": 2.0,
        "bars_per_year": 365,
    }
    result = eval_heldout_once(combo, heldout)
    # contract: a metrics dict with the core backtest fields
    assert isinstance(result, dict)
    for key in ("heldout_pnl_pct", "heldout_sharpe", "heldout_n_trades", "heldout_win_rate"):
        assert key in result
