---
title: ADR 0057 — Sprint 37 Carry-overs Hardening (Security HIGH + Trading-logic + Quant + Playbook)
type: decision
tags: [adr, sprint-37, carry-overs-hardening, halt-unknown-symbol, symbol-whitelist, hmac-integrity, clock-injection, calibration-amendment]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/decisions/0018-config-hash-and-override.md
  - project/pre-s37-backlog.md
---

# ADR 0057 — Sprint 37 Hardening переносов

## Статус

Принято (2026-04-27) — реализовано в S37 (`feature/sprint-37-carry-overs-hardening` → тег `v0.1.0-alpha.37`). Парная поправка ADR 0056 (базовый показатель калибровки + семантика Sharpe, тот же спринт).

## Контекст

Consilium ROUND 5 после S36 (3 агента — trader-expert + trading-logic-reviewer + quant-stats-reviewer) — КОНСЕНСУС на (c) сначала спринт переносов S37, затем (a) активация δ TESTNET в S38. Инфраструктура δ ПОДКЛЮЧЕНА LIVE в S36, но 10 переносов остались в pre-s37-backlog.md. Для S37 отобраны 6 критических пунктов, 4 отложены до S38+.

ROUND 5 РАСШИРИЛ исходный подмножество мейнтейнера из 6 пунктов:
- Уникальный ReasonCode HALT_UNKNOWN_SYMBOL обязателен (НЕ переиспользовать существующий) согласно правилу атрибуции audit-log
- Поправка базового показателя калибровки (S22 6.17 → 2.96 среднее по фолдам, консервативно)
- Поправка ADR 0056 для семантики вычисления Sharpe

## Решение (6 под-решений)

### SD-1 — Уникальный ReasonCode HALT_UNKNOWN_SYMBOL

НОВЫЙ ReasonCode `HALT_UNKNOWN_SYMBOL` (канонический 49 → **50**). Отличается от существующих кодов HALT_S36_*, сохраняет атрибуцию аудита halt_log per правило γ primary-wins.

Обоснование (trading-logic-reviewer ROUND 5): переиспользование HALT_S36_CONSECUTIVE_LOSSES для сбоя разрешения символа означало бы, что halt_log навсегда записывает «consecutive losses» когда фактическая причина — «unknown symbol». Уничтожает атрибуцию post-mortem.

Список допустимых значений property-теста (`tests/property/test_request_halt_mapping.py`) расширен на +1 запись. Синхронизация канонического счётчика 49 → 50 в `current-state.md` + `reason-codes-schema.md` + подвале `execution-state-machine.md` + `.github/workflows/ci.yml`.

### SD-2 — Семантика fail-closed для символа

Семантическое изменение `RuntimeManager._check_halt_gate()`:

**До S37**: неизвестный/отсутствующий символ → `logger.warning("runtime.halt_gate_skipped_no_symbol")` + return False (HaltGate неактивен — молчаливый обход).

**После S37**: неизвестный/отсутствующий символ → `logger.error("runtime.halt_gate_unknown_symbol")` + `coordinator.request_halt(HALT_UNKNOWN_SYMBOL)` + `_stopping=True` + return True (остановка fail-closed).

Обоснование: опечатка оператора в переменной окружения → молчаливый пропуск = HaltGate неактивен = бот торгует без защитной сети. Fail-closed предотвращает работу production бота без принудительного применения HaltGate.

### SD-3 — Setting белого списка символов + стартовый баннер

НОВЫЙ Setting `s35_demo_approved_symbols: list[str]` (по умолчанию `["BTCUSDT"]` per заблокированный один символ pre-s35-backlog).

`_check_halt_gate()` проверяет: `if symbol not in self._settings.s35_demo_approved_symbols → HALT_UNKNOWN_SYMBOL`.

Стартовый баннер в `RuntimeManager.run()` после `coordinator.bootstrap()` отображает (когда `s35_demo_active=True`):
- список approved_symbols
- пороги остановки (4 триггера + значения)
- флаг fail_closed=True

Аудит, видимый оператору при старте.

### SD-4 — HMAC-целостность activation_ts

`StateRepository` расширен методами `set_signed()` + `get_signed()` по паттерну HMAC ADR 0018. Переиспользует `risk_override_hmac_key` (отдельно от API-секрета per ADR 0018 H2).

Формат конверта: `{"payload": <value>, "sig": <HMAC-SHA256 hex>}`.

`_check_halt_gate()` читает activation_ts через `get_signed()` — вызывает ValueError при несовпадении подписи. Путь остановки: подделанное значение → остановка HALT_UNKNOWN_SYMBOL + выход бота (требуется проверка оператором).

### SD-5 — Инъекция часов в `_check_halt_gate`

Аргумент конструктора `RuntimeManager.__init__`: `clock: Callable[[], datetime] = lambda: datetime.now(UTC)`.

Заменить прямые вызовы `datetime.now(UTC)` в `_check_halt_gate()` на `self._clock()`. Обеспечивает детерминированные property-тесты + будущие сценарии воспроизведения.

Паттерн соответствует прецеденту S8a `RiskManager.__init__(clock=...)`.

### SD-6 — Публичное свойство coordinator.symbol

`Coordinator` предоставляет:
```python
@property
def symbol(self) -> str:
    return self._symbol
```

`RuntimeManager._check_halt_gate()` заменяет приватную утечку `getattr(self._coordinator, "_symbol", None)` на `self._coordinator.symbol`.

Устраняет нарушение Деметры. Стабильный контракт публичного API per ADR 0019.

## Последствия

### Положительные
- Symbol fail-closed = production-ready путь остановки (нет молчаливого обхода)
- HMAC целостность = обнаружение подделки activation_ts (нет атаки отката)
- Инъекция часов = детерминированные property-тесты (разблокировка тестируемости)
- Свойство coordinator.symbol = чистый публичный API (нет приватного доступа)
- Атрибуция аудита HALT_UNKNOWN_SYMBOL сохранена
- Активация δ после S37 = дисциплина production-готовности + уверенность оператора

### Отрицательные
- Временные затраты ~8-10ч (задерживает накопление данных δ на ~2-4 недели)
- Накладные расходы верификации HMAC per вызов `_check_halt_gate` (пренебрежимо мало — меньше миллисекунды)
- Рост счётчика ReasonCode (49 → 50) = будущие накладные расходы канонической синхронизации

### Нейтральные
- Нет изменений состояний/событий/переходов FSM (канонические 16/30/74 без изменений, только reason codes 49→50)
- SD-* ADR 0055 без изменений
- Действие оператора по активации δ без изменений (установить переменную окружения + перезапустить) per playbook T7

## Реализация

Per план S37 (`plans/2026-04-27-sprint-37-carry-overs-hardening.md`):
- T1 (этот коммит): ADR 0057 + поправка ADR 0056 парные
- T2: Безопасность #1+#2 — белый список символов + fail-closed + HALT_UNKNOWN_SYMBOL
- T3: Безопасность #3 — HMAC-целостность activation_ts
- T4: Логика торговли #4 — инъекция часов
- T5: Логика торговли #5 — свойство coordinator.symbol
- T6: Quant #8 — граничные тесты DSR + базовый показатель S22 6.17→2.96
- T7: Страница playbook оператора
- T8: Синхронизация wiki + счётчики + отправка

## Дальнейшие шаги

**Действия оператора после отправки S37:**
1. Изучить ADR 0057 + поправку ADR 0056 + delta-activation-playbook.md
2. Установить `S35_DEMO_ACTIVE=true` в production .env (per playbook шаг 1)
3. Перезапустить бота — первый тик записывает activation_ts (подписанный HMAC)
4. Контролировать halt_log + trade_history per процедура playbook

## Связанные

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-й честный выход v0.6)
- ADR 0052 (S34 поправка к критериям приёмки LOCKED)
- ADR 0053 (S35 инфраструктура δ TESTNET до активации)
- ADR 0055 (S36 активация δ — предшественник)
- ADR 0056 (поправка S36 DSR sigma_SR + парная поправка S37)
- ADR 0018 (config_hash + паттерн HMAC override — источник SD-4)
- ADR 0019 (дизайн coordinator — источник SD-6)
- ADR 0022 (жизненный цикл RuntimeManager — паттерн часов SD-5)
- pre-s37-backlog.md ROUND 5 consilium trail
- delta-activation-playbook.md (процедура оператора T7)

---

## Поправка S38 пункт #6 — семантика усечения `months_since`

`RuntimeManager._check_halt_gate()` вычисляет:

```python
months_since = (self._clock() - last_ts).days // 30
```

**Усечение** (целочисленное деление Python `//`):

| Прошло дней | months_since |
|---|---|
| 29 | 0 |
| 30 | 1 |
| 59 | 1 |
| 60 | 2 |
| 179 | 5 |
| 180 | 6 (триггер HALT_S36_NO_TRADE_TIMEOUT) |

Следствие: HALT_S36_NO_TRADE_TIMEOUT срабатывает только после ПОЛНЫХ 6 × 30 = 180 дней без сделки. НЕ после 5 месяцев 29 дней. Консервативный сдвиг (недострел до 30 дней).

Интерпретация оператором (законная остановка vs граничный артефакт):
- Истинная остановка: бот активен >180 дней, n=0 сделок — деградация стратегии ИЛИ смена рыночного режима ИЛИ ошибка конфигурации
- Граничный артефакт: ОТСУТСТВУЕТ — усечение односторонне занижает, никогда не срабатывает ложно

Per ROUND 6 trading-logic-reviewer C4 (перенос S37 T4): «усечение намеренное, консервативный недострел до 30 дней. Задокументировать явно.»

**Пункт #9 (расширенная документация семантики Sharpe в ADR)** закрыт через поправку 2 ADR 0056 (S38 T1) — см. парный ADR для семантической таблицы из 3 строк `trial_mean_fold_oos_sharpe` vs `pooled_trade_oos_sharpe` vs `live_sharpe`.
