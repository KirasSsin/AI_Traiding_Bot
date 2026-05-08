---
name: S37 brainstorm decisions
description: Round 1 verdicts for Q1-Q4 (carry-overs sprint ordering, scope, TESTNET activation timing, operator playbook)
type: project
---

# S37 brainstorm — Round 1 verdicts

**Date:** 2026-04-27

## Q1 — v0.7+ ordering primary
**CONFIRM** (c) S37 carry-overs sprint first, δ activate in S38 (same session as S37 ship per Q3).
- Item #2 (symbol fail-closed) = silent HaltGate bypass risk confirmed in code (manager.py:175-178: getattr → warn → return False)
- 1 trade sample at 13/year cost is dominated by known silent-bypass-on-money-path risk
- Key evidence: _check_halt_gate() returns False (not halt) when symbol is None

## Q2 — S37 carry-overs scope
**EXPAND** — 6-item critical subset confirmed but with amendment: item #2 requires new dedicated ReasonCode HALT_UNKNOWN_SYMBOL (NOT reuse HALT_S36_CONSECUTIVE_LOSSES — that violates γ halt persistence root-cause attribution).
- enum: 49→50
- ADR 0055 SD-4 table must be updated with symbol-mismatch → HALT_UNKNOWN_SYMBOL mapping
- Item #3 HMAC effort underestimated: ~3h not 30min (state_repo.set/get path + SECRET KEY source + new setting)
- Task ordering recommended: #2 (fail-closed) → #5 (public property, same file) → #4 (clock injection) — minimize merge conflicts
- Items #6, #7, #9, #10 deferred to S38+

## Q3 — TESTNET activation timing post-S37
**CONFIRM** immediately post-S37 ship. No calendar hold.
- S37 closes all silent-bypass risks
- CI gate (GitHub Actions) catches CI-detectable regressions before merge
- Architecture Demeter violation (#7) is code quality, not runtime safety — does not block δ

## Q4 — Operator playbook documentation
**CONFIRM** YES — dedicated delta-activation-playbook.md.
- Must be written AFTER code tasks complete (references HALT_UNKNOWN_SYMBOL, HMAC signature, startup banner)
- Must include: how to verify activation_ts persisted in SQLite, halt_log HMAC check, startup symbol banner verification, grep pattern for HaltGate active confirmation
- Path: wiki/project/components/delta-activation-playbook.md

## Cross-cutting concerns
- CC1: ReasonCode 49→50 triggers wiki sync cascade (current-state.md + index.md + ADR 0055 SD-4 + sprint-37 page)
- CC2: Item #3 HMAC — read src/risk/state_repo.py before estimating (SECRET KEY source not documented in backlog)
- CC3: Items #4+#5+#2 are all in manager.py:175-178 — do as one task sequence to minimize conflicts

## ESC to user
- ESC-1: MAINNET promotion criteria — should S37 produce ADR 0057 locking n≥50 + Sharpe/DSR floors, or defer criteria-locking to S38 when live data available? Product decision.

## Recommended S37 scope (6 items + 1 expanded):
| Task | Items | Est | δ gate? |
|------|-------|-----|---------|
| T1 | Symbol whitelist + startup banner (#1) | 2h | YES |
| T2 | Symbol fail-closed + HALT_UNKNOWN_SYMBOL enum (#2) | 2h | YES |
| T3 | activation_ts HMAC hardening (#3) | 3h | Pre-MAINNET |
| T4 | coordinator.symbol public + clock injection (#4+#5) | 2h | NO |
| T5 | DSR boundary tests (#8) | 1h | NO |
| T6 | Wiki sync + δ-activation-playbook + canonical counts | 1h | pre-ship |
| Total | | ~11h | |

## Why/How to apply
- Item #2 is the most dangerous item because it makes operator BELIEVE halt gate is active when it is not
- HALT_UNKNOWN_SYMBOL is a new dedicated ReasonCode — do not reuse existing codes
- Playbook written last (after code tasks) to reflect actual post-S37 behavior
