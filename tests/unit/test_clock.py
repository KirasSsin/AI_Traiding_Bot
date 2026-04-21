"""Tests for ClockDriftMonitor."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from src.marketdata.clock import ClockDriftError, ClockDriftMonitor


def _client_returning(server_time: datetime) -> MagicMock:
    c = MagicMock()
    c.get_server_time.return_value = server_time
    return c


def test_drift_within_threshold_returns_ms() -> None:
    now = datetime.now(tz=UTC)
    client = _client_returning(now + timedelta(milliseconds=200))
    monitor = ClockDriftMonitor(rest_client=client, threshold_ms=1000)

    drift = monitor.check_drift()

    assert -2000 < drift < 2000  # small drift incl. measurement noise
    assert abs(drift) < 1000


def test_drift_exceeds_threshold_raises() -> None:
    now = datetime.now(tz=UTC)
    client = _client_returning(now + timedelta(seconds=5))
    monitor = ClockDriftMonitor(rest_client=client, threshold_ms=1000)

    with pytest.raises(ClockDriftError) as exc:
        monitor.check_drift()
    assert exc.value.drift_ms >= 1000


def test_default_threshold_is_1000ms() -> None:
    client = _client_returning(datetime.now(tz=UTC))
    monitor = ClockDriftMonitor(rest_client=client)
    assert monitor.threshold_ms == 1000
