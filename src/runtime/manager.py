"""RuntimeManager — live-runtime process lifecycle (ADR 0022).

Owns: bootstrap → ws_consumer.start → main loop → graceful shutdown.
Single thread for tick loop; pybit thread for WS callbacks (lock-protected
via Coordinator/Reconciler RLock/Lock).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from src.marketdata.quality import BarPriceQualityDetector
from src.platform.logging import get_logger
from src.risk.halt_gate import HaltGate, HaltTrigger
from src.risk.reason_codes import ReasonCode
from src.signalgen.models import SignalSide

if TYPE_CHECKING:
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.platform.config import Settings
    from src.risk.equity_tracker import EquityTracker
    from src.risk.manager import RiskManager
    from src.risk.state_repo import StateRepository
    from src.risk.trade_history import TradeHistoryRepository
    from src.runtime.bar_source import BarSource
    from src.signalgen.mean_reversion_strategy import MeanReversionRsiBBStrategy
    from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy

    # Strategy union — both implement the same on_bar(Bar) -> Signal | None contract.
    # S15 ADR 0030 added MeanReversionRsiBBStrategy as drop-in replacement.
    Strategy = EmaCrossoverAdxRsiStrategy | MeanReversionRsiBBStrategy

logger = get_logger(__name__)


# S36 T4: HaltTrigger → ReasonCode dispatch per ADR 0055 SD-4.
# HaltTrigger uses "S35_*" string values (legacy enum naming);
# ReasonCode uses HALT_S36_* (canonical reason taxonomy 46-49).
_HALT_TRIGGER_TO_REASON: dict[HaltTrigger, ReasonCode] = {
    HaltTrigger.DD_INTRADAY: ReasonCode.HALT_S36_DD_INTRADAY,
    HaltTrigger.DD_MULTIDAY: ReasonCode.HALT_S36_DD_MULTIDAY,
    HaltTrigger.CONSECUTIVE_LOSSES: ReasonCode.HALT_S36_CONSECUTIVE_LOSSES,
    HaltTrigger.NO_TRADE_TIMEOUT: ReasonCode.HALT_S36_NO_TRADE_TIMEOUT,
}


class RuntimeManager:
    """Process lifecycle owner — see ADR 0022 sub-decision 7."""

    def __init__(
        self,
        *,
        coordinator: Coordinator,
        reconciler: Reconciler,
        ws_consumer: BybitPrivateWSConsumer,
        bar_source: BarSource,
        strategy: Strategy,
        risk_manager: RiskManager,
        settings: Settings,
        equity_tracker: EquityTracker,
        trade_repo: TradeHistoryRepository,
        state_repo: StateRepository,
    ) -> None:
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._ws_consumer = ws_consumer
        self._bar_source = bar_source
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._settings = settings
        self._equity_tracker = equity_tracker
        self._trade_repo = trade_repo
        self._state_repo = state_repo
        # S36 T4 architecture-reviewer MEDIUM: instance-side cache avoids per-tick
        # state_repo.get() round-trip after first call. activation_ts immutable post-write.
        self._activation_ts: datetime | None = None
        self._stopping: bool = False
        self._kill_switch_path: Path = Path(settings.runtime_kill_switch_path)
        self._quality_detector = BarPriceQualityDetector(
            threshold_pct=settings.runtime_quality_threshold_pct
        )

    def run(self) -> None:
        """Blocking entry-point with HALT_RUNTIME_CRASH guard.

        ADR 0022 sub-decisions 5, 6, 7. Sequence:
          1. clean stale .kill_switch sentinel
          2. coordinator.bootstrap (raises propagate — ws.start blocked on bootstrap failure)
          3. ws_consumer.start
          4. _main_loop wrapped with: KeyboardInterrupt → clean shutdown,
             other Exception → request_halt(HALT_RUNTIME_CRASH) → re-raise.
        """
        # Sub-decision 5: clean stale .kill_switch from previous session
        if self._kill_switch_path.exists():
            self._kill_switch_path.unlink()

        # Sequencing invariant: bootstrap FIRST, then WS, then loop
        self._coordinator.bootstrap()
        # S37 ADR 0057 SD-3: operator-visible startup banner когда s35_demo_active=True
        if self._settings.s35_demo_active:
            logger.info(
                "runtime.s35_demo_startup_banner",
                approved_symbols=list(self._settings.s35_demo_approved_symbols),
                halt_thresholds={
                    "dd_intraday": str(self._settings.s35_halt_dd_intraday),
                    "dd_multiday": str(self._settings.s35_halt_dd_multiday),
                    "consecutive_losses": self._settings.s35_halt_consecutive_losses,
                    "no_trade_months": self._settings.s35_halt_no_trade_months,
                },
                fail_closed=True,
            )
        self._ws_consumer.start()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("runtime.keyboard_interrupt")
            self._shutdown(reason="KEYBOARD_INTERRUPT")
        except Exception as e:  # noqa: BLE001 — top-level guard per ADR 0022 sub-decision 6
            logger.exception(
                "runtime.crash",
                exc_type=type(e).__name__,
                exc_msg=str(e),
            )
            self._coordinator.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
            self._shutdown(reason="HALT_RUNTIME_CRASH")
            raise
        else:
            self._shutdown(reason="NORMAL_EXIT")

    def _main_loop(self) -> None:
        """Tick at fixed cadence until self._stopping (set by tick or shutdown).

        ADR 0022 sub-decision 7. Exception propagation handled by run() in T16.
        """
        while not self._stopping:
            self._tick()
            time.sleep(self._settings.runtime_bar_poll_cadence_seconds)

    def _tick(self) -> None:
        """One tick: kill_switch → check_alive → halt_gate → poll → strategy → risk → bracket.

        Sequential by ADR 0022 sub-decisions 1, 2, 4, 5.
        S36 T4: HaltGate evaluation per-tick when settings.s35_demo_active=True.
        """
        if self._maybe_kill_switch():
            return
        if not self._check_alive_inline():
            return
        if self._settings.s35_demo_active and self._check_halt_gate():
            return
        self._poll_bar_and_strategy()

    def _check_halt_gate(self) -> bool:
        """S36 T4 — HaltGate evaluation per ADR 0055 SD-3 + SD-4.

        Returns True если halt fired (caller should skip rest of tick).
        Inactive когда settings.s35_demo_active=False (returns False without inspection).

        On first call (no `s35:activation_ts` в StateRepository):
          - persists `now()` as activation timestamp;
          - subsequent calls re-use persisted ts для multiday HWM window.

        Halt dispatch: HaltTrigger → ReasonCode via _HALT_TRIGGER_TO_REASON,
        coordinator.request_halt(reason) + self._stopping=True.
        """
        if not self._settings.s35_demo_active:
            return False

        # S37 ADR 0057 SD-2+SD-3: fail-closed symbol whitelist check.
        # Performed BEFORE activation_ts persistence to avoid side-effects on
        # misconfigured boot. T5 will replace _symbol private access с self._coordinator.symbol public property.
        symbol = getattr(self._coordinator, "_symbol", None)
        if symbol is None or symbol not in self._settings.s35_demo_approved_symbols:
            logger.error(
                "runtime.halt_gate_unknown_symbol",
                symbol=symbol,
                whitelist=list(self._settings.s35_demo_approved_symbols),
            )
            self._coordinator.request_halt(ReasonCode.HALT_UNKNOWN_SYMBOL)
            self._stopping = True
            return True

        # S36 T4 architecture-reviewer MEDIUM: instance-cache avoids per-tick DB round-trip.
        # Namespace key per domain-prefix convention (was "s35:activation_ts").
        if self._activation_ts is None:
            activation_record = self._state_repo.get("runtime:halt_gate:activation_ts")
            if activation_record is None:
                now = datetime.now(UTC)
                self._state_repo.set("runtime:halt_gate:activation_ts", {"value": now.isoformat()})
                self._activation_ts = now
            else:
                self._activation_ts = datetime.fromisoformat(activation_record["value"])
        activation_ts = self._activation_ts

        # Compute HaltGate inputs
        intraday_dd = self._equity_tracker.intraday_dd_pct()
        hwm = self._equity_tracker.hwm_since(since_ts=activation_ts)
        current = self._equity_tracker.current_total() or Decimal("0")
        if hwm is not None and hwm > Decimal("0") and current < hwm:
            multiday_dd = (hwm - current) / hwm
        else:
            multiday_dd = Decimal("0")
        consec = self._trade_repo.consecutive_losses(symbol=symbol)
        last_ts = self._trade_repo.last_trade_ts(symbol=symbol)
        if last_ts is not None:
            months_since = (datetime.now(UTC) - last_ts).days // 30
        else:
            # No trades yet — measure от activation_ts (NOT zero, чтобы fire 6mo timeout
            # если no trades closed — signal-frequency starvation pre-commit ROUND 3).
            months_since = (datetime.now(UTC) - activation_ts).days // 30

        gate = HaltGate(
            dd_intraday_threshold=self._settings.s35_halt_dd_intraday,
            dd_multiday_threshold=self._settings.s35_halt_dd_multiday,
            consecutive_losses_threshold=self._settings.s35_halt_consecutive_losses,
            no_trade_months_threshold=self._settings.s35_halt_no_trade_months,
        )
        trigger = gate.evaluate(
            intraday_dd=intraday_dd,
            multiday_dd=multiday_dd,
            consecutive_losses=consec,
            months_since_last_trade=months_since,
        )
        if trigger is None:
            return False

        reason = _HALT_TRIGGER_TO_REASON[trigger]
        logger.error(
            "runtime.halt_gate_fired",
            trigger=trigger.value,
            reason=reason.value,
            symbol=symbol,
            intraday_dd=str(intraday_dd),
            multiday_dd=str(multiday_dd),
            consecutive_losses=consec,
            months_since=months_since,
        )
        self._coordinator.request_halt(reason)
        self._stopping = True
        return True

    def _maybe_kill_switch(self) -> bool:
        """Sentinel-file check (ADR 0022 sub-decision 5). True => caller should exit tick."""
        if self._kill_switch_path.exists():
            logger.info(
                "runtime.kill_switch_detected",
                sentinel_path=str(self._kill_switch_path),
            )
            self._coordinator.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
            self._stopping = True
            return True
        return False

    def _check_alive_inline(self) -> bool:
        """ADR 0022 sub-decision 4 — WS health-check inline in main thread (no worker)."""
        return self._ws_consumer.check_alive(
            max_silence_seconds=self._settings.runtime_ws_check_alive_max_silence
        )

    def _poll_bar_and_strategy(self) -> None:
        """REST kline → strategy.on_bar → risk.assess → coordinator.start_bracket.

        Stall halt fires AFTER each poll attempt regardless of bar presence
        (ADR 0022 sub-decision 3). LONG-only — FLAT signals skip risk per
        RiskManager LONG-only contract (src/risk/manager.py:159).
        """
        from src.execution.state_machine import ExecutionState

        bar = self._bar_source.poll()
        if self._bar_source.should_halt(threshold=self._settings.runtime_bar_poll_stall_threshold):
            logger.error(
                "runtime.bar_poll_stall",
                consecutive_failures=self._bar_source.consecutive_failures,
                threshold=self._settings.runtime_bar_poll_stall_threshold,
            )
            self._coordinator.request_halt(ReasonCode.HALT_BAR_POLL_STALL)
            self._stopping = True
            return
        if bar is None:
            return
        # S9 Q1 — quality check BEFORE strategy consumes bar.
        # _stopping=True matches stall + kill-switch patterns (lines 116, 146):
        # halt is terminal, main loop must exit (else log storm at poll cadence).
        if self._quality_detector.check(current_close=bar.close):
            self._coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
            self._stopping = True
            return
        logger.info("runtime.bar_tick", bar_close_ts=bar.close_time.isoformat())
        signal = self._strategy.on_bar(bar)
        if signal is None or signal.side == SignalSide.FLAT:
            return
        # FSM pre-check — only call start_bracket from FLAT (one-open-order invariant).
        # Reading via _repo (matches T17 plan pattern; no public current_state() on Coordinator).
        symbol = getattr(self._coordinator, "_symbol", None)
        if symbol is None:
            logger.warning("runtime.coordinator_missing_symbol_attr")
            return
        row = self._coordinator._repo.get(symbol)
        if row is None or row.state != ExecutionState.FLAT:
            logger.debug(
                "runtime.signal_skipped_non_flat_state",
                side=str(signal.side),
                current_state=row.state.value if row else "MISSING",
            )
            return
        assessment = self._risk_manager.assess(signal, mark_price=bar.close)
        if not assessment.approved:
            logger.info(
                "runtime.signal_rejected",
                side=str(signal.side),
                reason_code=assessment.reason_code.value,
            )
            return
        # Defense-in-depth + mypy type-narrowing.
        # RiskAssessment._consistency validator guarantees these are non-None when
        # approved=True, but mypy can't see that — explicit guard preserves invariant
        # if the validator ever changes and silences `arg-type` errors at the call site.
        if assessment.qty is None or assessment.tp_price is None or assessment.sl_price is None:
            logger.error(
                "runtime.assessment_missing_prices",
                side=str(signal.side),
                qty=str(assessment.qty),
                tp_price=str(assessment.tp_price),
                sl_price=str(assessment.sl_price),
            )
            return
        # SignalSide is LONG only at this point — translate to Bybit "Buy" string
        entry_side = "Buy" if signal.side == SignalSide.LONG else "Sell"
        self._coordinator.start_bracket(
            entry_qty=assessment.qty,
            entry_side=entry_side,
            tp_price=assessment.tp_price,
            sl_trigger_price=assessment.sl_price,
        )

    def _shutdown(self, *, reason: str) -> None:
        """Graceful drain — idempotent ws.stop + structured log.

        ADR 0022 sub-decisions 13 (structlog runtime.shutdown event) + 17 (graceful drain).
        Best-effort: ws.stop exceptions are logged but never re-raised.
        Records in-flight order count snapshot for ops audit.
        """
        if getattr(self, "_shutdown_done", False):
            return
        self._shutdown_done = True
        self._stopping = True
        try:
            self._ws_consumer.stop()
        except Exception as e:  # noqa: BLE001 — best-effort drain
            logger.error("runtime.shutdown_ws_stop_failed", err=str(e))

        # In-flight order count snapshot — best-effort, never raise
        in_flight = 0
        try:
            from src.execution.state_machine import ExecutionState

            symbol = getattr(self._coordinator, "_symbol", None)
            if symbol is not None:
                row = self._coordinator._repo.get(symbol)
                if row is not None and row.state in {
                    ExecutionState.ENTRY_PENDING,
                    ExecutionState.EXIT_PENDING,
                    ExecutionState.OCO_ARMING,
                }:
                    in_flight = 1
        except Exception:  # noqa: BLE001 — snapshot is best-effort
            pass

        logger.info("runtime.shutdown", reason=reason, in_flight_orders=in_flight)

    def shutdown(self, *, reason: str) -> None:
        """Public alias — operator-callable graceful shutdown."""
        self._shutdown(reason=reason)
