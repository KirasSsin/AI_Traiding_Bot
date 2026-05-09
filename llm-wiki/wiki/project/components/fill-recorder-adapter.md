---
title: FillRecorderAdapter
type: component
tags: [fill-recorder, bybit-ws, fill-history, production-wiring, s12]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/risk/fill_recorder_adapter.py
---

# FillRecorderAdapter

**TL;DR:** Bridges Bybit V5 WS execution events → `FillHistoryRepository`. 2-layer pattern: always-on structlog audit (Layer 1) + best-effort DB insert via lookup chain (Layer 2). Race-condition safe (skip+warn). S12 Q5 (per ADR 0027).

## Purpose

- Closes the 8-month-old `_NoopFillRecorder` stub in `_cmd_run` (ADR 0022 S8a T20, S11 T2 deferral).
- Enables operator post-mortem fill audit during S12 demo validation window.
- Satisfies `_FillRecorderProto` interface expected by `_cmd_run` without requiring `FillHistoryRepository` to be a drop-in (Q5 REVISE-additive — it is not).

## Публичный API

```python
class FillRecorderAdapter:
    def __init__(
        self,
        *,
        repo: FillHistoryRepository,
        state_repo: ExecutionStateRepo,
        trade_history_repo: TradeHistoryRepository,
    ) -> None: ...

    def on_fill_event(self, evt: dict[str, Any]) -> None:
        """Implements _FillRecorderProto. Called on every Bybit V5 WS execution event."""
```

## Архитектура — 2-layer pattern

### Layer 1: always-on audit (structlog)

Every `on_fill_event` call emits a structured log event `fill_event_received` with the full `evt` dict. Fires regardless of lookup chain success or failure. Provides recovery-safe audit trail: even if DB insert fails, the fill event is preserved in the structlog JSON stream.

### Layer 2: best-effort DB insert

Lookup chain resolves `WS orderId → trade_id`:

```
evt["orderId"]
  → execution_state.find_by_order_id(order_id)  →  bracket_id
  → trade_history.find_trade_id_by_signal(signal_id)  →  trade_id
  → FillHistoryRepository.insert_fill(FillRecord(..., parent_trade_id=trade_id))
```

If ANY step fails (record not found, exception, etc.) → log `fill_event_skipped` with reason + return. Never raises. Never crashes.

## S12 schema gap (S13 carry-over)

`execution_state` table has **no `entry_signal_id` column** per migrations 0003 + 0004 + 0005. The lookup chain breaks at the `bracket_id ↔ trade_id` gap: `find_by_order_id` returns a bracket row, but there is no path from `bracket_id` to `signal_id` without `entry_signal_id`. **Result: Layer 2 always skips during S12.**

Layer 1 (structlog audit) fires on every fill regardless — fill events are not lost.

**Fix deferred to S13:** add `entry_signal_id` column to `execution_state` via new migration + wire `Coordinator.start_bracket` to persist `signal_id` at bracket creation time. Q7 zero-migration constraint (S12 plan-level commitment) deferred this to S13.

## Инварианты

- **Never crashes on malformed WS event** — exception-swallowing per WS thread crash-prevention policy (a crash in the WS callback kills the consumer thread).
- **Layer 1 fires ALWAYS** — structlog audit is unconditional.
- **Layer 2 fires only when fully resolved** — any lookup miss → skip+warn, no partial writes.
- **Idempotent** — `FillHistoryRepository.insert_fill` uses UNIQUE INDEX on `exec_id`; duplicate WS events are silently ignored.

## Tests

`tests/unit/test_fill_recorder_adapter.py` — 7 tests covering:

- Layer 1 always fires (structlog event present regardless of lookup success)
- Layer 2 skips on `find_by_order_id` miss
- Layer 2 skips on `find_trade_id_by_signal` miss
- Layer 2 inserts on full resolution
- Exception-swallowing (malformed evt dict does not propagate)
- Idempotency (duplicate exec_id → no second insert attempt error)
- `on_fill_event` return type is `None`

## Связанные

- [[fill-history]] — `FillHistoryRepository` and `FillRecord` — DB-backed fill storage (S9 Q3 B1)
- [[ws-private-consumer]] — Bybit V5 private WS (order + wallet execution topic source)
- [[bybit-adapter]] — REST/WS Bybit V5 wiring
- [[coordinator]] — `_NoopFillRecorder` stub replaced by this adapter in `_cmd_run`
- [[../decisions/0027-sprint-12-live-demo-validation]] — Q5 verdict trail (REVISE-additive)
- [[../sprints/sprint-12-live-demo-validation]] — S12 delivery context

## Sources

- `src/risk/fill_recorder_adapter.py` (S12 T1, commit `044dad8`)
- `tests/unit/test_fill_recorder_adapter.py` (7 tests)
