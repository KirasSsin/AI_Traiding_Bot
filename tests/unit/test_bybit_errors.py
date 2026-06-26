"""Tests for BybitErrorMapper."""

from src.execution.bybit.errors import ReasonCode, map_error


def test_clock_drift() -> None:
    assert map_error(10002, "request not valid") is ReasonCode.CLOCK_DRIFT


def test_api_key_invalid() -> None:
    assert map_error(10003, "invalid api key") is ReasonCode.WRONG_API_KEY


def test_rate_limit() -> None:
    assert map_error(10006, "too many visits") is ReasonCode.RATE_LIMIT_HIT


def test_maintenance() -> None:
    assert map_error(10016, "service not available") is ReasonCode.EXCHANGE_MAINTENANCE


def test_insufficient_balance() -> None:
    assert map_error(110007, "insufficient balance") is ReasonCode.INSUFFICIENT_BALANCE


def test_filter_violations_all_map_to_same_code() -> None:
    for code in (110017, 170131, 170140, 170213):
        assert map_error(code, "") is ReasonCode.FILTER_VIOLATION


def test_unknown_code_maps_to_unknown() -> None:
    assert map_error(99999999, "unseen") is ReasonCode.UNKNOWN_ERROR


def test_110001_maps_to_already_terminal() -> None:
    assert (
        map_error(110001, "order not exists or finished")
        is ReasonCode.REJECT_ORDER_ALREADY_TERMINAL
    )


def test_already_terminal_in_enum() -> None:
    assert "REJECT_ORDER_ALREADY_TERMINAL" in {r.value for r in ReasonCode}


def test_110072_maps_to_reject_duplicate_order() -> None:
    # S51 D1 — OrderLinkedID duplicate. Our prior deterministic flatten submit
    # already landed; must be mapped (not UNKNOWN_ERROR) so flatten paths can
    # recognize it as idempotency-complete (success) instead of a spurious HALT.
    assert map_error(110072, "OrderLinkedID is duplicate") is ReasonCode.REJECT_DUPLICATE_ORDER


def test_110072_not_unknown() -> None:
    assert map_error(110072, "OrderLinkedID is duplicate") is not ReasonCode.UNKNOWN_ERROR


def test_reject_duplicate_order_in_enum() -> None:
    assert "REJECT_DUPLICATE_ORDER" in {r.value for r in ReasonCode}


def test_170005_maps_to_rate_limit() -> None:
    # S55 BYBIT-03 — order frequency limit (orders/sec). Previously UNKNOWN_ERROR,
    # which has no flatten short-circuit. After rest-exhaustion re-wrap the
    # coordinator needs a .reason it recognizes (RATE_LIMIT_HIT) instead of UNKNOWN.
    assert map_error(170005, "order frequency limit") is ReasonCode.RATE_LIMIT_HIT


def test_170222_maps_to_rate_limit() -> None:
    # S55 BYBIT-03 — order count limit (orders/min).
    assert map_error(170222, "order count limit") is ReasonCode.RATE_LIMIT_HIT


def test_170005_170222_not_unknown() -> None:
    assert map_error(170005, "") is not ReasonCode.UNKNOWN_ERROR
    assert map_error(170222, "") is not ReasonCode.UNKNOWN_ERROR
