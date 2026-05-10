"""ATR breakout backtest runner — S40 T3 + S41 multi-combo (ADR 0060, ADR 0061).

Exact port of scripts/autoresearch_endless.py::strat_atr_breakout + _backtest
for the atr_breakout strategy.

This module bypasses the generic replay_engine for the atr_breakout strategy
because replay_engine has structural gaps for this strategy:
  1. sl_atr_mult wiring (uses config default 1.5x, not sweep param)
  2. long_only=True suppresses reverse-signal exits in replay_engine
  3. WFA + 10% position_size != research sequential additive PnL

Execution semantics preserved verbatim from research:
  - Signal on close(T-1) → fill at open(T) (no look-ahead)
  - ATR stop checked BEFORE reverse signal (research _backtest priority)
  - Wilder ATR (not classical EMA ATR)
  - Entry: close[i-1] > close[i-2] + mult * atr[i-2]
  - Exit reverse: close[i-1] < close[i-2] - mult * atr[i-2] (OR stop)
  - Sequential additive PnL (sum, NOT compounded, NOT Kelly-sized)
  - Open position closed on last bar mark-to-market

S40 locked params (BTCUSDT 4H): per ADR 0060. MUST NOT change without new ADR.
S41 multi-combo params: per ADR 0061. Each combo locked independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isnan, sqrt
from typing import Any

import numpy as np
import pandas as pd

# Mirror constants from scripts/autoresearch_endless.py exactly.
_COMMISSION_TAKER = 0.001  # 0.1% taker
_SLIPPAGE = 0.0005  # 0.05% adverse

# BARS_PER_YEAR per interval — mirrors autoresearch_endless.py::BARS_PER_YEAR_BY_INTERVAL
_BARS_PER_YEAR_BY_INTERVAL: dict[str, int] = {
    "5": int(365.25 * 24 * 12),
    "15": int(365.25 * 24 * 4),
    "60": int(365.25 * 24),
    "240": int(365.25 * 6),
    "D": int(365.25),
}

# Parquet file mapping per (symbol, interval) combo.
# Mirrors scripts/autoresearch_endless.py::COMBOS.
# S45 T1: all combos use uniform 3.3y data (2023-01-01 → 2026-04-26).
# BTCUSDT_4h_binance.parquet (8.7y exception) archived to data/_archive/.
PARQUET_BY_COMBO: dict[tuple[str, str], str] = {
    ("BTCUSDT", "240"): "data/BTCUSDT_4h.parquet",
    ("BTCUSDT", "60"): "data/BTCUSDT_1h.parquet",
    ("BTCUSDT", "15"): "data/BTCUSDT_15m.parquet",
    ("BTCUSDT", "D"): "data/BTCUSDT_1d.parquet",
    ("ETHUSDT", "240"): "data/ETHUSDT_4h.parquet",
    ("ETHUSDT", "60"): "data/ETHUSDT_1h.parquet",
    ("ETHUSDT", "15"): "data/ETHUSDT_15m.parquet",
    ("SOLUSDT", "240"): "data/SOLUSDT_4h.parquet",
    ("SOLUSDT", "60"): "data/SOLUSDT_1h.parquet",
    ("SOLUSDT", "15"): "data/SOLUSDT_15m.parquet",
}

# ADR 0061 LOCKED — per-combo params from autoresearch endless best_per_combo.json.
# Each combo's params LOCKED independently (anti-snooping audit trail per ADR 0061).
# DO NOT modify without a new ADR amendment.
# Source: data/autoresearch_endless/best_per_combo.json
ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO: dict[tuple[str, str], dict[str, Any]] = {
    ("BTCUSDT", "240"): {  # BTCUSDT 4H — original S40 params (ADR 0060)
        "atr_period": 9,
        "atr_breakout_mult": 2.5,
        "atr_stop_period": 21,
        "atr_stop_mult": 1.5,
    },
    ("BTCUSDT", "60"): {  # BTCUSDT 1H — autoresearch endless best
        "atr_period": 9,
        "atr_breakout_mult": 2.5,
        "atr_stop_period": 21,
        "atr_stop_mult": 3.0,
    },
    ("BTCUSDT", "15"): {  # BTCUSDT 15M — autoresearch endless best
        "atr_period": 9,
        "atr_breakout_mult": 3.0,
        "atr_stop_period": 14,
        "atr_stop_mult": 3.0,
    },
    ("BTCUSDT", "D"): {  # BTCUSDT 1D — autoresearch endless best
        "atr_period": 9,
        "atr_breakout_mult": 1.0,
        "atr_stop_period": 9,
        "atr_stop_mult": 3.0,
    },
    ("ETHUSDT", "240"): {  # ETHUSDT 4H — autoresearch endless best
        "atr_period": 14,
        "atr_breakout_mult": 2.5,
        "atr_stop_period": 14,
        "atr_stop_mult": 1.5,
    },
    ("ETHUSDT", "60"): {  # ETHUSDT 1H — autoresearch endless best
        "atr_period": 14,
        "atr_breakout_mult": 2.5,
        "atr_stop_period": 21,
        "atr_stop_mult": 1.5,
    },
    ("ETHUSDT", "15"): {  # ETHUSDT 15M — autoresearch endless best
        "atr_period": 9,
        "atr_breakout_mult": 3.0,
        "atr_stop_period": 14,
        "atr_stop_mult": 2.0,
    },
    ("SOLUSDT", "240"): {  # SOLUSDT 4H — autoresearch endless best
        "atr_period": 21,
        "atr_breakout_mult": 1.5,
        "atr_stop_period": 9,
        "atr_stop_mult": 2.0,
    },
    ("SOLUSDT", "60"): {  # SOLUSDT 1H — autoresearch endless best
        "atr_period": 9,
        "atr_breakout_mult": 2.0,
        "atr_stop_period": 21,
        "atr_stop_mult": 3.0,
    },
    ("SOLUSDT", "15"): {  # SOLUSDT 15M — autoresearch endless best
        "atr_period": 21,
        "atr_breakout_mult": 2.5,
        "atr_stop_period": 9,
        "atr_stop_mult": 3.0,
    },
}


@dataclass
class _TradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    pnl_pct: float  # net (after commission + slippage), fractional (not ×100)


def _atr(df: pd.DataFrame, period: int) -> np.ndarray:
    """Wilder ATR — exact port of scripts/autoresearch_endless.py::_atr().

    Uses prev_close[0] = close[0] so TR[0] = h-l for valid OHLC data.
    Wilder smoothing: SMA seed then EMA-like.

    Returns array same length as df; NaN for indices < period-1.
    """
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr: np.ndarray = np.maximum.reduce(
        [
            high - low,
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ]
    )
    atr_out = np.full_like(tr, np.nan)
    if len(tr) < period:
        return atr_out
    atr_out[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr_out[i] = (atr_out[i - 1] * (period - 1) + tr[i]) / period
    return atr_out


def _backtest_single(
    df: pd.DataFrame, params: dict[str, Any], bars_per_year: int
) -> dict[str, Any]:
    """Single contiguous atr_breakout backtest.

    Ports scripts/autoresearch_endless.py::strat_atr_breakout + _backtest verbatim.

    Entry condition (bar i-1 signal → fill at open[i]):
        close[i-1] > close[i-2] + atr_breakout_mult * atr[i-2]

    Exit conditions:
        1. low[i] <= stop_price (ATR stop) → fill at stop_price * (1 - SLIPPAGE)
        2. close[i-1] < close[i-2] - atr_breakout_mult * atr[i-2] → fill at open[i] * (1 - SLIPPAGE)

    Args:
        df: OHLCV DataFrame with columns [open, high, low, close, volume] (or similar).
        params: dict with keys atr_period, atr_breakout_mult, atr_stop_period, atr_stop_mult.
        bars_per_year: annualization constant for the interval (e.g. 2190 for 4H).

    Returns:
        dict with n_trades, total_pnl_pct, sharpe, win_rate, trades (list of _TradeRecord).
    """
    atr_period = int(params["atr_period"])
    atr_breakout_mult = float(params["atr_breakout_mult"])
    atr_stop_period = int(params["atr_stop_period"])
    atr_stop_mult = float(params["atr_stop_mult"])

    close = df["close"].to_numpy(dtype=np.float64)
    open_ = df["open"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)

    # Precompute ATR arrays
    atr_arr = _atr(df, atr_period)
    atr_stop = _atr(df, atr_stop_period) if atr_stop_period != atr_period else atr_arr

    # Build signals (exact port of strat_atr_breakout)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    warmup = max(atr_period, atr_stop_period) + 3

    for i in range(warmup, n):
        if not isnan(atr_arr[i - 2]):
            if close[i - 1] > close[i - 2] + atr_breakout_mult * atr_arr[i - 2]:
                entry[i] = True
            if close[i - 1] < close[i - 2] - atr_breakout_mult * atr_arr[i - 2]:
                exit_[i] = True

    trades: list[_TradeRecord] = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    entry_atr = 0.0

    for i in range(warmup, n):
        if not in_pos:
            if entry[i]:
                a = atr_stop[i - 1] if i >= 1 else float("nan")
                if isnan(a):
                    continue
                entry_price = open_[i] * (1.0 + _SLIPPAGE)
                entry_idx = i
                entry_atr = a
                in_pos = True
        else:
            stop_price = entry_price - entry_atr * atr_stop_mult
            if low[i] <= stop_price:
                exit_price = stop_price * (1.0 - _SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
                trades.append(_TradeRecord(entry_idx, i, entry_price, exit_price, pnl_net))
                in_pos = False
            elif exit_[i]:
                exit_price = open_[i] * (1.0 - _SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
                trades.append(_TradeRecord(entry_idx, i, entry_price, exit_price, pnl_net))
                in_pos = False

    # Close open position on last bar mark-to-market
    if in_pos:
        exit_price = close[-1] * (1.0 - _SLIPPAGE)
        pnl_gross = (exit_price - entry_price) / entry_price
        pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
        trades.append(_TradeRecord(entry_idx, n - 1, entry_price, exit_price, pnl_net))

    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "sharpe": float("nan"),
            "total_pnl_pct": 0.0,
            "win_rate": float("nan"),
            "trades": [],
        }

    pnls = np.array([t.pnl_pct for t in trades])
    mean_holding = float(np.mean([t.exit_idx - t.entry_idx for t in trades]))
    pnl_std = float(pnls.std(ddof=1))

    if pnl_std > 0 and mean_holding > 0:
        trades_per_year = bars_per_year / mean_holding
        sharpe = float((pnls.mean() / pnl_std) * sqrt(trades_per_year))
    else:
        sharpe = float("nan") if pnl_std == 0 else 0.0

    return {
        "n_trades": n_trades,
        "sharpe": sharpe,
        "total_pnl_pct": float(pnls.sum() * 100.0),
        "win_rate": float(float((pnls > 0).mean())),
        "trades": trades,
    }


def _load_parquet_df(
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Load and normalize OHLCV DataFrame from parquet for (symbol, interval).

    Handles both 'ts' (Binance) and 'time' (Bybit) column schemas.
    Filters to [start_date, end_date] inclusive.

    Raises:
        FileNotFoundError: if parquet path not in PARQUET_BY_COMBO
    """
    data_path = PARQUET_BY_COMBO.get((symbol, interval))
    if data_path is None:
        raise FileNotFoundError(
            f"No parquet data path registered for ({symbol}, {interval}). "
            f"Supported combos: {sorted(PARQUET_BY_COMBO.keys())}"
        )

    raw = pd.read_parquet(data_path)

    # Normalize timestamp column — handles 'ts' (Binance) and 'time' (Bybit) schemas
    if "ts" in raw.columns:
        raw["_ts"] = pd.to_datetime(raw["ts"], utc=True)
    elif "time" in raw.columns:
        raw["_ts"] = pd.to_datetime(raw["time"], utc=True)
    else:
        raw = raw.reset_index()
        raw["_ts"] = pd.to_datetime(raw.iloc[:, 0], utc=True)

    raw = raw.sort_values("_ts").reset_index(drop=True)
    mask = raw["_ts"].dt.date >= start_date
    mask &= raw["_ts"].dt.date <= end_date
    df = raw[mask].copy().reset_index(drop=True)

    return df


def run_atr_breakout_backtest(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run atr_breakout single contiguous backtest.

    S40: uses LOCKED params from ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO for BTCUSDT 4H.
    S41: extended to all 10 (symbol, interval) combos — each with independently locked params.

    Execution model is exact port of scripts/autoresearch_endless.py::strat_atr_breakout
    + _backtest. NOT WFA. NOT Kelly-sized. Sequential additive PnL.

    Args:
        symbol: e.g. "BTCUSDT", "ETHUSDT", "SOLUSDT"
        interval: e.g. "240" (4H), "60" (1H), "15" (15M), "D" (1D)
        start_date: inclusive start
        end_date: inclusive end
        params: explicit params dict (atr_period, atr_breakout_mult, atr_stop_period,
                atr_stop_mult). If None, uses ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO lookup.

    Returns:
        {
            "n_trades": int,
            "total_pnl_pct": float,  # sum(pnl_net) * 100
            "sharpe": float,         # (mean/std) * sqrt(bars_per_year / mean_holding)
            "win_rate": float,
            "trades": list[_TradeRecord],
        }

    Raises:
        FileNotFoundError: if parquet data not found for (symbol, interval)
        ValueError: if data is empty for given date range, or combo not in locked params
    """
    # Resolve params: explicit override OR locked combo params
    if params is None:
        locked = ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.get((symbol, interval))
        if locked is None:
            raise ValueError(
                f"No locked params for ({symbol}, {interval}). "
                f"Pass explicit params= or add to ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO."
            )
        resolved_params: dict[str, Any] = {
            "atr_period": int(locked["atr_period"]),
            "atr_breakout_mult": float(locked["atr_breakout_mult"]),
            "atr_stop_period": int(locked["atr_stop_period"]),
            "atr_stop_mult": float(locked["atr_stop_mult"]),
        }
    else:
        resolved_params = {
            "atr_period": int(params["atr_period"]),
            "atr_breakout_mult": float(params["atr_breakout_mult"]),
            "atr_stop_period": int(params["atr_stop_period"]),
            "atr_stop_mult": float(params["atr_stop_mult"]),
        }

    bars_per_year = _BARS_PER_YEAR_BY_INTERVAL.get(interval, 2190)

    df = _load_parquet_df(symbol, interval, start_date, end_date)

    if df.empty:
        raise ValueError(f"No OHLCV data for {symbol} {interval} in {start_date}..{end_date}")

    # Run inner backtest — minimal dict
    inner = _backtest_single(df, resolved_params, bars_per_year)

    # S43 T4 — Build equity_curve + timestamps parallel arrays для uPlot.
    # Each trade closes на bar `exit_idx` — its timestamp = df["_ts"].iloc[exit_idx].
    trades_list = inner.get("trades", [])
    equity_curve: list[float] = [0.0]
    equity_timestamps: list[int] = []
    if trades_list and not df.empty:
        # Starting equity timestamp = first bar в df (before any trades)
        equity_timestamps.append(int(df["_ts"].iloc[0].timestamp()))
        for tr in trades_list:
            equity_curve.append(equity_curve[-1] + (tr.pnl_pct * 100.0))
            equity_timestamps.append(int(df["_ts"].iloc[tr.exit_idx].timestamp()))

    # T11 — build trade_markers payload (entry/exit timestamps + prices + pnl per trade)
    trade_markers: dict[str, list[float | int]] | None = None
    if trades_list and not df.empty:
        trade_markers = {
            "entry_timestamps": [int(df["_ts"].iloc[t.entry_idx].timestamp()) for t in trades_list],
            "exit_timestamps": [int(df["_ts"].iloc[t.exit_idx].timestamp()) for t in trades_list],
            "entry_prices": [float(t.entry_price) for t in trades_list],
            "exit_prices": [float(t.exit_price) for t in trades_list],
            "pnl_pcts": [float(t.pnl_pct * 100.0) for t in trades_list],
        }

    # Wrap in dashboard contract envelope
    from src.backtest.research_runner_envelope import build_research_runner_envelope

    sharpe_raw = float(inner["sharpe"])
    return build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol=symbol,
        interval=interval,
        n_trades=int(inner["n_trades"]),
        sharpe=sharpe_raw if sharpe_raw == sharpe_raw else 0.0,  # NaN guard
        win_rate=float(inner["win_rate"])
        if float(inner["win_rate"]) == float(inner["win_rate"])
        else 0.0,
        total_pnl_pct=float(inner["total_pnl_pct"]),
        bars_per_year=bars_per_year,
        equity_curve=equity_curve,
        equity_timestamps=equity_timestamps,
        runner_label=f"ATR breakout {interval} {symbol} (LOCKED)",
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        trade_markers=trade_markers,
    )


def _run_atr_breakout_wfa(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    train_bars: int | None = None,
    test_bars: int | None = None,
    k_folds: int | None = None,
    embargo_bars: int | None = None,
) -> dict[str, Any]:
    """S44 T2 — WFA для atr_breakout с per-combo LOCKED params.

    S45 — Tier-aware defaults per ADR 0014 amendment (low-freq 4H/D test_bars=250).

    Pattern: donchian_runner._run_donchian_wfa adapted к research kernel
    (_backtest_single signature). PnL accounting sequential-additive preserved
    (per ADR 0064 + S42 trader-expert verdict — replay_engine architecturally
    blocked per docstring lines 5-12).
    """
    from src.backtest.research_wfa import get_wfa_tier_params, run_research_wfa

    tier = get_wfa_tier_params(interval)
    train_bars = train_bars if train_bars is not None else tier["train_bars"]
    test_bars = test_bars if test_bars is not None else tier["test_bars"]
    k_folds = k_folds if k_folds is not None else tier["k_folds"]
    embargo_bars = embargo_bars if embargo_bars is not None else tier["embargo_bars"]

    locked = ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.get((symbol, interval))
    if locked is None:
        raise ValueError(
            f"No LOCKED params for ({symbol}, {interval}). "
            f"Supported combos: {sorted(ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.keys())}"
        )
    params: dict[str, Any] = {
        "atr_period": int(locked["atr_period"]),
        "atr_breakout_mult": float(locked["atr_breakout_mult"]),
        "atr_stop_period": int(locked["atr_stop_period"]),
        "atr_stop_mult": float(locked["atr_stop_mult"]),
    }
    bars_per_year = _BARS_PER_YEAR_BY_INTERVAL.get(interval, 2190)
    df = _load_parquet_df(symbol, interval, start_date, end_date)
    if df.empty:
        raise ValueError(f"No OHLCV для {symbol} {interval} в [{start_date}, {end_date}]")

    return run_research_wfa(
        df=df,
        params=params,
        backtest_fn=_backtest_single,  # research kernel
        bars_per_year=bars_per_year,
        symbol=symbol,
        train_bars=train_bars,
        test_bars=test_bars,
        k_folds=k_folds,
        embargo_bars=embargo_bars,
        n_trials=10,  # S45 C1 — atr_breakout family = 10 hypotheses
        sprint_tag="S44",
    )
