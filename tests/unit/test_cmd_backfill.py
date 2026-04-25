"""_cmd_backfill wire tests (S13 T2 per ADR 0028 Q3)."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from src import __main__ as cli
from src.marketdata.models import Bar, DataQuality


def _make_bar(open_time: datetime) -> Bar:
    close_time = datetime(
        open_time.year, open_time.month, open_time.day,
        open_time.hour + 1 if open_time.hour < 23 else 0,
        tzinfo=UTC,
    )
    # ensure close_time > open_time always
    from datetime import timedelta
    close_time = open_time + timedelta(hours=1)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=open_time,
        close_time=close_time,
        open=Decimal("50000.0"),
        high=Decimal("50100.0"),
        low=Decimal("49900.0"),
        close=Decimal("50050.0"),
        volume=Decimal("1.0"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_cmd_backfill_writes_parquet_with_paginated_klines(tmp_path: Path) -> None:
    """T2 — backfill calls BybitRESTClient.get_klines + writes Parquet."""
    from datetime import timedelta
    bars = [_make_bar(datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=h)) for h in range(100)]

    with patch("src.__main__.BybitRESTClient") as mock_rest_class:
        mock_rest = MagicMock()
        mock_rest.get_klines.return_value = bars
        mock_rest_class.return_value = mock_rest

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test"
            mock_settings.bybit_api_secret = "test"
            mock_settings.testnet = True
            mock_settings_class.return_value = mock_settings

            args = argparse.Namespace(
                symbol="BTCUSDT",
                from_date="2024-01-01",
                to_date="2024-01-05",
                output_path=str(tmp_path / "BTCUSDT_1h.parquet"),
            )
            exit_code = cli._cmd_backfill(args)

    assert exit_code == 0
    assert (tmp_path / "BTCUSDT_1h.parquet").exists()
    df = pd.read_parquet(tmp_path / "BTCUSDT_1h.parquet")
    assert len(df) == 100
    assert set(df.columns) >= {"time", "open", "high", "low", "close", "volume"}
    mock_rest.get_klines.assert_called_once()


def test_cmd_backfill_returns_error_on_empty_response(tmp_path: Path) -> None:
    """T2 — empty kline response → exit 1, no crash, no file written."""
    with patch("src.__main__.BybitRESTClient") as mock_rest_class:
        mock_rest = MagicMock()
        mock_rest.get_klines.return_value = []
        mock_rest_class.return_value = mock_rest

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test"
            mock_settings.bybit_api_secret = "test"
            mock_settings.testnet = True
            mock_settings_class.return_value = mock_settings

            args = argparse.Namespace(
                symbol="BTCUSDT",
                from_date="2024-01-01",
                to_date="2024-01-05",
                output_path=str(tmp_path / "empty.parquet"),
            )
            exit_code = cli._cmd_backfill(args)

    assert exit_code == 1
    assert not (tmp_path / "empty.parquet").exists()


def test_cmd_backfill_default_output_path_derives_from_symbol(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T2 — default output = data/<symbol>_1h.parquet relative to cwd."""
    monkeypatch.chdir(tmp_path)
    from datetime import timedelta
    bars = [_make_bar(datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=h)) for h in range(5)]

    with patch("src.__main__.BybitRESTClient") as mock_rest_class:
        mock_rest = MagicMock()
        mock_rest.get_klines.return_value = bars
        mock_rest_class.return_value = mock_rest

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test"
            mock_settings.bybit_api_secret = "test"
            mock_settings.testnet = True
            mock_settings_class.return_value = mock_settings

            args = argparse.Namespace(
                symbol="BTCUSDT",
                from_date="2024-01-01",
                to_date="2024-01-02",
                output_path=None,
            )
            exit_code = cli._cmd_backfill(args)

    assert exit_code == 0
    expected_path = tmp_path / "data" / "BTCUSDT_1h.parquet"
    assert expected_path.exists()
