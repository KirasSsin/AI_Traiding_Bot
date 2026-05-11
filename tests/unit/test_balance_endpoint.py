"""S48 T4 — /api/bybit/balance endpoint integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from src.dashboard.app import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_balance_endpoint_returns_json(client: TestClient) -> None:
    """GET /api/bybit/balance returns JSON с required fields."""
    fake_balance = {
        "source": "fallback",
        "total_equity_usdt": 10000.0,
        "fetched_at_iso": "2026-05-11T12:00:00+00:00",
        "error": "no_api_keys",
    }
    with patch("src.dashboard.app.get_account_balance", return_value=fake_balance):
        r = client.get("/api/bybit/balance")
    assert r.status_code == 200
    assert r.json() == fake_balance


def test_balance_endpoint_no_cache_header(client: TestClient) -> None:
    """Balance response must NOT cache (live data per S47 cache-control middleware)."""
    with patch(
        "src.dashboard.app.get_account_balance",
        return_value={
            "source": "fallback",
            "total_equity_usdt": 10000.0,
            "fetched_at_iso": "2026-05-11T12:00:00+00:00",
            "error": None,
        },
    ):
        r = client.get("/api/bybit/balance")
    assert "no-cache" in r.headers.get("Cache-Control", "").lower()


def test_balance_endpoint_success_path(client: TestClient) -> None:
    """Success path с real balance value."""
    success_payload = {
        "source": "bybit_v5",
        "total_equity_usdt": 12345.67,
        "fetched_at_iso": "2026-05-11T12:00:00+00:00",
        "error": None,
    }
    with patch("src.dashboard.app.get_account_balance", return_value=success_payload):
        r = client.get("/api/bybit/balance")
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "bybit_v5"
    assert data["total_equity_usdt"] == 12345.67
