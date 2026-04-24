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

    def get_order(self, *, symbol: str, order_id: str) -> dict | None:
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
    """Stub matching real OrderSnapshot field names (order_status, avg_price, cum_exec_fee)."""
    def __init__(self, status: str, avgPrice: Decimal):
        self.order_status = status
        self.avg_price = avgPrice
        self.cum_exec_fee = Decimal("0")
        self.fee_currency = "USDT"


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
    assert r.heal_context and r.heal_context["avg_price"] == "62000"


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


# ---------------------------------------------------------------------------
# Task 14: staleness check (heal_max_age_seconds)
# ---------------------------------------------------------------------------

def test_entry_pending_heal_blocked_by_staleness(monkeypatch):
    """ADR 0021 sub-decision 4: crash > heal_max_age_seconds → HALT not HEAL."""
    monkeypatch.setenv("HEAL_MAX_AGE_SECONDS", "3600")
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),
        open_orders=[],
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC) - timedelta(seconds=4000),  # stale > 3600
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "DIVERGENCE"
    assert r.halt_reason == "HALT_BOOTSTRAP_AMBIGUOUS"
    assert (r.heal_context or {}).get("sub_reason") == "stale_age"


# ---------------------------------------------------------------------------
# Task 15: EXIT_PENDING classification
# ---------------------------------------------------------------------------

def test_exit_pending_exited_when_position_flat_no_open_orders():
    adapter = _FakeAdapter(
        exch_qty=Decimal("0"),
        open_orders=[],
        entry_order=None,
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local, expected_state=ExecutionState.EXIT_PENDING)
    assert r.verdict == "EXITED"
    assert r.halt_reason is None


def test_exit_pending_halt_when_position_still_there():
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),  # still open
        open_orders=[],
        entry_order=None,
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local, expected_state=ExecutionState.EXIT_PENDING)
    assert r.verdict == "DIVERGENCE"
    assert r.halt_reason == "HALT_EXIT_RECONCILE_DIVERGENCE"


# ---------------------------------------------------------------------------
# Task 16: _wallet_cache + on_wallet_event
# ---------------------------------------------------------------------------

def test_reconciler_reads_wallet_cache_first(monkeypatch):
    """WS-fed cache hit → no REST call."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("99.9"),  # REST value — should NOT be used
        open_orders=[],
        entry_order=None,
    )
    rest_calls = []
    orig_get_wallet = adapter.get_wallet_balance
    def spy(*a, **kw):
        rest_calls.append((a, kw))
        return orig_get_wallet(*a, **kw)
    adapter.get_wallet_balance = spy

    reco = Reconciler(adapter=adapter)
    reco.on_wallet_event({"coin": "BTC", "walletBalance": "0.001"})  # WS-fed
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local)
    assert r.exch_qty == Decimal("0.001")
    assert rest_calls == []  # REST not called


def test_reconciler_falls_back_to_rest_on_cache_miss():
    adapter = _FakeAdapter(exch_qty=Decimal("0.002"), open_orders=[], entry_order=None)
    reco = Reconciler(adapter=adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.002"), entry_order_id=None)
    r = reco.reconcile(local)
    assert r.exch_qty == Decimal("0.002")  # came from REST adapter
