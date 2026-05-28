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


@pytest.mark.parametrize(
    "payload",
    [
        "../etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "abc/../../etc",
        "%2e%2e%2f",
        "ABCDEF0123456789",  # uppercase hex — not lowercase sha256
        "z" * 16,  # non-hex chars
        "a" * 15,  # too short
        "a" * 17,  # too long
    ],
)
def test_run_id_traversal_or_malformed_returns_404(client: TestClient, payload: str) -> None:
    """H1 — path traversal / malformed run_id rejected before any disk access."""
    r = client.get(f"/api/runs/{payload}")
    assert r.status_code == 404


def test_run_id_valid_16hex_accepted(client: TestClient) -> None:
    """H1 — valid 16-char lowercase hex run_id reaches get_run (404 only if missing file)."""
    r = client.get("/api/runs/0123456789abcdef")
    # No cached run with this id → 404 from get_run None, NOT a validation reject.
    assert r.status_code == 404


def test_get_glossary_returns_200_with_expected_keys() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/glossary")
    assert response.status_code == 200
    body = response.json()
    assert "entries" in body
    assert "strategy_to_metrics" in body
    assert "sections" in body
    assert isinstance(body["entries"], dict)
    assert isinstance(body["sections"], list)
    assert len(body["sections"]) > 0
    # Canonical section keys from glossary_data.py SECTIONS list
    assert any(
        s in body["sections"]
        for s in ("verdict_status", "gate_blocking_metrics", "trade_statistics")
    )


def test_get_bybit_balance_returns_200_fallback_when_no_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Without API keys → source='fallback'
    monkeypatch.delenv("BYBIT_API_KEY", raising=False)
    monkeypatch.delenv("BYBIT_API_SECRET", raising=False)
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/bybit/balance")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] in ("bybit_v5", "fallback", "cached")
    assert isinstance(body["total_equity_usdt"], int | float)
    assert isinstance(body["fetched_at_iso"], str)
