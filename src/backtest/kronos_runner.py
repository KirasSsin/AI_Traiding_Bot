"""Kronos exploratory backtest runner — S52 T6 (ADR 0068, V5, ESC-1=A).

Replays a pre-populated :class:`~src.ml.prediction_cache.PredictionCache` through
a bar-by-bar kernel driving :class:`~src.signalgen.kronos_strategy.KronosStrategy`.

Design constraints (V5, ESC-1=A):
  - EXPLORATORY ONLY — no formal WFA path, no ``run_research_wfa`` call, no
    ``CrossTrialLog.append_trial`` (no formal N_trials increment).  Hypothesis #11
    is deferred to forward paper-trade (ADR 0068 GATE 0 finding).
  - Verdict is hard-pinned to ``VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED`` via
    :func:`~src.backtest.research_runner_envelope.build_research_runner_envelope`
    ``verdict_override``.  ``acceptance_gate`` stays ``None`` (non-gating).
  - Look-ahead safety: fills use NEXT bar open (``open[i+1]``), NOT ``open[i]``.
    The strategy decides on a closed bar; the earliest executable price is the
    next bar's open.  Mirrors the supertrend_runner contract (close(T) -> open(T+1)).
  - No torch, no network.  The runner only drives the cache-lookup path of
    ``KronosStrategy.on_bar``; the cache must be pre-populated by the caller
    (T7 cache-build script).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sqrt
from typing import Any

import numpy as np
import pandas as pd

from src.backtest.research_runner_envelope import (
    VERDICT_RAW_PRETRAIN_LEAKAGE,
    build_research_runner_envelope,
)
from src.marketdata.models import Bar
from src.ml.prediction_cache import PredictionCache
from src.signalgen.kronos_strategy import KronosStrategy
from src.signalgen.models import SignalSide

_log = logging.getLogger(__name__)

_COMMISSION_TAKER: float = 0.001  # 0.1% taker — mirrors supertrend_runner
_SLIPPAGE: float = 0.0005  # 0.05% adverse

# Seconds in a 365.25-day year (consistent with 8766 h/year used elsewhere).
_SECONDS_PER_YEAR: float = 365.25 * 24 * 3600  # 31_557_600

# Timeframe string → interval in seconds (mirrors _build_bar_from_row map).
_TF_SECONDS: dict[str, float] = {
    "1m": 60.0,
    "5m": 300.0,
    "15m": 900.0,
    "1h": 3600.0,
    "4h": 14400.0,
    "1d": 86400.0,
}


def _bars_per_year(timeframe: str) -> float:
    """Return annualised bar count for ``timeframe`` using a 365.25-day year.

    Examples:
        ``_bars_per_year("1h")`` → 8766.0
        ``_bars_per_year("1d")`` → 365.25
        ``_bars_per_year("5m")`` → 105192.0
    """
    tf_sec = _TF_SECONDS.get(timeframe, 3600.0)
    return _SECONDS_PER_YEAR / tf_sec


@dataclass
class _TradeRecord:
    """Single completed round-trip trade."""

    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    pnl_pct: float  # net after commission + slippage, fractional (not x100)


def _build_bar_from_row(
    row: "pd.Series[Any]",
    symbol: str,
    timeframe: str,
    is_closed: bool = True,
) -> Bar:
    """Construct a :class:`~src.marketdata.models.Bar` from a normalized OHLCV row.

    The ``_ts`` column (UTC datetime) is used as ``open_time``; ``close_time`` is
    derived as ``open_time + 1 interval`` (bar not yet in final form — used only
    for the cache-key close_ts via ``bar.close_time``).

    Args:
        row: OHLCV DataFrame row with columns ``_ts``, ``open``, ``high``,
            ``low``, ``close``, ``volume``.
        symbol: Trading symbol (e.g. ``"BTCUSDT"``).
        timeframe: Bar timeframe string (e.g. ``"1h"``).  Used to derive the
            close-time offset.
        is_closed: Whether to mark the bar as closed (True in backtest — all
            bars are already settled).

    Returns:
        A validated :class:`Bar` instance.
    """
    # Map timeframe string to timedelta for close_time derivation.
    _tf_to_td: dict[str, timedelta] = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
    }
    td = _tf_to_td.get(timeframe, timedelta(hours=1))

    open_time: datetime = pd.Timestamp(row["_ts"]).to_pydatetime().replace(tzinfo=UTC)
    close_time: datetime = open_time + td

    open_price = Decimal(str(float(row["open"])))
    high_price = Decimal(str(float(row["high"])))
    low_price = Decimal(str(float(row["low"])))
    close_price = Decimal(str(float(row["close"])))
    volume = Decimal(str(float(row["volume"])))

    return Bar(
        symbol=symbol,
        interval=timeframe,
        open_time=open_time,
        close_time=close_time,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        trade_count=0,
        is_closed=is_closed,
    )


def run_kronos_exploratory(
    *,
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    params: dict[str, Any],
    cache: PredictionCache,
) -> dict[str, Any]:
    """Run a cache-replay exploratory backtest for the Kronos strategy.

    Drives :class:`~src.signalgen.kronos_strategy.KronosStrategy` bar-by-bar
    through the supplied OHLCV DataFrame.  Predictions are looked up from
    ``cache`` (pre-populated by the T7 build script); cache-miss bars produce
    no signal, no trade, no crash.

    Fills mirror the supertrend_runner contract:
      - Entry signal on closed bar i -> fill at ``open[i+1] * (1 + SLIPPAGE)``
      - Exit signal on closed bar i  -> fill at ``open[i+1] * (1 - SLIPPAGE)``
      - A signal on the LAST bar (no next bar) is skipped for entries; an open
        position is closed at last-bar mark-to-market.

    This function MUST NOT call ``run_research_wfa`` and MUST NOT register
    ``cross_trial_sharpes`` entries.  The verdict is hard-pinned to
    ``VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED`` (non-gating, exploratory only).

    Args:
        df: Normalized OHLCV DataFrame.  Must contain columns ``_ts``,
            ``open``, ``high``, ``low``, ``close``, ``volume``.
        symbol: Trading symbol (e.g. ``"BTCUSDT"``).
        timeframe: Bar timeframe string (e.g. ``"1h"``).
        params: Strategy configuration dict.  Expected keys:
            ``model_id``, ``weights_hash``, ``timeframe``, ``params_hash``,
            ``device``.  Optional ``threshold`` (``Decimal`` or str).
        cache: Pre-populated :class:`~src.ml.prediction_cache.PredictionCache`.

    Returns:
        Dashboard-contract envelope dict from
        :func:`~src.backtest.research_runner_envelope.build_research_runner_envelope`
        with ``verdict == VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED`` and
        ``acceptance_gate == None``.
    """
    model_id: str = str(params.get("model_id", "kronos"))
    weights_hash: str = str(params.get("weights_hash", "unknown"))
    params_hash: str = str(params.get("params_hash", "unknown"))
    device: str = str(params.get("device", "cpu"))
    raw_threshold = params.get("threshold")
    threshold: Decimal = (
        Decimal(str(raw_threshold)) if raw_threshold is not None else Decimal("0.006")
    )

    strategy = KronosStrategy(
        symbol=symbol,
        cache=cache,
        model_id=model_id,
        weights_hash=weights_hash,
        timeframe=timeframe,
        params_hash=params_hash,
        device=device,
        threshold=threshold,
    )

    df_reset = df.reset_index(drop=True)
    n = len(df_reset)
    open_arr: np.ndarray = df_reset["open"].to_numpy(dtype=np.float64)
    close_arr: np.ndarray = df_reset["close"].to_numpy(dtype=np.float64)

    trades: list[_TradeRecord] = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    # equity_curve tracks fractional cumulative PnL (additive, per ADR 0064)
    equity_pct: list[float] = [0.0]

    for i in range(n):
        try:
            bar = _build_bar_from_row(df_reset.iloc[i], symbol=symbol, timeframe=timeframe)
        except Exception:
            _log.debug("kronos_runner: skipping malformed bar at index %d", i)
            continue

        signal = strategy.on_bar(bar)

        if signal is None:
            continue

        # Fills require a next bar open (look-ahead safety: signal decided at
        # close[i], fill at open[i+1]).  A signal on the last bar is skipped
        # for entries; an open long is closed at mark-to-market below.
        has_next = (i + 1) < n

        if signal.side == SignalSide.LONG and not in_pos:
            if has_next:
                fill = open_arr[i + 1] * (1.0 + _SLIPPAGE)
                entry_price = fill
                entry_idx = i + 1
                in_pos = True
                _log.debug(
                    "kronos_runner: ENTRY bar=%d fill=%.4f (open[%d]=%.4f)",
                    i,
                    fill,
                    i + 1,
                    open_arr[i + 1],
                )

        elif signal.side == SignalSide.FLAT and in_pos:
            if has_next:
                fill = open_arr[i + 1] * (1.0 - _SLIPPAGE)
                pnl_gross = (fill - entry_price) / entry_price
                pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
                trades.append(
                    _TradeRecord(
                        entry_idx=entry_idx,
                        exit_idx=i + 1,
                        entry_price=entry_price,
                        exit_price=fill,
                        pnl_pct=pnl_net,
                    )
                )
                equity_pct.append(equity_pct[-1] + pnl_net)
                in_pos = False
                _log.debug(
                    "kronos_runner: EXIT bar=%d fill=%.4f pnl_net=%.4f",
                    i,
                    fill,
                    pnl_net,
                )

    # Close open position at last-bar mark-to-market (mirrors supertrend_runner)
    if in_pos:
        fill = close_arr[-1] * (1.0 - _SLIPPAGE)
        pnl_gross = (fill - entry_price) / entry_price
        pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
        trades.append(
            _TradeRecord(
                entry_idx=entry_idx,
                exit_idx=n - 1,
                entry_price=entry_price,
                exit_price=fill,
                pnl_pct=pnl_net,
            )
        )
        equity_pct.append(equity_pct[-1] + pnl_net)

    n_trades = len(trades)
    pnls = np.array([t.pnl_pct for t in trades])

    if n_trades == 0:
        sharpe = float("nan")
        total_pnl_pct = 0.0
        win_rate = float("nan")
    else:
        total_pnl_pct = float(pnls.sum() * 100.0)
        win_rate = float((pnls > 0).mean())
        pnl_std = float(pnls.std(ddof=1)) if n_trades > 1 else 0.0
        mean_holding = float(np.mean([t.exit_idx - t.entry_idx for t in trades]))
        if pnl_std > 0 and mean_holding > 0:
            trades_per_year = _bars_per_year(timeframe) / mean_holding
            sharpe = float((pnls.mean() / pnl_std) * sqrt(trades_per_year))
        else:
            sharpe = float("nan") if pnl_std == 0 else 0.0

    # Build equity curve as % values for the dashboard (multiply pct fractions x100)
    equity_curve_pct: list[float] = [v * 100.0 for v in equity_pct]

    envelope = build_research_runner_envelope(
        runner_name="kronos_exploratory",
        symbol=symbol,
        interval=timeframe,
        n_trades=n_trades,
        sharpe=sharpe,
        win_rate=win_rate if not (isinstance(win_rate, float) and win_rate != win_rate) else 0.0,
        total_pnl_pct=total_pnl_pct,
        bars_per_year=int(_bars_per_year(timeframe)),
        equity_curve=equity_curve_pct,
        runner_label="Kronos (exploratory, pretrain-leakage suspected)",
        verdict_override=VERDICT_RAW_PRETRAIN_LEAKAGE,
    )

    # Inject trades as plain dicts so the dashboard json.dumps(..., default=str)
    # serializes structured records (NOT '_TradeRecord(...)' string reprs).
    # Tests inspect entry/exit prices via dict keys.
    envelope["trades"] = [asdict(t) for t in trades]

    return envelope
