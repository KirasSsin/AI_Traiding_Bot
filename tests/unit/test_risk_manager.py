"""Tests for RiskManager orchestrator — Sprint 4 Task 12. TDD RED."""

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.models import HaltState
from src.risk.override import CbOverride, OverrideStore
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeHistoryRepository, TradeRecord
from src.signalgen.models import Signal, SignalSide

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"
_UTC = UTC


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "test.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "cb_override.json",
        # ADR 0018 sub-decision 9 — required fields, no committed defaults.
        bybit_api_key="test_api_key_value",
        bybit_api_secret="test_api_secret_value",  # noqa: S106 — fixture
        risk_override_hmac_key="k" * 32,
    )


_T0 = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)


def _fixed_clock(dt: datetime):
    return lambda: dt


def _make_signal(*, generated_at: datetime = _T0, atr: Decimal = Decimal("100")) -> Signal:
    return Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.LONG,
        bar_close_time=generated_at - timedelta(seconds=1),
        generated_at=generated_at,
        ema_fast=Decimal("30100"),
        ema_slow=Decimal("30000"),
        adx_14=Decimal("28"),
        plus_di_14=Decimal("30"),
        minus_di_14=Decimal("20"),
        rsi_14=Decimal("45"),
        atr_14=atr,
        reason="ema_cross+adx",
    )


def _make_trade_record(*, pnl: Decimal, exit_ts: datetime = _T0) -> TradeRecord:
    now = exit_ts
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=now - timedelta(hours=1),
        exit_ts=now,
        qty=Decimal("0.001"),
        entry_price=Decimal("30000"),
        exit_price=Decimal("31000") if pnl > 0 else Decimal("29000"),
        pnl_quote=pnl,
        pnl_pct=pnl / Decimal("30"),
        fees_paid=Decimal("0.10"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=now,
    )


def _make_manager(db, settings, clock=None):
    from src.risk.manager import RiskManager
    return RiskManager(
        conn=db,
        settings=settings,
        clock=clock or _fixed_clock(_T0),
    )


def _seed_equity(db, *, realized: Decimal, ts: datetime = _T0):
    from src.risk.equity_tracker import EquityTracker
    EquityTracker(db).record(
        realized=realized,
        unrealized=Decimal("0"),
        ts=ts,
        source="BAR_CLOSE",
    )


# ---------------------------------------------------------------------------
# 1. Approval flow
# ---------------------------------------------------------------------------


def test_approve_returns_approved_assessment(db, settings):
    _seed_equity(db, realized=Decimal("10000"))
    mgr = _make_manager(db, settings)
    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))

    assert result.approved is True
    assert result.qty is not None and result.qty > 0
    assert result.sl_price < Decimal("30000") < result.tp_price
    assert result.kelly_phase == 1
    assert result.reason_code == ReasonCode.ENTRY_LONG_TREND_FOLLOWING
    assert result.halt_state == HaltState.L0


# ---------------------------------------------------------------------------
# 2. Look-ahead invariant
# ---------------------------------------------------------------------------


def test_look_ahead_violation_raises(db, settings):
    """assessed_at < signal.generated_at must raise ValueError."""
    _seed_equity(db, realized=Decimal("10000"))
    # clock returns _T0, signal generated_at is _T0 + 1s (in the future)
    future = _T0 + timedelta(seconds=1)
    mgr = _make_manager(db, settings, clock=_fixed_clock(_T0))
    signal = _make_signal(generated_at=future)
    with pytest.raises(ValueError, match="look-ahead"):
        mgr.assess(signal, mark_price=Decimal("30000"))


def test_same_timestamp_does_not_raise(db, settings):
    """assessed_at == signal.generated_at is valid (boundary)."""
    _seed_equity(db, realized=Decimal("10000"))
    mgr = _make_manager(db, settings, clock=_fixed_clock(_T0))
    signal = _make_signal(generated_at=_T0)
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.approved is True


# ---------------------------------------------------------------------------
# 3. Halt L1
# ---------------------------------------------------------------------------


def test_halt_l1_rejects_assessment(db, settings):
    """15.5% drawdown → L1 halt → assess rejected."""
    peak = Decimal("10000")
    current = peak * Decimal("0.845")  # 15.5% drop

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))

    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L1
    assert result.halt_state == HaltState.L1


# ---------------------------------------------------------------------------
# 4. Halt L2
# ---------------------------------------------------------------------------


def test_halt_l2_rejects_assessment(db, settings):
    """22.5% drawdown → L2 halt."""
    peak = Decimal("10000")
    current = peak * Decimal("0.775")  # 22.5% drop

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))

    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2
    assert result.halt_state == HaltState.L2


# ---------------------------------------------------------------------------
# 5. Halt L3
# ---------------------------------------------------------------------------


def test_halt_l3_rejects_assessment(db, settings):
    """30.5% drawdown → L3 halt."""
    peak = Decimal("10000")
    current = peak * Decimal("0.695")  # 30.5% drop

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))

    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L3
    assert result.halt_state == HaltState.L3


# ---------------------------------------------------------------------------
# 6. Override resume L2
# ---------------------------------------------------------------------------


def test_override_resumes_l2(db, settings):
    """Valid override with matching config_hash resumes trading at L2."""
    peak = Decimal("10000")
    current = peak * Decimal("0.775")  # L2

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    # Write a valid override
    override_path = settings.risk_override_path
    override_path.parent.mkdir(parents=True, exist_ok=True)
    store = OverrideStore(override_path, hmac_key=settings.risk_override_hmac_key)
    store.write(
        override=CbOverride(
            level="L2",
            reason="manual resume after review",
            config_hash=settings.config_hash(),
            created_at=_T0 - timedelta(minutes=5),
            expires_at=_T0 + timedelta(hours=2),
        )
    )

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.approved is True


def test_override_is_consumed_after_bypass(db, settings):
    """Audit H3 (CWE-672) — override is single-use; bypass consumes the file.

    Without consume, a 1-hour override would authorise every trade in that
    window. After the fix, a second assess() call sees no active override
    and rejects with HALT_DRAWDOWN_L2.
    """
    peak = Decimal("10000")
    current = peak * Decimal("0.775")  # L2

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    override_path = settings.risk_override_path
    override_path.parent.mkdir(parents=True, exist_ok=True)
    store = OverrideStore(override_path, hmac_key=settings.risk_override_hmac_key)
    store.write(
        override=CbOverride(
            level="L2",
            reason="manual resume — single use",
            config_hash=settings.config_hash(),
            created_at=_T0 - timedelta(minutes=5),
            expires_at=_T0 + timedelta(hours=2),
        )
    )

    signal = _make_signal()
    first = mgr.assess(signal, mark_price=Decimal("30000"))
    assert first.approved is True
    # Override file must be gone (renamed to *.consumed.<ts>.json).
    assert not override_path.exists()
    consumed = list(override_path.parent.glob("cb_override.consumed.*.json"))
    assert len(consumed) == 1

    # Second assess — no active override → halt re-applies.
    # generated_at must be <= clock (_T0) per look-ahead invariant.
    second = mgr.assess(_make_signal(generated_at=_T0 - timedelta(seconds=1)), mark_price=Decimal("30000"))
    assert second.approved is False
    assert second.reason_code == ReasonCode.HALT_DRAWDOWN_L2


# ---------------------------------------------------------------------------
# 7. Override invalid hash → ignored
# ---------------------------------------------------------------------------


def test_override_invalid_hash_ignored(db, settings):
    """Override with stale config_hash is ignored — halt remains active."""
    peak = Decimal("10000")
    current = peak * Decimal("0.775")  # L2

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    override_path = settings.risk_override_path
    override_path.parent.mkdir(parents=True, exist_ok=True)
    store = OverrideStore(override_path, hmac_key=settings.risk_override_hmac_key)
    store.write(
        override=CbOverride(
            level="L2",
            reason="bad hash override",
            config_hash="a" * 64,  # wrong hash
            created_at=_T0 - timedelta(minutes=5),
            expires_at=_T0 + timedelta(hours=2),
        )
    )

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2


# ---------------------------------------------------------------------------
# 8. Override expired → ignored
# ---------------------------------------------------------------------------


def test_override_expired_ignored(db, settings):
    """Expired override is ignored — halt remains active."""
    peak = Decimal("10000")
    current = peak * Decimal("0.775")  # L2

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    override_path = settings.risk_override_path
    override_path.parent.mkdir(parents=True, exist_ok=True)
    store = OverrideStore(override_path, hmac_key=settings.risk_override_hmac_key)
    store.write(
        override=CbOverride(
            level="L2",
            reason="expired override",
            config_hash=settings.config_hash(),
            created_at=_T0 - timedelta(hours=3),
            expires_at=_T0 - timedelta(hours=1),  # expired
        )
    )

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2


# ---------------------------------------------------------------------------
# 9. Phase transition
# ---------------------------------------------------------------------------


def test_phase_transition_at_30_trades(db, settings):
    """30 closed trades → phase=2 in assessment."""
    _seed_equity(db, realized=Decimal("10000"))
    repo = TradeHistoryRepository(db)
    for _ in range(30):
        repo.insert_closed_trade(_make_trade_record(pnl=Decimal("1.0")))

    mgr = _make_manager(db, settings)
    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.kelly_phase == 2


# ---------------------------------------------------------------------------
# 10. Wilson lower bound for phase 3
# ---------------------------------------------------------------------------


def test_wilson_lower_bound_phase3(db, settings):
    """100 trades, 55 wins → phase=3. Wilson lower bound p ≈ 0.453, NOT raw 0.55.

    With p_lower ≈ 0.453 and b ≈ 1.0:
      f* = (0.453 * 1 - 0.547) / 1 ≈ -0.094 → clamped to 0 → Quarter-Kelly(0) = 0
    Meaning qty=0 → REJECT_MIN_NOTIONAL (conservative path).

    If we used raw p=0.55: f*=(0.55-0.45)/1=0.1 → Quarter-Kelly(0.025) > 0 → would approve.
    This verifies Wilson lower bound IS being used.
    """
    _seed_equity(db, realized=Decimal("100000"))
    repo = TradeHistoryRepository(db)

    # Insert 100 trades: 55 wins, 45 losses — within 90-day window
    ts_base = _T0 - timedelta(days=10)
    for i in range(55):
        repo.insert_closed_trade(_make_trade_record(
            pnl=Decimal("1.0"), exit_ts=ts_base + timedelta(minutes=i)
        ))
    for i in range(45):
        repo.insert_closed_trade(_make_trade_record(
            pnl=Decimal("-1.0"), exit_ts=ts_base + timedelta(minutes=55 + i)
        ))

    mgr = _make_manager(db, settings)
    signal = _make_signal()
    # With Wilson lower bound, p_lower ≈ 0.453 → f* negative → qty=0
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.kelly_phase == 3
    # Wilson lower bound causes negative f* → REJECT_MIN_NOTIONAL
    assert result.reason_code == ReasonCode.REJECT_MIN_NOTIONAL


# ---------------------------------------------------------------------------
# 11. Atomic state flush
# ---------------------------------------------------------------------------


def test_update_equity_persists_cb_state(db, settings):
    """update_equity writes risk:cb:current_level to state table atomically."""
    from src.risk.state_repo import StateRepository

    peak = Decimal("10000")
    current = peak * Decimal("0.845")  # L1

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    mgr.update_equity(realized=current, unrealized=Decimal("0"), ts=_T0)

    state = StateRepository(db)
    record = state.get("risk:cb:current_level")
    assert record is not None
    assert record["level"] == "L1"


# ---------------------------------------------------------------------------
# 12. Zero-qty rejection → REJECT_MIN_NOTIONAL
# ---------------------------------------------------------------------------


def test_zero_qty_returns_reject_min_notional(db, settings):
    """Huge ATR causes qty=0 → REJECT_MIN_NOTIONAL (not REJECT_RISK_EXCEEDED)."""
    _seed_equity(db, realized=Decimal("100"))  # tiny equity
    mgr = _make_manager(db, settings)
    # ATR so large that (fraction * equity) / (k * atr) rounds to 0
    signal = _make_signal(atr=Decimal("999999999"))
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.approved is False
    assert result.reason_code == ReasonCode.REJECT_MIN_NOTIONAL


# ---------------------------------------------------------------------------
# 13. Determinism — clock injected, no datetime.now leaks
# ---------------------------------------------------------------------------


def test_assessed_at_uses_injected_clock(db, settings):
    """assessed_at in RiskAssessment must match injected clock exactly."""
    _seed_equity(db, realized=Decimal("10000"))
    fixed_now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=_UTC)
    mgr = _make_manager(db, settings, clock=_fixed_clock(fixed_now))
    signal = _make_signal(generated_at=fixed_now)  # same ts, no look-ahead
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.assessed_at == fixed_now


# ---------------------------------------------------------------------------
# 14. load_state restores halt level
# ---------------------------------------------------------------------------


def test_load_state_restores_halt_level(db, settings):
    """load_state reads risk:cb:current_level from DB and sets _current_halt."""
    from src.risk.state_repo import StateRepository

    state = StateRepository(db)
    state.set("risk:cb:current_level", {"level": "L2"})

    mgr = _make_manager(db, settings)
    mgr.load_state()

    _seed_equity(db, realized=Decimal("10000"))
    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    assert result.halt_state == HaltState.L2
    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2


# ---------------------------------------------------------------------------
# 15. record_closed_trade delegates to repository
# ---------------------------------------------------------------------------


def test_record_closed_trade_returns_trade_id(db, settings):
    mgr = _make_manager(db, settings)
    record = _make_trade_record(pnl=Decimal("5.0"))
    trade_id = mgr.record_closed_trade(record)
    assert isinstance(trade_id, int)
    assert trade_id >= 1


# ---------------------------------------------------------------------------
# 16. Halt severity: higher level wins, no downgrade
# ---------------------------------------------------------------------------


def test_halt_no_downgrade(db, settings):
    """After L2 is set, a subsequent update showing L1-level DD doesn't downgrade."""
    peak = Decimal("10000")

    _seed_equity(db, realized=peak, ts=_T0 - timedelta(hours=2))
    mgr = _make_manager(db, settings)

    # First update: L2
    l2_current = peak * Decimal("0.775")
    mgr.update_equity(realized=l2_current, unrealized=Decimal("0"), ts=_T0 - timedelta(hours=1))

    # Second update: only L1-level (recovered somewhat)
    l1_current = peak * Decimal("0.845")
    mgr.update_equity(realized=l1_current, unrealized=Decimal("0"), ts=_T0)

    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    # Should still be L2 (no downgrade)
    assert result.halt_state == HaltState.L2
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2


# ---------------------------------------------------------------------------
# 17. LONG-only gate — v0.1 FSM does not support FLAT signals at assess()
# ---------------------------------------------------------------------------


def test_assess_rejects_non_long_signal(db, settings):
    """v0.1 FSM is LONG+FLAT only; assess() expects LONG entries.

    FLAT signals are exit semantics handled outside Risk; reaching assess()
    with a non-LONG side is a contract violation that must raise.
    """
    _seed_equity(db, realized=Decimal("10000"))
    mgr = _make_manager(db, settings)
    flat_signal = Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.FLAT,
        bar_close_time=_T0 - timedelta(seconds=1),
        generated_at=_T0,
        ema_fast=Decimal("30100"),
        ema_slow=Decimal("30000"),
        adx_14=Decimal("28"),
        plus_di_14=Decimal("30"),
        minus_di_14=Decimal("20"),
        rsi_14=Decimal("45"),
        atr_14=Decimal("100"),
        reason="exit_flip",
    )
    with pytest.raises(ValueError, match="LONG-only"):
        mgr.assess(flat_signal, mark_price=Decimal("30000"))


# ---------------------------------------------------------------------------
# 18. Atomic state flush — equity snapshot rolls back on state failure
# ---------------------------------------------------------------------------


def test_update_equity_atomic_rollback_on_state_failure(db, settings, monkeypatch):
    """If state write fails mid-flush, equity snapshot must NOT persist.

    Invariant (risk-manager.md #5): equity snapshot + CB state in ONE transaction.
    """
    _seed_equity(db, realized=Decimal("10000"), ts=_T0 - timedelta(hours=1))
    mgr = _make_manager(db, settings)
    initial = db.execute("SELECT COUNT(*) FROM equity_snapshots").fetchone()[0]

    def boom(*args, **kwargs):
        raise RuntimeError("simulated state-write failure")

    monkeypatch.setattr(mgr._state, "update_many_no_commit", boom)

    with pytest.raises(RuntimeError, match="simulated"):
        mgr.update_equity(realized=Decimal("9000"), unrealized=Decimal("0"), ts=_T0)

    final = db.execute("SELECT COUNT(*) FROM equity_snapshots").fetchone()[0]
    assert final == initial, "equity snapshot leaked despite state failure"


# ---------------------------------------------------------------------------
# 19. qty quantize uses ROUND_DOWN (Bybit BUY step-floor compliance)
# ---------------------------------------------------------------------------


def test_qty_quantize_rounds_down(db, settings, monkeypatch):
    """8dp quantize must use ROUND_DOWN (Bybit BUY step-floor per ADR 0007)."""
    from src.risk import manager as mgr_mod

    _seed_equity(db, realized=Decimal("10000"))
    # Force compute_qty to return value with non-zero 9th decimal
    monkeypatch.setattr(mgr_mod, "compute_qty", lambda **kw: Decimal("0.123456789"))
    mgr = _make_manager(db, settings)
    signal = _make_signal()
    result = mgr.assess(signal, mark_price=Decimal("30000"))
    # ROUND_DOWN: 0.123456789 → 0.12345678 (truncated)
    # ROUND_HALF_EVEN: 0.123456789 → 0.12345679 (banker rounding up, 9>5)
    assert result.qty == Decimal("0.12345678"), f"got {result.qty}"


# ---------------------------------------------------------------------------
# 20. _prev_close persistence across restart
# ---------------------------------------------------------------------------


def test_on_bar_close_persists_prev_close(db, settings):
    """on_bar_close persists prev_close to state for flash-CB continuity."""
    from src.risk.state_repo import StateRepository

    mgr = _make_manager(db, settings)

    class _Bar:
        close = Decimal("30000")

    mgr.on_bar_close(_Bar())
    record = StateRepository(db).get("risk:cb:prev_close")
    assert record == {"value": "30000"}


def test_load_state_restores_prev_close(db, settings):
    """After restart, _prev_close must be restored — no one-bar flash CB gap."""
    from src.risk.state_repo import StateRepository

    StateRepository(db).set("risk:cb:prev_close", {"value": "29500"})
    mgr = _make_manager(db, settings)
    mgr.load_state()
    assert mgr._prev_close == Decimal("29500")
