---
title: Pre-S10 backlog — brainstorm verdicts trail
type: backlog
tags: [sprint-10, brainstorm, phase-2, verdicts, trader-expert, wfa, dsr, monte-carlo]
created: 2026-04-25
updated: 2026-04-25
status: open
sources:
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0024-sprint-9-data-quality-types-analytics.md
  - project/components/dsr.md
  - project/components/backtest-harness.md
---

# Pre-S10 backlog — PHASE 2 brainstorming trail

## S10 scope (maintainer-locked)

**D = Walk-Forward Analysis (WFA) + DSR integration + Monte Carlo permutations**

Builds on:
- ADR 0014 (walk-forward train=2000, test=500, K=5, embargo=20, OOS/IS Sharpe ≥ 0.7)
- ADR 0015 (sign-flip MC permutations N=2000, p ≤ 0.05, block bootstrap secondary)
- S9 B2 DSR foundation (`src/analytics/dsr.py`)
- S2-era backtest engine (revive + extend `src/backtest/replay_engine.py` + `vector_backtest.py`)

## S10 PHASE 2 brainstorming verdicts

### Q1 — WFA window unit (bars vs hours)

**ROUND 1 verdict:** CONFIRM (trader-expert)

**Decision:** Bars. Settings `wfa_train_bars: int = 2000`, `wfa_test_bars: int = 500`, `wfa_embargo_bars: int = 20`, `wfa_k_folds: int = 5`. ADR 0014 explicit, multi-timeframe = YAGNI v0.1.

**ROUND 2:** N/A (CONFIRM).

---

### Q2 — Acceptance gate (Sharpe-only vs Sharpe + DSR)

**ROUND 1 verdict:** REVISE (trader-expert)

**Maintainer original recommendation:** Add DSR ≥ 0.95 as hard AND third gate layer.

**Trader chosen option:** DSR computed and reported per fold + aggregate, but NOT added as hard gate. Gate remains ADR 0014 (OOS/IS Sharpe ≥ 0.7) AND ADR 0015 (MC p ≤ 0.05).

**Trader rationale:**
- K=5 folds × 500 OOS bars × ~1 trade/4-6 bars × 40-60% flat = ~40-80 trades per fold
- DSR coefficient of variation > 0.3 на N=40 with BTC return distributions
- DSR ≥ 0.95 calibrated для long IS periods (thousands trades), NOT 5-fold OOS windows
- Hard gate would reject borderline-valid strategies at unacceptable Type II error rates
- Calibrate DSR threshold empirically AFTER seeing real fold trade counts in S10 execution

**ROUND 2:** NOT triggered. Maintainer accepts (concrete CV > 0.3 estimate + Type II error rationale technically stronger).

**Final accepted decision:** DSR computed per fold + aggregate (informational). Hard gate threshold TBD post-S10 empirical calibration. WFA gate = ADR 0014 + 0015 only.

**Wiki/code follow-ups:**
- Update `wiki/project/components/dsr.md` "Referenced by" — change "DSR consumed by walk-forward acceptance gate" → "DSR reported alongside walk-forward results; hard gate threshold TBD post-empirical calibration"

---

### Q3 — MC permutation type

**ROUND 1 verdict:** CONFIRM (trader-expert)

**Decision:** Sign-flip per-trade pnl_pct sign randomly, N=2000 permutations. Test statistic = Sharpe или mean return. p-value = fraction of permuted statistics ≥ observed. Per ADR 0015 line 35 "сохраняет маргинальные распределения PnL". Signal-flip rejected (CPU expensive — N=2000 replays). Bar-flip rejected (breaks autocorrelation, block bootstrap better для that).

**ROUND 2:** N/A (CONFIRM).

---

### Q4 — Backtest engine (revive S2 vs new architecture)

**ROUND 1 verdict:** CONFIRM с mandatory scope caveat (trader-expert)

**Decision:** Revive + extend `src/backtest/replay_engine.py` + `vector_backtest.py`. NEW `src/backtest/walk_forward.py` orchestrates rolling windows, calls `run_replay()` per fold.

**Mandatory caveat (must capture в plan):** `walk_forward.py` MUST extract per-trade `trades_df` from each fold's result and pass к `compute_dsr()` directly. Must NOT use `_compute_metrics()` Sharpe as DSR input — they are different series.

**Dual-Sharpe trap (cross-cutting concern):**
1. **Bar-returns Sharpe** (`replay_engine._compute_metrics()`, `sqrt(8760)` annualized) — used для ADR 0014 OOS/IS ratio gate
2. **Per-trade Sharpe** (`compute_dsr()` internal, not annualized) — DSR consumes per-trade `TradeRecord`
3. **Display Sharpe** (WFA reporter, `sqrt(8760)` fixed factor) — informational only

`walk_forward.py` design: route `trades_df` → DSR path; `equity_df` → existing Sharpe gate path.

**ROUND 2:** N/A.

**Wiki/code follow-ups:**
- Update `backtest-harness.md` "Open questions" section с dual-Sharpe distinction documentation

---

### Q5 — Per-fill integration (per-trade DSR vs per-fill granularity)

**ROUND 1 verdict:** CONFIRM (trader-expert)

**Decision:** DSR consumes `list[TradeRecord]` (per-trade). FillRecord NOT consumed by DSR в S10. Per-fill granularity для DSR = artificial N inflation (correlated within trade — entry/exit fill of same trade, ms apart). Bailey & López de Prado assume IID returns at trade level.

**ROUND 2:** N/A.

---

### Q6 — Annualization factor (S9 deferred)

**ROUND 1 verdict:** REVISE (trader-expert)

**Maintainer original recommendation:** Derive from trade frequency `len(trades) / observation_period_years`.

**Trader chosen option:** Fixed constant `sqrt(365 * 24) = sqrt(8760)` для display Sharpe в WFA reporter, consistent с existing `replay_engine._compute_metrics()` line 51 convention.

**Trader rationale:**
- Derive from observed trade frequency = circular (function of strategy's own activity level)
- 2 strategies с identical edge but different bar-holding periods → non-comparable Sharpe (defeats purpose)
- ADR 0014 ratio (OOS/IS Sharpe ≥ 0.7) requires SAME factor in both windows — fixed constant guarantees, derived would differ between IS/OOS
- DSR formula already annualization-independent (S9 verified)
- Existing `replay_engine` uses `sqrt(8760)` — correct convention для 24/7 crypto 1H

**ROUND 2:** NOT triggered. Maintainer accepts (circularity argument + IS/OOS consistency requirement technically sound).

**Final accepted decision:** Fixed `sqrt(8760)` annualization для display Sharpe только. DSR unaffected (cancels). ADR 0014 gate Sharpe = bar-returns Sharpe, already annualized via existing `_compute_metrics()`.

**Wiki/code follow-ups:**
- **Pre-existing bug discovered:** `src/backtest/vector_backtest.py` uses `sqrt(365 * 24 * 60)` (1m bar assumption). For 1H BTCUSDT — off by `sqrt(60)` ≈ 7.7×. **Must-fix в S10 backtest audit.**
- Document fixed constant convention в `backtest-harness.md`

---

### Q7 — DSR n_trials > 1 sigma_SR (S9 deferred)

**ROUND 1 verdict:** CONFIRM (trader-expert)

**Decision:** Implement `n_trials > 1` support в `compute_dsr()` by accepting optional `sigma_sr: float` parameter (caller supplies). `walk_forward.py` aggregator computes `sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K])` and calls `compute_dsr(all_oos_trades, n_trials=K, sigma_sr=sigma_sr)`. Closes `NotImplementedError` path в `src/analytics/dsr.py:107` (S9 placeholder explicitly для S10).

**Caveat:** sigma_SR estimate с N=5 folds = noisy (small sample). Document caveat в WFA report. Aggregate DSR is informational (per Q2 decision), so noise acceptable.

**ROUND 2:** N/A.

**Wiki/code follow-ups:**
- Update `dsr.md` invariant row 7 — remove "NYI v0.1", document `sigma_sr` parameter contract

---

## Cross-cutting concerns

1. **Dual-Sharpe series (Q4 + Q6 + Q7):** plan author MUST explicitly name 3 distinct series и map each к correct consumer:
   - Bar-returns Sharpe → ADR 0014 OOS/IS ratio gate
   - Per-trade Sharpe → DSR internal computation
   - Display Sharpe → WFA reporter (informational)

2. **VectorBacktester annualization bug:** `src/backtest/vector_backtest.py` `sqrt(365*24*60)` wrong для 1H (assumes 1m bars). Must-fix в S10 backtest audit BEFORE results trusted.

3. **Q2 + Q7 combined:** DSR computed but not gated. sigma_SR for aggregate DSR. Both informational. Empirical calibration of DSR threshold deferred к follow-up sprint.

4. **quant-stats-reviewer mandatory:** на DSR n_trials > 1 implementation (Q7 closes S9 NotImplementedError) + WFA aggregation logic + MC permutation correctness. Same agent caught BLOCKER в S9 (Pearson kurtosis) — relied on for formula correctness.

## Escalation items для user

None. All engineering/architecture scope.

## Transition

PHASE 2 complete. SPRINT_STATE → phase=3-planning. Next: PHASE 3 plan write (`superpowers:writing-plans` skill) → trace map + bite-sized TDD tasks.

## Related

- [[decisions/0014-walk-forward-train2000-test500]] — WFA window + Sharpe gate locked decisions
- [[decisions/0015-sign-flip-mc-permutations-n2000]] — MC permutation N=2000 + p ≤ 0.05 locked
- [[decisions/0024-sprint-9-data-quality-types-analytics]] — DSR foundation (S9)
- [[decisions/0025-sprint-10-wfa-dsr-mc]] — Sprint 10 ADR
- [[sprints/sprint-10-wfa-dsr-mc]] — Sprint 10 page
- [[components/dsr]] — `compute_dsr` API (extend с sigma_sr)
- [[components/backtest-harness]] — S2 backtest engine (revive)
- [[architecture/development-workflow]] — PHASE 2 binding protocol
