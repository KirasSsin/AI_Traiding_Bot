---
name: Multi-timeframe + multi-symbol architectural gaps (S15 brainstorm)
description: Key patterns and blockers discovered during S15 Q2/Q3/Q4 architecture feasibility review
type: project
---

## RiskManager Kelly contamination (Q2 blocker)

`src/risk/trade_history.py::load_recent` (line 85-93): `WHERE exit_ts >= ?` has no symbol filter.
With N symbols sharing one DB, Kelly phase inputs for each symbol bleed across all symbols.
Fix required before multi-symbol is safe: add `symbol: str | None = None` param to `load_recent`,
pass `symbol=self._symbol` from `RiskManager._compute_pb`.

**Why:** Per-symbol Kelly requires per-symbol win-rate/payoff. Cross-symbol contamination = wrong sizing.
**How to apply:** Flag as BLOCK in any multi-symbol PR that does not include this fix.

## BarSource is already multi-timeframe (Q3 confirmed)

`src/runtime/bar_source.py::BarSource._INTERVAL_MS` includes all intervals including "15": 900_000.
BarSource, BarBuilder, Bar model, and Bar.interval Literal all already support "15m".
The WS consumer (ws.py) constructs topic via pybit kline_stream(interval=, symbol=) — config-driven.
**Not a bottleneck for 15M expansion.**

## rest.py interval_map single-entry pattern (Q3 blocker)

`src/marketdata/bybit/rest.py::get_klines` lines 66-68:
`interval_map = {"60": "1h"}` and `interval_ms = {"60": 3_600_000}`.
KeyError on any interval != "60". Must extend both dicts for each new timeframe.
Comment "# extend when adding more TFs" is the correct location.

## heal_max_age_seconds semantic coupling (Q3 blocker)

`src/platform/config.py::heal_max_age_seconds` default=3600 with description "1 bar period of 1H".
At 15M (900s/bar), default 3600s = 4 bars stale passes heal check → production safety bug.
Fix: compute at runtime from interval_ms (interval_ms // 1000 * N_bars), not hardcoded field default.

## BybitWSConsumer (src/marketdata/bybit/ws.py) is dead code in live runtime

`_cmd_run` uses REST BarSource, not BybitWSConsumer. ws.py uses asyncio.Queue + call_soon_threadsafe.
This file is unused in live trading path. Flag as dead code candidate. If ever wired, asyncio integration
needs ADR (ADR 0022 defers asyncio to S9+, still deferred as of S15).

## _cmd_backfill interval hardcoding (Q3 medium)

`src/__main__.py::_cmd_backfill` line 205: `get_klines(symbol, "60", ...)` literal.
`_load_ohlcv` line 335: `f"data/{symbol}_1h.parquet"` literal.
Both break at 15M. Fix: `--interval` CLI arg + derive parquet filename from interval label.

## coordinator-per-symbol pattern safe for ADR 0022

N independent Coordinator instances each with their own RLock = N single-writers.
ADR 0022 invariant is per-instance, not process-global. Replication pattern (not refactor) preserves it.
execution_state PRIMARY KEY=symbol already supports multi-row (one per symbol).
