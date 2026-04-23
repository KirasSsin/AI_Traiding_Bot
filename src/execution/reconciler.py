"""Post-reconnect reconciler. ADR 0019 sub-decision 3."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class ExchangeQueryClient(Protocol):
    """Minimal contract reconciler needs from the exchange.

    Concrete impl wired in Task 8 (Coordinator) — likely a thin wrapper
    over BybitRESTClient._http.get_open_orders / .get_positions.
    """

    def get_open_orders(self, symbol: str) -> list[dict]: ...
    def get_position(self, symbol: str) -> dict | None: ...


@dataclass(frozen=True)
class OpenOrderSnapshot:
    order_id: str
    side: str           # "Buy" | "Sell"
    order_type: str     # "Market" | "Limit" | ...
    qty: Decimal
    price: Decimal | None        # None for market
    take_profit: Decimal | None
    stop_loss: Decimal | None
    order_link_id: str | None    # client_order_id


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    qty: Decimal           # 0 == flat
    avg_price: Decimal | None  # None when flat


@dataclass(frozen=True)
class ExchangeState:
    """Normalized snapshot of exchange-side truth for one symbol."""
    symbol: str
    open_orders: tuple[OpenOrderSnapshot, ...]
    position: PositionSnapshot


class Reconciler:
    """Fetches exchange-side state. Diff/verdict is Task 7."""

    def __init__(self, client: ExchangeQueryClient) -> None:
        self._client = client

    def fetch_exchange_state(self, symbol: str) -> ExchangeState:
        """Pull open orders + position for `symbol`, normalize to ExchangeState."""
        raw_orders = self._client.get_open_orders(symbol)
        orders = tuple(_normalize_order(o) for o in raw_orders)

        raw_pos = self._client.get_position(symbol)
        position = _normalize_position(symbol, raw_pos)

        return ExchangeState(symbol=symbol, open_orders=orders, position=position)


def _normalize_order(o: dict) -> OpenOrderSnapshot:
    """Bybit V5 open-order dict → OpenOrderSnapshot."""
    return OpenOrderSnapshot(
        order_id=o["orderId"],
        side=o["side"],
        order_type=o["orderType"],
        qty=Decimal(o["qty"]),
        price=Decimal(o["price"]) if o.get("price") not in (None, "", "0") else None,
        take_profit=Decimal(o["takeProfit"]) if o.get("takeProfit") not in (None, "", "0") else None,
        stop_loss=Decimal(o["stopLoss"]) if o.get("stopLoss") not in (None, "", "0") else None,
        order_link_id=o.get("orderLinkId") or None,
    )


def _normalize_position(symbol: str, raw: dict | None) -> PositionSnapshot:
    """Bybit position dict (or None) → PositionSnapshot. None == flat."""
    if raw is None:
        return PositionSnapshot(symbol=symbol, qty=Decimal("0"), avg_price=None)
    qty = Decimal(raw.get("size", "0"))
    if qty == 0:
        return PositionSnapshot(symbol=symbol, qty=Decimal("0"), avg_price=None)
    avg_price = Decimal(raw["avgPrice"]) if raw.get("avgPrice") else None
    return PositionSnapshot(symbol=symbol, qty=qty, avg_price=avg_price)
