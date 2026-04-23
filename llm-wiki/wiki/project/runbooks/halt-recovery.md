---
title: Halt Recovery Runbook
type: runbook
tags: [operations, halt, recovery, sprint-6]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources:
  - project/decisions/0020-sprint-6-execution-spot-oco-emulation
  - project/components/oco
  - project/components/reconciler
---

# Halt Recovery Runbook

Руководство для оператора по ручному восстановлению бота после перехода в состояние `HALTED`. Каждый раздел соответствует конкретному коду причины остановки.

> **Важно:** Перед любым SQL-изменением убедитесь, что бот остановлен (`Ctrl+C` или `systemctl stop bot`). Никогда не выполняйте SQL-сброс на работающем боте.

---

## 1. HALT_FLATTEN_FAILED

### Триггер

Координатор дважды пытался закрыть позицию (полный объём + retry с `qty_step`), оба раза получил ошибку от биржи. Бот встал в `HALTED` с ненулевым остатком базовой монеты.

Переход FSM: `(OCO_ARMED | EXIT_PENDING | EXIT_SL_RESIDUAL) + FLATTEN_FAILED → HALTED`

Источник: ADR 0020 sub-decision 10.

### Диагностика

1. Проверить состояние в БД:
   ```sql
   SELECT state, bracket_id, last_attempt_num,
          oco_tp_order_id, oco_sl_order_id, updated_at
   FROM execution_state
   WHERE symbol='BTCUSDT';
   ```

2. Bybit Web UI → раздел «Assets» → BTC balance + вкладка «Open Orders». Зафиксировать фактический остаток BTC.

3. Проверить структурированный лог:
   ```bash
   grep HALT_FLATTEN_FAILED var/log/bot.log | tail -20
   ```
   Обратить внимание на `retCode` и `retMsg` от биржи — это укажет на причину отказа (min-qty, stale filter, reject exchange).

### Восстановление

1. **Отменить все открытые ордера** по символу через Bybit Web UI. Не доверять боту — отменять вручную.

2. **Закрыть позицию** через Bybit Web UI: Spot → Sell BTC → Market. Убедиться, что BTC balance = 0 (с учётом комиссии).

3. **Сбросить состояние бота** через прямой SQL:
   ```sql
   UPDATE execution_state
   SET state='FLAT',
       bracket_id=NULL,
       last_attempt_num=0,
       arming_started_at=NULL,
       oco_tp_order_id=NULL,
       oco_sl_order_id=NULL,
       updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
   WHERE symbol='BTCUSDT';
   ```

4. **Перезапустить бот.** Проверить:
   - `state=FLAT` в БД
   - `walletBalance ≈ 0 BTC` на бирже
   - Нет открытых ордеров на Bybit

5. **Post-mortem обязателен** — см. раздел ниже.

### Post-mortem

Добавить запись в `wiki/log.md`:

| Поле | Значение |
|------|----------|
| Timestamp | UTC дата и время HALT |
| Qty stuck | Количество базовой монеты (BTC), застрявшее в позиции |
| Root cause hypothesis | reject биржи / min-qty hit / stale lot filter / сеть |
| Fix applied | Ссылка на PR или описание изменения кода |

---

## 2. HALT_OCO_SIBLING_STUCK

### Триггер

SL или TP-ордер сработал (Filled). Координатор вызвал `cancel_order(sibling)`, но получил `retCode`, отличный от `110001` (ордер уже не существует). FSM перешёл в `EXIT_SIBLING_CANCEL_FAILED`, затем — в `HALTED` после timeout или ручного вмешательства.

Переход FSM: `EXIT_SIBLING_CANCELLING → EXIT_SIBLING_CANCEL_FAILED → HALTED`

Источник: ADR 0020 sub-decision 6.

### Диагностика

1. Проверить идентификаторы ордеров:
   ```sql
   SELECT oco_tp_order_id, oco_sl_order_id, bracket_id
   FROM execution_state
   WHERE symbol='BTCUSDT';
   ```

2. Bybit Web UI → «Order History» + «Open Orders»: определить, какой leg заполнен (Filled), а какой завис (Active / PartiallyFilled).

3. Проверить лог:
   ```bash
   grep SIBLING_CANCEL_FAILED var/log/bot.log | tail -10
   ```
   Зафиксировать `retCode` и `orderId` застрявшего ордера.

### Восстановление

1. **Отменить застрявший sibling-ордер** через Bybit Web UI (кнопка Cancel рядом с ордером).

2. Если позиция по BTC ненулевая (частичное исполнение SL/TP): **закрыть остаток** через Web UI Market Sell.

3. **SQL-сброс** (тот же шаблон, что и для HALT_FLATTEN_FAILED):
   ```sql
   UPDATE execution_state
   SET state='FLAT',
       bracket_id=NULL,
       last_attempt_num=0,
       arming_started_at=NULL,
       oco_tp_order_id=NULL,
       oco_sl_order_id=NULL,
       updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
   WHERE symbol='BTCUSDT';
   ```

4. **Перезапустить бот.** Убедиться в отсутствии открытых ордеров и нулевом балансе BTC.

### Post-mortem

Выяснить точный `retCode` от биржи при попытке отмены. Наиболее частые причины:

- `110013` — ордер уже частично исполнен, нельзя отменить стандартным методом
- `170213` — ордер заблокирован системой риска биржи
- Сетевой таймаут при вызове cancel_order

---

## 3. HALT_PHANTOM_SL

### Триггер

Reconciler при вызове `get_open_orders` обнаружил активный SL-ордер на бирже, для которого нет соответствующего `bracket_id` в локальной `execution_state`. Это признак того, что ордер был создан предыдущим процессом, который упал, не записав результат в БД.

Переход FSM: `RECONCILING + RECONCILE_DIVERGENCE → HALTED`

Источник: ADR 0020 sub-decision 4.

### Диагностика

1. Bybit Web UI → «Open Orders»: найти ордер с подозрительным `orderLinkId`. Формат link-id у бота: `oco-{bracket_id}-sl-{attempt}`.

2. Извлечь `bracket_id` из `orderLinkId` и проверить в БД:
   ```sql
   SELECT * FROM execution_state WHERE bracket_id='{bracket_id}';
   ```
   Если строка не найдена — это phantom от крашнувшегося процесса.

3. Проверить лог:
   ```bash
   grep PHANTOM_SL var/log/bot.log | tail -10
   grep RECONCILE_DIVERGENCE var/log/bot.log | tail -10
   ```

### Восстановление

1. **Отменить phantom-ордер** через Bybit Web UI. Убедиться, что он не был частично исполнен (check Order History).

2. **Проверить баланс кошелька** — если phantom не был исполнен, BTC balance должен быть равен нулю. Если есть остаток — закрыть через Market Sell.

3. При необходимости — **SQL-сброс** (если `execution_state.state` отличается от `FLAT`):
   ```sql
   UPDATE execution_state
   SET state='FLAT',
       bracket_id=NULL,
       last_attempt_num=0,
       arming_started_at=NULL,
       oco_tp_order_id=NULL,
       oco_sl_order_id=NULL,
       updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
   WHERE symbol='BTCUSDT';
   ```

4. **Перезапустить бот.** `Coordinator.bootstrap()` заново просмотрит историю ордеров и корректно восстановит контекст.

### Post-mortem

Phantom SL — индикатор того, что процесс упал между вызовом `create_order` и записью результата в БД. Необходимо проверить:

- Есть ли retry-логика вокруг записи `oco_sl_order_id` в БД
- Не упал ли процесс из-за OOM или сигнала SIGKILL
- Логи системы (journalctl, dmesg) на момент краша

---

## 4. HALT_RECONCILE_DIVERGENCE (Sprint 5)

> Полная документация этого кода находится на странице компонента reconciler.
> См. [[../components/reconciler#divergence-handling]] для подробностей.
> Данный раздел описывает только ручное вмешательство, если reconciler эскалировал в `HALTED`.

### Краткий триггер

Reconciler обнаружил расхождение между локальным `execution_state` и фактическим состоянием биржи, которое не смог разрешить автоматически.

### Восстановление

1. Сравнить баланс BTC на Bybit Web UI с `execution_state.state` и `position_qty` в БД. Определить источник истины (биржа всегда приоритетнее).

2. Вручную закрыть любые открытые позиции и ордера через Bybit Web UI, если это необходимо.

3. **SQL-сброс** к состоянию `FLAT`:
   ```sql
   UPDATE execution_state
   SET state='FLAT',
       bracket_id=NULL,
       last_attempt_num=0,
       arming_started_at=NULL,
       oco_tp_order_id=NULL,
       oco_sl_order_id=NULL,
       updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
   WHERE symbol='BTCUSDT';
   ```

4. **Перезапустить бот.**

---

## Общие SQL-шаблоны

### Сброс execution_state в FLAT (схема Sprint 6)

> Схема Sprint 6 не содержит колонки `halt_reason` — только поля, перечисленные ниже.
> Миграция: `migrations/0003_execution_state.sql` + `migrations/0004_execution_state_v2.sql`.

```sql
-- Сброс execution_state к FLAT (Sprint 6 schema — нет колонки halt_reason):
UPDATE execution_state
SET state='FLAT',
    bracket_id=NULL,
    last_attempt_num=0,
    arming_started_at=NULL,
    oco_tp_order_id=NULL,
    oco_sl_order_id=NULL,
    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE symbol='BTCUSDT';
```

### Диагностический SELECT (полный снимок состояния)

```sql
SELECT symbol, state, position_qty, entry_price,
       bracket_id, last_attempt_num,
       oco_tp_order_id, oco_sl_order_id,
       arming_started_at, updated_at
FROM execution_state
WHERE symbol='BTCUSDT';
```

> **Колонки, которых НЕТ в схеме Sprint 6:** `halt_reason`, `halt_at`. Не включайте их в SQL.

---

## Связанные материалы

- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]
- [[../components/oco]]
- [[../components/reconciler]]
- [[../components/execution-state-machine]]
- [[../../trading/concepts/reason-codes]]
