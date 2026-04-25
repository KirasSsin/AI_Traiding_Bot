---
title: Pre-S14 backlog — pre-registered tuning experiment
type: backlog
tags: [sprint-14, brainstorm, phase-2, verdicts, trader-expert, tuning, pre-registration, n-trials]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0028-sprint-13-strategy-validation.md
  - project/sprints/sprint-13-backfill-wfa.md
  - project/architecture/acceptance-criteria.md
---

# Pre-S14 backlog — Pre-registered tuning experiment

## Context (post-S13 verdict)

S13 shipped (PR #21, tag `v0.1.0-alpha.13`). Verdict: **FAIL** (4/6 criteria — t1=-44.46, t2=-101.38, t4 win=30%@RR=0.797, t5 n_trades=20 < 100). Critical insight: strategy fires ~1 trade per 10 days regardless of data span. Mean expectancy = -0.46 (no edge).

User chose **Option A** (pre-registered tuning) → если still FAIL → **Option B** (honest close).

Per Q7-S13 trader REVISE (originally rejected by user): pre-commit framework now ACCEPTED in spirit:
- S14 = exactly 1 tuning iteration
- Parameters pre-registered BEFORE measurement (no look-ahead через researcher)
- N_trials=2 (DSR multi-testing penalty applies)
- If FAIL again → S15 = honest close (Option B), no further tuning

## S14 PHASE 2 brainstorming questions (5 questions)

### Q1 — Tuning parameter set (pre-registration)

**Question:** Which strategy parameters tighten для +signal frequency? Pre-register exact values BEFORE measurement.

**Maintainer recommended option:** Moderate tightening across 4 dimensions:
- EMA fast: 12 → **9**
- EMA slow: 26 → **21**
- ADX threshold: 25 → **20**
- RSI bounds: 30/70 → **35/65** (wider entry zone)

**Alternatives considered:**
- (a) **Moderate (recommended)** — 4 param changes, each ~25-30% adjustment
- (b) Aggressive (5/13 EMA, ADX 15, RSI 40/60) — fewer signals filtered → much higher trade frequency, но risk over-optimizing для noise
- (c) Single-param (only EMA 9/21) — minimal change, может not enough к flip verdict
- (d) Different filter family (replace ADX с ATR-band breakout) — major scope, не "tuning" anymore

**Reasoning for recommended:**
- 9/21 EMA = standard short-term combination (Fibonacci-derived, не arbitrary)
- ADX 20 = standard "weak trend" threshold (vs 25 = "moderate trend")
- RSI 35/65 = wider but still oversold/overbought (not extreme 30/70)
- 4 dimensions changed = одна "experimental variant", не parameter sweep

**Risk/concern:**
- Bigger changes = more trades, но statistically same edge if base strategy has none
- 4 simultaneous changes = harder к attribute которое helped (если PASS)
- Multi-testing penalty per Bailey 2014: 4 changes × current N=1 → effective N_trials may be > 2

---

### Q2 — N_trials accounting

**Question:** S13 measurement = N_trials=1. S14 re-measurement с new params = N_trials=2 (per CC1)? OR higher (4 simultaneous param changes count separately)?

**Maintainer recommended option:** N_trials=2 (one re-measurement event), not 4×.

**Alternatives considered:**
- (a) **N_trials=2** (one experimental variant, despite 4 param changes) — DSR sigma_sr penalty applies
- (b) N_trials=5 (S13 baseline + 4 individual param changes counted separately) — strict interpretation, harsher DSR penalty
- (c) N_trials=2 для DSR + report 4-param-change context separately

**Reasoning for recommended:**
- Trader-expert practice: each "measurement event" = N_trials++, не each param dimension
- Bailey & López de Prado eq. 13: N_trials counts distinct strategy variants tested, не parameter dimensions per variant
- DSR sigma_sr requires cross-trial Sharpe std — only available для 2 actual measurements

**Risk/concern:**
- Conservative interpretation (b) might be more honest, но penalty may be too harsh для n=20-30 sample
- HIDDEN: future S15+ tuning attempts (если operator tries despite Option B commitment) further increment N_trials

---

### Q3 — PASS verdict semantics при borderline result

**Question:** Если S14 measurement returns T1=1.05, DSR=0.01 (just-above-threshold) — declare PASS OR escalate as "borderline, operator decides"?

**Maintainer recommended option:** Strict PASS = ALL T1-T6 green AND DSR > 0 (formula-based, no operator override). Borderline still PASS technically.

**Alternatives considered:**
- (a) **Strict formula PASS** (recommended) — no operator subjective override
- (b) Borderline-amber zone: T1 < 1.2, T2 < 2.0, DSR < 0.1 → escalate к operator review
- (c) Per-criterion margin requirement (e.g. T1 ≥ 1.1 for "true PASS")

**Reasoning for recommended:**
- Avoid operator confirmation bias на borderline numbers
- Acceptance criteria thresholds = formula, not negotiable
- Per S13 Q7 ESC-1=c defer pattern: operator decides next steps regardless (Mainnet pilot vs other) — borderline PASS still gets human eyeball

**Risk/concern:**
- Strict formula може PASS strategy that's actually no-edge с lucky variance
- Mitigation: even on PASS, S15 Mainnet pilot Phase 1 = 1% capital — risk bounded

---

### Q4 — Strategy parameter wiring

**Question:** Where к store new params? Hardcode в `src/signalgen/strategy.py` defaults OR config-driven via `Settings`?

**Maintainer recommended option:** Config-driven via existing `Settings` fields (already supported per S11 `_cmd_run` wiring).

**Alternatives considered:**
- (a) **Config-driven via Settings** (recommended) — values в Settings defaults OR `.env`. Strategy unchanged.
- (b) Hardcode strategy defaults — simpler но overrides per-symbol future flexibility
- (c) New strategy class variant `EmaCrossoverAdxRsiStrategyTuned(EmaCrossoverAdxRsiStrategy)` — overengineering

**Reasoning for recommended:**
- Settings already has `strategy_ema_fast`, `strategy_ema_slow`, `strategy_adx_threshold`, `strategy_rsi_oversold`, `strategy_rsi_overbought` (per S11 verification)
- Defaults change в `Settings` field definitions OR runtime override via `.env`
- Reverts trivially (revert Settings defaults change)
- Same code path tested S13

**Risk/concern:**
- Settings default change = silent behavioral shift (need explicit migration note в commit)
- Existing tests с old defaults may break — verify

---

### Q5 — FAIL fallthrough к Option B (honest close)

**Question:** Если S14 verdict FAIL, S15 = honest close ship. Pre-commit это сейчас (binding) OR re-confirm после S14 measurement?

**Maintainer recommended option:** Pre-commit now per user verbatim "Option A → если still FAIL → Option B". Binding.

**Alternatives considered:**
- (a) **Pre-commit Option B fallthrough** (recommended) — binding, no further tuning iterations
- (b) Defer decision к S15 brainstorm — repeats earlier ESC-1=c pattern
- (c) Allow 1 more tuning iter (N_trials=3) — violates user's "Option A → if FAIL → Option B" framework

**Reasoning for recommended:**
- User explicit: "Option A → если still FAIL → Option B" = commitment
- Bounded multi-testing discipline (max N_trials=2 на same dataset)
- Avoid unbounded p-hacking iteration trap

**Risk/concern:**
- Operator regret if S14 FAIL (e.g. "what if I'd tried 5/13 EMA?")
- Mitigation: document considered alternatives (Q1 option b) with rationale why moderate chosen

---

## ROUND 1 verdicts (TRADER-EXPERT, complete)

**Maintainer source-claim verification (CC1 lesson):**
- ✅ Q1 trader frequency math VERIFIED via grep: S13 measured 20 OOS trades / 2500 OOS bars = 1 trade per 5.2 days. T5 ≥100 requires 1 trade per 25 bars (~1/day). 5x increase needed; tuning realistically 2-3x. T5 structurally unreachable confirmed.
- ✅ Q1 RSI semantic verified: `strategy.py:128` `not_overbought = rsi < overbought`. My "35/65 wider" was BACKWARDS — 65 < 70 = MORE restrictive (fewer LONG entries). True wider would need higher overbought (75+).
- ✅ Q2 sigma_SR gap verified: `dsr.py:73` says "std([fold_sharpe_1, ..., fold_sharpe_K])" = cross-FOLD only. N_trials=2 needs cross-TRIAL implementation (Bailey eq. 13). Real engineering gap.

| # | Question | ROUND 1 verdict | Type | Final accepted | Wiki/code follow-ups |
|---|----------|-----------------|------|----------------|----------------------|
| Q1 | Tuning parameter set | **EXPAND** | T5 mathematically unreachable + RSI semantic error | Question moot — invalidated by trader's structural impossibility argument. **OPTION B (honest close) chosen** — see USER FINAL DECISION below | acceptance-criteria.md may need T5 floor calibration note (S14+) |
| Q2 | N_trials accounting | **REVISE** | DSR cross-trial sigma_SR not implemented | Moot — Option B skips re-measurement. Documented as deferred S15+ if any future revision attempt | dsr.py cross-trial sigma_SR implementation deferred |
| Q3 | PASS verdict semantics | **CONFIRM** | agree | Strict formula PASS, no operator override | — |
| Q4 | Strategy parameter wiring | **CONFIRM** | agree | Settings config (S11 supports) — moot per Option B | — |
| Q5 | FAIL fallthrough к Option B | **CONFIRM** | agree | Pre-commit binding | Honored — Option B invoked directly w/o S14 measurement |

## Cross-cutting concerns (trader-flagged)

- **CC1 (Q1+Q2 conjoint):** T5 unreachability + DSR cross-trial gap = double-blocker для Option A. Option A would produce theatrical FAIL re-measurement без statistical meaning. Skip к Option B saves 1 sprint cycle.

## USER FINAL DECISION (binding, post-trader verdicts)

**User direction (verbatim):** "Продолжаем тогда (B) Honest close immediately."

**Decision:** Option B accepted. S14 = honest close ship.

**Rationale (per user):**
- Trader's Q1 EXPAND = strong evidence T5 structurally unreachable (5x signal frequency gap)
- Option A pre-commit framework was designed assuming tuning could flip verdict — but trader's math shows tuning won't reach T5 floor
- Saves 1 sprint vs (A)
- Same end-state (Option B) but skips theatrical FAIL re-measurement

## Escalation list для user

NONE — user already authorized Option B per pre-commit framework S13 ESC-1=c "defer + decide case-by-case after seeing data". Numbers seen, decision made.

## Maintainer follow-ups (post-verdict)

- ✅ Verify trader Q1+Q2 source claims via grep (CC1)
- ✅ Surface trader concerns + Option B recommendation к user
- ✅ User confirmed Option B
- ⏳ Draft ADR 0029 (S14 = honest close, no edge verdict, project status update)
- ⏳ Sprint page + wiki sync + PHASE 8 ship

## Related

- [[decisions/0028-sprint-13-strategy-validation]] — S13 ADR (verdict FAIL trigger)
- [[sprints/sprint-13-backfill-wfa]] — S13 measurement results
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
