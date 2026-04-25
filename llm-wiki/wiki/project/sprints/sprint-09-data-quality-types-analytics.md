---
title: Sprint 9 — Data quality + mypy strict + per-fill analytics + DSR
type: sprint
tags: [sprint-9, data-quality, mypy-strict, per-fill, dsr, halt-code]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-9-quality-types-analytics
  - project/decisions/0024-sprint-9-data-quality-types-analytics
  - project/pre-s9-backlog
---

# Sprint 9 — Data quality + mypy strict + per-fill analytics + DSR

## Overview

S9 закрывает 3 deferred carry-overs (C + G + B grouping per pre-S9 brainstorm). Pure additive: 3 new modules + 1 new migration + WS topic extension + override removal. 0 behavioral regressions. FSM/event/transition counts unchanged (HALT_DATA_QUALITY uses existing RISK_HALT event path per ADR 0023 invariant).

12 TDD tasks, ~14 commits squash-merged. Tag `v0.1.0-alpha.9`.

**Key finding (Q2 G):** per-module `mypy --strict src/risk/` empirically reported clean, but full-tree `mypy src/` после override removal exposed 18 cross-module errors. Lesson: always full-tree verify before override removal.

**Key finding (Q3 B2):** quant-stats-reviewer T9 BLOCKER caught wrong kurtosis convention (Fisher excess vs Pearson total). Per Bailey & López de Prado eq. 13, formula uses `gamma_4` = total kurtosis; `scipy.stats.kurtosis(..., fisher=False)` correct.

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-9-quality-types-analytics]]
- ADR (NEW): [[../decisions/0024-sprint-9-data-quality-types-analytics]]
- Brainstorm trail: [[../pre-s9-backlog]]

## Deliverables

### Q1 — Data quality (3 tasks)

- T1: NEW `src/marketdata/quality.py::BarPriceQualityDetector` (8 tests) — REST-vs-REST consecutive bar deviation (`915305a` + `d503c8d` review fixes)
- T2: Coordinator HALT_DATA_QUALITY explicit dispatch + property test allow-list expanded к 4 codes (`c4f65d4`)
- T3: RuntimeManager integration — quality detector wired в tick pipeline, `_stopping=True` set on halt (`92d4246` + `4e2b8ac` review fixes)

### Q2 — mypy strict (1 task + follow-up)

- T4: Removed `ignore_errors = true` override (`3a68562`); follow-up fixed 18 exposed errors across 7 files (`9f91b8c`). All `src/` modules pass `mypy --strict` clean.

### Q3 B1 — Per-fill schema (4 tasks)

- T5: NEW `migrations/0006_trade_fills.sql` (FK trade_history, UNIQUE exec_id, composite index) + 3 tests (`e297c46` + `5e939ab` FK enforcement test)
- T6: NEW `src/risk/fill_history.py::FillRecord` + `FillHistoryRepository` + 7 tests (`e1f35da`)
- T7: WS execution topic subscription + `_FillRecorderProto` + `_on_execution_raw` + 3 tests (`52c728a` + `f3ba12a` docstring fix)
- T8: NEW `wiki/project/components/fill-history.md` (`b67d87e`)

### Q3 B2 — DSR (2 tasks)

- T9: NEW `src/analytics/dsr.py` — Bailey & López de Prado DSR formula + 8 tests + quant-stats-reviewer APPROVED post-fix BLOCKER (`93ba369` + `3074aa4` Pearson kurtosis fix + n_trials NYI guard)
- T10: NEW `wiki/project/components/dsr.md` (`22c28ef`)

### Wiki + ADR sync (2 tasks)

- T11: NEW ADR 0024 + index.md entry (`4230c4b`)
- T12: This sprint page + data-quality.md component + current-state.md counts + components/README.md cluster + mental-map.md updates

## FSM growth

NONE. Counts unchanged: 16 states / 30 events / 74 transitions / 45 reason codes.

HALT_DATA_QUALITY (pre-allocated в ReasonCode enum since S4) routed через existing RISK_HALT event path per ADR 0023 invariant.

## Reason codes growth

NONE.

## Tests

- pytest: 621 passed / 24 skipped / 0 failed (NEW: 8 quality + 7 fill_history + 8 dsr + 1 coordinator + 3 migration + 3 ws_private + 2 runtime = +32 tests, baseline 589 → 621)
- mypy --strict src/ → Success: no issues found in 62 source files
- Property test `tests/property/test_request_halt_mapping.py` — 4 codes в allow-list (added HALT_DATA_QUALITY)

## Wiki updates

- 3 new component pages: data-quality, fill-history, dsr
- 1 new ADR (0024)
- 1 new sprint page (this)
- 1 new migration (0006)
- mental-map.md: data quality + per-fill + DSR domain queries added
- components/README.md: 3 new components added к clusters

## Open issues для S10+

- DSR annualization factor (deferred — irregular trade frequency normalization decision)
- DSR n_trials > 1 (NYI v0.1, requires sigma_SR per Bailey eq. 12)
- Walk-Forward acceptance gate consuming DSR (S10 D scope)
- Per-fill consumed by DSR (currently per-trade only — future granularity if needed)
- Production wiring of FillRecorder (`__main__.py::_cmd_run` STUB since S8a — defer к operator-readiness sprint)

## Key decisions

- **REST-vs-REST quality detector** (NOT WS+REST kline) — closes async dependency + WS partial-bar false-positive risk per Q1 trader REVISE
- **mypy strict full enable lessons** — empirical per-module check INSUFFICIENT; always full-tree verify (18 cross-module errors surfaced)
- **Split B1 + B2** — independent concerns, parallel ship
- **HALT_DATA_QUALITY uses existing RISK_HALT** — no new FSM state/event/transition needed (ADR 0023 invariant satisfied via _REQUEST_HALT_CODES allow-list expansion)
- **Pearson kurtosis (NOT Fisher)** в DSR formula per quant-stats-reviewer T9 BLOCKER — caught wrong convention before merge
- **DSR annualization deferred** — per-trade Sharpe internally consistent для DSR (Φ output unit-free, annualization cancels)
- **`_stopping=True` after quality halt** — match stall + kill-switch terminal halt patterns (else log storm at poll cadence)

## Related

- [[../plans/2026-04-25-sprint-9-quality-types-analytics]] — full plan + trace map
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — aggregate ADR
- [[../pre-s9-backlog]] — PHASE 2 verdicts trail
- [[sprint-08c-wiki-backfill]] — predecessor sprint
- [[../components/data-quality]] + [[../components/fill-history]] + [[../components/dsr]] — new components
