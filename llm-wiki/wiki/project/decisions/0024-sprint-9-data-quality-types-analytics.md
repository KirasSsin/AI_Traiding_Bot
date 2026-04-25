---
title: 0024. Sprint 9 — Data quality detector + mypy strict + per-fill analytics + DSR
type: decision
date: 2026-04-25
sprint: 9
tags: [adr, sprint-9, data-quality, mypy, per-fill, dsr, analytics]
sources:
  - project/pre-s9-backlog.md
  - project/decisions/0023-halt-code-fsm-event-mapping.md
  - project/decisions/0022-sprint-8a-live-runtime.md
status: accepted
---

# 0024. Sprint 9 — Data quality + mypy strict + per-fill analytics + DSR

**Status:** accepted
**Date:** 2026-04-25

## Context

Sprint 9 закрывает 3 deferred carry-overs:

1. **C (Q1):** WS+REST price epsilon-halt detector — deferred с S8b (originally S8 Q8 alternative); `HALT_DATA_QUALITY` pre-allocated в `ReasonCode` enum since S4 без активного detector.
2. **G (Q2):** mypy --strict full enable — `pyproject.toml` уже declares `strict = true` но overrides excluded `src.core.*`, `src.backtest.*`, `src.risk.*` через `ignore_errors = true`.
3. **B (Q3):** Per-fill analytics + DSR foundation — deferred ADR 0021 (S7) → ADR 0022 (S8a) → S8b → S9 (3-sprint deferral).

PHASE 2 brainstorming verdicts (`pre-s9-backlog.md`):
- Q1: REVISE accepted — REST-vs-REST consecutive bar (NOT WS+REST kline). Trader rationale: WS kline subscription doesn't exist, async dep contradicts S8a ADR 0022 deferral, partial-bar updates create false-positive risk.
- Q2: REVISE accepted — order src.core → src.risk → src.backtest. Empirical follow-up в plan: ALL 3 modules pass `mypy --strict` clean per-module check. But `mypy src/` full-tree exposed 18 cross-module errors after override removal — fixed in T4 follow-up commit.
- Q3: CONFIRM — split B1 (per-fill table + WS execution topic) + B2 (DSR module on TradeRecord).

## Decision

### Q1 (C — Data quality)

`BarPriceQualityDetector` в `src/marketdata/quality.py`:
- Single-instance in-memory baseline (NOT stateless — clarified post-review). Baseline lost на restart (acceptable v0.1 single-process).
- Threshold: 0.5% relative deviation (Settings: `runtime_quality_threshold_pct`, default `Decimal("0.005")`)
- Cadence: per-bar (after `BarSource.poll()` returns new closed bar)
- Halt routing: `Coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)` → existing `RISK_HALT` event path
- FSM impact: NONE (uses existing event, no new state/event/transition)
- `_stopping=True` set after halt (matches stall + kill-switch patterns; halt terminal — main loop must exit, else log storm at poll cadence)

Per ADR 0023 invariant: `HALT_DATA_QUALITY` added к `_REQUEST_HALT_CODES` allow-list в `tests/property/test_request_halt_mapping.py`. Property test 4/4 GREEN.

### Q2 (G — mypy strict)

Removed block from `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["src.core.*", "src.backtest.*", "src.risk.*"]
ignore_errors = true
```

Empirical pre-removal per-module check (`mypy --strict src/risk/`) reported clean — but full-tree `mypy src/` exposed 18 cross-module errors (per-module mypy doesn't see import resolution). T4 follow-up fixed all 18:
- 5 import-untyped (added pandas/scipy/plotly к `ignore_missing_imports`)
- 3 import-not-found (added plotly)
- 2 unused-ignore (cleanup)
- 2 type-arg (added type parameters)
- 2 arg-type (explicit None checks)
- 1 no-any-return (annotated json.loads result)
- 3 operator (Decimal accumulator с explicit `start=Decimal(0)`)

Result: `mypy src/` → Success in 62 source files. Zero behavioral changes.

### Q3 B1 (Per-fill schema)

- NEW migration: `migrations/0006_trade_fills.sql` — `trade_fills` table с FK `parent_trade_id → trade_history.trade_id`, UNIQUE INDEX `exec_id`, composite index (parent_trade_id, fill_ts)
- NEW model: `src/risk/fill_history.py::FillRecord` (pydantic v2 frozen)
- NEW repository: `src/risk/fill_history.py::FillHistoryRepository`
- WS extension: `src/execution/bybit/ws_private.py` adds `_FillRecorderProto` Protocol + `execution_stream` subscription + `_on_execution_raw` handler
- FK enforcement test added (PRAGMA foreign_keys = ON, INSERT с invalid parent_trade_id raises IntegrityError)

**Production wiring deferred:** `src/__main__.py::_cmd_run` is STUB since S8a (T20 integration test never completed). Concrete FillRecorder адаптер (Bybit dict → FillRecord) NOT instantiated in production. Defer к operator-readiness sprint.

### Q3 B2 (DSR module)

- NEW: `src/analytics/dsr.py` (`src/analytics/__init__.py` пуст stub since S4)
- Functions: `compute_returns(trades, *, use_log=True)`, `compute_dsr(trades, *, benchmark_sharpe=0.0, n_trials=1, use_log=True)`
- Operates на `TradeRecord` array (closed trades с `exit_ts` populated) — no look-ahead
- log returns default (additive compounding); simple via flag
- **Pearson kurtosis** (NOT Fisher excess) per Bailey & López de Prado eq. 13 — caught by quant-stats-reviewer T9 BLOCKER B1
- `n_trials > 1` raises `NotImplementedError` (eq. 12 sigma_SR multiplier NYI v0.1, defer к S10+)
- Annualization NOT applied — per-trade Sharpe internally consistent для DSR (Φ output unit-free, annualization cancels)
- quant-stats-reviewer T9: APPROVED post-fix

## Consequences

**Plus:**
- HALT_DATA_QUALITY now active (was placeholder enum-only since S4)
- mypy strict prevents future type drift accumulation (61 source files clean)
- Per-fill granularity unblocks S10+ analytics (slippage, fee breakdown, partial-fill audit)
- DSR foundation ready для S10 walk-forward acceptance gate
- 3 deferred carry-overs closed
- Property test ADR 0023 invariant expanded (3 → 4 codes)

**Minus:**
- Production wiring deferred (FillRecorder not instantiated в `__main__.py::_cmd_run` — pre-existing S8a STUB, не S9 regression)
- New WS topic = surface area для pybit drift (mitigated: `_FillRecorderProto` + try/except в `_on_execution_raw` mirrors existing `_on_order_raw` pattern)
- DSR без real backtest data = academic until first live trades (S11+)
- mypy strict revealed 18 cross-module errors that per-module check missed — pattern lesson for future override removals (always full-tree verify)

## Related

- [[../pre-s9-backlog]] — PHASE 2 brainstorming verdicts trail
- [[0021-sprint-7-resilience]] — per-fill execution topic deferral source
- [[0022-sprint-8a-live-runtime]] — wallet WS+REST epsilon-halt rejection (REST canonical per ADR 0020 sub-decision 4)
- [[0023-halt-code-fsm-event-mapping]] — `_REQUEST_HALT_CODES` allow-list invariant
- [[../components/data-quality]] — Q1 detector implementation (T12)
- [[../components/fill-history]] — Q3 B1 implementation
- [[../components/dsr]] — Q3 B2 implementation
- [[../plans/2026-04-25-sprint-9-quality-types-analytics]] — implementation plan + trace map
- [[../sprints/sprint-09-data-quality-types-analytics]] — sprint delivery record

## Amendments

- (none yet)
