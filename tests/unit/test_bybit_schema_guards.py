"""S49 B2 BLOCKER — unguarded result.list access in kline loop + filters.

bybit-api-reviewer (S49 tech-audit) BLOCKER B2: rest.py kline loop and
filters.from_instruments_info accessed resp["result"]["list"][0] with no guard →
bare KeyError/IndexError on Bybit V5 schema shift or empty list. Route both sites
through a defensive guard that raises a typed BybitAPIError instead.
"""

from __future__ import annotations

import pytest
from src.marketdata.bybit.rest import BybitAPIError, _safe_extract_list
from src.marketdata.filters import BybitFilters

# --- helper guard ---


def test_safe_extract_list_happy_path() -> None:
    resp = {"result": {"list": [{"a": 1}]}}
    assert _safe_extract_list(resp, "ctx") == [{"a": 1}]


def test_safe_extract_list_missing_result_raises_typed() -> None:
    with pytest.raises(BybitAPIError):
        _safe_extract_list({}, "ctx")


def test_safe_extract_list_list_not_array_raises_typed() -> None:
    with pytest.raises(BybitAPIError):
        _safe_extract_list({"result": {"list": "nope"}}, "ctx")


def test_safe_extract_list_empty_returns_empty_not_indexerror() -> None:
    assert _safe_extract_list({"result": {"list": []}}, "ctx") == []


# --- filters.from_instruments_info ---


def test_filters_empty_list_raises_typed_not_indexerror() -> None:
    """Empty result.list → typed error, not IndexError."""
    resp = {"retCode": 0, "result": {"list": []}}
    with pytest.raises((BybitAPIError, ValueError)):
        BybitFilters.from_instruments_info(resp)


def test_filters_missing_result_raises_typed_not_keyerror() -> None:
    """Missing result key → typed error, not KeyError."""
    resp = {"retCode": 0}
    with pytest.raises((BybitAPIError, ValueError)):
        BybitFilters.from_instruments_info(resp)


# --- rest.get_klines loop (empty list = graceful break, not IndexError) ---


class _FakeHTTP:
    def __init__(self, resp: dict) -> None:
        self._resp = resp

    def get_kline(self, **_kwargs) -> dict:
        return self._resp


def _make_client(resp: dict):
    from src.marketdata.bybit.rest import BybitRESTClient

    client = BybitRESTClient.__new__(BybitRESTClient)
    client._http = _FakeHTTP(resp)  # type: ignore[attr-defined]
    return client


def test_get_klines_empty_list_breaks_gracefully() -> None:
    """Empty list in a successful response → loop breaks, returns [] (no IndexError)."""
    client = _make_client({"retCode": 0, "result": {"list": []}})
    bars = client.get_klines("BTCUSDT", "60", start_ms=1_000_000, end_ms=2_000_000)
    assert bars == []


def test_get_klines_missing_list_key_raises_typed() -> None:
    """Missing 'list' key on a retCode==0 response → typed BybitAPIError, not KeyError."""
    client = _make_client({"retCode": 0, "result": {}})
    with pytest.raises(BybitAPIError):
        client.get_klines("BTCUSDT", "60", start_ms=1_000_000, end_ms=2_000_000)
