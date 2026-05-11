"""S48 T5 — glossary_data.py structure + STRATEGY_TO_METRICS_MAP coverage."""

from __future__ import annotations

from src.dashboard.glossary_data import (
    GLOSSARY_ENTRIES,
    SECTIONS,
    STRATEGY_TO_METRICS_MAP,
    GlossaryEntry,
    get_glossary,
)


def test_all_entries_have_required_fields() -> None:
    """Each glossary entry has term + section + description_ru + applies_to."""
    for term, entry in GLOSSARY_ENTRIES.items():
        assert isinstance(term, str) and term, f"Empty term: {term!r}"
        assert "section" in entry and entry["section"]
        assert "description_ru" in entry and entry["description_ru"]
        assert "applies_to" in entry and isinstance(entry["applies_to"], list)


def test_minimum_entry_count() -> None:
    """Glossary covers at least core T1-T6 + DSR + MC + finals + warnings + symbols."""
    assert len(GLOSSARY_ENTRIES) >= 30, f"Got {len(GLOSSARY_ENTRIES)}, expected >=30"


def test_critical_terms_present() -> None:
    """Required terms must exist."""
    required = [
        "t1_sharpe_oos",
        "t5_n_trades",
        "dsr",
        "mc_p_value",
        "total_pnl_pct",
        "win_rate",
        "raw_full_period",
        "subperiod_robustness",
    ]
    for term in required:
        assert term in GLOSSARY_ENTRIES, f"Missing required term: {term}"


def test_strategy_map_covers_all_6_presets() -> None:
    """STRATEGY_TO_METRICS_MAP includes all 6 STRATEGY_PRESETS."""
    expected_presets = {
        "ema_crossover_s13",
        "mean_reversion_s15",
        "mean_reversion_s17_relaxed",
        "donchian_breakout_s35",
        "volume_breakout_iter10",
        "atr_breakout",
    }
    actual = set(STRATEGY_TO_METRICS_MAP.keys())
    assert expected_presets.issubset(actual), f"Missing presets: {expected_presets - actual}"


def test_strategy_map_references_existing_terms() -> None:
    """STRATEGY_TO_METRICS_MAP values reference real GLOSSARY_ENTRIES keys."""
    for preset, term_list in STRATEGY_TO_METRICS_MAP.items():
        for term in term_list:
            assert term in GLOSSARY_ENTRIES, f"Preset {preset} references non-existent term: {term}"


def test_sections_match_canonical_list() -> None:
    """SECTIONS list contains expected sections (main-page render order)."""
    required_sections = {
        "verdict_status",
        "gate_blocking_metrics",
        "informational_metrics",
        "trade_statistics",
        "warnings",
        "strategy_presets",
    }
    assert required_sections.issubset(
        set(SECTIONS)
    ), f"Missing sections: {required_sections - set(SECTIONS)}"


def test_get_glossary_returns_full_payload() -> None:
    """Public API returns full glossary + map + sections."""
    result = get_glossary()
    assert "entries" in result
    assert "strategy_to_metrics" in result
    assert "sections" in result
    entries = result["entries"]
    assert isinstance(entries, dict)
    assert len(entries) >= 30


def test_glossary_entry_typed_dict_importable() -> None:
    """GlossaryEntry TypedDict importable (mypy strictness check)."""
    assert GlossaryEntry is not None
