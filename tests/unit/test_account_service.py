"""S48 T3 — Bybit balance wrapper с graceful degradation (architect C1 BINDING)."""

from __future__ import annotations

import logging
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from src.dashboard import account_service
from src.dashboard.account_service import get_account_balance


@pytest.fixture(autouse=True)
def _reset_cache_between_tests() -> None:
    """H3 (S49) — clear TTL cache + adapter singleton before each test for isolation."""
    account_service._reset_balance_cache()


def _make_wallet_snapshot(balance: str = "10247.83") -> MagicMock:
    """Helper: mock WalletSnapshot with wallet_balance Decimal."""
    snap = MagicMock()
    snap.wallet_balance = Decimal(balance)
    return snap


def test_balance_success_path() -> None:
    """Real Bybit response → returns total_equity_usdt."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.return_value = _make_wallet_snapshot("10247.83")
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "bybit_v5"
    assert result["total_equity_usdt"] == 10247.83
    assert "fetched_at_iso" in result
    assert result.get("error") is None


def test_balance_no_keys_fallback() -> None:
    """Missing API keys → fallback $10000 с error message."""
    with patch("src.dashboard.account_service._get_adapter", return_value=None):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert result["error"] == "no_api_keys"


def test_balance_bybit_error_fallback() -> None:
    """Bybit API exception → fallback $10000 с sanitized error token.

    H2.4 (S49) — raw exc (may carry request context / signature) MUST NOT leak
    to client. error field == sanitized "fetch_failed" token; full exc → logger only.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.side_effect = RuntimeError("403 invalid signature secret=abc")
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert result["error"] == "fetch_failed"
    # Raw exc content must NOT appear in the client-facing error field.
    assert "403" not in result["error"]
    assert "secret" not in result["error"]


def test_balance_error_does_not_leak_raw_exc(caplog: pytest.LogCaptureFixture) -> None:
    """H2.4 (S49) — full exc string still logged (operator diagnostics) but not returned."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.side_effect = RuntimeError("sensitive-context-XYZ")
    # Override conftest _silence_noisy_loggers (may raise this logger's level) for this test.
    logging.getLogger("src.dashboard.account_service").setLevel(logging.WARNING)
    with (
        caplog.at_level(logging.WARNING, logger="src.dashboard.account_service"),
        patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter),
    ):
        result = get_account_balance()
    assert result["error"] == "fetch_failed"
    # Full detail preserved in logs for the operator (extra={"error": str(exc)}).
    assert any("sensitive-context-XYZ" in str(getattr(rec, "error", "")) for rec in caplog.records)


def test_balance_malformed_response_fallback() -> None:
    """Bybit returns unexpected type → fallback (sanitized error)."""
    mock_adapter = MagicMock()
    # Return object without wallet_balance attr (AttributeError on access)
    bad_snap = MagicMock(spec=[])  # spec=[] means no attributes
    mock_adapter.get_wallet_balance.return_value = bad_snap
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert result["error"] == "fetch_failed"


def test_balance_ttl_cache_hit_within_window() -> None:
    """H3 (S49) — 2 calls within TTL → only 1 Bybit fetch (rate-limit guard)."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.return_value = _make_wallet_snapshot("12345.67")
    with patch(
        "src.dashboard.account_service._get_adapter", return_value=mock_adapter
    ) as get_adapter:
        first = get_account_balance()
        second = get_account_balance()
    assert first["total_equity_usdt"] == 12345.67
    # Second call served from cache → no extra Bybit fetch + no extra adapter build.
    assert mock_adapter.get_wallet_balance.call_count == 1
    assert get_adapter.call_count == 1
    assert second["total_equity_usdt"] == 12345.67
    assert second["source"] == "cached"


def test_balance_ttl_cache_expiry_refetches() -> None:
    """H3 (S49) — after TTL expiry → re-fetch from Bybit."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.return_value = _make_wallet_snapshot("100.0")
    fake_now = [1000.0]
    with (
        patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter),
        patch("src.dashboard.account_service.time.monotonic", side_effect=lambda: fake_now[0]),
    ):
        get_account_balance()  # t=1000 → fetch #1
        fake_now[0] = 1000.0 + account_service._BALANCE_TTL_SECONDS + 0.1  # past TTL
        get_account_balance()  # → fetch #2
    assert mock_adapter.get_wallet_balance.call_count == 2


def test_balance_fallback_not_cached() -> None:
    """H3 (S49) — fallback (no keys) must NOT poison the cache; later success re-fetches."""
    # First: no adapter → fallback, not cached.
    with patch("src.dashboard.account_service._get_adapter", return_value=None):
        first = get_account_balance()
    assert first["source"] == "fallback"
    # Then: adapter available → real fetch happens (cache not blocked by prior fallback).
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.return_value = _make_wallet_snapshot("777.0")
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        second = get_account_balance()
    assert second["source"] == "bybit_v5"
    assert second["total_equity_usdt"] == 777.0
