---
name: S38 brainstorm decisions
description: Round 1 verdicts for Q1-Q4 (δ TESTNET activation, monitoring cadence, S38 scope, pre-activation gating)
type: project
---

# S38 Brainstorm — Round 1 Verdicts

**Date:** 2026-04-27
**Context:** Post-S37 ship (tag v0.1.0-alpha.37). All 6 critical carry-overs closed. δ TESTNET production-ready. ROUND 5 binding: δ activate in S38.

## Q1 — δ activate timing
**CONFIRM** (a) δ activate now.
- ROUND 5 pre-commitment #4 binding: "δ activate immediately post-S37 ship, no observation gap"
- All 6 security HIGH closed (S37 SPRINT_STATE confirmed)
- Demeter refactor (#7) does not touch _tick() / HaltGate.evaluate() — not a blocker
- HMAC key rotation false-positive risk is operator-controlled (playbook checklist items 8-9)

## Q2 — Monitoring cadence
**REVISE** (a) weekly + mandatory T+4h first-tick gate.
- Weekly steady-state is correct for 4H strategy (1 trade per 28 days)
- First-tick production run (HaltGate + HMAC + EquityTracker path) needs 24h heightened gate
- Amendment: check halt_log at T+4h (after first 4H bar cycle completes), then weekly
- Playbook Step 5 should be upgraded from advisory to operator pre-commitment

## Q3 — S38 sprint scope
**CONFIRM** (b) Item #7 Demeter refactor + Items #6/#9 documentation.
- Item #7 scope MUST be DI wiring only — zero changes to _tick() body or HaltGate.evaluate()
- Item #10 (extended scenarios) deferred until δ produces real edge cases
- Architecture-reviewer should verify scope boundary before Item #7 coding

## Q4 — Pre-activation gating
**CONFIRM** (a) Playbook checklist (9 items).
- Settings validators catch most misconfigurations at construction (HMAC key < 32 chars = ValueError)
- ADR 0052 operator acknowledgment = MAINNET only, not TESTNET
- Gap identified: add item 10 to checklist — verify no stale activation_ts row in state table from prior aborted activation (stale row with different HMAC key → tamper halt on first tick)

## Critical cross-cutting concerns

### CC1 — HMAC tamper halt ReasonCode ambiguity (HIGH)
Playbook halt response table lists HALT_UNKNOWN_SYMBOL for "activation_ts tampered" but
HMAC tamper raises ValueError from state_repo.get_signed(). If RuntimeManager doesn't
explicitly catch this ValueError → unhandled crash, no halt_log entry, operator has no
SQLite evidence. Must verify manager.py tamper handling path in S38 T1.

### CC2 — Stale activation_ts risk (MEDIUM)
If prior aborted activation attempt left a signed activation_ts row in state table with
a different HMAC key version → tamper halt on first tick of new activation. Add to
playbook checklist: "verify no stale runtime:halt_gate:activation_ts in state table."

## Recommended S38 task order
| Task | Content | Priority |
|------|---------|----------|
| T0 | Operator δ activation (env var + 5 steps + T+4h check) | P0 operator action |
| T1 | Verify HMAC tamper → halt path in manager.py (CC1 fix) | HIGH code |
| T2 | Item #6 months_since documentation | LOW |
| T3 | Item #7 RiskSharedDeps Demeter refactor (DI only) | MEDIUM |
| T4 | Item #9 Sharpe semantics ADR doc | LOW |
| T5 | Playbook amendments (T+4h gate + stale activation_ts item) | LOW |
| T6 | Wiki sync | post-sprint |

## Why/How to apply
- CC1 is the only new production safety risk discovered in brainstorm — verify manager.py before S38 T3+
- Q2 REVISE is same option (a) amended — no ROUND 2 needed (not a different option)
- 12mo MAINNET-promotion clock starts at activation_ts write (day-1 of δ operation)
