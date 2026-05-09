---
title: 0031. Sprint 16 — v0.2 honest close (2 strategy families tested both FAIL)
type: decision
date: 2026-04-26
sprint: 16
tags: [adr, sprint-16, honest-close-v02, no-edge, mvp-incomplete, n-trials-archival, v0.3-readiness]
sources:
  - project/pre-s16-backlog.md
  - project/decisions/0030-sprint-15-mean-reversion-multi-symbol.md
  - project/decisions/0029-sprint-14-honest-close.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0031. Sprint 16 — v0.2 honest close (2 strategy families tested both FAIL)

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S15 shipped (PR #23, tag `v0.1.0-alpha.15`). Verdict FAIL but T5 ≥100 trades floor REACHED for first time (108 trades aggregate via mean-reversion × 3 symbols BTC/ETH/SOL на 1H Bybit Spot). ADR 0030 multi-symbol aggregation hypothesis VALIDATED — strategy still no measurable edge (MC p=0.998 = random-equivalent).

S16 PHASE 2 brainstorming — single direction question delegated к trader-expert per user directive ("пусть агенты сами и решат"):

**Q1 trader-expert ROUND 1 verdict: CONFIRM (D) Honest close v0.2.**

Trader rationale (verified via grep + s15_wfa_result.json + cross_trial_sharpes.json):

1. **DSR cross-trial math**: sigma_SR=22.681 с -44.46 anchor. Bailey 2014 expected max Sharpe gate ≈ +21.5 для n_trials=3. Не achievable на 1H crypto. B' и C structurally futile.
2. **BTC +1.75 signal**: единственный positive direction в проекте — но p=0.197 не passes 0.05 MC gate; 9 trades/fold = unreliable t-stat. Institutional knowledge для v0.3, не decision-reversing для S16.
3. **ETH fold -188.65**: data pathology (extreme vol window 2021-2022), но MC p=0.998 на full distribution = strategy random-equivalent regardless.
4. **Option C (15M)**: 2 sprints architectural blockers (interval_map в `rest.py:66-67` + heal_max_age в `config.py:97-102` production safety bug) для academically weaker test (Hudson & Urquhart 2021: mean-reversion degrades sub-hourly).
5. **Option D breaks DSR accumulation cleanly + preserves v0.3 optionality**: Bailey 2014 N_trials per hypothesis (не per framework instance) → v0.3 fresh-start resets cross_trial baseline.
6. **Evidence base sufficient**: 2 strategy families × 5y data × proper WFA+DSR+MC pipeline.

## Решение

### S16 scope: v0.2 honest close ship

**v0.2 status declaration:**

- **Infrastructure: COMPLETE** (16 FSM states + 30 events + 74 transitions + 45 reason codes + 38 component pages + 30 ADRs (31 с этим) + 16 sprint pages (17 с этим) + WFA + DSR + MC + cross-trial log + multi-symbol CLI + 2 strategy families wired)
- **Strategy validation: NEGATIVE × 2 hypotheses** —
  1. **EMA(12)×EMA(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT (S13)**: 20 OOS trades, T1=-44.46, all 4 critical T-criteria FAIL (T1+T2+T4+T5)
  2. **Mean-reversion RSI(14)<30 AND close<lower_BB(20, 2σ) на 1H × 3 symbols BTC+ETH+SOL (S15)**: 108 OOS trades aggregate (T5 floor REACHED), но T6 mean -12.38 / MC p 0.998 / DSR 0 — FAIL
- **MVP DONE per acceptance-criteria.md: NOT achieved** (T5 reached в S15 но T1+T6+MC+DSR fail; S13 had multi-criteria fail)
- **Mainnet exposure: 0** (Bybit demo 33min only, no live trading)
- **Tag: `v0.1.0-alpha.16`** = v0.2 honest close marker, NOT MVP DONE

### S16 deliverables

**T1: ADR 0031 (this document)** — accepted, status final.

**T2: sprint-16-honest-close-v02 page** — canonical v0.2 close summary с:
- Final v0.2 status declaration (2 strategy families both FAIL)
- Empirical results trail (S13 + S15 measurements aggregated)
- BTC +1.75 signal noted (institutional knowledge для v0.3, не decision-reversing)
- ETH fold -188.65 flagged как data pathology
- Cross-trial log archival policy
- All carry-overs preserved

**T3: Wiki sync** — current-state.md + index.md updated к "v0.2 closed honest" + counts (ADR 30→31, sprint pages 17→18).

**T4: log.md sprint-end entry** — chronological closure event.

**T5: SPRINT_STATE → between-sprints с post-v0.2-honest-close status** — operator decides v0.3 future direction.

**T6: cross_trial_sharpes archival**:
```bash
mv data/cross_trial_sharpes.json data/cross_trial_sharpes_v0.2.json
echo '{"trials": []}' > data/cross_trial_sharpes.json  # v0.3 fresh baseline
```

**T7: PHASE 8 ship** — sprint-finish: tag `v0.1.0-alpha.16` (v0.2 honest close marker).

### NO new code, NO measurement re-run

Per Option D framework + S14 ADR 0029 precedent: skip theatrical re-measurement. All deliverables = documentation + archival policy. Q7-S12 zero-migration constraint preserved trivially.

### Cross-cutting concerns (binding)

- **CC1 (BTC institutional knowledge):** BTC-only mean-reversion (single-symbol, isolated from ETH/SOL noise) = strongest observed signal в проекте (sharpe ratio mean +1.75, MC p 0.197). Future v0.3 hypothesis worth testing с fresh trial counter. Documented в sprint-16 page "Open issues for v0.3+" + ADR 0031.

- **CC2 (cross_trial_sharpes archival policy — BINDING):** N_trials per hypothesis (Bailey 2014 eq. 13), не per framework. v0.3 starting fresh hypothesis (e.g. ML, regime-switch, BTC-only mean-reversion с different entry logic) MUST:
  1. Archive current `data/cross_trial_sharpes.json` (containing `[-44.46, -12.384]`) к `data/cross_trial_sharpes_v0.2.json`
  2. Reset `data/cross_trial_sharpes.json` к `{"trials": []}`
  3. New v0.3 N_trials counter starts at 0 (first measurement = trial #1)
  4. Без этого policy, future sprint inherits -44.46 anchor → impossible DSR gate (sigma_SR penalty severe)
  Implemented в S16 T6.

- **CC3 (ETH fold pathology):** S15 ETHUSDT fold sharpe -188.65 = data pathology (likely extreme vol window 2021-2022). NOT strategy-attributable failure — MC p=0.998 на full distribution = random-equivalent regardless. Future developers reading S15 results should understand aggregate FAIL = genuine, не outlier-artifact.

- **CC4 (Tag semantics):** `v0.1.0-alpha.16` = v0.2 honest close marker, NOT MVP DONE. v0.1.0 (drop alpha) reserved для actual T1-T6 PASS achievement (not currently feasible per N_trials=2 DSR penalty).

- **CC5 (No spec amendment):** acceptance-criteria.md NOT modified. T1-T6 thresholds stand. v0.2 honest close acknowledges thresholds не met для chosen strategies + timeframe + venue.

- **CC6 (Q3 15M blockers preserved):** Architecture-reviewer findings от S15 brainstorm preserved для potential future revival:
  - `src/marketdata/bybit/rest.py:66-67` `interval_map={"60":"1h"}` KeyError on "15"
  - `src/platform/config.py:97-102` `heal_max_age_seconds=3600` semantic refactor needed (production safety bug at 15M)
  - `src/__main__.py:131,191,205,335` hardcoded "60" / "_1h.parquet"
  Documented в sprint-16 page Open Issues.

### Future direction options (deferred к operator)

Per trader ESC-1 (informational, not blocker):

**(v0.3-A) BTC-only mean-reversion fresh start** — strongest observed signal (S15 BTC +1.75 / p 0.197), isolated от ETH/SOL noise. Single-symbol. Fresh `cross_trial_sharpes.json`. Cost: 1-2 sprints.

**(v0.3-B) Regime-switch (HMM detection on volatility)** — context layer + market regime filter. Cost: 3-5 sprints (HMM training pipeline new).

**(v0.3-C) ML-driven (XGBoost classifier)** — per ADR 0030 deferred. NOT recommended per S15 evidence (MC p=0.998 = no partial signal для ML к learn). Defer until simpler v0.3 strategy demonstrates partial edge first.

**(v0.3-D) Different timeframe (15M / 4H)** — Q3 architectural blockers documented. 15M = noisier (mean-reversion degrades sub-hourly per Hudson & Urquhart 2021). 4H = lower frequency но cleaner trend signals. Cost: 2 sprints (1 architectural + 1 measurement).

**(v0.3-E) Project pause** — close current branch, freeze repo as "v0.2 honest close marker — infrastructure complete, 2 strategies tested negative". Reactivate if new candidate emerges.

**Operator decides if/when. No commitment from S16.**

## Последствия

**Plus:**
- Honest closure based on 2 empirical measurements (S13 -44.46 + S15 -12.38 OOS Sharpe)
- 17 sprints infrastructure preserved + reusable для future strategy attempts
- DSR cross-trial accumulator broken cleanly via archival policy → v0.3 fresh start possible
- BTC institutional knowledge documented for future BTC-only retry
- Avoids p-hacking trap (per Bailey 2014 multi-testing penalty)
- 0 capital exposure (no Mainnet trading)
- Pattern reuse от S14 ADR 0029 (proven honest close framework)

**Minus:**
- "MVP DONE" не achieved per acceptance-criteria.md spec (no spec amendment)
- 2 strategy hypotheses (EMA crossover + mean-reversion) empirically rejected на 1H Bybit Spot
- All S12+S13+S14+S15 carry-overs unaddressed (10+ items remain open)
- No live trading validation beyond 33min S12 demo
- Q3 15M architectural fixes deferred (interval_map, heal_max_age)

**v0.3+ carry-overs preserved (anticipated):**

All previous + new from S15:
- F live demo Mainnet validation actual run (operator-driven, not run since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)
- 48h Bybit demo validation (operator-driven)
- Q3 15M architectural blockers (interval_map + heal_max_age — preserved per CC6)
- Multi-symbol live runtime fan-out (S15 deferred — `_cmd_run` kept single-symbol)
- Capital allocation cross-symbol exposure caps (S15 deferred — natural per-symbol Kelly was sufficient for measurement)
- Strategy revision OR pivot decision (per v0.3 options A/B/C/D/E — operator-driven)

## Связанные документы

- [[../pre-s16-backlog]] — PHASE 2 verdict (trader CONFIRM Option D)
- [[0030-sprint-15-mean-reversion-multi-symbol]] — S15 ADR (mean-reversion + multi-symbol)
- [[0029-sprint-14-honest-close]] — S14 honest close (precedent pattern)
- [[0028-sprint-13-strategy-validation]] — S13 ADR (-44.46 anchor)
- [[../sprints/sprint-15-mean-reversion-multi-symbol]] — S15 measurement results
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, not amended)
- [[../sprints/sprint-16-honest-close-v02]] — спринт delivery record

## Поправки

- (none yet)
