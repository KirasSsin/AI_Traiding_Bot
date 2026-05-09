---
title: MC permutations — sign-flip + block bootstrap
type: component
tags: [backtest, mc, statistics, sprint-10]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/mc_permutation.py
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# MC permutations (sign-flip + block bootstrap)

**TL;DR:** Pure-function module computing two MC permutation tests on per-trade returns array per ADR 0015. `sign_flip_p_value` (primary, N=2000) flips per-trade pnl sign random ±1; `block_bootstrap_p_value` (secondary, block 20-50 bars) preserves autocorrelation. Test statistic: `|mean(returns)|` two-sided. p-value = fraction permuted statistics ≥ observed.

## Public API

| Symbol | Path |
|--------|------|
| `sign_flip_p_value` | `src/backtest/mc_permutation.py::sign_flip_p_value` |
| `block_bootstrap_p_value` | `src/backtest/mc_permutation.py::block_bootstrap_p_value` |

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | N=2000 default per ADR 0015 | function default arg | `tests/unit/test_mc_sign_flip.py::*` |
| 2 | Empty returns → NaN (defensive) | `len(returns) == 0` check | `test_empty_returns_returns_nan` |
| 3 | Seed reproducibility | `rng = np.random.default_rng(seed)` | `test_seed_reproducibility` |
| 4 | p-value в [0, 1] always | `count_extreme / n_iterations` | `test_p_value_in_unit_interval` |
| 5 | Sign-flip preserves marginal distributions | `signs * returns` (no replace) | ADR 0015 line 35 |
| 6 | Block bootstrap block_size > N → NaN | guard `block_size > len(returns)` | `test_empty_returns_returns_nan` |
| 7 | Block bootstrap preserves autocorrelation | resamples blocks not single bars | `tests/unit/test_mc_block_bootstrap.py::test_block_size_affects_resampling` |
| 8 | Block bootstrap on constant returns → p=1.0 | resampling preserves values, only orders | T6 spec correction (implementer caught) |

## Configuration

Settings (future):
- `wfa_mc_iterations: int = 2000` (ADR 0015)
- `wfa_mc_block_size: int = 30` (range 20-50 per ADR 0015)

## Test statistic

Both tests use `|mean(returns)|` as proxy для Sharpe sign. Two-sided test:
- `count_extreme = N(|mean(perm)| ≥ |mean(observed)|)`
- `p = count_extreme / n_iterations`

## Referenced by

- [[walk-forward]] — `evaluate_acceptance_gate` consumes p-value (L2 gate per ADR 0015)
- [[wfa-reporter]] — reports both p-values (sign-flip primary, block bootstrap secondary)

## Related

- [[../decisions/0015-sign-flip-mc-permutations-n2000]] — locked N=2000, p ≤ 0.05
- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — origin ADR
- [[backtest-harness]] — replay engine provides OOS returns consumed by sign-flip test
- [[../../trading/concepts/monte-carlo-permutations]] — concept page
- [[../sprints/sprint-10-wfa-dsr-mc]] — sprint where mc-permutations was created
- [[../architecture/acceptance-criteria]] — T4 MC p-value gate (≤0.05).

## Sources

- `src/backtest/mc_permutation.py` — implementation (T5+T6)
- `tests/unit/test_mc_sign_flip.py` (5 tests)
- `tests/unit/test_mc_block_bootstrap.py` (4 tests)
