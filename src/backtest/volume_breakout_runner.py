"""volume_breakout backtest runner — S39 T5b (ADR 0059).

Exact port of research/backtest_v2.py::_backtest_single adapted for volume_breakout
with volume confirmation (from research/strategies.py::strat_volume_breakout).

This module bypasses the generic replay_engine for the volume_breakout strategy
because replay_engine has 3 structural gaps for this strategy:
  1. sl_atr_mult wiring (uses config default 1.5x, not sweep#1644 param 2.9663x)
  2. long_only=True suppresses -1 channel-exit signals in replay_engine.py:170
  3. WFA + 10% position_size != research sequential additive PnL

Operator decision: Variant 3 (S39 task T5b brief) — port research execution model
exactly. Other strategies (donchian/mean_reversion/ema_crossover) use replay_engine
unchanged.

Execution semantics preserved verbatim from research:
  - Signal on close(T-1) → fill at open(T) (no look-ahead)
  - ATR stop checked BEFORE channel exit (research line 140)
  - Wilder ATR (not classical EMA ATR)
  - ref_high/ref_low use [i-2] index (window ends at i-2, excludes current bar i)
  - Volume check uses [i-1] (bar i-1 inclusive)
  - Sequential additive PnL (sum, NOT compounded, NOT Kelly-sized)
  - Open position closed on last bar mark-to-market

Locked params: sweep#1644 per ADR 0059. MUST NOT change without new ADR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isnan, sqrt
from typing import Any

import numpy as np
import pandas as pd

# Mirror constants from research/backtest_v2.py exactly.
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
    """Wilder ATR — exact port of research/backtest_v2.py::_atr().

    Uses prev_close[0] = close[0] so TR[0] = max(h-l, |h-c|, |l-c|) which
    equals h-l for valid OHLC data. Wilder smoothing: SMA seed then EMA-like.

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
    # Wilder smoothing: first value = SMA of first `period` TRs, then exponential
    atr_out[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr_out[i] = (atr_out[i - 1] * (period - 1) + tr[i]) / period
    return atr_out


def _backtest_single(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    """Single contiguous volume_breakout backtest.

    Ports research/backtest_v2.py::_backtest_single with volume confirmation
    from research/strategies.py::strat_volume_breakout.

    Entry condition (bar i-1 signal → fill at open[i]):
        close[i-1] > roll_high[i-2]  (Donchian breakout)
        AND volume[i-1] > vol_mean[i-1] * vol_mult  (volume confirmation)

    Exit conditions (in priority order — ATR stop FIRST per research line 140):
        1. low[i] <= stop_price  → fill at stop_price * (1 - SLIPPAGE)
        2. close[i-1] < roll_low[i-2]  → fill at open[i] * (1 - SLIPPAGE)

    Args:
        df: OHLCV DataFrame with columns [open, high, low, close, volume].
        params: dict with keys lookback_n, exit_lookback_n, vol_window, vol_mult,
                atr_period, atr_stop_mult.

    Returns:
        dict with n_trades, total_pnl_pct, sharpe, win_rate, trades (list of _TradeRecord).
    """
    lookback_n = int(params["lookback_n"])
    exit_lookback_n = int(params["exit_lookback_n"])
    vol_window = int(params["vol_window"])
    vol_mult = float(params["vol_mult"])
    atr_period = int(params["atr_period"])
    atr_stop_mult = float(params["atr_stop_mult"])

    close = df["close"].to_numpy(dtype=np.float64)
    open_ = df["open"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    volume = df["volume"].to_numpy(dtype=np.float64)
    n = len(df)

    # Indicators — precomputed (no look-ahead: all use pandas rolling which is causal)
    roll_high = pd.Series(high).rolling(lookback_n, min_periods=lookback_n).max().to_numpy()
    roll_low = pd.Series(low).rolling(exit_lookback_n, min_periods=exit_lookback_n).min().to_numpy()
    vol_mean = pd.Series(volume).rolling(vol_window, min_periods=vol_window).mean().to_numpy()
    atr = _atr(df, atr_period)

    # Warmup: need enough bars for all indicators + the [i-2] index shift
    warmup = max(lookback_n, exit_lookback_n, atr_period, vol_window) + 1

    trades: list[_TradeRecord] = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    entry_atr = 0.0

    for i in range(warmup, n):
        if not in_pos:
            # Entry signal uses [i-2] for ref_high (window excludes current bar)
            # and [i-1] for volume mean (bar i-1 inclusive), close[i-1] for breakout check.
            if i < 2:
                continue
            ref_high = roll_high[i - 2]
            vol_mean_check = vol_mean[i - 1]
            if (
                not isnan(ref_high)
                and not isnan(vol_mean_check)
                and close[i - 1] > ref_high
                and volume[i - 1] > vol_mean_check * vol_mult
            ):
                entry_price = open_[i] * (1.0 + _SLIPPAGE)
                entry_idx = i
                entry_atr = atr[i - 1]
                if isnan(entry_atr):
                    # Skip: no valid ATR to compute stop — stay flat
                    continue
                in_pos = True
        else:
            # Exit conditions — ATR stop checked FIRST (research/backtest_v2.py line 140)
            stop_price = entry_price - entry_atr * atr_stop_mult
            ref_low = roll_low[i - 2] if i >= 2 else float("nan")
            channel_exit = (not isnan(ref_low)) and close[i - 1] < ref_low

            if low[i] <= stop_price:
                # Intrabar stop: fill at stop_price with adverse slippage
                exit_price = stop_price * (1.0 - _SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
                trades.append(_TradeRecord(entry_idx, i, entry_price, exit_price, pnl_net))
                in_pos = False
            elif channel_exit:
                # Channel exit: fill at open[i] with adverse slippage
                exit_price = open_[i] * (1.0 - _SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
                trades.append(_TradeRecord(entry_idx, i, entry_price, exit_price, pnl_net))
                in_pos = False

    # Close open position on last bar mark-to-market (research/backtest_v2.py line 154-159)
    if in_pos:
        exit_price = close[-1] * (1.0 - _SLIPPAGE)
        pnl_gross = (exit_price - entry_price) / entry_price
        pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
        trades.append(_TradeRecord(entry_idx, n - 1, entry_price, exit_price, pnl_net))

    # Aggregate metrics
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
        # Annualize: per-trade Sharpe × sqrt(BARS_PER_YEAR / mean_holding_bars)
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


def run_volume_breakout_backtest(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Run volume_breakout single contiguous backtest using LOCKED params (sweep#1644).

    Execution model is exact port of research/backtest_v2.py::_backtest_single
    adapted for volume_breakout with volume confirmation. This is the EXACT
    pipeline that produced research baseline +20.42% (8mo) / +122.66% (3.3y).

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
    from src.__main__ import _load_ohlcv

    df = _load_ohlcv(
        symbol=symbol,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        interval=interval,
    )
    if df.empty:
        raise ValueError(f"No OHLCV data for {symbol} {interval} in {start_date}..{end_date}")

    # Pull locked params from the canonical source (volume_breakout_strategy.py)
    from src.signalgen.volume_breakout_strategy import VOLUME_BREAKOUT_LOCKED_PARAMS

    params: dict[str, Any] = {
        "lookback_n": int(VOLUME_BREAKOUT_LOCKED_PARAMS["lookback_n"]),  # type: ignore[call-overload]
        "exit_lookback_n": int(VOLUME_BREAKOUT_LOCKED_PARAMS["exit_lookback_n"]),  # type: ignore[call-overload]
        "vol_window": int(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_window"]),  # type: ignore[call-overload]
        "vol_mult": float(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_mult"]),  # type: ignore[arg-type]
        "atr_period": int(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_period"]),  # type: ignore[call-overload]
        "atr_stop_mult": float(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"]),  # type: ignore[arg-type]
    }

    return _backtest_single(df, params)
