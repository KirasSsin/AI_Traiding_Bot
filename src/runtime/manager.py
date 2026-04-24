"""RuntimeManager — live-runtime process lifecycle (ADR 0022).

Owns: bootstrap → ws_consumer.start → main loop → graceful shutdown.
Single thread for tick loop; pybit thread for WS callbacks (lock-protected
via Coordinator/Reconciler RLock/Lock).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.platform.config import Settings
    from src.risk.manager import RiskManager
    from src.runtime.bar_source import BarSource
    from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy as Strategy

logger = logging.getLogger(__name__)


class RuntimeManager:
    """Process lifecycle owner — see ADR 0022 sub-decision 7."""

    def __init__(
        self,
        *,
        coordinator: "Coordinator",
        reconciler: "Reconciler",
        ws_consumer: "BybitPrivateWSConsumer",
        bar_source: "BarSource",
        strategy: "Strategy",
        risk_manager: "RiskManager",
        settings: "Settings",
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
        """Blocking entry-point: bootstrap → ws.start → main loop → shutdown.

        ADR 0022 sub-decisions 6 + 7. Wraps _main_loop with HALT_RUNTIME_CRASH guard
        (added in Task 16).
        """
        # Sub-decision 5: clean stale .kill_switch from previous session
        if self._kill_switch_path.exists():
            self._kill_switch_path.unlink()

        # Sequencing invariant: bootstrap FIRST, then WS, then loop
        self._coordinator.bootstrap()
        self._ws_consumer.start()
        try:
            self._main_loop()
        finally:
            self._shutdown(reason="NORMAL_EXIT")

    def _main_loop(self) -> None:
        """Tick at fixed cadence until self._stopping (set by tick or shutdown).

        ADR 0022 sub-decision 7. Exception propagation handled by run() in T16.
        """
        import time as _time
        while not self._stopping:
            self._tick()
            _time.sleep(self._settings.runtime_bar_poll_cadence_seconds)

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
                extra={"sentinel_path": str(self._kill_switch_path)},
            )
            self._coordinator.request_halt("KILL_SWITCH_REQUESTED")
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
        from src.signalgen.models import SignalSide

        bar = self._bar_source.poll()
        if self._bar_source.should_halt(threshold=self._settings.runtime_bar_poll_stall_threshold):
            logger.error(
                "runtime.bar_poll_stall",
                extra={
                    "consecutive_failures": self._bar_source.consecutive_failures,
                    "threshold": self._settings.runtime_bar_poll_stall_threshold,
                },
            )
            self._coordinator.request_halt("HALT_BAR_POLL_STALL")
            self._stopping = True
            return
        if bar is None:
            return
        logger.info("runtime.bar_tick", extra={"bar_close_ts": bar.close_time.isoformat()})
        signal = self._strategy.on_bar(bar)
        if signal is None or signal.side == SignalSide.FLAT:
            return
        assessment = self._risk_manager.assess(signal, mark_price=bar.close)
        if not assessment.approved:
            logger.info(
                "runtime.signal_rejected",
                extra={"side": str(signal.side), "reason": getattr(assessment, "reason_code", None)},
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
        # Body added in Task 17
        pass
