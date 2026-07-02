---
title: "Сверка с биржей как источник истины (reconcile)"
section: "05-исполнение-ордеров"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/execution/reconciler.py, src/execution/coordinator.py, src/execution/bybit/adapter.py
---

# Сверка с биржей как источник истины (reconcile)

**TL;DR:** После любого обрыва связи бот спрашивает биржу — «сколько у меня монет на кошельке?» — и сверяет ответ со своими записями. Биржа всегда права. Если записи расходятся — бот останавливается и ждёт оператора.

## Простыми словами

Представьте, что вы отдали брокеру поручение купить 1 BTC, и вдруг пропал интернет. Вернувшись, вы хотите знать: куплен ли BTC на самом деле, или нет? Вы не доверяете своим черновикам — вы звоните брокеру и спрашиваете остаток счёта. Брокер знает правду.

В торговом боте та же ситуация. Бот хранит внутри базы данных своё представление о позиции: «у меня открыта сделка, я держу 0.01 BTC». Но в случае обрыва WebSocket-соединения (потери связи с биржей) или перезапуска программы это представление может устареть. Может, BTC уже продался по стоп-лоссу пока связь была прервана. Может, наоборот, ордер на покупку не успел исполниться.

**Сверка (reconcile)** — это процедура «сверки счёта»: бот запрашивает у биржи фактический баланс кошелька и открытые ордера, сравнивает с тем, что записано у него в базе, и выносит один из четырёх вердиктов. На основе вердикта бот либо продолжает работу, либо восстанавливается из сбоя, либо останавливается.

**Ключевой принцип** (ADR 0020, sub-decision 4): на Bybit Spot V5 нет API-метода «получить мою открытую позицию» (как это есть на фьючерсах). Вместо него биржа предоставляет **баланс кошелька** (`walletBalance`). Сколько базовой монеты (например, BTC) числится на кошельке — столько и считается открытой позицией. Биржа — единственный источник истины.

## Как это работает у нас

### Шаг 1. Откуда берётся баланс — WS-кэш и REST-запрос

Бот получает баланс двумя способами (в порядке приоритета):

**Способ A — из кэша WebSocket.** Когда биржа по [[bybit-private-websocket|приватному WebSocket]] присылает событие обновления кошелька (топик `wallet`), метод `on_wallet_event()` сохраняет новый баланс в памяти:

```python
def on_wallet_event(self, evt: dict[str, Any]) -> None:
    with self._lock:
        coin = evt["coin"]
        self._wallet_cache[coin] = Decimal(str(evt["walletBalance"]))
```

(src/execution/reconciler.py:98-102)

**Способ B — REST-запрос.** Если кэш пуст (например, сразу после запуска), метод `_fetch_exch_qty()` делает прямой [[bybit-rest-client-and-backoff|REST-запрос]] к бирже (через [[bybit-order-adapter|адаптер Bybit]]):

```python
def _fetch_exch_qty(self, symbol: str | None) -> Decimal:
    coin = self._base_coin or self._derive_base_coin(symbol)
    with self._lock:
        cached = self._wallet_cache.get(coin)
    if cached is not None:
        return Decimal("0") if cached < self._dust_threshold else cached
    # Cache miss → blocking REST fetch WITHOUT the Lock held (I/O hoisted out).
    snap = self._query.get_wallet_balance(coin=coin)
    return Decimal("0") if snap.wallet_balance < self._dust_threshold else snap.wallet_balance
```

(src/execution/reconciler.py:104-122)

### Шаг 2. Порог пыли — защита от ложных сигналов

Монеты в копейках. Из-за округления на бирже в кошельке может оказаться крошечный остаток — например, 0.000001 BTC. Если считать такой остаток «открытой позицией», бот будет думать, что держит актив, хотя фактически кошелёк пуст.

**Порог пыли (dust threshold)** — минимальный остаток, ниже которого бот считает позицию закрытой. По умолчанию:

```python
dust_threshold: Decimal = Decimal("0.00001")
```

(src/execution/reconciler.py:84)

Логика в `derive_position_qty()`:

```python
def derive_position_qty(self, state: ExchangeState) -> Decimal:
    if state.wallet.wallet_balance < self._dust_threshold:
        return Decimal("0")
    return state.wallet.wallet_balance
```

(src/execution/reconciler.py:131-135)

Проще говоря: баланс меньше 0.00001 монеты = кошелёк пустой = позиции нет.

### Шаг 3. Основная функция `reconcile()` — два режима

Главная точка входа — `reconcile()`. Она работает в двух режимах:

```python
def reconcile(self, local: LocalState, *, expected_state: object = None) -> ReconcileResult:
```

(src/execution/reconciler.py:299)

- **Режим 1 (бинарный, устаревший S6):** `expected_state=None` — сравнивает только количество монет. Результат: либо AGREE (совпало), либо DIVERGENCE (расхождение).
- **Режим 2 (четырёхзначный, ADR 0021):** `expected_state` задан — знает, в каком состоянии был бот до обрыва, и может вынести умный вердикт: AGREE, DIVERGENCE, HEAL_ENTRY_FILLED или EXITED.

Функция устроена как два этапа, разделённых по времени удержания блокировки (подробнее — в разделе про lock-hoist):

```python
# --- I/O phase: blocking REST fetches, NO Lock held ---
exch_qty = self._fetch_exch_qty(sym)
open_orders = self._query.get_open_orders(symbol=sym) if sym else []
# ...
# --- Pure classify phase: no I/O, no shared-state mutation, no Lock needed ---
return self._classify(local, expected_state, exch_qty, open_orders, entry_order)
```

(src/execution/reconciler.py:321-335)

### Шаг 4. Четыре вердикта — что они означают

Вердикт возвращается как строка в поле `ReconcileResult.verdict`:

```python
Verdict = Literal["AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED"]
```

(src/execution/reconciler.py:13)

| Вердикт | Что означает | Что бот делает дальше |
|---|---|---|
| `AGREE` | Баланс биржи совпадает с записями бота (с точностью до порога пыли) | Продолжает работу штатно |
| `DIVERGENCE` | Расхождение, которое бот не может объяснить | Останавливается (HALTED) |
| `HEAL_ENTRY_FILLED` | Бот не знал, что ордер на вход исполнился, но биржа подтверждает — исполнился | «Лечит» состояние: фиксирует покупку, продолжает работу |
| `EXITED` | Биржа показывает пустой кошелёк и нет открытых ордеров — позиция была закрыта без ведома бота | Переходит в состояние FLAT (нет позиции), продолжает |

### Шаг 5. Классификация состояния ENTRY_PENDING (вход ожидается)

Если бот ждал исполнения ордера на покупку и в этот момент оборвалась связь, после восстановления он запускает `_classify_entry_pending()`. Эта функция пытается «вылечить» состояние (HEAL) вместо того, чтобы сразу остановиться. Для этого она проходит четыре проверки:

```python
def _classify_entry_pending(
    self,
    local: LocalState,
    exch_qty: Decimal,
    open_orders: list[dict[str, Any]],
    entry_order: OrderSnapshot | None,
) -> ReconcileResult:
```

(src/execution/reconciler.py:199)

**Проверка 1 — ордер реально исполнился?**
```python
if entry_order is None or entry_order.order_status != "Filled":
    # → DIVERGENCE, halt_reason="HALT_BOOTSTRAP_AMBIGUOUS"
```
(src/execution/reconciler.py:208-216)

Если биржа говорит, что ордер не в статусе `Filled` — непонятно, что произошло. Безопаснее остановиться.

**Проверка 2 — купленного хватает?**
```python
expected_qty = local.expected_entry_qty or Decimal("0")
if exch_qty < expected_qty - self._dust_threshold:
    # → DIVERGENCE, halt_reason="HALT_BOOTSTRAP_AMBIGUOUS"
```
(src/execution/reconciler.py:219-228)

Если на кошельке меньше монет, чем ожидалось при покупке (с допуском на пыль) — что-то пошло не так.

**Проверка 3 — нет «осиротевших» ордеров брекета?**
```python
bracket_orders = [o for o in open_orders if self._belongs_to_current_bracket(o, local)]
if bracket_orders:
    # → DIVERGENCE, halt_reason="HALT_BOOTSTRAP_AMBIGUOUS"
```
(src/execution/reconciler.py:231-240)

После исполнения входного ордера не должно быть активных ордеров стоп-лосса или тейк-профита из того же брекета — иначе состояние непредсказуемо.

**Проверка 4 — запись не слишком старая?**
```python
age_seconds = (datetime.now(UTC) - local.updated_at).total_seconds()
if age_seconds > self._heal_max_age_seconds:
    # → DIVERGENCE, halt_reason="HALT_BOOTSTRAP_AMBIGUOUS", sub_reason="stale_age"
```
(src/execution/reconciler.py:243-253)

Если запись в базе данных старше `heal_max_age_seconds` (по умолчанию 3600 секунд = 1 час), доверять ей нельзя — слишком много могло измениться.

Прошли все четыре проверки → `HEAL_ENTRY_FILLED`: бот «исцеляет» состояние, записывает фактическую цену исполнения и количество с биржи, и продолжает работу как будто покупка произошла штатно.

### Шаг 6. Классификация состояния EXIT_PENDING (выход ожидается)

Если бот ждал закрытия позиции (продажи) и связь оборвалась:

```python
def _classify_exit_pending(
    self,
    _local: LocalState,
    exch_qty: Decimal,
    open_orders: list[dict[str, Any]],
) -> ReconcileResult:
    if exch_qty < self._dust_threshold and len(open_orders) == 0:
        return ReconcileResult(verdict="EXITED", ...)
    return ReconcileResult(
        verdict="DIVERGENCE",
        halt_reason="HALT_EXIT_RECONCILE_DIVERGENCE",
    )
```

(src/execution/reconciler.py:270-297)

Логика проста: кошелёк пустой (меньше порога пыли) И нет открытых ордеров → позиция была закрыта → EXITED. В любом другом случае → DIVERGENCE → остановка.

Обратите внимание: параметр `_local` (локальное состояние бота) в этой ветке намеренно не используется — классификация выхода опирается только на данные биржи.

### Шаг 7. Принадлежность ордера к текущему брекету

При проверке «осиротевших» ордеров бот должен понять, принадлежит ли открытый ордер текущей сделке или это что-то постороннее. Для этого используются детерминированные идентификаторы ордеров: каждый ордер стоп-лосса/тейк-профита из [[oco-bracket-emulation|OCO-брекета]] получает идентификатор вида `oco-{bracket_id}-{role}-{attempt}`.

```python
def _belongs_to_current_bracket(self, o: dict[str, Any], local: LocalState) -> bool:
    if local.bracket_id is None:
        return True  # Pre-bootstrap: any open order is suspect
    link_id: str = o.get("orderLinkId", "")
    return link_id.startswith(f"oco-{local.bracket_id}-")
```

(src/execution/reconciler.py:173-179)

Здесь есть важный нюанс: если поле `bracket_id` ещё не присвоено (то есть бот только что перезапустился и ещё не дошёл до размещения своего первого ордера), метод возвращает `True` для любого открытого ордера — то есть каждый открытый ордер на бирже считается подозрительным и потенциально «нашим». Это намеренно консервативная позиция: лучше ошибочно заподозрить посторонний ордер, чем пропустить неизвестный собственный. В такой ситуации бот не станет продолжать работу — он остановится и запросит оператора. (reconciler.py:175-177)

Если `bracket_id` присвоен, проверка работает по префиксу: ордер принадлежит текущей сделке тогда и только тогда, когда его идентификатор начинается с `oco-{bracket_id}-`. Ордера с другим идентификатором отклоняются как посторонние.

### Шаг 8. Координатор запускает сверку — `on_ws_reconnect()`

Сам по себе `Reconciler` — это «мозг», который сравнивает данные. Но кто его вызывает? [[coordinator-orchestration|`Coordinator`]] — оркестратор, который управляет всем жизненным циклом ордеров. При переподключении WebSocket он вызывает `on_ws_reconnect()`:

```python
def on_ws_reconnect(self) -> None:
```

(src/execution/coordinator.py:174)

Функция работает в **три временных окна** с разными уровнями блокировки:

**Окно 1 (под замком):** Проверяет, что состояние позволяет сверку. Переводит [[execution-state-machine|FSM]] в промежуточное состояние RECONCILING. Снимает снимок локального состояния.

```python
with self._lock:
    # ...проверки...
    self._transition(ExecutionEvent.WS_RECONNECT)  # → RECONCILING
    local = self._build_local_state(row)
```

(src/execution/coordinator.py:194-203)

**Окно 2 (без замка):** Выполняет REST-запросы к бирже. Это медленно — может занять до ~15.5 секунд при нагрузке на биржу. Замок НЕ удерживается — об этом подробнее в разделе «lock-hoist».

```python
# I/O window: blocking REST fetches run with the RLock RELEASED (ARCH-02).
result = self._reconciler.reconcile(local, expected_state=state)
```

(src/execution/coordinator.py:205-206)

**Окно 3 (под замком):** Применяет вердикт — переводит FSM в нужное состояние.

```python
with self._lock:
    if result.verdict == "HEAL_ENTRY_FILLED":
        self._apply_heal_entry_filled(result)
        self._transition(ExecutionEvent.RECONCILE_ENTRY_FILLED)  # → LONG_OPEN
    elif result.verdict == "EXITED":
        self._apply_exited()
        self._transition(ExecutionEvent.RECONCILE_EXITED)  # → FLAT
    elif result.verdict == "AGREE":
        self._transition(ExecutionEvent.RECONCILE_OK)
    else:  # DIVERGENCE
        self._set_halt(reason=..., ...)
        self._transition(ExecutionEvent.RECONCILE_DIVERGENCE)  # → HALTED
```

(src/execution/coordinator.py:208-226)

### Шаг 9. Запуск и восстановление — `bootstrap()`

`bootstrap()` вызывается один раз при старте бота:

```python
def bootstrap(self) -> None:
```

(src/execution/coordinator.py:257)

**Холодный старт** (нет записи в базе данных — бот запускается впервые):

```python
with self._lock:
    row = self._repo.get(self._symbol)
    if row is None:
        self._bootstrap_done = True
        return
```

(src/execution/coordinator.py:286-290)

Нет записи → нет состояния для восстановления → бот готов к новым сделкам.

**Тёплый старт** (есть [[execution-state-persistence-and-halt-audit|сохранённая запись]] — бот перезапускается после сбоя):

1. Восстанавливает `last_attempt_num` из истории ордеров на бирже (чтобы знать, какой был последний попытки размещения ордера).
2. Делегирует в `on_ws_reconnect()` — использует ту же самую логику сверки.
3. Фиксирует время старта.

```python
# Off-lock REST I/O (recover + reconcile); each takes its own narrow lock.
self._recover_attempt_num(row)
self.on_ws_reconnect()

with self._lock:
    self._upsert_fields(bootstrap_at=_now_iso())
    self._bootstrap_done = True
```

(src/execution/coordinator.py:293-298)

## Архитектурный нюанс — lock-hoist (вынос долгих операций из-под замка)

Это важная техническая деталь, которая влияет на безопасность работы бота.

### Проблема

Бот использует многопоточность: одновременно работает поток WebSocket (получает обновления ордеров в реальном времени) и поток сверки (делает REST-запросы к бирже). Оба потока должны синхронизироваться через общий замок (Lock/RLock).

Запросы к бирже могут занять до **~15.5 секунд** при исчерпании лимита запросов (5 повторных попыток с задержками 0.5 + 1.0 + 2.0 + 4.0 + 8.0 секунд). Если держать замок всё это время, поток WebSocket будет заблокирован. Последствие: бот не успеет отменить «сиблинговый» ордер (тейк-профит или стоп-лосс) в узком окне 0 миллисекунд, пока биржа исполняет другой ордер. Это может привести к «фантомному» короткому ордеру на Spot.

### Решение (ARCH-02)

В S55 весь блокирующий ввод-вывод вынесен из-под замка. Замок берётся только для быстрых операций над состоянием (не I/O):

- Перед I/O: краткий захват замка → читаем состояние → переходим в RECONCILING → отпускаем замок.
- I/O без замка: делаем REST-запросы к бирже (могут занять до 15.5с).
- После I/O: краткий захват замка → применяем вердикт → отпускаем замок.

(src/execution/reconciler.py:105-122, coordinator.py:180-226)

Аналогия: если кассир делает долгий звонок в банк, он не блокирует всю очередь — он отходит в сторону, звонит, возвращается с ответом.

## Примеры / сценарии

### Сценарий А — штатное переподключение (AGREE)

Бот держит 0.01 BTC. Связь оборвалась на 5 секунд. После восстановления:

1. `on_ws_reconnect()` переводит FSM в RECONCILING.
2. REST-запрос к бирже: баланс = 0.01 BTC.
3. Локальная запись: position_qty = 0.01 BTC.
4. `_binary_verdict()`: `|0.01 - 0.01| = 0 < 0.00001` → **AGREE**.
5. FSM переходит обратно в OCO_ARMED. Бот работает дальше.

### Сценарий Б — стоп-лосс сработал пока не было связи (EXITED)

Бот был в состоянии EXIT_PENDING. Связь оборвалась. Стоп-лосс исполнился. После восстановления:

1. `_classify_exit_pending()` вызывается с `expected_state=EXIT_PENDING`.
2. Баланс биржи: 0.000000001 BTC (округление после продажи) < 0.00001 → считается 0.
3. Открытых ордеров нет.
4. Вердикт: **EXITED**.
5. `_apply_exited()`: записывает `last_exit_reason = "EXIT_RECONCILE_DETECTED"`, qty = 0.
6. FSM переходит в FLAT. Бот готов к новым сделкам.

### Сценарий В — покупка исполнилась пока не было связи (HEAL)

Бот разместил ордер на покупку BTC и ждал подтверждения (ENTRY_PENDING). Связь оборвалась. Покупка исполнилась. После восстановления:

1. `_classify_entry_pending()` вызывается.
2. Проверка 1: `get_order()` → статус = "Filled". Отлично.
3. Проверка 2: баланс = 0.009995 BTC. Ожидали 0.01 BTC. Разница = 0.000005 < 0.00001. Проходим (комиссия биржи).
4. Проверка 3: ордеров брекета нет — они ещё не были размещены.
5. Проверка 4: запись обновлена 30 минут назад < 3600 секунд. Проходим.
6. Вердикт: **HEAL_ENTRY_FILLED**.
7. `_apply_heal_entry_filled()`: записывает фактическую цену и количество.
8. FSM переходит в LONG_OPEN. Бот вооружает стоп-лосс и тейк-профит.

### Сценарий Г — необъяснимое расхождение (DIVERGENCE)

Бот думает, что держит 0.01 BTC. После восстановления биржа показывает 0.005 BTC. Разница 0.005 >> 0.00001.

Вердикт: **DIVERGENCE**. FSM переходит в HALTED (один из [[safety-stops-and-halts|тормозов бота]]). Бот ждёт оператора; при необходимости запускается [[emergency-flatten-and-residual|аварийное закрытие позиции]].

## Подводные камни / что важно понимать

**1. Биржа — источник истины, локальная база — вторичная.** Это намеренное архитектурное решение. Если в [[storage-and-database|локальной базе данных]] есть ошибка (баг, ручная правка), биржа её исправит при следующей сверке. Но если на бирже что-то пошло не так — бот немедленно останавливается.

**2. Fail-closed при неоднозначности.** Принцип: если непонятно что делать — останавливайся. Но код остановки зависит от того, какая именно часть сверки обнаружила проблему. Всего таких кодов три, и по ним оператор может понять, на каком шаге бот встал:

| Код остановки | Откуда берётся | Когда возникает |
|---|---|---|
| `HALT_BOOTSTRAP_AMBIGUOUS` | `_classify_entry_pending()` (reconciler.py:214, 226, 238, 251) | Бот ждал исполнения ордера на вход, но после переподключения что-то не сходится: ордер не в статусе Filled, монет на кошельке меньше ожидаемого, есть «осиротевшие» ордера брекета, или запись в базе слишком старая |
| `HALT_EXIT_RECONCILE_DIVERGENCE` | `_classify_exit_pending()` (reconciler.py:295) | Бот ждал закрытия позиции (продажи), но после переподключения кошелёк не пуст или ещё есть открытые ордера — непонятно, продалось ли |
| `HALT_RECONCILE_DIVERGENCE` | `_binary_verdict()` (reconciler.py:154) | Любое другое состояние (бот был в OCO_ARMED, LONG_OPEN, PARTIAL_FILL и т.п.) и баланс биржи расходится с записями бота |

Во всех трёх случаях действие одно: FSM переходит в HALTED, бот ждёт оператора. Различие кодов помогает понять при расследовании, на каком шаге возникло расхождение.

**3. Двойное использование `expected_entry_qty`.** Поле `expected_oco_qty` в базе данных выполняет роль `expected_entry_qty` для reconciler-а. Это историческое наследование имени от старой схемы S5 — в коде прокомментировано явно (coordinator.py:388-389).

**4. Холодный старт — не сверка.** Если нет записи в базе данных, `bootstrap()` просто возвращает управление без какой-либо сверки с биржей. Сверка нужна только для восстановления существующего состояния.

**5. lock-hoist нарушает наивную логику «держи замок всё время».** Человеку кажется, что для безопасности нужно держать замок от начала до конца операции. Но здесь это приводило бы к зависанию WebSocket-потока на 15+ секунд. Компромисс: менее строгое удержание замка, но с гарантией что каждое изменение состояния FSM всё равно происходит под замком.

**6. RECONCILING — переходное состояние.** Пока бот находится в состоянии RECONCILING (идёт сверка), он намеренно игнорирует новые события WebSocket — они будут обработаны после завершения сверки. Это предотвращает гонку состояний, когда событие приходит в «серую зону» между записями.

**7. Порог пыли — не ноль.** Порог `0.00001` выбран с запасом от однобитных округлений. Он не настраивается через конфиг пользователя — это константа по умолчанию в конструкторе `Reconciler` (reconciler.py:84).

## Связанные документы

- [[coordinator-orchestration]] — общий цикл работы Coordinator, FSM-переходы, управление ордерами
- [[execution-state-machine]] — диаграмма состояний FSM, все переходы включая RECONCILING и HALTED
- [[execution-state-persistence-and-halt-audit]] — как состояние сохраняется в базе данных, что записывается при HALT
- [[oco-bracket-emulation]] — брекет из трёх ордеров (TP/SL/Entry), откуда берётся bracket_id и orderLinkId
- [[emergency-flatten-and-residual]] — что происходит после DIVERGENCE: экстренное закрытие позиции
- [[bybit-rest-client-and-backoff]] — логика повторных попыток REST-запросов и расчёт 15.5-секундного максимума задержки
- [[bybit-private-websocket]] — источник событий `wallet` для WS-кэша баланса; переподключение WS запускает `on_ws_reconnect()`
- [[bybit-order-adapter]] — слой, через который reconciler запрашивает биржу: баланс кошелька, открытые ордера, статус ордера
- [[order-lifecycle-overview]] — общий обзор зоны исполнения, куда встроена сверка как этап восстановления
- [[reconcile-and-monitor-commands]] — CLI-команда `reconcile-only`: та же логика сверки, запускаемая оператором вручную без торговли
- [[run-modes-testnet-live-reconcile]] — режим reconcile при старте и восстановлении контура биржи
- [[safety-stops-and-halts]] — HALTED как один из тормозов бота; общий принцип fail-closed при неоднозначности
- [[storage-and-database]] — где хранится локальная запись состояния (вторичный источник), которую сверка сравнивает с биржей
- [[startup-and-wiring]] — как при запуске собирается Coordinator и вызывается `bootstrap()` (тёплый/холодный старт)
- [[main-loop-tick]] — рабочий цикл, который останавливается при HALTED и возобновляется после успешной сверки
- [[account-balance]] — тот же `walletBalance` Bybit как источник данных, но в контексте дашборда

За техническими деталями: `llm-wiki/wiki/project/components/execution-layer.md`
