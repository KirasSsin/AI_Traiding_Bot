---
title: 0040. Sprint 27 — Formula bug fixes (annualization + Sortino + RSI warm-up + reason_code + MC seed)
type: decision
date: 2026-04-26
sprint: 27
tags: [adr, sprint-27, bug-fixes, replay-engine, sortino, rsi, reason-codes, mc-permutation, audit, formulas]
sources:
  - data/formulas_audit_v1.json
  - data/formulas_audit_v1_post_s27.json
  - project/decisions/0039-sprint-25-dashboard.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0040. Sprint 27 — Formula bug fixes

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S26 shipped (Dashboard UI redesign). Operator directive verbatim:

> "Твоя задача провести ревизию всех торговых метрик и формул и оптимизировать
> их чтобы торговля была в плюсе. Вызывай subagents трейдера и трейдера с
> логикой и проводи brainstorming всех стратегий, их нужно вывести в плюс.
> И определить ближайшие спринты по доработкам."

Built `scripts/audit_formulas.py` — comprehensive sweep dump:
- 30 experiments (3 strategies × 11 symbol/interval combos на 2023-2026)
- 17 formulas inventoried
- Per-trade dump (entry/exit, pnL, reason codes)
- Aggregate: 0 PASS / 30 FAIL

Output: `data/formulas_audit_v1.json` (347 KB).
Auto-refresh hook добавлен в `run_backtest()` — dashboard runs обновляют файл.

Dispatched parallel subagents:
- **trader-expert** (domain perspective) — 4 questions: formula revision / parameter optimization / new strategy hypotheses / sprint plan
- **trading-logic-reviewer** (code-level) — 5 axes: formula correctness / look-ahead bias / signal-execution invariants / acceptance gate / trade extraction integrity

## Verdicts

### Trader-expert (EXPAND on framing)

> "Assumption that 'optimizing formulas and metrics' will achieve profitability is falsified by audit. The 17 inventoried formulas contain zero technical bugs. Three experiments already achieve positive aggregate PnL. The failures are purely structural: T5 requires n≥100, but 4H single-symbol produces n=30-45 — 3-4× gap no parameter change can close."

Confirmed:
- CC1 (T5 unreachable single-symbol 4H) BINDING
- ETH 4H mean_reversion_s15: +$404, PF=1.45, T1=7.63 — passes T1/T3/T4/T6, fails только T5+MC (power-limited)
- BTC 4H mean_reversion_s15: +$155, T1=5.48 — same pattern
- Multi-symbol pooling = single engineering path к T5 PASS

Sprint backlog (5 sprints proposed):
- **S28** Multi-symbol 4H mean_reversion (n≈135 → T5 PASS)
- **S29** Regime filter + SMA50 trend gate (CC2 fold concentration)
- **S30** SL calibration + t-stat power validation
- **S31** Donchian 4H breakout (independent hypothesis)
- **S32** DSR cross-trial accumulation + MC power audit

### Trading-logic-reviewer (PARTIAL FAIL — 4 bugs)

| Severity | File:Line | Issue |
|----------|-----------|-------|
| **HIGH** | `src/backtest/replay_engine.py:51` | `np.sqrt(24*365)` hardcoded для всех timeframes — corrupts 27/30 experiments |
| MEDIUM | `src/backtest/strategy_metrics.py:80-85` | Sortino non-canonical (`std(losers, ddof=1)` instead of `sqrt(mean(min(r,0)²))`) |
| MEDIUM | `src/backtest/indicators.py:50-53` | RSI без NaN warm-up (.fillna(50.0)) |
| INFO/CC5 | `src/backtest/trade_extractor.py:70` | All trades labeled EXIT_TP_HIT (hardcoded) |
| LOW | `src/backtest/mc_permutation.py:24` | seed=None default → non-reproducible p-values |

Verified clean:
- Look-ahead bias (PASS) — entries fill at next-bar open, indicators causal
- Signal/execution FSM transitions — valid 3-state backtest machine
- Acceptance gate logic — correct AND of per-fold + MC
- Trade extraction integrity — pnL arithmetic exact (verified manually на 2 trades)

## Decision

**Accept all 5 bug fixes (T1-T5).** Defer strategy work (S28+) к follow-up sprints
per trader-expert backlog.

ESC items requiring operator decision before S28:
- **ESC-1** — multi-symbol authorization (S28 expands beyond BTCUSDT MVP scope)
- **ESC-2** — "in profit" vs "pass acceptance criteria" — different goals (live pilot ETH 4H pre-S28?)
- **ESC-3** — operational implications 4H multi-symbol (3 simultaneous positions, 1-5 day holds)

## Последствия

### Code changes (5 commits)

1. **T1** `src/backtest/replay_engine.py` + `src/__main__.py` + `src/dashboard/backtest_runner.py`:
   - `_compute_metrics(bars_per_year=8760)` parameterized
   - `run_replay` reads `config["bars_per_year"]`
   - `_run_wfa_single_symbol(bars_per_year=8760)` accepts param + injects в config
   - CLI `_cmd_wfa` derives `bars_per_year_cli` from interval map
   - dashboard runner passes `BARS_PER_YEAR[interval]` в `strategy_config["bars_per_year"]`

2. **T2** `src/backtest/strategy_metrics.py` + `src/backtest/replay_engine.py`:
   - Sortino downside_dev = `sqrt(mean(min(r,0)²))` over ALL trades (canonical Sortino & Price 1994)

3. **T3** `src/backtest/indicators.py`:
   - RSI mask first `rsi_period` bars NaN
   - ATR mask first `atr_period` bars NaN
   - mean_reversion strategy unaffected (BB gates handle warm-up via min_periods=20)

4. **T4** `src/backtest/trade_extractor.py`:
   - `_map_exit_reason()` helper: free-form 'SL'/'TP'/'SIGNAL_FLIP'/'EOD'/'KILL_SWITCH' → canonical ReasonCode
   - Unknown / missing → EXIT_TP_HIT fallback (backward compat)

5. **T5** `src/backtest/mc_permutation.py`:
   - `sign_flip_p_value(seed=42)` default
   - `block_bootstrap_p_value(seed=42)` default

### Test additions (4 new test files, 18 new test cases)

- `tests/unit/test_replay_engine_annualization.py` — 5 cases (1H/4H/15M baseline, Sortino, default backward compat)
- `tests/unit/test_strategy_metrics_sortino.py` — 4 cases (canonical formula, edge cases, anti-regression)
- `tests/unit/test_backtest_indicators_warmup.py` — 4 cases (RSI/ATR NaN warm-up, mean_reversion regression, signal gating)
- `tests/unit/test_trade_extractor_reason_code.py` — 8 cases (SL/TP/SIGNAL_FLIP/EOD/KILL_SWITCH mapping + fallbacks + mixed trades)
- `tests/unit/test_mc_sign_flip.py` extended — 1 new case (default seed reproducibility)

**Test count: 745 (S26 baseline) → 762 (S27 +18 / -1 modified).**

### Audit re-run results

`data/formulas_audit_v1.json` regenerated post-fix (full sweep 30 experiments).

Pre-fix vs post-fix delta:
- Verdict count unchanged: 0 PASS / 30 FAIL (bugs не fundamentally изменили acceptance gate outcomes)
- Reason codes diverse: 187 EXIT_SL_HIT + 141 EXIT_TP_HIT + 2 EXIT_TIME_STOP (было 100% EXIT_TP_HIT)
- ema_crossover SOLUSDT 4H: pnl +88→+131 (RSI warm-up fix removed invalid early entries)
- ema_crossover SOLUSDT 4H: T1 sharpe 1.66→2.48 (same cause)
- mean_reversion картина без изменений (BB gates immune к RSI warm-up)

`data/formulas_audit_v1_post_s27.json` — snapshot для historic comparison.
`data/runs.backup_pre_s27_fixes/` — pre-fix per-run cache (30 files) preserved.

### Wiki sync

- ADR 0040 added к `wiki/index.md` "Project — Decisions" section
- `sprint-27-formula-bug-fixes.md` page added к `wiki/project/sprints/`
- `current-state.md` updated: sprint history row +S27 (canonical counts unchanged 16/30/74/45)
- SPRINT_STATE: phase=between-sprints, sprint=27, tag=v0.1.0-alpha.27

### Backward compatibility

- `_compute_metrics` default `bars_per_year=8760` preserves pre-S27 behavior для callers без kwarg
- `extract_trade_records` unknown reason_code → EXIT_TP_HIT (matches pre-fix)
- MC `seed=None` still supported (pass explicitly если требуется non-deterministic)

### Carry-overs к S28+

- **ESC-1/2/3** decisions pending (operator)
- Trader-expert sprint backlog (S28-S32) not yet planned (PHASE 3 после ESC resolution)
- DSR cross-trial sigma_SR (S14 Q2) still unimplemented (defer к S31)

## Ссылки

- Trader-expert audit: `.claude/agent-memory/trader-expert/s27_brainstorm.md`
- Trading-logic-reviewer audit: detailed bug table в этом ADR
- Pre-fix audit: `data/runs.backup_pre_s27_fixes/`
- Post-fix audit: `data/formulas_audit_v1_post_s27.json`
- Sortino & Price (1994) "Performance measurement in a downside risk framework"
- [[../sprints/sprint-27-formula-bug-fixes]] — спринт delivery record
- Bailey & López de Prado (2018) "Backtesting Without Smoothness"
