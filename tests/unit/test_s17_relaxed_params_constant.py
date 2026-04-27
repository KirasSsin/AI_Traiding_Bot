"""S17-relaxed params named constant — S33 T4 (Item #5 anti-S15-recurrence guard).

Per consilium ROUND 2 trader Q1 binding condition #1:
"S17-relaxed params (RSI 35/65, BB 1.5σ) NOT S15 (RSI 30/70, BB 2σ — MC p=0.998 noise)"

Per consilium ROUND 2 Item #5: explicit named constant prevents copy-paste regression
of S15 params. Reference: sprint-17-btc-mean-reversion-relaxed.md PASS partial verdict.

S33 ADR 0050 pre-registration: MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED перед F measurement.
"""

from __future__ import annotations

from decimal import Decimal

from src.signalgen.mean_reversion_strategy import MEAN_REVERSION_S17_RELAXED_PARAMS


def test_s17_relaxed_params_exact_values_locked():
    """LOCKED values per S17 PASS partial verdict — anti-S15-recurrence."""
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_period"] == 14
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_oversold"] == Decimal("35")
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_overbought"] == Decimal("65")
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_period"] == 20
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_std_mult"] == 1.5
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["and_gate_required"] is True


def test_s17_relaxed_params_NOT_s15_noise():
    """Sanity check: S17-relaxed NOT equal к S15 noise params (RSI 30/70, BB 2σ)."""
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_oversold"] != Decimal("30")  # S15 noise
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_overbought"] != Decimal("70")  # S15 noise
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_std_mult"] != 2.0  # S15 noise
