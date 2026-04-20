"""Parquet writer for OHLCV bars (OLAP storage)."""
from collections.abc import Iterable
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.marketdata.models import Bar

_SCHEMA = pa.schema(
    [
        pa.field("open_time", pa.timestamp("ns", tz="UTC")),
        pa.field("close_time", pa.timestamp("ns", tz="UTC")),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("trade_count", pa.int64()),
        pa.field("data_quality", pa.string()),
    ]
)


class ParquetBarWriter:
    """Writes Bars to Parquet files (snappy compression).

    Each `append()` produces one new `.parquet` file, timestamped.
    Consolidation (merge small files) — out of scope v0.1.
    """

    def __init__(self, directory: Path, symbol: str, interval: str) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._symbol = symbol
        self._interval = interval

    def append(self, bars: Iterable[Bar]) -> Path:
        bars_list = list(bars)
        if not bars_list:
            raise ValueError("cannot append empty bar list")

        table = pa.table(
            {
                "open_time": [b.open_time for b in bars_list],
                "close_time": [b.close_time for b in bars_list],
                "open": [float(b.open) for b in bars_list],
                "high": [float(b.high) for b in bars_list],
                "low": [float(b.low) for b in bars_list],
                "close": [float(b.close) for b in bars_list],
                "volume": [float(b.volume) for b in bars_list],
                "trade_count": [b.trade_count for b in bars_list],
                "data_quality": [str(b.data_quality) for b in bars_list],
            },
            schema=_SCHEMA,
        )

        fname = (
            f"{self._symbol.lower()}_{self._interval}_"
            f"{bars_list[0].close_time.strftime('%Y%m%d%H%M%S')}"
            f"-{bars_list[-1].close_time.strftime('%Y%m%d%H%M%S')}.parquet"
        )
        path = self._dir / fname
        pq.write_table(table, path, compression="snappy")
        return path
