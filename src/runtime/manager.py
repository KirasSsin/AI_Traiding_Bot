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
        settings: "Settings",
    ) -> None:
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._ws_consumer = ws_consumer
        self._bar_source = bar_source
        self._strategy = strategy
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
        # Body added in Task 15
        raise NotImplementedError("_main_loop body added in Task 15")

    def _shutdown(self, *, reason: str) -> None:
        # Body added in Task 17
        pass
