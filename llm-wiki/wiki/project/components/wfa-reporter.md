---
title: WFA reporter — 3-series Sharpe routing + DSR aggregate
type: component
tags: [backtest, wfa, reporter, sprint-10]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/wfa_reporter.py
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# WFA reporter

**TL;DR:** Pure function `format_wfa_report` formats structured WFA output. **CRITICAL** routes 3 distinct Sharpe series correctly per cross-cutting concern #1 (must NOT conflate). Computes DSR aggregate (sigma_sr from per-fold Sharpes per S10 Q7) — informational only, NOT in gate.

## 3 Sharpe series (DO NOT conflate)

| Series | Source | Annualization | Use |
|--------|--------|---------------|-----|
| **Bar-returns Sharpe** | `replay_engine._compute_metrics:51` | `sqrt(8760)` | ADR 0014 OOS/IS gate |
| **Per-trade Sharpe** | `compute_dsr` internal | NONE (per-trade) | DSR formula |
| **Display Sharpe** | `wfa_reporter` (per-trade × `sqrt(8760)`) | `sqrt(8760)` fixed | Informational only |

## Public API

| Symbol | Path |
|--------|------|
| `format_wfa_report` | `src/backtest/wfa_reporter.py::format_wfa_report` |
| `_ANNUALIZATION_FACTOR` | `src/backtest/wfa_reporter.py::_ANNUALIZATION_FACTOR` (private constant `sqrt(8760)`) |

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | 3 distinct Sharpe series в report dict | explicit keys | `tests/unit/test_wfa_reporter.py::test_report_contains_three_sharpe_series` |
| 2 | DSR aggregate uses sigma_sr from per-fold Sharpes | `np.std(fold_sharpes, ddof=1)` | `test_report_includes_dsr_aggregate_informational` |
| 3 | Display Sharpe annualization = `sqrt(8760)` fixed | `_ANNUALIZATION_FACTOR` constant | `test_display_sharpe_uses_fixed_8760_factor` |
| 4 | DSR informational, NOT в gate (Q2) | `acceptance_gate` separate key | `test_report_passes_through_gate_result` |
| 5 | Pure function, no I/O, no module-level mutable state | function signature | code review |

## Data flow

```
WalkForwardRunner.run() → runner_result (folds + aggregate)
    ↓ + trades_for_dsr (TradeRecord list) + mc_p_value + gate_result
format_wfa_report():
    series 1: bar_returns_sharpe_per_fold = [f.oos_metrics.Sharpe Ratio for f in folds]
    series 2: per_trade_sharpe = mean/std of compute_returns(trades_for_dsr)
    series 3: display_sharpe = per_trade_sharpe × sqrt(8760)
    dsr_aggregate = compute_dsr(trades_for_dsr, n_trials=K, sigma_sr=std(fold_sharpes))
    ↓
report dict
```

## Referenced by

- [[walk-forward]] — produces input for reporter
- [[dsr]] — aggregate DSR consumer

## Related

- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — origin ADR (Q4+Q6+Q7)
- [[../decisions/0014-walk-forward-train2000-test500]] — Sharpe gate convention
- [[backtest-harness]] — replay engine source of bar-returns Sharpe

## Sources

- `src/backtest/wfa_reporter.py` — implementation (T8)
- `tests/unit/test_wfa_reporter.py` (4 tests)
- `tests/integration/test_wfa_pipeline.py` (end-to-end)
