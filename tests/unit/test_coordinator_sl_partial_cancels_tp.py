"""Sprint 6 trading-logic-reviewer Blocker #4 — SL IOC partial must cancel TP sibling.

Bybit Spot Stop fires as IOC. A partial fill leaves residual exposure that
the coordinator flattens via Market Sell. The TP leg, however, is still
live on the book. If the residual flatten lands first and we transition
RESIDUAL_FLATTENED → FLAT, the orphan TP can self-fill on the next bid
spike — opening a phantom short on Spot (the venue rejects the fill, but
some accounts allow margin/cross which will leak).

Invariant: before placing the residual flatten Market Sell, cancel the
stored oco_tp_order_id (best-effort: 110001 OK, exceptions logged + dropped).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.execution.bybit.errors import ReasonCode as AdapterReasonCode
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow

BRACKET_ID = "feedface"
TP_OID = "TP-LIVE"
SL_OID = "SL-LIVE"
SL_LID = f"oco-{BRACKET_ID}-sl-1"


@dataclass
class _CancelResult:
    cancelled: bool
    reason_code: object | None = None


class _StubAdapter:
    # S55 ARCH-03/BYBIT-05: public venue-filter accessors the Coordinator reads
    # (step_size for _qty_step / step-floor, min_order_qty for dust detection).
    step_size = Decimal("0.0001")
    min_order_qty = Decimal("0.0001")

    def __init__(
        self,
        *,
        cancel_raises: bool = False,
        cancel_returns_already_terminal: bool = False,
        step_size: Decimal | None = None,
        min_order_qty: Decimal | None = None,
    ) -> None:
        self.events: list[tuple[str, dict]] = []
        self._cancel_raises = cancel_raises
        self._cancel_returns_already_terminal = cancel_returns_already_terminal
        if step_size is not None:
            self.step_size = step_size
        if min_order_qty is not None:
            self.min_order_qty = min_order_qty

    def cancel_order(self, *, symbol: str, order_id: str):  # noqa: ARG002 — test-double interface
        self.events.append(("cancel", {"order_id": order_id}))
        if self._cancel_raises:
            raise RuntimeError("transient venue error")
        if self._cancel_returns_already_terminal:
            return _CancelResult(
                cancelled=False,
                reason_code=AdapterReasonCode.REJECT_ORDER_ALREADY_TERMINAL,
            )
        return _CancelResult(cancelled=True)

    def place_order(
        self,
        *,
        symbol: str,  # noqa: ARG002 — test-double interface
        side: str,
        qty: Decimal,
        order_link_id: str | None = None,
    ):
        self.events.append(
            ("place_order", {"side": side, "qty": qty, "order_link_id": order_link_id})
        )


def _seed(repo: ExecutionStateRepo, *, state: ExecutionState) -> None:
    repo.upsert(
        ExecutionStateRow(
            symbol="BTCUSDT",
            state=state,
            position_qty=Decimal("0.001"),
            entry_price=Decimal("65000"),
            oco_main_order_id=None,
            bracket_id=BRACKET_ID,
            oco_tp_order_id=TP_OID,
            oco_sl_order_id=SL_OID,
            expected_oco_qty=Decimal("0.001"),
            arming_started_at=None,
            last_attempt_num=1,
            updated_at=datetime.now(tz=UTC).isoformat(),
        )
    )


def _make(tmp_path: Path, **adapter_kwargs):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _StubAdapter(**adapter_kwargs)
    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=None, symbol="BTCUSDT", base_coin="BTC"
    )
    coord._bootstrap_done = True  # tests pre-date Task 22 guard; bypass for routing tests
    return coord, repo, adapter


def _evt_kinds(adapter: _StubAdapter) -> list[str]:
    return [k for k, _ in adapter.events]


# --- Behaviour ----


def test_sl_partial_cancels_tp_before_market_sell(tmp_path):
    coord, repo, adapter = _make(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event(
        {
            "orderLinkId": SL_LID,
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0.0003",
        }
    )
    kinds = _evt_kinds(adapter)
    # TP cancel MUST precede the residual market sell
    assert "cancel" in kinds, "TP sibling never cancelled"
    assert "place_order" in kinds, "residual market sell never placed"
    assert kinds.index("cancel") < kinds.index(
        "place_order"
    ), f"TP cancel must precede residual flatten, got order: {kinds}"
    cancel_args = next(args for k, args in adapter.events if k == "cancel")
    assert cancel_args["order_id"] == TP_OID
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


def test_sl_partial_cancels_tp_even_when_leaves_qty_zero(tmp_path):
    """leavesQty=0 means SL fully filled in this echo — no residual to flatten,
    but TP is still live on the book and must be cancelled."""
    coord, repo, adapter = _make(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event(
        {
            "orderLinkId": SL_LID,
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0",
        }
    )
    kinds = _evt_kinds(adapter)
    assert "cancel" in kinds, "TP sibling never cancelled (leaves=0 path)"
    assert "place_order" not in kinds  # nothing to flatten
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


def test_sl_partial_tp_cancel_already_terminal_is_ok(tmp_path):
    """TP returning 110001 (already filled) is non-fatal — proceed with
    residual flatten."""
    coord, repo, adapter = _make(tmp_path, cancel_returns_already_terminal=True)
    _seed(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event(
        {
            "orderLinkId": SL_LID,
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0.0003",
        }
    )
    kinds = _evt_kinds(adapter)
    assert kinds == ["cancel", "place_order"]
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


def test_sl_partial_tp_cancel_exception_does_not_block_flatten(tmp_path):
    """Transient cancel failure must not block the residual flatten —
    flatten is the safety-critical path."""
    coord, repo, adapter = _make(tmp_path, cancel_raises=True)
    _seed(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event(
        {
            "orderLinkId": SL_LID,
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0.0003",
        }
    )
    kinds = _evt_kinds(adapter)
    assert "cancel" in kinds  # we tried
    assert "place_order" in kinds  # and we still flattened
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


# --- S55 BYBIT-04: residual flatten carries a deterministic orderLinkId ----------


def _seed_no_bracket(repo: ExecutionStateRepo, *, state: ExecutionState) -> None:
    """Seed a row WITHOUT a bracket_id — exercises the BYBIT-04 fallback path."""
    repo.upsert(
        ExecutionStateRow(
            symbol="BTCUSDT",
            state=state,
            position_qty=Decimal("0.001"),
            entry_price=Decimal("65000"),
            oco_main_order_id=None,
            bracket_id=None,
            oco_tp_order_id=None,
            oco_sl_order_id=SL_OID,
            expected_oco_qty=Decimal("0.001"),
            arming_started_at=None,
            last_attempt_num=1,
            updated_at=datetime.now(tz=UTC).isoformat(),
        )
    )


def test_residual_flatten_orderlinkid_deterministic_when_bracket_id_none(tmp_path):
    """BYBIT-04: a residual flatten Market Sell placed when bracket_id is None must
    STILL carry a stable, deterministic orderLinkId (derived from the symbol). A None
    orderLinkId would defeat the 110072 idempotency dedupe on a _retry_with_backoff
    re-submit → risk of a SECOND Market Sell → oversell."""
    coord, repo, adapter = _make(tmp_path)
    _seed_no_bracket(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event(
        {
            "orderLinkId": "oco-orphan-sl-1",
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0.0003",
        }
    )
    place = next(args for k, args in adapter.events if k == "place_order")
    assert place["order_link_id"] is not None, "residual Sell placed with orderLinkId=None"
    assert place["order_link_id"].startswith("flat-"), place["order_link_id"]
    assert "BTCUSDT" in place["order_link_id"], place["order_link_id"]
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


def test_residual_flatten_orderlinkid_deterministic_with_bracket_id(tmp_path):
    """The bracket_id-present path keeps its existing deterministic orderLinkId."""
    coord, repo, adapter = _make(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event(
        {
            "orderLinkId": SL_LID,
            "orderStatus": "PartiallyFilled",
            "leavesQty": "0.0003",
        }
    )
    place = next(args for k, args in adapter.events if k == "place_order")
    assert place["order_link_id"] == f"flat-{BRACKET_ID}-res-1"
