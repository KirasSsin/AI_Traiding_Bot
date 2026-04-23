"""Bybit V5 MARKET order adapter — ADR 0020 sub-decisions 1 & 3."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.execution.bybit.errors import ReasonCode, map_error
from src.marketdata.filters import BybitFilters

# ADR 0020 sub-decision 3: these fields are rejected by Bybit Spot V5 with ErrCode 170130.
_BANNED_SPOT_FIELDS = (
    "tpslMode",
    "takeProfit",
    "stopLoss",
    "tpOrderType",
    "slOrderType",
    "triggerDirection",
)


@dataclass(frozen=True)
class OrderAck:
    """Minimal acknowledgement returned by Bybit after a successful place_order."""

    order_id: str
    order_link_id: str | None


class BybitAPIError(RuntimeError):
    """Bybit `place_order` returned non-zero retCode."""

    def __init__(self, ret_code: int, ret_msg: str, reason: ReasonCode) -> None:
        super().__init__(f"retCode={ret_code} ({reason}): {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.reason = reason


class BybitMarketAdapter:
    """MARKET spot orders only (v0.1 scope). ADR 0020."""

    def __init__(self, *, rest: Any, filters: BybitFilters) -> None:
        self._rest = rest
        self._filters = filters

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: Decimal,
        order_link_id: str | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> OrderAck:
        """Place a Spot MARKET order on Bybit V5.

        Guards (ADR 0020 sub-decision 3):
        - Raises ValueError for any banned Spot field in extra_payload.
        - Raises ValueError if marketUnit=quoteCoin is requested.
        - Always pins marketUnit=baseCoin in the final payload.

        Filter validation runs before the REST call; min-notional is skipped
        because MARKET orders have no price at order-build time.
        """
        extra = dict(extra_payload) if extra_payload else {}

        # Guard: banned Spot V5 fields
        for banned in _BANNED_SPOT_FIELDS:
            if banned in extra:
                raise ValueError(
                    f"Field {banned!r} is banned for Bybit Spot V5: {banned} "
                    f"(probe v1 / ErrCode 170130, ADR 0020 sub-decision 3)"
                )

        # Guard: marketUnit=quoteCoin causes 16-dp accumulation drift (probe S2 v2)
        market_unit = extra.pop("marketUnit", "baseCoin")
        if market_unit == "quoteCoin":
            raise ValueError(
                "marketUnit=quoteCoin banned: causes 16-dp accumulation drift "
                "(probe S2 v2, ADR 0020 sub-decision 3)"
            )

        # Filter validation — price=None skips min-notional (no ref price for MARKET)
        self._filters.validate_order(qty=qty)

        payload: dict[str, Any] = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": str(qty),
            "marketUnit": "baseCoin",
        }
        if order_link_id:
            payload["orderLinkId"] = order_link_id
        payload.update(extra)

        resp = self._rest._http.place_order(**payload)
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)

        return OrderAck(
            order_id=resp["result"]["orderId"],
            order_link_id=resp["result"].get("orderLinkId"),
        )

    def place_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: Decimal,
        price: Decimal,
        order_link_id: str,
    ) -> OrderAck:
        """ADR 0020 sub-decision 2: TP leg of 3-order Spot OCO bracket (Limit Sell, GTC)."""
        self._filters.validate_order(qty=qty, price=price)
        payload: dict[str, Any] = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": "Limit",
            "timeInForce": "GTC",
            "qty": str(qty),
            "price": str(price),
            "marketUnit": "baseCoin",
            "orderLinkId": order_link_id,
        }
        resp = self._rest._http.place_order(**payload)
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)
        return OrderAck(
            order_id=resp["result"]["orderId"],
            order_link_id=resp["result"].get("orderLinkId"),
        )
