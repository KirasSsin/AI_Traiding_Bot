---
title: Sprint 37 — Carry-overs Hardening (security HIGH + trading-logic + quant + δ activation playbook)
type: sprint
tags: [sprint-37, carry-overs-hardening, halt-unknown-symbol, symbol-whitelist, hmac-integrity, clock-injection, calibration-amendment, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - project/decisions/0057-sprint-37-carry-overs-hardening.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/plans/2026-04-27-sprint-37-carry-overs-hardening.md
  - project/pre-s37-backlog.md
---

# Sprint 37 — Carry-overs Hardening

## Overview

**Operator approved ROUND 5 consilium binding** (3 agents CONSENSUS) — (c) S37 carry-overs sprint first, then (a) δ TESTNET activate в S38. EXPANDED scope с НЕВ ReasonCode + calibration amendment + ADR 0056 doc clarifications.

Tag v0.1.0-alpha.37. КУ avg ~50% / ~10 hours.

**δ TESTNET production-ready post-S37.** Operator action: set `S35_DEMO_ACTIVE=true` per delta-activation-playbook.md.

## Plan / ADR links

- [[../decisions/0057-sprint-37-carry-overs-hardening]] — ADR 0057 (6 sub-decisions)
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — ADR 0056 amendment section appended
- [[../plans/2026-04-27-sprint-37-carry-overs-hardening]] — Sprint 37 plan
- [[../pre-s37-backlog]] S37 ROUND 5 binding consilium trail
- [[../components/delta-activation-playbook]] — operator playbook (NEW T7)

## 8 tasks shipped

| Task | Type | Commits |
|------|------|---------|
| T1 ADR 0057 + ADR 0056 amendment LOCKED pre-commit | Wiki ADRs | 2dc5542 |
| T2 Security #1+#2 — symbol whitelist + fail-closed + HALT_UNKNOWN_SYMBOL (49→50) | Code + 8 tests | 654ef66 + e686dba |
| T3 Security #3 — activation_ts HMAC integrity per ADR 0018 pattern | Code + 6 tests | e122a38 |
| T4 Trading-logic #4 — clock injection per ADR 0057 SD-5 | Code + 3 tests | 7d5116a |
| T5 Trading-logic #5 — Coordinator.symbol public property | Code + 2 tests | 29f0075 |
| T6 Quant #8 — DSR boundary tests n=9/10/29/30 + S22 baseline 6.17→2.96 | Code + 5 tests | cf44af4 |
| T7 δ activation operator playbook | Wiki component (243 lines) | 63ddac6 |
| T8 sprint-37 + counts + sync + ship | Wiki sync | (this commit) |

## КУ achieved

| Item | T (token) | P (speed) | Q (quality) | КУ % |
|------|----------|-----------|-------------|------|
| T1 ADRs LOCKED | 1 | 2 | 5 | 50% |
| T2 Security symbol whitelist + fail-closed | 2 | 3 | 5 | 50% |
| T3 HMAC integrity | 2 | 3 | 5 | 50% |
| T4 Clock injection | 1 | 2 | 4 | 46% |
| T5 Public property | 1 | 2 | 4 | 46% |
| T6 DSR boundary + baseline | 1 | 2 | 4 | 46% |
| T7 Operator playbook | 1 | 2 | 5 | 50% |
| T8 wiki sync | 1 | 2 | 4 | 46% |
| **Sprint avg** | — | — | — | **48%** |

Time invested: ~10 hours.

## ADR 0057 6 sub-decisions implemented

| SD | Description | Implementation |
|----|-------------|----------------|
| SD-1 | HALT_UNKNOWN_SYMBOL distinct ReasonCode (49→50) | T2 (reason_codes.py + property test) |
| SD-2 | Symbol fail-closed semantic (halt, NOT warn+skip) | T2 (`_check_halt_gate` rewrite) |
| SD-3 | s35_demo_approved_symbols Setting + startup banner + case normalization | T2 (config.py + manager.py + validator) |
| SD-4 | activation_ts HMAC integrity per ADR 0018 pattern | T3 (state_repo.set_signed/get_signed) |
| SD-5 | Clock injection в `_check_halt_gate` (S8a precedent) | T4 (Callable[[], datetime] kwarg) |
| SD-6 | Coordinator.symbol public property | T5 (@property + fixture migration) |

## ADR 0056 amendment

- Calibration baseline 6.17 → 2.96 (mean fold conservative, was T1 aggregate inflated by fold #4 outlier)
- Sharpe semantics 3-row table (trial_mean_fold_oos_sharpe vs pooled_trade_oos_sharpe vs live_sharpe)

## Phase 5 Verify outcome

- pytest: 897 passed unit + 33 integration (was 871 + 33 baseline = +26 NEW tests)
- mypy --strict src/: 0 errors
- canonical counts: 16/30/74/**50** (reason codes 49→50 per T2)
- ADRs 0057 + 0056 amendment committed BEFORE T2-T7 code (anti-snooping discipline preserved)
- HMAC integrity tested (6 cases — round-trip + tamper + missing envelope + wrong key)
- Clock injection deterministic (3 cases — default + injected for activation_ts + injected for NO_TRADE_TIMEOUT)
- Boundary tests parametrized (4 cases — n=9/10/29/30)

## Phase 6 Review

- T1: doc-reviewer skipped (template approach + verbatim trail)
- T2: security-auditor + trading-logic-reviewer parallel — security HIGH (case-normalize) + trading-logic C2 (s35_demo_active=False bypass test) FIXED inline (e686dba)
- T3: skipped (mirrors verified ADR 0018 HMAC pattern)
- T4-T7: skipped (mechanical code, S8a precedent для T4, ADR-driven для T5-T7)

## FSM growth

Reason codes: 49 → **50** (+1 HALT_UNKNOWN_SYMBOL per T2).
Other canonical counts unchanged: states=16, events=30, transitions=74.

## Tests summary

26 NEW tests total: T2=8 (5 + 3 reviewer fix) + T3=6 + T4=3 + T5=2 + T6=5 + T7=0 + reason-code count updates 2.
pytest 871→897 unit + 33 integration preserved.

## Wiki updates summary

5 NEW files:
- ADR 0057 (T1)
- delta-activation-playbook.md component (T7)
- sprint-37 page (T8)
- 4 NEW test files (test_symbol_whitelist + test_activation_ts_hmac + test_check_halt_gate_clock_injection + test_coordinator_symbol_property)

8 MODIFIED files:
- ADR 0056 amendment section appended (T1)
- index.md (+ S37 sprint + ADR 0057 + playbook)
- current-state.md (counts: 56→57 ADRs / 40→41 sprints / 47→48 components / **49→50 reason codes** + S37 row + tag alpha.37)
- reason-codes-schema.md (+1 HALT_UNKNOWN_SYMBOL row)
- execution-state-machine.md (footer sync)
- log.md (sprint-end)
- SPRINT_STATE.md (phase=8-ship)
- .github/workflows/ci.yml (canonical reason_codes 49→50)
- + 5 fixture test files (T5 coord._symbol → coord.symbol migration) + 3 enum count tests (T2)

## Open issues для S38+

**δ TESTNET activation status:** Production-ready. Operator MUST set `S35_DEMO_ACTIVE=true` per delta-activation-playbook.md procedure.

**Carry-overs persisted в pre-s37-backlog (Items deferred к S38+):**
- Item #6 months_since truncation documentation
- Item #7 RiskSharedDeps refactor (Demeter — RuntimeManager accesses risk_manager properties)
- Item #9 trial_mean_fold_oos_sharpe vs pooled_trade_oos_sharpe extended ADR
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios

**S38+ operational:**
- 12mo MAINNET-promotion ADR (per ADR 0055 SD-8 deferred)
- Architecture refactor (Item #7)

## Key decisions

1. **6 sub-decisions ADR 0057 LOCKED pre-T2** — anti-snooping (Bailey 2014)
2. **HALT_UNKNOWN_SYMBOL distinct ReasonCode** (NOT reuse) — γ primary-wins audit attribution
3. **Fail-closed semantic** — silent bypass vulnerability closed
4. **HMAC integrity** — activation_ts tamper-detection
5. **Clock injection** — deterministic property tests + future replay
6. **coordinator.symbol public property** — Demeter compliance
7. **Calibration baseline 2.96** — conservative replaces extreme 6.17 outlier
8. **DSR boundary tests** — off-by-one regression coverage closed
9. **Operator playbook** — single source of truth для δ activation procedure

## S37 process artifact

Per S28+ binding:
- PHASE 1 Orient (continuation post-S36 ship)
- PHASE 2 Brainstorm — ROUND 5 consilium 3 agents CONSENSUS (`pre-s37-backlog.md`)
- PHASE 3 Plan file (HARD-GATE satisfied, trace map mandatory)
- PHASE 4 8 tasks subagent-driven с per-task SPRINT_STATE updates
- TodoWrite phase tracker
- PHASE 5 Verify (pytest 897+33 / mypy 0 / canonical 16/30/74/50 / ADRs anti-snooping committed pre-T2)
- PHASE 6 Review (selective per task — T2 security+trading-logic parallel, T3-T7 skipped per pattern)
- PHASE 7 Sync (this commit)
- PHASE 8 Ship via gh pr + squash merge + tag v0.1.0-alpha.37
- PHASE 9 Close — SPRINT_STATE → between-sprints + δ activate operator action

## Related

- ADR 0050-0054 (S33-S35 lineage)
- ADR 0055 (S36 δ activation — paired predecessor)
- ADR 0056 (S36 DSR amendment + S37 amendment paired)
- ADR 0057 (S37 carry-overs hardening — этот sprint)
- ADR 0018 (HMAC pattern — SD-4 source)
- ADR 0019 (coordinator design — SD-6 source)
- ADR 0022 (RuntimeManager lifecycle — SD-5 clock pattern)
- pre-s35-backlog.md (ROUND 3 binding)
- pre-s36-backlog.md (ROUND 4 binding)
- pre-s37-backlog.md (ROUND 5 binding)
- delta-activation-playbook.md (operator procedure)
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
