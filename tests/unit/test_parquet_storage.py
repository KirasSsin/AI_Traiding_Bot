from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from src.marketdata.models import Bar, DataQuality
from src.marketdata.storage import ParquetBarWriter


def _bar(i: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=UTC)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=base + timedelta(hours=i),
        close_time=base + timedelta(hours=i + 1),
        open=Decimal("60000"),
        high=Decimal("60500"),
        low=Decimal("59800"),
        close=Decimal("60200"),
        volume=Decimal("1.5"),
        trade_count=100,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_writer_creates_file_and_persists_bars(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    bars = [_bar(i) for i in range(3)]

    writer.append(bars)

    files = list(tmp_path.glob("*.parquet"))
    assert len(files) == 1
    table = pq.read_table(files[0])
    assert table.num_rows == 3
    assert set(table.schema.names) >= {
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "data_quality",
    }


def test_writer_leaves_no_tmp_file_on_success(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    path = writer.append([_bar(0)])

    assert path.exists()
    # final file written, no leftover temp artifact
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob("*.parquet")) == [path]


def test_writer_atomic_no_partial_final_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate a crash during the rename step → final path must not exist
    # (write went to .tmp), and the tmp artifact must be cleaned up.
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")

    import src.marketdata.storage as storage_mod

    def _boom(_src: str, _dst: str) -> None:
        raise OSError("simulated crash during rename")

    monkeypatch.setattr(storage_mod.os, "replace", _boom)

    with pytest.raises(OSError, match="simulated crash"):
        writer.append([_bar(0)])

    # no corrupt/partial final partition left behind
    assert list(tmp_path.glob("*.parquet")) == []
    # tmp cleaned up on failure
    assert list(tmp_path.glob("*.tmp")) == []


def test_writer_append_is_additive(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(i) for i in range(2)])
    writer.append([_bar(i) for i in range(2, 5)])

    files = sorted(tmp_path.glob("*.parquet"))
    total = sum(pq.read_table(f).num_rows for f in files)
    assert total == 5


# --- SHA-256 sidecar manifest tests ---


def test_append_creates_sha256_sidecar(tmp_path: Path) -> None:
    """Each parquet write must produce a matching .sha256 sidecar."""
    from src.marketdata.storage import verify_parquet

    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    path = writer.append([_bar(0)])

    sidecar = path.with_suffix(".sha256")
    assert sidecar.exists(), "sidecar .sha256 not written"
    # sidecar contains a valid 64-char hex digest
    digest = sidecar.read_text().strip()
    assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    # verify_parquet confirms integrity
    assert verify_parquet(path) is True


def test_verify_parquet_detects_corruption(tmp_path: Path) -> None:
    """`verify_parquet` returns False when file content differs from sidecar hash."""
    from src.marketdata.storage import verify_parquet

    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    path = writer.append([_bar(0)])

    # Corrupt the parquet (append a byte)
    path.write_bytes(path.read_bytes() + b"\x00")
    assert verify_parquet(path) is False


def test_verify_parquet_missing_sidecar(tmp_path: Path) -> None:
    """`verify_parquet` returns False when sidecar is absent."""
    from src.marketdata.storage import verify_parquet

    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    path = writer.append([_bar(0)])

    path.with_suffix(".sha256").unlink()
    assert verify_parquet(path) is False


def test_no_sidecar_tmp_artifact_on_success(tmp_path: Path) -> None:
    """Atomic write leaves no .sha256.tmp temp files on success."""
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(0)])

    assert list(tmp_path.glob("*.tmp")) == []


def test_sidecar_written_for_multiple_appends(tmp_path: Path) -> None:
    """Every `append` call produces its own sidecar; each passes verify_parquet."""
    from src.marketdata.storage import verify_parquet

    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    paths = [writer.append([_bar(i)]) for i in range(3)]

    sidecars = list(tmp_path.glob("*.sha256"))
    assert len(sidecars) == 3
    for p in paths:
        assert verify_parquet(p) is True
