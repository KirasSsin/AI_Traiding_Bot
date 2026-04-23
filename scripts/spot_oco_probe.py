"""Final Bybit V5 Spot OCO probe — capture B1/B3/B4 evidence with WS streams.

Pattern (v0.1 must use, since native tpslMode=Full DOES NOT WORK ON SPOT):
  1. Market BUY (no TP/SL params)
  2. Limit Sell at TP price (orderType=Limit)
  3. Stop Sell at SL price (orderType=Market, orderFilter=StopOrder, triggerPrice, triggerDirection=2)
  4. Cancel-other on fill — client-side (Spot has NO native OCO sibling-cancel)

Output: scripts/spot_oco_probe_output.json
"""

from __future__ import annotations

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

OUT_PATH = REPO_ROOT / "scripts" / "spot_oco_probe_output.json"
SYMBOL = "BTCUSDT"
TARGET_NOTIONAL_USDT = Decimal("50")


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class WSCapture:
    def __init__(self, *, api_key: str, api_secret: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._ws: Any = None
        self._msgs: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _on_exec(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "execution", "msg": m})

    def _on_order(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "order", "msg": m})

    def start(self) -> None:
        self._ws = WebSocket(
            testnet=False,
            demo=True,
            channel_type="private",
            api_key=self._api_key,
            api_secret=self._api_secret,
        )
        self._ws.execution_stream(callback=self._on_exec)
        self._ws.order_stream(callback=self._on_order)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._msgs)

    def stop(self) -> None:
        if self._ws and hasattr(self._ws, "exit"):
            try:
                self._ws.exit()
            except Exception:
                pass


def _round_qty(q: Decimal, step: Decimal) -> Decimal:
    return (q / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step


def _round_price(p: Decimal, tick: Decimal, *, mode: str) -> Decimal:
    r = ROUND_DOWN if mode == "down" else ROUND_UP
    return (p / tick).quantize(Decimal("1"), rounding=r) * tick


def _safe(label: str, fn, *a, **kw) -> dict[str, Any]:
    try:
        return {"label": label, "ok": True, "response": fn(*a, **kw)}
    except Exception as e:
        return {
            "label": label,
            "ok": False,
            "exception_type": type(e).__name__,
            "exception_str": str(e),
        }


def main() -> None:
    s = Settings()
    out: dict[str, Any] = {
        "started_at": _now_iso(),
        "env": "demo (api-demo.bybit.com, mainnet host, virtual money)",
        "symbol": SYMBOL,
        "target_notional_usdt": str(TARGET_NOTIONAL_USDT),
    }

    http = HTTP(
        testnet=False,
        demo=True,
        api_key=s.bybit_api_key,
        api_secret=s.bybit_api_secret,
    )

    print(f"[{_now_iso()}] instruments-info...")
    r = http.get_instruments_info(category="spot", symbol=SYMBOL)
    item = r["result"]["list"][0]
    step = Decimal(item["lotSizeFilter"]["basePrecision"])
    tick = Decimal(item["priceFilter"]["tickSize"])
    out["filters"] = {"step": str(step), "tick": str(tick)}

    print(f"[{_now_iso()}] tickers...")
    r = http.get_tickers(category="spot", symbol=SYMBOL)
    last = Decimal(r["result"]["list"][0]["lastPrice"])
    qty = _round_qty(TARGET_NOTIONAL_USDT / last, step)
    tp = _round_price(last * Decimal("1.02"), tick, mode="up")
    sl = _round_price(last * Decimal("0.98"), tick, mode="down")
    print(f"  last={last} qty={qty} TP={tp} SL={sl}")
    out["computed"] = {"last": str(last), "qty": str(qty), "tp": str(tp), "sl": str(sl)}

    print(f"[{_now_iso()}] starting WS streams...")
    ws = WSCapture(api_key=s.bybit_api_key, api_secret=s.bybit_api_secret)
    ws.start()
    time.sleep(3)

    # ----- B2 RE-VERIFY: explicit attempt with tpslMode=Full + TP/SL on Spot -----
    print(f"\n[{_now_iso()}] B2: place Market BUY with takeProfit+stopLoss+tpslMode=Full")
    out["B2_native_tpsl_attempt"] = _safe(
        "B2_native_tpsl",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=str(qty),
        marketUnit="baseCoin",
        orderLinkId=f"b2probe-{uuid.uuid4().hex[:8]}",
        takeProfit=str(tp),
        stopLoss=str(sl),
        tpslMode="Full",
    )

    # ----- Emulated OCO pattern -----
    print(f"\n[{_now_iso()}] EMU 1/3: Market BUY (no TP/SL params)")
    entry_link = f"oco-entry-{uuid.uuid4().hex[:8]}"
    out["emu_entry"] = _safe(
        "emu_entry",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=str(qty),
        marketUnit="baseCoin",
        orderLinkId=entry_link,
    )

    print(f"  sleeping 5s for execution stream...")
    time.sleep(5)
    out["ws_after_entry"] = ws.snapshot()
    print(f"  WS msgs so far: {len(out['ws_after_entry'])}")

    print(f"\n[{_now_iso()}] EMU 2/3: Limit Sell @ TP (oco-tp)")
    tp_link = f"oco-tp-{uuid.uuid4().hex[:8]}"
    out["emu_tp_limit"] = _safe(
        "emu_tp_limit",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Limit",
        qty=str(qty),
        price=str(tp),
        orderLinkId=tp_link,
        timeInForce="GTC",
    )
    time.sleep(2)

    print(f"\n[{_now_iso()}] EMU 3/3: Stop Sell @ SL (oco-sl, conditional)")
    sl_link = f"oco-sl-{uuid.uuid4().hex[:8]}"
    out["emu_sl_stop"] = _safe(
        "emu_sl_stop",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Market",
        qty=str(qty),
        marketUnit="baseCoin",
        orderFilter="StopOrder",
        triggerPrice=str(sl),
        triggerDirection=2,
        orderLinkId=sl_link,
    )
    time.sleep(3)
    out["ws_after_oco_legs_placed"] = ws.snapshot()

    # ----- B3: are TP & SL legs visible in get_open_orders -----
    print(f"\n[{_now_iso()}] B3: get_open_orders (default)")
    out["B3_open_orders_default"] = _safe(
        "B3_open_orders_default", http.get_open_orders, category="spot", symbol=SYMBOL
    )
    print(f"[{_now_iso()}] B3: get_open_orders openOnly=0")
    out["B3_open_orders_openOnly_0"] = _safe(
        "B3_open_orders_openOnly_0",
        http.get_open_orders,
        category="spot",
        symbol=SYMBOL,
        openOnly=0,
    )
    print(f"[{_now_iso()}] B3: get_open_orders orderFilter=StopOrder")
    out["B3_open_orders_StopOrder"] = _safe(
        "B3_open_orders_stop",
        http.get_open_orders,
        category="spot",
        symbol=SYMBOL,
        orderFilter="StopOrder",
    )

    # ----- B1: cancel TP leg → capture cancelType from WS -----
    if out["emu_tp_limit"]["ok"] and out["emu_tp_limit"]["response"].get("retCode") == 0:
        tp_id = out["emu_tp_limit"]["response"]["result"]["orderId"]
        print(f"\n[{_now_iso()}] B1: cancelling TP limit {tp_id} → expect cancelType=CancelByUser")
        out["B1_cancel_tp"] = _safe(
            "B1_cancel_tp",
            http.cancel_order,
            category="spot",
            symbol=SYMBOL,
            orderId=tp_id,
        )
        time.sleep(3)

    if out["emu_sl_stop"]["ok"] and out["emu_sl_stop"]["response"].get("retCode") == 0:
        sl_id = out["emu_sl_stop"]["response"]["result"]["orderId"]
        print(f"[{_now_iso()}] B1b: cancelling SL stop {sl_id}")
        out["B1_cancel_sl"] = _safe(
            "B1_cancel_sl",
            http.cancel_order,
            category="spot",
            symbol=SYMBOL,
            orderId=sl_id,
            orderFilter="StopOrder",
        )
        time.sleep(3)

    out["ws_after_cancels"] = ws.snapshot()

    # ----- B5: Spot Market partial-fill check (look at execution stream from earlier) -----
    print(f"\n[{_now_iso()}] B5: order_history for entry — check fill type")
    out["B5_order_history_entry"] = _safe(
        "B5_history_entry",
        http.get_order_history,
        category="spot",
        symbol=SYMBOL,
        orderLinkId=entry_link,
        limit=10,
    )

    print(f"\n[{_now_iso()}] cleanup: cancel_all_orders + StopOrder")
    out["cleanup_default"] = _safe(
        "cleanup_default", http.cancel_all_orders, category="spot", symbol=SYMBOL
    )
    out["cleanup_stop"] = _safe(
        "cleanup_stop",
        http.cancel_all_orders,
        category="spot",
        symbol=SYMBOL,
        orderFilter="StopOrder",
    )

    out["final_ws_msg_count"] = len(ws.snapshot())
    out["all_ws_messages"] = ws.snapshot()
    out["finished_at"] = _now_iso()
    ws.stop()
    time.sleep(1)

    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {OUT_PATH}")
    print(f"Total WS msgs: {out['final_ws_msg_count']}")


if __name__ == "__main__":
    main()
