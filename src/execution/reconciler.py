"""Post-reconnect reconciler. ADR 0019 sub-decision 3."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRow


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

    def reconcile(
        self, symbol: str, local: ExecutionStateRow | None
    ) -> ReconcileResult:
        """Diff local FSM state vs exchange snapshot. Caller acts on verdict.

        Rules (v0.1, single-symbol LONG-only):
        - local None or local.state in FLAT-set: exchange must be flat (qty 0
          AND no open orders) → OK; otherwise DIVERGENCE.
        - local in active set (LONG_OPEN, OCO_ARMED, PARTIAL_FILL,
          ENTRY_PENDING, EXIT_PENDING, RECONCILING, HALTED, ERROR):
            * exchange position qty must equal local.position_qty within eps
            * if local.oco_main_order_id is set, exchange must have an open
              order with matching orderId; otherwise DIVERGENCE.
        """
        exchange = self.fetch_exchange_state(symbol)
        ex_qty = exchange.position.qty
        ex_has_orders = len(exchange.open_orders) > 0

        # Case 1: no local row at all
        if local is None:
            if ex_qty == 0 and not ex_has_orders:
                return ReconcileResult(
                    ReconcileVerdict.OK, exchange, None,
                    "no local state; exchange flat",
                )
            return ReconcileResult(
                ReconcileVerdict.DIVERGENCE, exchange, None,
                f"no local state but exchange has qty={ex_qty} orders={len(exchange.open_orders)}",
            )

        # Case 2: local says flat-equivalent
        if local.state in _FLAT_STATES:
            if ex_qty == 0 and not ex_has_orders:
                return ReconcileResult(
                    ReconcileVerdict.OK, exchange, local,
                    f"local {local.state.value} matches exchange flat",
                )
            return ReconcileResult(
                ReconcileVerdict.DIVERGENCE, exchange, local,
                f"local {local.state.value} but exchange has qty={ex_qty} orders={len(exchange.open_orders)}",
            )

        # Case 3: local says active position
        qty_diff = abs(ex_qty - local.position_qty)
        if qty_diff > _QTY_EPS:
            return ReconcileResult(
                ReconcileVerdict.DIVERGENCE, exchange, local,
                f"qty mismatch: local={local.position_qty} exchange={ex_qty} diff={qty_diff}",
            )

        if local.oco_main_order_id is not None:
            ids = {o.order_id for o in exchange.open_orders}
            if local.oco_main_order_id not in ids:
                return ReconcileResult(
                    ReconcileVerdict.DIVERGENCE, exchange, local,
                    f"oco order {local.oco_main_order_id} missing on exchange (open_ids={sorted(ids)})",
                )

        return ReconcileResult(
            ReconcileVerdict.OK, exchange, local,
            f"local {local.state.value} qty={local.position_qty} matches exchange",
        )


class ReconcileVerdict(StrEnum):
    OK = "OK"
    DIVERGENCE = "DIVERGENCE"


@dataclass(frozen=True)
class ReconcileResult:
    """Outcome of comparing local FSM state vs exchange state."""
    verdict: ReconcileVerdict
    exchange_state: ExchangeState
    local_row: ExecutionStateRow | None
    detail: str       # human-readable diff for audit log


_QTY_EPS = Decimal("1e-8")
_FLAT_STATES = {ExecutionState.FLAT, ExecutionState.INIT, ExecutionState.COOLDOWN, ExecutionState.KILLED}


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
    avg_price = (
        Decimal(raw["avgPrice"]) if raw.get("avgPrice") not in (None, "", "0") else None
    )
    return PositionSnapshot(symbol=symbol, qty=qty, avg_price=avg_price)
