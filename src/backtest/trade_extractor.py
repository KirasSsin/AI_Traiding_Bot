"""DataFrame → TradeRecord conversion для DSR computation.

Sprint 13 Task 5 (per ADR 0028 Q5). Closes S10 + S12 carry-over: WFA produces
per-fold trade DataFrames; DSR requires list[TradeRecord]. Bridge между layers.

Backtest synthesizes entry_signal_id (UUID) — uniqueness sole DSR-relevant
constraint. Default reason_code = EXIT_TP_HIT (placeholder, doesn't affect DSR
which consumes pnl_pct only). kelly_phase = 1 (backtest assumption).

CC1: extractor agnostic к N_trials (consumer responsibility).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def extract_trade_records(df: pd.DataFrame, *, symbol: str) -> list[TradeRecord]:
    """Convert WFA fold trade DataFrame → list[TradeRecord] для DSR.

    Args:
        df: pandas DataFrame с columns entry_ts, exit_ts, qty, entry_price,
            exit_price, net_pnl, fees_paid.
        symbol: trading pair.

    Returns:
        list[TradeRecord] (empty if df.empty).
    """
    if df.empty:
        return []

    records: list[TradeRecord] = []
    now_utc = datetime.now(UTC)

    for _, row in df.iterrows():
        qty = Decimal(str(row["qty"]))
        entry_price = Decimal(str(row["entry_price"]))
        pnl_quote = Decimal(str(row["net_pnl"]))
        fees_paid = Decimal(str(row.get("fees_paid", 0)))

        notional = qty * entry_price
        pnl_pct = (pnl_quote / notional) if notional > 0 else Decimal("0")

        entry_ts = row["entry_ts"]
        if hasattr(entry_ts, "to_pydatetime"):
            entry_ts = entry_ts.to_pydatetime()

        exit_ts = row["exit_ts"]
        if hasattr(exit_ts, "to_pydatetime"):
            exit_ts = exit_ts.to_pydatetime()

        records.append(
            TradeRecord(
                symbol=symbol,
                entry_signal_id=uuid4(),
                entry_ts=entry_ts,
                exit_ts=exit_ts,
                qty=qty,
                entry_price=entry_price,
                exit_price=Decimal(str(row["exit_price"])),
                pnl_quote=pnl_quote,
                pnl_pct=pnl_pct,
                fees_paid=fees_paid,
                reason_code=ReasonCode.EXIT_TP_HIT,
                kelly_phase=1,
                recorded_at=now_utc,
            )
        )

    return records
