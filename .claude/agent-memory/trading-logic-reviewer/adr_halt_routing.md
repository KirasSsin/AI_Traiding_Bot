---
name: ADR halt-code dispatch rules and allow-list invariants
description: How halt reason codes map to FSM events in coordinator.request_halt; ADR 0023 allow-list
type: project
---

`Coordinator.request_halt(reason)` dispatches:
- `KILL_SWITCH_REQUESTED` → `ExecutionEvent.KILL_SWITCH_REQUESTED`
- All other HALT_* codes (HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL, HALT_DATA_QUALITY, etc.) → `ExecutionEvent.RISK_HALT`

**ADR 0023 allow-list:** `tests/property/test_request_halt_mapping.py::_REQUEST_HALT_CODES` is the canonical gate. Any new HALT_* code MUST be added to that frozenset. As of S9 Q1 the set is:
- HALT_BAR_POLL_STALL, HALT_DATA_QUALITY (S9 Q1), HALT_RUNTIME_CRASH, KILL_SWITCH_REQUESTED

**Why:** property test enumerates every code → confirms FSM lands in HALTED with matching halt_reason. Missing entry = silent halt-path corruption.

**How to apply:** when reviewing changes that add new ReasonCode entries, grep `_REQUEST_HALT_CODES` and confirm new HALT_* code is present.
