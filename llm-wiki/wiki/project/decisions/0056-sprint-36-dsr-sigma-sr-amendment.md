---
title: ADR 0056 — Sprint 36 DSR Sigma_SR Sourcing Amendment
type: decision
tags: [adr, sprint-36, dsr-amendment, sigma-sr-sourcing, n-trials-thresholds, methodology-correction]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/sprints/sprint-35-testnet-donchian-risk.md
  - project/pre-s36-backlog.md
---

## Status

Accepted (2026-04-27) — implemented в S36 T6. Paired ADR 0055.

## Context

S35 T4 quant-stats-reviewer review identified 2 carry-overs (H1 + H2):
- **H1**: `donchian_runner.py:191-193` falls back к per-fold OOS Sharpe stdev as `sigma_SR` proxy when `cross_trial_sharpes.json` empty. Statistically inadmissible per Bailey & López de Prado (2014) — within-trial variance ≠ cross-trial variance.
- **H2**: Variable `aggregate_oos_sharpe` (donchian_runner.py:171) computed as arithmetic mean of fold-level OOS Sharpes, NOT pooled OOS Sharpe over all OOS trades. Naming creates downstream confusion в cross_trial log entries + DSR computation.

S35 T4 verdict was robust to H1 (FAIL conjoint independent direction) — but methodology gap formally documented. S36 δ activation = future live demo evaluation will hit same code path, must fix BEFORE next measurement.

## Decision

### Sigma_SR sourcing hierarchy (binding)

1. **PREFERRED** — `cross_trial_sharpes.json` contains ≥ 3 entries:
   ```python
   sigma_SR = statistics.stdev([entry.oos_sharpe for entry in entries])
   n_trials = len(entries)  # pooling protocol (a) per S33 T3
   ```

2. **DEGENERATE** — 1-2 entries:
   ```python
   sigma_SR = float("nan")
   n_trials = 1  # no multi-testing correction
   dsr_status = "DSR_UNDERPOWERED — informational only. n_trials < 3"
   ```

3. **INADMISSIBLE FALLBACK (REMOVED)** — per-fold Sharpe stdev as `sigma_SR` proxy. Confounds within-trial noise с cross-trial selection variability per Bailey 2014 eq.12. Previously `donchian_runner.py:191-193` — REMOVED в S36 T6.

### N_trades thresholds для DSR reporting

| n_trades | DSR | Status |
|----------|-----|--------|
| < 10 | NaN | `INSUFFICIENT_TRADES` (variance undefined) |
| 10 ≤ n < 30 | computed | `UNDERPOWERED` (informational only) |
| ≥ 30 | computed | `GATE_ELIGIBLE` |

Replaces previous `n < 2` guard в `compute_dsr` (too permissive).

### Variable naming correction

`aggregate_oos_sharpe` (donchian_runner.py:171) → **`trial_mean_fold_oos_sharpe`**

Rationale: clarifies arithmetic mean of fold OOS Sharpes vs pooled trade-level OOS Sharpe. Both metrics reported где applicable:

- `trial_mean_fold_oos_sharpe`: arithmetic mean of K fold OOS Sharpes — used для cross-trial log entry
- `pooled_trade_oos_sharpe`: trade-level Sharpe over ALL OOS trades concatenated — used для overall trial Sharpe metric

## Consequences

### Positive
- Methodology corrected per Bailey 2014 — no inadmissible fallback
- Honest reporting за small-n regimes (NaN + UNDERPOWERED flags vs. silent computation)
- Variable rename eliminates downstream confusion в reports + cross_trial entries

### Negative
- S33 cross_trial archive (`data/cross_trial_sharpes_v0.6.json`) used old naming convention — backward-compat needed when reading historical archive
- S35 T4 Donchian backtest `data/donchian_backtest_results.json` used `aggregate_oos_sharpe` field — historical record не invalidated, но naming inconsistency

### Neutral
- No verdict change on existing measurements (all FAIL conjoint regardless of fallback choice — verified per S35 T4 quant-stats H1 conservative direction analysis)

## Implementation

S36 T6 paired commit:
- `src/backtest/donchian_runner.py` — REMOVE lines 191-193 inadmissible fallback, replace с sourcing hierarchy
- `src/analytics/dsr.py` — add `compute_dsr_with_status()` with N-thresholds
- `src/analytics/cross_trial_log.py` — add `entry_count() -> int` helper
- `tests/unit/test_dsr_sigma_sr_amendment.py` — 5 NEW tests verifying each branch

## Follow-ups

- S33 archive backward-compat: `data/cross_trial_sharpes_v0.6.json` may need migration script если future audit reads its `aggregate_oos_sharpe` field
- S35 archive: same consideration для `data/donchian_backtest_results.json`
- Future S37+ ADR может extend N_trials thresholds based на TESTNET data accumulation

## Related

- ADR 0014 (WFA acceptance thresholds — S22 baseline source)
- ADR 0050 (S33 Trading Restart — cross_trial reset precedent)
- ADR 0052 (S34 amendment LOCKED — n_trials counter Item #10)
- ADR 0055 (S36 δ activation — paired primary ADR)
- pre-s36-backlog.md (ROUND 4 binding consilium trail)
- Bailey & López de Prado 2014 (DSR formula + sigma_SR pooling)
- S35 T4 quant-stats-reviewer review (carry-over source)

---

## S37 Amendment (ROUND 5 quant-stats-reviewer verdict)

### Calibration baseline correction (ADR 0055 SD-6 dependency)

`S22_SYNTHETIC_SHARPE` constant в `src/analytics/live_trade_reporter.py:28`:

| Variant | Value | Source |
|---------|-------|--------|
| **S36 T7 ORIGINAL** | 6.17 | T1 aggregate Sharpe per `sprint-22-4h-test.md` |
| **S37 T6 AMENDED** | **2.96** | mean of fold OOS Sharpes [1.93, -2.92, 1.32, 12.70, 1.78] |

Rationale: T1 aggregate 6.17 inflated by fold #4 outlier (Sharpe=12.70 at n≈12 trades — small-n + fold concentration extreme). Mean fold = 2.96 conservative baseline для calibration ratio target ≥0.7 (live_Sharpe / S22_synthetic).

Δ calibration ratio interpretation:
- live_Sharpe=2.0 vs 6.17 baseline → ratio 0.32 (FAIL <0.7) — too pessimistic
- live_Sharpe=2.0 vs 2.96 baseline → ratio 0.68 (FAIL <0.7) — borderline conservative
- live_Sharpe=2.5 vs 2.96 baseline → ratio 0.84 (PASS) — realistic target

### Sharpe computation semantics (clarification per quant-stats C3)

Three statistically-distinct Sharpe variants used в codebase. Future audits MUST cite which:

| Metric | Definition | Use site |
|--------|------------|----------|
| `trial_mean_fold_oos_sharpe` | arithmetic mean of K WFA fold OOS Sharpes (donchian_runner.py:171 post-S36 T6 rename) | cross_trial log entry, sigma_SR pooling |
| `pooled_trade_oos_sharpe` | trade-level Sharpe over ALL OOS trades concatenated | overall trial Sharpe metric |
| `live_sharpe` | per-TradeRecord pnl_quote returns annualized via `sqrt(bars_per_year/avg_bars_per_trade)` | δ live demo evaluation (live_trade_reporter.py:67) |

Trial mean ≠ pooled trade-level в general. Live Sharpe (per-trade) ≠ WFA Sharpe (bar-level equity curve).

ADR 0056 sigma_SR sourcing hierarchy unchanged. n_trades thresholds unchanged. Only constants + semantic doc amended.
