---
title: ADR 0051 — Sprint 34 6-th Honest Close v0.6 (hybrid pair с ADR 0052 amendment)
type: decision
tags: [adr, sprint-34, honest-close-v06, sixth-honest-close, hybrid, falsification-record]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0050-sprint-33-trading-restart.md
  - project/sprints/sprint-33-trading-restart.md
  - project/decisions/0029-sprint-14-honest-close.md
  - project/decisions/0031-sprint-16-honest-close-v02.md
  - project/decisions/0033-sprint-18-honest-close-v01.md
  - project/decisions/0036-sprint-21-honest-close-v04.md
  - project/decisions/0038-sprint-23-honest-close-v05.md
  - data/sprint_33_F_measurement.json
  - data/sprint_34_amended_gates_precheck.json
---

# ADR 0051 — Sprint 34 6-th Honest Close v0.6

## Status

Accepted (2026-04-27) — implemented в S34 (`feature/sprint-34-honest-close-v06-hybrid` → tag `v0.1.0-alpha.34`). Hybrid pair с ADR 0052 (acceptance-criteria amendment LOCKED).

## Context

Sixth honest close в проекте. Pre-committed failure branch (Item #12 ADR 0050) TRIGGERED post-S33 F BACKTEST FAIL conjoint.

Operator chose **hybrid path** per S34 consilium consensus (3 agents trader-expert + trading-logic-reviewer + quant-stats-reviewer voted A(b) primary / A(a) fallback / hybrid optimal).

This ADR (0051) handles A(a) honest close component. Paired ADR 0052 handles A(b) acceptance-criteria amendment LOCKED для future resumption.

### S33 verdict (final pre-honest-close measurement)

Per `data/sprint_33_F_measurement.json` (ADR 0050 ship):

**FAIL conjoint** на 5/9 acceptance gates:
- T1 Sharpe OOS=8.47 ✓ / T2 Sortino=17.44 ✓ / T3 Max DD=0.025 ✓ / T4 Win 42.4% / RR 2.16 ✓
- **T5 raw n=66 < 100 ❌** + **n_eff=26 << 100 ❌** (Kish 1965 design effect deflation 2.5× с rho=0.75)
- **T6 OOS/IS Sharpe ratio mean=-2.84 < 0.7 ❌**
- **MC p-value aggregate=0.52 > 0.10 ❌**
- **DSR=0.919 < 0.95 ❌** (n_trials=3 multi-symbol, sigma_SR pooled=2.24)

Per-symbol: BTCUSDT=23 trades (-4.40), ETHUSDT=25 (-3.85), SOLUSDT=18 (-0.28).

### Pre-check на amended gates (S34 T1)

Per `data/sprint_34_amended_gates_precheck.json`:

**S33 data на S34 amended gates (T5=50 / n_eff≥50 / MC≤0.05 / T6+DSR unchanged) STILL FAILS 4/5 gates:**
- T5 raw 66 ≥ 50 ✓
- T5 n_eff 26 << 50 ❌
- MC 0.52 >> 0.05 ❌
- T6 -2.84 << 0.7 ❌
- DSR 0.919 < 0.95 ❌

**Confirms:** amendment alone insufficient. 6-th honest close v0.6 fully justified.

## 6 Strategy Hypotheses Falsification Record (4.81y backfill BTCUSDT + S15+S33 multi-symbol)

| # | Sprint | Strategy | Timeframe | Symbols | n trades | Verdict | Key insight |
|---|--------|----------|-----------|---------|----------|---------|-------------|
| 1 | S13 | EMA crossover + RSI | 1H | BTC | 20 | FAIL T5/T6/MC | Sample too small |
| 2 | S15 | Mean-reversion RSI+BB strict (RSI 30/70, BB 2σ AND-gated) | 1H | BTC+ETH+SOL | 108 aggregate | FAIL — T5 PASS но T6 -12.38 / MC p=0.998 | Aggregate noise — params too tight |
| 3 | S17 | Mean-reversion RSI+BB relaxed (RSI 35/65, BB 1.5σ AND-gated) | 1H | BTC | 59 | FAIL T5 (count) ONLY — 5/6 + DSR=1.0 + MC p=0.01 PASS | Strategy edge real, sample insufficient |
| 4 | S20 | Mean-reversion RSI+BB | 15M | BTC | 73 | FAIL T1=-45.57 catastrophic fold #2 -185.21 | Hudson&Urquhart 2021 empirically validated 1st time |
| 5 | S22 | Mean-reversion RSI+BB | 4H | BTC | 62 | FAIL T5 (count) ONLY — 5/6 + DSR=0.996 + MC p=0.018 PASS | Strategy edge regime-INDEPENDENT (S17+S22) |
| 6 | **S33** | Mean-reversion RSI+BB S17-relaxed | 4H | BTC+ETH+SOL | 66 raw / **n_eff=26** | **FAIL conjoint** — T5+T6+MC+DSR all fail | **Multi-symbol expansion empirically falsified — correlation deflation prevents T5 reachability** |

## Structural Insights (BINDING для v0.7+)

1. **T5=100 floor STRUCTURALLY UNREACHABLE на BTC-only mean-reversion** (3 timeframes: 59 1H / 73 15M / 62 4H = 60-73 trades все). Confirmed S22 (BINDING per ADR 0037).

2. **Multi-symbol expansion path empirically FALSIFIED (S33 S34 T1 pre-check)** — correlation deflation rho≈0.75 BTC-ETH-SOL gives n_eff = n_raw / 2.5. n_eff=26 << T5 floor 100. Adding 4-th correlated symbol = ~7 additional effective trades only. Cannot buy way к T5=100 через correlated-asset expansion.

3. **Strategy edge REGIME-INDEPENDENT** (S17 1H + S22 4H both PASS partial 5/6+DSR+MC) — institutional knowledge preserved для v0.7+ если strategy class continues.

4. **Hudson & Urquhart 2021 empirically validated 3rd time** (S20 + S22 + S33) — heavy-tailed crypto returns produce catastrophic single-fold drawdowns at small n (S33 BTC fold #3 -32.68 confirmed pattern).

## v0.5 Final State (preserved для historical record)

- 5 prior honest closes (S14/S16/S18/S21/S23)
- v0.5 closed Sprint 23 с CC1 T5=100 unreachable single-symbol BINDING + CC3 strategy edge regime-INDEPENDENT
- Multi-symbol revival approved S15 (failed) → S33 (failed multi-symbol BTC+ETH+SOL 4H)

## Decision

**6-th honest close v0.6.** Mirror S14 ADR 0029 pattern + S16 ADR 0031 + S18 ADR 0033 + S21 ADR 0036 + S23 ADR 0038 BINDING precedent.

### Action items

1. **Archive** `data/cross_trial_sharpes.json` (3 S33 entries) → `data/cross_trial_sharpes_v0.6.json`
2. **Reset** `data/cross_trial_sharpes.json` → `{"trials": []}` (для v0.7+ fresh-start, mirror S16/S18/S21/S23)
3. **Document** 6 hypothesis falsification record (этот ADR section выше)
4. **Pair** с ADR 0052 acceptance-criteria amendment LOCKED (forward path optional)
5. **Tag** `v0.1.0-alpha.34` = honest close marker, NOT MVP DONE

### NO action items

- ❌ No new measurement run (S34 = docs+amendment only)
- ❌ No spec amendment к T5 = 100 в этом ADR (separate ADR 0052 handles amended spec)
- ❌ No new strategy hypothesis added (anti-N_trials-penalty discipline per Bailey & López de Prado)

## v0.7+ Direction Options (operator decides — NOT pre-committed в этом ADR)

Future operator может choose:

| Option | Description | Pre-requisites |
|--------|-------------|---------------|
| **(a) Project pause indefinitely** | Tag stable end. Resume позже когда conditions change. | None |
| **(b) Run new measurement с amended spec** | Use ADR 0052 LOCKED amended gates. New backtest sprint S35+. | Operator written acknowledgment per ADR 0052 + new data period extension |
| **(c) Different strategy class** | Donchian / ML / HMM (paradigm shift beyond mean-reversion). | New ADR с pre-registered hypothesis + N_trials counter accumulates |
| **(d) Different timeframe** | 1D mean-reversion с volume gate. | NOT recommended per S34 consilium (T5 problem worse) |
| **(e) Different asset class** | Uncorrelated instruments (commodity futures, FX). | Beyond v0.1 scope. Major refactor. |

## Consequences

### Positive

1. **Scientific honesty preserved** — 6 hypothesis falsification documented + cross_trial archived
2. **Project state stable** — kit infrastructure mature, S34 amendment ready для resumption
3. **Anti-snooping discipline maintained** — no spec lowered post-hoc для accommodate negative result; amendment in separate ADR 0052 LOCKED before future measurement
4. **Hudson & Urquhart 2021 institutional knowledge documented** (3rd empirical validation S33 BTC fold #3)
5. **Multi-symbol expansion path EMPIRICALLY falsified** — future operators не повторят S15+S33 attempts с same hypothesis
6. **Pattern continues** — 6-th honest close consistent с S14/S16/S18/S21/S23 transparency norm

### Negative

1. **No live deployment** — strategy validation negative across 6 hypotheses + 3 timeframes + multi-symbol
2. **Project ROI uncertain** — 33 sprints invested, no profitable strategy identified
3. **MVP DONE per acceptance-criteria.md NOT achieved** — T5=100 floor structural blocker confirmed
4. **Operator decision required для v0.7+** — no automated path forward

### Neutral

1. Kit infrastructure (S32 series + S33) remains usable для any future direction
2. Pattern consistent с industry norm (most quant strategies fail empirical validation)
3. Documented insights have value beyond v0.1 (regime-independence + Hudson&Urquhart 2021 validation + correlation deflation insight)

## Implementation

T2 commit (this commit):
- `data/cross_trial_sharpes.json` reset к `{"trials": []}`
- `data/cross_trial_sharpes_v0.6.json` NEW (3 S33 entries archived)
- ADR 0051 (this file)

## Related

- ADR 0029 (S14 1-st honest close) — pattern reference
- ADR 0031 (S16 2-nd honest close v0.2)
- ADR 0033 (S18 3-rd honest close v0.1 final)
- ADR 0036 (S21 4-th honest close v0.4)
- ADR 0038 (S23 5-th honest close v0.5)
- **ADR 0051 (this — 6-th honest close v0.6)**
- ADR 0050 (S33 Trading Restart — pre-committed failure branch trigger)
- ADR 0052 (S34 acceptance-criteria amendment — paired hybrid)
- pre-s33-backlog.md S34 Direction Consilium section
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique — 3rd validation S33)
- Kish 1965 (design effect для clustered samples — n_eff S33)
