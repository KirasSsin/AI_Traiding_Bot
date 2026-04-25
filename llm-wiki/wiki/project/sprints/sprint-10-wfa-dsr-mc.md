---
title: Sprint 10 — Walk-Forward Analysis + DSR aggregate + Monte Carlo permutations
type: sprint
tags: [sprint-10, wfa, dsr, monte-carlo, backtest]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-10-wfa-dsr-mc
  - project/decisions/0025-sprint-10-wfa-dsr-mc
  - project/pre-s10-backlog
---

# Sprint 10 — WFA + DSR + MC permutations

## Overview

S10 ships production-grade walk-forward validation pipeline. Builds на S9 B2 DSR foundation + locked ADR 0014 (WFA params) + ADR 0015 (MC params). 11 TDD tasks, ~14 commits squash-merged. Tag `v0.1.0-alpha.10`.

**Closes S9 deferred:**
- DSR `n_trials > 1 NotImplementedError` → sigma_sr param implementation (Q7)
- DSR annualization decision → fixed `sqrt(8760)` для display Sharpe (Q6)
- WFA acceptance gate consuming DSR → DSR informational, NOT in gate per Q2 trader REVISE

**Bonus fix:** Pre-existing bug `vector_backtest.py:62` annualization `sqrt(365*24*60)` (1m assumption) → `sqrt(8760)` (1H correct).

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-10-wfa-dsr-mc]]
- ADR (NEW): [[../decisions/0025-sprint-10-wfa-dsr-mc]]
- Brainstorm trail: [[../pre-s10-backlog]]

## Deliverables

11 tasks, 14 commits squash-merged on `feature/sprint-10-wfa-dsr-mc`.

### T1 — vector_backtest annualization fix (`07c6042`)
- `src/backtest/vector_backtest.py:62-64` annualization `sqrt(365*24*60)` → `sqrt(8760)` для 1H BTCUSDT
- Pandas 3.x deprecation fix (`replace(0, method="ffill")` → `replace(0, np.nan).ffill().fillna(0)`)
- 2 new tests

### T2-T3 — WFA orchestrator (`57ff9d3` + `06cf625`)
- NEW `WindowSplitter` (frozen dataclass, ADR 0014 defaults) + 6 tests
- `WalkForwardRunner` orchestrator с dual-Sharpe routing + 5 tests

### T4 — DSR sigma_sr extension (`0dc0b8a` + `c33dd28`)
- `src/analytics/dsr.py::compute_dsr` extended с `sigma_sr: float | None` param
- `n_trials > 1` raises ValueError if sigma_sr None (no longer NotImplementedError)
- Bailey eq. 12 implementation per ADR 0025
- quant-stats-reviewer T4 BLOCKER fix: sigma_sr < 0 also raises ValueError
- 5 tests (4 + 1 fix test)

### T5-T6 — MC permutations (`3cda6f6` + `0e93847`)
- NEW `sign_flip_p_value` (primary, N=2000) + 5 tests
- `block_bootstrap_p_value` (secondary, block 30 default) + 4 tests
- T6 spec correction: implementer caught block bootstrap on constant returns yields p=1.0 (resampling preserves values)

### T7 — Acceptance gate (`b98fff2`)
- `evaluate_acceptance_gate` ANDs Sharpe + MC per ADR 0014 + 0015
- DSR NOT в gate (Q2 trader REVISE — informational only)
- 4 tests

### T8 — WFA reporter (`855a66a`)
- NEW `format_wfa_report` — 3-Sharpe series routing
- DSR aggregate с sigma_sr from per-fold Sharpes (Q7)
- 4 tests

### T9 — Integration test (`86d3db3`)
- `tests/integration/test_wfa_pipeline.py` end-to-end (synthetic data → replay × K → DSR → MC → gate → report)
- `pytest.mark.integration` registered in pytest.ini

### T10-T11 — ADR + wiki sync
- ADR 0025 + index.md entry (`fd2762b`)
- 3 NEW component pages: walk-forward + mc-permutations + wfa-reporter
- This sprint page + counts updates

## FSM growth

NONE. WFA = analytics post-process layer. Counts unchanged: 16/30/74/45.

## Reason codes growth

NONE.

## Tests

- pytest unit: 656 passed / 24 skipped / 0 failed (baseline 630 → +26 new tests)
- pytest integration: 1 passed (T9 end-to-end)
- mypy --strict src/: clean
- New: integration test marker `pytest.mark.integration` registered

## Wiki updates

- 3 NEW component pages (walk-forward + mc-permutations + wfa-reporter)
- 1 NEW ADR (0025)
- 1 NEW sprint page (this)
- Modified: current-state.md (counts 32→35, ADR 24→25, sprint pages 11→12)
- components/README.md (Cluster 8 expanded)
- mental-map.md (3 query rows)

## Open issues для S11+

- DSR threshold gate calibration (Q2 deferred — TBD post-empirical fold data)
- Live demo Mainnet validation (S11 F per S9 carry-over roadmap)
- Per-fold DSR в reporter currently NaN (DataFrame→TradeRecord conversion deferred — informational anyway)
- WFA wired в `__main__.py` CLI subcommand — defer

## Key decisions

- **DSR informational, NOT gate (Q2 trader REVISE):** N=40-80 trades/fold = high DSR variance, would reject valid strategies. Calibrate threshold empirically.
- **Fixed sqrt(8760) annualization (Q6 trader REVISE):** Derived from trade frequency = circular + breaks IS/OOS comparability.
- **3-Sharpe series trap (cross-cutting concern #1):** Bar-returns / per-trade / display — must not conflate. Test-enforced в reporter.
- **Revive S2 backtest:** Existing `replay_engine` battle-tested, WFA = orchestration layer на top, не replacement.
- **sigma_sr external param (Q7):** Closes S9 NotImplementedError. Caller (`wfa_reporter`) computes `sigma_sr = std(per_fold_sharpes, ddof=1)`.
- **sigma_sr < 0 guard (T4 quant-stats fix):** Defensive ValueError (std non-negative по definition).
- **T6 spec correction:** Implementer caught block bootstrap on constant returns yields p=1.0 (correct math). Replaced spec test с valid contract check.

## Related

- [[../plans/2026-04-25-sprint-10-wfa-dsr-mc]] — full plan + trace map
- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — aggregate ADR
- [[../pre-s10-backlog]] — PHASE 2 verdicts trail
- [[sprint-09-data-quality-types-analytics]] — predecessor sprint (B2 DSR foundation)
- [[../components/walk-forward]] + [[../components/mc-permutations]] + [[../components/wfa-reporter]] — new components
