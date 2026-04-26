"""S27 T4 — preserve actual exit reason_code в trade_extractor.

Pre-fix: src/backtest/trade_extractor.py:70 hardcoded ReasonCode.EXIT_TP_HIT
для всех trades regardless of actual exit type. Result: every trade в
formulas_audit_v1.json shows EXIT_TP_HIT including SL hits.

Per trading-logic-reviewer audit (CC5):
> "EXIT_TP_HIT on ALL 30 experiments including losses. Every trade across
> all 30 experiments shows reason_code=EXIT_TP_HIT, including trades with
> negative PnL. Stop-loss hits should be EXIT_SL_HIT."

Fix: replay_engine emits free-form 'SL'/'TP'/'SIGNAL_FLIP'/'EOD'/'KILL_SWITCH'
strings в trades_df 'reason_code' column. Map к canonical ReasonCode enum.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.trade_extractor import extract_trade_records
from src.risk.reason_codes import ReasonCode


def _make_trade_row(
    *, reason_code_str: str, net_pnl: float = 10.0,
) -> dict:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    return {
        "entry_ts": pd.Timestamp(base),
        "exit_ts": pd.Timestamp(base.replace(hour=2)),
        "qty": 0.001,
        "entry_price": 50000.0,
        "exit_price": 50000.0 + (net_pnl / 0.001),
        "net_pnl": net_pnl,
        "fees_paid": 0.05,
        "reason_code": reason_code_str,
    }


def test_sl_exit_maps_to_canonical_exit_sl_hit() -> None:
    df = pd.DataFrame([_make_trade_row(reason_code_str="SL", net_pnl=-15.0)])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert len(records) == 1
    assert records[0].reason_code == ReasonCode.EXIT_SL_HIT


def test_tp_exit_maps_to_canonical_exit_tp_hit() -> None:
    df = pd.DataFrame([_make_trade_row(reason_code_str="TP", net_pnl=20.0)])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].reason_code == ReasonCode.EXIT_TP_HIT


def test_signal_flip_maps_to_canonical_exit_signal_flip() -> None:
    df = pd.DataFrame([_make_trade_row(reason_code_str="SIGNAL_FLIP", net_pnl=5.0)])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].reason_code == ReasonCode.EXIT_SIGNAL_FLIP


def test_eod_maps_to_canonical_exit_time_stop() -> None:
    df = pd.DataFrame([_make_trade_row(reason_code_str="EOD", net_pnl=2.0)])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].reason_code == ReasonCode.EXIT_TIME_STOP


def test_kill_switch_maps_to_canonical_exit_circuit_breaker() -> None:
    df = pd.DataFrame([_make_trade_row(reason_code_str="KILL_SWITCH", net_pnl=-10.0)])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].reason_code == ReasonCode.EXIT_CIRCUIT_BREAKER


def test_missing_reason_code_falls_back_to_exit_tp_hit() -> None:
    """Backward compat: row without reason_code field defaults к EXIT_TP_HIT."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    row = {
        "entry_ts": pd.Timestamp(base),
        "exit_ts": pd.Timestamp(base.replace(hour=2)),
        "qty": 0.001,
        "entry_price": 50000.0,
        "exit_price": 50010.0,
        "net_pnl": 10.0,
        "fees_paid": 0.05,
    }
    df = pd.DataFrame([row])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].reason_code == ReasonCode.EXIT_TP_HIT


def test_unknown_reason_code_falls_back_to_exit_tp_hit() -> None:
    """Unknown free-form string → EXIT_TP_HIT fallback (don't crash)."""
    df = pd.DataFrame([_make_trade_row(reason_code_str="UNKNOWN_FOOBAR", net_pnl=1.0)])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].reason_code == ReasonCode.EXIT_TP_HIT


def test_mixed_exit_reasons_preserved_per_trade() -> None:
    """Multi-row df: each trade preserves its own reason_code."""
    df = pd.DataFrame([
        _make_trade_row(reason_code_str="TP", net_pnl=20.0),
        _make_trade_row(reason_code_str="SL", net_pnl=-15.0),
        _make_trade_row(reason_code_str="SIGNAL_FLIP", net_pnl=3.0),
    ])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert len(records) == 3
    assert records[0].reason_code == ReasonCode.EXIT_TP_HIT
    assert records[1].reason_code == ReasonCode.EXIT_SL_HIT
    assert records[2].reason_code == ReasonCode.EXIT_SIGNAL_FLIP
