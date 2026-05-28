"""S49 B1 BLOCKER — flatten/residual Market Sell must carry a deterministic orderLinkId.

bybit-api-reviewer (S49 tech-audit) BLOCKER B1: flatten/residual place_order calls
carried NO orderLinkId. _retry_with_backoff auto-retries on order-frequency rate-limit
codes (170005/170222). If a rate-limit code is returned AFTER the order landed
server-side → retry submits a SECOND Market Sell → double execution → money loss.

Fix: every flatten/residual placement gets a STABLE, deterministic orderLinkId so
Bybit dedupes the retry by orderLinkId (idempotency key). Stable across retries of
the SAME logical order ⇒ a re-submit is rejected as duplicate, not executed twice.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.execution.bybit.adapter import OrderAck, WalletSnapshot
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.marketdata.filters import BybitFilters
from src.risk.reason_codes import ReasonCode

BRACKET_ID = "deadbeef"


@dataclass
class _RecordingAdapter:
    """Records every place_order call (incl. order_link_id) for assertions."""

    _filters: BybitFilters
    placed_orders: list[dict] = field(default_factory=list)
    cancelled_ids: list[tuple[str, str]] = field(default_factory=list)
    cancel_all_called: bool = False
    last_cancel_all_symbol: str | None = None
    wallet_balance: Decimal = Decimal("0.001234")
    wallet_locked: Decimal = Decimal("0")

    def cancel_all_orders(self, *, symbol: str) -> None:
        self.cancel_all_called = True
        self.last_cancel_all_symbol = symbol

    def cancel_order(self, *, symbol: str, order_id: str):
        self.cancelled_ids.append((symbol, order_id))

        @dataclass
        class _CR:
            cancelled: bool = True
            reason_code: object | None = None

        return _CR()

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
        return WalletSnapshot(
            coin=coin,
            wallet_balance=self.wallet_balance,
            available=self.wallet_balance - self.wallet_locked,
            locked=self.wallet_locked,
        )

    def place_order(self, *, symbol, side, qty, order_link_id=None):
        self.placed_orders.append(
            {"symbol": symbol, "side": side, "qty": str(qty), "orderLinkId": order_link_id}
        )
        return OrderAck(order_id=f"EX-{len(self.placed_orders)}", order_link_id=order_link_id)


def _filters() -> BybitFilters:
    return BybitFilters(
        symbol="BTCUSDT",
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.000001"),
        max_order_qty=Decimal("100"),
        min_order_amt=Decimal("5"),
    )


def _repo(tmp_path: Path) -> ExecutionStateRepo:
    conn = sqlite3.connect(tmp_path / "exec.db")
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    return ExecutionStateRepo(conn)


def _seed(repo: ExecutionStateRepo, *, state: ExecutionState, tp_oid: str | None) -> None:
    repo.upsert(
        ExecutionStateRow(
            symbol="BTCUSDT",
            state=state,
            position_qty=Decimal("0.001234"),
            entry_price=Decimal("65000"),
            oco_main_order_id=None,
            bracket_id=BRACKET_ID,
            oco_tp_order_id=tp_oid,
            oco_sl_order_id="EX-sl",
            expected_oco_qty=Decimal("0.001234"),
            arming_started_at=None,
            last_attempt_num=3,
            updated_at=datetime.now(tz=UTC).isoformat(),
        )
    )


def _coord(repo: ExecutionStateRepo, adapter: _RecordingAdapter) -> Coordinator:
    c = Coordinator(adapter=adapter, repo=repo, reconciler=None, symbol="BTCUSDT", base_coin="BTC")
    c._bootstrap_done = True
    return c


# --- emergency flatten ---


def test_emergency_flatten_market_sell_carries_order_link_id(tmp_path):
    adapter = _RecordingAdapter(_filters=_filters())
    repo = _repo(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMED, tp_oid=None)
    coord = _coord(repo, adapter)

    coord.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)

    sells = [o for o in adapter.placed_orders if o["side"] == "Sell"]
    assert len(sells) == 1
    assert sells[0]["orderLinkId"], "emergency flatten Market Sell must carry an orderLinkId"
    # Deterministic: derived from bracket_id, recognizable as a flatten leg.
    assert BRACKET_ID in sells[0]["orderLinkId"]
    assert len(sells[0]["orderLinkId"]) <= 36, "Bybit orderLinkId max length is 36"


# --- residual flatten (SL IOC partial) ---


def test_residual_flatten_market_sell_carries_order_link_id(tmp_path):
    adapter = _RecordingAdapter(_filters=_filters())
    repo = _repo(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMED, tp_oid="TP-LIVE")
    coord = _coord(repo, adapter)

    coord.on_order_event(
        {
            "orderLinkId": f"oco-{BRACKET_ID}-sl-3",
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0.0003",
        }
    )

    sells = [o for o in adapter.placed_orders if o["side"] == "Sell"]
    assert len(sells) == 1
    assert sells[0]["orderLinkId"], "residual flatten Market Sell must carry an orderLinkId"
    assert BRACKET_ID in sells[0]["orderLinkId"]
    assert len(sells[0]["orderLinkId"]) <= 36


# --- idempotency: a retry of the SAME logical placement reuses the SAME orderLinkId ---


def test_retry_of_placement_reuses_same_order_link_id(monkeypatch):
    """_retry_with_backoff re-invokes the SAME callable on a rate-limit code.

    Because the orderLinkId is computed deterministically BEFORE the retry loop
    and embedded in the call, both attempts carry the identical orderLinkId →
    Bybit dedupes the second submission (no double execution).
    """
    import time as _time

    from src.execution.bybit import adapter as adapter_mod

    monkeypatch.setattr(_time, "sleep", lambda *_: None)

    # A fake pybit HTTP that returns a rate-limit code once, then success — and
    # records the orderLinkId seen on EACH attempt.
    seen_link_ids: list[str | None] = []
    call_state = {"n": 0}

    class _FakeHTTP:
        def place_order(self, **payload):
            seen_link_ids.append(payload.get("orderLinkId"))
            call_state["n"] += 1
            if call_state["n"] == 1:
                return {"retCode": 170005, "retMsg": "order frequency limit", "result": {}}
            return {
                "retCode": 0,
                "result": {"orderId": "EX-1", "orderLinkId": payload.get("orderLinkId")},
            }

    class _FakeRest:
        _http = _FakeHTTP()

    real_adapter = adapter_mod.BybitMarketAdapter(rest=_FakeRest(), filters=_filters())
    ack = real_adapter.place_order(
        symbol="BTCUSDT",
        side="Sell",
        qty=Decimal("0.001"),
        order_link_id=f"flat-{BRACKET_ID}-res-3",
    )

    assert call_state["n"] == 2, "expected one rate-limit retry"
    assert (
        seen_link_ids[0] == seen_link_ids[1]
    ), "retry must reuse the SAME orderLinkId so Bybit dedupes the duplicate submission"
    assert ack.order_link_id == f"flat-{BRACKET_ID}-res-3"
