---
title: Halt Recovery Runbook
type: runbook
tags: [operations, halt, recovery, sprint-6, sprint-7]
created: 2026-04-23
updated: 2026-04-24
status: stable
sources:
  - project/decisions/0020-sprint-6-execution-spot-oco-emulation
  - project/decisions/0021-sprint-7-resilience
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

## 4. HALT_BOOTSTRAP_AMBIGUOUS (Sprint 7)

### Триггер

`Coordinator.bootstrap()` на старте процесса вызвал `reconciler.reconcile()`, и вердикт был `DIVERGENCE` — local SQLite и exchange расходятся, и это не классический heal/exit-случай. Бот **не выходит** из bootstrap пока оператор не разрешил расхождение.

Переход FSM: `INIT → RECONCILING + RECONCILE_DIVERGENCE → HALTED`
`halt_reason = "HALT_BOOTSTRAP_AMBIGUOUS"` (записан в `execution_state.halt_reason` + `halt_log`)

Источник: ADR 0021 sub-decision 1.

### Диагностика

1. Прочитать halt-trail:
   ```sql
   SELECT ts, reason, context_json FROM halt_log
   WHERE symbol='BTCUSDT' ORDER BY ts DESC LIMIT 5;
   ```
   `context_json` содержит local-state snapshot + reconcile verdict.

2. Прочитать current state:
   ```sql
   SELECT state, halt_reason, position_qty, entry_price,
          oco_main_order_id, oco_tp_order_id, oco_sl_order_id,
          bootstrap_at, last_reconcile_at
   FROM execution_state WHERE symbol='BTCUSDT';
   ```

3. Bybit Web UI → Open Orders + walletBalance(BTC). Сравнить с local snapshot.

### Восстановление

1. **Решить, кто прав** — обычно exchange (per ADR 0019 reconcile-as-truth). Если local имеет несоответствующий `oco_main_order_id`, который exchange не знает — local stale.

2. **Привести exchange в чистое состояние:** отменить все открытые ордера через Web UI, при необходимости закрыть позицию Market Sell.

3. **Сбросить execution_state** (см. шаблон ниже, **включая `halt_reason=NULL`**).

4. **Перезапустить бот.** `bootstrap()` теперь увидит чистый exchange + чистый local → AGREE → FLAT.

### Post-mortem

Зафиксировать в `wiki/log.md`: какой именно diff вызвал ambiguous-вердикт. Если повторяется — обновить classifier в `src/execution/reconciler.py::_classify_*` и добавить regression тест.

---

## 5. HALT_EXIT_RECONCILE_DIVERGENCE (Sprint 7)

### Триггер

Бот был в `EXIT_PENDING`, WS отвалился, после reconnect reconciler увидел state mismatch (например, exit-ордер уже не в open_orders, но walletBalance не сошёлся с ожидаемым FLAT). Отдельный halt-код от bootstrap-divergence — runbook путь иной.

Переход FSM: `EXIT_PENDING + WS_RECONNECT → RECONCILING + RECONCILE_DIVERGENCE → HALTED`
`halt_reason = "HALT_EXIT_RECONCILE_DIVERGENCE"`

Источник: ADR 0021 sub-decision 3.

### Диагностика

1. Прочитать halt_log + execution_state (как выше).
2. Bybit Web UI → Order History для exit-ордера: filled / cancelled / partially?
3. walletBalance(BTC): остаток или ноль?

### Восстановление

1. Если exit-ордер был filled, и BTC=0 → state в SQLite stale. SQL-сброс к FLAT (см. шаблон) **включая `halt_reason=NULL`** + `last_exit_reason='EXIT_RECONCILE_DETECTED'` для аудита.
2. Если exit-ордер partial → закрыть остаток вручную через Market Sell, затем SQL-сброс.
3. Перезапустить бот.

### Post-mortem

EXIT divergence обычно индикатор того, что `EXIT_PENDING` order заполнился во время WS-разрыва, но автоматический heal-путь не сработал. Проверить:

- Возраст filled события > `heal_max_age_seconds=3600` (1H)? Тогда DIVERGENCE — корректное поведение.
- Иначе — баг в classifier'е, требуется тест + фикс.

---

## 6. HALT_RECONCILE_DIVERGENCE (Sprint 5)

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

### Сброс execution_state в FLAT (схема Sprint 7)

> Sprint 7 миграция `0005_halt_persistence.sql` добавила колонки `halt_reason`, `last_exit_reason`, `last_reconcile_at`, `bootstrap_at` + audit-таблицу `halt_log`.
> Миграции: `migrations/0003_execution_state.sql` + `0004_execution_state_v2.sql` + `0005_halt_persistence.sql`.

```sql
-- Сброс execution_state к FLAT (Sprint 7 schema):
UPDATE execution_state
SET state='FLAT',
    bracket_id=NULL,
    last_attempt_num=0,
    arming_started_at=NULL,
    oco_main_order_id=NULL,
    oco_tp_order_id=NULL,
    oco_sl_order_id=NULL,
    halt_reason=NULL,                    -- S7: primary-wins; reset на manual recovery
    last_exit_reason=NULL,               -- опционально: оставить для audit-trail
    last_reconcile_at=NULL,
    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE symbol='BTCUSDT';
```

> **Не удалять `halt_log` записи.** Append-only audit. Чтение для post-mortem — обязательно.

### Диагностический SELECT (полный снимок состояния)

```sql
SELECT symbol, state, halt_reason, last_exit_reason,
       position_qty, entry_price,
       bracket_id, last_attempt_num,
       oco_main_order_id, oco_tp_order_id, oco_sl_order_id,
       arming_started_at, last_reconcile_at, bootstrap_at, updated_at
FROM execution_state
WHERE symbol='BTCUSDT';
```

### Halt audit trail

```sql
SELECT ts, reason, context_json FROM halt_log
WHERE symbol='BTCUSDT' ORDER BY ts DESC LIMIT 20;
```

---

## HALT_RUNTIME_CRASH (43)

**Source:** unhandled exception в `RuntimeManager.run()` → top-level `except Exception` в `src/runtime/manager.py` (ADR 0022 sub-decision 6).

**Investigation steps:**
1. Найти crash log:
   ```bash
   grep "runtime.crash" $LOG_DIR/*.log | tail -20
   ```
2. Извлечь exception:
   ```sql
   SELECT ts, reason, context_json
   FROM halt_log
   WHERE symbol = ? AND reason = 'HALT_RUNTIME_CRASH'
   ORDER BY ts DESC LIMIT 5;
   ```
3. Reproduce in dev — fix bug → новый ADR amendment if invariant changed.
4. Operator MANUAL_RESET требуется (как любой halt).

## HALT_BAR_POLL_STALL (44)

**Source:** `BarSource.consecutive_failures >= settings.runtime_bar_poll_stall_threshold` (default 24 × 5s = 120s) — ADR 0022 sub-decision 3.

**Halt class:** signal-pipeline (НЕ position-safety). OCO bracket exchange-side; existing positions защищены.

**Investigation steps:**
1. Bybit REST status:
   ```bash
   curl -s https://api.bybit.com/v5/market/time | jq
   ```
2. Recent failure cluster:
   ```bash
   grep "bar_source.poll_failed" $LOG_DIR/*.log | tail -50
   ```
3. Если cluster < 5 минут — likely transient, можно MANUAL_RESET без эскалации. Если > 30 минут — investigate network / API key / Bybit incident page.
4. После reset BarSource counter автоматически сбрасывается на первом успешном poll.

## KILL_SWITCH_REQUESTED (45)

**Source:** sentinel-file `.kill_switch` detected (`python -m src kill`) — ADR 0022 sub-decision 5.

**Operator-initiated** — нормальный shutdown path. Не error.

**Recovery:**
1. Verify intent — почему оператор kill'нул?
2. Cleanup sentinel:
   ```bash
   rm -f $RUNTIME_KILL_SWITCH_PATH   # default ".kill_switch"
   ```
3. Перед restart — MANUAL_RESET halt_reason (как и любой halt):
   ```sql
   UPDATE execution_state
   SET halt_reason = NULL
   WHERE symbol = ?;
   ```
4. Restart: `python -m src run` (sentinel автоматически cleanup-нится на startup в `RuntimeManager.run()`).

## Связанные материалы

- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]
- [[../decisions/0021-sprint-7-resilience]]
- [[../components/oco]]
- [[../components/reconciler]]
- [[../components/execution-state-machine]]
- [[../components/ws-private-consumer]]
- [[../../trading/concepts/reason-codes]]
