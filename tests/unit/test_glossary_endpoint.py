"""S48 T6 — /api/glossary endpoint integration."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from src.dashboard.app import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_glossary_endpoint_returns_full_payload(client: TestClient) -> None:
    """GET /api/glossary returns entries + strategy_to_metrics + sections."""
    r = client.get("/api/glossary")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert "strategy_to_metrics" in data
    assert "sections" in data
    assert len(data["entries"]) >= 30
    assert "ema_crossover_s13" in data["strategy_to_metrics"]


def test_glossary_endpoint_entries_have_required_fields(client: TestClient) -> None:
    """Each entry has section + description_ru + applies_to."""
    r = client.get("/api/glossary")
    entries = r.json()["entries"]
    for _term, entry in entries.items():
        assert "section" in entry
        assert "description_ru" in entry
        assert "applies_to" in entry
        assert isinstance(entry["applies_to"], list)


def test_glossary_endpoint_strategy_map_references_existing_terms(client: TestClient) -> None:
    """STRATEGY_TO_METRICS_MAP terms exist в entries."""
    r = client.get("/api/glossary")
    data = r.json()
    entries_keys = set(data["entries"].keys())
    for preset, term_list in data["strategy_to_metrics"].items():
        for term in term_list:
            assert term in entries_keys, f"Preset {preset} references missing term {term}"
