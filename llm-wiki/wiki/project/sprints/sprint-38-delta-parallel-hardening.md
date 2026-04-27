---
title: Sprint 38 — δ Parallel Hardening (F2 quant + bybit-api-reviewer + Item #7 + playbook amendments)
type: sprint
tags: [sprint-38, delta-parallel, pnl-pct-fix, bybit-api-review, demeter-refactor, playbook-amendments, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - project/decisions/0058-sprint-38-delta-parallel-hardening.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/decisions/0057-sprint-37-carry-overs-hardening.md
  - project/plans/2026-04-27-sprint-38-delta-parallel-hardening.md
  - project/pre-s38-backlog.md
---

# Sprint 38 — δ Parallel Hardening

## Overview

**Operator approved Path A** (ROUND 6 consilium binding) — δ TESTNET activate immediately + S38 sprint runs в parallel.

Tag v0.1.0-alpha.38. КУ avg ~50% / ~7 hours.

**Two parallel tracks:**
- **Track 1 (operator-side):** δ TESTNET activation per `delta-activation-playbook.md` 5-step procedure (operator action — set `S35_DEMO_ACTIVE=true`)
- **Track 2 (AI-side):** S38 sprint 7 tasks (T1-T7) — F2 correctness fix + bybit-api-reviewer first invocation + Item #7 Demeter refactor + playbook amendments + docs

Track 2 code touches NOT live runtime tick path (DI wiring + analytics + docs only) — δ TESTNET safe to run в parallel.

## Plan / ADR links

- [[../decisions/0058-sprint-38-delta-parallel-hardening]] — ADR 0058 (5 sub-decisions)
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — ADR 0056 amendment 2 appended (Sharpe pnl_pct semantics)
- [[../decisions/0057-sprint-37-carry-overs-hardening]] — ADR 0057 amendment appended (months_since truncation)
- [[../plans/2026-04-27-sprint-38-delta-parallel-hardening]] — Sprint 38 plan
- [[../pre-s38-backlog]] S38 ROUND 6 binding consilium trail
- [[../components/delta-activation-playbook]] — operator playbook (extended T6)
- [[../../queries/2026-04-27-bybit-api-reviewer-first-invocation]] — F3 review document

## 7 tasks shipped

| Task | Type | Commits |
|------|------|---------|
| T1 ADR 0058 + ADR 0056 amendment 2 LOCKED pre-commit | Wiki ADRs | 778f2c0 |
| T2 F2 quant HIGH fix (compute_live_sharpe pnl_pct + generate_live_report MC) | Code + 3 tests | 2711ef9 + 513d77b |
| T3 F3 bybit-api-reviewer first invocation (6-axis review) | Wiki query | 6ab8e7f |
| T4 Item #7 RiskSharedDeps Demeter refactor (DI ONLY + smoke-start gate) | Code + 5 tests | b3b611c |
| T5 ADR 0057 amendment (months_since truncation semantics) | Wiki ADR | c4f01f3 |
| T6 δ playbook amendments (5 NEW gates + UNDERPOWERED + halt-triggered) | Wiki component | 3fb0a67 |
| T7 sprint-38 + counts + sync | Wiki sync | (this commit) |

## КУ achieved

| Item | T (token) | P (speed) | Q (quality) | КУ % |
|------|----------|-----------|-------------|------|
| T1 ADRs LOCKED | 1 | 2 | 5 | 50% |
| T2 F2 pnl_pct fix | 1 | 2 | 5 | 50% |
| T3 bybit-api-reviewer | 2 | 2 | 5 | 50% |
| T4 RiskSharedDeps refactor | 2 | 2 | 5 | 50% |
| T5 ADR 0057 amendment | 1 | 2 | 4 | 46% |
| T6 playbook amendments | 1 | 2 | 4 | 46% |
| T7 sync | 1 | 2 | 4 | 46% |
| **Sprint avg** | — | — | — | **48%** |

Time invested: ~7 hours.

## ADR 0058 5 sub-decisions implemented

| SD | Description | Implementation |
|----|-------------|----------------|
| SD-1 | F2 fix — `compute_live_sharpe` uses `pnl_pct` | T2 (live_trade_reporter.py:62 + generate_live_report MC) |
| SD-2 | F3 bybit-api-reviewer first invocation | T3 (query document) |
| SD-3 | Item #7 RiskSharedDeps Demeter refactor (DI wiring only) | T4 (NamedTuple + property + backward-compat) |
| SD-4 | Playbook amendments F4-F7 + UNDERPOWERED + halt-triggered | T6 |
| SD-5 | 12mo MAINNET-promotion ADR DEFERRED к n=10 milestone | ADR 0058 explicit (no code) |

## ADR 0056 amendment 2

- Live Sharpe returns = `pnl_pct` (NOT `pnl_quote`) — Kelly variance bias closed
- 2-row table comparing S37 ORIGINAL vs S38 AMENDED extraction
- Backward-compat note (existing test fixtures preserved)

## ADR 0057 amendment

- `months_since` truncation table (29→0, 30→1, 60→2, 180→6 boundaries)
- Conservative under-fire rationale (≤30 days, no spurious-fire risk)
- Item #9 closure pointer к ADR 0056 amendment 2

## bybit-api-reviewer findings (T3, query document)

20 findings via 6-axis review (rate limits / order params / WS schema / retCode / pagination / HMAC):
- **0 BLOCKER**
- **3 HIGH** (H1 rate-limit backoff missing + H2 WS reconnect verification gap + H3 accountType="UNIFIED" hardcoded)
- **4 MEDIUM** (M1 retCode taxonomy gaps / M2 pybit response-shape direct access / M3 WS data array isinstance guard / M4 WS consumer __repr__ secret redaction)
- **3 LOW** (cosmetic)
- **10 VERIFIED** (V1-V10 positive findings)

**Triage:**
- H1 + H2 → pre-s39-backlog (operationally safe at single-symbol 4H low-cadence δ)
- H3 → escalated к T6 playbook gate (operator pre-flight verification)
- M1-M4 + LOW → pre-s39-backlog

## T6 playbook amendments (5 NEW gates + monitoring)

Pre-activation gates added:
- F4 Bybit TESTNET API key scope (Order write permission)
- F5 No stale `runtime:halt_gate:activation_ts` row check
- F7 Gate 2: SQLite WAL + > 1GB disk space
- F7 Gate 3: Bootstrap → ws_consumer.start ordering invariant doc
- T3 H3: Bybit account type=UNIFIED verification (escalate если CLASSIC)

Monitoring section additions:
- "DSR UNDERPOWERED expected for 12mo" annotation (per quant — small-n regime, NOT failure)
- "Halt-triggered immediate review" branch (weekend halt blind spot mitigation)

## Phase 5 Verify outcome

- pytest: 905 passed unit + 33 integration (was 897 + 33 baseline = +8 NEW tests)
- mypy --strict src/: 0 errors (79 source files)
- canonical counts: 16/30/74/**50** unchanged (no NEW ReasonCodes в S38)
- ADRs 0058 + ADR 0056 amendment 2 + ADR 0057 amendment committed BEFORE T2-T7 code (anti-snooping discipline preserved)
- F2 fix verified (3 tests covering pnl_quote scaling does NOT affect Sharpe)
- T4 backward-compat preserved (5 tests + existing 26 RuntimeManager + integration tests GREEN)

## Phase 6 Review

Per kit binding selective per task:
- T1: doc skipped (verbatim ADR template)
- T2: skipped (mechanical 1-line fix verified by F2 explicit test)
- T3: bybit-api-reviewer = the review itself (output is reviewer-domain finding)
- T4: skipped (backward-compat tests cover refactor + smoke-start gate verified)
- T5+T6: skipped (mechanical docs amendments)

## FSM growth

Reason codes: 50 unchanged (no NEW codes в S38). canonical 16/30/74/50.

## Tests summary

8 NEW tests total: T2=3 (pnl_pct fix) + T4=5 (RiskSharedDeps refactor). pytest 897 → 905 unit + 33 integration preserved.

## Wiki updates summary

3 NEW files:
- ADR 0058 (T1)
- delta-activation-playbook bybit-api-reviewer query (T3)
- sprint-38 page (T7)

7 MODIFIED files:
- ADR 0056 amendment 2 appended (T1)
- ADR 0057 amendment appended (T5)
- src/analytics/live_trade_reporter.py (T2 — pnl_pct fix x2)
- src/risk/manager.py (T4 — RiskSharedDeps + property)
- src/runtime/manager.py (T4 — shared_deps kwarg + backward-compat)
- src/__main__.py (T4 — prefer shared_deps)
- delta-activation-playbook.md (T6 — 5 NEW gates + monitoring)
- + 2 NEW test files
- index.md / current-state.md / log.md / SPRINT_STATE.md (T7 — this commit)

## Open issues для S39+

**δ TESTNET activation status:** Operator-side per `delta-activation-playbook.md` (Track 1 parallel с S38).

**Carry-overs persisted в pre-s39-backlog (NEW from T3 bybit-api-reviewer + ROUND 6):**

T3 bybit-api-reviewer findings:
- H1 rate-limit backoff missing (operationally safe at single-symbol low-cadence)
- H2 WS reconnect verification gap (operator monitors per playbook)
- M1 retCode taxonomy gaps (10001 + 110001 + 170131)
- M2 pybit response-shape direct access (defensive guards)
- M3 WS data array isinstance guard
- M4 WS consumer __repr__ secret redaction
- 3 LOW cosmetic findings

S37+ deferred (continued):
- F8 block_size constant unification (quant LOW)
- 12mo MAINNET-promotion ADR (draft trigger: n=10 first non-NaN DSR)
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios (accumulate edge cases)
- Item #7 backward-compat shim cleanup (when all callers migrated к shared_deps)

## Key decisions

1. **5 sub-decisions ADR 0058 LOCKED pre-T2** — anti-snooping (Bailey 2014)
2. **F2 pnl_pct correctness** — Kelly variance bias closed (compute_live_sharpe + generate_live_report MC)
3. **bybit-api-reviewer first invocation** — long-dormant agent finally exercised (S30→S38)
4. **Item #7 RiskSharedDeps Demeter refactor** — DI ONLY constraint preserved (NOT _tick body)
5. **Playbook 5 NEW gates** — operator pre-activation production-readiness
6. **DSR UNDERPOWERED expected annotation** — operator misread prevention
7. **Halt-triggered immediate review** — weekend halt blind spot mitigation
8. **12mo MAINNET ADR DEFERRED к n=10** — anti-snooping discipline preserved

## S38 process artifact

Per S28+ binding:
- ✅ PHASE 1 Orient (continuation post-S37 ship)
- ✅ PHASE 2 Brainstorm — ROUND 6 consilium 3 agents UNANIMOUS Q1 (`pre-s38-backlog.md`)
- ✅ PHASE 3 Plan file (HARD-GATE satisfied, trace map mandatory)
- ✅ PHASE 4 7 tasks subagent-driven с per-task SPRINT_STATE updates
- ✅ TodoWrite phase tracker
- ✅ PHASE 5 Verify (pytest 905+33 / mypy 0 / canonical 16/30/74/50)
- ✅ PHASE 6 Review (selective per task)
- ✅ PHASE 7 Sync (this commit)
- ⏳ PHASE 8 Ship via gh pr + squash merge + tag v0.1.0-alpha.38
- ⏳ PHASE 9 Close — SPRINT_STATE → between-sprints + δ activation operator action

## Related

- ADR 0050-0057 (S33-S37 lineage)
- ADR 0058 (S38 — этот sprint)
- ADR 0056 amendment 2 (Sharpe pnl_pct semantics)
- ADR 0057 amendment (months_since truncation)
- ADR 0018 (HMAC pattern reference)
- pre-s35-backlog / pre-s36-backlog / pre-s37-backlog / pre-s38-backlog
- delta-activation-playbook.md (operator procedure — extended T6)
- bybit-api-reviewer query document (T3 finding source)
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (small-n statistical reality)
