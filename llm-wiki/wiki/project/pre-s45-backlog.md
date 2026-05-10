---
title: Pre-S45 Backlog — Quant discipline corrections + uniform 3.3y data + WFA recalibration
type: backlog
tags: [sprint-45, wfa-recalibration, dsr, cross-trial-log, data-uniform]
created: 2026-05-10
updated: 2026-05-10
status: active
sources:
  - llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
---

# Pre-S45 Backlog

## Контекст

S44 retrofit раскрыл что ВСЕ 11 research presets WFA_FAIL под ADR 0014 default WFA params (test_bars=500, k_folds=5). Common root cause: T5 floor (n≥50 trades в pooled OOS) — strategies fire 5-38 trades в OOS windows.

Дополнительно operator выявил:
1. `BTCUSDT_4h_binance.parquet` (8.7y) был exception от standard 3.3y data — не известного origin (не в git, downloaded externally до S40). Operator решение: **uniform 3.3y everywhere**.
2. S44 reviewer concerns: B1 cross_trial_log dedup blocker, C1 n_trials per-strategy bug, B2 train slice unused docs.

S45 = data uniform + quant corrections + WFA recalibration (1 attempt only per ESC-1).

## Operator decisions (binding)

- **ESC-1:** **(a) 1 recalibration attempt only.** Если post-S45 WFA still FAIL ВСЕ 11 → S46 honest portfolio close, **не Path B** (operator excluded new strategies).
- **ESC-2:** **(a) Pure Path A diagnostic.** S45 = quant fix + recalibration. Operator decision на S46 после verdict.
- **Data:** **Uniform 3.3y** для всех combos. Remove `BTCUSDT_4h_binance.parquet` exception.
- **New strategies (Path B):** **EXCLUDED.** Доводим existing portfolio.

## S45 PHASE 2 Brainstorming Trail

### Q1 — Strategic direction
- **ROUND 1:** REVISE → Pure Path A (recalibration first, deferred Path B decision)
- **Final:** Pure Path A diagnostic. Operator excluded new strategies entirely.

### Q2 — WFA recalibration approach
- **ROUND 1:** REVISE → universal lever (test_bars 500→250, train_bars 2000→1500 для 4H/D tier), не per-strategy config knobs
- **Trader rationale:** Per-strategy config = O(N×M) maintenance surface. Single principled lever cleaner.
- **Final:** ADR 0014 amendment — 4H/D low-frequency tier. ADR 0065 must contain trade-frequency derivation table BEFORE recalibration run (anti-snooping).
- **CC:** Если хотя бы 1 combo PASS → cross_trial_log reset (treats as N_trials+1 fresh event per Bailey 2014).

### Q3 — Sprint scope
- **ROUND 1:** CONFIRM quant only S45
- **Final:** UI deferrals (drawdown chart, markers, heatmap) → S46. S37/S38 carry-overs → S47.

### Q4 — Cross_trial_log dedup strategy (B1 fix)
- **ROUND 1:** REVISE → guard в `CrossTrialLog.append_trial()`, не callers (architectural)
- **Trader rationale:** Caller pattern = future runners forget guard. Composite key (sprint, symbol_composite) deduplication.
- **Final:** Reset `data/cross_trial_sharpes.json` к empty. Add idempotency guard в `append_trial()` checking (sprint, symbol_composite) tuple uniqueness. All current 26 duplicate entries from S44 dashboard reruns invalidated.

### Q5 — n_trials per-strategy (C1 fix)
- **ROUND 1:** CONFIRM с amendment — change `run_research_wfa` default `n_trials=11` → `1` (fail-safe)
- **Final:**
  - Default `n_trials=1` (fail-safe)
  - `_run_atr_breakout_wfa()` explicit `n_trials=10` (10 atr family combos)
  - `_run_volume_breakout_wfa()` explicit `n_trials=1` (single hypothesis)
  - Integration test asserts correct N per preset

### Q6 — New strategy seed
- **ROUND 1:** DEFER → S46+ post-recalibration
- **Final:** **EXCLUDED entirely** per operator. Не S46+.

### Q7 — S37/S38 long-standing
- **ROUND 1:** CONFIRM defer к S47+
- **Final:** F8/M1-M4/Item #7/Item #10 → S47.

### Q8 — Sprint task count
- **ROUND 1:** REVISE → 7 tasks (DSR property test → S46)
- **Final operator scope:** 8 tasks (added "remove 8.7y file + ADR 0060 baseline update" as T1):
  1. Remove `BTCUSDT_4h_binance.parquet` from registry → use 3.3y `BTCUSDT_4h.parquet`
  2. Update ADR 0060 baseline (recompute на 3.3y, ≈ +183%)
  3. CrossTrialLog idempotency guard в `append_trial()` + reset log (B1)
  4. n_trials default 11→1 + atr explicit 10 + vb explicit 1 (C1)
  5. B2 train slice docs (inline в research_wfa.py)
  6. ADR 0014 amendment + WFA recalibration code (4H/D tier: test_bars=250, train_bars=1500)
  7. Re-run 11 combos на recalibrated WFA + capture verdict table
  8. ADR 0065 + sprint-45 + wiki sync

## Cross-cutting concerns

- **CC1 RESOLVED:** Q1+Q2 jointly answered (Pure Path A + universal lever).
- **CC2 (anti-snooping):** ADR 0065 must include trade-frequency derivation table BEFORE recalibration run executed.
- **CC3 (Bailey 2014):** Если recalibration produces WFA_PASS → reset cross_trial_log (fresh start for new WFA config). Document в ADR 0065.
- **CC4 (Q5+Q6 interaction):** default n_trials change forces audit of all `_run_*_wfa()` callers. Currently 2 callers — both must explicit pass.

## Escalations к user

- ESC-1 RESOLVED: 1 attempt only.
- ESC-2 RESOLVED: Pure Path A diagnostic, S46 honest close если still fail.
- Data ground truth: Uniform 3.3y baseline.
- Path B EXCLUDED: операtor doesn't want new strategies в roadmap.

## S45 Scope (locked)

### In-scope (8 tasks above)

### Out-of-scope (S46+)

- UI deferrals (drawdown subchart, per-trade markers, monthly heatmap, mobile, theme switch, live trade feed)
- Path B new strategies (EXCLUDED entirely)

### Out-of-scope (S47+)

- F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10 boundary
- DSR property test, WindowSplitter k_folds=1 edge, numpy warning suppress, cross_trial_log read failure test
- Trading-logic C2-C4 minor concerns

## Files identified для edit (PHASE 3 plan input)

- `src/backtest/atr_breakout_runner.py` — `PARQUET_BY_COMBO` update + `_run_atr_breakout_wfa()` n_trials=10
- `src/backtest/volume_breakout_runner.py` — `_run_volume_breakout_wfa()` n_trials=1
- `src/backtest/research_wfa.py` — default `n_trials=1`, B2 train slice doc, low-freq tier params
- `src/analytics/cross_trial_log.py` — `append_trial()` idempotency guard
- `data/cross_trial_sharpes.json` — reset к empty
- `data/BTCUSDT_4h_binance.parquet` — DELETE OR move к archive folder
- `tests/integration/test_atr_breakout_wfa.py` — update asserts (3.3y window, n_trials=10)
- `tests/integration/test_volume_breakout_wfa.py` — assert n_trials=1
- `tests/unit/test_cross_trial_log.py` — new dedup guard tests
- `llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md` — amendment section
- `llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md` — amendment (3.3y baseline)
- `llm-wiki/wiki/project/decisions/0065-sprint-45-wfa-recalibration.md` — NEW
- `llm-wiki/wiki/project/sprints/sprint-45-wfa-recalibration.md` — NEW
- `llm-wiki/wiki/project/architecture/current-state.md` — sprint history + counts
- `llm-wiki/wiki/index.md` + `log.md`

## Next phase

PHASE 3 — `superpowers:writing-plans` skill creates `2026-05-10-sprint-45-wfa-recalibration.md` plan.
