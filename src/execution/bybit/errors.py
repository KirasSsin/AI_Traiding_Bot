"""Map Bybit V5 retCode → domain ReasonCode (per ADR 0016)."""

from enum import StrEnum


class ReasonCode(StrEnum):
    CLOCK_DRIFT = "CLOCK_DRIFT"
    WRONG_API_KEY = "WRONG_API_KEY"
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
    EXCHANGE_MAINTENANCE = "EXCHANGE_MAINTENANCE"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    FILTER_VIOLATION = "FILTER_VIOLATION"
    REJECT_ORDER_ALREADY_TERMINAL = "REJECT_ORDER_ALREADY_TERMINAL"
    # S47 T9 — bybit-api-reviewer S38 M1: extend taxonomy для testnet debuggability
    INVALID_PARAM = "INVALID_PARAM"
    # S51 D1 — OrderLinkedID duplicate (Bybit V5 retCode 110072). A retried
    # placement reusing the SAME deterministic orderLinkId after the original
    # already landed. For idempotent flatten placements (S49 B1) this proves
    # our prior submit succeeded → flatten treats it as success, not a HALT.
    # This is the BYBIT-LOCAL enum; it does NOT affect the canonical 65-code
    # ReasonCode in src/risk/reason_codes.py.
    REJECT_DUPLICATE_ORDER = "REJECT_DUPLICATE_ORDER"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


_MAP: dict[int, ReasonCode] = {
    # S47 T9: 10001 — Parameter error / invalid argument (was UNKNOWN_ERROR before)
    10001: ReasonCode.INVALID_PARAM,
    10002: ReasonCode.CLOCK_DRIFT,
    10003: ReasonCode.WRONG_API_KEY,
    10006: ReasonCode.RATE_LIMIT_HIT,
    # S55 BYBIT-03 — order-frequency (170005) / order-count (170222) rate limits.
    # _retry_with_backoff retries these; on EXHAUSTION the adapter re-wraps the
    # rest BybitAPIError into adapter.BybitAPIError(reason=map_error(...)). They were
    # UNKNOWN_ERROR before, so coordinator.flatten could not recognize the .reason
    # (110072 short-circuit unreachable → fall-through to double-sell, BYBIT-02).
    170005: ReasonCode.RATE_LIMIT_HIT,
    170222: ReasonCode.RATE_LIMIT_HIT,
    10016: ReasonCode.EXCHANGE_MAINTENANCE,
    # 110001 stays REJECT_ORDER_ALREADY_TERMINAL — adapter.py line 213 pins this behaviour
    110001: ReasonCode.REJECT_ORDER_ALREADY_TERMINAL,
    # 110072 — OrderLinkedID is duplicate (S51 D1). Flatten paths pin retCode==110072
    # before treating it as success, so this mapping cannot silently swallow a
    # different error.
    110072: ReasonCode.REJECT_DUPLICATE_ORDER,
    110007: ReasonCode.INSUFFICIENT_BALANCE,
    110017: ReasonCode.FILTER_VIOLATION,
    170131: ReasonCode.FILTER_VIOLATION,
    170140: ReasonCode.FILTER_VIOLATION,
    170213: ReasonCode.FILTER_VIOLATION,
}


def map_error(ret_code: int, ret_msg: str = "") -> ReasonCode:  # noqa: ARG001
    """Return matching ReasonCode, or UNKNOWN_ERROR if ret_code not mapped."""
    return _MAP.get(ret_code, ReasonCode.UNKNOWN_ERROR)


class BybitAdapterError(RuntimeError):
    """S47 T10 — raised when Bybit V5 response schema is unexpected.

    bybit-api-reviewer S38 finding M2: direct dict access (resp["result"]["list"])
    raises bare KeyError on schema shift with no context. This exception provides
    a clear message including the calling operation context.
    """
