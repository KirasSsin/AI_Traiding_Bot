"""Bybit V5 MARKET order adapter — domain-friendly wrapper."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.execution.bybit.errors import ReasonCode, map_error
from src.execution.models import Order, OrderSide, OrderStatus, OrderType
from src.marketdata.filters import BybitFilters


class BybitAPIError(RuntimeError):
    """Bybit `place_order` returned non-zero retCode."""

    def __init__(self, ret_code: int, ret_msg: str, reason: ReasonCode) -> None:
        super().__init__(f"retCode={ret_code} ({reason}): {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.reason = reason


_SIDE_MAP = {OrderSide.BUY: "Buy", OrderSide.SELL: "Sell"}


class BybitMarketAdapter:
    """MARKET spot orders only (v0.1 scope)."""

    def __init__(self, rest_client: Any, filters: BybitFilters) -> None:
        self._rest = rest_client
        self._filters = filters

    def place_market_order(
        self,
        client_order_id: str,
        side: OrderSide,
        qty: Decimal,
        reference_price: Decimal,
        *,
        take_profit: Decimal | None = None,
        stop_loss: Decimal | None = None,
        tpsl_mode: str | None = None,
    ) -> Order:
        """Place MARKET order; validate via filters; return Order.

        `reference_price` is needed only for the notional (min_order_amt) check;
        it does NOT go into the order — MARKET orders have no price parameter.
        """
        self._filters.validate_order(qty=qty, price=reference_price)
        now = datetime.now(tz=UTC)

        payload = {
            "category": "spot",
            "symbol": self._filters.symbol,
            "side": _SIDE_MAP[side],
            "orderType": "Market",
            "qty": str(qty),
            "orderLinkId": client_order_id,
        }
        if take_profit is not None:
            payload["takeProfit"] = str(take_profit)
        if stop_loss is not None:
            payload["stopLoss"] = str(stop_loss)
        if tpsl_mode is not None:
            payload["tpslMode"] = tpsl_mode

        resp = self._rest._http.place_order(**payload)
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)

        return Order(
            client_order_id=client_order_id,
            exch_order_id=resp["result"]["orderId"],
            symbol=self._filters.symbol,
            side=side,
            type=OrderType.MARKET,
            status=OrderStatus.NEW,
            orig_qty=qty,
            executed_qty=Decimal("0"),
            price=None,
            created_at=now,
            updated_at=now,
        )
