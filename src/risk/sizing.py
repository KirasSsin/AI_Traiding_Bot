"""Position sizing pure functions — Sprint 4, Task 5."""

from decimal import Decimal


def compute_qty(
    equity: Decimal,
    fraction: Decimal,
    atr: Decimal,
    price: Decimal,  # noqa: ARG001 — kept for API symmetry with signal.mark_price
    k: Decimal = Decimal("1.5"),
) -> Decimal:
    """Position-size formula: qty = (fraction * equity) / (k * atr).

    All inputs Decimal. k = stop-distance multiplier (default 1.5 per Settings).
    Returns 0 when fraction or atr is zero (defensive — caller should pre-check).
    Raises ValueError on negative inputs.
    """
    if equity < Decimal("0"):
        raise ValueError(f"equity must be >= 0, got {equity}")
    if fraction < Decimal("0"):
        raise ValueError(f"fraction must be >= 0, got {fraction}")
    if atr < Decimal("0"):
        raise ValueError(f"atr must be >= 0, got {atr}")

    if fraction == Decimal("0") or atr == Decimal("0"):
        return Decimal("0")

    return (fraction * equity) / (k * atr)
