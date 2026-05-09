---
title: Walk-Forward — WindowSplitter + WalkForwardRunner
type: component
tags: [backtest, wfa, validation, sprint-10]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/walk_forward.py
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# Walk-Forward Analysis

**TL;DR:** Production WFA orchestrator. `WindowSplitter` (frozen dataclass) generates rolling K-fold (train, test) tuples per ADR 0014 defaults (train=2000, test=500, embargo=20, K=5). `WalkForwardRunner` invokes existing `run_replay()` per fold (IS + OOS), routes results к dual-Sharpe paths. `evaluate_acceptance_gate` ANDs Sharpe + MC gates per ADR 0014 + 0015. DSR informational only per S10 Q2 verdict.

## Public API

| Symbol | Path |
|--------|------|
| `WindowSplitter` (frozen dataclass) | `src/backtest/walk_forward.py::WindowSplitter` |
| `WindowSplitter.split` | `src/backtest/walk_forward.py::WindowSplitter.split` |
| `WalkForwardRunner` | `src/backtest/walk_forward.py::WalkForwardRunner` |
| `WalkForwardRunner.run` | `src/backtest/walk_forward.py::WalkForwardRunner.run` |
| `evaluate_acceptance_gate` | `src/backtest/walk_forward.py::evaluate_acceptance_gate` |

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | ADR 0014 defaults: train=2000, test=500, embargo=20, K=5 | dataclass field defaults | `tests/unit/test_window_splitter.py::test_default_params_match_adr_0014` |
| 2 | Insufficient data raises ValueError | `min_required` check | `test_insufficient_data_raises` |
| 3 | Rolling advance = test_bars per fold | loop `train_start = k * test_bars` | `test_K_folds_advance_by_test_window` |
| 4 | Negative params rejected at construction | `__post_init__` validation | `test_negative_params_rejected` |
| 5 | Acceptance gate AND-combine (Sharpe + MC) | `passed = sharpe AND mc` | `tests/unit/test_wfa_acceptance_gate.py::*` |
| 6 | DSR NOT в gate (Q2 verdict — informational) | no `dsr_gate_passed` key | `test_dsr_not_in_gate_decision` |
| 7 | Runner invokes replay 2×K times (IS + OOS per fold) | per-fold double dispatch | `tests/unit/test_walk_forward_runner.py::test_runner_invokes_replay_per_fold` |

## Data flow

```
synthetic OHLCV df
    ↓
WindowSplitter.split(total_bars) → 5× (train_start, train_end, test_start, test_end)
    ↓ per fold
WalkForwardRunner.run():
    train_window = df.iloc[tr_start:tr_end]
    is_result = replay_fn(train_window, config)   # IS replay
    test_window = df.iloc[te_start:te_end]
    oos_result = replay_fn(test_window, config)   # OOS replay
    folds.append({oos_is_sharpe_ratio, oos_trades_df, ...})
    ↓
evaluate_acceptance_gate(fold_oos_is_sharpe_ratios, mc_p_value)
    ↓
{passed, sharpe_gate_passed, mc_gate_passed, failed_folds, ...}
```

## Referenced by

- [[wfa-reporter]] — consumes runner output (3-Sharpe routing)
- [[mc-permutations]] — sister statistical method (sign-flip + block bootstrap)
- [[backtest-harness]] — base replay engine

## Related

- [[../decisions/0014-walk-forward-train2000-test500]] — locked WFA params
- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — origin ADR
- [[dsr]] — DSR consumer (sigma_sr from per-fold Sharpes)
- [[../../trading/concepts/walk-forward-validation]] — concept page
- [[../sprints/sprint-10-wfa-dsr-mc]] — sprint where walk-forward was created
- [[../architecture/acceptance-criteria]] — T3 OOS/IS Sharpe gate (≥0.7).

## Sources

- `src/backtest/walk_forward.py` — implementation (T2+T3+T7)
- `tests/unit/test_window_splitter.py` (6 tests)
- `tests/unit/test_walk_forward_runner.py` (5 tests)
- `tests/unit/test_wfa_acceptance_gate.py` (4 tests)
- `tests/integration/test_wfa_pipeline.py` (1 end-to-end test)
