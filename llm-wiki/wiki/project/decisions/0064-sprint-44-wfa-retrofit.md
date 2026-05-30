---
title: "0064. Sprint 44 — WFA retrofit (research presets acceptance gate restoration)"
type: decision
tags: [adr, sprint-44, wfa-retrofit, dsr, mc, acceptance-gate, atr-breakout, volume-breakout, parity, sprint-51]
created: 2026-05-10
updated: 2026-05-30
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s44-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-44-wfa-retrofit.md
---

# 0064. Sprint 44 — WFA retrofit

**Status:** accepted
**Date:** 2026-05-10

## Контекст

S40+S41+S42+S43 ship atr_breakout (10 combos) + volume_breakout как research presets с `verdict: "RAW"` — acceptance discipline (T1-T6 + DSR + MC + N_trials counter) skipped. S42 trader-expert flagged structural blocker: research runners use sequential additive PnL, replay_engine uses Kelly-compounded.

S44 = restore epistemic discipline.

## Решение

**Sequential-additive preserved.** Per Q1 trader-expert REVISE: replay_engine architecturally blocked (3 documented gaps в `atr_breakout_runner.py:5-12`). Sequential-additive — valid signal-quality discriminator для T1-T6/DSR/MC. Pre-S44 baselines (+819.81% etc.) preserved verbatim.

**Per-runner WFA loop.** Per Q2 REVISE: `_run_atr_breakout_wfa()` + `_run_volume_breakout_wfa()` thin wrappers использующие shared `run_research_wfa()` helper в `src/backtest/research_wfa.py`. `WindowSplitter` folds + per-fold `_backtest_single()` call + aggregate OOS trades + DSR + MC + acceptance gate.

**N_trials counter:** Pre-S44 verified empty (0 trials в `data/cross_trial_sharpes.json`). Post-S44 = 10 trials (BTCUSDT D skipped — WFA_FAIL_DATA имеет sharpe=NaN). DSR sigma_SR computed from cross_trial_sharpes pool per ADR 0056 (degenerate <3 entries → fallback к n_trials=1 path).

**Three-valued verdict:** `WFA_PASS` / `WFA_FAIL` / `WFA_FAIL_DATA` — distinguishing data-limited failures от statistical failures.

## Per-combo verdict table (S44 actual results)

| Combo | n_trades | DSR | MC p | Verdict | Failed criteria |
|-------|----------|-----|------|---------|-----------------|
| atr_breakout BTCUSDT 15M | 9 | NaN | 0.989 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout BTCUSDT 1H | 16 | 0.127 | 0.022 | **WFA_FAIL** | n_eff, t5, sharpe, dsr |
| atr_breakout BTCUSDT 4H | 10 | 0.000 | 0.669 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout BTCUSDT 1D | 0 | — | — | **WFA_FAIL_DATA** | data_volume (1212 bars < 4520) |
| atr_breakout ETHUSDT 15M | 7 | NaN | 0.419 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout ETHUSDT 1H | 14 | 0.000 | 0.409 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout ETHUSDT 4H | 6 | NaN | 0.350 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout SOLUSDT 15M | 7 | NaN | 0.963 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout SOLUSDT 1H | 15 | 0.000 | 0.560 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| atr_breakout SOLUSDT 4H | 20 | 0.000 | 0.053 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |
| volume_breakout BTCUSDT 4H | 38 | 0.000 | 0.199 | **WFA_FAIL** | n_eff, t5, sharpe, mc, dsr |

**Honest interpretation:** ALL 11 combos failed WFA OOS validation. Common root cause = T5 floor (n≥50 trades в pooled OOS) — strategies fire too few trades в OOS windows under ADR 0014 default WFA setup (train=2000/test=500/k=5). Pre-S44 RAW verdicts (e.g. +819% BTCUSDT 4H) hid this OOS validation failure.

## Последствия

**Pros:**
- Acceptance discipline restored — operator видит honest WFA verdict, не inflated training PnL.
- WFA_FAIL_DATA sub-verdict distinguishes data limitation от strategy failure.
- N_trials counter wired = future Bailey 2014 cumulative deflation correct.
- Pre-S44 baselines preserved (no number changes).

**Cons:**
- All current research presets show WFA_FAIL post-retrofit. Operator confidence в atr_breakout/volume_breakout strategies должен update — autoresearch sweep selection survives full-period optimization but не WFA OOS gates под текущих settings.
- ADR 0014 default WFA params (train=2000/test=500) не aligned с low-frequency strategies (5-20 trades per fold). Future S45+ may explore reduced WFA params для strategy-specific T5 calibration.
- Sequential-additive ≠ live execution Kelly (per ADR 0012). Operator должен понимать backtest = signal-quality discriminator vs production sizing.

**Carry-overs к S45+:**
- UI deferrals (drawdown subchart, per-trade markers, monthly heatmap) — S45.
- WFA params recalibration для low-frequency strategies (alternative train/test ratios) — S45 OR S46.
- Long-standing S37/S38: F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10.

## Verification

- Unit tests: ~970 passed (+10 vs S43 baseline 956).
- Integration tests: ~58 passed (+4).
- mypy --strict: 0 errors.
- Canonical counts: 16/30/74/56 unchanged.
- Manual smoke: all 11 combos returning honest WFA verdict, dashboard renders TIER 1-6 + DSR + MC table.

## Дополнение D4 (S51, 2026-05-30) — live/backtest ATR parity (windowed re-seed fix)

**Проблема (trading-logic-reviewer S50 carry-over).** WFA в S44 валидировал
параметры через full-history vectorized Wilder ATR (`atr_breakout_runner._atr`,
которая идентична `src.signalgen.indicators.wilder_atr`). Но live
`ATRBreakoutStrategy.on_bar` пересчитывал ОБА Wilder ATR (signal period=9 и
stop period=21) на ограниченном sliding deque (`maxlen = max(period) + 10 = 31`).
Wilder ATR — рекурсивный RMA; на скользящем окне он **пере-инициализируется
(re-seed) каждый бар** после насыщения буфера → live ATR расходится с
full-history путём, который WFA подтвердил. Тот же класс дефекта, что S50
исправил в Supertrend (`_update_atr`).

**Измерено эмпирически (BTCUSDT 4H, 7273 бара, LOCKED params):**

| Метрика | Значение (windowed vs full-history) |
|---------|-------------------------------------|
| stop ATR (p=21): max rel diff | 38.72% |
| stop ATR (p=21): mean rel diff | 5.72% (88.7% баров > 1%) |
| signal ATR (p=9): max rel diff | 10.44% |
| **SIGNAL-BAR FLIPS (windowed vs full-history, при ОДИНАКОВОЙ [-2] индексации)** | **16** |
| entries/exits windowed | 13 / 13 |
| entries/exits full-history | 9 / 9 |

16 расхождений сигналов = live торговал иначе, чем WFA валидировал →
**MATERIAL** на SHIPPED LOCKED стратегии.

**Решение (S51 D4, TDD).** `on_bar` теперь держит оба Wilder ATR
**инкрементально по полной истории** (helper `_WilderATR`, O(1)/бар) — зеркало
`indicators.wilder_atr` и backtest runner `_atr`, без windowed re-seed.
Сигнальная индексация (`atr[-2]` / `closes[-2,-3]`) и entry/exit семантика
СОХРАНЕНЫ — менялись только ATR-значения. Параметры НЕ менялись (windowed
re-seed БЫЛ багом). Parity тесты (`tests/unit/test_atr_breakout_parity.py`):
streaming ATR == full-history `_atr` в пределах 1e-9 на 7273-баровой серии
BTCUSDT 4H + 600-баровой синтетике. Full unit suite GREEN (1245 passed), mypy 0.

### Открытый follow-up (НЕ в scope D4 — flagged оператору)

При измерении обнаружен **второй, более крупный** дефект, отдельный от
windowed re-seed: **ATR-index offset**. Live `on_bar` оценивает breakout по
`close[T-1]` + `atr_signal[T-1]` (на бар позже), тогда как research kernel
использует данные через `i-1` с заполнением `open[i]` (research entry bar i ⇔
streaming decision bar i-1). Из-за этого с full-history ATR live даёт 9 entries
против 28 у research kernel на BTCUSDT 4H (9 vs 28). Это исправление меняло бы
больше, чем re-seed, и требует отдельного решения (потенциально новый ADR про
streaming↔backtest signal-bar parity для всех breakout-стратегий). Помечено для
оператора, в D4 НЕ трогалось.

## Статус

accepted (2026-05-08) — amended D4 windowed-ATR parity fix (2026-05-30, S51)

## Связанные

- [[../sprints/sprint-44-wfa-retrofit]]
- [[../plans/2026-05-10-sprint-44-wfa-retrofit]]
- [[0014-walk-forward-train2000-test500]]
- [[0052-sprint-34-acceptance-criteria-amendment]]
- [[0056-sprint-36-dsr-sigma-sr-amendment]]
- [[0060-sprint-40-atr-breakout-pre-registration]]
- [[0061-sprint-41-atr-breakout-multi-combo-presets]]
- [[0062-sprint-42-atr-breakout-hardening]]
- [[0063-sprint-43-ui-polish]]
