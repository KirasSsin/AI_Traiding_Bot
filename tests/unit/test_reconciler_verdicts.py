"""Reconciler 4-valued verdict tests (ADR 0021 sub-decision 3)."""
from decimal import Decimal

import pytest

from src.execution.reconciler import ReconcileResult
from src.execution.bybit.adapter import WalletSnapshot


class _FakeAdapter:
    """Minimal adapter stub satisfying ExchangeQueryClient + get_order for Task 12 tests."""

    def __init__(self, *, exch_qty: Decimal, open_orders: list, entry_order: dict | None):
        self._exch_qty = exch_qty
        self._open_orders = open_orders
        self._entry_order = entry_order

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
        return WalletSnapshot(
            coin=coin,
            wallet_balance=self._exch_qty,
            available=Decimal("0"),
            locked=self._exch_qty,
        )

    def get_open_orders(self, *, symbol: str) -> list:
        return self._open_orders

    def get_order(self, *, order_id: str) -> dict | None:
        return self._entry_order


def test_reconcile_result_verdict_is_4_valued():
    """Verdict must be one of AGREE / DIVERGENCE / HEAL_ENTRY_FILLED / EXITED."""
    r = ReconcileResult(
        verdict="AGREE",
        exch_qty=Decimal("0"),
        entry_price=None,
        halt_reason=None,
        heal_context=None,
    )
    assert r.verdict == "AGREE"


def test_reconcile_result_heal_context_field_exists():
    r = ReconcileResult(
        verdict="HEAL_ENTRY_FILLED",
        exch_qty=Decimal("0.001"),
        entry_price=Decimal("62000"),
        halt_reason=None,
        heal_context={"avgPrice": "62000", "cumExecFee": "0.05"},
    )
    assert r.heal_context["avgPrice"] == "62000"


def test_reconcile_result_rejects_unknown_verdict():
    with pytest.raises((ValueError, TypeError)):
        ReconcileResult(
            verdict="WHATEVER",
            exch_qty=Decimal("0"),
            entry_price=None,
            halt_reason=None,
            heal_context=None,
        )


# ---------------------------------------------------------------------------
# Task 12: Reconciler.reconcile() expected_state kw + adapter= alias
# ---------------------------------------------------------------------------

from src.execution.reconciler import Reconciler, LocalState  # noqa: E402
from src.execution.state_machine import ExecutionState  # noqa: E402


def test_reconcile_accepts_expected_state_kw_optional():
    """Backward compat: existing callers w/o expected_state still work."""
    fake_adapter = _FakeAdapter(exch_qty=Decimal("0.001"), open_orders=[], entry_order=None)
    reco = Reconciler(adapter=fake_adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local)  # no expected_state → binary path
    assert r.verdict == "AGREE"


def test_reconcile_accepts_expected_state_entry_pending():
    """New path: expected_state provided → 4-valued classification."""
    fake_adapter = _FakeAdapter(exch_qty=Decimal("0.001"), open_orders=[], entry_order=None)
    reco = Reconciler(adapter=fake_adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0"), entry_order_id="x")
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    # Classification in next task; just verify call doesn't crash.
    assert r.verdict in ("AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED")


# ---------------------------------------------------------------------------
# Task 13: ENTRY_PENDING HEAL_ENTRY_FILLED path
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta  # noqa: E402


class _EntryOrder:
    def __init__(self, status: str, avgPrice: Decimal):
        self.status = status
        self.avgPrice = avgPrice


def test_entry_pending_heal_when_filled_position_matches_no_orphans(tmp_path):
    """ADR 0021 sub-decision 3: all 3 conditions → HEAL_ENTRY_FILLED."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),
        open_orders=[],  # no orphan TP/SL
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC) - timedelta(seconds=30),  # fresh
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "HEAL_ENTRY_FILLED"
    assert r.entry_price == Decimal("62000")
    assert r.heal_context and r.heal_context["avgPrice"] == "62000"


def test_entry_pending_halt_when_position_short_of_expected(tmp_path):
    """Partial fill + no orphans → still DIVERGENCE (HEAL requires exact/overfill above dust)."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.0001"),  # way below expected 0.001
        open_orders=[],
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC),
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "DIVERGENCE"
    assert r.halt_reason == "HALT_BOOTSTRAP_AMBIGUOUS"


def test_entry_pending_halt_when_orphan_open_orders_exist(tmp_path):
    """If any open orders exist for bracket → not narrow HEAL (that's OCO_ARMING path)."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),
        open_orders=[{"orderLinkId": "oco-abc-TP-1", "orderId": "tp1"}],
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC),
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "DIVERGENCE"
