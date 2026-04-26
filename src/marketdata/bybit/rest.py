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
        """Fetch OHLCV bars in [start_ms, end_ms). Paginates backward (Bybit V5 end-anchored).

        Per Bybit V5 spec: when start, end and limit are all specified, API returns the
        newest `limit` bars BEFORE `end`. Walking forward от start_ms causes each batch
        to return near end_ms → loop exits after 1 call for large ranges.

        Fix: walk backward — start с cur_end=end_ms, decrement cur_end к oldest_in_batch
        after each call, until oldest covers start_ms. Batches prepended so result is
        oldest-first within [start_ms, end_ms).
        """
        from src.marketdata.models import Bar, DataQuality

        # S19 Condition A1 (ADR 0034): single-dict refactor — value = (domain_interval_label, step_ms).
        # Add new timeframes here only — single source of truth, prevents dict drift.
        # S22 ADR 0037: added "240" (4H) для v0.5-C test.
        # S25: added 5M/30M/2H/1D для dashboard timeframe coverage.
        intervals: dict[str, tuple[str, int]] = {
            "5": ("5m", 300_000),
            "15": ("15m", 900_000),
            "30": ("30m", 1_800_000),
            "60": ("1h", 3_600_000),
            "120": ("2h", 7_200_000),
            "240": ("4h", 14_400_000),
            "D": ("1d", 86_400_000),
        }
        if interval not in intervals:
            raise ValueError(
                f"Unsupported interval '{interval}'. "
                f"Supported: {sorted(intervals.keys())}. Add к intervals dict в rest.py."
            )
        domain_interval, step_ms = intervals[interval]

        bars: list[Bar] = []
        cur_end = end_ms
        while cur_end > start_ms:
            resp = self._http.get_kline(
                category="spot",
                symbol=symbol,
                interval=interval,
                start=start_ms,
                end=cur_end,
                limit=limit_per_call,
            )
            if resp["retCode"] != 0:
                raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""))
            rows = list(reversed(resp["result"]["list"]))  # oldest-first within batch
            if not rows:
                break
            batch_bars: list[Bar] = []
            for row in rows:
                open_ms = int(row[0])
                if open_ms < start_ms or open_ms >= end_ms:
                    continue
                open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
                close_time = open_time + timedelta(milliseconds=step_ms)
                batch_bars.append(
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
            if not batch_bars:
                break
            # Prepend batch (batches walk backward; prepending keeps oldest-first order)
            bars = batch_bars + bars
            # Walk back: next batch ends at oldest bar of current batch
            oldest_open_ms = int(rows[0][0])
            if oldest_open_ms <= start_ms:
                break  # covered start_ms
            cur_end = oldest_open_ms
        return bars
