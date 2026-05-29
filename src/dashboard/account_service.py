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
import threading
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

FALLBACK_BALANCE_USDT: float = 10_000.0
_BALANCE_COIN = "USDT"

# H3 (S49) — TTL cache + adapter singleton (Bybit rate-limit guard).
# Frontend may poll /api/bybit/balance; without a TTL every poll builds a fresh
# adapter + hits Bybit. Cache successful results for _BALANCE_TTL_SECONDS and
# reuse a single adapter instance across calls.
_BALANCE_TTL_SECONDS: float = 5.0
_cache_lock = threading.Lock()
_cached_adapter: Any | None = None
_cached_balance: dict[str, Any] | None = None
_cached_at_monotonic: float = 0.0


def _reset_balance_cache() -> None:
    """Test hook — clear cached adapter + balance (call from tests, not production)."""
    global _cached_adapter, _cached_balance, _cached_at_monotonic
    with _cache_lock:
        _cached_adapter = None
        _cached_balance = None
        _cached_at_monotonic = 0.0


def _get_cached_adapter() -> Any | None:
    """Return the singleton adapter, building it lazily on first use.

    Reuses one BybitMarketAdapter across calls (avoids rebuilding Settings + REST
    client per request). Returns None if keys missing / init failed (graceful).
    """
    global _cached_adapter
    with _cache_lock:
        if _cached_adapter is None:
            _cached_adapter = _get_adapter()
        return _cached_adapter


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

    H3 (S49) — serves a cached result within _BALANCE_TTL_SECONDS (rate-limit
    guard). Only successful Bybit fetches are cached; fallback results are NOT
    cached (so a transient failure does not block subsequent real fetches).

    Returns:
        dict с keys:
        - source: "bybit_v5" | "fallback" | "cached"
        - total_equity_usdt: float
        - fetched_at_iso: str (ISO 8601 UTC)
        - error: str | None (only set если source=fallback)
    """
    # Declared global at function top (read at TTL-hit check below precedes assignment).
    global _cached_balance, _cached_at_monotonic

    # H3 — TTL cache hit: return cached snapshot без Bybit call.
    with _cache_lock:
        if (
            _cached_balance is not None
            and (time.monotonic() - _cached_at_monotonic) < _BALANCE_TTL_SECONDS
        ):
            cached = dict(_cached_balance)
            cached["source"] = "cached"
            return cached

    now_iso = datetime.now(UTC).isoformat()
    adapter = _get_cached_adapter()

    if adapter is None:
        # Fallback is NOT cached — keep retrying on each call once keys appear.
        return {
            "source": "fallback",
            "total_equity_usdt": FALLBACK_BALANCE_USDT,
            "fetched_at_iso": now_iso,
            "error": "no_api_keys",
        }

    try:
        snapshot = adapter.get_wallet_balance(coin=_BALANCE_COIN)
        total_equity = float(snapshot.wallet_balance)
        result = {
            "source": "bybit_v5",
            "total_equity_usdt": total_equity,
            "fetched_at_iso": now_iso,
            "error": None,
        }
        # Cache only successful fetches.
        with _cache_lock:
            _cached_balance = dict(result)
            _cached_at_monotonic = time.monotonic()
        return result
    except Exception as exc:  # noqa: BLE001
        # H2.4 (S49) — do NOT return str(exc) to the client (may carry pybit request
        # context / signature). Sanitized token to client; full detail to logs only.
        logger.warning("bybit_balance_fetch_failed", extra={"error": str(exc)})
        return {
            "source": "fallback",
            "total_equity_usdt": FALLBACK_BALANCE_USDT,
            "fetched_at_iso": now_iso,
            "error": "fetch_failed",
        }
