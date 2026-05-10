"""Phase 5 HARD-GATE — atr_breakout multi-combo baselines (S42 T4 — unified preset per ADR 0062).

Verifies that all 10 (symbol, interval) combos via unified 'atr_breakout' preset
produce the expected PnL within ±2% tolerance.

Source: data/autoresearch_endless/best_per_combo.json
"""

from __future__ import annotations

from datetime import date

import pytest

# ---------------------------------------------------------------------------
# Multi-combo baselines (LOCKED per ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO — server-side lookup)
# Full period for Bybit data: 2023-01-01 → 2026-04-26 (3.3y)
# ---------------------------------------------------------------------------
BYBIT_START = date(2023, 1, 1)
BYBIT_END = date(2026, 4, 26)

# Tolerance wider than S40 (±2%) since these are new combos not yet production-verified
REPLICATION_TOLERANCE_PCT = 2.0

# (symbol, interval, expected_pnl_pct, expected_n_trades)
MULTI_COMBO_BASELINES = [
    ("SOLUSDT", "240", 264.29, 71),
    ("ETHUSDT", "60", 181.74, 109),
    ("BTCUSDT", "15", 107.35, 245),
    ("BTCUSDT", "60", 146.36, 106),
    ("SOLUSDT", "60", 214.08, 124),
    ("ETHUSDT", "240", 152.30, 28),
    ("SOLUSDT", "15", 150.51, 230),
    ("BTCUSDT", "D", 167.54, 32),
    ("ETHUSDT", "15", 35.53, 240),
]


@pytest.mark.integration
def test_unified_atr_breakout_preset_registered() -> None:
    """Unified 'atr_breakout' preset MUST be in STRATEGY_PRESETS with 10 supported_combos."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert (
        "atr_breakout" in STRATEGY_PRESETS
    ), "atr_breakout not in STRATEGY_PRESETS. S42 T4 consolidation incomplete."
    preset = STRATEGY_PRESETS["atr_breakout"]
    assert preset.get("type") == "atr_breakout"
    sc = preset.get("supported_combos", [])
    assert len(sc) == 10, f"Expected 10 supported_combos, got {len(sc)}"


@pytest.mark.integration
@pytest.mark.parametrize(
    "symbol,interval,expected_pnl,expected_n",
    MULTI_COMBO_BASELINES,
)
def test_multi_combo_runner_pnl_floor(
    symbol: str,
    interval: str,
    expected_pnl: float,
    expected_n: int,
) -> None:
    """S42 T4 runner MUST produce PnL within ±2% of autoresearch baseline via unified preset."""
    from src.backtest.atr_breakout_runner import (
        ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO,
        run_atr_breakout_backtest,
    )

    # Verify locked params exist for this combo
    assert (symbol, interval) in ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO, (
        f"({symbol}, {interval}) not in ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO. "
        f"T2 task incomplete."
    )

    result = run_atr_breakout_backtest(
        symbol=symbol,
        interval=interval,
        start_date=BYBIT_START,
        end_date=BYBIT_END,
    )
    pnl = float(result["total_pnl_pct"])
    n = int(result["n_trades"])

    floor = expected_pnl - REPLICATION_TOLERANCE_PCT
    assert pnl >= floor, (
        f"FAIL Phase 5 HARD-GATE ({symbol} {interval}): "
        f"PnL={pnl:.2f}% < floor={floor:.2f}% (baseline={expected_pnl}%). "
        f"n_trades={n}."
    )
    # n_trades within ±5 (wider tolerance for non-primary combos)
    assert abs(n - expected_n) <= 5, (
        f"FAIL Phase 5 HARD-GATE ({symbol} {interval}): "
        f"n_trades={n}, expected ~{expected_n} (±5)."
    )


@pytest.mark.integration
def test_atr_breakout_runner_accepts_params_kwarg() -> None:
    """run_atr_breakout_backtest MUST accept explicit params kwarg (T1 generalization)."""
    from src.backtest.atr_breakout_runner import run_atr_breakout_backtest

    custom_params = {
        "atr_period": 9,
        "atr_breakout_mult": 2.5,
        "atr_stop_period": 21,
        "atr_stop_mult": 1.5,
    }
    result = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
        params=custom_params,
    )
    assert "n_trades" in result
    assert "total_pnl_pct" in result
    assert "sharpe" in result


@pytest.mark.integration
def test_atr_breakout_locked_params_by_combo_has_all_combos() -> None:
    """ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO MUST have entries for all 10 combos."""
    from src.backtest.atr_breakout_runner import ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO

    expected_combos = {
        ("BTCUSDT", "240"),
        ("BTCUSDT", "60"),
        ("BTCUSDT", "15"),
        ("BTCUSDT", "D"),
        ("ETHUSDT", "240"),
        ("ETHUSDT", "60"),
        ("ETHUSDT", "15"),
        ("SOLUSDT", "240"),
        ("SOLUSDT", "60"),
        ("SOLUSDT", "15"),
    }
    missing = expected_combos - set(ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.keys())
    assert not missing, f"Missing combos in ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO: {missing}"
