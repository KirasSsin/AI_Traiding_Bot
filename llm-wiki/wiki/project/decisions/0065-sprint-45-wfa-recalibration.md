---
title: "0065. Sprint 45 — WFA recalibration + quant discipline + uniform 3.3y data"
type: decision
tags: [adr, sprint-45, wfa-recalibration, dsr, cross-trial-log, data-uniform, honest-close]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s45-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-45-wfa-recalibration.md
---

# 0065. Sprint 45 — WFA recalibration

**Статус:** accepted
**Дата:** 2026-05-10

## Контекст

S44 retrofit раскрыл что ВСЕ 11 research presets WFA_FAIL под ADR 0014 default WFA params. Reviewer concerns: B1 cross_trial_log dedup blocker, C1 n_trials per-strategy bug, B2 train slice docs gap. Operator выявил 8.7y BTC binance file как inconsistent exception (origin unknown).

S45 = data uniform + quant corrections + 1 recalibration attempt per ESC-1.

## Решения

### Решение A — Uniform 3.3y data
Removed `BTCUSDT_4h_binance.parquet` (8.7y exception) from `PARQUET_BY_COMBO` registry. Archived в `data/_archive/`. ADR 0060 baseline recomputed: BTC 4H = +174.29% (было +819.81% on 8.7y), Sharpe 1.94 (было 1.11), n_trades 28 (было 69). LOCKED params unchanged.

### Решение B — CrossTrialLog idempotency (B1 fix)
`CrossTrialLog.append_trial()` теперь updates existing entry on duplicate (sprint, symbol) tuple OR appends new. Prevents log poisoning от dashboard reruns. Reset log к empty (S44 26 duplicate entries invalidated). Position preserved on update.

### Решение C — n_trials per-strategy (C1 fix)
Default `run_research_wfa(n_trials=1)` (fail-safe). atr_breakout family explicit `n_trials=10`. volume_breakout explicit `n_trials=1`. Correct DSR multi-testing penalty per Bailey 2014.

### Решение D — WFA recalibration (ADR 0014 amendment)
Low-freq tier (4H/D): `test_bars=250, train_bars=1500, k_folds=5, embargo=20` (min_required=2770). High-freq (5M/15M/1H) unchanged. Anti-snooping: trade-frequency derivation table committed BEFORE recalibration run в ADR 0014 amendment.

### Решение E — B2 train slice documentation
For LOCKED-params strategies, train_slice intentionally NOT passed к backtest_fn. Documented в `research_wfa.py` docstring + inline comment. `wfa_params["train_bars"]` reflects test window positioning, не actual IS isolation.

## Таблица вердиктов S45 (post-recalibration)

| Combo | n_oos | DSR | MC p | Вердикт | Failed criteria |
|-------|-------|-----|------|---------|-----------------|
| atr_breakout BTCUSDT 15M | 9 | NaN | 0.989 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout BTCUSDT 1H | 16 | 0.127 | 0.022 | **WFA_FAIL** | n_eff, t5, sharpe, dsr |
| atr_breakout BTCUSDT 4H | 7 | NaN | 0.642 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout BTCUSDT 1D | 0 | — | — | **WFA_FAIL_DATA** | data_volume |
| atr_breakout ETHUSDT 15M | 7 | NaN | 0.419 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout ETHUSDT 1H | 14 | 0.000 | 0.409 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout ETHUSDT 4H | 4 | NaN | 1.000 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout SOLUSDT 15M | 7 | NaN | 0.963 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout SOLUSDT 1H | 15 | 0.000 | 0.560 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| atr_breakout SOLUSDT 4H | 10 | 0.000 | 0.061 | **WFA_FAIL** | n_eff, t5, sharpe, mc |
| volume_breakout BTCUSDT 4H | 22 | 0.851 | 0.330 | **WFA_FAIL** | n_eff, t5, sharpe, mc |

### Delta vs S44 baseline

Low-freq tier (test_bars=250) сделал 4H combos **хуже**, не лучше — fewer bars per fold = fewer signals:
- BTCUSDT 4H: 10 trades → **7**
- ETHUSDT 4H: 6 → **4**
- SOLUSDT 4H: 20 → **10**
- volume_breakout: 38 → **22**

Единственное положительное изменение: volume_breakout DSR улучшилось 0.000 → 0.851 (от n_trials=11→1 fix per Решение C). Но n_eff/t5/sharpe gates все ещё fail.

## ESC-1 (a) — честное закрытие портфеля

Per pre-commit operator decision (ESC-1 (a)): максимум 1 recalibration attempt. **0/11 WFA_PASS** = trigger conditions met → S46 = honest portfolio close.

**Корень проблемы:** structural T5 floor (n≥50 trades в pooled OOS) hostile к ВСЕМ research strategies на 3.3y window:
- atr_breakout fires 0.5–2.5 trades per OOS fold
- volume_breakout fires ~4 trades per fold
- Pooled across 5 folds = 4–20 trades максимум (vs 50 floor)

**Не fitting issue, не strategy issue, не data issue — фундаментальный sample size constraint.** Strategies могут быть perfectly valid in-sample (atr_breakout BTC 4H 3.3y +174%), но T5_FLOOR=50 не достижим без significantly larger trade frequency OR significantly longer data.

## Последствия

**Плюсы:**
- B1+C1+B2 discipline corrections shipped — production code clean.
- Uniform data baseline (3.3y) = single mental model для operator.
- WFA recalibration честно протестирована per anti-snooping discipline.
- Честный вердикт как основа для S46 portfolio close decision.

**Минусы:**
- Все 11 research presets confirmed WFA_FAIL. Не viable для live capital deployment.
- Path B (new strategies) excluded per operator. S46 = portfolio close, не replacement.
- Sequential-additive ≠ live execution Kelly (per ADR 0012). Backtest = signal-quality discriminator.

**Carry-overs к S46+:**
- S46: honest portfolio close — mark all 11 presets WFA_FAIL definitively, document strategic implications.
- UI deferrals (drawdown subchart, per-trade markers, monthly heatmap) — S43 carry, S46+.
- S37/S38 long-standing (F8/M1-M4/Item 7/Item 10) — S47.

## Верификация

- Unit tests: ~970 (+9: 5 dedup + 4 tier + 1 default check)
- Integration tests: ~58 (+4: 2 n_trials + 2 tier wiring)
- mypy --strict: 0 errors
- Canonical counts: 16/30/74/56 (UNCHANGED)

## Связанные

- [[../sprints/sprint-45-wfa-recalibration]]
- [[../plans/2026-05-10-sprint-45-wfa-recalibration]]
- [[../pre-s45-backlog]]
- [[0014-walk-forward-train2000-test500]] (amended S45 — low-freq tier)
- [[0052-sprint-34-acceptance-criteria-amendment]]
- [[0056-sprint-36-dsr-sigma-sr-amendment]]
- [[0060-sprint-40-atr-breakout-pre-registration]] (amended S45 — 3.3y baseline)
- [[0064-sprint-44-wfa-retrofit]]
