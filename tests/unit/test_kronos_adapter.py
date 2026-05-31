"""T2 Kronos adapter tests (Sprint 52 — C2 boundary Protocol + C6 Decimal cast).

Covers:
- MockKronosAdapter returns list[Decimal] of length == horizon, all elements Decimal.
- Determinism: identical input → identical output across calls.
- MockKronosAdapter satisfies the runtime_checkable KronosAdapter Protocol.
- KronosModelAdapter instantiation raises a clean ImportError (torch/submodule absent
  here), with the two-step operator instruction (submodule init + `[ml]` extra).
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest
from src.ml.kronos_adapter import (
    KronosAdapter,
    KronosModelAdapter,
    MockKronosAdapter,
)


def _make_ohlcv_df(rows: int = 64) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with a 1h DatetimeIndex."""
    start = datetime(2025, 1, 1)
    index = pd.DatetimeIndex([start + timedelta(hours=i) for i in range(rows)])
    base = [100.0 + i for i in range(rows)]
    return pd.DataFrame(
        {
            "open": base,
            "high": [b + 1.0 for b in base],
            "low": [b - 1.0 for b in base],
            "close": [b + 0.5 for b in base],
            "volume": [1000.0 + i for i in range(rows)],
        },
        index=index,
    )


def test_mock_returns_list_of_decimal_length_horizon() -> None:
    df = _make_ohlcv_df()
    adapter = MockKronosAdapter()
    out = adapter.predict(df, lookback=32, horizon=3)

    assert isinstance(out, list)
    assert len(out) == 3
    for value in out:
        assert isinstance(value, Decimal)
        assert not isinstance(value, float)


def test_mock_horizon_one() -> None:
    df = _make_ohlcv_df()
    adapter = MockKronosAdapter()
    out = adapter.predict(df, lookback=32, horizon=1)
    assert len(out) == 1
    assert isinstance(out[0], Decimal)


def test_mock_is_deterministic() -> None:
    df = _make_ohlcv_df()
    adapter = MockKronosAdapter()
    first = adapter.predict(df, lookback=32, horizon=5)
    second = adapter.predict(df, lookback=32, horizon=5)
    assert first == second


def test_mock_satisfies_protocol() -> None:
    adapter = MockKronosAdapter()
    assert isinstance(adapter, KronosAdapter)


def test_model_adapter_raises_clean_importerror_without_torch() -> None:
    from src.ml.kronos_variant import KRONOS_MINI

    with pytest.raises(ImportError) as exc_info:
        KronosModelAdapter(variant=KRONOS_MINI)
    assert "[ml]" in str(exc_info.value)


def test_model_adapter_syspath_rolled_back_on_importerror() -> None:
    """After ImportError (torch absent) kronos_root must NOT remain in sys.path (FIX 2)."""
    import os
    import sys

    from src.ml import kronos_adapter as _ka_module
    from src.ml.kronos_variant import KRONOS_MINI

    # Compute the same kronos_root the adapter's __init__ will compute.
    kronos_root = os.path.normpath(
        os.path.join(os.path.dirname(_ka_module.__file__), "..", "..", "third_party", "kronos")
    )

    with pytest.raises(ImportError):
        KronosModelAdapter(variant=KRONOS_MINI)

    assert (
        kronos_root not in sys.path
    ), f"kronos_root leaked into sys.path after ImportError: {kronos_root}"


def test_model_adapter_accepts_variant_and_raises_two_step_hint() -> None:
    from src.ml.kronos_adapter import KronosModelAdapter
    from src.ml.kronos_variant import KRONOS_BASE

    # torch/Kronos absent here → __init__ must raise ImportError with the
    # two-step operator instruction (submodule init + pip install ml).
    with pytest.raises(ImportError) as exc:
        KronosModelAdapter(variant=KRONOS_BASE, device="cpu")
    msg = str(exc.value)
    assert "submodule" in msg.lower()
    assert "[ml]" in msg


# ---------------------------------------------------------------------------
# T8 / CC3: predict() call-contract guard (torch-free)
# ---------------------------------------------------------------------------


class _StandInPredictor:
    """Records kwargs passed to .predict() and returns a synthetic pred_df."""

    def __init__(self) -> None:
        self.recorded_kwargs: dict[str, object] = {}

    def predict(self, **kwargs: object) -> pd.DataFrame:
        self.recorded_kwargs = kwargs
        # Return a minimal DataFrame with a 'close' column (horizon=2 rows).
        return pd.DataFrame({"close": [100.5, 101.0]})


def _make_adapter_without_torch(
    temperature: float = 1.0,
    top_p: float = 0.9,
    sample_count: int = 20,
    max_context: int = 64,
) -> tuple["KronosModelAdapter", _StandInPredictor]:
    """Construct KronosModelAdapter bypassing the torch __init__."""
    from src.ml.kronos_adapter import KronosModelAdapter

    adapter: KronosModelAdapter = object.__new__(KronosModelAdapter)
    stand_in = _StandInPredictor()
    adapter._predictor = stand_in  # type: ignore[attr-defined]
    adapter._device = "cpu"  # type: ignore[attr-defined]
    adapter._max_context = max_context  # type: ignore[attr-defined]
    adapter._temperature = temperature  # type: ignore[attr-defined]
    adapter._top_p = top_p  # type: ignore[attr-defined]
    adapter._sample_count = sample_count  # type: ignore[attr-defined]
    return adapter, stand_in


def test_predict_forwards_correct_kwargs_to_predictor() -> None:
    """Lock the call contract: predict() must forward exactly the real Kronos API kwargs."""
    adapter, stand_in = _make_adapter_without_torch(
        temperature=1.0, top_p=0.9, sample_count=20, max_context=8
    )

    # Build a tiny OHLCV DataFrame with at least 2 rows (need interval inference).
    start = datetime(2025, 1, 1)
    index = pd.DatetimeIndex([start + timedelta(hours=i) for i in range(10)])
    df = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(10)],
            "high": [101.0 + i for i in range(10)],
            "low": [99.0 + i for i in range(10)],
            "close": [100.5 + i for i in range(10)],
            "volume": [1000.0 + i for i in range(10)],
        },
        index=index,
    )

    horizon = 2
    result = adapter.predict(df, lookback=8, horizon=horizon)

    # Verify call contract: exactly these kwargs, no extras.
    kw = stand_in.recorded_kwargs
    expected_keys = {"df", "x_timestamp", "y_timestamp", "pred_len", "T", "top_p", "sample_count"}
    assert set(kw.keys()) == expected_keys, f"Unexpected kwargs: {set(kw.keys()) ^ expected_keys}"

    # Scalar params forwarded from adapter fields.
    assert kw["pred_len"] == horizon
    assert kw["T"] == 1.0
    assert kw["top_p"] == 0.9
    assert kw["sample_count"] == 20

    # Timestamps MUST be pandas Series (Kronos `calc_time_stamps` uses the `.dt`
    # accessor — a DatetimeIndex has no `.dt` and raises). x_timestamp = last
    # max_context rows, y_timestamp = future horizon.
    assert isinstance(kw["x_timestamp"], pd.Series)
    assert isinstance(kw["y_timestamp"], pd.Series)
    assert len(kw["y_timestamp"]) == horizon  # type: ignore[arg-type]

    # Result: list[Decimal] read from pred_df["close"].
    assert isinstance(result, list)
    assert len(result) == horizon
    for val in result:
        assert isinstance(val, Decimal), f"Expected Decimal, got {type(val)}"

    # Values match the stand-in's close column.
    assert result[0] == Decimal(str(100.5))
    assert result[1] == Decimal(str(101.0))
