"""Detect missing close_time intervals in Parquet bar archive."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq


def find_gaps(parquet_dir: Path, interval_ms: int) -> list[tuple[datetime, datetime]]:
    """Return list of (gap_start, gap_end) — where `gap_start` = close_time
    of the bar before the gap, `gap_end` = open_time of the bar after.
    Times are UTC datetimes (Parquet stores ns-precision UTC).
    """
    files = sorted(parquet_dir.glob("*.parquet"))
    if not files:
        return []

    close_times: list[datetime] = []
    open_times: list[datetime] = []
    for f in files:
        table = pq.read_table(f, columns=["open_time", "close_time"])  # type: ignore[no-untyped-call]
        for ot in table["open_time"].to_pylist():
            open_times.append(ot.replace(tzinfo=UTC) if ot.tzinfo is None else ot)
        for ct in table["close_time"].to_pylist():
            close_times.append(ct.replace(tzinfo=UTC) if ct.tzinfo is None else ct)

    paired = sorted(zip(open_times, close_times, strict=True), key=lambda p: p[0])
    step = timedelta(milliseconds=interval_ms)
    gaps: list[tuple[datetime, datetime]] = []
    for i in range(len(paired) - 1):
        _, prev_close = paired[i]
        next_open, _ = paired[i + 1]
        if next_open > prev_close and next_open - prev_close >= step:
            gaps.append((prev_close, next_open))
    return gaps
