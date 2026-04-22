"""Integration test — 50-bar synthetic risk flow exercising the full risk module.

Sprint 4 Task 15. Covers:
- Phase 1 baseline with 5 closed trades
- Equity drawdown cascade: L0 → L1 → L2 via update_equity
- Manual override via OverrideStore (direct write, matching config_hash)
- Flash-crash halt via on_bar_close + assess with large price drop
- State persistence across RiskManager re-instantiation
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.kelly import phase_from_trade_count
from src.risk.manager import RiskManager
from src.risk.models import HaltState, RiskAssessment
from src.risk.override import CbOverride, OverrideStore
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord
from src.signalgen.models import Signal, SignalSide

_MIGRATIONS = Path(__file__).parents[2] / "migrations"
_UTC = timezone.utc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2026, 4, 23, 0, 0, 0, tzinfo=_UTC)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "test.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
    )


def _signal(*, ts: datetime, atr: Decimal = Decimal("500")) -> Signal:
    return Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.LONG,
        bar_close_time=ts - timedelta(seconds=1),
        generated_at=ts,
        ema_fast=Decimal("40100"),
        ema_slow=Decimal("40000"),
        adx_14=Decimal("28"),
        plus_di_14=Decimal("30"),
        minus_di_14=Decimal("20"),
        rsi_14=Decimal("45"),
        atr_14=atr,
        reason="ema_cross+adx",
    )


def _trade(*, ts: datetime, pnl: Decimal) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=ts - timedelta(hours=1),
        exit_ts=ts,
        qty=Decimal("0.001"),
        entry_price=Decimal("40000"),
        exit_price=Decimal("41000") if pnl >= 0 else Decimal("39000"),
        pnl_quote=pnl,
        pnl_pct=pnl / Decimal("40"),
        fees_paid=Decimal("0.10"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=ts,
    )


def _make_mgr(conn: sqlite3.Connection, settings: Settings, clock_state: dict) -> RiskManager:
    return RiskManager(
        conn=conn,
        settings=settings,
        clock=lambda: clock_state["now"],
    )


# ---------------------------------------------------------------------------
# Main integration test
# ---------------------------------------------------------------------------


def test_50_bar_synthetic_risk_flow(tmp_path: Path) -> None:
    # -----------------------------------------------------------------------
    # 1. Setup
    # -----------------------------------------------------------------------
    settings = _settings(tmp_path)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)

    clock_state: dict = {"now": _BASE_TS}
    mgr = _make_mgr(conn, settings, clock_state)
    mgr.load_state()

    # -----------------------------------------------------------------------
    # 2. Phase 1 baseline — seed equity at 10 000 USDT, insert 5 trades
    # -----------------------------------------------------------------------
    mgr.update_equity(
        realized=Decimal("10000"), unrealized=Decimal("0"), ts=_BASE_TS
    )

    pnl_values = [
        Decimal("120"),
        Decimal("-40"),
        Decimal("200"),
        Decimal("-80"),
        Decimal("150"),
    ]
    for i, pnl in enumerate(pnl_values):
        ts = _BASE_TS + timedelta(hours=i + 1)
        clock_state["now"] = ts
        record = _trade(ts=ts, pnl=pnl)
        mgr.record_closed_trade(record)

    # Phase must be 1 (n=5 < 30)
    from src.risk.trade_history import TradeHistoryRepository
    trade_count = TradeHistoryRepository(conn).count()
    assert trade_count == 5
    assert phase_from_trade_count(trade_count) == 1

    # -----------------------------------------------------------------------
    # 3. Approve — normal market, no halt active
    # -----------------------------------------------------------------------
    ts_assess = _BASE_TS + timedelta(hours=10)
    clock_state["now"] = ts_assess
    sig1 = _signal(ts=ts_assess)
    result: RiskAssessment = mgr.assess(sig1, mark_price=Decimal("40000"))

    assert result.approved is True
    assert result.kelly_phase == 1
    assert result.qty is not None and result.qty > 0
    assert result.halt_state == HaltState.L0

    # -----------------------------------------------------------------------
    # 4. Equity drops to trigger L1  (16 % drawdown, threshold is 15 %)
    # -----------------------------------------------------------------------
    ts_l1 = _BASE_TS + timedelta(hours=11)
    clock_state["now"] = ts_l1
    # 10000 * (1 - 0.16) = 8400
    mgr.update_equity(
        realized=Decimal("8400"), unrealized=Decimal("0"), ts=ts_l1
    )

    sig2 = _signal(ts=ts_l1)
    result_l1 = mgr.assess(sig2, mark_price=Decimal("40000"))

    assert result_l1.approved is False
    assert result_l1.reason_code == ReasonCode.HALT_DRAWDOWN_L1
    assert result_l1.halt_state == HaltState.L1

    # -----------------------------------------------------------------------
    # 5. Equity drops to trigger L2  (23 % drawdown, threshold is 22 %)
    # -----------------------------------------------------------------------
    ts_l2 = _BASE_TS + timedelta(hours=12)
    clock_state["now"] = ts_l2
    # 10000 * (1 - 0.23) = 7700
    mgr.update_equity(
        realized=Decimal("7700"), unrealized=Decimal("0"), ts=ts_l2
    )

    sig3 = _signal(ts=ts_l2)
    result_l2 = mgr.assess(sig3, mark_price=Decimal("40000"))

    assert result_l2.approved is False
    assert result_l2.reason_code == ReasonCode.HALT_DRAWDOWN_L2
    assert result_l2.halt_state == HaltState.L2

    # -----------------------------------------------------------------------
    # 6. Manual override for L2 — write file directly (matching config_hash)
    # -----------------------------------------------------------------------
    ts_override = _BASE_TS + timedelta(hours=13)
    clock_state["now"] = ts_override

    override_path = settings.risk_override_path
    override_path.parent.mkdir(parents=True, exist_ok=True)
    store = OverrideStore(override_path)
    store.write(
        override=CbOverride(
            level="L2",
            reason="test resume after review",
            config_hash=settings.config_hash(),
            created_at=ts_override - timedelta(minutes=1),
            expires_at=ts_override + timedelta(hours=2),
        )
    )

    sig4 = _signal(ts=ts_override)
    result_resumed = mgr.assess(sig4, mark_price=Decimal("40000"))

    assert result_resumed.approved is True, (
        f"Expected approved after L2 override, got reason_code={result_resumed.reason_code}"
    )

    # -----------------------------------------------------------------------
    # 7. Flash crash — set prev_close via on_bar_close, then assess with
    #    mark_price that is 12.5 % below prev_close (> 8 % flash_abs)
    # -----------------------------------------------------------------------
    from src.marketdata.models import Bar

    ts_bar = _BASE_TS + timedelta(hours=14)
    clock_state["now"] = ts_bar

    normal_bar = Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=ts_bar - timedelta(hours=1),
        close_time=ts_bar - timedelta(seconds=1),
        open=Decimal("40000"),
        high=Decimal("40500"),
        low=Decimal("39500"),
        close=Decimal("40000"),
        volume=Decimal("100"),
        trade_count=500,
        is_closed=True,
    )
    mgr.on_bar_close(normal_bar)

    # Override is still active for L2, but flash (severity=4) > L2 (severity=2).
    # Flash detection happens in assess() before halt-check, so if flash triggers
    # it escalates _current_halt to FLASH and rejects.
    ts_flash = _BASE_TS + timedelta(hours=14, minutes=1)
    clock_state["now"] = ts_flash
    sig_flash = _signal(ts=ts_flash, atr=Decimal("500"))
    # mark_price = 35000 → drop of 12.5 % from 40000, well above 8 % flash_abs
    result_flash = mgr.assess(sig_flash, mark_price=Decimal("35000"))

    assert result_flash.approved is False
    assert result_flash.reason_code == ReasonCode.HALT_FLASH_CRASH
    assert result_flash.halt_state == HaltState.FLASH

    # -----------------------------------------------------------------------
    # 8. State persistence — new RiskManager, same conn, load_state
    # -----------------------------------------------------------------------
    # First persist current halt to the state table via a dummy update_equity
    # (update_equity always writes risk:cb:current_level to state table)
    ts_persist = _BASE_TS + timedelta(hours=15)
    clock_state["now"] = ts_persist
    mgr.update_equity(
        realized=Decimal("7700"), unrealized=Decimal("0"), ts=ts_persist
    )

    mgr2 = _make_mgr(conn, settings, clock_state)
    mgr2.load_state()

    # After load_state the halt must be at least L2 (may be FLASH or L2)
    assert mgr2._current_halt in {HaltState.L2, HaltState.L3, HaltState.FLASH}, (
        f"Expected halted state after reload, got {mgr2._current_halt}"
    )
