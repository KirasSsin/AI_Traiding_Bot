"""S52 T6 — kronos_runner.py unit tests (TDD RED -> GREEN).

Verifies:
  1. run_kronos_exploratory() returns an envelope with
     verdict == "RAW_PRETRAIN_LEAKAGE_SUSPECTED" and acceptance_gate == None.
  2. run_research_wfa is NOT called (monkeypatched to raise if invoked).
  3. No cross_trial_sharpes registration occurs (CrossTrialLog.append_trial must
     not be called — asserted via monkeypatch/spy).
  4. Cache-replay correctness: trades occur on NEXT-bar open (open[i+1]) — a
     fixture where same-bar vs next-bar fill differ proves the invariant.
  5. Cache-miss bars produce no trades and no crash.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from src.backtest.research_runner_envelope import VERDICT_RAW_PRETRAIN_LEAKAGE
from src.ml.prediction_cache import CacheKey, PredictionCache

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_SYMBOL = "BTCUSDT"
_TF = "1h"
_MODEL_ID = "kronos-mini"
_WEIGHTS_HASH = "aabbcc"
_PARAMS_HASH = "ddeeff"
_DEVICE = "cpu"

_BASE_TS = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
_BAR_INTERVAL_SEC = 3600  # 1 h


def _close_ts_for_df_row(row_idx: int) -> int:
    """Return unix timestamp for the close_time of the bar at DataFrame row_idx.

    _build_bar_from_row sets open_time = _ts[row_idx] = BASE + row_idx*3600 and
    close_time = open_time + 1h = BASE + (row_idx+1)*3600.  The cache key uses
    bar.close_time.timestamp(), so we must populate with (row_idx+1) offset.
    """
    return _BASE_TS + (row_idx + 1) * _BAR_INTERVAL_SEC


def _make_cache_key_for_row(row_idx: int) -> CacheKey:
    """Return the CacheKey that will be looked up when on_bar processes row_idx."""
    return CacheKey(
        model_id=_MODEL_ID,
        weights_hash=_WEIGHTS_HASH,
        symbol=_SYMBOL,
        timeframe=_TF,
        bar_close_ts=_close_ts_for_df_row(row_idx),
        params_hash=_PARAMS_HASH,
        device=_DEVICE,
    )


def _populate_cache(
    cache: PredictionCache,
    bar_idx: int,
    pred_close: Decimal,
) -> None:
    """Write a single-step prediction so that the signal fires at DataFrame row bar_idx."""
    cache.put(_make_cache_key_for_row(bar_idx), [pred_close])


def _make_ohlcv_df(
    n: int,
    base_close: float = 50_000.0,
    base_open: float = 49_950.0,
) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with n rows (1H bars starting 2024-01-01).

    Column ``_ts`` (UTC datetime) mirrors the parquet-normalized form used by
    existing runners.  ``open``, ``close`` are flat for simplicity.
    """
    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    return pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": [float(base_open)] * n,
            "high": [float(base_close) * 1.002] * n,
            "low": [float(base_open) * 0.998] * n,
            "close": [float(base_close)] * n,
            "volume": [100.0] * n,
        }
    )


def _make_kronos_params() -> dict[str, Any]:
    """Minimal params dict for run_kronos_exploratory."""
    return {
        "model_id": _MODEL_ID,
        "weights_hash": _WEIGHTS_HASH,
        "timeframe": _TF,
        "params_hash": _PARAMS_HASH,
        "device": _DEVICE,
    }


# ---------------------------------------------------------------------------
# Test 1: envelope shape + verdict
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_returns_envelope_verdict(tmp_path: Path) -> None:
    """Envelope has verdict RAW_PRETRAIN_LEAKAGE_SUSPECTED and acceptance_gate None."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    df = _make_ohlcv_df(20)
    cache = PredictionCache(tmp_path / "cache")

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    assert isinstance(result, dict), "must return dict"
    assert result["verdict"] == VERDICT_RAW_PRETRAIN_LEAKAGE
    assert result["acceptance_gate"] is None


def test_run_kronos_exploratory_envelope_keys(tmp_path: Path) -> None:
    """Envelope contains standard dashboard keys (mirrors existing runners)."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    df = _make_ohlcv_df(20)
    cache = PredictionCache(tmp_path / "cache")

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    for key in ("verdict", "acceptance_gate", "warnings", "n_trades", "metrics"):
        assert key in result, f"missing key: {key!r}"


def test_run_kronos_exploratory_pretrain_leakage_warning(tmp_path: Path) -> None:
    """Warnings list contains a pretrain_leakage chip (level==high)."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    df = _make_ohlcv_df(20)
    cache = PredictionCache(tmp_path / "cache")

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    warnings = result["warnings"]
    codes = [w["code"] for w in warnings]
    assert "pretrain_leakage" in codes, f"expected pretrain_leakage chip, got: {codes}"
    high_warnings = [w for w in warnings if w["code"] == "pretrain_leakage"]
    assert high_warnings[0]["level"] == "high"


# ---------------------------------------------------------------------------
# Test 2: run_research_wfa NOT called
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_does_not_call_wfa(tmp_path: Path) -> None:
    """run_research_wfa must not be called (exploratory-only path, V5)."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    df = _make_ohlcv_df(20)
    cache = PredictionCache(tmp_path / "cache")

    def _raise_if_called(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("run_research_wfa must NOT be called in kronos_runner")

    with (
        patch(
            "src.backtest.research_wfa.run_research_wfa",
            side_effect=_raise_if_called,
        ),
        patch(
            "src.backtest.kronos_runner.run_research_wfa",
            side_effect=_raise_if_called,
            create=True,  # allow patching even if not imported at module level
        ),
    ):
        result = run_kronos_exploratory(
            df=df,
            symbol=_SYMBOL,
            timeframe=_TF,
            params=_make_kronos_params(),
            cache=cache,
        )

    assert result["verdict"] == VERDICT_RAW_PRETRAIN_LEAKAGE


# ---------------------------------------------------------------------------
# Test 3: CrossTrialLog.append_trial NOT called
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_no_cross_trial_append(tmp_path: Path) -> None:
    """CrossTrialLog.append_trial must not be called (no formal N_trials)."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    df = _make_ohlcv_df(20)
    cache = PredictionCache(tmp_path / "cache")

    append_mock = MagicMock()
    with patch("src.analytics.cross_trial_log.CrossTrialLog.append_trial", append_mock):
        run_kronos_exploratory(
            df=df,
            symbol=_SYMBOL,
            timeframe=_TF,
            params=_make_kronos_params(),
            cache=cache,
        )

    append_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: look-ahead safety — fills use open[i+1], NOT open[i]
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_next_bar_fill(tmp_path: Path) -> None:
    """Fills must use open[i+1] (next bar open), not open[i] (same-bar look-ahead).

    Fixture: 10 bars.  Bar 3 (index 3) has a cached prediction above threshold
    -> ENTRY_LONG_KRONOS.  Bar open prices are all distinct and chosen so that
    same-bar (open[3] = 1234.0) and next-bar (open[4] = 9999.0) differ obviously.
    The first trade's entry_price should be derived from open[4], NOT open[3].
    """
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 20
    base_close = 50_000.0
    # Entry must fire AFTER the 14-bar Wilder-ATR warm-up (S53 T4 risk gate).
    entry_bar = 16

    # Craft opens: open[entry_bar] = 1234.0, open[entry_bar+1] = 9999.0 — distinguishable
    opens = [base_close * 0.999] * n
    opens[entry_bar] = 1234.0
    opens[entry_bar + 1] = 9999.0

    closes = [base_close] * n
    highs = [max(o, c) * 1.002 for o, c in zip(opens, closes, strict=False)]
    lows = [min(o, c) * 0.998 for o, c in zip(opens, closes, strict=False)]

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_fill")
    # entry_bar: predict close > current_close * (1 + threshold) -> ENTRY signal
    _populate_cache(cache, bar_idx=entry_bar, pred_close=Decimal("55000.0"))

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert (
        len(trades) >= 1
    ), f"Expected at least 1 trade from ENTRY signal on bar 3; got trades={trades}"
    first_trade = trades[0]
    entry_price = getattr(first_trade, "entry_price", None)
    if entry_price is None:
        entry_price = first_trade.get("entry_price") if isinstance(first_trade, dict) else None  # type: ignore[union-attr]

    assert entry_price is not None, "trade must have entry_price"
    # entry_price = open[4] * (1 + SLIPPAGE); open[4] = 9999.0 -> near 9999.0
    # same-bar fill would be near 1234.0 — clearly different
    assert abs(float(entry_price) - 1234.0) > 100.0, (
        f"entry_price {entry_price} looks like same-bar fill open[3]=1234.0 "
        "(look-ahead detected)"
    )
    assert abs(float(entry_price) - 9999.0) < 20.0, (
        f"entry_price {entry_price} should be near open[4]=9999.0 (next-bar fill) "
        "but got a different value"
    )


# ---------------------------------------------------------------------------
# Test 5: cache-miss bars produce no trades and no crash
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_cache_miss_no_trades(tmp_path: Path) -> None:
    """When the cache has no predictions, no trades occur and no exception is raised."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    df = _make_ohlcv_df(20)
    cache = PredictionCache(tmp_path / "cache_empty")
    # No cache.put() calls — all lookups miss.

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    assert result["n_trades"] == 0
    assert result["trades"] == []
    # S55 TQ-07 — 0-trade path: win_rate is internally nan but the envelope
    # COERCES it nan→0.0 (kronos_runner.py line ~313). Pin the coercion so a
    # regression that surfaced raw nan (breaks json + dashboard) would fail.
    assert result["win_rate"] == 0.0
    assert result["metrics"]["win_rate"] == 0.0
    # equity_pct never advances past its seed [0.0] → exposed curve is [0.0].
    assert result["equity_curve"]["equity_pct"] == [0.0]


# ---------------------------------------------------------------------------
# Test 6: cache-hit entry + exit round trip
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_entry_and_exit_round_trip(tmp_path: Path) -> None:
    """An entry at bar i followed by an exit signal at bar j produces one closed trade."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 30
    base_close = 50_000.0
    closes = [float(base_close)] * n
    opens = [float(base_close) * 0.999] * n
    highs = [float(base_close) * 1.002] * n
    lows = [float(base_close) * 0.998] * n

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_roundtrip")
    # Bar 16 (past the 14-bar ATR warm-up): strong upside prediction -> ENTRY_LONG_KRONOS
    _populate_cache(cache, bar_idx=16, pred_close=Decimal("55000.0"))
    # Bar 20: prediction below current close -> EXIT_FLAT_KRONOS
    _populate_cache(cache, bar_idx=20, pred_close=Decimal("45000.0"))

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert len(trades) >= 1, f"expected >= 1 trade from entry+exit signals, got {len(trades)}"
    assert result["n_trades"] >= 1


# ---------------------------------------------------------------------------
# Test 7: per-timeframe Sharpe annualization (FIX 2 — PHASE 6 R1)
# ---------------------------------------------------------------------------


def test_bars_per_year_differs_by_timeframe() -> None:
    """bars_per_year must be derived from the timeframe, not hardcoded to 1H.

    Expected values (365.25-day year = 31_557_600 seconds):
      1h  → 31_557_600 / 3600   = 8766  bars/year
      1d  → 31_557_600 / 86400  ≈  365.25 bars/year
      5m  → 31_557_600 / 300    = 105192 bars/year
    """
    from src.backtest.kronos_runner import _bars_per_year

    assert _bars_per_year("1h") == pytest.approx(8766.0, rel=1e-3)
    assert _bars_per_year("1d") == pytest.approx(365.25, rel=1e-3)
    assert _bars_per_year("5m") == pytest.approx(105192.0, rel=1e-3)
    # Ensure 5m ≠ 1h ≠ 1d (the fix: not all equal to 8766)
    assert abs(_bars_per_year("5m") - _bars_per_year("1h")) > 1000
    assert abs(_bars_per_year("1d") - _bars_per_year("1h")) > 1000


# ---------------------------------------------------------------------------
# Test 8: Bar.interval matches requested timeframe (FIX 3 — PHASE 6 R1)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test 9: trades serialize to dicts, not str repr (FIX C — PHASE 6 R2 / M1)
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_trades_are_dicts(tmp_path: Path) -> None:
    """envelope['trades'] must be a list of plain dicts (json-serializable structured),

    NOT a list of _TradeRecord dataclasses that json.dumps(default=str) turns into
    '_TradeRecord(...)' strings (broken contract). After a round-trip through
    json.dumps(..., default=str) + json.loads, each trade must still be a dict
    with float entry_price / exit_price / pnl_pct fields.
    """
    import json

    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 30
    base_close = 50_000.0
    closes = [float(base_close)] * n
    opens = [float(base_close) * 0.999] * n
    highs = [float(base_close) * 1.002] * n
    lows = [float(base_close) * 0.998] * n

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_dicts")
    # Bars past the 14-bar ATR warm-up (S53 T4 risk gate).
    _populate_cache(cache, bar_idx=16, pred_close=Decimal("55000.0"))
    _populate_cache(cache, bar_idx=20, pred_close=Decimal("45000.0"))

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result["trades"]
    assert isinstance(trades, list)
    assert len(trades) >= 1
    for t in trades:
        assert isinstance(t, dict), f"trade must be dict, got {type(t)}"
        assert "entry_price" in t and "exit_price" in t and "pnl_pct" in t

    # Round-trip through the dashboard serialization contract.
    serialized = json.dumps(result, default=str)
    reloaded = json.loads(serialized)
    reloaded_trades = reloaded["trades"]
    assert isinstance(reloaded_trades, list)
    for t in reloaded_trades:
        assert isinstance(t, dict), f"serialized trade must be dict, got {type(t)}: {t!r}"
        assert not str(t).startswith("_TradeRecord"), "trade was stringified to dataclass repr"


# ---------------------------------------------------------------------------
# Test 10: last-bar mark-to-market — open position closed at close[-1] * (1 - SLIPPAGE)
# (PHASE 6 R3)
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_last_bar_mark_to_market(tmp_path: Path) -> None:
    """An open position with no exit signal is closed at the final bar's mark-to-market.

    Formula (kronos_runner.py line 272): fill = close_arr[-1] * (1.0 - _SLIPPAGE)
    where _SLIPPAGE = 0.0005.

    Fixture:
    - 20 bars.  Bar 16 (past the 14-bar ATR warm-up) has an entry prediction.
    - No exit prediction on any subsequent bar.
    - Entry fill = open[17] * (1 + SLIPPAGE).
    - Exit (mark-to-market) fill = close[19] * (1 - SLIPPAGE).
    - Exactly 1 trade, exit_idx = n - 1 = 19.
    """
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 20
    entry_bar = 16  # past the 14-bar Wilder-ATR warm-up (S53 T4 risk gate)
    base_close = 50_000.0
    base_open = 49_900.0
    last_close = 51_000.0  # distinct from others to identify mark-to-market branch

    closes = [base_close] * (n - 1) + [last_close]
    opens = [base_open] * n
    highs = [max(o, c) * 1.001 for o, c in zip(opens, closes, strict=False)]
    lows = [min(o, c) * 0.999 for o, c in zip(opens, closes, strict=False)]

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    slippage = 0.0005  # mirrors kronos_runner._SLIPPAGE constant

    cache = PredictionCache(tmp_path / "cache_mtm")
    # entry_bar: strong upside prediction -> ENTRY_LONG_KRONOS.
    _populate_cache(cache, bar_idx=entry_bar, pred_close=Decimal("60000.0"))
    # No exit prediction afterwards -> position never explicitly closed -> mark-to-market.

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert len(trades) == 1, f"expected exactly 1 trade (mark-to-market), got {len(trades)}"

    trade = trades[0]
    exit_price = trade["exit_price"] if isinstance(trade, dict) else trade.exit_price
    expected_exit = last_close * (1.0 - slippage)
    assert (
        abs(float(exit_price) - expected_exit) < 0.01
    ), f"mark-to-market exit_price {exit_price} != close[-1]*(1-SLIPPAGE) = {expected_exit}"

    exit_idx = trade["exit_idx"] if isinstance(trade, dict) else trade.exit_idx
    assert exit_idx == n - 1, f"exit_idx must be {n - 1} (last bar), got {exit_idx}"


# ---------------------------------------------------------------------------
# Test 11: single-trade Sharpe — pnl_std==0 → sharpe=nan (PHASE 6 R3)
# (Actual code path: n_trades==1 → pnl_std=0.0 → else: float("nan") if pnl_std==0)
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_single_trade_sharpe_is_nan(tmp_path: Path) -> None:
    """With exactly 1 trade (pnl_std = 0 by construction), Sharpe is float('nan').

    Code path (kronos_runner.py):
      pnl_std = 0.0  (n_trades == 1, ddof=1 branch skipped)
      if pnl_std > 0 and mean_holding > 0: ...   <- False
      else: sharpe = float("nan") if pnl_std == 0 else 0.0  <- float("nan")

    The test verifies the ACTUAL behavior (nan), not an assumed finite value.
    ``math.isnan`` must return True and ``math.isfinite`` must return False.
    """
    import math

    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 30
    base_close = 50_000.0
    closes = [float(base_close)] * n
    opens = [float(base_close) * 0.999] * n
    highs = [float(base_close) * 1.002] * n
    lows = [float(base_close) * 0.998] * n

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_sharpe")
    # Bar 16 (past the 14-bar ATR warm-up): entry; bar 20: exit — one round-trip trade.
    _populate_cache(cache, bar_idx=16, pred_close=Decimal("55000.0"))
    _populate_cache(cache, bar_idx=20, pred_close=Decimal("45000.0"))

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert len(trades) == 1, f"expected exactly 1 trade, got {len(trades)}"

    sharpe = result["metrics"]["sharpe"]
    assert math.isnan(
        sharpe
    ), f"single-trade Sharpe (pnl_std=0) must be nan per code path, got {sharpe}"
    assert not math.isfinite(
        sharpe
    ), f"single-trade Sharpe must not be finite (pnl_std=0 → nan branch), got {sharpe}"


# ---------------------------------------------------------------------------
# Test 12: EXACT net-PnL value assertions (S55 TQ-06 — closes S27-class
# structure-not-value gap). Existing tests check trade COUNT / shape / fill
# LOCATION but NEVER the exact pnl_pct value, so a sign error, a missing 2x
# commission, or wrong-side slippage would pass every test.  These two cases
# pin the EXACT pnl_net per the code formula for both fill paths:
#   signal-exit:    fill = open[exit_idx] * (1 - SLIPPAGE)
#   mark-to-market: fill = close[-1]      * (1 - SLIPPAGE)
# with entry fill = open[entry_idx] * (1 + SLIPPAGE),
#      pnl_gross   = (fill - entry_price) / entry_price,
#      pnl_net     = pnl_gross - 2.0 * COMMISSION_TAKER.
# COMMISSION_TAKER = 0.001, SLIPPAGE = 0.0005 (kronos_runner module constants).
# ---------------------------------------------------------------------------

_COMMISSION_TAKER = 0.001  # mirrors src.backtest.kronos_runner._COMMISSION_TAKER
_SLIPPAGE = 0.0005  # mirrors src.backtest.kronos_runner._SLIPPAGE


def test_run_kronos_exploratory_pnl_exact_signal_exit(tmp_path: Path) -> None:
    """EXACT pnl_net for a signal-driven round trip (entry open[i+1], exit open[j+1]).

    Fixture: 30 flat-close bars (close = 50_000) so signals fire deterministically.
      - entry prediction at bar 16 -> entry fill at open[17] (distinct = 49_000)
      - exit  prediction at bar 20 -> exit  fill at open[21] (distinct = 53_000)
    Hand-computed expected (mirrors the EXACT code formula):
      entry_price = 49_000 * (1 + 0.0005) = 49_024.5
      exit_fill   = 53_000 * (1 - 0.0005) = 52_973.5
      pnl_gross   = (52_973.5 - 49_024.5) / 49_024.5
      pnl_net     = pnl_gross - 2 * 0.001
    """
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 30
    base_close = 50_000.0
    closes = [float(base_close)] * n
    opens = [float(base_close) * 0.999] * n  # flat baseline opens
    entry_fill_idx = 17  # open used for entry fill (entry signal at bar 16)
    exit_fill_idx = 21  # open used for exit fill  (exit signal at bar 20)
    opens[entry_fill_idx] = 49_000.0
    opens[exit_fill_idx] = 53_000.0
    highs = [max(o, c) * 1.002 for o, c in zip(opens, closes, strict=False)]
    lows = [min(o, c) * 0.998 for o, c in zip(opens, closes, strict=False)]

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_pnl_signal")
    _populate_cache(cache, bar_idx=16, pred_close=Decimal("55000.0"))  # ENTRY_LONG
    _populate_cache(cache, bar_idx=20, pred_close=Decimal("45000.0"))  # EXIT_FLAT

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert len(trades) == 1, f"expected exactly 1 round-trip trade, got {len(trades)}"
    trade = trades[0]
    pnl_pct = trade["pnl_pct"] if isinstance(trade, dict) else trade.pnl_pct

    entry_price = 49_000.0 * (1.0 + _SLIPPAGE)
    exit_fill = 53_000.0 * (1.0 - _SLIPPAGE)
    expected = (exit_fill - entry_price) / entry_price - 2.0 * _COMMISSION_TAKER

    assert abs(float(pnl_pct) - expected) < 1e-9, (
        f"signal-exit pnl_net {pnl_pct} != hand-computed {expected} "
        "(sign / 2x-commission / slippage-side regression)"
    )
    # Sanity: this trade is a +profit (exit > entry net of costs) — guards a sign flip.
    assert float(pnl_pct) > 0.0


def test_run_kronos_exploratory_pnl_exact_mark_to_market(tmp_path: Path) -> None:
    """EXACT pnl_net for the mark-to-market path (open entry, close[-1] exit).

    Fixture: 20 bars, entry prediction at bar 16, NO exit afterwards -> the open
    position is closed at the last bar's mark-to-market.
      - entry fill at open[17] (distinct = 49_900)
      - exit  fill at close[19] = close[-1] (distinct = 51_000)
    Hand-computed expected:
      entry_price = 49_900 * (1 + 0.0005) = 49_924.95
      exit_fill   = 51_000 * (1 - 0.0005) = 50_974.5
      pnl_net     = (exit_fill - entry_price) / entry_price - 2 * 0.001
    """
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 20
    entry_bar = 16
    base_close = 50_000.0
    last_close = 51_000.0
    closes = [base_close] * (n - 1) + [last_close]
    opens = [49_900.0] * n  # flat; only open[17] is used for the entry fill
    highs = [max(o, c) * 1.001 for o, c in zip(opens, closes, strict=False)]
    lows = [min(o, c) * 0.999 for o, c in zip(opens, closes, strict=False)]

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_pnl_mtm")
    _populate_cache(cache, bar_idx=entry_bar, pred_close=Decimal("60000.0"))  # ENTRY only

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert len(trades) == 1, f"expected exactly 1 mark-to-market trade, got {len(trades)}"
    trade = trades[0]
    pnl_pct = trade["pnl_pct"] if isinstance(trade, dict) else trade.pnl_pct

    entry_price = 49_900.0 * (1.0 + _SLIPPAGE)
    exit_fill = last_close * (1.0 - _SLIPPAGE)
    expected = (exit_fill - entry_price) / entry_price - 2.0 * _COMMISSION_TAKER

    assert abs(float(pnl_pct) - expected) < 1e-9, (
        f"mark-to-market pnl_net {pnl_pct} != hand-computed {expected} "
        "(sign / 2x-commission / slippage-side regression)"
    )
    assert float(pnl_pct) > 0.0


def test_run_kronos_exploratory_two_trades_win_rate_and_equity_curve(tmp_path: Path) -> None:
    """EXACT win_rate (0.5) + equity_curve_pct (cumulative ×100) for 2 closed trades.

    S55 TQ-07 — closes the S27-class gap: existing tests pin single-trade pnl by
    value but NEVER the multi-trade win_rate aggregate nor the cumulative
    equity_curve. A sign error in win_rate or a non-additive equity bug would
    pass every other test.

    Fixture: 30 flat-close bars (close = 50_000) so signals fire deterministically.
    The strategy FSM (TL-06) is FLAT→LONG→FLAT, so the predictions drive an
    ENTRY→EXIT→ENTRY→EXIT sequence → exactly 2 closed round trips:
      - Trade 1 (WINNER): entry signal bar 16 → fill open[17]=49_000;
                          exit  signal bar 20 → fill open[21]=53_000.
      - Trade 2 (LOSER):  entry signal bar 22 → fill open[23]=53_000;
                          exit  signal bar 24 → fill open[25]=49_000.
    Hand-computed (entry = open*(1+SLIPPAGE), exit = open*(1-SLIPPAGE),
    pnl_net = (exit-entry)/entry - 2*COMMISSION):
      pnl1 = +0.07855156095421677  (winner)
      pnl2 = -0.07839576438195997  (loser)
    → win_rate = 0.5; equity_curve_pct = [0, pnl1*100, (pnl1+pnl2)*100].
    """
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 30
    base_close = 50_000.0
    closes = [base_close] * n
    opens = [base_close * 0.999] * n  # flat baseline opens
    # Fill bars: entry signal at bar k → entry fill at open[k+1];
    #            exit  signal at bar k → exit  fill at open[k+1].
    opens[17] = 49_000.0  # trade 1 entry fill (signal bar 16)
    opens[21] = 53_000.0  # trade 1 exit  fill (signal bar 20)
    opens[23] = 53_000.0  # trade 2 entry fill (signal bar 22)
    opens[25] = 49_000.0  # trade 2 exit  fill (signal bar 24)
    highs = [max(o, c) * 1.002 for o, c in zip(opens, closes, strict=False)]
    lows = [min(o, c) * 0.998 for o, c in zip(opens, closes, strict=False)]

    tss = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "_ts": pd.to_datetime(tss, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )

    cache = PredictionCache(tmp_path / "cache_two_trades")
    # Bars past the 14-bar ATR warm-up. ENTRY: pred > close*(1+threshold);
    # EXIT: pred < close. FSM enforces alternation FLAT→LONG→FLAT.
    _populate_cache(cache, bar_idx=16, pred_close=Decimal("55000.0"))  # ENTRY 1
    _populate_cache(cache, bar_idx=20, pred_close=Decimal("45000.0"))  # EXIT 1
    _populate_cache(cache, bar_idx=22, pred_close=Decimal("55000.0"))  # ENTRY 2
    _populate_cache(cache, bar_idx=24, pred_close=Decimal("45000.0"))  # EXIT 2

    result = run_kronos_exploratory(
        df=df,
        symbol=_SYMBOL,
        timeframe=_TF,
        params=_make_kronos_params(),
        cache=cache,
    )

    trades = result.get("trades", [])
    assert len(trades) == 2, f"expected exactly 2 closed trades, got {len(trades)}"

    # Hand-compute pnl1/pnl2 from the EXACT code formula for both fill paths.
    entry1 = 49_000.0 * (1.0 + _SLIPPAGE)
    exit1 = 53_000.0 * (1.0 - _SLIPPAGE)
    pnl1 = (exit1 - entry1) / entry1 - 2.0 * _COMMISSION_TAKER
    entry2 = 53_000.0 * (1.0 + _SLIPPAGE)
    exit2 = 49_000.0 * (1.0 - _SLIPPAGE)
    pnl2 = (exit2 - entry2) / entry2 - 2.0 * _COMMISSION_TAKER
    assert pnl1 > 0.0, "fixture invariant: trade 1 must be a winner"
    assert pnl2 < 0.0, "fixture invariant: trade 2 must be a loser"

    # win_rate = (pnls > 0).mean() = 1 winner / 2 trades = 0.5 (no nan coercion here).
    assert result["win_rate"] == pytest.approx(0.5, abs=1e-9)
    assert result["metrics"]["win_rate"] == pytest.approx(0.5, abs=1e-9)

    # equity_curve_pct = cumulative additive pnl_net ×100, seeded with 0.0.
    equity_pct = result["equity_curve"]["equity_pct"]
    expected_equity = [0.0, pnl1 * 100.0, (pnl1 + pnl2) * 100.0]
    assert equity_pct == pytest.approx(expected_equity, abs=1e-9), (
        f"equity_curve_pct {equity_pct} != cumulative ×100 {expected_equity} "
        "(non-additive / wrong-scale / missing-seed regression)"
    )


def test_build_bar_from_row_interval_matches_timeframe() -> None:
    """_build_bar_from_row must set bar.interval = timeframe, not hard-coded '1h'."""

    import pandas as pd
    from src.backtest.kronos_runner import _build_bar_from_row

    row = pd.Series(
        {
            "_ts": pd.Timestamp("2024-01-01 00:00:00", tz="UTC"),
            "open": 50000.0,
            "high": 50100.0,
            "low": 49900.0,
            "close": 50050.0,
            "volume": 100.0,
        }
    )

    bar_1h = _build_bar_from_row(row, symbol="BTCUSDT", timeframe="1h")
    assert bar_1h.interval == "1h"

    bar_5m = _build_bar_from_row(row, symbol="BTCUSDT", timeframe="5m")
    assert bar_5m.interval == "5m"

    bar_1d = _build_bar_from_row(row, symbol="BTCUSDT", timeframe="1d")
    assert bar_1d.interval == "1d"

    bar_4h = _build_bar_from_row(row, symbol="BTCUSDT", timeframe="4h")
    assert bar_4h.interval == "4h"
