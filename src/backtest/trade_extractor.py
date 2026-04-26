"""DataFrame → TradeRecord conversion для DSR computation.

Sprint 13 Task 5 (per ADR 0028 Q5). Closes S10 + S12 carry-over: WFA produces
per-fold trade DataFrames; DSR requires list[TradeRecord]. Bridge между layers.

Backtest synthesizes entry_signal_id (UUID) — uniqueness sole DSR-relevant
constraint. kelly_phase = 1 (backtest assumption).

S27 T4 (CC5): preserve actual exit reason_code from replay_engine. Pre-fix
hardcoded EXIT_TP_HIT для всех trades — corrupted formulas_audit_v1.json
diagnostic value (couldn't distinguish SL hits from TP hits). Free-form
strings 'SL'/'TP'/'SIGNAL_FLIP'/'EOD'/'KILL_SWITCH' → canonical ReasonCode.

CC1: extractor agnostic к N_trials (consumer responsibility).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


# S27 T4: replay_engine free-form exit_reason → canonical ReasonCode mapping
_EXIT_REASON_MAP: dict[str, ReasonCode] = {
    "SL": ReasonCode.EXIT_SL_HIT,
    "TP": ReasonCode.EXIT_TP_HIT,
    "SIGNAL_FLIP": ReasonCode.EXIT_SIGNAL_FLIP,
    "EOD": ReasonCode.EXIT_TIME_STOP,
    "KILL_SWITCH": ReasonCode.EXIT_CIRCUIT_BREAKER,
}


def _map_exit_reason(raw: object) -> ReasonCode:
    """Map replay_engine free-form exit_reason к canonical ReasonCode.

    Unknown / missing → EXIT_TP_HIT (backward-compat fallback).
    """
    if raw is None:
        return ReasonCode.EXIT_TP_HIT
    key = str(raw)
    return _EXIT_REASON_MAP.get(key, ReasonCode.EXIT_TP_HIT)


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

        # S27 T4: preserve actual exit reason_code from replay_engine output
        reason_code = _map_exit_reason(row.get("reason_code"))

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
                reason_code=reason_code,
                kelly_phase=1,
                recorded_at=now_utc,
            )
        )

    return records
