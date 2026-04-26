---
name: FillRecorder adapter pattern S12
description: S12 T1 2-layer pattern, schema gap, UNIQUE INDEX idempotency, WAL concurrent access
type: project
---

FillRecorderAdapter (src/risk/fill_recorder_adapter.py) — S12 T1. 2-layer pattern:
1. Always-on structlog audit (Layer 1)
2. Best-effort DB insert via lookup chain (Layer 2 — currently always-skips due to schema gap)

Schema gap: execution_state has no entry_signal_id column (confirmed migrations 0003+0004+0005). Adapter always reaches the `entry_signal_id = getattr(state_row, "entry_signal_id", None)` branch → None → skip. DB insert is permanently skipped in S12. Deferred to S13+ (needs migration, violates Q7 zero-migration constraint).

UNIQUE INDEX on exec_id: `uq_trade_fills_exec_id ON trade_fills(exec_id)` — migration 0006. INSERT OR IGNORE pattern in FillHistoryRepository.insert_fill. Duplicate delivery → IGNORE + fetch existing fill_id. Idempotent.

Decimal precision: all monetary fields stored as str(Decimal) TEXT. `_build_fill_record` converts via `Decimal(str(evt[field]))` — correct double-conversion. Scientific notation edge case: `Decimal(str("1e-7"))` → `Decimal("1E-7")` which is valid Decimal, but str() of it normalizes differently. Not a precision bug — arithmetic correct. Just a display concern.

WAL concurrent access: FillHistoryRepository uses `with self._conn:` (BEGIN IMMEDIATE transaction). _cmd_monitor uses `?mode=ro` URI (read-only connection). WAL allows concurrent readers + one writer — no contention issue.

find_by_order_id LIMIT 1 determinism: execution_state has symbol as PRIMARY KEY (one row per symbol). ORDER IDs are session-unique in practice, but no ORDER BY in LIMIT 1 query. For a single-symbol bot (BTCUSDT), at most one row exists → no non-determinism in practice.

**Why:** ADR 0027 Q5 REVISE-additive verdict. FillRecord.parent_trade_id Field(gt=0) required non-nullable — adapter cannot insert without resolved trade_id.

**How to apply:** S13 schema fix needs migration adding entry_signal_id to execution_state OR bracket_id↔signal_id junction table. Only then does Layer 2 become active.
