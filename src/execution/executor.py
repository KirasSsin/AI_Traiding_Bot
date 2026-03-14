import asyncio
import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional, List, Tuple, Any

from pybit.unified_trading import HTTP

from src.core.models import Order, Signal

logger = logging.getLogger(__name__)

class BybitExecutor:
    """
    Handles trading execution on Bybit.
    Mocks actual HTTP POSTs for MVP safety, but structure is production-ready.
    """
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        live_trading: bool = False,
        category: str = "linear",
        demo: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.live_trading = live_trading
        self.category = category
        self.demo = demo
        self._http: HTTP | None = None
        
        # Internal tracking of active orders
        self.active_orders: Dict[str, Order] = {}
        self.execution_log: List[Order] = []

    async def start(self):
         self._http = HTTP(
             testnet=self.testnet,
             demo=self.demo,
             api_key=self.api_key,
             api_secret=self.api_secret,
         )
         logger.info(
            "BybitExecutor initialized. Testnet: %s | Demo: %s | Live trading: %s",
            "Yes" if self.testnet else "No",
            "Yes" if self.demo else "No",
            "Yes" if self.live_trading else "No",
        )

    async def stop(self):
         logger.info("BybitExecutor stopped.")

    async def fetch_balance(self) -> float:
        """Fetches the total equity from the Bybit Unified Trading Account."""
        try:
            if not self._http:
                raise Exception("pybit HTTP client not initialized")

            data = await asyncio.to_thread(
                self._http.get_wallet_balance,
                accountType="UNIFIED",
            )
            if data.get("retCode") == 0:
                balance = float(data["result"]["list"][0]["totalEquity"])
                logger.info(f"Successfully fetched Bybit balance: ${balance:.2f}")
                return balance
            logger.error(f"Failed to fetch balance. API Response: {data}")
            return 0.0
        except Exception as e:
            logger.error(f"Error connecting to Bybit API to fetch balance: {e}")
            return 0.0

    async def execute_signal(self, signal: Signal, quantity: float, category: Optional[str] = None) -> Optional[Order]:
        """
        Takes an approved signal and executes it on the exchange.
        V5 API supports unified endpoints: e.g. /v5/order/create with category=spot/linear/inverse/option
        """
        order_category = category or self.category
        logger.info(f"Executing {signal.direction} order for {quantity} {signal.symbol} at {signal.entry_price}")

        if not self.live_trading:
            mock_order_id = int(time.time() * 1000)
            order = Order(
                symbol=signal.symbol,
                order_id=mock_order_id,
                client_order_id=f"bot_{mock_order_id}",
                direction=signal.direction,
                type="MARKET",
                price=signal.entry_price,
                quantity=quantity,
                status="FILLED",
                timestamp=mock_order_id,
            )
            self.active_orders[str(mock_order_id)] = order
            self._record_execution(order)
            logger.info(f"Order EXECUTED (MOCK): {order}")
            return order

        if not self._http:
            logger.error("pybit HTTP client not initialized. Cannot place live order.")
            return None

        try:
            qty = await self._normalize_quantity(
                order_category,
                signal.symbol,
                quantity,
            )
            if qty <= 0:
                logger.error("Normalized quantity <= 0. Order aborted.")
                return None

            side = "Buy" if signal.direction == "BUY" else "Sell"
            response = await asyncio.to_thread(
                self._http.place_order,
                category=order_category,
                symbol=signal.symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
            )
            if response.get("retCode") != 0:
                logger.error(f"Live order failed. API Response: {response}")
                return None

            result = response.get("result", {})
            order_id = result.get("orderId") or int(time.time() * 1000)
            order = Order(
                symbol=signal.symbol,
                order_id=int(order_id) if str(order_id).isdigit() else int(time.time() * 1000),
                client_order_id=result.get("orderLinkId") or f"bot_{order_id}",
                direction=signal.direction,
                type="MARKET",
                price=signal.entry_price,
                quantity=qty,
                status="FILLED",
                timestamp=int(time.time() * 1000),
            )
            self.active_orders[str(order.order_id)] = order
            self._record_execution(order)
            logger.info(f"Order EXECUTED (LIVE): {order}")
            return order
        except Exception as e:
            logger.error(f"Error executing live order: {e}")
            return None

    def _record_execution(self, order: Order):
        self.execution_log.append(order)
        if len(self.execution_log) > 50:
            self.execution_log.pop(0)

    async def _normalize_quantity(self, category: str, symbol: str, quantity: float) -> float:
        if not self._http:
            return quantity
        try:
            info = await asyncio.to_thread(
                self._http.get_instruments_info,
                category=category,
                symbol=symbol,
            )
            if info.get("retCode") != 0:
                logger.error(f"Failed to fetch instruments info: {info}")
                return quantity

            lot = info["result"]["list"][0]["lotSizeFilter"]
            step = Decimal(lot["qtyStep"])
            min_qty = Decimal(lot["minOrderQty"])

            qty = Decimal(str(quantity))
            qty = qty.quantize(step, rounding=ROUND_DOWN)
            if qty < min_qty:
                qty = min_qty
            normalized = float(qty)
            logger.info(f"Normalized quantity: {normalized} (step={step}, min={min_qty})")
            return normalized
        except Exception as e:
            logger.error(f"Failed to normalize quantity: {e}")
            return quantity

    async def get_qty_for_usdt(self, category: str, symbol: str, usdt_amount: float) -> Tuple[float, float]:
        if not self._http:
            raise RuntimeError("pybit HTTP client not initialized")
        tick = await asyncio.to_thread(
            self._http.get_tickers,
            category=category,
            symbol=symbol,
        )
        if tick.get("retCode") != 0:
            raise RuntimeError(f"get_tickers failed: {tick}")
        last_price = float(tick["result"]["list"][0]["lastPrice"])

        info = await asyncio.to_thread(
            self._http.get_instruments_info,
            category=category,
            symbol=symbol,
        )
        if info.get("retCode") != 0:
            raise RuntimeError(f"get_instruments_info failed: {info}")
        lot = info["result"]["list"][0]["lotSizeFilter"]
        step = Decimal(lot["qtyStep"])
        min_qty = Decimal(lot["minOrderQty"])

        qty = Decimal(str(usdt_amount)) / Decimal(str(last_price))
        qty = qty.quantize(step, rounding=ROUND_DOWN)
        if qty < min_qty:
            qty = min_qty
        return last_price, float(qty)

    async def fetch_execution_history(
        self,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if not self._http:
            logger.error("pybit HTTP client not initialized. Cannot fetch executions.")
            return []
        try:
            params = {
                "category": category or self.category,
                "limit": limit,
            }
            if symbol:
                params["symbol"] = symbol
            data = await asyncio.to_thread(self._http.get_executions, **params)
            if data.get("retCode") != 0:
                logger.error(f"Failed to fetch executions. API Response: {data}")
                return []
            items = data.get("result", {}).get("list", [])
            executions: List[Dict[str, Any]] = []
            for item in items:
                side = (item.get("side") or "").upper()
                direction = "BUY" if side == "BUY" else "SELL" if side == "SELL" else side
                ts_raw = item.get("execTime") or item.get("createdTime") or 0
                try:
                    ts = int(ts_raw)
                except Exception:
                    ts = 0
                executions.append({
                    "id": item.get("execId") or item.get("orderId") or item.get("orderLinkId"),
                    "direction": direction,
                    "price": float(item.get("execPrice") or item.get("price") or 0),
                    "qty": float(item.get("execQty") or item.get("qty") or 0),
                    "status": "FILLED",
                    "timestamp": ts,
                    "source": "API",
                })
            return executions
        except Exception as e:
            logger.error(f"Error fetching executions: {e}")
            return []
