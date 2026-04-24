"""RuntimeManager — live-runtime process lifecycle (ADR 0022).

Owns: bootstrap → ws_consumer.start → main loop → graceful shutdown.
Single thread for tick loop; pybit thread for WS callbacks (lock-protected
via Coordinator/Reconciler RLock/Lock).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.platform.logging import get_logger
from src.risk.reason_codes import ReasonCode
from src.signalgen.models import SignalSide

if TYPE_CHECKING:
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.platform.config import Settings
    from src.risk.manager import RiskManager
    from src.runtime.bar_source import BarSource
    from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy as Strategy

logger = get_logger(__name__)


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
    ) -> None:
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._ws_consumer = ws_consumer
        self._bar_source = bar_source
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._settings = settings
        self._stopping: bool = False
        self._kill_switch_path: Path = Path(settings.runtime_kill_switch_path)

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
        """One tick: kill_switch → check_alive → poll → strategy → risk → bracket.

        Sequential by ADR 0022 sub-decisions 1, 2, 4, 5.
        """
        if self._maybe_kill_switch():
            return
        if not self._check_alive_inline():
            return
        self._poll_bar_and_strategy()

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
