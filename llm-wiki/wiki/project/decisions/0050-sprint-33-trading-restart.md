---
title: ADR 0050 — Sprint 33 Trading Restart (test debt + MC fix + E DSR cross-trial + F multi-symbol BACKTEST verdict FAIL conjoint)
type: decision
tags: [adr, sprint-33, trading-restart, multi-symbol, mean-reversion, dsr-cross-trial, mc-p-value-fix, pre-registration, failure-branch-triggered, sixth-honest-close]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/plans/2026-04-27-sprint-33-trading-restart.md
  - project/pre-s33-backlog.md
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/decisions/0014-walk-forward-acceptance-thresholds.md
  - project/decisions/0015-monte-carlo-test.md
  - data/sprint_33_F_measurement.json
  - data/cross_trial_sharpes.json
---

# ADR 0050 — Sprint 33 Trading Restart

## Status

Accepted (2026-04-27) — implemented в S33 (`feature/sprint-33-trading-restart` → tag `v0.1.0-alpha.33`). First trading sprint после 8-sprint S32 series kit improvements. **Verdict FAIL conjoint — pre-committed failure branch (Item #12) TRIGGERED → S34 = 6-th honest close v0.6.**

## Context

Per pre-S33 brainstorm consilium (3 agents × 2 rounds, persisted в `pre-s33-backlog.md`):
- 6 escalation items APPROVED unanimously
- 13 REQUIRED + 2 OPTIONAL NEW items consolidated
- All 3 agents CONFIRM_REVISE final position

**Project state pre-S33:**
- 32 sprints shipped (S1-S32e). Tag `v0.1.0-alpha.32e`. Kit infrastructure mature.
- 5 honest closes prior (S14/S16/S18/S21/S23) — все 5 strategy hypotheses FAIL conjoint
- T5=100 floor STRUCTURALLY UNREACHABLE single-symbol BTC (S22 binding insight)
- S17+S22 partial PASS evidence (5/6+DSR+MC) — strategy edge regime-INDEPENDENT, but T5 fails on count

**S33 hypothesis (per consilium synthesis):** Multi-symbol BTC+ETH+SOL 4H mean-reversion с S17-relaxed params reaches T5 ≥ 100 mathematically (n≈135-180 raw aggregate).

## Options

**Option A: Single-symbol BTC continuation**
- Pros: simple, no new infra
- Cons: T5 structurally closed (3 timeframes 60-73 trades)

**Option B: Multi-symbol BACKTEST measurement (S33) + Live deferred (S34)**
- Pros: validates F mathematically, zero new live code, predictable ship
- Cons: Live deployment needs 650-850 LoC infra (Kelly capital-split + orchestration + halt-cascade isolation + correlation matrix)

**Option C: Skip S33 → operator pause**
- Pros: no measurement effort
- Cons: leaves T5 hypothesis untested, project state ambiguous

## Decision

**Option B selected per consilium ROUND 2 unanimous CONSENSUS.** S33 = backtest measurement sprint + 5 prerequisite changes. Live deployment infra → S34 separate sprint (если F passes).

### S33 6 tasks shipped

| # | Change | Commit | Items |
|---|--------|--------|-------|
| T1 | Test debt fix (3 pytest + 1 mypy) + bars_per_year 4H end-to-end integration test | 88b3670 | Q6 + #11 |
| T2 | CC-D MC p-value fix BOTH formulas `(count+1)/(N+1)` per Phipson & Smyth 2010 / ADR 0015 + Hypothesis property tests | 807fce3 | #1 + #2 |
| T3 | E DSR cross-trial extension (TrialEntry +symbol field with backfill BTCUSDT + sigma_SR pooling protocol (a) all entries) — closes S14 Q2 carry-over | 804d99e | #6 + #7 + #9 |
| T4 | F preparation: WFA fold coverage validation per-symbol + MEAN_REVERSION_S17_RELAXED_PARAMS named constant + CLI args --wfa-train/test/folds/embargo | 576621c | #5 + #10 |
| T5 | F BACKTEST run (BTC+ETH+SOL 4H, WFA train=1000/test=250 K=5, 3 trials appended, n_eff correction reported) | 18d6e99 | #3 + #7 + #8 |
| T6 | ADR 0050 + sprint-33 page + index/counts sync (this commit) | (pending) | #4 + #12 + #13 + #15 |

## 9-item Pre-Registration Checklist (LOCKED PRE-MEASUREMENT — Item #4)

ADR 0050 documents pre-registered values ДО F measurement (anti-data-snooping per Bailey & López de Prado 2014):

| # | Param | Value | Source |
|---|-------|-------|--------|
| 1 | Strategy params | `MEAN_REVERSION_S17_RELAXED_PARAMS` (RSI 14 / oversold=Decimal('35') / overbought=Decimal('65') / BB period=20 / std_mult=1.5 / and_gate_required=True) | Item #5 — sprint-17 PASS partial reference |
| 2 | WFA window train_bars | 1000 | CC6 (b) consensus 4H specific |
| 3 | WFA window test_bars | 250 | CC6 (b) — preserves OOS/IS ratio 0.25 (ADR 0014 default) |
| 4 | WFA k_folds | 5 | ADR 0014 default |
| 5 | WFA embargo_bars | 20 | ADR 0014 default |
| 6 | Symbols | BTCUSDT + ETHUSDT + SOLUSDT (no additions) | ESC-1 consensus |
| 7 | MC p-value threshold | ≤ 0.10 (pre-committed failure branch trigger) | Item #12 |
| 8 | DSR threshold | ≥ 0.95 | ADR 0014 |
| 9 | n_trials counting protocol | (a) — pool ALL (sprint, symbol) pairs as independent trials | Item #6 + #7 |

**sigma_SR pooling protocol:** (a) — pool all entries (methodologically conservative per Bailey & López de Prado eq. 12).

## ESC-3 — 4 Binding Conditions для S34 LIVE Multi-symbol (Item #3)

S34 LIVE deployment requires ALL 4 conditions before authorization:

1. **Operator written ack** — 100% capital exposure during concurrent BTC+ETH+SOL LONG signals
2. **Kelly capital-split logic** — RiskManager `concurrent_positions: int` config + 1/N capital allocation OR risk-weighted (1/ATR_symbol) per consilium quant
3. **Correlation matrix** — `risk/manager.py` adds correlation-adjusted portfolio σ (deflation factor sqrt(1+(m-1)*rho), rho≈0.75 для BTC/ETH/SOL) per quant Q3 EXPAND
4. **Halt-cascade isolation specification** — explicit: BTC halt does NOT halt ETH/SOL (current behavior, document policy) per trader Q1 binding 4-th condition

S34 ADR (если triggered) documents these 4 conditions с acceptance tests.

## F BACKTEST Measurement Results (T5 — pre-registered execution)

Per `data/sprint_33_F_measurement.json`:

### Verdict: **FAIL conjoint** на 5/9 acceptance gates

| Criterion | Result | Threshold | Pass? |
|-----------|--------|-----------|-------|
| T1 Sharpe OOS | 8.47 | ≥ 1.0 | ✅ |
| T2 Sortino OOS | 17.44 | ≥ 1.5 | ✅ |
| T3 Max DD | 0.025 | ≤ 0.30 | ✅ |
| T4 Win rate | 42.4% | ≥ 40% | ✅ |
| T4 Avg RR | 2.16 | ≥ 1.5 | ✅ |
| **T5 n_trades raw** | **66** | **≥ 100** | ❌ |
| **T5 n_trades effective (n_eff Item #8)** | **26** | **≥ 100** | ❌ |
| **T6 OOS/IS Sharpe ratio mean** | **-2.84** | **≥ 0.7** | ❌ |
| **MC p-value aggregate (Item #12 pre-committed)** | **0.52** | **≤ 0.10** | ❌ |
| **DSR (n_trials=3, sigma_SR pooled=2.24)** | **0.919** | **≥ 0.95** | ❌ |

### Per-symbol results

| Symbol | Trades | Mean fold OOS Sharpe | Notable fold |
|--------|--------|----------------------|--------------|
| BTCUSDT | 23 | -4.40 | Fold #3 catastrophic -32.68 |
| ETHUSDT | 25 | -3.85 | All folds negative |
| SOLUSDT | 18 | -0.28 (least bad) | All folds negative |

### n_eff correction (Item #8 — Kish 1965 design effect)

Raw n=66 (BTC=23+ETH=25+SOL=18). Cross-symbol correlation rho≈0.75 average (BTC-ETH ~0.85 / BTC-SOL ~0.70 / ETH-SOL ~0.75 per quant Q1 EXPAND).

Deflation factor: `1 + (m-1)*rho = 1 + 2*0.75 = 2.50`.

Effective n_eff = 66 / 2.5 = **26** (massively below T5=100).

t-stat denominator understated by sqrt(2.5) ≈ 1.58× — reported t-stat = 1.47, corrected t-stat = 1.47/1.58 ≈ **0.93** (also fails T5 threshold ≥ 2.0).

### Cross-trial sigma_SR (closes S14 Q2 carry-over per T3)

3 entries appended к `data/cross_trial_sharpes.json` per protocol (a):
- (sprint=33, symbol=BTCUSDT, oos_sharpe=-4.40)
- (sprint=33, symbol=ETHUSDT, oos_sharpe=-3.85)
- (sprint=33, symbol=SOLUSDT, oos_sharpe=-0.28)

`sigma_SR pooled = statistics.stdev([-4.40, -3.85, -0.28]) = 2.24` — first-time multi-symbol DSR computation. n_trials=3 (NOT 1 — protocol (a) correct).

## Pre-Committed Failure Branch (Item #12) — TRIGGERED

S33 ADR 0050 documented BEFORE measurement: "if F fails T5 OR MC p>0.10 OR DSR<0.95 → S34 = honest close v0.6 OR operator override."

**ALL 3 trigger conditions met:**
- T5 FAIL (raw 66 < 100, n_eff 26 << 100)
- MC p = 0.52 > 0.10
- DSR = 0.919 < 0.95

**Default action:** S34 = 6-th honest close v0.6 (mirror S14/S16/S18/S21/S23 BINDING precedent).

**Override option (operator-only):** explicit statistical-framework override statement в S34 ADR с full acknowledgment that:
- Statistical evidence does NOT support live deployment
- Multi-symbol path explored, hypothesis falsified empirically
- Spec amendment к acceptance-criteria.md required if continuing (T5 floor 100 lowered OR MC threshold relaxed)

## Reviewer Dispatch Plan (Item #15)

S33 = formula/stats/process sprint, no production trading code modifications в `src/{execution,signalgen,risk}/` беyond test fixtures + named constant + CLI args. Reviewer matrix:

| Reviewer | Used? | Rationale |
|----------|-------|-----------|
| trader-expert | ✅ Phase 2 brainstorm | Trading strategy/business consilium |
| trading-logic-reviewer | ✅ Phase 2 brainstorm | Engineering consilium |
| quant-stats-reviewer | ✅ Phase 2 brainstorm | Math/stats consilium |
| python-reviewer | ⏸️ Skip | No new generic Python code |
| architecture-reviewer | ⏸️ Skip | No cross-module refactor |
| data-integrity-reviewer | ⏸️ Skip | No schema migration (TrialEntry +symbol = backward-compat) |
| security-auditor | ⏸️ Skip | No money/API/override code touched |
| test-engineer | ⏸️ Skip | New tests добавлены TDD, not coverage gap |
| doc-reviewer | ⏸️ Skip | Wiki updates standard pattern |
| dashboard-reviewer | ⏸️ Skip | No dashboard touched |
| bybit-api-reviewer | ⏸️ Skip | No Bybit V5 API code touched |

**Phase 6 actual review:** Skipped — config + tests + docs sprint, NO production src/ changes требующие code review beyond Phase 2 consilium.

Anti-pattern avoided: 5-agent parallel dispatch для pure-stats sprint = wasted ~30 min (per Item #15).

## Implementation Refs

Per plan `2026-04-27-sprint-33-trading-restart.md`:
- T1 → 88b3670 (test debt fix + bars_per_year 4H integration test)
- T2 → 807fce3 (CC-D MC p-value fix BOTH formulas + property tests)
- T3 → 804d99e (E DSR cross-trial extension)
- T4 → 576621c (F preparation: WFA validation + S17 named constant)
- T5 → 18d6e99 (F BACKTEST measurement FAIL conjoint)
- T6 → (this commit)

Tag: `v0.1.0-alpha.33`.

## Test/Quality State Post-S33

- pytest unit: 803 passed (+30 vs S32 baseline 773 = +5 T1 + 7 T2 + 10 T3 + 5 T4 + 3 fixed pre-existing)
- mypy --strict src/: 0 errors (was 1 pre-existing — fixed T1)
- ruff: ~169 pre-existing baseline (unchanged S33)
- canonical counts: 16/30/74/45 (unchanged через S33)
- CI: passed (5th PR validation S32b infrastructure)

## Consequences

### Positive

1. **Hypothesis tested cleanly** — S17-relaxed multi-symbol expansion empirically falsified, no spec ambiguity
2. **MC p-value formula compliance** — ADR 0015 violation closed (CC-D fix BOTH formulas)
3. **S14 Q2 carry-over closed** — DSR cross-trial sigma_SR multi-symbol support implemented (T3)
4. **Pre-registration discipline demonstrated** — first sprint с full LOCKED ADR ДО measurement (anti-data-snooping)
5. **Failure branch worked as designed** — pre-committed → predictable next step (no post-hoc rationalization)
6. **n_eff correction reported** — first sprint с correlation-deflated effective sample size disclosure
7. **Test debt 0** — pytest 0 failures + mypy 0 errors first time post-S27 (8 sprints debt cleared)

### Negative

1. **F hypothesis FAILED** — multi-symbol path не resolves T5 unreachability (n_eff=26 << 100 due correlation)
2. **6-th honest close** likely (S34 default action) — project pause OR spec amendment required
3. **MC p-value impact retroactive** — prior reports с p=0 systematically over-confident (S15/S17/S20/S22 measurements). Re-interpretation needed if strategic decisions relied on those.
4. **No new strategy edge identified** — S33 не proposed alternative hypothesis после F FAIL

### Neutral

1. Kit infrastructure (S32 series) functioned end-to-end — first real trading sprint post-S32
2. CI infrastructure validated 5th PR
3. Pattern continues: S33 = sprint #6 testing same conjoint failure mode (5 honest closes prior)

## Follow-ups

### S34 candidate (per pre-committed failure branch)

**Default:** S34 = 6-th honest close v0.6 (operator-driven decision, mirror S14 ADR 0029 pattern):
- Document FAIL conjoint S33 verdict
- Archive cross_trial_sharpes.json к `_v0.6.json` + reset (mirror S16/S18/S21/S23 honest close pattern)
- v0.7+ direction: operator decides между:
  - (a) Project pause (S24 Option E precedent)
  - (b) Spec amendment к acceptance-criteria.md T5 floor (operator-driven explicit override statement)
  - (c) Different strategy class (Donchian breakout, ML-driven signal filter, etc — beyond mean-reversion paradigm)
  - (d) Different timeframe + different params (e.g., 1D mean-reversion с volume gate)

**Alternative:** If operator chooses override, S34 amends ADR + adjusts gates с explicit "operator override" documentation.

### Carry-overs preserved

- bybit-api-reviewer first real-world validation (S35+ если live deployment ever happens)
- Bridge 4 corpus partition implementation (S40+ когда corpus > 100 obs)
- t-stat heavy-tail correction (CC-E, Hudson&Urquhart 2021) — math improvement, deferred
- ESC-3 4 binding conditions documented (этот ADR) для S34 LIVE multi-symbol prerequisite

### NOT planned

- ❌ Re-run F с different params (data-snooping anti-pattern — pre-registration violated)
- ❌ Pool aggregate Sharpe (n_trials=1) к "improve" DSR — protocol (a) BINDING per S33 ADR
- ❌ Continue к Bridge 4 / live infra без operator authorization S34 direction

## Related

- ADR 0014 (WFA defaults — train=2000/test=500 amended via CC6 (b) для 4H S33: train=1000/test=250)
- ADR 0015 (MC permutation test — CC-D fix restores compliance)
- ADR 0017 (review-agent harness)
- ADR 0029 (S14 honest close — pattern reference)
- ADR 0030 (S15 multi-symbol attempt — anti-recurrence reference)
- ADR 0032 (S17 mean-reversion relaxed — params source)
- ADR 0037 (S22 4H test — failure branch precedent BINDING)
- ADR 0038 (S23 v0.5 honest close — 5-th honest close)
- ADR 0048 (S32d Kit Phase 3 — 8 candidates A-H)
- ADR 0049 (S32e Kit Audit)
- ADR 0050 (this) — S33 trading restart с FAIL verdict
- pre-s33-backlog.md — 3-agent consilium ROUND 1 + ROUND 2 verdicts
- Bailey & López de Prado 2014 (DSR + cross-trial sigma_SR + pre-registration discipline)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique — CC-E ongoing concern)
- Kish 1965 (design effect для clustered samples — Item #8 n_eff)
- Phipson & Smyth 2010 (MC p-value `(count+1)/(N+1)` — CC-D reference)
