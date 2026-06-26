"""S55 BLOCKER TL-01/TL-02: live-runtime OCO wiring (ADR 0020 sub-decisions 1+6+10+11).

Before this fix the runtime entry path called ONLY ``coordinator.start_bracket``
(Market BUY → ENTRY_PENDING). The TP Limit + SL Stop-Market legs are designed to
arm AFTER the entry fill via ``Coordinator.arm_oco``, but that helper had ZERO
production call sites — the entry-Filled branch in ``on_order_event`` only
transitioned ENTRY_PENDING → LONG_OPEN and returned, never arming. Net effect:
enter LONG → fill → LONG_OPEN forever with NO stop-loss, NO take-profit, and
every EXIT_FLAT_* signal dropped by ``manager.py`` (``flatten`` also had zero
production call sites). Unbounded-loss defect on a δ-TESTNET-activatable path.

These tests pin the three production call sites:
  1. entry-Filled WS event → arm_oco fires → TP Limit + SL Stop-Market placed
     (LONG_OPEN → OCO_ARMING → OCO_ARMED), qty net of base-coin fee (G5).
  2. EXIT_FLAT signal while position held → coordinator.flatten() called.
  3. reconcile_arming_ttl wired into the tick cadence → stuck OCO_ARMING HALTs.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.execution.bybit.adapter import OrderAck
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo
from src.marketdata.filters import BybitFilters

_SYMBOL = "BTCUSDT"
_BASE_COIN = "BTC"


@dataclass
class _FakeAdapter:
    """Records every leg placement; mimics BybitMarketAdapter surface used by Coordinator."""

    placed_orders: list[dict] = field(default_factory=list)
    limit_orders: list[dict] = field(default_factory=list)
    stop_orders: list[dict] = field(default_factory=list)
    _filters: BybitFilters = field(
        default_factory=lambda: BybitFilters(
            symbol=_SYMBOL,
            step_size=Decimal("0.000001"),
            tick_size=Decimal("0.01"),
            min_order_qty=Decimal("0.000048"),
            max_order_qty=Decimal("71.7"),
            min_order_amt=Decimal("5"),
        )
    )

    # S55 ARCH-03: public venue-filter accessors mirroring BybitMarketAdapter.
    @property
    def step_size(self) -> Decimal:
        return self._filters.step_size

    @property
    def min_order_qty(self) -> Decimal:
        return self._filters.min_order_qty

    def place_order(self, *, symbol, side, qty, order_link_id=None, extra_payload=None):
        self.placed_orders.append(
            {"symbol": symbol, "side": side, "qty": str(qty), "orderLinkId": order_link_id}
        )
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)

    def place_limit_order(self, *, symbol, side, qty, price, order_link_id):
        self.limit_orders.append(
            {
                "symbol": symbol,
                "side": side,
                "qty": str(qty),
                "price": str(price),
                "orderLinkId": order_link_id,
            }
        )
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)

    def place_stop_market_order(self, *, symbol, side, qty, trigger_price, order_link_id):
        self.stop_orders.append(
            {
                "symbol": symbol,
                "side": side,
                "qty": str(qty),
                "triggerPrice": str(trigger_price),
                "orderLinkId": order_link_id,
            }
        )
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)

    def cancel_all_orders(self, *, symbol):
        return None

    def get_wallet_balance(self, *, coin):
        from src.execution.bybit.adapter import WalletSnapshot

        return WalletSnapshot(
            coin=coin,
            wallet_balance=Decimal("0.001998"),
            available=Decimal("0.001998"),
            locked=Decimal("0"),
        )


def _make_coordinator(tmp_path: Path) -> tuple[Coordinator, ExecutionStateRepo, _FakeAdapter]:
    conn = sqlite3.connect(tmp_path / "exec.db")
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _FakeAdapter()
    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=None, symbol=_SYMBOL, base_coin=_BASE_COIN
    )
    coord.bootstrap()  # cold start (no row) → _bootstrap_done = True
    return coord, repo, adapter


# --- TL-01: entry-fill → arm_oco fires --------------------------------------


def test_entry_fill_arms_oco_legs(tmp_path):
    """start_bracket → entry-Filled WS event → TP+SL legs placed → OCO_ARMED."""
    coord, repo, adapter = _make_coordinator(tmp_path)

    bracket_id = coord.start_bracket(
        entry_qty=Decimal("0.002"),
        entry_side="Buy",
        tp_price=Decimal("70000.00"),
        sl_trigger_price=Decimal("60000.00"),
    )
    assert repo.get(_SYMBOL).state == ExecutionState.ENTRY_PENDING

    # Bybit entry-Filled WS echo: 0.1% taker fee deducted in base coin (BTC).
    coord.on_order_event(
        {
            "orderLinkId": f"oco-{bracket_id}-entry-1",
            "orderStatus": "Filled",
            "cumExecQty": "0.002",
            "cumExecFee": "0.000002",
            "feeCurrency": "BTC",
        }
    )

    row = repo.get(_SYMBOL)
    assert row.state == ExecutionState.OCO_ARMED, f"expected OCO_ARMED, got {row.state}"
    # TP Limit leg placed at tp_price, SL Stop-Market leg at sl_trigger_price.
    assert len(adapter.limit_orders) == 1, "TP Limit leg must be placed on entry fill"
    assert len(adapter.stop_orders) == 1, "SL Stop-Market leg must be placed on entry fill"
    assert adapter.limit_orders[0]["price"] == "70000.00"
    assert adapter.stop_orders[0]["triggerPrice"] == "60000.00"
    # G5 fee-aware qty: 0.002 - 0.000002 = 0.001998, floored to step (0.000001).
    assert adapter.limit_orders[0]["qty"] == "0.001998"
    assert adapter.stop_orders[0]["qty"] == "0.001998"
    assert row.oco_tp_order_id is not None
    assert row.oco_sl_order_id is not None


# --- TL-02: EXIT_FLAT signal → flatten --------------------------------------


def _settings(tmp_path: Path):
    s = MagicMock()
    s.runtime_kill_switch_path = str(tmp_path / ".kill_switch")
    s.runtime_bar_poll_cadence_seconds = 5.0
    s.runtime_bar_poll_stall_threshold = 24
    s.runtime_ws_check_alive_max_silence = 30.0
    s.runtime_warmup_bars = 50
    s.runtime_quality_threshold_pct = Decimal("0.005")
    s.s35_demo_active = False
    s.oco_arming_ttl_seconds = 60
    return s


def _shared_deps():
    from src.risk.manager import RiskSharedDeps

    return RiskSharedDeps(
        equity_tracker=MagicMock(), trade_repo=MagicMock(), state_repo=MagicMock()
    )


def _bar():
    from src.marketdata.models import Bar, DataQuality

    return Bar(
        symbol=_SYMBOL,
        interval="1h",
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        close_time=datetime(2026, 1, 1, 1, tzinfo=UTC),
        open=Decimal("60000"),
        high=Decimal("60100"),
        low=Decimal("59900"),
        close=Decimal("60050"),
        volume=Decimal("10"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_exit_flat_signal_calls_flatten(tmp_path):
    """An EXIT_FLAT signal while holding a position must call coordinator.flatten()."""
    from src.runtime.manager import RuntimeManager
    from src.signalgen.models import SignalSide

    coord = MagicMock()
    coord.symbol = _SYMBOL
    # S55 ARCH-03: manager reads FSM via public current_state(symbol), not _repo.
    coord.current_state.return_value = ExecutionState.OCO_ARMED

    bar = _bar()
    bs = MagicMock(poll=lambda: bar, consecutive_failures=0, should_halt=lambda **kw: False)
    sig = MagicMock(side=SignalSide.FLAT, reason="EXIT_FLAT_MEANREV_REVERT")
    strat = MagicMock(on_bar=lambda b: sig)
    risk = MagicMock()

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs,
        strategy=strat,
        risk_manager=risk,
        settings=_settings(tmp_path),
        shared_deps=_shared_deps(),
    )
    rm._tick()

    # EXIT signal must NOT be dropped: flatten fires, risk/bracket untouched.
    coord.flatten.assert_called_once()
    risk.assess.assert_not_called()
    coord.start_bracket.assert_not_called()


def test_exit_flat_signal_noop_when_flat(tmp_path):
    """EXIT_FLAT signal while already FLAT must NOT call flatten (nothing to exit)."""
    from src.runtime.manager import RuntimeManager
    from src.signalgen.models import SignalSide

    coord = MagicMock()
    coord.symbol = _SYMBOL
    coord.current_state.return_value = ExecutionState.FLAT

    bar = _bar()
    bs = MagicMock(poll=lambda: bar, consecutive_failures=0, should_halt=lambda **kw: False)
    sig = MagicMock(side=SignalSide.FLAT, reason="EXIT_FLAT_MEANREV_REVERT")
    strat = MagicMock(on_bar=lambda b: sig)

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs,
        strategy=strat,
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
        shared_deps=_shared_deps(),
    )
    rm._tick()

    coord.flatten.assert_not_called()


# --- TL-02: reconcile_arming_ttl wired into tick ----------------------------


def test_tick_runs_reconcile_arming_ttl(tmp_path):
    """A stuck OCO_ARMING bracket older than TTL must HALT via the tick cadence."""
    coord, repo, adapter = _make_coordinator(tmp_path)
    from src.risk.reason_codes import ReasonCode
    from src.runtime.manager import RuntimeManager

    # Seed an OCO_ARMING row whose arming_started_at is well past the TTL.
    bracket_id = coord.start_bracket(
        entry_qty=Decimal("0.002"),
        entry_side="Buy",
        tp_price=Decimal("70000.00"),
        sl_trigger_price=Decimal("60000.00"),
    )
    # Drive to LONG_OPEN, then begin arming but force the SL leg to fail so the
    # FSM stays in OCO_ARMING with a stale arming_started_at.
    coord._transition_to_long_open_for_test = None  # marker only

    # Manually transition to LONG_OPEN then partially arm: simplest is to mark
    # OCO_ARMING with an old timestamp directly via _upsert_fields after fill.
    coord.on_order_event(
        {
            "orderLinkId": f"oco-{bracket_id}-entry-1",
            "orderStatus": "Filled",
            "cumExecQty": "0.002",
            "cumExecFee": "0.000002",
            "feeCurrency": "BTC",
        }
    )
    # Force state back to OCO_ARMING with a stale timestamp (simulate partial arm).
    from dataclasses import replace

    cur = repo.get(_SYMBOL)
    stale = (datetime.now(tz=UTC) - timedelta(seconds=120)).isoformat()
    repo.upsert(replace(cur, state=ExecutionState.OCO_ARMING, arming_started_at=stale))

    strat = MagicMock()
    strat.on_bar.return_value = None  # no signal — isolate the TTL path
    bs = MagicMock(poll=lambda: None, consecutive_failures=0, should_halt=lambda **kw: False)

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs,
        strategy=strat,
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
        shared_deps=_shared_deps(),
    )
    rm._tick()

    row = repo.get(_SYMBOL)
    assert (
        row.state == ExecutionState.HALTED
    ), f"stuck OCO_ARMING past TTL must HALT, got {row.state}"
    assert row.halt_reason == ReasonCode.HALT_OCO_ARM_TIMEOUT.value
