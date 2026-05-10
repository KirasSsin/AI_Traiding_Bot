"""S42 T5 — supported_combos endpoint + combo enforcement tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_strategy_info_endpoint_returns_supported_combos(client: TestClient) -> None:
    r = client.get("/api/strategy/atr_breakout/info")
    assert r.status_code == 200
    data = r.json()
    assert "supported_combos" in data
    assert ["BTCUSDT", "240"] in data["supported_combos"]
    assert len(data["supported_combos"]) == 10


def test_strategy_info_unknown_strategy_returns_404(client: TestClient) -> None:
    r = client.get("/api/strategy/nonexistent/info")
    assert r.status_code == 404


def test_strategy_info_legacy_preset_returns_empty_supported_combos(client: TestClient) -> None:
    """Legacy presets (ema_crossover_s13) work с любого symbol/TF — no supported_combos field.
    Endpoint returns empty list."""
    r = client.get("/api/strategy/ema_crossover_s13/info")
    assert r.status_code == 200
    data = r.json()
    assert data.get("supported_combos") == []


def test_backtest_invalid_combo_for_atr_breakout_rejected_422(client: TestClient) -> None:
    """Pick BTCUSDT 5m — not в supported_combos. Server rejects 422."""
    r = client.post(
        "/api/backtest",
        json={
            "strategy_id": "atr_breakout",
            "symbol": "BTCUSDT",
            "interval": "5",
            "start": "2024-01-01",
            "end": "2024-06-01",
        },
    )
    assert r.status_code == 422
    detail_lower = r.json()["detail"].lower()
    assert (
        "supported_combos" in detail_lower
        or "no locked params" in detail_lower
        or "combo" in detail_lower
    )


def test_backtest_valid_combo_for_atr_breakout_not_422(client: TestClient) -> None:
    """BTCUSDT 240 IS в supported_combos — should not be rejected by combo gate."""
    r = client.post(
        "/api/backtest",
        json={
            "strategy_id": "atr_breakout",
            "symbol": "BTCUSDT",
            "interval": "240",
            "start": "2024-01-01",
            "end": "2024-06-01",
        },
    )
    # Either 200 OR 500 (data not found) — but NOT 422 (combo accepted by gate)
    assert r.status_code != 422


def test_strategy_info_response_includes_id_label_type(client: TestClient) -> None:
    """Endpoint mirrors basic preset metadata."""
    r = client.get("/api/strategy/atr_breakout/info")
    data = r.json()
    assert data["id"] == "atr_breakout"
    assert "ATR" in data["label"]  # S43 T1: label renamed to semantic Russian
    assert data["type"] == "atr_breakout"
