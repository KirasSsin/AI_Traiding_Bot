"""Tests for atr_breakout dashboard preset (S42 T4 — unified preset per ADR 0062)."""

from __future__ import annotations


def test_atr_breakout_preset_registered() -> None:
    """Unified 'atr_breakout' preset must exist in STRATEGY_PRESETS (S42 T4)."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "atr_breakout" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["atr_breakout"]
    assert preset["sprint"] == "S42"
    assert preset["type"] == "atr_breakout"


def test_atr_breakout_preset_has_supported_combos() -> None:
    """Unified preset must declare supported_combos list with 10 entries."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["atr_breakout"]
    sc = preset.get("supported_combos")
    assert isinstance(sc, list)
    assert len(sc) == 10
    assert ("BTCUSDT", "240") in sc


def test_atr_breakout_preset_has_no_per_combo_locked_dimensions() -> None:
    """Unified preset has no locked_symbol/locked_interval (server-side lookup instead)."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["atr_breakout"]
    assert "locked_symbol" not in preset
    assert "locked_interval" not in preset


def test_atr_breakout_preset_label_indicates_locked() -> None:
    """Label clarifies LOCKED + sprint."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["atr_breakout"]
    label = preset["label"]
    assert "S42" in label
    assert "LOCKED" in label or "locked" in label
