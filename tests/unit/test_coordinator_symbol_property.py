"""S37 T5 — Coordinator.symbol public property per ADR 0057 SD-6.

Replaces `getattr(coord, "_symbol", None)` private leak в RuntimeManager.
"""

from unittest.mock import MagicMock

from src.execution.coordinator import Coordinator


def _make_coordinator(symbol: str = "BTCUSDT") -> Coordinator:
    return Coordinator(
        adapter=MagicMock(),
        repo=MagicMock(),
        reconciler=MagicMock(),
        symbol=symbol,
        base_coin="BTC",
    )


def test_coordinator_exposes_symbol_public_property() -> None:
    """ADR 0057 SD-6: coord.symbol returns initialized symbol value."""
    coord = _make_coordinator(symbol="BTCUSDT")
    assert coord.symbol == "BTCUSDT"


def test_coordinator_symbol_property_matches_init_arg() -> None:
    """Property mirrors __init__ symbol kwarg для arbitrary value."""
    coord = _make_coordinator(symbol="ETHUSDT")
    assert coord.symbol == "ETHUSDT"
