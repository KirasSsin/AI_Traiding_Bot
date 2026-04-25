---
title: trade-extractor — DataFrame → TradeRecord conversion
type: component
tags: [backtest, dsr, trade-extractor, sprint-13]
created: 2026-04-26
updated: 2026-04-26
status: stable
sources:
  - src/backtest/trade_extractor.py
---

# trade-extractor

**TL;DR:** Bridge between WFA per-fold trade DataFrames and DSR pipeline. Closes S10/S12 carry-over (`trades_for_dsr=[]` placeholder). Synthesizes UUID per row для DSR row identity. S13 T5 (per ADR 0028 Q5).

## Purpose

WFA produces per-fold trade DataFrames (columns: entry_ts, exit_ts, qty, entry_price, exit_price, net_pnl, fees_paid). DSR computation requires `list[TradeRecord]` (pydantic model). This module bridges the two layers.

## Public API

```python
from src.backtest.trade_extractor import extract_trade_records

records: list[TradeRecord] = extract_trade_records(
    df=fold_trades_df,  # pd.DataFrame from WalkForwardRunner output
    symbol="BTCUSDT",
)
```

Returns empty list if `df.empty`.

## Architecture rationale

- **UUID synthesis:** backtest doesn't have real signal_ids (live trading flow only). UUID4 collision probability ~0 for realistic N. Uniqueness = sole DSR-relevant constraint.
- **Default reason_code = EXIT_TP_HIT:** placeholder; backtest doesn't distinguish exit reasons. DSR/T1-T6 don't consume reason_code.
- **kelly_phase = 1 hardcoded:** backtest assumption. DSR doesn't consume phase.
- **Decimal precision:** float -> str -> Decimal pipeline. Acceptable для analytics (per S12 quant-stats T2 review precedent).

## Invariants

- `pnl_pct = pnl_quote / (qty x entry_price)` — simple return (DSR converts к log via `log(1+r)`)
- Negative pnl preserved (no abs())
- Empty DataFrame -> empty list (no crash)
- Caller responsible для N_trials tracking (CC1 — extractor agnostic)

## Related

- [[walk-forward]] — produces fold trade DataFrames
- [[dsr]] — consumes list[TradeRecord]
- [[strategy-metrics]] — also consumes list[TradeRecord] (T1-T6 extraction)
- [[../decisions/0028-sprint-13-strategy-validation]] — Q5 verdict (DSR active S13)

## Sources

- `src/backtest/trade_extractor.py` (S13 T5, commit a2f1e07)
- `tests/unit/test_trade_extractor.py` (4 tests)
