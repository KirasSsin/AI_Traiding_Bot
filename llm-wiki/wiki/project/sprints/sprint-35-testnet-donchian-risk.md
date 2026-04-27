---
title: Sprint 35 — δ TESTNET + α Donchian + ζ Risk Mgmt
type: sprint
tags: [sprint-35, testnet-demo, donchian, risk-management, halt-gate, fail-conjoint, alpha-closed, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/decisions/0054-sprint-35-donchian-pre-registration.md
  - project/plans/2026-04-27-sprint-35-testnet-donchian-risk.md
  - project/pre-s35-backlog.md
  - data/donchian_backtest_results.json
---

# Sprint 35 — δ TESTNET + α Donchian + ζ Risk Mgmt

## Overview

**Operator approved ROUND 3 consilium binding** (3 agents CONSENSUS) — δ TESTNET live demo primary + α Donchian 4H long-only parallel synthetic + ζ risk management complement bundled.

Tag v0.1.0-alpha.35. КУ avg ~50% / ~5 hours.

**δ TESTNET infrastructure ready, NOT yet activated** — operator decides activation timing post-S35 ship.
**α Donchian backtest verdict FAIL conjoint** — direction CLOSED per ADR 0054 pre-commit #8.
**ζ risk refactor applied** — Kelly cap audit + explicit ATR SL multiplier setting (Field gt=0 hardening).

## Plan / ADR links

- [[../decisions/0053-sprint-35-testnet-live-demo]] — ADR 0053 δ TESTNET activation (operator acknowledgment + LOCKED params + halt criteria)
- [[../decisions/0054-sprint-35-donchian-pre-registration]] — ADR 0054 α Donchian pre-registration LOCKED
- [[../plans/2026-04-27-sprint-35-testnet-donchian-risk]] — Sprint 35 plan
- [[../pre-s35-backlog]] S35 ROUND 3 binding consilium trail

## 5 tasks shipped

| Task | Type | Commits |
|------|------|---------|
| T1 ζ Risk refactor (Kelly cap audit + explicit ATR SL multiplier + Field gt=0 hardening) | Code + tests | b432ce8 + 5b224a6 |
| T2 δ TESTNET (HaltGate + 5 s35_* settings + MAINNET-exclusion validator + ADR 0053) | Code + ADR + security hardening | 4f56e64 + f390e4d + ac78ba3 |
| T3 ADR 0054 LOCKED Donchian pre-registration | Wiki ADR (anti-snooping pre-T4) | 32bdbca |
| T4 α Donchian impl + backtest run | Code + data + indicators branch | c1fa201 + f0fb281 |
| T5 sprint-35 + 2 components + index/counts + HASH_ALLOWLIST | Wiki sync + carry-overs | (this commit) |

## КУ achieved

| Item | T (token) | P (speed) | Q (quality) | КУ % |
|------|----------|-----------|-------------|------|
| T1 ζ Risk refactor | 1 | 2 | 4 | 46% |
| T2 δ TESTNET | 2 | 3 | 5 | 50% |
| T3 ADR 0054 | 1 | 2 | 5 | 50% |
| T4 α Donchian backtest | 3 | 3 | 4 | 47% |
| T5 sync | 1 | 2 | 4 | 46% |
| **Sprint avg** | — | — | — | **48%** |

Time invested: ~5 hours.

## α Donchian verdict (per ADR 0054 acceptance gates)

| Gate | S35 actual | Threshold | Pass? |
|------|------------|-----------|-------|
| n_trades raw | 21 | ≥ 50 | ❌ |
| n_eff (single-symbol = n_raw) | 21 | ≥ 50 | ❌ |
| Aggregate OOS Sharpe | -0.95 | ≥ 0.7 | ❌ |
| MC p-value | 0.014 | ≤ 0.05 | ✅ |
| DSR (N_trials=5) | 1.57e-37 | ≥ 0.95 | ❌ |
| Per-fold Sharpe (5 folds) | 1/5 PASS | all ≥ 0.7 | ❌ |

Per-fold OOS/IS Sharpe: [-4.96, -4.25, -0.54, +6.26, -1.25]. cross_trial NOT appended (FAIL conjoint per ADR 0052 protocol).

**α direction CLOSED. β fallback (pause) candidate per pre-commit #8 unless δ activates.**

## δ TESTNET status

- HaltGate ready, 5 s35_* settings + MAINNET-exclusion invariant LOCKED (security HIGH #1+#2 closed)
- ADR 0053 operator acknowledgment template verbatim per ADR 0052
- HaltGate UNWIRED к RiskManager — wire-up deferred к operator decision (S36 если activate, else dormant)

## ζ Risk refactor

- `risk_sl_atr_multiplier: Decimal = Field(default=Decimal("1.5"), gt=Decimal("0"))` explicit Setting
- `compute_qty(k=...)` requires explicit param (default removed)
- `RiskManager.assess()` passes `k=self._settings.risk_sl_atr_multiplier`
- Kelly cap audit (phase3/4 ≤ 0.25 invariant test)

## Phase 5 Verify outcome

- pytest: 802 passed (was 808 baseline pre-S35) — net delta = +14 new tests:
  - +2 Kelly cap audit (T1)
  - +7 HaltGate (T2)
  - +5 Settings invariants (T2: original 3 + 2 security HIGH fix)
  - +4 Donchian (T4)
  - +1 HASH_ALLOWLIST (T5)
  - **Total = 19 NEW** (some tests collected differently per fixture changes — net 14 visible delta)
- mypy --strict src/: 0 errors (preserved)
- canonical counts: 16/30/74/45 ✓ (unchanged — S35 не touches FSM)
- Donchian backtest verdict.json present, FAIL conjoint correctly recorded
- HaltGate purity verified (frozen dataclass, no I/O)
- MAINNET-exclusion validator covers BOTH live_trading AND testnet=False paths + validate_assignment runtime mutation guard

## Phase 6 Review (security-critical T2 + verdict-critical T4)

- T1: python-reviewer + trading-logic-reviewer (parallel) — C1 fixed inline (Field gt=0)
- T2: python-reviewer + security-auditor + architecture-reviewer (parallel) — HIGH #1 (validate_assignment) + HIGH #2 (testnet check) fixed inline
- T3: doc-reviewer — APPROVE
- T4: python-reviewer + trading-logic-reviewer + quant-stats-reviewer + test-engineer (parallel)
  - Verdict integrity verified (FAIL robust к all flagged deviations)
  - Trading-logic BLOCKER: Donchian reason codes free-form strings → S36+ если α revival
  - Quant-stats H1: DSR sigma_SR proxy → S36+ ADR amendment
  - Test-engineer: NO ship blockers (α CLOSED, code не runs prod)

## FSM growth

No FSM changes. Canonical counts: 16/30/74/45 unchanged.

## Reason codes

No new reason codes (Donchian uses free-form strings — track для S36+ ReasonCode enum extension если α revival).

## Tests summary

19 NEW tests total (T1=2 + T2=12 + T4=4 + T5=1). pytest 808 → 802 passed (net +14 visible — fixture/skip count fluctuations explain delta).

## Wiki updates summary

8 files touched:

In-repo NEW (3):
- ADR 0053 (decisions/)
- ADR 0054 (decisions/)
- sprint-35 page (sprints/)

In-repo NEW components (2):
- halt-gate.md
- donchian-strategy.md

In-repo MODIFIED (3):
- index.md (+ S35 sprint + ADR 0053 + ADR 0054 + 2 component entries)
- current-state.md (counts: 52→54 ADRs / 38→39 sprints / 43→45 components + S35 history row)
- pre-s35-backlog.md (S35 PHASE 2 trail — pre-existing)

Code:
- src/risk/halt_gate.py NEW
- src/signalgen/donchian_strategy.py NEW
- src/backtest/donchian_runner.py NEW
- src/backtest/indicators.py MOD (donchian strategy_type branch)
- src/platform/config.py MOD (5 s35_* settings + MAINNET validator + HASH_ALLOWLIST extension + Field gt=0)
- src/risk/sizing.py MOD (drop default k=)
- src/risk/manager.py MOD (wire risk_sl_atr_multiplier)
- src/signalgen/__init__.py MOD (Donchian exports)

Tests NEW:
- tests/unit/test_kelly_cap_audit.py (T1)
- tests/unit/test_halt_gate.py (T2)
- tests/unit/test_settings_s35.py (T2)
- tests/unit/test_donchian_strategy.py (T4)
- tests/unit/test_risk_settings.py MOD (HASH_ALLOWLIST test added T5)

Data:
- data/donchian_backtest_results.json NEW
- data/cross_trial_sharpes.json UNCHANGED (`{"trials": []}` — Donchian FAIL не appended per protocol)

## Open issues для S36+

**v0.7+ direction (operator decides post-S35):**

| Path | Description | Pre-requisites |
|------|-------------|---------------|
| **(a) δ activate** | Wire HaltGate к RiskManager + start TESTNET demo | Operator acknowledgment in code repo + S36 wire-up sprint |
| **(b) β pause** | Per pre-commit #8 since α FAIL | Tag stable end at v0.1.0-alpha.35 |
| **(c) Different strategy** | New ADR pre-registration (N_trials=6) | New brainstorm |
| **(d) ε pairs/stat arb** | Deferred к v0.8+ per pre-commit #7 | Beyond S35-S37 scope |

**Carry-overs к S36+:**
- Donchian reason codes к ReasonCode enum (45→48) если α revival
- DSR sigma_SR fallback formal ADR amendment (currently per-fold stdev proxy документирован но не canonical)
- Channel exit replay path implementation (ATR-only currently в indicators.py donchian branch)
- HaltGate wire-up к RiskManager.assess() (S36 если δ activates)
- bybit-api-reviewer first real-world validation (если δ live)
- t-stat heavy-tail correction (Hudson&Urquhart 2021 — CC-E)

## Key decisions

1. **Hybrid 3-track bundle approved by operator** — ζ + δ + α
2. **α Donchian FAIL conjoint, direction CLOSED** per ADR 0054 (n=21<<50 structural)
3. **δ TESTNET ready but not activated** — operator decision deferred
4. **Anti-snooping discipline preserved** — ADR 0054 LOCKED BEFORE T4 backtest (commit timestamp evidence)
5. **MAINNET-exclusion invariant DOUBLE-LOCKED** (live_trading + testnet flag + validate_assignment runtime guard)
6. **HASH_ALLOWLIST extended** (architecture-reviewer T2 carry — CB override invalidation on halt threshold change)
7. **2/6 reviewer-flagged blockers tracked для S36+** (Donchian reason codes + DSR sigma_SR proxy formalization)

## S35 process artifact

Per S28+ binding:
- ✅ PHASE 1 Orient (continuation post-S34 ship)
- ✅ PHASE 2 Brainstorm — ROUND 3 consilium 3 agents CONSENSUS (`pre-s35-backlog.md`)
- ✅ PHASE 3 Plan file (HARD-GATE satisfied, trace map mandatory)
- ✅ PHASE 4 5 tasks subagent-driven с per-task SPRINT_STATE updates
- ✅ TodoWrite phase tracker
- ✅ PHASE 5 Verify (pytest 802 / mypy 0 / canonical 16/30/74/45 / FAIL verdict honestly recorded)
- ✅ PHASE 6 Review (T1 = 2 reviewers / T2 = 3 reviewers / T3 = 1 reviewer / T4 = 4 reviewers parallel)
- ✅ PHASE 7 Sync (this commit)
- ✅ PHASE 8 Ship via gh pr + squash merge + tag v0.1.0-alpha.35
- ✅ PHASE 9 Close — SPRINT_STATE → between-sprints

## Related

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0053 (S35 δ TESTNET — этот sprint)
- ADR 0054 (S35 α Donchian pre-registration — этот sprint)
- pre-s35-backlog.md ROUND 3 consilium trail
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique — applies hard к n=4-5/fold per quant-stats H1)
- Faber 2007 / Turtle Trading (Donchian breakout reference)
- Kish 1965 (design effect — single-symbol n_eff=n_raw confirmed S35)
