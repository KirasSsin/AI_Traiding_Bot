"""Bybit V5 Spot OCO probe v3 — close v3-A/B/C/D + optional E.

Targets (per trading-logic-reviewer 2nd round BLOCK):
  v3-A  Stop trigger event sequence (Untriggered → ??? → Filled): does `Triggered` exist on Spot?
  v3-B  Clean-wallet G5 reproduction: Sell at exact cumExecQty must fail 170131
  v3-C  WS `wallet` private topic — event shape on Buy
  v3-D  Stop submitted with TIF=GTC — does post-Filled echo show GTC or IOC?
  v3-E  Phantom SL (above current with direction=2) — stays Untriggered indefinitely

Flow chosen to minimize wallet contamination:
  1. Drain BTC balance via Market Sell (start clean)
  2. v3-B Buy → Sell ordered (expect 170131) → Sell safe (expect rc=0) → cancel safe Sell
  3. v3-C wallet topic verified concurrently across all probes
  4. v3-A/D fresh entry → place Stop close-to-market with GTC → wait fire → capture sequence
  5. v3-E phantom SL → wait 30s → GET order

Output: scripts/spot_oco_probe_v3_output.json
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

OUT_PATH = REPO_ROOT / "scripts" / "spot_oco_probe_v3_output.json"
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

    def _on_order(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "order", "msg": m})

    def _on_exec(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "execution", "msg": m})

    def _on_wallet(self, m: dict[str, Any]) -> None:
        with self._lock:
            self._msgs.append({"ts": _now_iso(), "topic": "wallet", "msg": m})

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
        self._ws.wallet_stream(callback=self._on_wallet)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._msgs)

    def stop(self) -> None:
        if self._ws and hasattr(self._ws, "exit"):
            try:
                self._ws.exit()
            except Exception:
                pass

    def order_events_for(self, order_id: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        with self._lock:
            for m in self._msgs:
                if m["topic"] != "order":
                    continue
                for d in m["msg"].get("data", []):
                    if d.get("orderId") == order_id:
                        out.append({"ts": m["ts"], "data": d})
        return out

    def wallet_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return [m for m in self._msgs if m["topic"] == "wallet"]


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


def _get_btc_balance(http: HTTP) -> Decimal:
    try:
        r = http.get_wallet_balance(accountType="UNIFIED", coin="BTC")
        for c in r["result"]["list"][0]["coin"]:
            if c["coin"] == "BTC":
                return Decimal(c["walletBalance"] or "0")
    except Exception:
        return Decimal("0")
    return Decimal("0")


def _get_last_price(http: HTTP) -> Decimal:
    r = http.get_tickers(category="spot", symbol=SYMBOL)
    return Decimal(r["result"]["list"][0]["lastPrice"])


def main() -> None:
    s = Settings()
    out: dict[str, Any] = {"started_at": _now_iso(), "env": "demo"}

    http = HTTP(testnet=False, demo=True, api_key=s.bybit_api_key, api_secret=s.bybit_api_secret)

    print(f"[{_now_iso()}] instruments-info...")
    r = http.get_instruments_info(category="spot", symbol=SYMBOL)
    item = r["result"]["list"][0]
    step = Decimal(item["lotSizeFilter"]["basePrecision"])
    tick = Decimal(item["priceFilter"]["tickSize"])
    min_notional = Decimal(item["lotSizeFilter"].get("minOrderAmt", "5"))
    out["filters"] = {"step": str(step), "tick": str(tick), "min_notional": str(min_notional)}

    last0 = _get_last_price(http)
    out["last_price_initial"] = str(last0)

    print(f"[{_now_iso()}] starting WS (order+execution+wallet)...")
    ws = WSCapture(api_key=s.bybit_api_key, api_secret=s.bybit_api_secret)
    ws.start()
    time.sleep(3)

    # ===== STEP 0: drain BTC balance to ~0 for clean v3-B =====
    print(f"\n[{_now_iso()}] STEP 0: drain wallet")
    btc_pre = _get_btc_balance(http)
    out["wallet_btc_before_drain"] = str(btc_pre)
    print(f"  BTC before drain: {btc_pre}")
    if btc_pre > Decimal("0"):
        drain_qty = _round_qty(btc_pre, step)
        if drain_qty * last0 >= min_notional:
            out["drain_sell"] = _safe(
                "drain_sell",
                http.place_order,
                category="spot",
                symbol=SYMBOL,
                side="Sell",
                orderType="Market",
                qty=str(drain_qty),
                marketUnit="baseCoin",
                orderLinkId=f"v3-drain-{uuid.uuid4().hex[:6]}",
            )
            time.sleep(3)
        else:
            out["drain_skipped_dust"] = str(drain_qty)
    btc_after_drain = _get_btc_balance(http)
    out["wallet_btc_after_drain"] = str(btc_after_drain)
    print(f"  BTC after drain: {btc_after_drain}")

    # ===== v3-B: clean-wallet G5 reproduction =====
    print(f"\n[{_now_iso()}] v3-B: clean-wallet entry + Sell sizing")
    last_b = _get_last_price(http)
    qty_b = _round_qty(TARGET_NOTIONAL_USDT / last_b, step)
    tp_b = _round_price(last_b * Decimal("1.02"), tick, mode="up")
    out["v3B_computed"] = {"last": str(last_b), "qty": str(qty_b), "tp": str(tp_b)}

    v3b_entry_link = f"v3b-entry-{uuid.uuid4().hex[:6]}"
    out["v3B_entry"] = _safe(
        "v3B_entry",
        http.place_order,
        category="spot",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=str(qty_b),
        marketUnit="baseCoin",
        orderLinkId=v3b_entry_link,
    )
    time.sleep(4)

    cum_exec_qty: Decimal | None = None
    cum_exec_fee: Decimal | None = None
    if out["v3B_entry"]["ok"] and out["v3B_entry"]["response"].get("retCode") == 0:
        oid_b = out["v3B_entry"]["response"]["result"]["orderId"]
        events = ws.order_events_for(oid_b)
        out["v3B_entry_events"] = events
        for ev in reversed(events):
            d = ev["data"]
            if d.get("orderStatus") == "Filled":
                cum_exec_qty = Decimal(d["cumExecQty"])
                cum_exec_fee = Decimal(d["cumExecFee"])
                out["v3B_filled_summary"] = {
                    "ordered_qty": str(qty_b),
                    "cumExecQty": str(cum_exec_qty),
                    "cumExecFee": str(cum_exec_fee),
                    "feeCurrency": d.get("feeCurrency"),
                    "real_owned_btc": str(cum_exec_qty - cum_exec_fee),
                }
                break

    btc_after_entry = _get_btc_balance(http)
    out["v3B_wallet_btc_after_entry"] = str(btc_after_entry)
    print(f"  cumExecQty={cum_exec_qty} cumExecFee={cum_exec_fee} wallet_now={btc_after_entry}")

    if cum_exec_qty is not None and cum_exec_fee is not None:
        # v3-B-1: Sell at exact cumExecQty (NO fee subtraction) — expect 170131
        print(f"  v3-B-1: Sell Limit @ TP at exact cumExecQty={cum_exec_qty}")
        out["v3B1_sell_at_cumExecQty"] = _safe(
            "v3B1_sell_at_cumExecQty",
            http.place_order,
            category="spot",
            symbol=SYMBOL,
            side="Sell",
            orderType="Limit",
            qty=str(cum_exec_qty),
            price=str(tp_b),
            timeInForce="GTC",
            orderLinkId=f"v3b1-{uuid.uuid4().hex[:6]}",
        )

        # v3-B-2: Sell at safe step_floor(cumExecQty - cumExecFee) — expect rc=0
        safe_qty = _round_qty(cum_exec_qty - cum_exec_fee, step)
        print(f"  v3-B-2: Sell Limit @ TP at safe qty={safe_qty}")
        out["v3B2_sell_at_safe_qty"] = _safe(
            "v3B2_sell_at_safe_qty",
            http.place_order,
            category="spot",
            symbol=SYMBOL,
            side="Sell",
            orderType="Limit",
            qty=str(safe_qty),
            price=str(tp_b),
            timeInForce="GTC",
            orderLinkId=f"v3b2-{uuid.uuid4().hex[:6]}",
        )
        out["v3B_safe_qty"] = str(safe_qty)

    # cancel any open Sells before next phase
    time.sleep(2)
    out["v3B_cleanup"] = _safe("v3B_cleanup", http.cancel_all_orders, category="spot", symbol=SYMBOL)
    time.sleep(2)

    # ===== v3-A + v3-D: trigger a Stop, capture full orderStatus sequence + post-Filled TIF =====
    print(f"\n[{_now_iso()}] v3-A/D: place Stop close-to-market with GTC, wait fire")
    last_ad = _get_last_price(http)
    btc_for_stop = _get_btc_balance(http)
    safe_for_stop = _round_qty(btc_for_stop, step)
    out["v3AD_pre"] = {"last": str(last_ad), "wallet_btc": str(btc_for_stop), "safe_qty": str(safe_for_stop)}

    # Place Stop with triggerPrice = last + 1 tick, direction=1 (rising). Fires on next uptick.
    # Use SELL Stop (we own BTC). Direction=1 means trigger when price >= triggerPrice.
    trig_price = _round_price(last_ad + tick, tick, mode="up")

    if safe_for_stop * last_ad >= min_notional:
        v3ad_link = f"v3ad-stop-{uuid.uuid4().hex[:6]}"
        out["v3AD_place_stop_GTC"] = _safe(
            "v3AD_place_stop_GTC",
            http.place_order,
            category="spot",
            symbol=SYMBOL,
            side="Sell",
            orderType="Market",
            qty=str(safe_for_stop),
            marketUnit="baseCoin",
            orderFilter="StopOrder",
            triggerPrice=str(trig_price),
            triggerDirection=1,
            timeInForce="GTC",
            orderLinkId=v3ad_link,
        )

        if out["v3AD_place_stop_GTC"]["ok"] and out["v3AD_place_stop_GTC"]["response"].get("retCode") == 0:
            oid_ad = out["v3AD_place_stop_GTC"]["response"]["result"]["orderId"]
            print(f"  Stop placed @ trigger={trig_price} (last={last_ad}), waiting up to 60s for fire...")
            fired = False
            for _ in range(60):
                time.sleep(1)
                events = ws.order_events_for(oid_ad)
                for ev in events:
                    if ev["data"].get("orderStatus") in ("Filled", "PartiallyFilled"):
                        fired = True
                        break
                if fired:
                    break
            time.sleep(2)
            final_events = ws.order_events_for(oid_ad)
            out["v3AD_event_sequence"] = final_events
            statuses = [ev["data"].get("orderStatus") for ev in final_events]
            tifs = [ev["data"].get("timeInForce") for ev in final_events]
            out["v3AD_status_sequence"] = statuses
            out["v3AD_tif_sequence"] = tifs
            print(f"  status sequence: {statuses}")
            print(f"  TIF sequence: {tifs}")
        else:
            out["v3AD_place_failed"] = True
    else:
        out["v3AD_skipped_dust"] = str(safe_for_stop)

    # ===== v3-E: phantom SL — triggerPrice ABOVE current with direction=2 (falling) =====
    print(f"\n[{_now_iso()}] v3-E: phantom SL (price above current, direction=falling)")
    last_e = _get_last_price(http)
    btc_e = _get_btc_balance(http)
    safe_e = _round_qty(btc_e, step)
    if safe_e * last_e >= min_notional:
        phantom_trig = _round_price(last_e * Decimal("1.05"), tick, mode="up")  # 5% ABOVE current
        v3e_link = f"v3e-phantom-{uuid.uuid4().hex[:6]}"
        out["v3E_place_phantom"] = _safe(
            "v3E_place_phantom",
            http.place_order,
            category="spot",
            symbol=SYMBOL,
            side="Sell",
            orderType="Market",
            qty=str(safe_e),
            marketUnit="baseCoin",
            orderFilter="StopOrder",
            triggerPrice=str(phantom_trig),
            triggerDirection=2,  # falling — but trigger price is ABOVE current, so impossible
            orderLinkId=v3e_link,
        )
        if out["v3E_place_phantom"]["ok"] and out["v3E_place_phantom"]["response"].get("retCode") == 0:
            oid_e = out["v3E_place_phantom"]["response"]["result"]["orderId"]
            print(f"  phantom placed @ trigger={phantom_trig} (last={last_e}), waiting 15s...")
            time.sleep(15)
            r_e = _safe("v3E_get_order", http.get_open_orders, category="spot", symbol=SYMBOL, orderId=oid_e)
            out["v3E_get_after_15s"] = r_e
            r_e_filter = _safe(
                "v3E_get_stop", http.get_open_orders, category="spot", symbol=SYMBOL,
                orderFilter="StopOrder", orderId=oid_e,
            )
            out["v3E_get_stop_filter"] = r_e_filter
    else:
        out["v3E_skipped_dust"] = str(safe_e)

    # ===== Cleanup =====
    print(f"\n[{_now_iso()}] cleanup")
    out["cleanup_default"] = _safe("cleanup_default", http.cancel_all_orders, category="spot", symbol=SYMBOL)
    out["cleanup_stop"] = _safe(
        "cleanup_stop", http.cancel_all_orders, category="spot", symbol=SYMBOL, orderFilter="StopOrder"
    )
    time.sleep(2)
    btc_final = _get_btc_balance(http)
    out["wallet_btc_final"] = str(btc_final)
    if btc_final > Decimal("0"):
        flat_qty = _round_qty(btc_final, step)
        last_f = _get_last_price(http)
        if flat_qty * last_f >= min_notional:
            out["final_flatten"] = _safe(
                "final_flatten", http.place_order,
                category="spot", symbol=SYMBOL, side="Sell", orderType="Market",
                qty=str(flat_qty), marketUnit="baseCoin",
                orderLinkId=f"v3-final-flat-{uuid.uuid4().hex[:6]}",
            )

    out["wallet_event_count"] = len(ws.wallet_events())
    out["wallet_events_sample"] = ws.wallet_events()[:3]
    out["all_ws_message_count"] = len(ws.snapshot())
    out["finished_at"] = _now_iso()
    ws.stop()
    time.sleep(1)

    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {OUT_PATH}")


if __name__ == "__main__":
    main()
