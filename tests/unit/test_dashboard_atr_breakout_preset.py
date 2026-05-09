"""Tests for atr_breakout dashboard preset (S40 T4 per ADR 0060)."""

from __future__ import annotations


def test_atr_breakout_preset_registered() -> None:
    """Preset atr_breakout_iter_endless must exist in STRATEGY_PRESETS."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "atr_breakout_iter_endless" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["atr_breakout_iter_endless"]
    assert preset["sprint"] == "S40"
    assert preset["type"] == "atr_breakout"


def test_atr_breakout_preset_has_locked_dimensions() -> None:
    """Preset must declare locked_symbol=BTCUSDT and locked_interval=240."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["atr_breakout_iter_endless"]
    assert preset.get("locked_symbol") == "BTCUSDT"
    assert preset.get("locked_interval") == "240"


def test_atr_breakout_preset_locked_params_in_indicators() -> None:
    """Preset indicators reflect ADR 0060 LOCKED params."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["atr_breakout_iter_endless"]
    ind = preset["indicators"]
    ab = ind["atr_breakout"]
    assert ab["atr_period"] == 9
    assert abs(ab["atr_breakout_mult"] - 2.5) < 1e-9
    assert ab["atr_stop_period"] == 21
    assert abs(ab["atr_stop_mult"] - 1.5) < 1e-9


def test_atr_breakout_preset_label_indicates_locked() -> None:
    """Label clarifies LOCKED + sprint."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["atr_breakout_iter_endless"]
    label = preset["label"]
    assert "S40" in label
    assert "LOCKED" in label or "locked" in label
    assert "BTCUSDT" in label or "BTC" in label
