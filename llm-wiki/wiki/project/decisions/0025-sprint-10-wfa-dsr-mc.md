---
title: 0025. Sprint 10 — Walk-Forward + DSR aggregate + Monte Carlo permutations
type: decision
date: 2026-04-25
sprint: 10
tags: [adr, sprint-10, wfa, dsr, monte-carlo, backtest, statistics]
sources:
  - project/pre-s10-backlog.md
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0024-sprint-9-data-quality-types-analytics.md
status: accepted
---

# 0025. Sprint 10 — WFA + DSR aggregate + MC permutations

**Status:** accepted
**Date:** 2026-04-25

## Контекст

Sprint 10 builds на S9 B2 DSR foundation + locked ADR 0014 (walk-forward train=2000/test=500/K=5/embargo=20/Sharpe ≥ 0.7) + ADR 0015 (sign-flip MC N=2000, p ≤ 0.05). Statistical validation layer для strategy validation pre-prod.

PHASE 2 brainstorming verdicts (`pre-s10-backlog.md`):
- Q1 CONFIRM bars unit
- Q2 REVISE — DSR informational, NOT hard gate (N=40-80 trades/fold = high variance)
- Q3 CONFIRM sign-flip per-trade returns
- Q4 CONFIRM revive S2 + dual-Sharpe trap caveat
- Q5 CONFIRM per-trade DSR (per-fill = N inflation)
- Q6 REVISE — fixed sqrt(8760) annualization (NOT derived — circular)
- Q7 CONFIRM sigma_sr external param (closes S9 NotImplementedError)

## Решение

### Q1+Q4 — WFA architecture
- `WindowSplitter` (frozen dataclass) generates rolling fold tuples per ADR 0014
- `WalkForwardRunner` orchestrates IS+OOS replay per fold via existing `run_replay`
- Output dict: per-fold details + aggregate OOS trades

### Q2 — Acceptance gate
- L1 (ADR 0014): every fold's OOS/IS Sharpe ratio ≥ `sharpe_threshold` (default 0.7)
- L2 (ADR 0015): MC p-value ≤ `p_threshold` (default 0.05)
- PASS = L1 AND L2
- DSR computed and reported (informational), NOT в gate. Threshold TBD post-empirical calibration.

### Q3+Q5 — MC + DSR semantics
- Sign-flip per-trade `pnl_pct` sign random ±1, N=2000 iterations
- Block bootstrap secondary, block 30 bars (range 20-50 per ADR 0015)
- DSR consumes per-trade `TradeRecord` (not per-fill — would inflate N artificially)

### Q6 — Annualization
- Fixed `sqrt(365 × 24) = sqrt(8760)` для display Sharpe
- Aligned с existing `replay_engine._compute_metrics:51`
- DSR formula independent of annualization (S9 verified — cancels)
- Pre-existing bug `vector_backtest.py:62` `sqrt(365*24*60)` (1m assumption) — fixed T1

### Q7 — DSR sigma_sr extension
- `compute_dsr(..., sigma_sr: float | None = None)` — required if `n_trials > 1`
- Closes S9 NotImplementedError per Bailey & López de Prado eq. 12
- Quant-stats T4 review caught additional concern: `sigma_sr < 0` rejected с ValueError (std non-negative по definition)
- WFA reporter computes `sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K], ddof=1)` для aggregate DSR

### 3 Sharpe series (cross-cutting concern #1)
1. **Bar-returns Sharpe** (`replay_engine._compute_metrics`, sqrt(8760) annualized) — ADR 0014 OOS/IS gate
2. **Per-trade Sharpe** (DSR internal) — NOT annualized
3. **Display Sharpe** (sqrt(8760) on per-trade) — informational

`wfa_reporter.format_wfa_report` routes correctly. Tests enforce separation.

## Последствия

**Plus:**
- Production-grade WFA pipeline (rolling K=5, dual-gate, MC + DSR informational)
- Closes S9 carry-overs (sigma_sr NotImplementedError; annualization factor)
- Pre-existing bug fixed (`vector_backtest.py` annualization)
- 3-Sharpe trap documented + test-enforced
- T4 quant-stats reviewer added defensive sigma_sr < 0 guard

**Minus:**
- DSR threshold gate deferred к follow-up sprint (empirical calibration после real fold data)
- Per-fold DSR в reporter currently NaN (DataFrame→TradeRecord conversion deferred — informational anyway)
- MC sign-flip default N=2000 на large datasets = ~few seconds per WFA run (acceptable)
- T6 spec test correction: block bootstrap on constant returns yields p=1.0 (resampling preserves values, only orders) — implementer correctly identified spec error

## Связанные документы

- [[../pre-s10-backlog]] — PHASE 2 verdicts trail
- [[0014-walk-forward-train2000-test500]] — WFA window + Sharpe gate locked
- [[0015-sign-flip-mc-permutations-n2000]] — MC permutation N=2000 + p ≤ 0.05 locked
- [[0024-sprint-9-data-quality-types-analytics]] — DSR foundation (S9)
- [[../components/walk-forward]] — implementation (T2-T3-T7)
- [[../components/mc-permutations]] — implementation (T5-T6)
- [[../components/wfa-reporter]] — implementation (T8)
- [[../components/dsr]] — sigma_sr extension (T4)
- [[../plans/2026-04-25-sprint-10-wfa-dsr-mc]] — implementation plan + trace map

## Поправки

- (none yet)
