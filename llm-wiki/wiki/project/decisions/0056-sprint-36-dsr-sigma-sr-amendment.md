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

## Статус

Принято (2026-04-27) — реализовано в S36 T6. Парный ADR 0055.

## Контекст

Ревью quant-stats-reviewer в S35 T4 выявило 2 переноса (H1 + H2):
- **H1**: `donchian_runner.py:191-193` использует как запасной вариант стандартное отклонение OOS Sharpe по фолдам в качестве прокси для `sigma_SR` когда `cross_trial_sharpes.json` пуст. Статистически недопустимо per Bailey & López de Prado (2014) — дисперсия внутри испытания ≠ дисперсия между испытаниями.
- **H2**: Переменная `aggregate_oos_sharpe` (donchian_runner.py:171) вычисляется как среднее арифметическое OOS Sharpe по фолдам, НЕ как pooled OOS Sharpe по всем OOS сделкам. Наименование создаёт путаницу в записях cross_trial log + вычислении DSR.

Вердикт S35 T4 был устойчив к H1 (FAIL conjoint независимо от выбора) — но методологический пробел формально задокументирован. Активация δ S36 = будущая оценка live demo обратится к тому же пути кода, исправить ДО следующего измерения.

## Решение

### Иерархия источников Sigma_SR (обязательная)

1. **ПРЕДПОЧТИТЕЛЬНО** — `cross_trial_sharpes.json` содержит ≥ 3 записи:
   ```python
   sigma_SR = statistics.stdev([entry.oos_sharpe for entry in entries])
   n_trials = len(entries)  # pooling protocol (a) per S33 T3
   ```

2. **ВЫРОЖДЕННЫЙ** — 1-2 записи:
   ```python
   sigma_SR = float("nan")
   n_trials = 1  # no multi-testing correction
   dsr_status = "DSR_UNDERPOWERED — informational only. n_trials < 3"
   ```

3. **НЕДОПУСТИМЫЙ ЗАПАСНОЙ ВАРИАНТ (УДАЛЁН)** — стандартное отклонение Sharpe по фолдам как прокси для `sigma_SR`. Смешивает шум внутри испытания с вариабельностью отбора между испытаниями per Bailey 2014 eq.12. Ранее `donchian_runner.py:191-193` — УДАЛЕНО в S36 T6.

### Пороги N_trades для отчётности DSR

| n_trades | DSR | Статус |
|----------|-----|--------|
| < 10 | NaN | `INSUFFICIENT_TRADES` (дисперсия неопределена) |
| 10 ≤ n < 30 | вычислен | `UNDERPOWERED` (только информационный) |
| ≥ 30 | вычислен | `GATE_ELIGIBLE` |

Заменяет предыдущую защиту `n < 2` в `compute_dsr` (слишком мягкая).

### Исправление наименования переменной

`aggregate_oos_sharpe` (donchian_runner.py:171) → **`trial_mean_fold_oos_sharpe`**

Обоснование: проясняет разницу между средним арифметическим OOS Sharpe по фолдам и pooled OOS Sharpe на уровне сделок. Оба показателя отображаются где применимо:

- `trial_mean_fold_oos_sharpe`: среднее арифметическое OOS Sharpe K фолдов — используется для записи в cross-trial log
- `pooled_trade_oos_sharpe`: Sharpe на уровне сделок по ВСЕМ OOS сделкам конкатенированным — используется как общий показатель Sharpe испытания

## Последствия

### Положительные
- Методология исправлена per Bailey 2014 — нет недопустимого запасного варианта
- Честная отчётность для режимов малых выборок (флаги NaN + UNDERPOWERED вместо молчаливого вычисления)
- Переименование переменной устраняет путаницу в отчётах + записях cross_trial

### Отрицательные
- Архив cross_trial S33 (`data/cross_trial_sharpes_v0.6.json`) использует старые соглашения по именованию — нужна обратная совместимость при чтении исторического архива
- Бэктест Donchian S35 T4 `data/donchian_backtest_results.json` использовал поле `aggregate_oos_sharpe` — историческая запись не аннулирована, но несогласованность наименований

### Нейтральные
- Нет изменения вердикта по существующим измерениям (все FAIL conjoint независимо от выбора запасного варианта — проверено per консервативный анализ H1 quant-stats S35 T4)

## Реализация

Парный коммит S36 T6:
- `src/backtest/donchian_runner.py` — УДАЛИТЬ строки 191-193 недопустимый запасной вариант, заменить иерархией источников
- `src/analytics/dsr.py` — добавить `compute_dsr_with_status()` с N-порогами
- `src/analytics/cross_trial_log.py` — добавить вспомогательную функцию `entry_count() -> int`
- `tests/unit/test_dsr_sigma_sr_amendment.py` — 5 НОВЫХ тестов, проверяющих каждую ветку

## Дальнейшие шаги

- Обратная совместимость архива S33: `data/cross_trial_sharpes_v0.6.json` может потребовать скрипта миграции если будущий аудит читает поле `aggregate_oos_sharpe`
- Архив S35: аналогичное соображение для `data/donchian_backtest_results.json`
- Будущий ADR S37+ может расширить пороги N_trials на основе накопленных данных TESTNET

## Связанные

- ADR 0014 (пороги приёмки WFA — источник базового показателя S22)
- ADR 0050 (S33 Trading Restart — прецедент сброса cross_trial)
- ADR 0052 (поправка S34 LOCKED — пункт #10 счётчика n_trials)
- ADR 0055 (S36 активация δ — первичный парный ADR)
- pre-s36-backlog.md (ROUND 4 binding consilium trail)
- Bailey & López de Prado 2014 (формула DSR + pooling sigma_SR)
- Ревью quant-stats-reviewer S35 T4 (источник переносов)
- [[../sprints/sprint-36-delta-activation]] — спринт delivery record (paired с ADR 0055)

---

## Поправка S37 (вердикт ROUND 5 quant-stats-reviewer)

### Коррекция базового показателя калибровки (зависимость ADR 0055 SD-6)

Константа `S22_SYNTHETIC_SHARPE` в `src/analytics/live_trade_reporter.py:28`:

| Вариант | Значение | Источник |
|---------|----------|----------|
| **S36 T7 ОРИГИНАЛ** | 6.17 | Aggregate Sharpe T1 per `sprint-22-4h-test.md` |
| **S37 T6 ПОПРАВЛЕНО** | **2.96** | Среднее OOS Sharpe по фолдам [1.93, -2.92, 1.32, 12.70, 1.78] |

Обоснование: агрегат T1 6.17 завышен выбросом фолда #4 (Sharpe=12.70 при n≈12 сделок — малая выборка + экстремальная концентрация фолда). Среднее по фолдам = 2.96 — консервативный базовый показатель для коэффициента калибровки ≥0.7 (live_Sharpe / S22_synthetic).

Интерпретация изменения коэффициента калибровки:
- live_Sharpe=2.0 vs базовый 6.17 → коэффициент 0.32 (FAIL <0.7) — чрезмерно пессимистично
- live_Sharpe=2.0 vs базовый 2.96 → коэффициент 0.68 (FAIL <0.7) — граничное, консервативно
- live_Sharpe=2.5 vs базовый 2.96 → коэффициент 0.84 (PASS) — реалистичная цель

### Семантика вычисления Sharpe (уточнение per quant-stats C3)

В кодовой базе используются три статистически различных варианта Sharpe. Будущие аудиты ДОЛЖНЫ указывать какой именно:

| Метрика | Определение | Место использования |
|---------|-------------|---------------------|
| `trial_mean_fold_oos_sharpe` | среднее арифметическое OOS Sharpe K фолдов WFA (donchian_runner.py:171 после переименования S36 T6) | запись cross_trial log, pooling sigma_SR |
| `pooled_trade_oos_sharpe` | Sharpe на уровне сделок по ВСЕМ OOS сделкам конкатенированным | общий показатель Sharpe испытания |
| `live_sharpe` | returns per-TradeRecord pnl_quote аннуализированные через `sqrt(bars_per_year/avg_bars_per_trade)` | оценка δ live demo (live_trade_reporter.py:67) |

Среднее по испытанию ≠ pooled уровень сделок в общем случае. Live Sharpe (per-trade) ≠ WFA Sharpe (кривая equity по барам).

Иерархия источников sigma_SR ADR 0056 без изменений. Пороги n_trades без изменений. Изменены только константы + семантическая документация.

---

## Поправка 2 S38 (нахождение F2 ROUND 6 quant-stats)

### Семантика returns для Live Sharpe

Входные данные `compute_live_sharpe()` ДОЛЖНЫ быть `pnl_pct` (дробные доходности), НЕ `pnl_quote` (абсолютный P&L).

| Вариант | Источник | Проблема |
|---------|----------|----------|
| **S37 ОРИГИНАЛ** | `[float(r.pnl_quote) for r in records]` | Смещение если Kelly sizing меняет размеры позиций — крупные позиции искусственно доминируют в соотношении среднее/стд |
| **S38 ПОПРАВЛЕНО** | `[float(r.pnl_pct) for r in records]` | Безразмерные доходности, сравнимые между размерами позиций |

Обоснование: формула Sharpe `(mean/std) * sqrt(N)` требует returns сопоставимой величины. `pnl_quote` масштабируется с размером позиции; `pnl_pct` нормализует. `dsr.py compute_returns()` корректно использует `pnl_pct` — live reporter приведён в соответствие.

Per quant-stats-reviewer ROUND 6: «текущий код использует pnl_quote (live_trade_reporter.py:62), что неявно предполагает фиксированный размер позиции. Если ADR 0057 или будущие изменения риска допускают переменное Kelly sizing, это становится проблемой корректности.»

### Примечание об обратной совместимости

Существующие тесты `test_live_trade_reporter.py` передают `_make_records()` с синтезированными TradeRecords с `pnl_pct = pnl_quote / Decimal("50000")`. Тесты продолжают проходить — меняется только извлечение returns.
