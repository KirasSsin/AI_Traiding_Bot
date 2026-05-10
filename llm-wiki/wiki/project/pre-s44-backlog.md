---
title: Pre-S44 Backlog — WFA retrofit (research presets acceptance gate restoration)
type: backlog
tags: [sprint-44, wfa-retrofit, dsr, mc, acceptance-gate, atr-breakout, volume-breakout]
created: 2026-05-10
updated: 2026-05-10
status: active
sources:
  - llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md
  - llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
---

# Pre-S44 Backlog

## Контекст

S40+S41+S42+S43 shipped atr_breakout (10 combos) + volume_breakout с UI polish, но research presets ВСЁ ЕЩЁ возвращают `verdict: "RAW"` — acceptance discipline (T1-T6 + DSR + MC + N_trials counter) skipped. S42 trader-expert flagged structural blocker: research runners use sequential additive PnL, replay_engine uses Kelly-compounded — incompatible accounting.

S44 = restore epistemic discipline.

## S44 PHASE 2 Brainstorming Trail

### Pre-PHASE 3 verification (ground truth)

Before plan locks, verified maintainer claims via inline checks:

| Claim | Maintainer | Reality | Action |
|-------|------------|---------|--------|
| `_autoscale_wfa_params` exists в codebase | YES (S38) | YES — `src/dashboard/backtest_runner.py:213` (used line 829) | Trader REVISE Q3 partial wrong — function exists; но still need ADR per-TF table |
| Pre-S44 N_trials count | 9 | **0** (cross_trial_sharpes.json empty `{"trials":[]}`) | Post-S44 N = 0 + 11 = 11 (lower DSR penalty than expected) |
| Per-TF data volumes | Many ETH/SOL 4H combos data-limited | 9/10 PASS ≥ 4520; **only BTCUSDT 1D fails** (1212 bars) | Single WFA_FAIL_DATA combo, не широкая проблема |

### Q1 — PnL accounting unification

- **Verdict ROUND 1:** REVISE → option (d) Keep sequential-additive
- **Trader rationale:** atr_breakout_runner CANNOT be wrapped в replay_engine (3 documented structural gaps in `atr_breakout_runner.py:5-12`: sl_atr_mult wiring / long_only suppression / Kelly sizing). Sequential-additive valid signal-quality discriminator для DSR/MC/T1-T6 (ADR 0052). Forcing Kelly = re-implement Wilder ATR stop priority внутри replay_engine = больше work чем WFA itself.
- **Maintainer accept:** Sound — preserves ADR 0060/0061 baselines (+819.81% verbatim), avoids signal engine rewrite scope creep.

### Q2 — Replay engine adoption

- **Verdict ROUND 1:** REVISE → option (b) Per-runner WFA loops
- **Trader rationale:** donchian_runner pattern works because `donchian_strategy` IS wired к replay_engine signal API. atr_breakout/volume_breakout signal engines NOT wired — building adapter = effectively rewriting `_backtest_single` inside replay_engine. Correct DRY: don't duplicate WFA orchestration logic, one execution kernel per strategy is fine. Need: `_run_atr_breakout_wfa()` в `atr_breakout_runner.py` + same для volume_breakout.
- **Maintainer accept:** Coupled с Q1 — both REVISE together as joint architectural answer.

### Q3 — WFA params (default vs per-combo)

- **Verdict ROUND 1:** REVISE → ADR 0014 defaults + per-TF minimum table в ADR 0064
- **Trader claim:** `_autoscale_wfa_params` НЕ exists в codebase
- **Maintainer correction:** Function EXISTS в `src/dashboard/backtest_runner.py:213`. Trader checked wrong files. Auto-scale logic уже handles small data edge case (S38 dashboard extension).
- **Final verdict:** ADR 0014 defaults → auto-scale via existing function. ADR 0064 documents per-combo bar counts table:

| Combo | Bar count | Default min (4520) | Verdict |
|-------|-----------|-------------------|---------|
| BTCUSDT 15M | 116372 | PASS | full WFA |
| BTCUSDT 1H | 29093 | PASS | full WFA |
| BTCUSDT 4H | 19056 | PASS | full WFA |
| **BTCUSDT 1D** | **1212** | **FAIL** | **WFA_FAIL_DATA OR auto-scale (k=3, train=400)** |
| ETHUSDT 15M | 116372 | PASS | full WFA |
| ETHUSDT 1H | 29093 | PASS | full WFA |
| ETHUSDT 4H | 7273 | PASS | full WFA |
| SOLUSDT 15M | 116372 | PASS | full WFA |
| SOLUSDT 1H | 29093 | PASS | full WFA |
| SOLUSDT 4H | 7273 | PASS | full WFA |
| volume_breakout BTC 4H | 7273 | PASS | full WFA |

### Q4 — DSR per-combo

- **Verdict ROUND 1:** CONFIRM (a)
- **Final:** Each of 11 combos = separate DSR computation. Operator pick = one preset = one DSR.

### Q5 — MC permutations

- **Verdict ROUND 1:** CONFIRM (a) n=2000 для всех
- **Final:** Standard sign_flip_p_value(n_iterations=2000), matches donchian_runner pattern.

### Q6 — N_trials counter

- **Verdict ROUND 1:** EXPAND — verify pre-S44 count
- **Verified:** Pre-S44 = **0** (cross_trial_sharpes.json empty)
- **Final:** Per-combo separate (10 atr + 1 vb = 11 NEW trials). Post-S44 N = 0 + 11 = **11**. DSR sigma_SR penalty per Bailey 2014: sigma_SR(N=11) ≈ 1.25 × baseline (much smaller than projected N=20 = 1.43×).
- **Verification task в S44:** must wire `CrossTrialLog.append_trial()` per combo с `oos_sharpe = mean(fold_oos_sharpes)`.

### Q7 — Verdict transition (RAW → PASS/FAIL)

- **Verdict ROUND 1:** CONFIRM (a) с mandatory three-valued sub-verdict
- **Final:** Replace `verdict: "RAW"` с:
  - `WFA_PASS` — все T1-T6 + DSR + MC clean
  - `WFA_FAIL` — failed на statistical grounds (T1 OR T2 OR DSR OR MC)
  - `WFA_FAIL_DATA` — failed T5 due к data volume (BTCUSDT 1D case)
- Distinguishing data-limited vs strategy-limited prevents operator confusion ("not enough data" ≠ "doesn't work").

### Q8 — Sprint scope

- **Verdict ROUND 1:** CONFIRM (a) WFA retrofit only
- **Final:** S44 = WFA only (focused architectural sprint). UI deferrals (drawdown chart, per-trade markers, monthly heatmap) → S45.

## Cross-cutting concerns

- **CC1 (RESOLVED):** Q1+Q2 coupled — both REVISE accepted as joint answer (per-runner WFA loop on `_backtest_single`, sequential-additive preserved).
- **CC2 (RESOLVED):** Q3 phantom function claim — verified function exists. Auto-scale handles edge case via existing infrastructure.
- **CC3 (NEW):** WFA loop must call `_backtest_single(fold_df, combo_params)` per fold — careful с lookahead. ATR period (max 21) needs warm-up bars — фold split must include lookback buffer to avoid bias на first bar of test set.
- **CC4 (NEW):** Cache key для backtest results (currently hash на strategy_id + symbol + interval + start + end + force flag) must NOT include WFA-specific state. Existing cache contract preserved.

## Escalations к user

- **ESC-1 RESOLVED inline:** ETH/SOL 4H data volumes verified 7273 bars (above 4520 minimum). Only BTCUSDT 1D requires WFA_FAIL_DATA OR auto-scale (k=3, train=400). Maintainer decision: **use auto-scale** (existing `_autoscale_wfa_params` handles).
- **ESC-2 RESOLVED inline:** Pre-S44 N_trials = 0 verified от `cross_trial_sharpes.json`. ADR 0064 N_trials section: "0 → 11 после S44".

## S44 Scope (locked)

### In-scope (S44)

1. **`_run_atr_breakout_wfa()`** в `src/backtest/atr_breakout_runner.py` — WindowSplitter folds + per-fold `_backtest_single` call + aggregate OOS trades + DSR + MC.
2. **`_run_volume_breakout_wfa()`** в `src/backtest/volume_breakout_runner.py` — same pattern.
3. **WFA fold lookback warm-up** — split must reserve `max(atr_period, atr_stop_period)` bars before each fold для warmup.
4. **Acceptance gate evaluation** — call `evaluate_acceptance_gate()` on per-fold OOS sharpes + MC p-value.
5. **Verdict computation** — three-valued: WFA_PASS / WFA_FAIL / WFA_FAIL_DATA.
6. **Envelope extension** — `research_runner_envelope.py` accepts new fields: `acceptance_gate`, `dsr`, `dsr_pass`, `mc_p_value`, `wfa_params`, `wfa_total_bars`, `fold_sharpe_ratios`, `failed_folds`. Currently null sentinels — must populate.
7. **Dashboard rendering** — JS `renderResult()` shows full TIER 1-6 + DSR + MC table when `verdict != "RAW"` (existing legacy WFA path).
8. **CrossTrialLog wiring** — `append_trial(sprint="S44", symbol=combo_key, oos_sharpe=mean_fold_oos)` per combo. 11 entries после S44 ship.
9. **WFA_FAIL_DATA visualization** — distinct verdict color (amber, не red FAIL) с tooltip "data-limited, retry when more bars".
10. **`/api/strategy/{id}/info`** + dashboard preset description — mention WFA acceptance gate restored (description updates).
11. **ADR 0064** — full document c per-combo verdict table (post-WFA actual results), N_trials accounting, sub-verdict schema.
12. **Wiki sync** — sprint-44 page + index.md + log.md + current-state.md.

### Out-of-scope (S45+)

- Drawdown subchart, per-trade markers, monthly returns heatmap (S43 deferred UI).
- F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10 (S37/S38 long-standing).
- 12mo MAINNET-promotion ADR (needs δ live data).
- legacy WFA presets (ema/mean_reversion/donchian) envelope adoption — nice-to-have but не blocking.

## Files identified для edit (PHASE 3 plan input)

- `src/backtest/atr_breakout_runner.py` — add `_run_atr_breakout_wfa()` (NEW function, ~80 lines)
- `src/backtest/volume_breakout_runner.py` — add `_run_volume_breakout_wfa()` (NEW function, ~70 lines)
- `src/backtest/research_runner_envelope.py` — extend signature к accept WFA results dict
- `src/dashboard/backtest_runner.py` — dispatch вызывает WFA path для research presets
- `src/dashboard/static/dashboard.js` — RAW mode block updated к show WFA verdict tables
- `src/analytics/cross_trial_log.py` — read once для verify N_trials base; write 11 new entries
- `data/cross_trial_sharpes.json` — 11 new trial entries (S44 sprint tag)
- `tests/unit/test_atr_breakout_wfa.py` (NEW) — WFA loop coverage
- `tests/unit/test_volume_breakout_wfa.py` (NEW) — WFA loop coverage
- `tests/integration/test_atr_breakout_dashboard_contract.py` — extend для verdict transition
- `llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md` (NEW)
- `llm-wiki/wiki/project/sprints/sprint-44-wfa-retrofit.md` (NEW)

## Next phase

PHASE 3 — `superpowers:writing-plans` skill creates `2026-05-10-sprint-44-wfa-retrofit.md` plan. ~14 TDD tasks.
