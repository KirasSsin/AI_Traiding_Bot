"""Map Bybit V5 retCode → domain ReasonCode (per ADR 0016)."""

from enum import StrEnum


class ReasonCode(StrEnum):
    CLOCK_DRIFT = "CLOCK_DRIFT"
    WRONG_API_KEY = "WRONG_API_KEY"
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
    EXCHANGE_MAINTENANCE = "EXCHANGE_MAINTENANCE"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    FILTER_VIOLATION = "FILTER_VIOLATION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


_MAP: dict[int, ReasonCode] = {
    10002: ReasonCode.CLOCK_DRIFT,
    10003: ReasonCode.WRONG_API_KEY,
    10006: ReasonCode.RATE_LIMIT_HIT,
    10016: ReasonCode.EXCHANGE_MAINTENANCE,
    110007: ReasonCode.INSUFFICIENT_BALANCE,
    110017: ReasonCode.FILTER_VIOLATION,
    170131: ReasonCode.FILTER_VIOLATION,
    170140: ReasonCode.FILTER_VIOLATION,
    170213: ReasonCode.FILTER_VIOLATION,
}


def map_error(ret_code: int, _ret_msg: str = "") -> ReasonCode:  # noqa: ARG001
    """Return matching ReasonCode, or UNKNOWN_ERROR if ret_code not mapped."""
    return _MAP.get(ret_code, ReasonCode.UNKNOWN_ERROR)
