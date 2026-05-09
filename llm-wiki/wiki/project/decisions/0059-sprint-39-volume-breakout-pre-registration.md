---
title: ADR 0059 — Sprint 39 volume_breakout pre-registration LOCKED
type: decision
tags: [adr, sprint-39, volume-breakout, autoresearch-integration, locked, anti-snooping, ru]
created: 2026-05-09
updated: 2026-05-09
status: accepted
sources:
  - llm-wiki/wiki/project/research-evidence/FINAL_STRATEGY.md
  - llm-wiki/wiki/project/research-evidence/CLOSE.md
  - llm-wiki/wiki/project/pre-s39-backlog.md
---

# ADR 0059. Sprint 39 — volume_breakout pre-registration LOCKED

**Статус:** accepted
**Дата:** 2026-05-09
**Предварительный коммит:** anti-snooping LOCK по модели ADR 0054

## Контекст

Autoresearch iter 10 (branch `autoresearch/donchian-may8`) завершил полный sweep 4510 комбинаций параметров через `research/program.md` (toy paradigm, вне kit). Итог: 213 PASS (4.72% pass rate) из 4510 sweep. Победитель sweep#1644 — стратегия `volume_breakout` на 4H BTCUSDT — выбран по centroid proximity (наиболее репрезентативный PASS, не outlier).

Браузинг pre-s39-backlog.md зафиксировал 10 вердиктов trader-expert (Q1-Q9 CONFIRM/REVISE/EXPAND). Данный ADR фиксирует архитектурные и операционные решения S39.

## Решение

### LOCKED параметры verbatim sweep#1644

```python
VOLUME_BREAKOUT_PARAMS = {
    "breakout_period": 20,
    "volume_mult": 1.5,
    "atr_period": 14,
    "atr_stop_mult": 2.0,
    "signal_side_mode": "long_only",
}
```

Символ: BTCUSDT. Таймфрейм: 4H. **НЕ ИЗМЕНЯТЬ без нового ADR (anti-snooping правило).**

Параметры зафиксированы VERBATIM из sweep#1644 per Q1 CONFIRM — без округления до 2 значащих цифр (post-observation tuning REJECTED, см. альтернативы).

### Dashboard preset ENFORCE

Dashboard preset `volume_breakout_iter10` принудительно ограничен 4H + BTCUSDT (backend возвращает 422 при любом другом сочетании). Обоснование Q7: ensemble backtests показывают значительную деградацию на других таймфреймах/символах — любой UI выбор за пределами оптимизированного пространства вводит оператора в заблуждение.

### Production runner — port research execution model

`src/backtest/volume_breakout_runner.py` точно портирует execution-модель из research/ (включая timing, OCO emulation, комиссии). Phase 5 HARD-GATE: `tests/integration/test_volume_breakout_baseline_floor.py` верифицирует что production runner реплицирует baseline в пределах ±0.5% per T5b BLOCKER fix.

## Evidence

### Первичная — held-out OOS (8 месяцев МЕДВЕЖИЙ рынок, 2025-08-26 → 2026-04-26)

Per Q6 REVISE (8mo PRIMARY, trader-expert ROUND 2 binding):

| Метрика | Значение | Интерпретация |
|---------|----------|---------------|
| Период | 8 месяцев (2025-08-26 → 2026-04-26) | BTCUSDT медвежий рынок |
| Sharpe ratio | **+9.96** | 95% CI ±1.5-2.0 (широкий — малая выборка n=17) |
| PnL | **+20.42%** | Quote return за период |
| n_trades | 17 | Малая выборка — необходим Gate 2 накопления |
| Win rate | 47.06% | |
| B&H benchmark | -30.14% | BTCUSDT за тот же период |
| Alpha vs B&H | **+50.56pp** | Strategy outperforms passive hold |

**Это единственное чистое OOS свидетельство.** Held-out период полностью изолирован до начала search loop autoresearch — нет загрязнения от 4510 implicit comparisons.

### Вторичная — полный backtest (3.3 года) ⚠️ предупреждение о загрязнении

Per Q6 REVISE: вторичное свидетельство с явной пометкой champion-bias (Bailey 2014 Section 5):

| Метрика | Значение |
|---------|----------|
| Период | ~3.3 года (полный training range) |
| PnL | +122.66% |
| N implicit comparisons | 4510 |
| Champion-bias inflation | Существенное завышение — оценка НЕ OOS |

**Bailey 2014 предупреждение:** при 4510 implicit comparisons ожидаемый лучший Sharpe случайно достижим даже без реального edge. 3.3y backtest = contaminated estimate. Не использовать как основное свидетельство.

### Сигнал робастности

- 127 PASS конфигурации с Sharpe > 5 (clustering вокруг sweep#1644 centroid)
- Все 9 других протестированных стратегий показали NEGATIVE на том же sweep
- sweep#1644 находится в centroid кластера PASS — не outlier

## Sizing Disclosure (Q5 amendment — обязательные 4 пункта)

1. **Research PnL = discriminator качества сигнала, не проектор долларовой доходности.** Backtests проводятся в нормализованном пространстве (100 unit portfolio).
2. **Под Kelly 0.25× cap реальная account return существенно ниже backtest PnL.** Kelly fraction = 0.25 от full Kelly (консервативный cap до n=10 live trades накопления).
3. **Арифметика "$10k × 1.2042" не переводится в account return.** Комиссии, проскальзывание, partial fills, временно̀е расхождение сигнал/исполнение — все не учтены в backtest PnL напрямую.
4. **Пересмотр Kelly fraction = post n=10 live trades + DSR gate.** До достижения n=10 live trades и успешного DSR gate — Kelly fraction остаётся на floor (фаза 1 Kelly sizing, ADR 0012).

## Acceptance Criteria Invariant (HARD-GATE)

Profit invariant: post-S39 backtest PnL ≥ baseline на обоих gates:

- **8mo held-out PnL ≥ +20.42%** (в пределах ±0.5%)
- **3.3y full PnL ≥ +122.66%** (в пределах ±0.5%)

Phase 5 HARD-GATE: `tests/integration/test_volume_breakout_baseline_floor.py` — **VERIFIED PASS post-T5b.**

## Gate 2 — forward paper-trade (Q2 CONFIRM)

Post-tag alpha.39: forward paper-trade на δ TESTNET, N≥10 signals MINIMUM.

Протокол Gate 2:
- Оператор активирует `volume_breakout_iter10` preset на δ TESTNET
- Мониторинг live Sharpe через `generate_live_report()` (ADR 0055 SD-6)
- DSR gate применяется при n≥20 trades (GATE_ELIGIBLE threshold per ADR 0056)

**IF FAIL Gate 2 → S40 honest close ADR обязателен ДО любого MAINNET-promotion** (fallback clause BINDING).

## N_trials Counter (CC3)

Volume_breakout = pre-registered hypothesis #8 проекта.

| Спринт | Гипотеза | N_trials accumulated |
|--------|---------|---------------------|
| S13 | EMA crossover 1H | 1 |
| S15 | Mean-reversion multi-symbol 1H | 2 |
| S17 | Mean-reversion BTC 1H relaxed | 3 |
| S20 | Mean-reversion BTC 15M | 4 |
| S22 | Mean-reversion BTC 4H | 5 |
| S33 | Mean-reversion multi-symbol 4H | 6 |
| S35 | Donchian breakout 4H | 7 |
| **S39** | **Volume breakout 4H** | **8** |

Cumulative N_trials post-S39: **8**. DSR penalty pooled растёт с каждой гипотезой — будущие гипотезы сталкиваются с более высоким bar (Bailey 2014 eq. 13 DSR sigma_SR: растущий cross-trial sigma_SR).

## Альтернативы

- **(b) Округление до 2 значащих цифр (vol_mult 1.5 → 1.5, breakout_period 20 → 20)** — REJECTED. Любое post-observation изменение параметров = нарушение anti-snooping дисциплины, даже косметическое. Verbatim = единственная допустимая форма.
- **(c) Re-search в окрестности sweep#1644** — REJECTED. Bailey 2014 champion-bias blowup: переоптимизация победителя из 4510 comparisons увеличивает статистическую инфляцию дополнительно.
- **(d) Аугментация фильтрами (EMA200/ADX/RSI/ATR)** — DEFERRED к S40+ per Q9 Option A (baseline LOCK now, ATR filter → следующий спринт). Baseline реплицирована, augmentation = отдельная гипотеза с новым ADR.
- **(e) 3.3y full backtest как PRIMARY** — REJECTED per Q6 REVISE (Bailey 2014 champion-bias явное загрязнение). 8mo held-out = единственное чистое evidence.

## Последствия

### Код

- **+3 ReasonCode**: `ENTRY_LONG_VOLUME_BREAKOUT` / `EXIT_FLAT_VOLUME_CHANNEL` / `EXIT_FLAT_ATR_STOP_VB` (A1)
- `compute_volume_breakout_signals()` helper в `src/signalgen/indicators.py` (A2)
- `VolumeBreakoutStrategy` class в `src/signalgen/volume_breakout_strategy.py` (A3)
- `src/backtest/volume_breakout_runner.py` — production runner replicating research execution model (T5b)
- Dashboard preset `volume_breakout_iter10` с ENFORCE 4H+BTCUSDT (A4)

### Инфраструктура качества

- `tests/integration/test_volume_breakout_baseline_floor.py` — Phase 5 HARD-GATE (A5 + T5b)
- `tests/unit/test_volume_breakout_signals.py` — unit signal fidelity tests
- `wiki/project/research-evidence/` — cherry-picked autoresearch evidence (A6)

### Операционные ограничения

- Gate 2 forward paper-trade BLOCKING к реальному капиталу
- Kelly 0.25× cap обязателен до n=10 live trades
- N_trials=8 учитывается в DSR computation (будущие backtests)

## Связанные документы

- [[../sprints/sprint-39-volume-breakout-tech-debt]] — детали реализации S39
- [[../components/volume-breakout-strategy]] — компонент страница VolumeBreakoutStrategy
- [[../research-evidence/FINAL_STRATEGY]] — sweep#1644 evidence (held-out OOS + full backtest)
- [[../research-evidence/CLOSE]] — autoresearch iter 1-7 falsification record
- [[0054-sprint-35-donchian-pre-registration]] — предыдущая pre-registration LOCKED (модель)
- [[0052-sprint-34-acceptance-criteria-amendment]] — acceptance gates источник
- [[0012-4-phase-kelly-sizing]] — Kelly sizing phases + 0.25× cap rationale
- [[0055-sprint-36-delta-activation]] — δ TESTNET activation (Gate 2 target platform)
