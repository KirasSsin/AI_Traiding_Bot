---
name: FSM canonical counts baseline
description: Reference counts for ExecutionState/ExecutionEvent/TRANSITIONS/ReasonCode after each sprint
type: project
---

**Baseline as of S8c (tag v0.1.0-alpha.8c):**
- FSM states: **16** (ExecutionState enum, state_machine.py)
- FSM events: **30** (ExecutionEvent enum, state_machine.py)
- FSM transitions: **74** (TRANSITIONS dict, state_machine.py; S8b T7 added (FLAT,RISK_HALT))
- Reason codes: **45** (ReasonCode enum, reason_codes.py; includes S9 Q1 HALT_DATA_QUALITY)

Verify command:
```
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```
Expected: `states=16, events=30, transitions=74, reason_codes=45`

**Why:** canonical-counts check is a HARD-GATE in sprint-finish skill. Any diff that changes these without ADR is a blocker.

**How to apply:** run the verify command after any src/execution/ or src/risk/ change. Compare to expected. If delta, check current-state.md and log.md for authoritative update.
