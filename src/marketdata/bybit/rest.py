"""Thin wrapper over pybit.unified_trading.HTTP — see ADR 0016."""

from datetime import UTC, datetime

from pybit.unified_trading import HTTP


class BybitAPIError(RuntimeError):
    """Raised when Bybit V5 returns non-zero retCode."""

    def __init__(self, ret_code: int, ret_msg: str) -> None:
        super().__init__(f"Bybit API error retCode={ret_code}: {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg


class BybitRESTClient:
    """Wraps pybit V5 HTTP client with our domain-friendly return types."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool) -> None:
        self._http = HTTP(testnet=testnet, api_key=api_key, api_secret=api_secret)

    def get_server_time(self) -> datetime:
        """Fetch Bybit server time as UTC datetime (seconds precision)."""
        resp = self._http.get_server_time()
        if resp["retCode"] != 0:
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""))
        ts_s = int(resp["result"]["timeSecond"])
        return datetime.fromtimestamp(ts_s, tz=UTC)
