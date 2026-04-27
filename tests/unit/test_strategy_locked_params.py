"""S36 T2 B1 critical fix tests — LOCKED params wired к live path.

Per pre-s36-backlog.md trading-logic-reviewer B1 BLOCKER:
  MEAN_REVERSION_S17_RELAXED_PARAMS must wire к live MeanReversionRsiBBStrategy
  constructor when s35_demo_active=True. Pre-commit #7 (LOCKED params) preserved.

Without this fix δ TESTNET would silently run S15-noise params (MC p=0.998)
instead of S22-validated S17-relaxed (MC p=0.018).
"""

from decimal import Decimal

from src.signalgen.mean_reversion_strategy import (
    MEAN_REVERSION_S17_RELAXED_PARAMS,
    MeanReversionRsiBBStrategy,
)


def test_locked_params_constants_exact_values() -> None:
    """LOCKED constants per ADR 0030 + S33 T4 — anti-S15-noise guard."""
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_period"] == 14
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_oversold"] == Decimal("35")
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_overbought"] == Decimal("65")
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_period"] == 20
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_std_mult"] == 1.5
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["and_gate_required"] is True


def test_strategy_accepts_bb_std_mult_param() -> None:
    """Constructor must accept bb_std_mult name (matches LOCKED dict key)."""
    s = MeanReversionRsiBBStrategy(
        symbol="BTCUSDT",
        rsi_period=14,
        rsi_oversold=Decimal("35"),
        rsi_overbought=Decimal("65"),
        atr_period=14,
        bb_period=20,
        bb_std_mult=1.5,
        and_gate_required=True,
    )
    assert s is not None
    # Verify bb_std_mult stored, not bb_k
    assert s._bb_std_mult == 1.5


def test_strategy_from_locked_params_factory() -> None:
    """Factory method maps LOCKED dict к constructor — single point of truth."""
    s = MeanReversionRsiBBStrategy.from_locked_s17_params(symbol="BTCUSDT")
    assert s is not None
    # Verify all LOCKED params propagated correctly
    assert s._rsi_oversold == Decimal("35")
    assert s._rsi_overbought == Decimal("65")
    assert s._bb_std_mult == 1.5
    assert s._and_gate_required is True
