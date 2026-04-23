"""Bybit Spot V5 testnet smoke — verify B1..B5 assumptions for ADR 0020.

Resolves:
    B1: cancelType field on Spot WS order stream values
    B2: tpslMode="Full" supported in single Spot V5 place_order call
    B3: TP/SL legs visibility — separate orders in get_open_orders or position-level
    B4: cumExecQty cumulative vs delta in execution stream
    B5: Spot Market partial-fill possibility

Usage:
    python scripts/testnet_tpsl_smoke.py             # dry-run (no orders placed)
    python scripts/testnet_tpsl_smoke.py --live-testnet  # places real testnet orders

Output: scripts/testnet_tpsl_smoke_output.json (gitignored)
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from decimal import ROUND_DOWN, ROUND_UP, Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pybit.unified_trading import HTTP, WebSocket  # noqa: E402

from src.platform.config import Settings  # noqa: E402

OUT_PATH = REPO_ROOT / "scripts" / "testnet_tpsl_smoke_output.json"
SYMBOL = "BTCUSDT"
TARGET_NOTIONAL_USDT = Decimal("50")


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class WSCollector:
    """Background collector for execution + order private streams."""

    def __init__(
        self, *, testnet: bool, demo: bool, api_key: str, api_secret: str
    ) -> None:
        self._testnet = testnet
        self._demo = demo
        self._api_key = api_key
        self._api_secret = api_secret
        self._ws: Any = None
        self._messages: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _on_execution(self, msg: dict[str, Any]) -> None:
        with self._lock:
            self._messages.append({"ts": _now_iso(), "topic": "execution", "msg": msg})

    def _on_order(self, msg: dict[str, Any]) -> None:
        with self._lock:
            self._messages.append({"ts": _now_iso(), "topic": "order", "msg": msg})

    def start(self) -> None:
        self._ws = WebSocket(
            testnet=self._testnet,
            demo=self._demo,
            channel_type="private",
            api_key=self._api_key,
            api_secret=self._api_secret,
        )
        self._ws.execution_stream(callback=self._on_execution)
        self._ws.order_stream(callback=self._on_order)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._messages)

    def stop(self) -> None:
        if self._ws is not None and hasattr(self._ws, "exit"):
            try:
                self._ws.exit()
            except Exception:
                pass


def _round_qty(qty: Decimal, step: Decimal) -> Decimal:
    return (qty / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step


def _round_price(price: Decimal, tick: Decimal, *, mode: str) -> Decimal:
    rounding = ROUND_DOWN if mode == "down" else ROUND_UP
    return (price / tick).quantize(Decimal("1"), rounding=rounding) * tick


def _safe_call(label: str, fn, *args, **kwargs) -> dict[str, Any]:
    """Wrap any HTTP call; capture exception as JSON-serializable dict."""
    try:
        result = fn(*args, **kwargs)
        return {"label": label, "ok": True, "response": result}
    except Exception as e:
        return {
            "label": label,
            "ok": False,
            "exception_type": type(e).__name__,
            "exception_str": str(e),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live-testnet",
        action="store_true",
        help="Actually place orders (default: dry-run)",
    )
    parser.add_argument(
        "--env",
        choices=["demo", "testnet", "demo-testnet"],
        default="demo",
        help=(
            "demo=api-demo.bybit.com (Demo Trading, virtual money on mainnet host); "
            "testnet=api-testnet.bybit.com (separate testnet accounts); "
            "demo-testnet=api-demo-testnet.bybit.com"
        ),
    )
    args = parser.parse_args()

    env_map = {
        "demo": (False, True, "api-demo.bybit.com"),
        "testnet": (True, False, "api-testnet.bybit.com"),
        "demo-testnet": (True, True, "api-demo-testnet.bybit.com"),
    }
    use_testnet, use_demo, host_label = env_map[args.env]

    s = Settings()
    api_key = s.bybit_api_key
    api_secret = s.bybit_api_secret

    output: dict[str, Any] = {
        "started_at": _now_iso(),
        "env": args.env,
        "host": host_label,
        "live": args.live_testnet,
        "symbol": SYMBOL,
        "target_notional_usdt": str(TARGET_NOTIONAL_USDT),
    }

    http = HTTP(
        testnet=use_testnet, demo=use_demo, api_key=api_key, api_secret=api_secret
    )

    print(f"[{_now_iso()}] Fetching instruments-info for {SYMBOL}...")
    instruments_call = _safe_call(
        "instruments_info", http.get_instruments_info, category="spot", symbol=SYMBOL
    )
    output["instruments_info"] = instruments_call
    if not instruments_call["ok"]:
        _dump_and_exit(output, code=3, msg="instruments_info failed")

    item = instruments_call["response"]["result"]["list"][0]
    step = Decimal(item["lotSizeFilter"]["basePrecision"])
    tick = Decimal(item["priceFilter"]["tickSize"])
    min_qty = Decimal(item["lotSizeFilter"]["minOrderQty"])
    min_amt = Decimal(item["lotSizeFilter"]["minOrderAmt"])
    print(f"  step={step} tick={tick} min_qty={min_qty} min_amt={min_amt}")

    print(f"[{_now_iso()}] Fetching tickers...")
    tickers_call = _safe_call("tickers", http.get_tickers, category="spot", symbol=SYMBOL)
    output["tickers"] = tickers_call
    if not tickers_call["ok"]:
        _dump_and_exit(output, code=4, msg="tickers failed")

    last_price = Decimal(tickers_call["response"]["result"]["list"][0]["lastPrice"])
    print(f"  last_price={last_price}")

    qty_raw = TARGET_NOTIONAL_USDT / last_price
    qty = _round_qty(qty_raw, step)
    if qty < min_qty:
        qty = min_qty
    notional = qty * last_price
    if notional < min_amt:
        qty = _round_qty((min_amt / last_price) * Decimal("1.05"), step)
        notional = qty * last_price

    tp_raw = last_price * Decimal("1.02")
    sl_raw = last_price * Decimal("0.98")
    tp = _round_price(tp_raw, tick, mode="up")
    sl = _round_price(sl_raw, tick, mode="down")

    print(f"  computed qty={qty} notional≈{notional} TP={tp} SL={sl}")
    output["computed_order"] = {
        "qty": str(qty),
        "notional_usdt": str(notional),
        "tp": str(tp),
        "sl": str(sl),
        "tpsl_mode": "Full",
    }

    if not args.live_testnet:
        print("\nDRY-RUN mode. Re-run with --live-testnet to actually place orders.")
        output["finished_at"] = _now_iso()
        OUT_PATH.write_text(json.dumps(output, indent=2, default=str))
        print(f"Output: {OUT_PATH}")
        return

    print(f"\n[{_now_iso()}] Starting WS private streams (execution + order)...")
    ws = WSCollector(
        testnet=use_testnet,
        demo=use_demo,
        api_key=api_key,
        api_secret=api_secret,
    )
    ws.start()
    time.sleep(3)
    print("  WS connected. Snapshot of pre-order messages:")
    print(f"  pre-order WS msg count: {len(ws.snapshot())}")
    output["ws_pre_order"] = ws.snapshot()

    entry_link_id = f"smoke-entry-{uuid.uuid4().hex[:12]}"
    print(f"\n[{_now_iso()}] Placing Market BUY {qty} {SYMBOL} with tpslMode=Full TP={tp} SL={sl}")
    print(f"  orderLinkId={entry_link_id}")
    place_call = _safe_call(
        "place_order_market_buy_with_tpsl",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=str(qty),
        marketUnit="baseCoin",
        orderLinkId=entry_link_id,
        takeProfit=str(tp),
        stopLoss=str(sl),
        tpslMode="Full",
    )
    output["place_order_response"] = place_call

    if not place_call["ok"]:
        print(f"  PLACE FAILED: {place_call['exception_str']}")
        time.sleep(2)
        output["ws_after_failed_place"] = ws.snapshot()
        ws.stop()
        _dump_and_exit(output, code=5, msg="place_order failed (B2 likely false)")

    resp = place_call["response"]
    print(f"  retCode={resp.get('retCode')} retMsg={resp.get('retMsg')}")
    if resp.get("retCode") != 0:
        print(f"  Bybit rejected: {resp}")
        time.sleep(2)
        output["ws_after_rejected_place"] = ws.snapshot()
        ws.stop()
        _dump_and_exit(output, code=6, msg=f"Bybit retCode={resp.get('retCode')}")

    entry_order_id = resp["result"]["orderId"]
    print(f"  entry orderId={entry_order_id}")

    print(f"\n[{_now_iso()}] Waiting 8s for execution stream...")
    time.sleep(8)
    output["ws_after_place"] = ws.snapshot()
    print(f"  WS messages collected: {len(output['ws_after_place'])}")

    print(f"\n[{_now_iso()}] Querying open_orders (B3)...")
    output["open_orders_after_place"] = _safe_call(
        "open_orders_after_place", http.get_open_orders, category="spot", symbol=SYMBOL
    )

    print(f"[{_now_iso()}] Querying open_orders with openOnly=0 (incl. conditional)...")
    output["open_orders_openOnly_0"] = _safe_call(
        "open_orders_openOnly_0",
        http.get_open_orders,
        category="spot",
        symbol=SYMBOL,
        openOnly=0,
    )

    print(f"[{_now_iso()}] Querying order_history for orderLinkId={entry_link_id}...")
    output["order_history_by_link_id"] = _safe_call(
        "order_history_by_link_id",
        http.get_order_history,
        category="spot",
        symbol=SYMBOL,
        orderLinkId=entry_link_id,
        limit=10,
    )

    print(f"[{_now_iso()}] Querying order_history (recent 20)...")
    output["order_history_recent"] = _safe_call(
        "order_history_recent",
        http.get_order_history,
        category="spot",
        symbol=SYMBOL,
        limit=20,
    )

    print(f"[{_now_iso()}] Querying get_positions (Spot — may be empty)...")
    output["get_positions_spot"] = _safe_call(
        "get_positions_spot", http.get_positions, category="spot", symbol=SYMBOL
    )

    print(f"[{_now_iso()}] Querying wallet_balance for BTC + USDT (Spot truth)...")
    output["wallet_balance_unified"] = _safe_call(
        "wallet_balance_unified",
        http.get_wallet_balance,
        accountType="UNIFIED",
        coin="BTC,USDT",
    )

    print(f"\n[{_now_iso()}] Placing far-OTM Limit SELL to capture cancelType=CancelByUser (B1)...")
    far_price = _round_price(last_price * Decimal("1.50"), tick, mode="up")
    limit_link_id = f"smoke-limit-{uuid.uuid4().hex[:12]}"
    limit_call = _safe_call(
        "limit_sell_far_otm",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Limit",
        qty=str(qty),
        price=str(far_price),
        orderLinkId=limit_link_id,
        timeInForce="GTC",
    )
    output["limit_sell_response"] = limit_call

    if limit_call["ok"] and limit_call["response"].get("retCode") == 0:
        limit_order_id = limit_call["response"]["result"]["orderId"]
        print(f"  limit orderId={limit_order_id}, sleeping 3s...")
        time.sleep(3)
        output["ws_after_limit_place"] = ws.snapshot()

        print(f"[{_now_iso()}] Cancelling limit (capture cancelType)...")
        output["cancel_limit_response"] = _safe_call(
            "cancel_limit",
            http.cancel_order,
            category="spot",
            symbol=SYMBOL,
            orderId=limit_order_id,
        )
        time.sleep(3)
        output["ws_after_cancel_limit"] = ws.snapshot()
    else:
        print(f"  limit place failed/rejected; skipping cancel test")

    print(f"\n[{_now_iso()}] Closing position via Market SELL (cleanup)...")
    btc_qty = qty
    try:
        wb = output["wallet_balance_unified"].get("response", {})
        if wb.get("retCode") == 0:
            for coin_row in wb["result"]["list"][0].get("coin", []):
                if coin_row["coin"] == "BTC":
                    actual = Decimal(coin_row.get("walletBalance", "0"))
                    actual_rounded = _round_qty(actual, step)
                    if actual_rounded > 0:
                        btc_qty = actual_rounded
                        print(f"  using actual BTC balance: {btc_qty}")
                    break
    except Exception as e:
        print(f"  wallet parse error: {e}")

    close_link_id = f"smoke-close-{uuid.uuid4().hex[:12]}"
    output["close_market_sell_response"] = _safe_call(
        "close_market_sell",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Market",
        qty=str(btc_qty),
        marketUnit="baseCoin",
        orderLinkId=close_link_id,
    )

    print(f"  sleeping 8s for execution + checking if TP/SL legs auto-cancel...")
    time.sleep(8)
    output["ws_after_close"] = ws.snapshot()

    print(f"\n[{_now_iso()}] Final state queries...")
    output["final_open_orders"] = _safe_call(
        "final_open_orders", http.get_open_orders, category="spot", symbol=SYMBOL
    )
    output["final_wallet_balance"] = _safe_call(
        "final_wallet_balance",
        http.get_wallet_balance,
        accountType="UNIFIED",
        coin="BTC,USDT",
    )

    print(f"\n[{_now_iso()}] Stopping WS...")
    ws.stop()
    time.sleep(1)

    output["finished_at"] = _now_iso()
    OUT_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nOutput written: {OUT_PATH}")
    print(f"Total WS messages: {len(ws.snapshot())}")


def _dump_and_exit(output: dict[str, Any], *, code: int, msg: str) -> None:
    output["finished_at"] = _now_iso()
    output["fatal_error"] = msg
    OUT_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nFATAL: {msg}")
    print(f"Output: {OUT_PATH}")
    sys.exit(code)


if __name__ == "__main__":
    main()
