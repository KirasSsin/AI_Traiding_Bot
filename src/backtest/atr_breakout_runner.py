"""ATR breakout backtest runner — S40 T3 (ADR 0060).

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

Locked params: per ADR 0060. MUST NOT change without new ADR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isnan, sqrt
from typing import Any

import numpy as np
import pandas as pd

# Mirror constants from scripts/autoresearch_endless.py exactly.
_BARS_PER_YEAR = 2190  # 4H bars per year
_COMMISSION_TAKER = 0.001  # 0.1% taker
_SLIPPAGE = 0.0005  # 0.05% adverse


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


def _backtest_single(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
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
        trades_per_year = _BARS_PER_YEAR / mean_holding
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


def run_atr_breakout_backtest(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Run atr_breakout single contiguous backtest using LOCKED params (ADR 0060).

    Execution model is exact port of scripts/autoresearch_endless.py::strat_atr_breakout
    + _backtest for BTCUSDT 4H. This is the EXACT pipeline that produced
    research baseline +819.81% (8.7y) / Sharpe 1.11 / 5/5 sub-periods positive.

    NOT WFA. NOT Kelly-sized. Sequential additive PnL.

    Args:
        symbol: e.g. "BTCUSDT"
        interval: e.g. "240" (4H)
        start_date: inclusive start
        end_date: inclusive end

    Returns:
        {
            "n_trades": int,
            "total_pnl_pct": float,  # sum(pnl_net) * 100
            "sharpe": float,         # (mean/std) * sqrt(BARS_PER_YEAR / mean_holding)
            "win_rate": float,
            "trades": list[_TradeRecord],
        }

    Raises:
        FileNotFoundError: if parquet data missing for (symbol, interval)
        ValueError: if data is empty for given date range
    """
    import pandas as pd

    # ATR breakout strategy validated on Binance 4H data (autoresearch used BTCUSDT_4h_binance.parquet).
    # Bybit data (BTCUSDT_4h.parquet) starts 2023-01-01 — insufficient for full 8.7y backtest.
    # Production runner uses Binance data to match research baseline exactly.
    # Derive parquet path from autoresearch COMBOS mapping:
    #   ("BTCUSDT", "240") → "data/BTCUSDT_4h_binance.parquet"
    _BINANCE_DATA: dict[tuple[str, str], str] = {
        ("BTCUSDT", "240"): "data/BTCUSDT_4h_binance.parquet",
    }
    data_path = _BINANCE_DATA.get((symbol, interval))
    if data_path is None:
        # Fallback to standard _load_ohlcv for other symbol/interval combos
        from src.__main__ import _load_ohlcv

        df = _load_ohlcv(
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=interval,
        )
    else:
        # Load Binance parquet directly (mirrors autoresearch_endless.py::_normalize_df)
        raw = pd.read_parquet(data_path)
        if "ts" in raw.columns:
            raw["ts"] = pd.to_datetime(raw["ts"], utc=True)
        elif "time" in raw.columns:
            raw = raw.rename(columns={"time": "ts"})
            raw["ts"] = pd.to_datetime(raw["ts"], utc=True)
        else:
            raw = raw.reset_index()
            raw["ts"] = pd.to_datetime(raw["ts"], utc=True)
        raw = raw.sort_values("ts").reset_index(drop=True)
        mask = raw["ts"].dt.date >= start_date
        mask &= raw["ts"].dt.date <= end_date
        df = raw[mask].copy().reset_index(drop=True)
        # Rename to standard columns expected by _backtest_single
        if "ts" in df.columns:
            df = df.rename(columns={"ts": "timestamp"})

    if df.empty:
        raise ValueError(f"No OHLCV data for {symbol} {interval} in {start_date}..{end_date}")

    # Pull locked params from the canonical source (atr_breakout_strategy.py)
    from src.signalgen.atr_breakout_strategy import ATR_BREAKOUT_LOCKED_PARAMS

    params: dict[str, Any] = {
        "atr_period": int(ATR_BREAKOUT_LOCKED_PARAMS["atr_period"]),  # type: ignore[call-overload]
        "atr_breakout_mult": float(ATR_BREAKOUT_LOCKED_PARAMS["atr_breakout_mult"]),  # type: ignore[arg-type]
        "atr_stop_period": int(ATR_BREAKOUT_LOCKED_PARAMS["atr_stop_period"]),  # type: ignore[call-overload]
        "atr_stop_mult": float(ATR_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"]),  # type: ignore[arg-type]
    }

    return _backtest_single(df, params)
