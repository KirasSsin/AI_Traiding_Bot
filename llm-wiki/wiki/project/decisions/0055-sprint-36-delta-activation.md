---
title: ADR 0055 — Sprint 36 δ TESTNET Activation (HaltGate Wire-up + B1 Critical Fix)
type: decision
tags: [adr, sprint-36, testnet-activation, halt-gate-wireup, b1-critical-fix, hybrid-duration, n-trials-freeze, mainnet-defer]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s36-backlog.md
---

## Статус

Принято (2026-04-27) — реализовано в S36 (`feature/sprint-36-delta-activation` → тег `v0.1.0-alpha.36`). Парный ADR 0056 (поправка DSR sigma_SR, тот же спринт).

## Контекст

Consilium ROUND 4 после S35 (3 агента — trader-expert + trading-logic-reviewer + quant-stats-reviewer + ROUND 2 trader-expert binding на Q4) — КОНСЕНСУС на (b) δ TESTNET activate. α Donchian FAIL conjoint (S35), направление ЗАКРЫТО. Инфраструктура δ готова (HaltGate + 5 настроек + MAINNET-exclusion DOUBLE-LOCKED), но НЕ ПОДКЛЮЧЕНА.

7 гипотез стратегий протестированы суммарно — все FAIL conjoint. Лучшее свидетельство S22 (DSR=0.996, MC p=0.018 после правки S33) — поддерживает путь вперёд несмотря на реальность малых выборок.

pre-s36-backlog.md ROUND 1+2 документирует 5 вопросов Q1-Q5 + 7 обязательных предварительных обязательств + критические находки (B1 + B2 + B3 + заморозка N_trials).

## Решение (8 под-решений)

### SD-1 — Гибридный вариант продолжительности (H) дословно per ROUND 2 trader-expert BINDING

> δ TESTNET работает бессрочно до наступления ОДНОГО из событий:
> (a) Срабатывание HaltGate (просадка/серия убытков/таймаут без сделок — ADR 0053 без изменений)
> (b) Достижение ворот PASS (n≥50 + ADR 0052/0053 conjoint)
> (c) 12 месяцев по календарю = **ворота продвижения на MAINNET, НЕ остановка.** Если n<50 на момент проверки → «информационно, недостаточно данных» + TESTNET продолжается если оператор не остановит. MAINNET заблокирован.
> Промежуточная контрольная точка в 6 месяцев не предусмотрена (конфликт с ADR 0053 строка 62 — таймаут без сделок 6 мес.).

Обоснование: в ROUND 1 было три позиции (12мес+6мес / одиночное событие / n-ворота 36мес). ROUND 2 trader-expert CHANGED → гибридный (H). Критическая находка: ADR 0053 строка 62 уже обязывает «≥ 6 месяцев без n ≥ 30 закрытых сделок → остановка». Промежуточная точка в 6 мес. избыточна + конфликт полномочий + вектор snooping.

### SD-2 — Обязательное исправление критического бага B1

Параметры `MEAN_REVERSION_S17_RELAXED_PARAMS` LOCKED ДОЛЖНЫ быть подключены к live-пути ДО первой сделки дня-1. Текущее состояние:
- `MeanReversionRsiBBStrategy.__init__` использует дефолт `bb_k=2.0` (в LOCKED dict spec `bb_std_mult=1.5`)
- `Settings.strategy_rsi_oversold=30/overbought=70` по умолчанию (LOCKED: 35/65)
- `src/__main__.py:124-131` передаёт дефолты Settings, игнорирует LOCKED константу

Pre-commit #7 из pre-s35-backlog.md нарушен молча. Должен быть исправлен в S36 T2.

Реализация: переименовать `bb_k` → `bb_std_mult` параметр конструктора, добавить `and_gate_required` параметр конструктора, добавить фабрику classmethod `from_locked_s17_params()`, условное подключение в `__main__.py` когда `s35_demo_active=True`.

### SD-3 — Определение многодневной просадки

multiday_dd = HWM с момента временной метки активации `s35_demo_active=True`. Персистентность: таблица SQLite `equity_snapshots` расширена OR новая строка `s35_activation_log`.

Временная метка активации сохраняется при первом запуске с `s35_demo_active=True`. Безопасность перезапуска: читать при последующих запусках из SQLite, не из Settings (переменные окружения могут изменяться без изменения кода).

Расчёт multiday_dd: `(hwm_since_activation - current_total) / hwm_since_activation`. Возвращает 0 если current >= hwm.

### SD-4 — Таблица маппинга HaltTrigger → ReasonCode

| HaltTrigger | ReasonCode |
|-------------|------------|
| `DD_INTRADAY` | `HALT_S36_DD_INTRADAY` |
| `DD_MULTIDAY` | `HALT_S36_DD_MULTIDAY` |
| `CONSECUTIVE_LOSSES` | `HALT_S36_CONSECUTIVE_LOSSES` |
| `NO_TRADE_TIMEOUT` | `HALT_S36_NO_TRADE_TIMEOUT` |

Уникальные коды (НЕ переиспользованы HALT_DRAWDOWN_L*/HALT_FLASH_CRASH) сохраняют атрибуцию в audit-log согласно вердикту trading-logic-reviewer ROUND 1. Канонический счётчик reason codes: 45→49.

### SD-5 — Протокол возобновления после остановки HaltGate

Остановка, вызванная HaltGate, требует проверки оператором. Путь переопределения HMAC НЕ применим (OverrideStore не относится к остановкам HaltGate — см. trading-logic C5 из ROUND 1).

Механизм возобновления: ручной сброс FSM через подкоманду `--reconcile-only` CLI ИЛИ обновление SPRINT_STATE (решение оператора). Оператор ДОЛЖЕН задокументировать выводы проверки в записи audit trail halt_log.

Обоснование: триггеры HaltGate — предзафиксированные ворота (просадка/серии/таймаут) — автоматическое возобновление нарушило бы дисциплину anti-snooping. Проверка оператором = честное признание.

### SD-6 — Адаптированная методология ворот для live данных

Per quant-stats-reviewer ROUND 1 дословно:

1. **Оценщик live Sharpe** — вычисляется по returns per-TradeRecord (НЕ по equity на уровне баров WFA). Аннуализируется через `sqrt(bars_per_year / avg_bars_per_trade)`.
2. **Замена T6 OOS/IS** — коэффициент калибровки live/синтетический = `live_Sharpe / S22_synthetic_Sharpe`. Базовый показатель S22 предварительно зарегистрирован (константа в коде, НЕ изменяемая в runtime).
3. **Ворота MC** — sign-flip если n≥20 сделок; block-bootstrap если n≥40 сделок. Ниже порога → MC отображается как флаг `"MC_INSUFFICIENT_N"`.
4. **Пороги DSR** per ADR 0056:
   - n_trades < 10 → DSR=NaN, status=`INSUFFICIENT_TRADES`
   - 10 ≤ n_trades < 30 → DSR вычислен, status=`UNDERPOWERED`
   - n_trades ≥ 30 → DSR вычислен, status=`GATE_ELIGIBLE`

### SD-7 — Заморозка N_trials на уровне 7 для δ live demo

δ использует `MeanReversionRsiBBStrategy` с `MEAN_REVERSION_S17_RELAXED_PARAMS` = та же гипотеза, что и в S22 (повторная оценка, не новый поиск стратегии). Штраф Bailey 2014 за множественное тестирование применяется к поиску гипотез, НЕ к форвардной оценке предварительно зарегистрированной стратегии.

Константа `DELTA_N_TRIALS_LOCKED = 7` в `src/analytics/live_trade_reporter.py` с дословным комментарием-перечислением:

```python
# Cumulative mean-reversion family hypothesis count (ADR 0055 SD-7):
# S13 EMA crossover, S15 mean-reversion strict, S17 mean-reversion relaxed,
# S20 mean-reversion 15M, S22 mean-reversion 4H, S33 multi-symbol mean-reversion,
# S35 Donchian breakout. δ TESTNET = S22 hypothesis re-evaluation (frozen).
DELTA_N_TRIALS_LOCKED: int = 7
```

### SD-8 — Критерии продвижения на MAINNET ОТЛОЖЕНЫ до S37+

Предзафиксированные пороги MAINNET сейчас преждевременны без контекста данных TESTNET. После 12-месячной проверки TESTNET (per SD-1 вариант (c)) оператор решает:

- (i) ADR S37+ предварительно регистрирует критерии продвижения на MAINNET (n≥X / Sharpe≥Y / и т.д.) дословно
- (ii) MAINNET откладывается бессрочно (TESTNET продолжается ИЛИ пауза β)

Инвариант MAINNET-exclusion остаётся DOUBLE-LOCKED (live_trading + флаг testnet + validate_assignment) — путь к MAINNET закрыт до тех пор, пока ADR S37+ явно его не откроет.

Шаблон подтверждения оператора для ADR S37+ (дословно per ADR 0052):

> «Статистические данные по состоянию на v0.7 [результаты данных TESTNET]; данное продвижение на MAINNET отражает [сводку свидетельств]. Я авторизую активацию MAINNET с предзафиксированными воротами приёмки [критерии]. Нового поиска гипотез нет.»

## Последствия

### Положительные
- Путь вперёд заблокирован (anti-snooping) — у оператора есть чёткий следующий шаг
- Исправление критического бага B1 предотвращает молчаливое использование шумовых параметров S15 при активации δ
- 4 НОВЫХ ReasonCode сохраняют атрибуцию в audit-log
- Гибридный вариант продолжительности (H) учитывает все 3 замечания ревьюеров без введения риска отказа от 36 месяцев
- Заморозка N_trials корректна per Bailey 2014 (нет ложного штрафа DSR за повторную оценку)

### Отрицательные
- 12-месячная проверка TESTNET может быть статистически неопределённой (ожидается n≈13 при базовом показателе S22 ~13/год). Разговор о продвижении на MAINNET может откладываться бессрочно.
- Остановка по HaltGate = ручная проверка оператором (нет автоматического возобновления) — операционные издержки
- Заморозка N_trials=7 может быть оспорена в будущих аудитах, если строгий ревьюер засчитает повторную оценку как новое испытание

### Нейтральные
- Нет регрессий кода — все обязательства ADR 0053 сохранены
- Канонические счётчики FSM без изменений (16/30/74) — только reason codes 45→49

## Реализация

Per план S36 (`plans/2026-04-27-sprint-36-delta-activation.md`):
- T1 (этот коммит): ADR 0055 + ADR 0056 парные
- T2: исправление B1 + фабрика + условное подключение
- T3: 4 метода источников состояния
- T4: подключение HaltGate в RuntimeManager._tick
- T5: ReasonCode +4 HALT_S36_*
- T6: рефакторинг DSR sigma_SR (реализация ADR 0056)
- T7: Live trade reporter
- T8: синхронизация wiki

## Дальнейшие шаги

**Действия оператора при активации δ:**
1. Записать переменную `s35_demo_active=True` в production .env
2. Перезапустить бота — первый запуск записывает временную метку активации в SQLite
3. Еженедельно контролировать halt_log + trade_history в SQLite
4. При 12 мес. + n<50: выбрать — продолжить ИЛИ остановить ИЛИ ADR S37+ для обсуждения MAINNET
5. При срабатывании триггера остановки: проверить halt_log оператором, решить — ручной сброс FSM ИЛИ честный выход S37+

## Связанные

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-й честный выход v0.6)
- ADR 0052 (S34 поправка к критериям приёмки LOCKED)
- ADR 0053 (S35 активация δ TESTNET — предшественник парный)
- ADR 0054 (S35 предварительная регистрация α Donchian — направление ЗАКРЫТО)
- ADR 0056 (этот — поправка DSR sigma_SR, парный)
- pre-s36-backlog.md ROUND 4 consilium trail
- Bailey & López de Prado 2014 (DSR + дисциплина предварительной регистрации)
- [[../sprints/sprint-36-delta-activation]] — спринт delivery record
- Hudson & Urquhart 2021 (критика t-стат тяжёлых хвостов + крипто-реальность разреженных сигналов)
- [[../components/halt-gate-wireup]] — wire-up component (RuntimeManager._tick integration)
- [[../components/live-trade-reporter]] — adapted live monitoring per SD-6 (Sharpe + calibration + MC)
- [[../components/delta-activation-playbook]] — operator step-by-step activation procedure
