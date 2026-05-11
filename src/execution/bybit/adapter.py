"""Bybit V5 MARKET order adapter — ADR 0020 sub-decisions 1 & 3."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.execution.bybit.errors import BybitAdapterError, ReasonCode, map_error
from src.marketdata.bybit.rest import _retry_with_backoff
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


def _safe_extract_list(resp: dict[str, Any], context: str) -> list[Any]:
    """S47 T10 — defensive extraction of resp['result']['list'].

    bybit-api-reviewer S38 finding M2: direct access raises bare KeyError on
    Bybit V5 schema shift. This helper raises BybitAdapterError with a clear
    message including `context` (the calling operation name).

    Use for operations that always expect result.list to be present (get_order,
    get_wallet_balance). For operations that treat a missing list as empty,
    use _safe_extract_list_or_empty instead.
    """
    result = resp.get("result")
    if not isinstance(result, dict):
        raise BybitAdapterError(
            f"Bybit response missing 'result' dict для {context}: got {type(result).__name__}"
        )
    items = result.get("list")
    if not isinstance(items, list):
        raise BybitAdapterError(
            f"Bybit response 'result.list' not list для {context}: got {type(items).__name__}"
        )
    return items


def _safe_extract_list_or_empty(resp: dict[str, Any], context: str) -> list[Any]:
    """S47 T10 — defensive extraction of resp['result']['list'], returning [] if list absent.

    For listing endpoints (get_open_orders, get_order_history) where Bybit may
    omit the 'list' key entirely when there are no results. Raises BybitAdapterError
    only if 'result' itself is missing or not a dict (genuine schema shift).
    If 'list' key is absent or None, returns [] (no orders case).
    """
    result = resp.get("result")
    if not isinstance(result, dict):
        raise BybitAdapterError(
            f"Bybit response missing 'result' dict для {context}: got {type(result).__name__}"
        )
    items = result.get("list")
    if items is None:
        return []
    if not isinstance(items, list):
        raise BybitAdapterError(
            f"Bybit response 'result.list' not list для {context}: got {type(items).__name__}"
        )
    return items


@dataclass(frozen=True)
class OrderAck:
    """Minimal acknowledgement returned by Bybit after a successful place_order."""

    order_id: str
    order_link_id: str | None


@dataclass(frozen=True)
class CancelResult:
    """Result of a cancel_order call. cancelled=False+reason=REJECT_ORDER_ALREADY_TERMINAL
    means the order was already Filled (non-fatal race per ADR 0020 sub-decision 6)."""

    cancelled: bool
    reason_code: ReasonCode | None = None


@dataclass(frozen=True)
class OrderSnapshot:
    order_id: str
    order_link_id: str
    order_status: str
    cum_exec_qty: Decimal
    cum_exec_fee: Decimal
    fee_currency: str
    avg_price: Decimal | None


@dataclass(frozen=True)
class WalletSnapshot:
    coin: str
    wallet_balance: Decimal
    available: Decimal
    locked: Decimal


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

        resp = _retry_with_backoff(lambda: self._rest._http.place_order(**payload))
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)

        return OrderAck(
            order_id=resp["result"]["orderId"],
            order_link_id=resp["result"].get("orderLinkId"),
        )

    def place_stop_market_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: Decimal,
        trigger_price: Decimal,
        order_link_id: str,
    ) -> OrderAck:
        """ADR 0020 sub-decision 2: SL leg of 3-order Spot OCO bracket.

        Bybit Spot silently rewrites timeInForce GTC→IOC (probe v3-D); we omit
        timeInForce entirely and handle IOC partial-fills at EXIT_SL_RESIDUAL.
        """
        self._filters.validate_order(qty=qty)
        payload: dict[str, Any] = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "orderFilter": "StopOrder",
            "qty": str(qty),
            "triggerPrice": str(trigger_price),
            "triggerBy": "LastPrice",
            "marketUnit": "baseCoin",
            "orderLinkId": order_link_id,
        }
        resp = _retry_with_backoff(lambda: self._rest._http.place_order(**payload))
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
        resp = _retry_with_backoff(lambda: self._rest._http.place_order(**payload))
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)
        return OrderAck(
            order_id=resp["result"]["orderId"],
            order_link_id=resp["result"].get("orderLinkId"),
        )

    def cancel_order(self, *, symbol: str, order_id: str) -> CancelResult:
        """ADR 0020 sub-decision 6: cancel-of-Filled returns 110001, classified non-fatal."""
        payload = {"category": "spot", "symbol": symbol, "orderId": order_id}
        resp = _retry_with_backoff(lambda: self._rest._http.cancel_order(**payload))
        if resp["retCode"] == 0:
            return CancelResult(cancelled=True)
        reason = map_error(resp["retCode"], resp.get("retMsg", ""))
        # Defense-in-depth: pin classifier to retCode==110001 (not the reason alone),
        # so future _MAP additions can't silently swallow a different error as "already terminal".
        if resp["retCode"] == 110001 and reason is ReasonCode.REJECT_ORDER_ALREADY_TERMINAL:
            return CancelResult(cancelled=False, reason_code=reason)
        raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)

    def cancel_all_orders(self, *, symbol: str) -> None:
        """Bulk cancel — used by flatten cascade and emergency halt."""
        resp = _retry_with_backoff(
            lambda: self._rest._http.cancel_all_orders(category="spot", symbol=symbol)
        )
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)

    def get_order(self, *, symbol: str, order_id: str) -> OrderSnapshot:
        """Used by sibling-cancel-on-Triggered handler + Reconciler order-history sweep.

        Bybit V5 shape: result.list[0] contains the order fields.
        """
        resp = _retry_with_backoff(
            lambda: self._rest._http.get_order(category="spot", symbol=symbol, orderId=order_id)
        )
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)
        items = _safe_extract_list(resp, "get_order")
        if not items:
            raise BybitAPIError(-1, f"order {order_id} not found", ReasonCode.UNKNOWN_ERROR)
        raw = items[0]
        return OrderSnapshot(
            order_id=raw["orderId"],
            order_link_id=raw.get("orderLinkId", ""),
            order_status=raw["orderStatus"],
            cum_exec_qty=Decimal(raw.get("cumExecQty") or "0"),
            cum_exec_fee=Decimal(raw.get("cumExecFee") or "0"),
            fee_currency=raw.get("feeCurrency", ""),
            avg_price=Decimal(raw["avgPrice"]) if raw.get("avgPrice") else None,
        )

    def get_open_orders(self, *, symbol: str) -> list[dict[str, Any]]:
        """ADR 0020 sub-decision 9: list active orders for prior-attempt detection.
        V5 GET /v5/order/realtime — returns currently open (Untriggered/New/PartiallyFilled).
        """
        resp = _retry_with_backoff(
            lambda: self._rest._http.get_open_orders(category="spot", symbol=symbol)
        )
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)
        return _safe_extract_list_or_empty(resp, "get_open_orders")

    def get_order_history(self, *, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """ADR 0020 sub-decision 9: recent terminal orders for prior-attempt detection.
        V5 GET /v5/order/history — Filled/Cancelled/Rejected within ~7 days.
        """
        resp = _retry_with_backoff(
            lambda: self._rest._http.get_order_history(category="spot", symbol=symbol, limit=limit)
        )
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)
        return _safe_extract_list_or_empty(resp, "get_order_history")

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
        """ADR 0020 sub-decision 4: canonical Spot position truth (no get_position on Spot V5).

        Bybit V5 shape: result.list[0].coin[0] contains the per-coin balance.
        availableToWithdraw='' means funds fully locked — coerce empty string to Decimal('0').
        """
        resp = _retry_with_backoff(
            lambda: self._rest._http.get_wallet_balance(accountType="UNIFIED", coin=coin)
        )
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)
        items = _safe_extract_list(resp, "get_wallet_balance")
        if not items:
            raise BybitAPIError(-1, f"wallet for {coin} not found", ReasonCode.UNKNOWN_ERROR)
        coin_rows = items[0].get("coin") or []
        if not coin_rows:
            raise BybitAPIError(-1, f"coin {coin} not in wallet", ReasonCode.UNKNOWN_ERROR)
        raw = coin_rows[0]
        avail_str = raw.get("availableToWithdraw") or "0"  # coerce '' to '0'
        return WalletSnapshot(
            coin=raw.get("coin", coin),
            wallet_balance=Decimal(raw.get("walletBalance") or "0"),
            available=Decimal(avail_str),
            locked=Decimal(raw.get("locked") or "0"),
        )
