---
title: Fill history — per-fill audit + analytics base
type: component
tags: [analytics, persistence, fills, ws-execution, sprint-9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/risk/fill_history.py
  - migrations/0006_trade_fills.sql
  - src/execution/bybit/ws_private.py
---

# Fill history

**TL;DR:** Per-fill granular audit log. `FillRecord` (pydantic v2 frozen) + `FillHistoryRepository` (SQLite-backed). FK к `trade_history.trade_id` (one trade → N fills). Idempotent insert на `exec_id` UNIQUE INDEX. Source = Bybit V5 WS `execution` topic (added в S9). Used by analytics (slippage measurement, fee breakdown, partial-fill audit). Production wiring of concrete recorder pending (`__main__.py::_cmd_run` STUB since S8a — defer к operator-readiness sprint).

## Публичный API

| Symbol | Path | Role |
|--------|------|------|
| `FillRecord` | `src/risk/fill_history.py::FillRecord` | pydantic v2 frozen model |
| `FillHistoryRepository.insert_fill` | `src/risk/fill_history.py::FillHistoryRepository.insert_fill` | idempotent insert; returns fill_id |
| `FillHistoryRepository.load_by_trade` | `src/risk/fill_history.py::FillHistoryRepository.load_by_trade` | ordered by fill_ts ASC |
| `FillHistoryRepository.count` | `src/risk/fill_history.py::FillHistoryRepository.count` | row count |

## Схема (migrations/0006_trade_fills.sql)

| Column | Type | Constraint |
|--------|------|-----------|
| fill_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| parent_trade_id | INTEGER | NOT NULL, FK trade_history.trade_id |
| exec_id | TEXT | NOT NULL, UNIQUE INDEX |
| fill_qty | TEXT | Decimal as str |
| fill_price | TEXT | Decimal as str |
| fill_fee | TEXT | Decimal as str |
| fee_currency | TEXT | NOT NULL |
| is_partial | INTEGER | CHECK 0 OR 1 |
| fill_ts | TEXT | ISO-8601 UTC |
| recorded_at | TEXT | ISO-8601 UTC |

Indexes:
- `uq_trade_fills_exec_id` (UNIQUE на exec_id) — idempotency на at-least-once WS delivery
- `idx_trade_fills_parent_ts` (parent_trade_id, fill_ts) — `load_by_trade` ORDER BY fill_ts ASC query plan

## Инварианты (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | Decimal precision preserved (no float conversion) | `str(Decimal)` write + `Decimal(str)` read | `tests/unit/test_fill_history.py::test_decimal_roundtrip` |
| 2 | Idempotent на exec_id (at-least-once WS delivery) | `INSERT OR IGNORE` + UNIQUE INDEX | `tests/unit/test_fill_history.py::test_insert_idempotent_on_duplicate_exec_id` |
| 3 | FK к trade_history.trade_id enforced (PRAGMA foreign_keys ON) | DDL FOREIGN KEY constraint + INSERT violation test | `tests/unit/test_db_migration_trade_fills.py::test_migration_0006_fk_enforced_at_insert` |
| 4 | fill_qty > 0 (pydantic Field constraint) | `fill_qty: Decimal = Field(..., gt=0)` | `tests/unit/test_fill_history.py::test_negative_qty_rejected_at_model` |
| 5 | AwareDatetime UTC roundtrip preserves timezone | `.isoformat()` write + `.fromisoformat().astimezone(UTC)` read | `tests/unit/test_fill_history.py::test_decimal_roundtrip` (implicit) |
| 6 | `is_partial` boolean roundtrip (1/0 ↔ True/False) | explicit cast в insert/_row_to_record | `tests/unit/test_fill_history.py::test_is_partial_flag_roundtrip` |

## Data flow

```
Bybit V5 WS execution topic
    ↓
BybitPrivateWSConsumer._on_execution_raw(msg)  [src/execution/bybit/ws_private.py]
    ↓ for each item in msg["data"]
fill_recorder.on_fill_event(evt)  [_FillRecorderProto]
    ↓ (recorder maps execId/execQty/execPrice → FillRecord)
FillHistoryRepository.insert_fill(record)  [src/risk/fill_history.py]
    ↓
SQLite trade_fills table (UNIQUE exec_id idempotency)
```

## Production wiring status

**PENDING.** `src/__main__.py::_cmd_run` is STUB since S8a (deferred к T20 integration test never completed). When operator-readiness sprint wires production runtime, must:

1. Construct `FillHistoryRepository(conn)` after `init_db`
2. Build adapter that maps Bybit V5 execution dict к `FillRecord` (parse execTime → AwareDatetime, Decimal cast for execQty/execPrice/execFee)
3. Inject adapter as `fill_recorder` kwarg к `BybitPrivateWSConsumer(...)`

Until then, WS execution events fire against `MagicMock` в tests only — no production persistence.

## Bybit V5 execution event schema

Per [Bybit V5 docs](https://bybit-exchange.github.io/docs/v5/websocket/private/execution):

| Field | Type | Notes |
|-------|------|-------|
| execId | str | Unique fill id (→ FillRecord.exec_id) |
| orderId | str | Parent order id |
| symbol | str | "BTCUSDT" |
| execQty | str | Decimal str (→ Decimal cast) |
| execPrice | str | Decimal str |
| execFee | str | Decimal str |
| feeCurrency | str | "USDT" / "BTC" / etc. |
| execType | str | "Trade" / "BustTrade" / "Funding" / etc. |
| isMaker | bool | True/False |
| execTime | str | Unix ms epoch (→ AwareDatetime) |

## Referenced by

- [[trade-history]] — parent table; FillRecord.parent_trade_id FK
- [[ws-private-consumer]] — source of execution events (now subscribes 3 topics: order + wallet + execution)
- [[dsr]] — future analytics consumer (DSR currently per-trade, may consume per-fill в S10+ if granularity needed)

## Связанные

- [[../decisions/0021-sprint-7-resilience]] — execution topic deferral source (S7→S9)
- [[../decisions/0022-sprint-8a-live-runtime]] — analytics+per-fill deferred again в S8b→S9
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — S9 aggregate ADR
- [[../sprints/sprint-09-data-quality-types-analytics]] — sprint where fill-history was created
- [[fill-recorder-adapter]] — S12 adapter that bridges WS execution events → FillHistoryRepository
- [[../architecture/storage]] — SQLite schema для `fills` таблицы.

## Sources

- `src/risk/fill_history.py` — FillRecord + FillHistoryRepository
- `migrations/0006_trade_fills.sql` — DDL
- `src/execution/bybit/ws_private.py::_FillRecorderProto` — Protocol contract
- `src/execution/bybit/ws_private.py::BybitPrivateWSConsumer._on_execution_raw` — WS topic handler
- `tests/unit/test_fill_history.py` (7 tests)
- `tests/unit/test_db_migration_trade_fills.py` (3 tests incl. FK enforcement)
- `tests/unit/test_ws_private_consumer.py::test_execution_event_*` (3 tests)
