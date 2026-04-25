"""DataFrame → TradeRecord conversion для DSR (S13 T5, closes S10/S12 carry-over)."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest
from src.backtest.trade_extractor import extract_trade_records
from src.risk.trade_history import TradeRecord


def _make_trades_df(n: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({
            "entry_ts": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i * 2),
            "exit_ts": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i * 2 + 1),
            "qty": 0.001,
            "entry_price": 50000.0 + i * 100,
            "exit_price": 50100.0 + i * 100,
            "net_pnl": 1.0 - i * 0.1,
            "fees_paid": 0.05,
        })
    return pd.DataFrame(rows)


def test_extract_trade_records_basic() -> None:
    """Healthy DataFrame → TradeRecord list, fields preserved Decimal precision."""
    df = _make_trades_df(n=3)
    records = extract_trade_records(df, symbol="BTCUSDT")

    assert len(records) == 3
    assert all(isinstance(r, TradeRecord) for r in records)
    assert records[0].symbol == "BTCUSDT"
    assert records[0].qty == Decimal("0.001")
    # pnl_pct = 1.0 / (0.001 * 50000) = 0.02
    assert records[0].pnl_pct == pytest.approx(Decimal("0.02"), rel=Decimal("0.01"))
    assert records[0].kelly_phase == 1


def test_extract_trade_records_empty_df() -> None:
    """Empty DataFrame → empty list, не crash."""
    df = pd.DataFrame()
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records == []


def test_extract_trade_records_synthetic_signal_id_unique() -> None:
    """Backtest synthesizes entry_signal_id UUID — unique per row."""
    df = _make_trades_df(n=5)
    records = extract_trade_records(df, symbol="BTCUSDT")
    signal_ids = [r.entry_signal_id for r in records]
    assert len(set(signal_ids)) == 5


def test_extract_trade_records_negative_pnl_preserved() -> None:
    """Loser trades: negative pnl_quote + pnl_pct preserved (no abs())."""
    df = pd.DataFrame([{
        "entry_ts": pd.Timestamp("2024-01-01", tz="UTC"),
        "exit_ts": pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),
        "qty": 0.001,
        "entry_price": 50000.0,
        "exit_price": 49500.0,
        "net_pnl": -0.5,
        "fees_paid": 0.05,
    }])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].pnl_quote == Decimal("-0.5")
    assert records[0].pnl_pct < Decimal("0")
