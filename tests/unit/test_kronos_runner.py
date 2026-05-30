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

    n = 10
    base_close = 50_000.0

    # Craft opens: open[3] = 1234.0, open[4] = 9999.0 — clearly distinguishable
    opens = [base_close * 0.999] * n
    opens[3] = 1234.0
    opens[4] = 9999.0

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
    # Bar 3: predict close > current_close * (1 + threshold) -> ENTRY signal
    # threshold default = 0.0025; current_close = 50_000 -> need pred > 50_125
    _populate_cache(cache, bar_idx=3, pred_close=Decimal("55000.0"))

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


# ---------------------------------------------------------------------------
# Test 6: cache-hit entry + exit round trip
# ---------------------------------------------------------------------------


def test_run_kronos_exploratory_entry_and_exit_round_trip(tmp_path: Path) -> None:
    """An entry at bar i followed by an exit signal at bar j produces one closed trade."""
    from src.backtest.kronos_runner import run_kronos_exploratory

    n = 15
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
    # Bar 3: strong upside prediction -> ENTRY_LONG_KRONOS
    _populate_cache(cache, bar_idx=3, pred_close=Decimal("55000.0"))
    # Bar 7: prediction below current close -> EXIT_FLAT_KRONOS
    _populate_cache(cache, bar_idx=7, pred_close=Decimal("45000.0"))

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
