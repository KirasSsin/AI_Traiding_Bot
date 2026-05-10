"""S43 T1 — preset metadata fields (description + optgroup) tests."""

from __future__ import annotations

from src.dashboard.backtest_runner import STRATEGY_PRESETS

EXPECTED_OPTGROUPS = {
    "ema_crossover_s13": "Тренд-следование",
    "mean_reversion_s15": "Возврат к среднему",
    "mean_reversion_s17_relaxed": "Возврат к среднему",
    "donchian_breakout_s35": "Прорывы",
    "volume_breakout_iter10": "Прорывы",
    "atr_breakout": "Прорывы",
}

EXPECTED_LABELS = {
    "ema_crossover_s13": "Тренд EMA 12/26 + ADX фильтр",
    "mean_reversion_s15": "Возврат к среднему RSI/Bollinger (классика)",
    "mean_reversion_s17_relaxed": "Возврат к среднему RSI/Bollinger (мягкий)",
    "donchian_breakout_s35": "Канал Дончиана пробой",
    "volume_breakout_iter10": "Прорыв с подтверждением объёма",
    "atr_breakout": "ATR-адаптивный пробой (multi-combo)",
}


def test_all_presets_have_optgroup() -> None:
    for pid, preset in STRATEGY_PRESETS.items():
        assert "optgroup" in preset, f"{pid} missing optgroup"
        assert preset["optgroup"] == EXPECTED_OPTGROUPS[pid]


def test_all_presets_have_description() -> None:
    for pid, preset in STRATEGY_PRESETS.items():
        assert "description" in preset, f"{pid} missing description"
        assert isinstance(preset["description"], str)
        assert len(preset["description"]) > 100, f"{pid} description too short"


def test_descriptions_use_html_strong_tags() -> None:
    """Descriptions use <strong> for term emphasis (no markdown)."""
    for pid, preset in STRATEGY_PRESETS.items():
        assert "<strong>" in preset["description"], f"{pid} description missing <strong> tags"


def test_labels_renamed_к_semantic_russian() -> None:
    for pid, preset in STRATEGY_PRESETS.items():
        assert preset["label"] == EXPECTED_LABELS[pid]
        # Old technical sprint identifier removed from label
        assert "[S" not in preset["label"], f"{pid} label still has [S<N>] tag"
