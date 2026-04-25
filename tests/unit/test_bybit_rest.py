"""Tests for BybitRESTClient (pybit wrapper)."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from src.marketdata.bybit.rest import BybitRESTClient
from src.marketdata.models import Bar, DataQuality


@pytest.fixture
def mock_http_cls() -> MagicMock:
    """Mock pybit.unified_trading.HTTP class."""
    cls = MagicMock()
    instance = MagicMock()
    cls.return_value = instance
    return cls


def test_client_init_passes_credentials(mock_http_cls: MagicMock) -> None:
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        _ = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
    mock_http_cls.assert_called_once_with(testnet=True, api_key="k", api_secret="s")


def test_get_server_time_returns_utc_datetime(mock_http_cls: MagicMock) -> None:
    # V5 response: timeSecond string + timeNano string
    mock_http_cls.return_value.get_server_time.return_value = {
        "retCode": 0,
        "result": {"timeSecond": "1745193600", "timeNano": "1745193600123456789"},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        ts = client.get_server_time()

    assert ts.tzinfo is UTC
    assert ts == datetime(2025, 4, 21, 0, 0, 0, tzinfo=UTC)


def test_get_server_time_raises_on_non_zero_retcode(mock_http_cls: MagicMock) -> None:
    mock_http_cls.return_value.get_server_time.return_value = {
        "retCode": 10002,
        "retMsg": "request expired",
        "result": {},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        with pytest.raises(RuntimeError, match="retCode=10002"):
            client.get_server_time()


def test_get_filters_parses_via_BybitFilters(mock_http_cls: MagicMock) -> None:
    mock_http_cls.return_value.get_instruments_info.return_value = {
        "retCode": 0,
        "result": {
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "lotSizeFilter": {
                        "basePrecision": "0.000001",
                        "quotePrecision": "0.00000001",
                        "minOrderQty": "0.000048",
                        "maxOrderQty": "71.73956243",
                        "minOrderAmt": "1",
                        "maxOrderAmt": "4000000",
                    },
                    "priceFilter": {"tickSize": "0.01"},
                }
            ]
        },
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        f = client.get_filters("BTCUSDT")
    assert f.symbol == "BTCUSDT"
    assert f.tick_size == Decimal("0.01")


def _kline_row(
    t_ms: int,
    o: str = "60000",
    h: str = "60100",
    lo: str = "59900",
    c: str = "60050",
    v: str = "1.0",
    turnover: str = "60050",
) -> list[str]:
    """V5 kline row shape: [startTime, open, high, low, close, volume, turnover]."""
    return [str(t_ms), o, h, lo, c, v, turnover]


def test_get_klines_single_page(mock_http_cls: MagicMock) -> None:
    start_ms = 1745193600000  # 2025-04-21 00:00:00 UTC
    rows = [_kline_row(start_ms + i * 3_600_000) for i in range(3)]
    # Bybit returns newest-first in `list`; we reverse internally
    mock_http_cls.return_value.get_kline.return_value = {
        "retCode": 0,
        "result": {"list": list(reversed(rows))},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        bars = client.get_klines(
            symbol="BTCUSDT",
            interval="60",
            start_ms=start_ms,
            end_ms=start_ms + 3 * 3_600_000,
        )
    assert len(bars) == 3
    assert all(isinstance(b, Bar) for b in bars)
    assert bars[0].open == Decimal("60000")
    assert bars[0].symbol == "BTCUSDT"
    assert bars[0].interval == "1h"
    assert bars[0].data_quality is DataQuality.OK
    # Ascending by close_time
    assert bars[0].close_time < bars[1].close_time < bars[2].close_time


def test_get_klines_paginates_over_1000_limit(mock_http_cls: MagicMock) -> None:
    """Bybit max 1000 rows per call; 2400 bars → 3 calls (backward pagination).

    Bybit V5 is end-anchored: each call returns 1000 newest bars before cur_end.
    Mock simulates this: returns 1000 bars ending at cur_end (exclusive).
    """
    start_ms = 1745193600000
    step_ms = 3_600_000
    total_bars = 2400
    end_ms = start_ms + total_bars * step_ms
    call_count = 0

    def fake_get_kline(**kwargs: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        cur_end = int(kwargs["end"])  # type: ignore[arg-type]
        # End-anchored: return 1000 newest bars strictly before cur_end
        end_idx = (cur_end - start_ms) // step_ms  # exclusive index
        batch_size = min(1000, end_idx)
        start_idx = end_idx - batch_size
        rows = [_kline_row(start_ms + i * step_ms) for i in range(start_idx, end_idx)]
        return {"retCode": 0, "result": {"list": list(reversed(rows))}}

    mock_http_cls.return_value.get_kline.side_effect = fake_get_kline
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        bars = client.get_klines(
            symbol="BTCUSDT",
            interval="60",
            start_ms=start_ms,
            end_ms=end_ms,
        )
    assert call_count == 3
    assert len(bars) == 2400


def test_get_klines_paginates_backward_for_large_range(mock_http_cls: MagicMock) -> None:
    """T3 BUG FIX (S13): pagination must walk backward from end_ms.

    Bybit V5 API end-anchored: each call returns 1000 newest bars before end_ms.
    For range > 1000 bars, must decrement cur_end к oldest_in_batch per batch
    until oldest covers start_ms.
    """
    base_open_ms = 1_700_000_000_000
    step_ms = 3_600_000
    total_bars = 2500
    start_ms = base_open_ms
    end_ms = base_open_ms + total_bars * step_ms

    call_count = 0

    def fake_get_kline(**kwargs: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        cur_end = int(kwargs["end"])  # type: ignore[arg-type]
        end_idx = (cur_end - base_open_ms) // step_ms
        batch_size = min(1000, end_idx)
        start_idx = max(0, end_idx - batch_size)
        rows = [
            [str(base_open_ms + i * step_ms), "100.0", "101.0", "99.0", "100.5", "1.0", "100.5"]
            for i in range(start_idx, end_idx)
        ]
        return {"retCode": 0, "result": {"list": list(reversed(rows))}}

    mock_http_cls.return_value.get_kline.side_effect = fake_get_kline
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        bars = client.get_klines(
            symbol="BTCUSDT",
            interval="60",
            start_ms=start_ms,
            end_ms=end_ms,
            limit_per_call=1000,
        )

    # Should fetch all 2500 bars across 3 batches
    assert len(bars) == 2500, f"Expected 2500 bars, got {len(bars)}"
    assert call_count == 3, f"Expected 3 API calls, got {call_count}"
    # Verify oldest-first ordering
    for i in range(1, len(bars)):
        assert bars[i].open_time > bars[i - 1].open_time


def test_get_klines_excludes_end_ms_boundary(mock_http_cls: MagicMock) -> None:
    """Contract is [start_ms, end_ms); a bar with open_time == end_ms must be dropped."""
    start_ms = 1745193600000
    step = 3_600_000
    # Bybit V5 `end` is inclusive — simulate it returning the boundary row.
    rows = [_kline_row(start_ms + i * step) for i in range(4)]  # includes end_ms
    mock_http_cls.return_value.get_kline.return_value = {
        "retCode": 0,
        "result": {"list": list(reversed(rows))},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        bars = client.get_klines(
            symbol="BTCUSDT",
            interval="60",
            start_ms=start_ms,
            end_ms=start_ms + 3 * step,  # exclusive — bar at index 3 must be dropped
        )
    assert len(bars) == 3
    assert all(int(b.open_time.timestamp() * 1000) < start_ms + 3 * step for b in bars)
