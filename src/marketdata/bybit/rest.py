"""Thin wrapper over pybit.unified_trading.HTTP — see ADR 0016."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from pybit.unified_trading import HTTP

if TYPE_CHECKING:
    from src.marketdata.filters import BybitFilters
    from src.marketdata.models import Bar


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

    def get_filters(self, symbol: str) -> BybitFilters:
        """Fetch `/v5/market/instruments-info?category=spot&symbol=X` → filters."""
        from src.marketdata.filters import BybitFilters

        resp = self._http.get_instruments_info(category="spot", symbol=symbol)
        return BybitFilters.from_instruments_info(resp)

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit_per_call: int = 1000,
    ) -> list[Bar]:
        """Fetch OHLCV bars in [start_ms, end_ms). Paginates if > 1000 rows."""
        from src.marketdata.models import Bar, DataQuality

        interval_map = {"60": "1h"}  # extend when adding more TFs
        interval_ms = {"60": 3_600_000}
        step_ms = interval_ms[interval]
        domain_interval = interval_map[interval]

        bars: list[Bar] = []
        cur_start = start_ms
        while cur_start < end_ms:
            resp = self._http.get_kline(
                category="spot",
                symbol=symbol,
                interval=interval,
                start=cur_start,
                end=end_ms,
                limit=limit_per_call,
            )
            if resp["retCode"] != 0:
                raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""))
            rows = list(reversed(resp["result"]["list"]))  # oldest-first
            if not rows:
                break
            for row in rows:
                open_ms = int(row[0])
                if open_ms >= end_ms:  # enforce [start_ms, end_ms) — Bybit end is inclusive
                    continue
                open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
                close_time = open_time + timedelta(milliseconds=step_ms)
                bars.append(
                    Bar(
                        symbol=symbol,
                        interval=domain_interval,
                        open_time=open_time,
                        close_time=close_time,
                        open=Decimal(row[1]),
                        high=Decimal(row[2]),
                        low=Decimal(row[3]),
                        close=Decimal(row[4]),
                        volume=Decimal(row[5]),
                        trade_count=0,
                        is_closed=True,
                        data_quality=DataQuality.OK,
                    )
                )
            last_open_ms = int(rows[-1][0])
            cur_start = last_open_ms + step_ms
        return bars
