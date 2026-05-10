"""Tests для volume_breakout dashboard preset (S39 T4) с ENFORCE locked dimensions."""

from __future__ import annotations


def test_volume_breakout_preset_registered() -> None:
    """Preset volume_breakout_iter10 must exist в STRATEGY_PRESETS."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "volume_breakout_iter10" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    assert preset["sprint"] == "S39"
    assert preset["type"] == "volume_breakout"


def test_volume_breakout_preset_has_locked_dimensions() -> None:
    """Preset must declare locked_symbol=BTCUSDT and locked_interval=240."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    assert preset.get("locked_symbol") == "BTCUSDT"
    assert preset.get("locked_interval") == "240"


def test_volume_breakout_preset_locked_params_in_indicators() -> None:
    """Preset indicators reflect ADR 0059 LOCKED params."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    ind = preset["indicators"]
    vb = ind["volume_breakout"]
    assert vb["lookback_n"] == 9
    assert vb["exit_lookback_n"] == 8
    assert vb["vol_window"] == 10
    assert abs(vb["vol_mult"] - 1.4563) < 1e-9
    assert vb["atr_period"] == 9
    assert abs(vb["atr_stop_mult"] - 2.9663) < 1e-9


def test_volume_breakout_preset_label_indicates_locked() -> None:
    """S43 — label semantic Russian; LOCKED info verified via description field."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    label = preset["label"]
    # Semantic Russian label (S43 rename)
    assert "Прорыв" in label
    assert "объём" in label.lower() or "объем" in label.lower()
    # LOCKED info now in description (semantic contract preserved)
    description = preset["description"]
    assert "LOCKED" in description
    assert "BTCUSDT" in description or "BTC" in description
    assert "S39" in description
