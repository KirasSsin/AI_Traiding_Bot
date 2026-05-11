"""S48 T3 — Bybit balance wrapper с graceful degradation (architect C1 BINDING)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.dashboard.account_service import get_account_balance


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
    """Bybit API exception → fallback $10000 с error reason."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.side_effect = RuntimeError("403 invalid signature")
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert "403 invalid signature" in result["error"]


def test_balance_malformed_response_fallback() -> None:
    """Bybit returns unexpected type → fallback."""
    mock_adapter = MagicMock()
    # Return object without wallet_balance attr (AttributeError on access)
    bad_snap = MagicMock(spec=[])  # spec=[] means no attributes
    mock_adapter.get_wallet_balance.return_value = bad_snap
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert result["error"] is not None
