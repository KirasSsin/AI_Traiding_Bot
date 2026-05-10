"""Smoke tests для dashboard FastAPI app (S25 ADR 0039)."""

from __future__ import annotations

import pytest

# Skip if dashboard deps not installed (optional dep group)
fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from src.dashboard.app import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_index_renders(client: TestClient) -> None:
    """React build SPA responds 200 + contains React mount point.

    S46: vanilla Jinja2 template archived to src/dashboard_legacy/.
    FastAPI now serves React build via FileResponse(dist/index.html).
    """
    r = client.get("/")
    # React build may not exist в test env (CI builds in separate step) —
    # accept 200 (build present) OR 503 (build missing fallback per app.py).
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert "AI Trading Bot" in r.text
        # React mount point (vanilla "backtest-form" id retired в T20)
        assert 'id="root"' in r.text


def test_strategies_endpoint(client: TestClient) -> None:
    r = client.get("/api/strategies")
    assert r.status_code == 200
    data = r.json()
    assert "ema_crossover_s13" in data
    assert "mean_reversion_s15" in data
    assert "mean_reversion_s17_relaxed" in data
    for sid, preset in data.items():
        assert preset["id"] == sid
        assert "label" in preset
        assert "type" in preset


def test_intervals_endpoint(client: TestClient) -> None:
    r = client.get("/api/intervals")
    assert r.status_code == 200
    data = r.json()
    ids = [iv["id"] for iv in data]
    # 30M + 2H skipped per backtest_runner (Bar.interval Literal limit)
    assert "5" in ids
    assert "15" in ids
    assert "60" in ids
    assert "240" in ids
    assert "D" in ids


def test_data_availability_endpoint(client: TestClient) -> None:
    r = client.get("/api/data/availability")
    assert r.status_code == 200
    # No assertion on content (varies на developer machine)


def test_runs_list_endpoint(client: TestClient) -> None:
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_backtest_invalid_strategy_returns_400(client: TestClient) -> None:
    r = client.post(
        "/api/backtest",
        json={
            "strategy_id": "nonexistent",
            "symbol": "BTCUSDT",
            "interval": "60",
            "start": "2023-01-01",
            "end": "2023-12-31",
        },
    )
    # 400 for backtest_runner ValueError, 422 для pydantic schema fail — both valid client errors
    assert r.status_code in (400, 422)


def test_backtest_invalid_interval_returns_400(client: TestClient) -> None:
    r = client.post(
        "/api/backtest",
        json={
            "strategy_id": "mean_reversion_s17_relaxed",
            "symbol": "BTCUSDT",
            "interval": "999",
            "start": "2023-01-01",
            "end": "2023-12-31",
        },
    )
    # 400 for backtest_runner ValueError, 422 для pydantic schema fail — both valid client errors
    assert r.status_code in (400, 422)


def test_run_not_found_returns_404(client: TestClient) -> None:
    r = client.get("/api/runs/nonexistent_run_id")
    assert r.status_code == 404
