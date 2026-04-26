---
title: Pre-S19 backlog — v0.4 direction selection (post-v0.1-FINAL-honest-close)
type: backlog
tags: [sprint-19, brainstorm, phase-2, verdicts, trader-expert, architecture-reviewer, v0.4-direction, post-v0.1-final]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0033-sprint-18-honest-close-v01.md
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/sprints/sprint-18-honest-close-v01.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
  - project/architecture/acceptance-criteria.md
---

# Pre-S19 backlog — v0.4 direction selection

## Context (post-S18 v0.1 FINAL honest close)

S18 shipped (PR #26, tag `v0.1.0-alpha.18`). v0.1 FINAL closed honest. 3 strategy hypotheses tested, all FAIL conjoint. **S17 partial signal preserved** (MC p=0.01 + DSR=1.0 + T1=25.99 на 59 BTC trades = institutional knowledge).

User constraint (BINDING per 2026-04-26): **MVP scope = BTCUSDT only**. Multi-symbol options out of MVP scope.

**User directive 2026-04-26:** "Зайди с этими вопросами в агентов трейдеров, пусть они проведут дискуссию и выберут" — trader-expert + architecture-reviewer joint discussion + verdict.

## S19 PHASE 2 brainstorming question (1 question — v0.4 direction)

### Q1 — v0.4 direction selection

**Question:** Какое v0.4 направление наиболее обоснованно с учётом S17 partial signal evidence + MVP BTC-only constraint + frequency structural limit (~60-70 BTC 1H mean-reversion trades / 4.81y max)?

**Maintainer recommended option:** (A) BTC 15M mean-reversion — STRONGEST viable per S17 evidence (4x frequency = T5 reachable estimate)

**5 options considered:**

- (a) **(v0.4-A) BTC 15M mean-reversion** — addresses frequency floor structural limit (4x = ~240 trades estimate). Q3 architectural blockers documented (interval_map в `rest.py:66-67` + heal_max_age в `config.py:97-102` production safety refactor). Cost: 2 sprints (1 architecture + 1 measurement). Risk: noise vs edge tradeoff (Hudson & Urquhart 2021 mean-reversion degrades sub-hourly).

- (b) **(v0.4-B) Hybrid mean-reversion + ML XGBoost filter** — S17 partial signal evidence (MC p=0.01) reverses ADR 0030 ML defer rationale ("no partial signal"). XGBoost classifier на BTC mean-reversion features. CPCV framework new infrastructure (purged combinatorial cross-validation per López de Prado AFML Ch.7). Cost: 5-10 sprints (feature engineering + model registry + monitoring + retraining cadence). Risk: complexity multiplier; ML-as-filter best когда base signal partial-edge (S17 confirmed).

- (c) **(v0.4-C) Multi-symbol revival** — out of MVP scope per user 2026-04-26 ("торговать будем в mvp только btc/usdt"). Reconsider post-MVP if MVP-DONE achieved on BTC-only first. S15 infrastructure preserved.

- (d) **(v0.4-D) Different timeframe — 4H** — lower frequency than 1H, не addresses T5 floor structural limit. НЕ recommended per S17 evidence (mean-reversion signal already weak в high-frequency regime).

- (e) **(v0.4-E) Project pause** — close current branch, freeze repo as "v0.1 FINAL honest close marker — infrastructure complete + 3 strategy hypotheses tested + 1 partial signal observed". Reactivate if новый candidate emerges. Cost: 0 sprints.

**Reasoning for recommended (A):**
- S17 evidence: mean-reversion regime works на BTC (MC p=0.01 stat-sig), failure mode = sample size only
- 15M = 4x frequency = ~240 trades estimate (T5 floor 100 reachable с margin)
- Reuses 100% S17 strategy infrastructure (MeanReversionRsiBBStrategy + cfg dispatch)
- Q3 architectural blockers known (2 specific files, ~1 sprint architectural fix)
- BTC-only constraint preserved (MVP scope honored)
- Fresh N_trials=1 baseline (S18 archival completed)
- 1 measurement sprint после architectural sprint = 2 sprints total к binary outcome (PASS/FAIL conjoint)
- Если PASS → MVP DONE strategy criteria → continue к S1-S6 system criteria + Mainnet pilot
- Если FAIL → 4 hypotheses tested, evidence base extended, operator decides v0.5

**Risk/concern:**
- 15M noise: mean-reversion edge может degrade per Hudson & Urquhart 2021. Counter-argument: S17 evidence показывает edge IS real на BTC mean-reversion, 15M may amplify both signal AND noise — empirical question
- 2 sprints cost: architectural fix + measurement. Counter: cheaper than ML XGBoost (5-10 sprints) и более direct test S17 hypothesis
- Production safety: `heal_max_age_seconds` semantic refactor required — нужен careful ADR + testing
- HIDDEN: Bybit Spot 15M historical data availability могут быть короче 1H. Verify before sprint commitment

## ROUND 1 verdicts (TRADER-EXPERT + ARCHITECTURE-REVIEWER, complete)

| # | Question | Trader verdict | Architecture verdict | Final accepted |
|---|----------|----------------|----------------------|----------------|
| Q1 | v0.4 direction selection | **EXPAND → CONFIRM (A) с 4 amendments** | **APPROVE_WITH_CONDITIONS (A) с 3 conditions** | (A) BTC 15M mean-reversion с **7 combined amendments** |

## Trader-expert verdict summary

**EXPAND structural reframe:**
1. S17 T1=25.99 / Sortino=4446 = small-sample artifacts (n=59) — NOT edge strength evidence
2. MC p=0.01 = real signal (permutation-based, not small-sample-fragile) — only valid claim
3. Fold concentration: fold #5 alone drives positive aggregate — does NOT improve at 15M (same calendar period)

**4 trader amendments BINDING:**
- T-Amendment 1: T5 floor 15M = raise к 150 OR add Lo 2002 autocorrelation-corrected t-stat (ESC-2)
- T-Amendment 2: Fold concentration pre-registration — if fold #5 is sole profitable fold = REGIME CONCENTRATION verdict
- T-Amendment 3: 15M data pre-condition — verify Bybit returns ≥150K bars (Day 1 check)
- T-Amendment 4: heal_max_age production safety = first-class ADR decision

**Trader rejected:**
- (B) ML XGBoost — DEFERRED к v0.5 (premature без 15M base signal confirmation)
- (C) multi-symbol — out of MVP scope per user
- (D) 4H — frequency direction wrong
- (E) pause — ESC-1 escalated (chosen autonomously: continue per S17 evidence + low cost)

## Architecture-reviewer verdict summary

**APPROVE_WITH_CONDITIONS (A) с 3 mandatory architecture conditions:**

- **Condition A1**: `rest.py:66-67` interval_map + interval_ms fix (~0.5 day, single-dict refactor)
- **Condition A2**: `config.py:97-102` heal_max_age semantic refactor → `heal_max_bars=1` (~1.5 days, ADR-level)
- **Condition A3 (HIGH)**: sqrt(8760) annualization parameterization (~1.5 days, 3 files: strategy_metrics.py:28 + wfa_reporter.py:25 + vector_backtest.py:64) — **CRITICAL**: 2× understimate Sharpe at 15M = false-FAIL risk на strategy с real edge

**Architecture concerns:**
- WFA params recalibration: test=500 bars at 15M = ~5.2 days per fold — quant-stats verdict needed (kept ADR 0014 defaults pending verdict)
- Bybit 15M data depth: Day 1 verify check
- DSR cross-trial gap (S14 Q2 5-sprint deferral): dormant если single-hypothesis test, activates если multi-sub-hypothesis

**Sprint scope (per architecture):**
- S19 (architectural): 5 tasks — interval_map + heal_max_bars + annualization param + WFA params ADR amendment + 15M backfill validation
- S20 (measurement): WFA 15M run + binary verdict
- **2 sprints total**

**Option (B) DEFER к v0.5** (5-7 sprints — premature без 15M base signal)

## Cross-cutting concerns (joint)

- **CC1 Annualization (HIGH)**: must resolve FIRST в S19 before measurement sprint
- **CC2 Bybit 15M data depth**: Day 1 verify — lowest-cost highest-risk check
- **CC3 heal_max_age operator migration**: silent wrong behavior at 15M — ADR must include migration notice
- **CC4 DSR cross-trial dormant** (single-hypothesis S19) — activate если multi-retry
- **CC5 rest.py dual-dict anti-pattern**: consolidate к single `INTERVALS` map в Condition A1 fix
- **CC6 Fold concentration**: 15M does NOT solve — pre-register check per T-Amendment 2

## ESC resolutions (autonomous mode per user "пусть они выберут")

**ESC-1 (continue vs pause):** **CONTINUE Option (A)** chosen
- Rationale: 2 sprints cheap (vs 5-10 для ML), S17 evidence justifies test, MC p=0.01 first genuine signal в проекте, frequency hypothesis directly testable

**ESC-2 (T5 floor 15M):** **Option (i) — raise к 150 trades** chosen
- Rationale: simpler implementation than autocorrelation-corrected t-stat, scales appropriately с frequency, T5 floor 150 = ~31 trades/year (vs S13 EMA ~4/year baseline)

## USER FINAL DECISION (autonomous mode)

S19 = architectural sprint per Option (A) с 7 combined amendments + ADR 0034.

**S19 deliverables (architectural):**
- T0 Bybit 15M data depth verification (Day 1 check — if <150K bars, escalate)
- T1 ADR 0034 (S19 architectural + 7 amendments + T5 raise к 150 + measurement plan для S20)
- T2 rest.py interval_map fix + single-dict refactor (Condition A1)
- T3 heal_max_bars semantic refactor + bootstrap wiring + ADR amendment (Condition A2)
- T4 Annualization factor parameterization (Condition A3 — 3 files)
- T5 WFA params 15M validation (keep ADR 0014 OR amend pending test window analysis)
- T6 15M backfill BTCUSDT (~168K bars expected)
- T7 sprint-19 page + wiki sync
- T8 PHASE 8 ship (tag v0.1.0-alpha.19)

**S20 (next sprint, measurement):**
- WFA 15M BTC measurement
- T1-T6 + DSR + MC verdict
- T5 floor 150 + fold concentration check (T-Amendment 2)
- Если PASS → MVP DONE strategy criteria → S21+ S1-S6 system criteria
- Если FAIL → S21 honest close v0.4 (4 hypotheses tested)

## Related

- [[decisions/0033-sprint-18-honest-close-v01]] — v0.1 FINAL honest close + v0.4 options A-E enumerated
- [[decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence (MC p=0.01)
- [[sprints/sprint-17-btc-mean-reversion-relaxed]] — S17 measurement details
- [[sprints/sprint-15-mean-reversion-multi-symbol]] — S15 multi-symbol baseline (Q3 architectural blockers identified)
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)

## Related

- [[decisions/0033-sprint-18-honest-close-v01]] — v0.1 FINAL honest close + v0.4 options A-E enumerated
- [[decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence (MC p=0.01)
- [[sprints/sprint-17-btc-mean-reversion-relaxed]] — S17 measurement details
- [[sprints/sprint-15-mean-reversion-multi-symbol]] — S15 multi-symbol baseline (Q3 architectural blockers identified)
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
