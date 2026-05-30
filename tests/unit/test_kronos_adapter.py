"""T2 Kronos adapter tests (Sprint 52 — C2 boundary Protocol + C6 Decimal cast).

Covers:
- MockKronosAdapter returns list[Decimal] of length == horizon, all elements Decimal.
- Determinism: identical input → identical output across calls.
- MockKronosAdapter satisfies the runtime_checkable KronosAdapter Protocol.
- KronosModelAdapter instantiation raises a clean ImportError (torch absent here),
  with the actionable `[ml]` extra message.
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
    with pytest.raises(ImportError) as exc_info:
        KronosModelAdapter(
            model_id="NeoQuasar/Kronos-mini",
            tokenizer_id="NeoQuasar/Kronos-Tokenizer-base",
        )
    assert "[ml]" in str(exc_info.value)
