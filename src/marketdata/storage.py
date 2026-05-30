"""Parquet writer for OHLCV bars (OLAP storage)."""

import hashlib
import os
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
        sidecar = path.with_suffix(".sha256")
        # Atomic write: stage both parquet and sidecar to .tmp, then os.replace
        # (atomic rename on POSIX) so a crash never leaves truncated/corrupt files.
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_sidecar = sidecar.with_suffix(".sha256.tmp")
        try:
            pq.write_table(table, tmp_path, compression="snappy")  # type: ignore[no-untyped-call]
            digest = _sha256(tmp_path)
            tmp_sidecar.write_text(digest)
            os.replace(tmp_path, path)
            os.replace(tmp_sidecar, sidecar)
        finally:
            # tmps are gone after successful replaces; only matters if an error raised.
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            if tmp_sidecar.exists():
                tmp_sidecar.unlink(missing_ok=True)
        return path


def _sha256(path: Path) -> str:
    """Return lowercase hex SHA-256 digest of a file's contents."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_parquet(path: Path) -> bool:
    """Return True if path's SHA-256 matches its .sha256 sidecar; False otherwise.

    Returns False (not raises) when the sidecar is missing or the digest mismatches,
    so callers can branch on integrity without exception handling.
    """
    sidecar = path.with_suffix(".sha256")
    if not sidecar.exists():
        return False
    expected = sidecar.read_text().strip()
    return _sha256(path) == expected
