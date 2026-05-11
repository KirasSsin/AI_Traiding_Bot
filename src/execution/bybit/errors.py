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
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


_MAP: dict[int, ReasonCode] = {
    # S47 T9: 10001 — Parameter error / invalid argument (was UNKNOWN_ERROR before)
    10001: ReasonCode.INVALID_PARAM,
    10002: ReasonCode.CLOCK_DRIFT,
    10003: ReasonCode.WRONG_API_KEY,
    10006: ReasonCode.RATE_LIMIT_HIT,
    10016: ReasonCode.EXCHANGE_MAINTENANCE,
    # 110001 stays REJECT_ORDER_ALREADY_TERMINAL — adapter.py line 213 pins this behaviour
    110001: ReasonCode.REJECT_ORDER_ALREADY_TERMINAL,
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
