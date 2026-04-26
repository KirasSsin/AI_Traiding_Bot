---
name: Halt persistence pattern
description: ADR 0021 sub-decisions 4+5 — write-ahead invariant, primary-wins semantics, halt_log schema
type: project
---

halt_log INSERT MUST happen BEFORE execution_state.halt_reason UPDATE inside same `with self._conn:` block. Reversing order = audit gap on crash (write-ahead invariant).

**Actual code in state_repo.py:** UPDATE fires first (lines 137-140), then INSERT halt_log (lines 142-145). This is an existing pre-S12 inversion — flagged but pre-existing, not introduced by S12 T1.

halt_reason UPDATE is conditional: `WHERE halt_reason IS NULL` — first non-null sticks (primary-wins). Unconditional UPDATE = root-cause loss regression.

halt_log schema (migration 0005): `(id INTEGER PK AUTOINCREMENT, symbol TEXT NOT NULL, ts TEXT NOT NULL, reason TEXT NOT NULL, context_json TEXT NOT NULL)`. Column named `ts`, NOT `occurred_at`. Column named `context_json`, NOT `payload_json`.

**Why:** ADR 0021 sub-decision 5. halt_log is append-only audit trail. If process crashes between UPDATE and INSERT, the audit entry is lost.

**How to apply:** Any new code writing to halt_log must INSERT before UPDATE. The existing pre-S12 inversion in _set_halt is a carry-over concern, not a regression.
