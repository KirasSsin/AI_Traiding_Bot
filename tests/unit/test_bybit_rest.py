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
