---
name: S37 consilium votes and HALT_UNKNOWN_SYMBOL decision
description: ROUND 5 S37 ordering/scope/timing votes + new ReasonCode semantic rationale + symbol fail-closed pattern
type: project
---

S37 ROUND 5 consilium (2026-04-27). Key decisions:

**Q1 (c) confirmed:** carry-overs sprint first, δ activate post-S37.
**Why:** `_check_halt_gate()` symbol bypass (manager.py:175-178) makes HaltGate silently inert on misconfiguration. Activating δ before fix invalidates 12mo operational evidence.

**HALT_UNKNOWN_SYMBOL new ReasonCode (49→50):**
- Do NOT reuse HALT_S36_CONSECUTIVE_LOSSES — semantic corruption in halt_reason audit log (γ halt persistence primary-wins = irreversible).
- Maps to ExecutionEvent.RISK_HALT via existing else-branch in coordinator.request_halt:634. No new FSM event, no TRANSITIONS change.
- Must be added to `_REQUEST_HALT_CODES` frozenset in tests/property/test_request_halt_mapping.py per ADR 0023.

**Symbol public property first:** Coordinator._symbol accessed via getattr in 3 places (manager.py:175, 279, 342). Must add `Coordinator.symbol: str` property BEFORE writing tests for fail-closed behavior. Hard sequencing: T1 (property) → T2 (fail-closed) → T3 (whitelist).

**months_since truncation is conservative (correct direction):** `days // 30` means 29 days = 0 months. Under-fires the timeout gate. Safe for a safety gate. Document in ADR 0055 amendment — operator must understand 180+ days = 6-month setting.

**δ activation timing:** separate operator session AFTER S37 CI + reviewer sign-off. Not bundled in S37 Phase 4.

**S37 T2 review result (654ef66, 2026-04-27):** CONFIRMED — no blockers.
- FSM dispatch: HALT_UNKNOWN_SYMBOL → RISK_HALT → HALTED (else-branch coordinator.py:634). Property test GREEN (9/9).
- Tick ordering correct: s35_demo_active=False early-return (line 172) fires BEFORE whitelist check (line 179). Whitelist never runs when demo inactive.
- _stopping=True set immediately after request_halt (line 186) — bot exits cleanly.
- activation_ts persistence skipped on whitelist fail (correct — no side-effects on misconfigured boot).
- Audit attribution: distinct enum value HALT_UNKNOWN_SYMBOL (not reused HALT_S36_*). halt_log post-mortem trail preserved.
- Open concerns (S38+): (1) private _symbol getattr still in place — T5 must add Coordinator.symbol public property; (2) no test for s35_demo_active=False skipping whitelist (gap but not blocker); (3) logger.error logs whitelist list contents (not a path-leak but may expose symbol config in structured logs).
- ReasonCode count: 49→50 confirmed, all three count-assert tests GREEN (83/83).

**How to apply:** In future reviews touching _check_halt_gate or HaltGate-related code — verify (1) fail-closed on unknown symbol, (2) public property not private getattr (T5 pending), (3) clock injectable, (4) HALT_UNKNOWN_SYMBOL in allow-list.
