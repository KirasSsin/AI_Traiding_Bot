"""4-phase Kelly position sizing with Wilson 95% CI.

ADR 0012 — source of truth.
"""
from dataclasses import dataclass
from decimal import Decimal
from math import sqrt


@dataclass(frozen=True)
class KellyCaps:
    """Per-phase position-fraction caps. Passed from Settings."""

    phase1: Decimal  # n < 30
    phase2: Decimal  # 30 <= n < 100
    phase3: Decimal  # 100 <= n < 200
    phase4: Decimal  # n >= 200


def phase_from_trade_count(n: int) -> int:
    """ADR 0012: 1 if n<30, 2 if n<100, 3 if n<200, 4 if n>=200.

    Args:
        n: Non-negative number of completed trades.

    Returns:
        Phase integer in {1, 2, 3, 4}.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n < 30:
        return 1
    if n < 100:
        return 2
    if n < 200:
        return 3
    return 4


def wilson_95_ci(wins: int, total: int) -> tuple[float, float]:
    """Wilson 95% CI for binomial proportion (Agresti-Coull form).

    Formula per kelly-phases.md:
        p_hat = wins / total
        z = 1.96
        center = p_hat + z*z/(2*total)
        spread = z * sqrt(p_hat*(1-p_hat)/total + z*z/(4*total*total))
        denom = 1 + z*z/total
        lower = (center - spread) / denom
        upper = (center + spread) / denom

    Returns:
        (lower, upper) as floats — statistical, per ADR 0007 (Decimal only for monetary).

    Raises:
        ValueError: If total <= 0 or wins not in [0, total].
    """
    if total <= 0:
        raise ValueError("total must be positive")
    if wins < 0 or wins > total:
        raise ValueError("wins must be in [0, total]")
    z = 1.96
    p_hat = wins / total
    center = p_hat + z * z / (2 * total)
    spread = z * sqrt(p_hat * (1 - p_hat) / total + z * z / (4 * total * total))
    denom = 1 + z * z / total
    return ((center - spread) / denom, (center + spread) / denom)


def kelly_fraction(p: float, b: float) -> float:
    """f* = (p*b - q) / b where q = 1 - p, b = avg_win / avg_loss.

    Args:
        p: Win probability, must be in [0, 1].
        b: Payoff ratio (avg_win / avg_loss). Returns 0 when b <= 0.

    Returns:
        Float >= 0. Returns 0 when formula yields non-positive or b <= 0.

    Raises:
        ValueError: If p not in [0, 1].
    """
    if not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1]")
    if b <= 0:
        return 0.0
    q = 1.0 - p
    f_star = (p * b - q) / b
    return max(0.0, f_star)


def phase_adjusted_fraction(
    phase: int,
    p: float,
    b: float,
    caps: KellyCaps,
) -> Decimal:
    """Apply phase rule to raw f*.

    - Phase 1 (n<30):   fixed caps.phase1 (no formula)
    - Phase 2 (n<100):  fixed caps.phase2 (no formula)
    - Phase 3 (n<200):  min(0.25 * f*, caps.phase3)  -- Quarter-Kelly
    - Phase 4 (n>=200): min(0.5 * f*, caps.phase4)   -- Half-Kelly

    Returns:
        Decimal monetary fraction used by sizing.compute_qty.

    Raises:
        ValueError: If phase not in {1, 2, 3, 4}.
    """
    if phase == 1:
        return caps.phase1
    if phase == 2:
        return caps.phase2
    f = kelly_fraction(p, b)
    if phase == 3:
        return min(Decimal(str(f * 0.25)), caps.phase3)
    if phase == 4:
        return min(Decimal(str(f * 0.5)), caps.phase4)
    raise ValueError(f"invalid phase: {phase}")
