"""Tests for BybitRESTClient (pybit wrapper)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from src.marketdata.bybit.rest import BybitRESTClient


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
    from decimal import Decimal

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
