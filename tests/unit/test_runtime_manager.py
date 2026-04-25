"""RuntimeManager — process lifecycle owner.

ADR 0022 sub-decisions 7, 13, 14, 15, 17.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _settings(tmp_path: Path):
    from decimal import Decimal

    s = MagicMock()
    s.runtime_kill_switch_path = str(tmp_path / ".kill_switch")
    s.runtime_bar_poll_cadence_seconds = 5.0
    s.runtime_bar_poll_stall_threshold = 24
    s.runtime_ws_check_alive_max_silence = 30.0
    s.runtime_warmup_bars = 50
    s.runtime_quality_threshold_pct = Decimal("0.005")  # NEW S9 Q1
    return s


def test_runtime_manager_ctor_stores_deps(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    rec = MagicMock()
    ws = MagicMock()
    bs = MagicMock()
    strat = MagicMock()
    risk = MagicMock()
    s = _settings(tmp_path)

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=rec,
        ws_consumer=ws,
        bar_source=bs,
        strategy=strat,
        risk_manager=risk,
        settings=s,
    )

    assert rm._coordinator is coord
    assert rm._reconciler is rec
    assert rm._ws_consumer is ws
    assert rm._bar_source is bs
    assert rm._strategy is strat
    assert rm._risk_manager is risk
    assert rm._settings is s
    assert rm._stopping is False
    assert rm._kill_switch_path == Path(s.runtime_kill_switch_path)


def test_run_bootstraps_then_starts_ws_then_loops(tmp_path, monkeypatch):
    from src.runtime.manager import RuntimeManager

    calls: list[str] = []
    coord = MagicMock()
    coord.bootstrap.side_effect = lambda: calls.append("bootstrap")
    ws = MagicMock()
    ws.start.side_effect = lambda: calls.append("ws.start")

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=ws,
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )

    # Patch _main_loop so run() exits immediately after bootstrap+ws.start
    monkeypatch.setattr(rm, "_main_loop", lambda: calls.append("main_loop"))
    monkeypatch.setattr(rm, "_shutdown", lambda *, reason: calls.append(f"shutdown:{reason}"))

    rm.run()

    assert calls.index("bootstrap") < calls.index("ws.start")
    assert calls.index("ws.start") < calls.index("main_loop")


def test_run_cleans_stale_kill_switch_before_bootstrap(tmp_path):
    from src.runtime.manager import RuntimeManager

    sentinel = tmp_path / ".kill_switch"
    sentinel.write_text("")
    assert sentinel.exists()

    coord = MagicMock()
    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._main_loop = lambda: None
    rm._shutdown = lambda *, reason: None

    rm.run()
    assert not sentinel.exists(), "stale .kill_switch must be removed before bootstrap"


def test_bootstrap_failure_blocks_ws_start(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    coord.bootstrap.side_effect = RuntimeError("boot failed")
    ws = MagicMock()

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=ws,
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._main_loop = lambda: None
    rm._shutdown = lambda *, reason: None

    with pytest.raises(RuntimeError, match="boot failed"):
        rm.run()
    ws.start.assert_not_called()


from datetime import UTC, datetime
from decimal import Decimal


def _bar():
    from src.marketdata.models import Bar, DataQuality
    return Bar(
        symbol="BTCUSDT", interval="1h",
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        close_time=datetime(2026, 1, 1, 1, tzinfo=UTC),
        open=Decimal("60000"), high=Decimal("60100"),
        low=Decimal("59900"), close=Decimal("60050"),
        volume=Decimal("10"), trade_count=0,
        is_closed=True, data_quality=DataQuality.OK,
    )


def test_tick_sequence_kill_then_alive_then_poll_then_strategy(tmp_path):
    """Per ADR 0022 sub-decisions 1+2+4+5: kill_switch → check_alive → poll → strategy → risk → bracket."""
    from src.execution.state_machine import ExecutionState
    from src.runtime.manager import RuntimeManager
    from src.signalgen.models import SignalSide

    calls: list[str] = []
    coord = MagicMock()
    coord.start_bracket.side_effect = lambda **kw: (calls.append("start_bracket"), "bracket-id-stub")[1]
    coord._symbol = "BTCUSDT"
    coord._repo = MagicMock()
    coord._repo.get.return_value = MagicMock(state=ExecutionState.FLAT)
    ws = MagicMock()
    ws.check_alive.side_effect = lambda **kw: (calls.append("check_alive"), True)[1]
    bar = _bar()
    bs = MagicMock()
    bs.poll.side_effect = lambda: (calls.append("poll"), bar)[1]
    bs.consecutive_failures = 0
    bs.should_halt.return_value = False
    strat = MagicMock()
    sig = MagicMock(side=SignalSide.LONG)
    strat.on_bar.side_effect = lambda b: (calls.append("on_bar"), sig)[1]
    risk = MagicMock()
    assessment = MagicMock(
        approved=True,
        qty=Decimal("0.001"),
        sl_price=Decimal("58000"),
        tp_price=Decimal("65000"),
    )
    risk.assess.side_effect = lambda signal, **kw: (calls.append("risk.assess"), assessment)[1]

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=ws, bar_source=bs, strategy=strat,
        risk_manager=risk, settings=_settings(tmp_path),
    )
    rm._tick()

    # Order: kill_switch (no call recorded — file absent), check_alive, poll, on_bar, risk.assess, start_bracket
    assert calls == ["check_alive", "poll", "on_bar", "risk.assess", "start_bracket"]
    # And start_bracket received the assessment-derived params (real Coordinator signature)
    coord.start_bracket.assert_called_once_with(
        entry_qty=Decimal("0.001"),
        entry_side="Buy",
        tp_price=Decimal("65000"),
        sl_trigger_price=Decimal("58000"),
    )


def test_tick_no_new_bar_skips_strategy(tmp_path):
    from src.runtime.manager import RuntimeManager

    bs = MagicMock()
    bs.poll.return_value = None
    bs.consecutive_failures = 0
    bs.should_halt.return_value = False
    strat = MagicMock()
    risk = MagicMock()

    rm = RuntimeManager(
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=strat,
        risk_manager=risk, settings=_settings(tmp_path),
    )
    rm._tick()
    strat.on_bar.assert_not_called()
    risk.assess.assert_not_called()


def test_tick_kill_switch_detected_sets_stopping(tmp_path):
    from src.runtime.manager import RuntimeManager

    sentinel = tmp_path / ".kill_switch"
    sentinel.write_text("")
    coord = MagicMock()

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=MagicMock(poll=lambda: None, consecutive_failures=0, should_halt=lambda **kw: False),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._tick()
    coord.request_halt.assert_called_with("KILL_SWITCH_REQUESTED")
    assert rm._stopping is True


def test_shutdown_stops_ws_consumer(tmp_path):
    """ADR 0022 sub-decision 17 — _shutdown stops ws_consumer + sets _stopping=True."""
    from src.runtime.manager import RuntimeManager

    ws = MagicMock()
    rm = RuntimeManager(
        coordinator=MagicMock(), reconciler=MagicMock(),
        ws_consumer=ws, bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._shutdown(reason="TEST")
    ws.stop.assert_called_once()
    assert rm._stopping is True


def test_shutdown_idempotent(tmp_path):
    """Second _shutdown call is a no-op (no double ws.stop)."""
    from src.runtime.manager import RuntimeManager

    ws = MagicMock()
    rm = RuntimeManager(
        coordinator=MagicMock(), reconciler=MagicMock(),
        ws_consumer=ws, bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._shutdown(reason="ONCE")
    rm._shutdown(reason="TWICE")
    ws.stop.assert_called_once()  # second call is no-op


def test_shutdown_ws_stop_failure_logged_not_raised(tmp_path):
    """ws.stop exception must be swallowed — shutdown is best-effort drain."""
    from src.runtime.manager import RuntimeManager

    ws = MagicMock()
    ws.stop.side_effect = RuntimeError("ws-stop-boom")

    rm = RuntimeManager(
        coordinator=MagicMock(), reconciler=MagicMock(),
        ws_consumer=ws, bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    # Should NOT raise — best-effort drain per ADR 0022 sub-decision 17
    rm._shutdown(reason="TEST")
    assert rm._stopping is True


def test_public_shutdown_delegates(tmp_path):
    """Public shutdown(reason=) is operator-callable alias for _shutdown."""
    from src.runtime.manager import RuntimeManager

    ws = MagicMock()
    rm = RuntimeManager(
        coordinator=MagicMock(), reconciler=MagicMock(),
        ws_consumer=ws, bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm.shutdown(reason="OPERATOR_REQUEST")
    ws.stop.assert_called_once()


def test_tick_stall_threshold_triggers_halt(tmp_path):
    from src.runtime.manager import RuntimeManager

    bs = MagicMock()
    bs.poll.return_value = None
    bs.consecutive_failures = 24
    bs.should_halt.return_value = True
    coord = MagicMock()

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._tick()
    coord.request_halt.assert_called_with("HALT_BAR_POLL_STALL")
    assert rm._stopping is True


def test_tick_risk_rejects_skips_bracket(tmp_path):
    """Risk-rejected signal must not place an order."""
    from src.execution.state_machine import ExecutionState
    from src.runtime.manager import RuntimeManager
    from src.signalgen.models import SignalSide

    coord = MagicMock()
    coord._symbol = "BTCUSDT"
    coord._repo = MagicMock()
    coord._repo.get.return_value = MagicMock(state=ExecutionState.FLAT)
    bar = _bar()
    bs = MagicMock(poll=lambda: bar, consecutive_failures=0, should_halt=lambda **kw: False)
    sig = MagicMock(side=SignalSide.LONG)
    strat = MagicMock(on_bar=lambda b: sig)
    risk = MagicMock()
    risk.assess.return_value = MagicMock(approved=False, qty=None, sl_price=None, tp_price=None)

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=strat,
        risk_manager=risk, settings=_settings(tmp_path),
    )
    rm._tick()
    coord.start_bracket.assert_not_called()


def test_tick_flat_signal_skips_bracket(tmp_path):
    """SignalSide.FLAT must NOT call risk.assess (LONG-only contract per RiskManager:159)."""
    from src.runtime.manager import RuntimeManager
    from src.signalgen.models import SignalSide

    coord = MagicMock()
    bar = _bar()
    bs = MagicMock(poll=lambda: bar, consecutive_failures=0, should_halt=lambda **kw: False)
    sig = MagicMock(side=SignalSide.FLAT)
    strat = MagicMock(on_bar=lambda b: sig)
    risk = MagicMock()

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=strat,
        risk_manager=risk, settings=_settings(tmp_path),
    )
    rm._tick()
    risk.assess.assert_not_called()
    coord.start_bracket.assert_not_called()


def test_tick_non_flat_state_skips_start_bracket(tmp_path):
    """When FSM != FLAT, _tick must NOT call start_bracket (one-open-order invariant)."""
    from src.execution.state_machine import ExecutionState
    from src.runtime.manager import RuntimeManager
    from src.signalgen.models import SignalSide

    coord = MagicMock()
    coord._symbol = "BTCUSDT"
    # Simulate FSM in ENTRY_PENDING — second LONG signal must NOT place new bracket.
    row = MagicMock(state=ExecutionState.ENTRY_PENDING)
    coord._repo = MagicMock()
    coord._repo.get.return_value = row

    bar = _bar()
    bs = MagicMock(poll=lambda: bar, consecutive_failures=0, should_halt=lambda **kw: False)
    sig = MagicMock(side=SignalSide.LONG)
    strat = MagicMock(on_bar=lambda b: sig)
    risk = MagicMock()

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=strat,
        risk_manager=risk, settings=_settings(tmp_path),
    )
    rm._tick()

    # FSM non-FLAT short-circuits BEFORE risk.assess and before start_bracket
    risk.assess.assert_not_called()
    coord.start_bracket.assert_not_called()


def test_main_loop_exception_persists_halt_then_reraises(tmp_path):
    """Unhandled exception in _main_loop → request_halt(HALT_RUNTIME_CRASH) → re-raise (ADR 0022 sub-decision 6)."""
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(start=lambda: None, stop=lambda: None),
        bar_source=MagicMock(), strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    coord.bootstrap.return_value = None
    rm._main_loop = MagicMock(side_effect=RuntimeError("boom"))
    shutdown_calls: list[str] = []
    rm._shutdown = lambda *, reason: shutdown_calls.append(reason)

    with pytest.raises(RuntimeError, match="boom"):
        rm.run()

    # Halt persisted BEFORE re-raise — exact ReasonCode enum member
    from src.risk.reason_codes import ReasonCode
    coord.request_halt.assert_called_with(ReasonCode.HALT_RUNTIME_CRASH)
    assert "HALT_RUNTIME_CRASH" in shutdown_calls


def test_keyboard_interrupt_clean_shutdown(tmp_path):
    """KeyboardInterrupt is NOT a crash — caught silently, _shutdown(KEYBOARD_INTERRUPT), no request_halt."""
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    shutdown_calls: list[str] = []

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(start=lambda: None, stop=lambda: None),
        bar_source=MagicMock(), strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    coord.bootstrap.return_value = None
    rm._main_loop = MagicMock(side_effect=KeyboardInterrupt())
    rm._shutdown = lambda *, reason: shutdown_calls.append(reason)

    rm.run()  # KeyboardInterrupt is caught, NOT re-raised
    assert "KEYBOARD_INTERRUPT" in shutdown_calls
    coord.request_halt.assert_not_called()  # KeyboardInterrupt is not a CRASH


def _bar_close(close_value: str, *, hour: int = 0) -> "Bar":  # type: ignore[name-defined]  # noqa: F821
    """Build Bar with a custom close + close_time hour offset для quality tests."""
    from src.marketdata.models import Bar, DataQuality

    base_open = datetime(2026, 4, 25, 12 + hour, tzinfo=UTC)
    base_close = datetime(2026, 4, 25, 13 + hour, tzinfo=UTC)
    close = Decimal(close_value)
    # OHLC invariants: high >= max(open, close), low <= min(open, close).
    # Use close as both open and close для simplicity (flat bar).
    return Bar(
        symbol="BTCUSDT", interval="1h",
        open_time=base_open, close_time=base_close,
        open=close, high=close + Decimal("100"),
        low=close - Decimal("100"), close=close,
        volume=Decimal("1.0"), trade_count=0,
        is_closed=True, data_quality=DataQuality.OK,
    )


def test_quality_detector_halts_on_consecutive_bar_deviation(tmp_path: Path) -> None:
    """S9 Q1: After two bar polls with >0.5% deviation, RuntimeManager
    calls coordinator.request_halt(HALT_DATA_QUALITY).
    """
    from src.execution.state_machine import ExecutionState
    from src.risk.reason_codes import ReasonCode
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    coord._symbol = "BTCUSDT"
    # State row stays FLAT — strategy / risk path not relevant for this test
    coord._repo.get.return_value = MagicMock(state=ExecutionState.FLAT)

    bar1 = _bar_close("100000", hour=0)
    bar2 = _bar_close("100600", hour=1)  # +0.6% from bar1.close
    bs = MagicMock()
    bs.poll.side_effect = [bar1, bar2]
    bs.consecutive_failures = 0
    bs.should_halt.return_value = False

    strat = MagicMock()
    strat.on_bar.return_value = None  # FLAT signal

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=bs,
        strategy=strat,
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._poll_bar_and_strategy()  # bar1 → establishes baseline
    rm._poll_bar_and_strategy()  # bar2 → triggers halt

    coord.request_halt.assert_called_with(reason=ReasonCode.HALT_DATA_QUALITY)
    # bar1 consumed by strategy, bar2 short-circuited by quality halt
    # (verifies `return` after request_halt actually skips strategy path)
    assert strat.on_bar.call_count == 1
    # Halt is terminal — main loop must exit
    assert rm._stopping is True


def test_quality_detector_within_threshold_continues_strategy(tmp_path: Path) -> None:
    """S9 Q1: 0.4% deviation <0.5% threshold → no halt, strategy invoked."""
    from src.execution.state_machine import ExecutionState
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    coord._symbol = "BTCUSDT"
    coord._repo.get.return_value = MagicMock(state=ExecutionState.FLAT)

    bar1 = _bar_close("100000", hour=0)
    bar2 = _bar_close("100400", hour=1)  # +0.4%
    bs = MagicMock()
    bs.poll.side_effect = [bar1, bar2]
    bs.consecutive_failures = 0
    bs.should_halt.return_value = False

    strat = MagicMock()
    strat.on_bar.return_value = None

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=bs,
        strategy=strat,
        risk_manager=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._poll_bar_and_strategy()
    rm._poll_bar_and_strategy()

    # No HALT_DATA_QUALITY call
    from src.risk.reason_codes import ReasonCode
    halt_calls = [c for c in coord.request_halt.call_args_list
                  if c.kwargs.get("reason") == ReasonCode.HALT_DATA_QUALITY]
    assert len(halt_calls) == 0
    # Strategy invoked twice (no skip)
    assert strat.on_bar.call_count == 2
