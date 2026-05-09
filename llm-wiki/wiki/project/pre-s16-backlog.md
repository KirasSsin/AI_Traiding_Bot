---
title: Pre-S16 backlog — direction decision after S15 FAIL (T5 reached, edge absent)
type: backlog
tags: [sprint-16, brainstorm, phase-2, verdicts, trader-expert, architecture-reviewer, post-s15-direction]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0030-sprint-15-mean-reversion-multi-symbol.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/decisions/0029-sprint-14-honest-close.md
---

# Pre-S16 backlog — direction decision

## Context (post-S15)

S15 shipped (PR #23, tag `v0.1.0-alpha.15`). Verdict: **FAIL** but key progress — T5 ≥100 floor REACHED for first time (108 trades aggregate via mean-reversion × 3 symbols).

**Per-symbol S15:**
- BTCUSDT: 44 trades, sharpe ratio mean +1.75, MC p 0.197 (best)
- ETHUSDT: 29 trades, sharpe ratio mean -39.35, MC p 0.998 (one catastrophic fold)
- SOLUSDT: 35 trades, sharpe ratio mean +0.45, MC p 0.65

**Aggregate S15:** T1=9.32 PASS / T2=29.55 PASS / T3=0.053 PASS / T4 win 37%/RR 2.27 PASS / T5 n=108 PASS на count BUT t_stat 1.04<2.0 FAIL / T6 mean -12.38 FAIL / MC p 0.998 FAIL / DSR 0 (n_trials=2, sigma_SR=22.68 cross-trial).

**N_trials accumulator:** S13 -44.46 + S15 -12.38 = 2 trials. Любой S16 measurement = trial 3.

**Critical:** ETH outlier fold sharpe -188 пулил mean negative. SOL также contributes variance. Strategy genuine failure mode = high-variance + MC random-equivalent (p 0.998).

## S16 PHASE 2 brainstorming question (1 question — direction choice)

### Q1 — Operator direction post-S15 FAIL

**Question:** Какое направление для S16 наиболее обоснованно с учётом 2 trials FAIL anchor (S13 -44.46 + S15 -12.38) + S15 evidence (T5 reached but no edge)?

**Maintainer recommended option:** (D) Honest close v0.2 — 2 strategy hypotheses tested both FAIL, evidence base dla "no edge in v0.1 framework" sufficient.

**Alternatives considered:**

- (a) **(B') S15 retry с broader RSI thresholds** (30/70 → 35/65) + variance cap (drop fold if sharpe < -10). Pros: addresses high-variance failure mode. Cons: N_trials=3 → DSR sigma_SR penalty even harsher с -44.46 anchor; broader thresholds = more noise = same edge problem.
- (b) **(C) Q3 15M timeframe** (per S15 backlog Q3 deferred). 4x signal frequency. Architecture blockers known: `interval_map` extension в `rest.py:66-67` + `heal_max_age_seconds` semantic refactor в `config.py:97-102` (production safety bug при 15M). Cost: 2 sprints. Pros: noise может быть OK для mean-reversion (less trend-bias); statistical power increases. Cons: noise может ухудшить edge (Hudson & Urquhart 2021 mean-reversion better at 1H+).
- (c) **(D) Honest close v0.2** (recommended). Pros: 2 trials FAIL = sufficient evidence; saves 1-3 sprints; preserves all infrastructure; v0.3 reset с fresh strategy hypothesis (e.g. ML, regime-switch) gets clean N_trials=1 anchor. Cons: stops short of exhausting v0.2 retry options.
- (d) **(E) Q4 ML XGBoost** (per S15 ADR 0030 deferred к v0.3+). Pros: addresses signal-quality root cause. Cons: 5-10 sprints scope, requires CPCV infrastructure, S15 evidence MC p=0.998 = no partial signal → ML has nothing к learn from. NOT recommended per S15 evidence.

**Reasoning for recommended (D):**

- 2 strategy families tested across 5y data (EMA crossover S13 + mean-reversion S15) — both FAIL
- DSR cross-trial sigma_SR = 22.68 with -44.46 anchor → any S16 measurement requires Sharpe > +20 just к compensate penalty (unrealistic for 1H crypto)
- S15 MC p 0.998 = strategy indistinguishable from random — base hypothesis (mean-reversion на 1H crypto) empirically rejected
- B' и C add complexity без addressing root cause (high-variance + no edge)
- Honest close v0.2 ≠ project death — preserves infrastructure для future strategy candidates с fresh N_trials anchor (v0.3 reset DSR baseline)
- ADR 0029 (S14 honest close) precedent — operator-driven direction, no commitment

**Risk/concern:**

- Operator regret ("what if 15M would work?") — mitigation: document Q3 architectural blockers preserved для future revival
- "Stopping too early" — counter: 2 trials × 5y = ~150K bars total examined. EMA crossover + mean-reversion = 2 distinct families. Sufficient evidence base
- Sunk cost fallacy: 17 sprints infrastructure ≠ requirement к keep retrying same framework
- HIDDEN: B' may be tempting because cheap. Counter: cheap ≠ informative. N_trials=3 anchor poisons future DSR for any v0.2 retry

## ROUND 1 verdicts (TRADER-EXPERT, complete)

| # | Question | ROUND 1 verdict | Type | Architecture-reviewer needed? | Final accepted |
|---|----------|-----------------|------|-------------------------------|----------------|
| Q1 | S16 direction post-S15 FAIL | **CONFIRM** | maintainer rec (D) accepted | NO (option C rejected) | (D) Honest close v0.2 |

## Trader rationale (verbatim summary)

1. **DSR cross-trial math makes B' и C structurally futile**. sigma_SR=22.68 с -44.46 anchor → expected max Sharpe gate ≈ +21.5 для n_trials=3. Не achievable на 1H crypto.
2. **BTC +1.75 signal noted** — единственный positive direction в проекте, но p=0.197 не passes 0.05 MC gate; 9 trades/fold = unreliable t-stat. Institutional knowledge для v0.3, не decision-reversing для S16.
3. **ETH fold -188.65** = data pathology (2021-2022 vol window), но MC p=0.998 на full distribution → strategy random-equivalent regardless.
4. **Option C (15M)**: 2 sprints architectural blockers (interval_map + heal_max_age) для academically weaker test (Hudson & Urquhart 2021: mean-reversion degrades sub-hourly).
5. **Option D breaks DSR accumulation cleanly** + preserves v0.3 optionality. Per Bailey 2014 eq. 13, N_trials counts per hypothesis — new v0.3 hypothesis resets `cross_trial_sharpes.json`.
6. **Precedent ADR 0029 + evidence base sufficient**: 2 families × 5y × proper WFA+DSR+MC pipeline.

## Cross-cutting concerns (trader-flagged)

- **CC1** — BTC +1.75 signal = institutional knowledge для v0.3. ADR 0031 must document: "future v0.3 hypothesis: BTC-only mean-reversion isolated from multi-symbol aggregation."
- **CC2** — `cross_trial_sharpes.json` reset semantics: v0.3 new hypothesis archives current к `data/cross_trial_sharpes_v0.2.json` + starts fresh empty. Without this policy, future sprint inherits -44.46 anchor → impossible DSR gate. MUST state в ADR 0031.
- **CC3** — ETH outlier fold flagged в ADR 0031 (one sentence) к prevent future misattribution.

## Escalation list для user

**ESC-1 (informational, не blocker):** Whether/when v0.3 starts + hypothesis selection. Engineering rec if pursued: fresh cross_trial log + single-symbol BTC mean-reversion (strongest observed signal) + ML deferred until simpler strategy shows partial edge first.

## Architecture-reviewer dispatch — SKIPPED

Option (b) C (15M) rejected by trader. No architecture verdict needed. PHASE 2 complete.

## USER FINAL DECISION (autonomous mode per directive "пусть агенты сами и решат")

S16 = v0.2 honest close (Option D). Documentation only — NO code changes. Pattern mirrors S14 (ADR 0029).

**S16 deliverables:**
- T1 ADR 0031 (v0.2 honest close)
- T2 sprint-16-honest-close-v02.md
- T3 wiki sync (current-state, index, log)
- T4 SPRINT_STATE → between-sprints
- T5 PHASE 8 ship (tag v0.1.0-alpha.16)
- T6 cross_trial_sharpes archival policy: `data/cross_trial_sharpes.json` → `data/cross_trial_sharpes_v0.2.json` + reset к `[]` для v0.3 readiness

## Related

- [[decisions/0030-sprint-15-mean-reversion-multi-symbol]] — S15 ADR (mean-reversion, multi-symbol)
- [[sprints/sprint-15-mean-reversion-multi-symbol]] — S15 sprint page (verdict + per-symbol)
- [[decisions/0029-sprint-14-honest-close]] — S14 honest close precedent
- [[decisions/0031-sprint-16-honest-close-v02]] — Sprint 16 ADR
- [[sprints/sprint-16-honest-close-v02]] — Sprint 16 page
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
