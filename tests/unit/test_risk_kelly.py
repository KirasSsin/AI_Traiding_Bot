"""Tests for src/risk/kelly.py — 4-phase Kelly + Wilson 95% CI.

TDD: RED phase — all tests written before implementation.
"""
from decimal import Decimal, getcontext
from math import isfinite

import pytest
from src.risk.kelly import (
    KellyCaps,
    kelly_fraction,
    phase_adjusted_fraction,
    phase_from_trade_count,
    wilson_95_ci,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEFAULT_CAPS = KellyCaps(
    phase1=Decimal("0.01"),
    phase2=Decimal("0.02"),
    phase3=Decimal("0.03"),
    phase4=Decimal("0.05"),
)


# ---------------------------------------------------------------------------
# phase_from_trade_count
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n, expected",
    [
        (0, 1),
        (1, 1),
        (29, 1),
        (30, 2),
        (31, 2),
        (99, 2),
        (100, 3),
        (101, 3),
        (199, 3),
        (200, 4),
        (201, 4),
        (1000, 4),
    ],
)
def test_phase_from_trade_count_boundaries(n, expected):
    assert phase_from_trade_count(n) == expected


def test_phase_from_trade_count_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        phase_from_trade_count(-1)


def test_phase_from_trade_count_negative_large_raises():
    with pytest.raises(ValueError):
        phase_from_trade_count(-100)


# ---------------------------------------------------------------------------
# wilson_95_ci
# ---------------------------------------------------------------------------


def test_wilson_95_ci_known_value():
    """Golden test: wins=55, total=100, p_hat=0.55 → approx [0.453, 0.643].

    Source: kelly-phases.md table (Phase 2 row).
    """
    lower, upper = wilson_95_ci(wins=55, total=100)
    assert abs(lower - 0.453) < 0.005, f"lower={lower:.4f} expected ~0.453"
    assert abs(upper - 0.643) < 0.005, f"upper={upper:.4f} expected ~0.643"


def test_wilson_95_ci_lower_less_than_upper():
    for wins, total in [(0, 10), (5, 10), (10, 10), (55, 100), (1, 1)]:
        lower, upper = wilson_95_ci(wins, total)
        assert lower < upper, f"wins={wins}, total={total}: lower={lower} >= upper={upper}"


def test_wilson_95_ci_bounds_in_unit_interval():
    for wins, total in [(0, 1), (1, 1), (0, 100), (100, 100), (55, 100)]:
        lower, upper = wilson_95_ci(wins, total)
        assert 0.0 <= lower <= 1.0, f"lower={lower} out of [0,1]"
        assert 0.0 <= upper <= 1.0, f"upper={upper} out of [0,1]"


def test_wilson_95_ci_zero_total_raises():
    with pytest.raises(ValueError, match="positive"):
        wilson_95_ci(wins=0, total=0)


def test_wilson_95_ci_negative_total_raises():
    with pytest.raises(ValueError):
        wilson_95_ci(wins=0, total=-1)


def test_wilson_95_ci_wins_exceeds_total_raises():
    with pytest.raises(ValueError, match=r"\[0, total\]"):
        wilson_95_ci(wins=6, total=5)


def test_wilson_95_ci_negative_wins_raises():
    with pytest.raises(ValueError):
        wilson_95_ci(wins=-1, total=10)


def test_wilson_95_ci_returns_floats():
    lower, upper = wilson_95_ci(wins=5, total=10)
    assert isinstance(lower, float)
    assert isinstance(upper, float)
    assert isfinite(lower)
    assert isfinite(upper)


def test_wilson_95_ci_all_wins():
    """wins == total: upper should be close to 1, lower < 1."""
    lower, upper = wilson_95_ci(wins=100, total=100)
    assert lower < upper <= 1.0


def test_wilson_95_ci_no_wins():
    """wins == 0: lower should be 0, upper > 0."""
    lower, upper = wilson_95_ci(wins=0, total=100)
    assert lower >= 0.0
    assert upper > lower


# ---------------------------------------------------------------------------
# kelly_fraction
# ---------------------------------------------------------------------------


def test_kelly_fraction_positive_edge():
    """p=0.6, b=2.0 → (0.6*2 - 0.4)/2 = (1.2 - 0.4)/2 = 0.4"""
    result = kelly_fraction(p=0.6, b=2.0)
    assert abs(result - 0.4) < 1e-9


def test_kelly_fraction_breakeven():
    """p=0.5, b=1.0 → (0.5*1 - 0.5)/1 = 0 → max(0, 0) = 0"""
    result = kelly_fraction(p=0.5, b=1.0)
    assert result == 0.0


def test_kelly_fraction_small_positive():
    """p=0.4, b=2.0 → (0.4*2 - 0.6)/2 = (0.8-0.6)/2 = 0.1"""
    result = kelly_fraction(p=0.4, b=2.0)
    assert abs(result - 0.1) < 1e-9


def test_kelly_fraction_negative_edge_clamped():
    """p=0.3, b=1.0 → (0.3*1 - 0.7)/1 = -0.4 → max(0, -0.4) = 0"""
    result = kelly_fraction(p=0.3, b=1.0)
    assert result == 0.0


def test_kelly_fraction_zero_b_returns_zero():
    result = kelly_fraction(p=0.7, b=0.0)
    assert result == 0.0


def test_kelly_fraction_negative_b_returns_zero():
    result = kelly_fraction(p=0.7, b=-1.0)
    assert result == 0.0


def test_kelly_fraction_p_above_one_raises():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        kelly_fraction(p=1.1, b=2.0)


def test_kelly_fraction_p_below_zero_raises():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        kelly_fraction(p=-0.1, b=2.0)


def test_kelly_fraction_p_at_boundaries():
    """p=0 and p=1 must not raise."""
    assert kelly_fraction(p=0.0, b=2.0) == 0.0
    result = kelly_fraction(p=1.0, b=2.0)
    assert result > 0.0


def test_kelly_fraction_returns_float():
    result = kelly_fraction(p=0.6, b=2.0)
    assert isinstance(result, float)


# ---------------------------------------------------------------------------
# phase_adjusted_fraction
# ---------------------------------------------------------------------------


def test_phase_adjusted_fraction_phase1_returns_cap():
    """Phase 1: ignore p, b — return caps.phase1."""
    result = phase_adjusted_fraction(phase=1, p=0.9, b=100.0, caps=DEFAULT_CAPS)
    assert result == DEFAULT_CAPS.phase1


def test_phase_adjusted_fraction_phase2_returns_cap():
    """Phase 2: ignore p, b — return caps.phase2."""
    result = phase_adjusted_fraction(phase=2, p=0.9, b=100.0, caps=DEFAULT_CAPS)
    assert result == DEFAULT_CAPS.phase2


def test_phase_adjusted_fraction_phase3_quarter_kelly():
    """Phase 3: min(0.25 * f*, cap3). With p=0.6, b=2 f*=0.4 → 0.25*0.4=0.1 < 0.03? No → cap."""
    # f* = 0.4, 0.25*0.4 = 0.1 > cap3=0.03 → result = 0.03
    result = phase_adjusted_fraction(phase=3, p=0.6, b=2.0, caps=DEFAULT_CAPS)
    assert result == DEFAULT_CAPS.phase3


def test_phase_adjusted_fraction_phase3_below_cap():
    """Phase 3: f* small → 0.25*f* < cap3 → return 0.25*f*."""
    # p=0.35, b=1.5 → f* = (0.35*1.5 - 0.65)/1.5 = (0.525-0.65)/1.5 = -0.125/1.5 < 0 → 0
    # Use p=0.55, b=1.1 → f* = (0.55*1.1 - 0.45)/1.1 = (0.605-0.45)/1.1 = 0.155/1.1 ≈ 0.1409
    # 0.25 * 0.1409 ≈ 0.03523 > 0.03 → still capped
    # Use p=0.52, b=1.05 → f* = (0.52*1.05 - 0.48)/1.05 = (0.546-0.48)/1.05 = 0.066/1.05 ≈ 0.0629
    # 0.25 * 0.0629 ≈ 0.01571 < 0.03 → not capped
    p, b = 0.52, 1.05
    f_star = kelly_fraction(p, b)
    expected = (Decimal(str(f_star)) * Decimal("0.25")).quantize(Decimal("1e-10"))
    result = phase_adjusted_fraction(phase=3, p=p, b=b, caps=DEFAULT_CAPS)
    assert result == expected
    assert result < DEFAULT_CAPS.phase3


def test_phase_adjusted_fraction_phase4_half_kelly():
    """Phase 4: min(0.5 * f*, cap4). With p=0.6, b=2 f*=0.4 → 0.5*0.4=0.2 > cap4=0.05 → cap."""
    result = phase_adjusted_fraction(phase=4, p=0.6, b=2.0, caps=DEFAULT_CAPS)
    assert result == DEFAULT_CAPS.phase4


def test_phase_adjusted_fraction_phase4_below_cap():
    """Phase 4: 0.5*f* < cap4 → return 0.5*f*."""
    # p=0.52, b=1.05 → f* ≈ 0.0629, 0.5*0.0629 ≈ 0.0314 < 0.05 → not capped
    p, b = 0.52, 1.05
    f_star = kelly_fraction(p, b)
    expected = (Decimal(str(f_star)) * Decimal("0.5")).quantize(Decimal("1e-10"))
    result = phase_adjusted_fraction(phase=4, p=p, b=b, caps=DEFAULT_CAPS)
    assert result == expected
    assert result < DEFAULT_CAPS.phase4


def test_phase_adjusted_fraction_cap_binding_huge_p_b():
    """Huge p,b → result must equal cap for phases 3 and 4."""
    result3 = phase_adjusted_fraction(phase=3, p=0.99, b=100.0, caps=DEFAULT_CAPS)
    assert result3 == DEFAULT_CAPS.phase3

    result4 = phase_adjusted_fraction(phase=4, p=0.99, b=100.0, caps=DEFAULT_CAPS)
    assert result4 == DEFAULT_CAPS.phase4


def test_phase_adjusted_fraction_returns_decimal():
    """Return type must be Decimal for all phases."""
    for phase in (1, 2, 3, 4):
        result = phase_adjusted_fraction(phase=phase, p=0.6, b=2.0, caps=DEFAULT_CAPS)
        assert isinstance(result, Decimal), f"phase={phase} returned {type(result)}"


def test_phase_adjusted_fraction_invalid_phase_raises():
    with pytest.raises(ValueError, match="invalid phase"):
        phase_adjusted_fraction(phase=0, p=0.6, b=2.0, caps=DEFAULT_CAPS)

    with pytest.raises(ValueError, match="invalid phase"):
        phase_adjusted_fraction(phase=5, p=0.6, b=2.0, caps=DEFAULT_CAPS)


def test_phase_adjusted_fraction_phase3_zero_f_star():
    """If kelly_fraction returns 0 (no edge), phase 3 returns 0."""
    # p=0.3, b=1.0 → f*=0 → 0.25*0=0
    result = phase_adjusted_fraction(phase=3, p=0.3, b=1.0, caps=DEFAULT_CAPS)
    assert result == Decimal("0")


def test_phase_adjusted_fraction_phase4_zero_f_star():
    """If kelly_fraction returns 0 (no edge), phase 4 returns 0."""
    result = phase_adjusted_fraction(phase=4, p=0.3, b=1.0, caps=DEFAULT_CAPS)
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# Decimal hot path — ADR 0007 invariant (no float multiply before Decimal cast)
# ---------------------------------------------------------------------------


def test_phase3_decimal_no_float_contamination():
    """Phase 3: must use Decimal arithmetic. f=0.3 → buggy float gives
    0.07500000000000001; correct Decimal path gives exact 0.075.
    """
    high_caps = KellyCaps(
        phase1=Decimal("0.01"),
        phase2=Decimal("0.02"),
        phase3=Decimal("0.20"),  # cap above expected result
        phase4=Decimal("0.20"),
    )
    # p=0.65, b=1.0 → f* = 0.30 → Quarter-Kelly = 0.075 (exact)
    result = phase_adjusted_fraction(phase=3, p=0.65, b=1.0, caps=high_caps)
    assert result == Decimal("0.075"), f"float contamination detected: {result}"


def test_phase4_decimal_no_float_contamination():
    """Phase 4: same Decimal-arithmetic invariant. f=0.30 → Half-Kelly = 0.15."""
    high_caps = KellyCaps(
        phase1=Decimal("0.01"),
        phase2=Decimal("0.02"),
        phase3=Decimal("0.20"),
        phase4=Decimal("0.20"),
    )
    result = phase_adjusted_fraction(phase=4, p=0.65, b=1.0, caps=high_caps)
    assert result == Decimal("0.15"), f"float contamination detected: {result}"
