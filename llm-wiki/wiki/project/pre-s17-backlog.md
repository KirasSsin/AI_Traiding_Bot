---
title: Pre-S17 backlog — BTC-only MVP retry, strategy hypothesis selection
type: backlog
tags: [sprint-17, brainstorm, phase-2, verdicts, trader-expert, btc-only-mvp, strategy-hypothesis-3]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0031-sprint-16-honest-close-v02.md
  - project/sprints/sprint-16-honest-close-v02.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/architecture/acceptance-criteria.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
---

# Pre-S17 backlog — BTC-only MVP retry, strategy hypothesis #3

## Context (post-S16)

S16 shipped (PR #24, tag `v0.1.0-alpha.16`). v0.2 closed honest. cross_trial_sharpes archived → fresh `[]` для new hypothesis (per Bailey 2014 N_trials per hypothesis).

**User clarification (2026-04-26):** "торговать будем в mvp только btc/usdt" — MVP scope = BTCUSDT only per ADR 0016 + ADR 0004 original. Multi-symbol = scope creep beyond MVP. v0.2 S15 ETH+SOL infrastructure preserved но не used для MVP measurement.

**User direction:** continue к MVP DONE с new strategy hypothesis. "пусть агенты сами и решат" — trader-expert decides direction.

## Constraints (BTC-only MVP)

- Single symbol BTCUSDT (per ADR 0016)
- 1H baseline timeframe (per ADR 0005, не amended)
- Bybit Spot venue (per ADR 0016)
- N_trials counter fresh (cross_trial_sharpes.json reset к [])
- Acceptance criteria T1-T6 + DSR + PBO (PBO deferred per ADR 0028 footnote 3)
- T5 ≥100 trades floor harder для single-symbol (S15 BTC alone = 44 trades / 5 folds — well below 100)

## S17 PHASE 2 brainstorming question (1 question — strategy hypothesis selection)

### Q1 — Next strategy hypothesis для BTC-only MVP retry

**Question:** Какая 3-я strategy hypothesis (после EMA crossover S13 + mean-reversion RSI+BB S15) наиболее вероятно даст T5≥100 trades + edge на BTC-only 1H Bybit Spot data (4.81y)?

**Maintainer recommended option:** (a) BTC-only mean-reversion с relaxed thresholds (RSI 35/65 + BB(20, 1.5σ)) + variance cap — fold sharpe < -10 dropped from aggregate per S15 ETH outlier lesson.

**Alternatives considered:**

- (a) **BTC-only mean-reversion relaxed** (recommended) — RSI 35/65 (wider zone) + BB k=1.5 (tighter bands = more breaches) + variance cap. Reuses S15 infrastructure (MeanReversionRsiBBStrategy + indicators.py mean_reversion branch + BB indicator). Pre-registered binding. Cost: 1 sprint (parameter tuning + variance cap implementation + measurement). Risk: relaxed thresholds = more noise, может ухудшить edge.

- (b) **Regime-switch (ATR-based volatility filter)** — добавить ATR percentile filter поверх mean-reversion: trade only when ATR(14) percentile [20, 80] (moderate vol, не extreme). Filters ETH-style outlier folds. Reuses RSI+BB + ATR indicator (already implemented). Cost: 1-2 sprints (regime detection + WFA). Risk: ATR filter может снизить trade count ниже T5 floor.

- (c) **Donchian channels breakout** (different family) — long when close > high(20-bar window) + ATR-based stop. Trend-following вместо mean-reversion. Reuses ATR. Pure NEW strategy class. Cost: 2 sprints (strategy implementation + indicators.py donchian branch + measurement). Risk: trend-following на 1H BTC = similar low frequency как S13 EMA crossover (T5 unreachable risk).

- (d) **Multi-timeframe (15M signal + 1H regime context)** — Q3 deferred from S15. Architectural blockers preserved: interval_map + heal_max_age (production safety). Cost: 2 sprints minimum (1 architecture + 1 measurement). Risk: 15M noisier per Hudson & Urquhart 2021.

- (e) **Honest close v0.1 (project complete)** — accept 2 strategy families failed + BTC-only constraint makes 3rd attempt structurally hard к hit T5 conjoint. Freeze repo as "v0.1 infrastructure complete + 2 strategy hypotheses tested negative". Cost: 0 sprints docs.

**Reasoning for recommended (a):**

- S15 BTCUSDT alone: 44 trades / 5 folds, sharpe ratio mean +1.75, MC p 0.197 — strongest signal observed (per S16 ADR 0031 CC1 institutional knowledge)
- Relaxed RSI 35/65 + BB k=1.5 = ~2-3x trade frequency (estimate ~90-130 BTC trades) — closer к T5 ≥100 floor on single-symbol
- Variance cap (drop fold sharpe < -10) addresses S15 high-variance failure mode (T6 mean -12.38 driven by outliers)
- Cheapest test (1 sprint, reuses infrastructure)
- Preserves DSR baseline (n_trials=1 fresh start per S16 CC2)
- Aligned с trader S16 v0.3-A recommendation
- Если PASS → MVP DONE (pending S1-S6 system-level criteria + Mainnet validation)
- Если FAIL → strong evidence для honest close v0.1

**Risk/concern:**

- Relaxed thresholds = more noise OS могут уменьшить edge per-trade (lower mean_pnl, lower t-stat)
- Variance cap = post-hoc filter = risk p-hacking. Mitigation: cap pre-registered с explicit threshold (sharpe < -10) before measurement
- Single-symbol BTC frequency limit: realistic max ~150 trades с relaxed thresholds; T5 floor 100 потенциально reached but borderline
- HIDDEN: BTC 1H mean-reversion academic prior (Hudson & Urquhart 2021) — actual edge может быть мал; relaxed thresholds amplify noise > signal
- N_trials=1 fresh DSR baseline = clean но if S17 FAIL, n_trials=2 with new (-44.46 not in chain) anchor is favorable for any S18 retry

## ROUND 1 verdicts (TRADER-EXPERT, complete)

| # | Question | ROUND 1 verdict | Type | Architecture-reviewer needed? | Final accepted |
|---|----------|-----------------|------|-------------------------------|----------------|
| Q1 | Next strategy hypothesis BTC-only MVP retry | **EXPAND → CONFIRM (a) с amendments** | (a) least-bad surviving option | NO | (a) BTC-only mean-reversion relaxed RSI 35/65 + BB(20, 1.5σ) + 3 amendments |

## Trader EXPAND analysis (verbatim summary)

**Frequency math (verified):**
- BTC S15 baseline: 44 trades / 2500 OOS bars = 1.76% signal rate
- BB(20, 1.5σ) one-sided tail = 3.34% vs 2σ = 2.27% → 1.47× raw
- RSI<35 vs RSI<30 → ~1.17× raw
- AND-gate joint multiplier (positive correlation between RSI extreme + BB breach) = 1.4-1.7× actual, NOT 2-3× independent
- **Expected BTC trades: 44 × 1.55 ≈ 68. Conservative 66, optimistic 88.** Maintainer's 90-130 estimate optimistic.
- **T5 floor 100 = uncertain to unreachable**

**Alternatives ruled out:**
- (b) ATR regime filter: definitionally frequency-reducing, не increasing → ≤44 trades, T5 certain FAIL
- (c) Donchian breakout: trend-following family → ~15-25 trades like S13 EMA, T5 structural FAIL
- (d) 15M multi-timeframe: 2 sprints architectural cost (interval_map + heal_max_age blockers per S16 CC6) + Hudson & Urquhart 2021 mean-reversion degrades sub-hourly
- (e) Honest close v0.1 NOW: premature — BTC +1.75 / p=0.197 strongest signal observed, fresh N_trials=1 baseline = clean DSR start, 1 sprint cheap, информationally valuable либо PASS либо 3rd negative result

**3 mandatory amendments к option (a):**

1. **Pre-register binding parameters:** RSI 35/65 + BB(20, 1.5σ) AND-gated. Same entry/exit logic как S15. NO tuning after seeing results.

2. **DROP variance cap -10 threshold.** Trader analysis: -10 was ETH-pathology-derived. BTC-only worst fold sharpe в S15 ≈ -7 — cap нечего к trigger. P-hacking red flag for external audit. Either DROP entirely (BTC-only doesn't need outlier protection) OR respecify principled formula `fold_sharpe < mean_IS - 2.5σ_IS`. Maintainer accepts: **DROP** (cleanest).

3. **T5 count failthrough clause:** If OOS trades < 100 → FAIL declared on T5 count alone, t_stat skipped, honest close v0.1 follows (3 hypotheses tested, documented). Clean binary: pass T5 floor → measure t_stat+DSR; fail T5 floor → close v0.1 с stronger evidence.

## Cross-cutting concerns (trader-flagged)

- **CC1** — T5 frequency gap = binding structural risk. Honest pre-registration must acknowledge T5 count may fail. ADR 0032 with failthrough as first-class outcome.
- **CC2** — Variance cap -10 = audit surface (reverse-engineered from S15 ETH). DROP per amendment.
- **CC3** — ATR regime filter (option b) definitionally unsuitable for sparse signal sets — document к prevent future re-proposal.
- **CC4** — Если S17 FAILS T5 → honest close v0.1 с 3 hypotheses tested = publishable-quality negative result. "Failure to find edge" ≠ project failure = scientific contribution.

## Escalation list для user

**ESC-1 (pre-registration binding):** RSI 35/65 + BB(20, 1.5σ) BINDING до S17 WFA run. Operator commitment, не engineering decision. **APPLIED autonomously per user directive "пусть агенты сами и решат"** — locked в ADR 0032.

**ESC-2 (T5 failthrough acceptance):** Если OOS trades < 100 → FAIL → honest close v0.1 (3 hypotheses tested). NO "tune one more time" pressure if T5 count is 80-99. **APPLIED autonomously per user directive** — locked в ADR 0032.

## Architecture-reviewer dispatch — SKIPPED

Option (d) multi-timeframe rejected by trader. NO architectural verdict needed.

## USER FINAL DECISION (autonomous mode per "пусть агенты сами и решат")

S17 = BTC-only mean-reversion relaxed (RSI 35/65 + BB(20, 1.5σ) AND-gated, NO variance cap, T5 failthrough binding).

**S17 deliverables:**
- T1 ADR 0032 (S17 strategy + 3 amendments + T5 failthrough clause)
- T2 indicators.py mean_reversion branch parameter wiring (RSI thresholds + BB k = configurable per cfg)
- T3 _run_wfa_single_symbol config update (RSI 35/65 + BB k=1.5)
- T4 measurement run BTC-only --symbol BTCUSDT (NOT --symbols)
- T5 ADR 0032 + sprint-17 page + wiki sync
- T6 PHASE 8 ship (tag v0.1.0-alpha.17)
  - If T5 PASS verdict → continue к S1-S6 system-level criteria
  - If T5 FAIL verdict → S18 = honest close v0.1 (sprint after S17)

## Related

- [[decisions/0031-sprint-16-honest-close-v02]] — S16 v0.2 honest close + CC1 BTC institutional knowledge + CC2 cross_trial archival policy
- [[sprints/sprint-15-mean-reversion-multi-symbol]] — S15 BTC alone signal observed
- [[sprints/sprint-16-honest-close-v02]] — S16 final v0.2 close + v0.3 options
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
- [[decisions/0016-bybit-spot-supersedes-binance]] — venue + BTC-only original scope
