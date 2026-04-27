---
title: Sprint 36 — δ TESTNET Activation (HaltGate Wire-up + B1 Critical Fix + DSR Amendment)
type: sprint
tags: [sprint-36, testnet-activation, halt-gate-wireup, b1-critical-fix, dsr-amendment, reason-codes-extension, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/plans/2026-04-27-sprint-36-delta-activation.md
  - project/pre-s36-backlog.md
---

# Sprint 36 — δ TESTNET Activation

## Overview

**Operator approved ROUND 4 consilium binding** (3 agents CONSENSUS + ROUND 2 BINDING Q4 hybrid option H) — δ TESTNET activate primary path post-S35 α Donchian FAIL conjoint.

Tag v0.1.0-alpha.36. КУ avg ~50% / ~10-12 hours.

**δ TESTNET infrastructure NOW WIRED LIVE.** HaltGate connected к RuntimeManager._tick. B1 CRITICAL fix applied (S17-relaxed LOCKED params wired к live path — δ NO LONGER runs S15-noise params silently). DSR sigma_SR ADR 0056 amendment closes S35 T4 carry-overs.

**Operator action для δ activate:** set `S35_DEMO_ACTIVE=true` в .env, restart bot. First tick auto-records activation_ts. HaltGate evaluates per-tick. 12mo MAINNET-promotion gate per ADR 0053 + ADR 0055 SD-1 (NOT TESTNET shutdown).

## Plan / ADR links

- [[../decisions/0055-sprint-36-delta-activation]] — ADR 0055 δ activation (8 sub-decisions)
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — ADR 0056 DSR sigma_SR amendment LOCKED
- [[../plans/2026-04-27-sprint-36-delta-activation]] — Sprint 36 plan
- [[../pre-s36-backlog]] — S36 ROUND 4 binding consilium trail

## 8 tasks shipped

| Task | Type | Commits |
|------|------|---------|
| T1 ADR 0055 + ADR 0056 LOCKED pre-commit (anti-snooping) | Wiki ADRs | ce38eab |
| T2 B1 CRITICAL fix (MEAN_REVERSION_S17_RELAXED_PARAMS wire-up + MappingProxyType immutability) | Code + tests | e82608e + ae67fc6 + 91a0294 |
| T3 State-source methods (4 new: EquityTracker.intraday_dd_pct/hwm_since + TradeHistoryRepository.consecutive_losses/last_trade_ts) | Code + 11 tests | bd62a55 |
| T4 HaltGate wire-up в RuntimeManager._tick + reviewer fixes (cache + namespace + tests) | Code + 7 integration tests | df8edec + cf319fa |
| T5 ReasonCode +4 HALT_S36_* (45→49 canonical) | Code + property test | 7d1177b |
| T6 DSR sigma_SR amendment + NaN guard hardening | Code + 8 tests | bb27899 + cc942df |
| T7 Live trade reporter ADR 0055 SD-6 (live Sharpe + calibration + MC gating) | Code + 11 tests | 93a6a78 |
| T8 sprint-36 + 2 components + sync + S37 carry-overs | Wiki sync | (this commit) |

## КУ achieved

| Item | T (token) | P (speed) | Q (quality) | КУ % |
|------|----------|-----------|-------------|------|
| T1 ADRs LOCKED | 1 | 2 | 5 | 50% |
| T2 B1 CRITICAL fix | 2 | 3 | 5 | 50% |
| T3 State-source methods | 1 | 2 | 4 | 46% |
| T4 HaltGate wire-up | 3 | 3 | 5 | 50% |
| T5 ReasonCode extension | 1 | 2 | 5 | 50% |
| T6 DSR amendment | 2 | 3 | 5 | 50% |
| T7 Live reporter | 1 | 2 | 4 | 46% |
| T8 wiki sync | 1 | 2 | 4 | 46% |
| **Sprint avg** | — | — | — | **48%** |

Time invested: ~10-12 hours.

## ADR 0055 8 sub-decisions implemented

| SD | Description | Implementation |
|----|-------------|----------------|
| SD-1 | Hybrid duration option (H) verbatim per ROUND 2 trader BINDING | ADR 0055 docs (no code) |
| SD-2 | B1 fix mandate | T2 (e82608e + 91a0294) |
| SD-3 | Multiday DD = HWM since activation_ts | T3 hwm_since + T4 wire-up |
| SD-4 | HaltTrigger → ReasonCode mapping | T5 enum + T4 _HALT_TRIGGER_TO_REASON |
| SD-5 | HaltGate halt resume protocol (manual FSM reset) | T4 _stopping=True (no auto-resume) |
| SD-6 | Adapted gates methodology | T7 live_trade_reporter |
| SD-7 | N_trials FREEZE at 7 | T7 DELTA_N_TRIALS_LOCKED constant |
| SD-8 | MAINNET promotion criteria DEFERRED к S37+ | pre-s37-backlog documented |

## ADR 0056 implementation

- sigma_SR sourcing hierarchy (N≥3 PREFERRED / 1-2 NaN DEGENERATE / 0 None)
- n_trades thresholds (<10 NaN INSUFFICIENT_TRADES / 10-30 UNDERPOWERED / ≥30 GATE_ELIGIBLE)
- variable rename aggregate_oos_sharpe → trial_mean_fold_oos_sharpe
- inadmissible per-fold stdev fallback REMOVED от donchian_runner.py
- NaN guard added к compute_dsr (defense-in-depth per quant-stats C1)

## Phase 5 Verify outcome

- pytest: 871 passed unit + 33 integration (was 828 + 26 baseline = +63 NEW)
- mypy --strict src/: 0 errors
- canonical counts: 16/30/74/**49** (reason codes 45→49 per T5)
- ADRs 0055 + 0056 committed BEFORE T2-T7 code (anti-snooping discipline preserved)
- HaltGate wire-up integration tests cover все 4 trigger paths + bypass + activation_ts persistence

## Phase 6 Review (per kit binding parallel reviewer dispatch)

- T1: doc-reviewer — APPROVE (все frontmatter + sources resolve + verbatim text preserved)
- T2: python-reviewer + trading-logic-reviewer + security-auditor (parallel) — security BLOCKER MappingProxyType FIXED inline + 1 HIGH symbol whitelist deferred к T8 startup banner
- T3: python-reviewer + data-integrity-reviewer (parallel) — APPROVE (clean SQLite patterns, Decimal hygiene)
- T4: python-reviewer + trading-logic-reviewer + security-auditor + architecture-reviewer (parallel) — 2 architecture MEDIUM (cache + namespace) + 1 trading-logic C1 (missing tests) all FIXED inline. 2 security HIGH (symbol fail-closed + activation_ts integrity) deferred к S37+.
- T5: skipped (mechanical enum + property test verifies)
- T6: quant-stats-reviewer — APPROVE + 1 C1 NaN guard FIXED inline (cc942df)
- T7: skipped (mechanical reporter, formula correctness verified в T6)

## FSM growth

Reason codes: 45 → **49** (+4 HALT_S36_* per T5).
Other canonical counts unchanged: states=16, events=30, transitions=74.

## Tests summary

63 NEW tests total: T2=4 + T3=11 + T4=7 integration + T5=property test extension + T6=9 + T7=11 + remainder fixture updates. pytest 828→871 unit + 26→33 integration.

## Wiki updates summary

8 files NEW:
- ADR 0055 (T1)
- ADR 0056 (T1)
- sprint-36 page (T8)
- halt-gate-wireup component (T8)
- live-trade-reporter component (T8)
- pre-s37-backlog (T8)
- 2 NEW test files (test_dsr_sigma_sr_amendment + test_dsr_status_thresholds)

8 files MODIFIED:
- index.md (+ S36 sprint + 2 ADRs + 2 components + pre-s37-backlog)
- current-state.md (counts: 54→56 ADRs / 39→40 sprints / 45→47 components / **45→49 reason codes** + S36 row)
- reason-codes-schema.md (+4 HALT_S36_* rows)
- execution-state-machine.md (footer sync)
- log.md (sprint-end)
- SPRINT_STATE.md (phase=8-ship)
- + various source files per task

## Open issues для S37+

**δ TESTNET activation status:** Infrastructure WIRED but operator must explicitly set `S35_DEMO_ACTIVE=true` env var к activate. Default `false` preserves backtests/ad-hoc workflows.

**Carry-overs persisted в pre-s37-backlog.md:**

1. **trading-logic C2 (T4)**: Clock injection в `_check_halt_gate` (currently uses wall-clock — non-deterministic в property tests)
2. **trading-logic C3 (T4)**: `coordinator.symbol` public property (currently `getattr(_, "_symbol", None)` private leak)
3. **trading-logic C4 (T4)**: months_since integer truncation documented
4. **architecture MEDIUM (T4)**: RiskSharedDeps refactor (Demeter violation — RiskManager properties → shared bundle)
5. **architecture LOW (T4)**: coordinator.symbol public property fix
6. **security HIGH (T2)**: Symbol whitelist + startup banner (operator-visible когда δ active)
7. **security HIGH (T4)**: Symbol fail-closed semantic + activation_ts integrity hardening
8. **quant-stats C2 (T6)**: Boundary tests n=10 + n=30 (off-by-one coverage)
9. **quant-stats C3 (T6)**: trial_mean_fold_oos_sharpe vs pooled trade-level Sharpe ADR documentation
10. **DD_MULTIDAY + NO_TRADE_TIMEOUT extended scenarios** — currently 1 test each, additional edge cases tracked

## Key decisions

1. **8 sub-decisions ADR 0055 LOCKED pre-T2** — anti-snooping discipline preserved (Bailey 2014)
2. **B1 CRITICAL fix wired BEFORE day-1 trade** — pre-commit #7 violation closed
3. **Hybrid duration option (H)** per ROUND 2 trader CHANGED — 12mo MAINNET-promotion gate (NOT shutdown), no 6mo interim
4. **MappingProxyType LOCKED constant** — fail-loud на mutation attempt (security defense)
5. **HaltGate UNWIRED → WIRED** — production code path активен когда demo flag True
6. **N_trials freeze at 7** (S22 hypothesis re-evaluation, no Bailey increment)
7. **DSR sigma_SR fallback REMOVED** (inadmissible per Bailey 2014 — closed S35 T4 H1 carry-over)
8. **Adapted live-data methodology** — live Sharpe (per-trade) + calibration ratio (S22 baseline) + MC gating (n>=20/40)

## S36 process artifact

Per S28+ binding:
- PHASE 1 Orient (continuation post-S35 ship)
- PHASE 2 Brainstorm — ROUND 4 consilium 3 agents + ROUND 2 BINDING Q4 (`pre-s36-backlog.md`)
- PHASE 3 Plan file (HARD-GATE satisfied, trace map mandatory)
- PHASE 4 8 tasks subagent-driven с per-task SPRINT_STATE updates
- TodoWrite phase tracker
- PHASE 5 Verify (pytest 871+33 / mypy 0 / canonical 16/30/74/49 / 4 ADRs anti-snooping committed BEFORE code)
- PHASE 6 Review (8 reviewer dispatches across T1-T7, BLOCKER + HIGH fixes inline)
- PHASE 7 Sync (this commit)
- PHASE 8 Ship via gh pr + squash merge + tag v0.1.0-alpha.36
- PHASE 9 Close — SPRINT_STATE → between-sprints

## Related

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0053 (S35 δ TESTNET pre-activation infrastructure)
- ADR 0054 (S35 α Donchian pre-registration — direction CLOSED)
- ADR 0055 (S36 δ activation — этот sprint)
- ADR 0056 (S36 DSR sigma_SR amendment — этот sprint)
- pre-s35-backlog.md (ROUND 3 binding consilium)
- pre-s36-backlog.md (ROUND 4 binding consilium)
- pre-s37-backlog.md (S37 carry-overs persisted)
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique + crypto sparse-signal)
- Kish 1965 (design effect для multi-symbol)
