"""S48 T3 — Bybit balance wrapper для dashboard (architect C1 BINDING).

Isolates pybit V5 dependency от FastAPI app.py — graceful degradation на
missing keys OR Bybit unavailability. Returns standardized dict с
source/value/error fields.

Architecture rationale: app.py НЕ должен напрямую import BybitMarketAdapter
(boundary violation). Wrapper provides intermediate layer:
1. Lazy init (адаптер создаётся при первом fetch, не на module import)
2. Graceful fallback (always returns valid dict, никогда raise)
3. Consistent contract для FastAPI endpoint (T4)

Real API notes (verified against src/execution/bybit/adapter.py):
- get_wallet_balance(*, coin: str) -> WalletSnapshot
- WalletSnapshot.wallet_balance: Decimal  (total held, incl. locked)
- BybitFilters required by BybitMarketAdapter but only used for order ops;
  dummy minimal values are safe for balance-only usage.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

FALLBACK_BALANCE_USDT: float = 10_000.0
_BALANCE_COIN = "USDT"


def _get_adapter() -> Any | None:
    """Lazy adapter instantiation. Returns None if API keys missing OR import fails.

    Patched в tests via mock; real path uses BybitMarketAdapter from execution layer.

    Returns:
        BybitMarketAdapter instance OR None если: no API keys в settings, OR
        adapter import/init failed (graceful degradation, never raises).
    """
    try:
        from src.execution.bybit.adapter import BybitMarketAdapter
        from src.marketdata.bybit.rest import BybitRESTClient
        from src.marketdata.filters import BybitFilters
        from src.platform.config import Settings

        settings = Settings()

        # Verify keys present (env vars BYBIT_API_KEY + BYBIT_API_SECRET)
        if not settings.bybit_api_key or not settings.bybit_api_secret:
            return None

        rest = BybitRESTClient(
            api_key=settings.bybit_api_key,
            api_secret=settings.bybit_api_secret,
            testnet=settings.testnet,
        )
        # BybitFilters required by constructor but only validated on order ops;
        # dummy values are safe for balance-only fetch.
        dummy_filters = BybitFilters(
            symbol="BTCUSDT",
            step_size=Decimal("0.000001"),
            tick_size=Decimal("0.01"),
            min_order_qty=Decimal("0.00001"),
            max_order_qty=Decimal("100"),
            min_order_amt=Decimal("1"),
        )
        return BybitMarketAdapter(rest=rest, filters=dummy_filters)
    except Exception as exc:  # noqa: BLE001
        logger.warning("bybit_adapter_init_failed", extra={"error": str(exc)})
        return None


def get_account_balance() -> dict[str, Any]:
    """Fetch total wallet balance USDT от Bybit V5 UNIFIED account.

    Returns:
        dict с keys:
        - source: "bybit_v5" | "fallback"
        - total_equity_usdt: float
        - fetched_at_iso: str (ISO 8601 UTC)
        - error: str | None (only set если source=fallback)
    """
    now_iso = datetime.now(UTC).isoformat()
    adapter = _get_adapter()

    if adapter is None:
        return {
            "source": "fallback",
            "total_equity_usdt": FALLBACK_BALANCE_USDT,
            "fetched_at_iso": now_iso,
            "error": "no_api_keys",
        }

    try:
        snapshot = adapter.get_wallet_balance(coin=_BALANCE_COIN)
        total_equity = float(snapshot.wallet_balance)
        return {
            "source": "bybit_v5",
            "total_equity_usdt": total_equity,
            "fetched_at_iso": now_iso,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("bybit_balance_fetch_failed", extra={"error": str(exc)})
        return {
            "source": "fallback",
            "total_equity_usdt": FALLBACK_BALANCE_USDT,
            "fetched_at_iso": now_iso,
            "error": str(exc),
        }
