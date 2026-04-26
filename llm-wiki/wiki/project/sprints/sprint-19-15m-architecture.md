---
title: Sprint 19 — BTC 15M architectural sprint (v0.4 prep, 7 amendments applied)
type: sprint
tags: [sprint-19, v0.4-direction-A, btc-15m, mean-reversion, architectural-sprint, t5-floor-150, annualization-fix, heal-max-bars-refactor, no-measurement]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/pre-s19-backlog.md
  - project/sprints/sprint-18-honest-close-v01.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
---

# Sprint 19 — BTC 15M architectural sprint

## Overview

S19 = architectural sprint per ADR 0034 (v0.4 direction A — BTC 15M mean-reversion). NO measurement run в S19 — preparation для S20 measurement sprint. 

PHASE 2 brainstorm: trader-expert + architecture-reviewer joint dispatch per user directive "пусть они проведут дискуссию и выберут". Both converged Option (A) с 7 combined amendments BINDING.

## Verdict

**ARCHITECTURAL PREP COMPLETE.** S20 = measurement sprint follows.

7 amendments applied (4 trader + 3 architecture):
- T-Amendment 1: T5 floor 150 trades for 15M (BINDING, S20)
- T-Amendment 2: Fold concentration pre-registration (BINDING, S20)
- T-Amendment 3: 15M data depth verified (167K bars from 2021-07-15 ✅)
- T-Amendment 4: heal_max_age production safety (encompassed by Condition A2)
- Condition A1: rest.py interval_map fix + single-dict refactor ✅
- Condition A2: heal_max_bars semantic refactor + bootstrap wiring ✅
- Condition A3: annualization parameterization (3 files) + CLI --interval ✅

## Plan / ADR links

- [[../decisions/0034-sprint-19-15m-architecture]] — Sprint 19 ADR (architectural prep + 7 amendments + S20 binding criteria)
- [[../pre-s19-backlog]] — PHASE 2 joint trader+architecture verdicts trail
- [[sprint-18-honest-close-v01]] — predecessor (v0.1 FINAL honest close + v0.4 options)
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence (MC p=0.01 — basis для v0.4-A direction)

## Deliverables

| Task | Status | Description |
|------|--------|-------------|
| T0 | ✅ DONE | Bybit 15M data depth verified (BTC 15M ≥ 2021-07-15, ~4.78y available) |
| T1 | ✅ DONE | ADR 0034 accepted |
| T2 | ✅ DONE | rest.py interval_map fix + single-dict refactor (Condition A1) |
| T3 | ✅ DONE | config.py heal_max_bars semantic refactor + `_cmd_run`/`_cmd_reconcile_only` bootstrap wiring (Condition A2) |
| T4 | ✅ DONE | Annualization parameterization (strategy_metrics.py + wfa_reporter.py + vector_backtest.py) + CLI `--interval` arg для backfill+wfa (Condition A3) |
| T5 | ✅ DONE | WFA params 15M validation — KEEP ADR 0014 defaults (test=500 bars at 15M = ~5.2 days adequate per architecture) |
| T6 | ✅ DONE | 15M backfill BTCUSDT — **167,383 bars written** к `data/BTCUSDT_15m.parquet` |
| T7 | ✅ This commit | sprint-19 page + wiki sync |
| T8 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.19) |

## FSM growth

NONE. S19 = config + CLI changes. Counts unchanged: **16 states / 30 events / 74 transitions / 45 reason codes**.

## Reason codes growth

NONE.

## Tests / quality

| Layer | S18 baseline | S19 final | Delta |
|-------|--------------|-----------|-------|
| pytest unit | 732 passed | **732 passed**, 24 skipped | OK (existing tests unaffected by config-only changes) |
| mypy --strict src/ | clean | **clean** (72 src files) | OK |
| Q7-S12 zero-migration | preserved | **preserved** | OK |

## Code changes summary

### Modified

- `src/marketdata/bybit/rest.py:66-79` — single-dict `intervals: dict[str, tuple[str, int]]` refactor (Condition A1). Adds "15": ("15m", 900_000). Raises ValueError for unsupported intervals.
- `src/platform/config.py:97-118` — added `heal_max_bars: int | None = Field(default=1)` field (Condition A2). Legacy `heal_max_age_seconds` preserved для backward-compat (None → fallback к legacy field).
- `src/__main__.py`:
  - NEW `_derive_heal_max_age_seconds(settings, interval)` helper
  - `_cmd_run` + `_cmd_reconcile_only` use derived value
  - `_load_ohlcv` accepts `interval` arg, parquet path varies (`_1h.parquet` / `_15m.parquet`)
  - `_cmd_backfill` + `_cmd_wfa` accept `--interval` CLI arg (choices ["60", "15"])
  - `_cmd_wfa` derives `bars_per_year` from interval, passes к `compute_t1_t6_metrics`
- `src/backtest/strategy_metrics.py:27-36` — added `bars_per_year: int = 8760` arg (Condition A3). Renamed `_ANNUALIZATION_FACTOR` → local `annualization_factor` derived per call.
- `src/backtest/wfa_reporter.py:23-32` — added `bars_per_year: int = 8760` arg (Condition A3). Same pattern.
- `src/backtest/vector_backtest.py:15-21` — added `bars_per_year: int = 8760` к `__init__` (Condition A3). `self.bars_per_year` used for sharpe annualization.

### NEW (NONE)

S19 = no new modules. All infrastructure reused.

## 15M backfill verification (T-Amendment 3 + T6)

Command: `TESTNET=false python -m src backfill --symbol BTCUSDT --interval 15 --from 2021-07-15 --to 2026-04-26`
Result: **167,383 bars written к data/BTCUSDT_15m.parquet** (~6.4MB Parquet snappy).

Coverage: 2021-07-15 → 2026-04-26 = ~4.78y × 35040 bars/y ≈ 167,491 expected. Actual 167,383 ≈ 99.9% coverage (small gaps acceptable per Bybit API normal behavior).

T-Amendment 3 verification: ≥ 150,000 bars threshold — **PASS** (167,383 >> 150,000).

## Wiki updates

- 1 NEW ADR (0034 — accepted)
- 1 NEW sprint page (this — sprint-19-15m-architecture)
- 1 NEW backlog (pre-s19-backlog.md)
- Modified: current-state.md (TL;DR post-S19, ADR 33→34, sprint pages 20→21, +S19 row), index.md (sprint-19 + ADR 0034), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.19)

## Next sprint (S20 — measurement, BINDING per ADR 0034)

S20 = WFA 15M measurement.

**Pre-registered command (BINDING):**
```bash
SPRINT_N=20 .venv/bin/python -m src wfa --symbol BTCUSDT --interval 15 \
  --start 2021-07-15 --end 2026-04-26
```

**Pre-registered configuration:**
- Strategy: MeanReversionRsiBBStrategy (S17 RSI 35/65 + BB(20, 1.5σ) preserved)
- Interval: 15M (bars_per_year=35040 для correct annualization)
- WFA params: ADR 0014 defaults (K=5, train=2000, test=500, embargo=20)
- T5 floor: **150 trades** (T-Amendment 1)
- N_trials: 1 (fresh baseline)

**Verdict criteria (BINDING):**
- T5 < 150 → FAIL count alone, t_stat skipped
- T5 ≥ 150 + fold concentration check (T-Amendment 2)
- All T1-T6 + DSR + MC PASS conjoint → MVP DONE strategy criteria
- FAIL → S21 honest close v0.4 (4 hypotheses tested)

## Open issues (carry-overs preserved + S19 follow-ups)

All S12-S18 carry-overs preserved (14+ items).

S19 follow-ups (post-S20):
- WFA params re-evaluation: ADR 0014 amendment если test=500 bars at 15M proves insufficient stable per S20 results
- Quant-stats-reviewer dispatch для annualization correctness verification (architecture CC1 — deferred к S20 если verdict marginal)
- DSR cross-trial sigma_SR implementation (S14 Q2 5-sprint deferred — activate если multi-hypothesis testing introduced)

## Key decisions (S19 ADR 0034)

- **Trader EXPAND → CONFIRM (A)**: BTC 15M = least-bad surviving option, 2 sprints cheap
- **Architecture APPROVE_WITH_CONDITIONS (A)**: 3 mandatory conditions — all addressed в S19
- **Joint convergence**: Option A с 7 amendments BINDING
- **ESC-1 CONTINUE Option (A)** (autonomous per "пусть они выберут"): S17 evidence justifies test
- **ESC-2 RAISE T5 floor к 150** (autonomous): simpler than autocorrelation-corrected t-stat
- **Single-dict intervals refactor**: prevents future TF drift
- **heal_max_bars semantic**: interval-agnostic, operator-safe
- **Annualization parameterization**: prevents 2× Sharpe understimate at 15M
- **NO measurement в S19**: preparation only, S20 = binary verdict

## Related

- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (full 7-amendment specification)
- [[../pre-s19-backlog]] — PHASE 2 joint verdicts trail
- [[sprint-18-honest-close-v01]] — v0.1 FINAL predecessor
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal basis для v0.4-A
- [[../decisions/0030-sprint-15-mean-reversion-multi-symbol]] — MeanReversionRsiBBStrategy + cfg dispatch (reused 100%)
- [[../decisions/0014-walk-forward-train2000-test500]] — WFA params (preserved для S20 15M, re-evaluate post-measurement)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, T5 floor 150 = pre-registration override)
