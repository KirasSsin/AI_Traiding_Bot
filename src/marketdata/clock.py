"""Clock drift monitor — detects local/server time skew (edge-case #9)."""

from datetime import UTC, datetime
from typing import Protocol


class _ServerTimeClient(Protocol):
    def get_server_time(self) -> datetime: ...


class ClockDriftError(RuntimeError):
    """Drift between local clock and exchange server exceeds threshold."""

    def __init__(self, drift_ms: int, threshold_ms: int) -> None:
        super().__init__(f"Clock drift {drift_ms}ms > threshold {threshold_ms}ms")
        self.drift_ms = drift_ms
        self.threshold_ms = threshold_ms


class ClockDriftMonitor:
    """Computes `server - local` drift in ms; raises if > threshold."""

    def __init__(self, rest_client: _ServerTimeClient, threshold_ms: int = 1000) -> None:
        self._client = rest_client
        self.threshold_ms = threshold_ms

    def check_drift(self) -> int:
        local = datetime.now(tz=UTC)
        server = self._client.get_server_time()
        drift_ms = int((server - local).total_seconds() * 1000)
        if abs(drift_ms) > self.threshold_ms:
            raise ClockDriftError(drift_ms, self.threshold_ms)
        return drift_ms
