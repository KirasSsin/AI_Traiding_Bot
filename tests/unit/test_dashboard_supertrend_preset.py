"""Tests for supertrend dashboard preset (S50 T10)."""

from __future__ import annotations


def test_supertrend_preset_registered() -> None:
    """Preset 'supertrend' must exist in STRATEGY_PRESETS."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "supertrend" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["supertrend"]
    assert preset["sprint"] == "S50"
    assert preset["type"] == "supertrend"


def test_supertrend_preset_has_locked_dimensions() -> None:
    """Preset must declare locked_symbol=BTCUSDT and locked_interval=60 (1H)."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["supertrend"]
    assert preset.get("locked_symbol") == "BTCUSDT"
    assert preset.get("locked_interval") == "60"


def test_supertrend_preset_has_supported_combos() -> None:
    """Preset must declare supported_combos with BTCUSDT/60 entry."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["supertrend"]
    sc = preset.get("supported_combos")
    assert isinstance(sc, list)
    assert len(sc) >= 1
    assert ("BTCUSDT", "60") in sc


def test_supertrend_preset_has_description_and_wfa_fail_note() -> None:
    """Preset description must be non-empty and contain honest WFA_FAIL note."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["supertrend"]
    desc = preset.get("description", "")
    assert len(desc) > 50
    # Honest WFA_FAIL verdict in description
    assert "WFA_FAIL" in desc


def test_supertrend_preset_has_optgroup() -> None:
    """Preset must have optgroup set (dashboard dropdown grouping)."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["supertrend"]
    optgroup = preset.get("optgroup", "")
    assert len(optgroup) > 0


def test_supertrend_preset_label_nonempty() -> None:
    """Preset label must be a non-empty Russian string."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["supertrend"]
    label = preset.get("label", "")
    assert len(label) > 5


def test_api_strategies_includes_supertrend() -> None:
    """GET /api/strategies response dict must include 'supertrend' key."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    # /api/strategies iterates STRATEGY_PRESETS — verifying the dict is sufficient
    assert "supertrend" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["supertrend"]
    # Fields surfaced by /api/strategies endpoint
    assert "label" in preset
    assert "type" in preset
    assert "optgroup" in preset
    assert "description" in preset
