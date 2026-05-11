"""S47 T10 — bybit adapter defensive response shape guards (M2)."""

from __future__ import annotations

import pytest
from src.execution.bybit.adapter import _safe_extract_list, _safe_extract_list_or_empty
from src.execution.bybit.errors import BybitAdapterError


def test_safe_extract_list_happy_path() -> None:
    resp = {"result": {"list": [{"orderId": "1"}, {"orderId": "2"}]}}
    assert _safe_extract_list(resp, "test") == [{"orderId": "1"}, {"orderId": "2"}]


def test_safe_extract_list_missing_result() -> None:
    with pytest.raises(BybitAdapterError, match="missing 'result' dict для test_ctx"):
        _safe_extract_list({}, "test_ctx")


def test_safe_extract_list_result_not_dict() -> None:
    with pytest.raises(BybitAdapterError, match="missing 'result' dict для test_ctx"):
        _safe_extract_list({"result": "not_dict"}, "test_ctx")


def test_safe_extract_list_list_missing() -> None:
    with pytest.raises(BybitAdapterError, match="'result.list' not list для test_ctx"):
        _safe_extract_list({"result": {}}, "test_ctx")


def test_safe_extract_list_list_not_array() -> None:
    with pytest.raises(BybitAdapterError, match="'result.list' not list для test_ctx"):
        _safe_extract_list({"result": {"list": "not_a_list"}}, "test_ctx")


# --- _safe_extract_list_or_empty (listing endpoints: no list key = empty, not error) ---


def test_safe_extract_list_or_empty_happy_path() -> None:
    resp = {"result": {"list": [{"orderId": "1"}]}}
    assert _safe_extract_list_or_empty(resp, "test") == [{"orderId": "1"}]


def test_safe_extract_list_or_empty_list_key_absent_returns_empty() -> None:
    """Bybit may omit list key entirely when no results — treat as empty list."""
    assert _safe_extract_list_or_empty({"result": {}}, "test_ctx") == []


def test_safe_extract_list_or_empty_missing_result_raises() -> None:
    with pytest.raises(BybitAdapterError, match="missing 'result' dict для test_ctx"):
        _safe_extract_list_or_empty({}, "test_ctx")


def test_safe_extract_list_or_empty_list_not_array_raises() -> None:
    with pytest.raises(BybitAdapterError, match="'result.list' not list для test_ctx"):
        _safe_extract_list_or_empty({"result": {"list": 42}}, "test_ctx")
