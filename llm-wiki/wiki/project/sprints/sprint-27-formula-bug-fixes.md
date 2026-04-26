---
title: Sprint 27 — Formula bug fixes (annualization + Sortino + RSI warm-up + reason_code + MC seed)
type: sprint
tags: [sprint-27, bug-fixes, replay-engine, sortino, rsi, reason-codes, mc-permutation, audit, formulas]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0040-sprint-27-formula-bug-fixes.md
  - data/formulas_audit_v1.json
  - data/formulas_audit_v1_post_s27.json
---

# Sprint 27 — Formula bug fixes

## Overview

Operator-driven audit sprint. Per directive 2026-04-26:

> "Провести ревизию всех торговых метрик и формул и оптимизировать их чтобы
> торговля была в плюсе. Вызывай subagents трейдера и трейдера с логикой."

Built `scripts/audit_formulas.py` — comprehensive sweep dump (30 experiments,
17 formulas, per-trade detail). Auto-refresh hook integrated в dashboard.

Joint trader+logic-reviewer parallel brainstorm produced:
- **Trader-expert** EXPAND verdict — formulas correct, failures structural (T5 unreachable single-symbol). Sprint backlog S28-S32.
- **Trading-logic-reviewer** PARTIAL FAIL — 4 bugs found (1 HIGH, 2 MEDIUM, 1 INFO/CC5, 1 LOW)

S27 scope = 5 bug fixes (T1-T5). Strategy work deferred к S28+ pending ESC items resolution.

## Plan / ADR links

- [[../decisions/0040-sprint-27-formula-bug-fixes]] — Sprint 27 ADR
- `data/formulas_audit_v1.json` — corrected sweep output
- `scripts/audit_formulas.py` — audit script

## Deliverables

### Code

| Task | Severity | Files | Description |
|------|----------|-------|-------------|
| T1 | HIGH | `src/backtest/replay_engine.py`, `src/__main__.py`, `src/dashboard/backtest_runner.py` | `bars_per_year` parameterized — fixes hardcoded `sqrt(24*365)` annualization for всех timeframes |
| T2 | MEDIUM | `src/backtest/strategy_metrics.py`, `src/backtest/replay_engine.py` | Sortino canonical downside_dev = `sqrt(mean(min(r,0)²))` per Sortino & Price 1994 |
| T3 | MEDIUM | `src/backtest/indicators.py` | RSI/ATR mask first `period` bars NaN (warm-up gating) |
| T4 | INFO/CC5 | `src/backtest/trade_extractor.py` | `_map_exit_reason()` preserves SL/TP/SIGNAL_FLIP/EOD/KILL_SWITCH → canonical ReasonCode |
| T5 | LOW | `src/backtest/mc_permutation.py` | `seed=42` default (was None) для audit reproducibility |

### Tests (4 new files, 18 new cases)

| File | Cases | Coverage |
|------|-------|----------|
| `tests/unit/test_replay_engine_annualization.py` | 5 | 1H/4H/15M baseline, Sortino, default backward compat |
| `tests/unit/test_strategy_metrics_sortino.py` | 4 | Canonical formula, edge cases (all-winners NaN, only-losers), anti-regression |
| `tests/unit/test_backtest_indicators_warmup.py` | 4 | RSI/ATR NaN warm-up, mean_reversion regression-clean, signal gating |
| `tests/unit/test_trade_extractor_reason_code.py` | 8 | 5 mapping tests + 2 fallbacks + 1 mixed |
| `tests/unit/test_mc_sign_flip.py` (extended) | +1 | Default seed reproducibility |

**Test count: 745 (S26) → 762 (+17 net, 1 modified to canonical Sortino).**

### Audit (S27 audit doc)

- `scripts/audit_formulas.py` — sweep + rebuild + auto-refresh hook
- `data/formulas_audit_v1.json` — corrected post-fix sweep (30 experiments, 347 KB)
- `data/formulas_audit_v1_post_s27.json` — snapshot для historic comparison
- `data/runs.backup_pre_s27_fixes/` — pre-fix per-run cache preserved

### Wiki updates

| Page | Change |
|------|--------|
| `wiki/project/decisions/0040-sprint-27-formula-bug-fixes.md` | NEW (this ADR) |
| `wiki/project/sprints/sprint-27-formula-bug-fixes.md` | NEW (this page) |
| `wiki/project/SPRINT_STATE.md` | sprint=27, phase=between-sprints, tag=v0.1.0-alpha.27 |
| `wiki/index.md` | + ADR 0040 + sprint-27 page entries |
| `wiki/project/architecture/current-state.md` | Sprint history row +S27 |

## FSM growth

No FSM changes (canonical counts unchanged: 16 states / 30 events / 74 transitions / 45 reason codes).

## Reason codes

No new reason codes. T4 fix surfaces existing canonical codes (EXIT_SL_HIT, EXIT_SIGNAL_FLIP, EXIT_TIME_STOP, EXIT_CIRCUIT_BREAKER) instead of hardcoded EXIT_TP_HIT.

## Tests

- 762 passed unit (was 745) — 18 new cases, 1 modified
- mypy --strict baseline preserved
- Full audit sweep passes (30 experiments, 0 errors except 3 expected 1d insufficient-bars cases)

## Open issues для S28+

### ESC items (operator decision required)

- **ESC-1** Multi-symbol authorization (S28 expanded scope beyond BTCUSDT MVP)
- **ESC-2** "In profit" vs "pass acceptance criteria" — different goals (live pilot ETH 4H pre-S28?)
- **ESC-3** Operational implications 4H multi-symbol (3 simultaneous positions, 1-5 day holds, capital commitment)

### Trader-expert backlog

| Sprint | Goal | Effort | Dependencies |
|--------|------|--------|--------------|
| S28 | Multi-symbol 4H mean_reversion (n≈135 → T5 PASS) | L | ESC-1 |
| S29 | Regime filter + SMA50 trend gate (CC2 fold concentration) | M | S28 |
| S30 | SL calibration {1.0/1.25/1.5}×ATR + t-stat power | M | S28+S29 |
| S31 | Donchian 4H breakout (independent hypothesis) | M | S28 data pipeline |
| S32 | DSR cross-trial sigma_SR + MC power audit | S | S27-S31 results |

## Key decisions

1. **Bug fixes first, strategy work later.** Per logic-reviewer findings — measurement instrument was broken для 27/30 experiments. No strategy verdicts trustworthy until fixes shipped.

2. **Formulas correct otherwise.** Trader-expert verified 17 formulas inventory — zero math bugs. All failures structural.

3. **CC5 surfaced.** Audit JSON reason codes were diagnostically useless (100% EXIT_TP_HIT). Now 187 SL / 141 TP / 2 TIME_STOP — enables loss root-cause analysis для S29+.

4. **No acceptance criteria changes.** Per ADR pattern, T1-T6 thresholds immutable. S27 fixes measurement, не criteria.

5. **Auto-refresh hook in dashboard.** Audit doc обновляется after каждый POST `/api/backtest`. Operator может flag pnL trends к trader-expert real-time.

## Related

- ADR 0011 (TA-Lib EMA + Wilder) — RSI/ATR warm-up convention
- ADR 0014 (WFA K=5 immutable) — bars_per_year derivation per fold
- ADR 0015 (MC sign-flip ADR) — seed default reproducibility
- ADR 0017 (review-agent harness) — trader-expert + trading-logic-reviewer parallel pattern used here
- ADR 0028 (S13 trade_extractor) — extended T4 mapping
- ADR 0034 (S19 bars_per_year) — earlier annualization parameterization (strategy_metrics)
- ADR 0039 (S25 dashboard) — backtest_runner dashboard caller
- Sortino & Price (1994) — canonical downside deviation formula
- Bailey & López de Prado (2018) — backtesting methodology
