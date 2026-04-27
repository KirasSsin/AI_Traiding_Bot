---
title: Sprint 33 — Trading Restart (test debt + MC fix + E DSR cross-trial + F multi-symbol BACKTEST verdict FAIL conjoint)
type: sprint
tags: [sprint-33, trading-restart, multi-symbol, mean-reversion, dsr-cross-trial, mc-p-value-fix, pre-registration, failure-branch-triggered, sixth-honest-close-pending, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - project/decisions/0050-sprint-33-trading-restart.md
  - project/plans/2026-04-27-sprint-33-trading-restart.md
  - project/pre-s33-backlog.md
  - data/sprint_33_F_measurement.json
---

# Sprint 33 — Trading Restart

## Overview

First trading sprint после 8-sprint S32 series kit improvements. Multi-symbol BTC+ETH+SOL 4H mean-reversion BACKTEST measurement с S17-relaxed params per pre-S33 3-agent consilium (trader-expert + trading-logic-reviewer + quant-stats-reviewer ROUND 1 + ROUND 2 unanimous APPROVE).

**Verdict: FAIL conjoint.** Pre-committed failure branch (Item #12) TRIGGERED → S34 = 6-th honest close v0.6 OR operator override.

Tag v0.1.0-alpha.33.

## Plan / ADR links

- [[../decisions/0050-sprint-33-trading-restart]] — Sprint 33 ADR (full pre-registration record + verdict)
- [[../plans/2026-04-27-sprint-33-trading-restart]] — Sprint 33 plan
- [[../pre-s33-backlog]] — 3-agent consilium ROUND 1 + ROUND 2 verdicts

## 6 tasks shipped

| Task | Type | Commit |
|------|------|--------|
| T1 Test debt fix + bars_per_year integration test | Code + tests (5 NEW + 3 fixed) | 88b3670 |
| T2 CC-D MC p-value fix BOTH formulas + Hypothesis property tests | Code + tests (7 NEW) | 807fce3 |
| T3 E DSR cross-trial extension (TrialEntry +symbol field with backfill BTCUSDT + sigma_SR pooling protocol (a)) — closes S14 Q2 carry-over | Code + tests (10 NEW) | 804d99e |
| T4 F preparation: WFA fold coverage validation per-symbol + MEAN_REVERSION_S17_RELAXED_PARAMS named constant + CLI args --wfa-train/test/folds/embargo | Code + tests (5 NEW) | 576621c |
| T5 F BACKTEST run (BTC+ETH+SOL 4H mean-reversion S17-relaxed, WFA train=1000/test=250 K=5) **VERDICT FAIL** | Measurement + cross_trial appended | 18d6e99 |
| T6 ADR 0050 + sprint-33 page + index/counts sync (this commit) | Wiki sync | (pending) |

## КУ achieved

| Item | T (token) | P (speed) | Q (quality) | КУ % |
|------|----------|-----------|-------------|------|
| T1 Test debt + integration test | 1 | 3 | 4 | 58% |
| T2 CC-D MC p-value fix | 2 | 3 | 5 | 70% |
| T3 E DSR cross-trial | 1 | 3 | 5 | 62% |
| T4 F preparation | 1 | 2 | 4 | 46% |
| T5 F BACKTEST measurement | 1 | 1 | 5 | 50% |
| T6 ADR + sync | 1 | 2 | 3 | 42% |
| **Sprint avg** | — | — | — | **55%** |

Time invested: ~6-8 hours (matches 8-12h forecast lower bound — TDD discipline + reused S15 multi-symbol code paths).

## F BACKTEST measurement results (T5)

**Verdict: FAIL conjoint** (5/9 acceptance gates failed).

### Aggregate metrics

| Criterion | Result | Threshold | Pass? |
|-----------|--------|-----------|-------|
| T1 Sharpe OOS | 8.47 | ≥ 1.0 | ✅ |
| T2 Sortino OOS | 17.44 | ≥ 1.5 | ✅ |
| T3 Max DD | 0.025 | ≤ 0.30 | ✅ |
| T4 Win rate | 42.4% | ≥ 40% | ✅ |
| T4 Avg RR | 2.16 | ≥ 1.5 | ✅ |
| **T5 n_trades raw** | **66** | **≥ 100** | ❌ |
| **T5 n_trades effective (n_eff)** | **26** | **≥ 100** | ❌ |
| **T6 OOS/IS Sharpe ratio mean** | **-2.84** | **≥ 0.7** | ❌ |
| **MC p-value aggregate** | **0.52** | **≤ 0.10** | ❌ |
| **DSR (n_trials=3, sigma_SR pooled=2.24)** | **0.919** | **≥ 0.95** | ❌ |

### Per-symbol results

| Symbol | Trades | Mean fold OOS Sharpe | Notable |
|--------|--------|----------------------|---------|
| BTCUSDT | 23 | -4.40 | Fold #3 catastrophic -32.68 |
| ETHUSDT | 25 | -3.85 | All 5 folds negative |
| SOLUSDT | 18 | -0.28 (least bad) | All folds negative |

### n_eff correction (Item #8 — Kish 1965 design effect)

Cross-symbol correlation rho ≈ 0.75 (BTC-ETH ~0.85 / BTC-SOL ~0.70 / ETH-SOL ~0.75).

Deflation: `1 + (m-1)*rho = 1 + 2×0.75 = 2.50`. n_eff = 66/2.5 = **26** (massively below T5=100).

t-stat correction: reported 1.47 → adjusted ~0.93 (also FAIL ≥ 2.0 threshold).

### Cross-trial DSR (T3 closes S14 Q2)

3 entries appended к `data/cross_trial_sharpes.json` (protocol (a)):
- (sprint=33, symbol=BTCUSDT, oos_sharpe=-4.40)
- (sprint=33, symbol=ETHUSDT, oos_sharpe=-3.85)
- (sprint=33, symbol=SOLUSDT, oos_sharpe=-0.28)

`sigma_SR pooled = 2.24` — first multi-symbol DSR computation.

## Pre-Committed Failure Branch (Item #12) TRIGGERED

S33 ADR 0050 documented BEFORE measurement (anti-data-snooping per Bailey & López de Prado 2014):

> "if F fails T5 OR MC p>0.10 OR DSR<0.95 → S34 = honest close v0.6 OR operator override"

**ALL 3 trigger conditions met:**
- T5 FAIL (raw 66 < 100, n_eff 26 << 100)
- MC p = 0.52 > 0.10
- DSR = 0.919 < 0.95

**Default action:** S34 = 6-th honest close v0.6 (mirror S14/S16/S18/S21/S23 BINDING precedent).

**Override option (operator-only):** explicit statistical-framework override statement в S34 ADR.

## Phase 5 Verify outcome

- pytest: 803 passed (was 773 = +5 T1 + 7 T2 + 10 T3 + 5 T4 + 3 fixed pre-existing failures)
- mypy --strict: 0 errors (was 1 pre-existing — fixed T1)
- canonical counts: 16/30/74/45 ✓
- bash -n hooks: ✓
- json validate (.mcp.json + cross_trial_sharpes.json + sprint_33_F_measurement.json): ✓
- yaml validate (.pre-commit-config.yaml + .github/workflows/ci.yml): ✓
- 4H bars_per_year integration test PASSED (S27 T1 integrity verified end-to-end via `4H vs 1H Sharpe ratio = sqrt(2190/8760) = 0.5` invariant)

## Phase 6 Review

Per Item #15 reviewer dispatch plan: `quant-stats-reviewer` + `trading-logic-reviewer` only used (Phase 2 brainstorm — no code review needed Phase 6 since S33 = config + tests + docs sprint, no production src/{execution,signalgen,risk}/ logic changes beyond TrialEntry schema (backward-compat) + named constant + CLI args).

5 dormant L5 reviewers (python-reviewer / architecture-reviewer / data-integrity-reviewer / security-auditor / dashboard-reviewer / bybit-api-reviewer) NOT dispatched per anti-token-waste guard (Item #15).

## FSM growth

No FSM changes (canonical counts: 16/30/74/45 — unchanged через S33).

## Reason codes

No new reason codes.

## Tests

30 NEW tests across S33 (T1: 5 / T2: 7 / T3: 10 / T4: 5 / + 3 pre-existing fixed). pytest: 773 → **803 passing**.

## Wiki updates summary

7 files touched:

In-repo NEW (3):
- ADR 0050 (decisions/)
- sprint-33 page (sprints/)
- pre-s33-backlog.md (project/)

In-repo MODIFIED (4):
- index.md (+ S33 sprint + ADR 0050)
- current-state.md (counts: 36→37 sprints / 49→50 ADRs + S33 sprint history row + test counts 773→803)
- log.md (sprint-end + session-end)
- SPRINT_STATE.md (S33 phase tracking + Phase 4 task progress)

In-repo NEW (code/data/tests):
- src/__main__.py MODIFIED (CLI args --wfa-train/test/folds/embargo + symbol kwarg)
- src/analytics/cross_trial_log.py MODIFIED (TrialEntry +symbol field + backfill)
- src/backtest/walk_forward.py MODIFIED (WalkForwardRunner.run() symbol kwarg + pre-validation)
- src/backtest/mc_permutation.py MODIFIED (CC-D fix BOTH formulas)
- src/signalgen/mean_reversion_strategy.py MODIFIED (+ MEAN_REVERSION_S17_RELAXED_PARAMS constant)
- 5 NEW test files (tests/test_bars_per_year_integration.py + tests/property/test_mc_invariants.py + tests/unit/{test_cross_trial_log_migration,test_dsr_multi_symbol,test_s17_relaxed_params_constant,test_wfa_fold_coverage}.py)
- 3 MODIFIED test fixtures (tests/test_replay_long_only.py + tests/test_replay_next_open.py)
- data/sprint_33_F_measurement.json NEW (measurement output)
- data/cross_trial_sharpes.json MODIFIED (3 S33 entries appended)

## Open issues для S34+

**S34 candidate (per pre-committed failure branch):**

**Default S34 = 6-th honest close v0.6** (operator decides operator-driven path):
- Document FAIL conjoint S33 verdict
- Archive cross_trial_sharpes.json к `_v0.6.json` + reset (mirror S16/S18/S21/S23)
- v0.7+ direction options: project pause / spec amendment / different strategy class / different timeframe

**Override option (operator-only):** explicit statistical-framework override statement.

**Carry-overs к S35+:**
- bybit-api-reviewer first real-world validation
- Bridge 4 corpus partition implementation (S40+ когда corpus > 100 obs)
- t-stat heavy-tail correction (Hudson&Urquhart 2021 — CC-E)
- ESC-3 4 binding conditions documented (для S34 LIVE multi-symbol если ever triggered)

**Trading carry-overs:**
- 5 strategy hypotheses tested across 4.81y BTC+ETH+SOL — все FAIL conjoint
- Edge regime-INDEPENDENT confirmed (S17+S22 partial PASS) but T5 unreachable
- Multi-symbol path empirically falsified S33 (n_eff=26 << 100 due correlation)

## Key decisions

1. **F multi-symbol hypothesis empirically FALSIFIED** — S33 demonstrated correlation deflation prevents T5 reachability even с 3-symbol expansion. Strategic implication: либо T5 floor amendment (operator) либо different strategy class.

2. **Pre-committed failure branch worked as designed** — predictable next step (S34 honest close), no post-hoc rationalization.

3. **CC-D MC p-value formula fix retroactive impact** — prior reports с p=0 systematically over-confident. S15/S17/S20/S22 measurements may need re-interpretation if strategic decisions relied on those values.

4. **S14 Q2 carry-over CLOSED** (T3 E DSR cross-trial extension) — multi-symbol DSR support implemented, sigma_SR pooled от 3 entries first time computed.

5. **Test debt 0** для first time post-S27 (8-sprint accumulation cleared) — S27 T1 fix integrity verified end-to-end via `4H vs 1H Sharpe ratio = sqrt(2190/8760) = 0.5` invariant.

6. **Reviewer dispatch discipline** — 5 dormant L5 reviewers NOT triggered (per Item #15 anti-token-waste guard).

## S33 process artifact

Per S28+ binding rules:
- ✅ PHASE 1 Orient
- ✅ PHASE 2 Brainstorm — 3-agent consilium 2 rounds (pre-s33-backlog.md)
- ✅ PHASE 3 Plan file (860b209)
- ✅ PHASE 4 6 tasks с per-task SPRINT_STATE updates
- ✅ TodoWrite phase tracker
- ✅ PHASE 5 Verify (pytest 803 / mypy 0 / canonical 16/30/74/45 / json+yaml validation)
- ✅ PHASE 6 Review skipped (per Item #15 reviewer dispatch plan)
- ✅ PHASE 7 Sync (index + current-state + kit-overview + log)
- ✅ PHASE 8 Ship via gh pr + squash merge + tag v0.1.0-alpha.33
- ✅ PHASE 9 Close — SPRINT_STATE → between-sprints + S34 trigger documented

## Related

- ADR 0014 (WFA defaults — amended CC6 (b) для 4H)
- ADR 0015 (MC permutation — CC-D fix restored compliance)
- ADR 0029 (S14 honest close — pattern reference)
- ADR 0030 (S15 multi-symbol attempt — anti-recurrence)
- ADR 0032 (S17 mean-reversion relaxed — params source)
- ADR 0037 (S22 4H test — failure branch precedent)
- ADR 0038 (S23 v0.5 honest close — 5-th honest close)
- ADR 0048 (S32d Kit Phase 3 — 8 candidates)
- ADR 0049 (S32e Kit Audit)
- **ADR 0050 (this S33 — F FAIL conjoint, 6-th honest close trigger pending)**
- Sprint S22 (BTC 4H PASS partial — regime-independent edge)
- Sprint S23 (T5=100 unreachable BINDING)
- Sprint S27 (formula bug fixes — bars_per_year + Sortino + RSI/ATR)
- pre-s33-backlog.md — full consilium trail
- Bailey & López de Prado 2014 (DSR + pre-registration)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique)
- Kish 1965 (design effect — n_eff)
- Phipson & Smyth 2010 (MC p-value formula)
