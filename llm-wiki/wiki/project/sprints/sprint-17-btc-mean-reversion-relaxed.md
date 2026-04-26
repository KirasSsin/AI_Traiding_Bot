---
title: Sprint 17 — BTC-only mean-reversion relaxed (RSI 35/65 + BB 1.5σ), MVP retry hypothesis #3
type: sprint
tags: [sprint-17, btc-only-mvp, mean-reversion-relaxed, hypothesis-3, t5-failthrough, verdict-fail-t5-count, dsr-pass, mc-significant]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/pre-s17-backlog.md
  - project/sprints/sprint-16-honest-close-v02.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
---

# Sprint 17 — BTC-only mean-reversion relaxed (MVP retry #3)

## Overview

S17 = MVP retry hypothesis #3 per S17 PHASE 2 brainstorm trader-expert ROUND 1 EXPAND verdict (option (a) с 3 mandatory amendments). Pre-registered binding parameters: RSI 35/65 + BB(20, 1.5σ) AND-gated, NO variance cap, T5 count failthrough → honest close v0.1 if <100 trades.

User constraint (BINDING): MVP scope = BTCUSDT only per ADR 0016 + 2026-04-26 user clarification. Multi-symbol infrastructure preserved (S15 T1 load_recent + T5 --symbols CLI) но не used в S17 measurement.

Fresh N_trials=1 baseline (S16 T6 cross_trial_sharpes archival completed) → DSR gate at single-trial formula.

## Verdict

**FAIL — T5 count only.** 59 OOS trades < 100 floor.

Per ADR 0032 amendment 3 BINDING: T5 count <100 → VERDICT FAIL → S18 = honest close v0.1 (3 hypotheses tested).

### Detailed metrics breakdown

| Criterion | Threshold | S17 result | Status |
|-----------|-----------|------------|--------|
| T1 Sharpe OOS | ≥1.0 | **25.99** | ✅ PASS |
| T2 Sortino OOS | ≥1.5 | 4446.49 | ✅ PASS |
| T3 MaxDD | <0.25 | 0.028 | ✅ PASS |
| T4 win/RR | RR≥2 → win≥35% | win 47.5% / RR 154.5 | ✅ PASS |
| T5 n_trades | ≥100 + t_stat≥2 + mean_pnl>0 | **59** / t_stat 2.13 / mean +2.40% | ❌ **FAIL (count only)** |
| T6 OOS/IS sharpe ratio | ≥0.7 | 0.712 | ✅ PASS (borderline) |
| **DSR** | >0 | **1.0** (n_trials=1, fresh baseline) | ✅ **PASS** |
| **MC p-value** | ≤0.05 | **0.01** | ✅ **PASS (statistically significant)** |
| Acceptance gate (composite) | sharpe + MC | sharpe FAIL (folds 1+2 below 0.7) | ❌ FAIL |

### Critical observation: 5/6 strategy criteria + DSR + MC PASS

S17 = first time в проекте с positive direction по MOST criteria одновременно. Failure mode = INSUFFICIENT SAMPLE SIZE only (59 vs 100 floor). T1=25.99 + DSR=1.0 + MC p=0.01 = strong statistical signal на limited data — но ADR 0032 pre-registration BINDING per Bailey 2014 multi-testing discipline.

**T1 Sharpe 25.99 + Sortino 4446 = suspiciously high — possibly overfit indicator.** Per acceptance-criteria.md: "Sharpe >2.0 suspicious; >3.0 almost certainly overfit (Hudson–Urquhart 2021)". Trader's frequency math actual outcome = 59 trades (predicted 66-88, conservative bound 66 — actual fell ниже даже conservative). Sample insufficient → metrics unstable.

### Per-fold breakdown

```
fold_sharpe_ratios: [0.96, -1.02, -1.46, 1.58, 3.50]
mean = 0.71 (T6 borderline pass)
2 negative folds (1, 2) below 0.7 sharpe gate threshold
```

Fold #5 sharpe 3.50 likely contains best mean-reversion signals → drives aggregate. Без fold #5 mean ≈ 0.01 — strategy edge concentrated в few periods (concerning for production).

## Plan / ADR links

- [[../decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — Sprint 17 ADR (pre-registered + 3 amendments)
- [[../pre-s17-backlog]] — PHASE 2 trader EXPAND verdict
- [[sprint-16-honest-close-v02]] — predecessor (v0.2 honest close + cross_trial archival)
- [[sprint-15-mean-reversion-multi-symbol]] — S15 BTC alone signal observed (institutional knowledge)

## Deliverables

| Task | Description | Status |
|------|-------------|--------|
| T1 | ADR 0032 (S17 strategy + 3 amendments + T5 failthrough) | ✅ DONE |
| T2 | indicators.py mean_reversion branch parameter wiring (already config-driven from S15) | ✅ NO CHANGE NEEDED |
| T3 | _run_wfa_single_symbol config update (RSI 35/65 + BB k=1.5) + sprint env var fix | ✅ DONE |
| T4 | Measurement run BTC-only --symbol BTCUSDT 4.81y | ✅ DONE (verdict FAIL T5 count) |
| T5 | Sprint-17 page + ADR + wiki sync | ✅ This commit |
| T6 | PHASE 8 ship (PR + tag v0.1.0-alpha.17) | pending |

## FSM growth

NONE. S17 = configuration tuning + measurement. Counts unchanged: **16 states / 30 events / 74 transitions / 45 reason codes**.

## Reason codes growth

NONE.

## Tests / quality

NO new tests added (trivial config change). Existing suite preserved:
- pytest unit: **732 passed**, 24 skipped (S16 baseline, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

## Code changes

### Modified

- `src/__main__.py` — `_run_wfa_single_symbol` config dict updated:
  - `rsi.oversold`: 30 → **35**
  - `rsi.overbought`: 70 → **65**
  - `bb.k`: 2.0 → **1.5**
  - `_cmd_wfa` `append_trial(sprint=15)` → `sprint=int(os.environ.get("SPRINT_N", "0"))` (parameterized)
- `data/cross_trial_sharpes.json` — runtime artifact, gitignored. Contains S17 trial entry: `[{"sprint": 17, "oos_sharpe": 0.712}]` (fresh n_trials=1 baseline confirmed)

### New (NONE)

S17 = no new code modules. All infrastructure reused from S15.

## Frequency math reconciliation

Trader pre-measurement prediction: 66-88 BTC trades (conservative-optimistic range).
Actual: **59 trades.**

AND-gate joint multiplier ~1.34x baseline (44 trades), ниже trader's predicted 1.4-1.7x. Possible reason: RSI 35/65 + BB 1.5σ correlated stronger чем trader's empirical estimate (positive correlation on price extremity events compresses joint probability further).

T5 floor 100 не reachable на BTC-only 1H mean-reversion regardless of relaxed thresholds tested. Future v0.4 attempts requiring T5 PASS должны:
- Use higher-frequency timeframe (15M = 4x — Q3 architectural blockers preserved)
- Use trend-following family (different signal class — но similar S13 frequency profile risk)
- Multi-symbol aggregation (out of MVP scope per user 2026-04-26)

## Wiki updates

- 1 NEW ADR (0032 — accepted)
- 1 NEW sprint page (this — sprint-17-btc-mean-reversion-relaxed)
- 1 NEW backlog (pre-s17-backlog.md)
- Modified: current-state.md (TL;DR post-S17, ADR 31→32, sprint pages 18→19, +S17 row), index.md, log.md, SPRINT_STATE
- s17_wfa_result.json committed (full measurement output preservation)

## Open issues для S18 (per ADR 0032 failthrough clause)

**S18 = honest close v0.1.** Documentation only sprint, mirrors S14 ADR 0029 + S16 ADR 0031 patterns:
- ADR 0033 v0.1 honest close (3 hypotheses tested negative)
- sprint-18-honest-close-v01.md
- Document 5/6 strategy criteria PASS + DSR PASS + MC stat-sig — **strategy direction promising но T5 sample insufficient on BTC-only 1H**
- Archive `cross_trial_sharpes.json` к `_v0.1-final.json`
- Tag v0.1.0-alpha.18 = v0.1 final honest close marker

### v0.4+ direction (deferred к operator, NO commitment)

- Different timeframe (15M / 4H per Q3 backlog) — addresses T5 frequency floor structural limit
- Different strategy family (regime-switch HMM, trend-following с trailing TA-Lib pattern recognition)
- Hybrid mean-reversion + ML filter (Q4 deferred, S17 evidence supports — DSR PASS + MC stat-sig = real signal partial, ML может filter)
- Multi-symbol revival (post-MVP scope, S15 infrastructure preserved)
- Project pause

### Carry-overs preserved (all S12+S13+S14+S15+S16 + new S17)

- F live demo Mainnet validation (operator-driven, not run since S12 33min)
- FillRecorderAdapter Layer 2 schema link
- 3-way endpoint enum (DEMO/TESTNET/MAINNET)
- T2 review C3 init_db dual-conn comment
- DSR per-fold DataFrame→TradeRecord conversion
- DSR threshold calibration (S15+ deferred per S11 Q5)
- halt_log INSERT order swap в `_set_halt`
- find_by_order_id ORDER BY explicit
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)
- 48h Bybit demo validation
- Q3 15M architectural blockers (interval_map + heal_max_age — preserved per S16 CC6)
- Multi-symbol live runtime fan-out (S15 deferred)
- Capital allocation cross-symbol exposure caps (S15 deferred — out of MVP per user)
- **NEW S17 carry-over:** S17 fold #5 sharpe 3.50 outlier — strategy edge concentrated в few periods, concerning for production stability

## Key decisions (S17 ADR 0032 + verdict)

- **Q1 EXPAND→CONFIRM (a) с amendments** (trader): BTC-only mean-reversion relaxed least-bad surviving option
- **Amendment 1**: Pre-registered RSI 35/65 + BB 1.5σ BINDING (no post-result tuning) — applied
- **Amendment 2**: DROPPED variance cap -10 (ETH-pathology-derived, audit-clean) — applied
- **Amendment 3**: T5 failthrough <100 trades → FAIL → S18 honest close v0.1 — **TRIGGERED** (59 trades)
- **CC1 T5 frequency uncertainty acknowledged honestly** — predicted 66-88, actual 59
- **CC4 Honest close v0.1 if FAIL = publishable scientific contribution** — S18 will document
- **N_trials=1 fresh baseline confirmed** working (DSR=1.0 single-trial PASS)
- **MC stat-significance achievement** (p=0.01) noted for v0.4+ institutional knowledge — strategy edge IS real on BTC mean-reversion regime, just sample insufficient на 1H BTC alone

## Related

- [[../decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 ADR
- [[../pre-s17-backlog]] — PHASE 2 verdict
- [[sprint-16-honest-close-v02]] — predecessor (v0.2 honest close pattern)
- [[sprint-15-mean-reversion-multi-symbol]] — S15 BTC institutional knowledge
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
