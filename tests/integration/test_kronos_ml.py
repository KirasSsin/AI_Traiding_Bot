"""S52 T9 — opt-in RUN_ML=1 Kronos real-inference integration test (C5).

Gated by ``RUN_ML=1`` env var + ``@pytest.mark.integration`` marker.

Default ``pytest`` run (no RUN_ML, no ``-m integration``) SKIPS this test
entirely.  torch is NEVER imported at collection time — the import lives
inside the test body behind the skip guard.

Operator instructions (Mac M4 Pro, MPS):
  1. pip install -e ".[ml]"
  2. RUN_ML=1 .venv/bin/pytest tests/integration/test_kronos_ml.py -v -m integration

CI safety: CI never sets RUN_ML and never installs ``.[ml]``, so torch is
absent and this test is always skipped there.  The CI pytest command
(``pytest tests/ -q --ignore=tests/integration``) additionally ignores the
whole integration directory, providing a double guard.

HONEST DISCLAIMER (ADR 0068 GATE 0):
  BTC/USDT confirmed in Kronos pretraining corpus.  Backtest results carry
  verdict VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED and are EXPLORATORY ONLY.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_ML") != "1",
        reason="Kronos real-inference test opt-in via RUN_ML=1 (requires torch + [ml] extra)",
    ),
]

# ---------------------------------------------------------------------------
# Real-inference test
# ---------------------------------------------------------------------------


def test_kronos_model_adapter_predict_returns_decimal_list() -> None:
    """Instantiate real KronosModelAdapter (mini, mps) + predict on synthetic OHLCV.

    Asserts:
    - predict() returns list[Decimal] of length == horizon.
    - All returned values are Decimal instances.
    - All returned prices are positive.

    Kept small (horizon=1, lookback=8, tiny synthetic df) — real model
    inference is slow on first call; subsequent calls are faster after warm-up.
    """
    # torch import is INSIDE the test body so collection is always torch-free.
    from decimal import Decimal  # noqa: PLC0415

    import pandas as pd  # noqa: PLC0415 — deferred to avoid collection-time torch pull
    from src.ml.kronos_adapter import KronosModelAdapter  # noqa: PLC0415
    from src.ml.kronos_variant import KRONOS_BASE  # noqa: PLC0415

    horizon = 1
    lookback = 8

    # Build a tiny synthetic OHLCV DataFrame (12 bars of synthetic BTC prices).
    timestamps = pd.date_range("2024-01-01", periods=12, freq="1h", tz="UTC")
    base_price = 40_000.0
    prices = [base_price + i * 10.0 for i in range(12)]
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p + 50.0 for p in prices],
            "low": [p - 50.0 for p in prices],
            "close": [p + 5.0 for p in prices],
            "volume": [100.0] * 12,
        },
        index=timestamps,
    )

    adapter = KronosModelAdapter(
        variant=KRONOS_BASE,
        device="mps",
        temperature=1.0,
        top_p=0.9,
        sample_count=1,
    )

    result = adapter.predict(df, lookback=lookback, horizon=horizon)

    assert isinstance(result, list), f"predict() must return list, got {type(result)}"
    assert len(result) == horizon, f"Expected {horizon} predictions, got {len(result)}"
    for i, val in enumerate(result):
        assert isinstance(
            val, Decimal
        ), f"Element {i} is {type(val)}, expected Decimal (C6 boundary)"
        assert val > Decimal("0"), f"Predicted price at step {i} must be positive, got {val}"


def test_kronos_runner_exploratory_end_to_end_verdict() -> None:
    """Build a tiny PredictionCache + run run_kronos_exploratory end-to-end.

    Asserts that the verdict is VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED
    (hard-pinned per ESC-1=A / V5 contract in kronos_runner.py).

    Uses MockKronosAdapter to pre-populate the cache so this test does NOT
    require real model weights — it only verifies the cache-replay path and
    end-to-end envelope contract.  (Real model inference is covered by the
    adapter test above.)
    """
    import tempfile  # noqa: PLC0415 — deferred
    from datetime import timedelta  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import pandas as pd  # noqa: PLC0415
    from src.backtest.kronos_runner import run_kronos_exploratory  # noqa: PLC0415
    from src.backtest.research_runner_envelope import (  # noqa: PLC0415
        VERDICT_RAW_PRETRAIN_LEAKAGE,
    )
    from src.ml.kronos_adapter import MockKronosAdapter  # noqa: PLC0415
    from src.ml.prediction_cache import (  # noqa: PLC0415
        CacheKey,
        PredictionCache,
        hash_params,
    )

    model_id = "test-mock-model"
    weights_hash = "mock_weights_hash_0000"
    symbol = "BTCUSDT"
    timeframe = "1h"
    device = "cpu"
    horizon = 1

    sampling_params: dict[str, object] = {
        "T": 1.0,
        "top_p": 0.9,
        "sample_count": 1,
        "horizon": horizon,
        "seed": 42,
    }
    params_hash = hash_params(sampling_params)

    # Build a small synthetic OHLCV df (20 bars).
    timestamps = pd.date_range("2024-01-01", periods=20, freq="1h", tz="UTC")
    base = 40_000.0
    prices = [base + i * 10.0 for i in range(20)]
    df = pd.DataFrame(
        {
            "_ts": timestamps,
            "open": prices,
            "high": [p + 50.0 for p in prices],
            "low": [p - 50.0 for p in prices],
            "close": [p + 5.0 for p in prices],
            "volume": [100.0] * 20,
        }
    )

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        cache = PredictionCache(cache_dir)
        mock_adapter = MockKronosAdapter()

        # Pre-populate the cache for every bar using the mock adapter.
        td = timedelta(hours=1)
        for _, row in df.iterrows():
            open_time = pd.Timestamp(row["_ts"]).to_pydatetime()
            bar_close_ts = int((open_time + td).timestamp())
            key = CacheKey(
                model_id=model_id,
                weights_hash=weights_hash,
                symbol=symbol,
                timeframe=timeframe,
                bar_close_ts=bar_close_ts,
                params_hash=params_hash,
                device=device,
            )
            context_df = df[df["_ts"] <= row["_ts"]].rename(columns={"_ts": "ts"}).set_index("ts")
            pred = mock_adapter.predict(context_df, lookback=64, horizon=horizon)
            cache.put(key, pred)

        result = run_kronos_exploratory(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            params={
                "model_id": model_id,
                "weights_hash": weights_hash,
                "params_hash": params_hash,
                "device": device,
                "threshold": "0.0001",  # very small to trigger trades from mock drift
            },
            cache=cache,
        )

    assert (
        result["verdict"] == VERDICT_RAW_PRETRAIN_LEAKAGE
    ), f"Expected {VERDICT_RAW_PRETRAIN_LEAKAGE!r}, got {result['verdict']!r}"
    assert result["acceptance_gate"] is None, "Non-gating verdict must have acceptance_gate=None"
