"""H1 — Rate-limit exponential backoff с jitter (S39 T7)."""

from __future__ import annotations

import pytest


def test_retry_with_backoff_succeeds_after_2_retries(monkeypatch) -> None:
    """When pybit returns 10006 twice then OK, helper retries и returns final result."""
    from src.marketdata.bybit.rest import _retry_with_backoff

    sleep_calls: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    call_count = {"n": 0}

    def fake_call() -> dict:
        call_count["n"] += 1
        if call_count["n"] < 3:
            return {"retCode": 10006, "retMsg": "too many visits", "result": {}}
        return {"retCode": 0, "retMsg": "OK", "result": {"list": []}}

    result = _retry_with_backoff(fake_call)

    assert call_count["n"] == 3
    assert result["retCode"] == 0
    assert len(sleep_calls) == 2  # 2 backoff sleeps before 3rd success
    # Exponential: first delay >= base, second delay >= 2*base
    assert sleep_calls[0] >= 0.5
    assert sleep_calls[1] >= 1.0


def test_retry_with_backoff_passes_through_non_rate_limit_response(monkeypatch) -> None:
    """Non-10006 response returned immediately, no retry."""
    from src.marketdata.bybit.rest import _retry_with_backoff

    sleep_calls: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def fake_call() -> dict:
        return {"retCode": 110001, "retMsg": "order not found", "result": {}}

    result = _retry_with_backoff(fake_call)
    assert result["retCode"] == 110001
    assert sleep_calls == []  # no retries


def test_retry_with_backoff_exhausts_max_retries(monkeypatch) -> None:
    """After max_retries=5 attempts, raises BybitAPIError."""
    from src.marketdata.bybit.rest import BybitAPIError, _retry_with_backoff

    sleep_calls: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def fake_call() -> dict:
        return {"retCode": 10006, "retMsg": "too many visits", "result": {}}

    with pytest.raises(BybitAPIError) as exc_info:
        _retry_with_backoff(fake_call)
    assert "Rate limit exhausted" in str(exc_info.value)
    assert exc_info.value.ret_code == 10006
    # 5 retries → 5 sleep calls
    assert len(sleep_calls) == 5


def test_retry_with_backoff_jitter_adds_randomness(monkeypatch) -> None:
    """Jitter prevents identical delays on consecutive retries."""
    from src.marketdata.bybit.rest import BybitAPIError, _retry_with_backoff

    sleep_calls: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def fake_call() -> dict:
        return {"retCode": 10006, "retMsg": "rate limited", "result": {}}

    with pytest.raises(BybitAPIError):
        _retry_with_backoff(fake_call)

    # Verify не все delays exact powers of 2 × base (jitter present)
    # base=0.5, exponential: [0.5, 1.0, 2.0, 4.0, 8.0]; с jitter — slightly above
    assert sleep_calls[0] > 0.5  # base + jitter
    assert sleep_calls[1] > 1.0
