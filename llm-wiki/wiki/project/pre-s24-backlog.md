---
title: Pre-S24 backlog — v0.6 direction selection (post-v0.5-honest-close)
type: backlog
tags: [sprint-24, brainstorm, phase-2, verdicts, trader-expert, architecture-reviewer, v0.6-direction, post-v0.5-final]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0038-sprint-23-honest-close-v05.md
  - project/decisions/0037-sprint-22-4h-test.md
  - project/sprints/sprint-23-honest-close-v05.md
  - project/sprints/sprint-22-4h-test.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
  - project/architecture/acceptance-criteria.md
---

# Pre-S24 backlog — v0.6 direction selection

## Context (post-S23 v0.5 honest close)

S23 shipped (PR #31, tag `v0.1.0-alpha.23`). v0.5 closed honest. **5 strategy hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint**.

**Critical institutional knowledge preserved (CC1+CC3 BINDING per ADR 0038):**

1. **T5 100 STRUCTURALLY UNREACHABLE на BTC-only mean-reversion** — 3 timeframes empirical evidence:
   - S17 BTC 1H: 59 trades
   - S20 BTC 15M: 73 trades (degraded T1=-45.57)
   - S22 BTC 4H: 62 trades

   FLAT-only constraint + AND-gate dominate trade count. Multi-symbol ONLY path к T5 ≥100 (out of MVP per user).

2. **Strategy edge regime-INDEPENDENT (S17+S22)** — both produced 5/6+DSR+MC PASS на 1H AND 4H. Combined trades ~121 (S17 59 + S22 62). Hypothesis stable in 1H-4H range.

3. **N_trials reset:** cross_trial_sharpes archived к `_v0.5-final.json`, fresh `[]` для v0.6 (4-th archival).

**User constraint (BINDING):** MVP scope = BTCUSDT only per ADR 0016 + 2026-04-26 confirmation.

**User directive 2026-04-26:** "Зайди с этими вопросами в агентов трейдеров, пусть они проведут дискуссию и выберут" → joint trader+architecture dispatch.

## S24 PHASE 2 brainstorming question (1 question — v0.6 direction)

### Q1 — v0.6 direction selection

**Question:** Какое v0.6 направление наиболее обоснованно учитывая (a) T5 100 structurally unreachable на BTC-only, (b) strategy edge regime-INDEPENDENT (S17+S22 ~120 combined trades), (c) Hudson & Urquhart 2021 only validates 15M degradation (4H stable)?

**Maintainer recommended option:** (F) MVP T5 floor amendment — empirical evidence shows 100 floor incompatible с BTC-only mean-reversion regardless of strategy work. Spec amendment к acceptance-criteria.md (T5 floor relaxation OR document multi-symbol allowed) могут unlock MVP DONE с existing S17/S22 evidence.

**6 options considered:**

- (a) **(v0.6-A) Hybrid mean-reversion + ML XGBoost filter** — S17+S22 combined ~120 trades. Trader S22 rejected ML на n=59 (CPCV needs ≥500), но n=120 still small для CPCV. ML overfit risk + 5-10 sprints CPCV framework. Cost: 5-10 sprints.

- (b) **(v0.6-B) HMM regime-switch + mean-reversion** — addresses fold concentration patterns (S17 fold #5, S22 fold #3, S20 fold #2). 4-6 sprints architectural cost. Increases complexity. Cost: 4-6 sprints.

- (c) **(v0.6-C) Multi-symbol revival post-MVP** — ONLY path к T5 ≥100 conjoint per S22 critical insight. Currently out of MVP scope per user 2026-04-26. Reconsider если operator amends MVP scope. Cost: 1 sprint (S15 infrastructure already exists).

- (d) **(v0.6-D) Different strategy class entirely** (donchian breakout, ATR-bands, regime-detection) — fresh hypothesis space. Donchian = trend-following family, S13 evidence shows similar low frequency. ATR-bands variant of mean-reversion (different params). Cost: 2-3 sprints (new strategy class).

- (e) **(v0.6-E) Project pause** — 5 hypotheses + structural insight = strong publishable contribution. Cost: 0.

- (f) **(v0.6-F) MVP T5 floor amendment** (recommended) — empirical evidence:
  - 4 BTC-only sprints showed 59/73/62 trades (max 73)
  - T5 floor 100 vs 73 = 27% gap, structurally unreachable per CC1 BINDING
  - Spec amendment options: (i) T5 floor relaxation к 60-75 (matches empirical), (ii) Allow multi-symbol в MVP (revives S15 infrastructure + path к T5 ≥100), (iii) Document T5 floor exception для mean-reversion family
  - Cost: 1 sprint (docs amendment к acceptance-criteria.md + ADR 0039 + recompute existing S17/S22 verdicts с amended criteria)
  - Если amended → S17+S22 могут retroactively PASS conjoint criteria → MVP DONE achievable on existing evidence

**Reasoning for recommended (F):**
- Empirical evidence accumulated за 5 sprints supports spec gap (BTC-only mean-reversion max ~73 trades vs 100 floor)
- Cheapest viable path к MVP DONE (1 sprint vs ML 5-10)
- Уже produced positive evidence (S17+S22 5/6+DSR+MC PASS)
- Operator-level decision (spec amendment = product decision, не engineering)
- Если amended → existing measurement evidence directly applicable, не нужны new measurement sprints

**Risk/concern:**
- Spec amendment goal-seeking concern (P-hacking accusation: "lowering bar к pass")
- Mitigation: amendment based на empirical structural limit, не cherry-picking
- Multi-symbol path (option F-ii) = scope expansion, may conflict с user MVP=BTC only constraint
- T5 floor relaxation (option F-i) = may produce statistical false-positives (small sample t-stat issues)
- Operator alone decides if spec amendment ethically defensible (per Bailey 2014 multi-testing discipline norm)

## ROUND 1 verdicts (TRADER-EXPERT + ARCHITECTURE-REVIEWER, complete)

| # | Question | Trader verdict | Architecture verdict | Final accepted |
|---|----------|----------------|----------------------|----------------|
| Q1 | v0.6 direction selection | **REVISE → (E) pause** | **CONFIRM trader REVISE → (E) pause** | (E) project pause + ESC-1 к user |

## Trader REVISE rationale (critical findings)

**CRITICAL FINDING:** Acceptance gate failure independent of T5 count в S17+S22 (verified в s17_wfa_result.json + s22_wfa_result.json):
- S17: `acceptance_gate.sharpe_gate_passed=false`, `failed_folds=[1,2]`
- S22: `acceptance_gate.sharpe_gate_passed=false`, `failed_folds=[1]`

**Maintainer framing "5/6+DSR+MC PASS" misleading** — composite acceptance gate also fails on per-fold sharpe consistency check. Option F spec amendment NOT unlocks MVP DONE on existing evidence (T5 floor + t_stat + acceptance_gate would all need amendment = "spec gutted, not amended").

**Bailey 2014 discipline:** T5 floor 100 = sample-size lower bound для t-test validity, не operator default. Adjusting after observing data = textbook multiple-comparison bias.

**Other options ruled out:**
- (A) ML XGBoost: n=120 still <500 CPCV minimum. S20 15M degradation проves NOT timeframe-invariant → pooling 1H+4H unjustified.
- (B) HMM: would overfit к S17 fold #5 + S22 fold #3 outliers (more complex ML overfit problem).
- (C) Multi-symbol revival: REQUIRES user reversal of BTC-only binding constraint (ESC-1).
- (D) Different strategy class: no escape от FLAT-only structural constraint.

**Option E (pause) — epistemically honest position:**
- 5 hypotheses tested, 2 (S17+S22) showed MC p≤0.02 + DSR≥0.996 stat-sig signals на 2 timeframes
- Scientific finding precise: BTC spot mean-reversion (RSI 35/65 + BB 1.5σ) statistically significant но structurally incapable of ≥100 OOS trades single-symbol any timeframe
- 24-sprint infrastructure preserved, capital exposure 0
- Sunk-cost ("25 sprints invested") NOT valid decision criterion

## Architecture verdict (CONFIRM trader REVISE)

**Acceptance gate failure CONFIRMED** с file:line evidence (sharpe_gate_passed=false в both files).

**Architecture critical addition к Option F cost:**
- Spec amendment requires WFA pipeline re-run (stale JSON otherwise) — НЕ pure docs amendment
- True cost: 2-3 sprints + quant-stats-reviewer + data-integrity-reviewer + trading-logic-reviewer sign-offs
- Maintainer 1-sprint estimate optimistic by 2-3x

**Option C (multi-symbol) = ONLY architecturally cheap path к MVP DONE** (1 sprint, S15 infrastructure preserved) — но requires user reversal of BTC-only constraint (cannot resolve architecturally).

**Architecture verdict:** CONFIRM trader REVISE к Option E под current binding constraints. If user lifts BTC-only constraint → Option C dominant. All other options require 2+ sprints with no guarantee.

## Cross-cutting concerns (joint)

- **CC1 acceptance_gate failure independent of T5** — both S17 + S22 fail composite gate, not just count
- **CC2 T1=25.99 (S17) vs T1=6.17 (S22) divergence** — 9.5x mean_pnl difference + lower t_stat at S22 = unstable signal estimate (likely fold #3 outlier dominance)
- **CC3 Multi-symbol parameters CC** (if Option C revived): use S17 relaxed (RSI 35/65, BB 1.5σ), не S15 original (RSI 30/70, BB 2σ) — distinct hypothesis requires fresh pre-registration
- **CC4 N_trials reset clean** (data/cross_trial_sharpes.json={"trials": []} confirmed)
- **CC5 Option F spec amendment cost underestimation** — institutional knowledge для future spec amendments

## ESCALATION к user (BLOCKING — operator decision required)

**ESC-1 (BLOCKING):** Pause vs scope expansion.

Verbatim per trader: "The project has accumulated 5 tested hypotheses. Two (S17 1H, S22 4H) produced statistically significant signals (MC p≤0.02) but cannot pass the pre-registered n≥100 trade floor on BTC-only single-symbol data. The options are:
- **(a) PAUSE** — declare findings, preserve infrastructure, publish results
- **(b) Expand MVP scope to multi-symbol** (reverses your 2026-04-26 BTC-only constraint and ADR 0016) — the only demonstrated path к ≥100 trades

Do you choose (a) or (b)?"

**ESC-2 (conditional on ESC-1 → b):** Multi-symbol parameters.
- (i) S15 original (RSI 30/70, BB 2σ) — failed T6+MC+DSR в S15
- (ii) S17 relaxed (RSI 35/65, BB 1.5σ) — showed BTC-only signal
- (ii) recommended per CC3 — но requires fresh pre-registered measurement sprint

**ESC-3 (conditional on operator requesting F-i):** T5 floor relaxation ethical acknowledgment.
- Lowering T5 count floor 60-75 NOT scientifically defensible (statistical power minimum, не operator default)
- Even с T5 lowered, t_stat (S17 2.13, S22 1.04) + acceptance_gate failures persist
- If pursued anyway → must be documented as post-observation amendment с explicit acknowledgment subsequent performance не independently confirmed under original spec

## USER FINAL DECISION (autonomous mode default = E pause)

Per user directive "пусть выберут" — agents converged Option (E) project pause.

**Default action (autonomous):** Document verdicts в backlog, no new sprint created, no spec amendment, no code changes. Project state remains at v0.5 honest close marker (`v0.1.0-alpha.23`).

**ESC-1 surface к user:** Operator decides pause vs scope expansion at any future point. No sprint commitment from S24.

Если operator chooses (b) scope expansion → S24 becomes ADR 0039 (MVP scope amendment) + ADR 0016 amendment + multi-symbol re-measurement sprint (S15 infrastructure reused).

Если operator confirms pause → S24 = backlog-only docs (this file), project freeze at v0.5 honest close marker.

## Related

- [[decisions/0038-sprint-23-honest-close-v05]] — v0.5 honest close + v0.6 options
- [[decisions/0037-sprint-22-4h-test]] — S22 4H regime-independent
- [[decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal
- [[sprints/sprint-23-honest-close-v05]] — S23 v0.5 honest close
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable per current ADR pattern; option F-i would amend)
- [[decisions/0016-bybit-spot-supersedes-binance]] — BTC-only constraint (option F-ii would amend)

## Related

- [[decisions/0038-sprint-23-honest-close-v05]] — v0.5 honest close + v0.6 options A-F enumerated
- [[decisions/0037-sprint-22-4h-test]] — S22 4H test (regime-independent edge confirmed)
- [[decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence
- [[sprints/sprint-23-honest-close-v05]] — S23 v0.5 honest close (predecessor)
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable per current ADR pattern, but spec amendment IS option F)
