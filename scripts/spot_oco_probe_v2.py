"""Bybit V5 Spot OCO probe v2 — close G5/G7/G14 + scenarios 2 & 5.

Targets (per trading-logic-reviewer Sonnet 4.6 BLOCK):
  G5  fee-currency-BTC reduces actual qty → Sell at ordered qty must fail 170131
  G7  Stop order timeInForce=GTC accepted on Spot?
  G14 testnet env diff vs Demo
  S2  marketUnit=quoteCoin on entry — does Bybit auto-handle BTC delta?
  S5  invalid SL triggerPrice → error class + cleanup behavior

Output: scripts/spot_oco_probe_v2_output.json
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

OUT_PATH = REPO_ROOT / "scripts" / "spot_oco_probe_v2_output.json"
SYMBOL = "BTCUSDT"
TARGET_NOTIONAL_USDT = Decimal("50")


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class WSCapture:
    def __init__(self, *, api_key: str, api_secret: str, demo: bool, testnet: bool) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._demo = demo
        self._testnet = testnet
        self._ws: Any = None
        self._msgs: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _on_order(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "order", "msg": m})

    def _on_exec(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "execution", "msg": m})

    def start(self) -> None:
        self._ws = WebSocket(
            testnet=self._testnet,
            demo=self._demo,
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

    def find_order_event(self, order_id: str) -> dict[str, Any] | None:
        with self._lock:
            for m in reversed(self._msgs):
                if m["topic"] != "order":
                    continue
                for d in m["msg"].get("data", []):
                    if d.get("orderId") == order_id:
                        return d
        return None


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


def run_demo(s: Settings) -> dict[str, Any]:
    out: dict[str, Any] = {
        "env": "demo (api-demo.bybit.com, virtual money)",
        "started_at": _now_iso(),
    }

    http = HTTP(testnet=False, demo=True, api_key=s.bybit_api_key, api_secret=s.bybit_api_secret)

    print(f"[{_now_iso()}] DEMO instruments-info...")
    r = http.get_instruments_info(category="spot", symbol=SYMBOL)
    item = r["result"]["list"][0]
    step = Decimal(item["lotSizeFilter"]["basePrecision"])
    tick = Decimal(item["priceFilter"]["tickSize"])
    min_notional = Decimal(item["lotSizeFilter"].get("minOrderAmt", "5"))
    out["filters"] = {"step": str(step), "tick": str(tick), "min_notional": str(min_notional)}

    r = http.get_tickers(category="spot", symbol=SYMBOL)
    last = Decimal(r["result"]["list"][0]["lastPrice"])
    qty_ordered = _round_qty(TARGET_NOTIONAL_USDT / last, step)
    tp = _round_price(last * Decimal("1.02"), tick, mode="up")
    sl_valid = _round_price(last * Decimal("0.98"), tick, mode="down")
    sl_invalid_above = _round_price(last * Decimal("1.05"), tick, mode="up")  # SL > entry → invalid
    out["computed"] = {
        "last": str(last),
        "qty_ordered": str(qty_ordered),
        "tp": str(tp),
        "sl_valid": str(sl_valid),
        "sl_invalid_above": str(sl_invalid_above),
    }
    print(f"  last={last} qty={qty_ordered} TP={tp} SL_valid={sl_valid}")

    print(f"[{_now_iso()}] starting WS...")
    ws = WSCapture(api_key=s.bybit_api_key, api_secret=s.bybit_api_secret, demo=True, testnet=False)
    ws.start()
    time.sleep(3)

    # ===== S2: marketUnit=quoteCoin entry =====
    print(f"\n[{_now_iso()}] S2: Market BUY with marketUnit=quoteCoin (qty=USDT amount)")
    s2_link = f"v2-s2-quote-{uuid.uuid4().hex[:6]}"
    out["S2_quoteCoin_entry"] = _safe(
        "S2_quoteCoin_entry",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=str(TARGET_NOTIONAL_USDT),  # USDT notional, not BTC qty
        marketUnit="quoteCoin",
        orderLinkId=s2_link,
    )
    time.sleep(4)
    s2_resp = out["S2_quoteCoin_entry"]
    if s2_resp["ok"] and s2_resp["response"].get("retCode") == 0:
        s2_oid = s2_resp["response"]["result"]["orderId"]
        s2_event = ws.find_order_event(s2_oid)
        out["S2_quoteCoin_filled_event"] = s2_event
        if s2_event:
            print(
                f"  S2 filled: cumExecQty={s2_event.get('cumExecQty')} "
                f"cumExecFee={s2_event.get('cumExecFee')} feeCurrency={s2_event.get('feeCurrency')}"
            )

    # ===== G5: place 2 distinct entries, then probe Sell sizing =====
    print(f"\n[{_now_iso()}] G5: baseCoin Market BUY for fee-impact verification")
    g5_entry_link = f"v2-g5-entry-{uuid.uuid4().hex[:6]}"
    out["G5_entry"] = _safe(
        "G5_entry",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=str(qty_ordered),
        marketUnit="baseCoin",
        orderLinkId=g5_entry_link,
    )
    time.sleep(4)

    g5_filled_event = None
    cum_exec_qty: Decimal | None = None
    cum_exec_fee: Decimal | None = None
    if out["G5_entry"]["ok"] and out["G5_entry"]["response"].get("retCode") == 0:
        g5_oid = out["G5_entry"]["response"]["result"]["orderId"]
        g5_filled_event = ws.find_order_event(g5_oid)
        out["G5_entry_filled_event"] = g5_filled_event
        if g5_filled_event:
            cum_exec_qty = Decimal(g5_filled_event["cumExecQty"])
            cum_exec_fee = Decimal(g5_filled_event["cumExecFee"])
            print(
                f"  G5 entry: ordered={qty_ordered} cumExecQty={cum_exec_qty} "
                f"cumExecFee={cum_exec_fee} fee_ccy={g5_filled_event.get('feeCurrency')}"
            )
            out["G5_actual_owned_btc"] = str(cum_exec_qty - cum_exec_fee)

    # G5a: Sell at ordered qty (expect 170131 if fee in BTC reduced position)
    print(f"\n[{_now_iso()}] G5a: Sell Limit @ TP at ORDERED qty={qty_ordered} (expect insufficient)")
    g5a_link = f"v2-g5a-ordered-{uuid.uuid4().hex[:6]}"
    out["G5a_sell_ordered_qty"] = _safe(
        "G5a_sell_ordered_qty",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Limit",
        qty=str(qty_ordered),
        price=str(tp),
        timeInForce="GTC",
        orderLinkId=g5a_link,
    )

    # G5b: Sell at cumExecQty (likely also fail because fee was BTC)
    if cum_exec_qty is not None:
        print(f"[{_now_iso()}] G5b: Sell Limit @ TP at cumExecQty={cum_exec_qty} (raw cumExec)")
        g5b_link = f"v2-g5b-cumexec-{uuid.uuid4().hex[:6]}"
        out["G5b_sell_cumExecQty"] = _safe(
            "G5b_sell_cumExecQty",
            http.place_order,
            category="spot",
            symbol=SYMBOL,
            side="Sell",
            orderType="Limit",
            qty=str(cum_exec_qty),
            price=str(tp),
            timeInForce="GTC",
            orderLinkId=g5b_link,
        )

    # G5c: Sell at cumExecQty - cumExecFee, step-floored (the SAFE sizing)
    if cum_exec_qty is not None and cum_exec_fee is not None:
        safe_qty = _round_qty(cum_exec_qty - cum_exec_fee, step)
        print(f"[{_now_iso()}] G5c: Sell Limit @ TP at SAFE qty={safe_qty} (cum-fee, floored)")
        g5c_link = f"v2-g5c-safe-{uuid.uuid4().hex[:6]}"
        out["G5c_sell_safe_qty"] = _safe(
            "G5c_sell_safe_qty",
            http.place_order,
            category="spot",
            symbol=SYMBOL,
            side="Sell",
            orderType="Limit",
            qty=str(safe_qty),
            price=str(tp),
            timeInForce="GTC",
            orderLinkId=g5c_link,
        )
        out["G5_safe_qty_computed"] = str(safe_qty)

    # ===== G7: Stop with timeInForce=GTC =====
    print(f"\n[{_now_iso()}] G7: Stop Sell with timeInForce=GTC")
    g7_link = f"v2-g7-gtc-{uuid.uuid4().hex[:6]}"
    out["G7_stop_gtc"] = _safe(
        "G7_stop_gtc",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Market",
        qty=str(qty_ordered),
        marketUnit="baseCoin",
        orderFilter="StopOrder",
        triggerPrice=str(sl_valid),
        triggerDirection=2,
        timeInForce="GTC",
        orderLinkId=g7_link,
    )

    # ===== S5: invalid SL triggerPrice (above current → wrong direction for SELL stop) =====
    print(f"\n[{_now_iso()}] S5: Stop Sell with INVALID triggerPrice ABOVE current (sl={sl_invalid_above})")
    s5_link = f"v2-s5-bad-{uuid.uuid4().hex[:6]}"
    out["S5_invalid_sl"] = _safe(
        "S5_invalid_sl",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Sell",
        orderType="Market",
        qty=str(qty_ordered),
        marketUnit="baseCoin",
        orderFilter="StopOrder",
        triggerPrice=str(sl_invalid_above),
        triggerDirection=2,
        orderLinkId=s5_link,
    )

    time.sleep(3)
    out["ws_after_probes"] = ws.snapshot()

    # ===== Cleanup =====
    print(f"\n[{_now_iso()}] cleanup: cancel_all default + StopOrder")
    out["cleanup_default"] = _safe(
        "cleanup_default", http.cancel_all_orders, category="spot", symbol=SYMBOL
    )
    out["cleanup_stop"] = _safe(
        "cleanup_stop", http.cancel_all_orders, category="spot", symbol=SYMBOL, orderFilter="StopOrder"
    )

    # Flatten any remaining BTC via Market Sell at safe qty
    print(f"\n[{_now_iso()}] flatten: get wallet BTC then Market Sell")
    bal = _safe(
        "wallet_btc",
        http.get_wallet_balance,
        accountType="UNIFIED",
        coin="BTC",
    )
    out["wallet_btc"] = bal
    btc_qty = Decimal("0")
    try:
        coins = bal["response"]["result"]["list"][0]["coin"]
        for c in coins:
            if c["coin"] == "BTC":
                btc_qty = Decimal(c["walletBalance"])
                out["wallet_btc_walletBalance"] = c["walletBalance"]
                out["wallet_btc_availableToWithdraw"] = c.get("availableToWithdraw", "")
                out["wallet_btc_locked"] = c.get("locked", "")
                break
    except Exception as e:
        out["wallet_parse_err"] = str(e)
    if btc_qty > Decimal("0"):
        flat_qty = _round_qty(btc_qty, step)
        if flat_qty * last >= min_notional:
            print(f"  flattening {flat_qty} BTC")
            out["flatten_market_sell"] = _safe(
                "flatten_sell",
                http.place_order,
                category="spot",
                symbol=SYMBOL,
                side="Sell",
                orderType="Market",
                qty=str(flat_qty),
                marketUnit="baseCoin",
                orderLinkId=f"v2-flat-{uuid.uuid4().hex[:6]}",
            )
        else:
            out["flatten_skipped_below_min"] = str(flat_qty)

    out["all_ws_messages"] = ws.snapshot()
    out["finished_at"] = _now_iso()
    ws.stop()
    time.sleep(1)
    return out


def run_testnet(s: Settings) -> dict[str, Any]:
    """G14: sanity diff on api-testnet.bybit.com — keys may not be valid here."""
    out: dict[str, Any] = {
        "env": "testnet (api-testnet.bybit.com, separate network)",
        "started_at": _now_iso(),
        "note": "demo keys typically DO NOT work on testnet — expect 10003 invalid key",
    }
    http = HTTP(testnet=True, demo=False, api_key=s.bybit_api_key, api_secret=s.bybit_api_secret)
    out["G14_wallet_check"] = _safe(
        "G14_wallet_check", http.get_wallet_balance, accountType="UNIFIED", coin="USDT"
    )
    out["G14_b2_native_tpsl_attempt"] = _safe(
        "G14_b2_native_tpsl",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty="0.0005",
        marketUnit="baseCoin",
        takeProfit="120000",
        stopLoss="40000",
        tpslMode="Full",
        orderLinkId=f"v2-tn-b2-{uuid.uuid4().hex[:6]}",
    )
    out["finished_at"] = _now_iso()
    return out


def main() -> None:
    s = Settings()
    out = {
        "started_at": _now_iso(),
        "demo": run_demo(s),
        "testnet": run_testnet(s),
        "finished_at": _now_iso(),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {OUT_PATH}")


if __name__ == "__main__":
    main()
