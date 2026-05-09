---
title: ADR 0054 — Sprint 35 α Donchian Breakout Pre-Registration LOCKED
type: decision
tags: [adr, sprint-35, donchian, breakout, long-only, pre-registration, n-trials-5, locked]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s35-backlog.md
---

# ADR 0054 — Sprint 35 Предварительная регистрация α Donchian Breakout LOCKED

## Статус

Принято (2026-04-27) **ДО** любого просмотра данных бэктеста — дисциплина anti-snooping per Bailey & López de Prado 2014.

## Контекст

Consilium ROUND 3 проголосовал за α (пробой Donchian) как параллельный синтетический трек:
- 7-я гипотеза, тестируемая за всё время проекта (счётчик N_trials pooled = 5)
- Ортогональная парадигма к возврату к среднему (пробой следованием тренду)
- Совместим с FSM long-only (без SHORT сигналов — инвариант `long_only=True` per ADR 0009)
- Оценка объёма ~280 строк кода

Штраф DSR при N_trials=5 рассчитан по протоколу pooling sigma_SR Bailey 2014 (a) — значительный, но не запретительный.

## Решение

Реализовать long-only стратегию пробоя Donchian с LOCKED параметрами ДО запуска бэктеста.

### LOCKED параметры (`DONCHIAN_LONG_ONLY_PARAMS`)

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| `lookback_n` | 20 | Классический Donchian (Faber 2007) стандартный период |
| `exit_lookback_n` | 10 | Выход по половинному периоду (вариант Turtle Trading) |
| `atr_period` | 14 | Стандартный Wilder ATR, согласованный с indicators.atr() |
| `atr_stop_mult` | 2.0 | Трейлинг-стоп 2× ATR (скорректированный по волатильности) |
| `signal_side_mode` | "long_only" | Инвариант FSM SignalSide (без SHORT) |
| `min_atr_filter` | None | Нет нижнего порога волатильности — принимать все пробои |

### Символ + таймфрейм LOCKED

- Символ: BTCUSDT (один символ — обходит корреляционное сдутие согласно уроку S33)
- Таймфрейм: 4H (согласовано с треком δ для сравнения в равных условиях)

### Счётчик N_trials

| Спринт | Накоплено испытаний | Стратегия |
|--------|---------------------|-----------|
| S13 | 1 | EMA crossover |
| S15 | 2 | Возврат к среднему строгий |
| S17 | 3 | Возврат к среднему ослабленный |
| S22 | 4 | Возврат к среднему 4H |
| **S35 α** | **5** | **Пробой Donchian** |

Штраф DSR при N_trials=5: `sigma_SR_pooled = sqrt((1/N) * sum(sharpe_i²))`. Скорректированный порог Bonferroni alpha per Bailey 2014.

### 6 Предзафиксированных ворот приёмки (дословно per ADR 0052 amended LOCKED)

| Ворота | Порог | Блокирует? |
|--------|-------|-----------|
| T5 n_trades raw | >= 50 | ДА |
| T5 n_eff (один символ → n_eff = n_raw) | >= 50 | ДА |
| T6 OOS/IS Sharpe | >= 0.7 | ДА |
| MC p-value | <= 0.05 | ДА |
| DSR (N_trials=5) | >= 0.95 | ДА |
| acceptance_gate.sharpe_gate_passed | per-fold >= 0.7 | ДА |

PASS = ВСЕ ворота одновременно AND. FAIL conjoint = направление α ЗАКРЫТО, запасной вариант β (пауза) per pre-commit #8.

### Запрещено без нового ADR

- ❌ Постфактум подбор параметров (snooping)
- ❌ SHORT сигналы (инвариант FSM long_only)
- ❌ Мультисимвол (один символ BTCUSDT LOCKED)
- ❌ Другой таймфрейм (4H LOCKED)
- ❌ Повторное использование данных OHLCV вне предварительно зарегистрированного диапазона

## Последствия

**Положительные:** Anti-snooping LOCKED до обращения к данным. N_trials корректно подсчитан (=5). Совместимость с FSM long-only — инженерных блокеров нет.

**Отрицательные:** Штраф DSR при N=5 делает порог более строгим, чем при N=4. При FAIL → направление α PERMANENTLY CLOSED.

**Нейтральные:** Влияния на производственную торговлю нет (только синтетический бэктест).

## Связанные

- ADR 0052 (поправка S34 LOCKED — источник ворот)
- ADR 0053 (S35 δ TESTNET — основной парный трек)
- pre-s35-backlog.md (ROUND 3 binding)
