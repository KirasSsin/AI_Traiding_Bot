---
title: "Жизненный цикл ордера: общий обзор"
section: "05-исполнение-ордеров"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/execution/coordinator.py, src/runtime/manager.py, src/execution/state_machine.py, src/execution/bracket.py, src/execution/reconciler.py, src/execution/bybit/ws_private.py, src/execution/bybit/adapter.py
---

# Жизненный цикл ордера: общий обзор

**TL;DR:** Каждая сделка бота проходит строгую последовательность шагов — от сигнала стратегии до полного закрытия позиции. Весь путь отслеживается конечным автоматом (машиной состояний), который не даёт боту открыть вторую сделку, пока первая не завершена.

---

## Простыми словами

Представьте, что вы хотите купить акцию. Вы не просто звоните брокеру и говорите «купи» — вы сначала решаете цену, размер, условия выхода. А потом ждёте подтверждения, что покупка прошла, и только тогда выставляете лимитный ордер на продажу с прибылью и стоп-ордер на случай убытка.

**Наш бот делает то же самое**, только автоматически и на бирже Bybit.

Ключевые слова:

- **Ордер (order)** — заявка на бирже: «купить X единиц по такой-то цене» или «продать по такой-то».
- **Позиция (position)** — то, что уже куплено и лежит у вас на счёте. Пока позиция открыта — есть риск.
- **Вход / entry** — момент покупки (открытие позиции).
- **Выход / exit** — момент продажи (закрытие позиции), бывает двух типов: с прибылью (TP — take profit) или с убытком (SL — stop-loss).
- **Сигнал (signal)** — команда от стратегии: «входи» или «выходи». Стратегия смотрит на графики и решает.
- **Спотовая торговля (Spot)** — торговля реальным активом: купил BTC — BTC лежит у тебя. Нет плеча, нет коротких позиций (в v0.1 бот умеет только покупать, то есть делать LONG).
- **LONG / лонг** — ставка на рост: покупаем сейчас, продаём дороже позже.
- **Тик (tick)** — один «шаг» главного цикла бота: проверить данные → проверить сигнал → при необходимости действовать.
- **Оркестратор (Coordinator)** — центральный модуль, который управляет всеми шагами сделки.
- **Happy-path** — нормальный, «счастливый» сценарий без ошибок и неожиданностей.

---

## Как это работает у нас

### Общая архитектура: кто кого вызывает

```text
RuntimeManager (живой цикл, тики каждые N секунд)
    │
    ├─ стратегия.on_bar()        → сигнал LONG или FLAT
    ├─ RiskManager.assess()      → одобрить или отклонить + рассчитать qty/TP/SL
    ├─ Coordinator.start_bracket() → открыть сделку (entry + TP + SL)
    │       │
    │       └─ BybitMarketAdapter → REST-запросы к бирже Bybit
    │
    ├─ BybitPrivateWSConsumer    → получает события от биржи по WebSocket
    │       │
    │       └─ Coordinator.on_order_event() → реагирует на заполнение/срабатывание
    │
    └─ Coordinator.reconcile_arming_ttl()  → страховка зависания каждый тик
```

**RuntimeManager** — это единственный, кто инициирует вход. Он живёт вне зоны исполнения, управляет всем жизненным циклом процесса бота (запуск, остановка, аварийное завершение); его пошаговый тик разобран в [[main-loop-tick|главном цикле]]. [[coordinator-orchestration|`Coordinator`]] получает задание от RuntimeManager и дальше ведёт сделку самостоятельно.

(src/runtime/manager.py:67–105, src/execution/coordinator.py:121–140)

---

### Инвариант «одна открытая позиция за раз»

Это фундаментальное правило бота: **он никогда не откроет новую сделку, пока предыдущая не закрыта**.

Реализация: перед вызовом `coordinator.start_bracket()` RuntimeManager проверяет текущее состояние [[execution-state-machine|FSM]] через `coordinator.current_state()`. Если состояние не равно `FLAT` (то есть позиции нет) — сигнал молча игнорируется.

```python
# src/runtime/manager.py:373-379
if state is None or state != ExecutionState.FLAT:
    logger.debug("runtime.signal_skipped_non_flat_state", ...)
    return
```

Это не просто программная проверка — `current_state()` работает под блокировкой (`self._lock`), что защищает от состояния гонки между основным потоком бота и потоком WebSocket-событий. (src/execution/coordinator.py:150–172)

---

### Машина состояний (FSM): «паспорт» сделки

Каждая сделка проходит через цепочку чётко определённых состояний. Переход между ними происходит только при конкретных событиях. Если событие не предусмотрено для текущего состояния — система выбрасывает ошибку `IllegalTransitionError`, а не продолжает вслепую.

В коде — 16 значений перечисления `ExecutionState` (src/execution/state_machine.py:12–28). Ниже показаны состояния основного пути сделки; полный список — в `state_machine.py:12–28` (включает также `INIT`, `PARTIAL_FILL`, `EXIT_PENDING`, `EXIT_SIBLING_CANCEL_FAILED`, `COOLDOWN`, `ERROR`, `KILLED`).

| Состояние | Что означает |
|---|---|
| `FLAT` | Позиции нет — бот готов к новой сделке; в это же состояние бот возвращается после закрытия позиции |
| `ENTRY_PENDING` | Ордер на покупку отправлен, ждём подтверждения |
| `LONG_OPEN` | Покупка исполнена, позиция открыта — TP/SL ещё не выставлены |
| `OCO_ARMING` | Выставляем TP-лимит, потом SL-стоп (промежуточный шаг) |
| `OCO_ARMED` | Оба ордера (TP + SL) на бирже — позиция защищена |
| `EXIT_SIBLING_CANCELLING` | Один из TP/SL сработал, отменяем второй |
| `EXIT_SL_RESIDUAL` | SL исполнился частично — продаём остаток |
| `RECONCILING` | Переподключение к бирже, сверяем состояние |
| `HALTED` | Аварийная остановка — требуется вмешательство оператора |

(src/execution/state_machine.py:12–28)

---

### Happy-path: от сигнала до закрытия

#### Шаг 1. Стратегия даёт сигнал LONG

Каждый тик RuntimeManager вызывает `_poll_bar_and_strategy()`: получает новую [[bar-model|свечу (bar)]] из источника данных, передаёт её стратегии, получает [[signal-architecture|сигнал]].

```python
# src/runtime/manager.py:346
signal = self._strategy.on_bar(bar)
```

Если сигнал `FLAT` (выходи) — это другой путь (см. ниже). Если `LONG` — идём дальше.

#### Шаг 2. RiskManager оценивает сигнал

Перед любой покупкой сигнал проходит [[risk-overview-decision-pipeline|оценку риска]]:
```python
# src/runtime/manager.py:380
assessment = self._risk_manager.assess(signal, mark_price=bar.close)
```
Если риск-менеджер не одобряет (`assessment.approved == False`) — сделка не открывается. Одобренный ответ содержит: `qty` (количество монет), `tp_price` (цена тейк-профита), `sl_price` (цена стоп-лосса). (src/runtime/manager.py:380–408)

#### Шаг 3. start_bracket — отправляем ордер на покупку

```python
# src/runtime/manager.py:403-408
self._coordinator.start_bracket(
    entry_qty=assessment.qty,
    entry_side="Buy",
    tp_price=assessment.tp_price,
    sl_trigger_price=assessment.sl_price,
)
```

Внутри `start_bracket()` происходит:

1. Генерируется уникальный `bracket_id` — 8-символьный префикс UUID4: `bracket_id = str(uuid.uuid4())[:8]` (src/execution/coordinator.py:351). Это «имя» всей группы ордеров этой сделки.
2. Строится структура из трёх ордеров через `build_bracket()` (src/execution/bracket.py:80–113).
3. Отправляется только первый ордер — рыночная покупка (Market BUY) через `adapter.place_order()`.
4. Состояние FSM переходит: `FLAT → ENTRY_PENDING`.
5. В базу данных сохраняются bracket_id, ожидаемое количество, запланированные цены TP и SL.

(src/execution/coordinator.py:336–398)

#### Шаг 4. Биржа исполняет покупку — WS-событие Filled

[[bybit-private-websocket|`BybitPrivateWSConsumer`]] подписан на приватный WebSocket Bybit и слушает ордерные события. Когда биржа исполняет ордер, она отправляет событие `{orderStatus: "Filled"}`.

Каждое сообщение обрабатывается в `_on_order_raw()`, парсится и передаётся в `coordinator.on_order_event()`. (src/execution/bybit/ws_private.py:204–240)

Внутри `on_order_event()` роль ордера определяется по полю `orderLinkId`:
- Формат ордера входа: `oco-{bracket_id}-entry-1`
- Роль `entry` + статус `Filled` → переход FSM: `ENTRY_PENDING → LONG_OPEN`, затем немедленно вызывается `_arm_oco_after_entry_fill()`.

(src/execution/coordinator.py:400–461)

#### Шаг 5. Арминг OCO: выставляем TP + SL

«OCO» расшифровывается как «One Cancels Other» (один отменяет другой). Это концепция: два ордера стоят одновременно, но когда один срабатывает — второй надо отменить. На Bybit Spot V5 нативного OCO нет, поэтому мы [[oco-bracket-emulation|эмулируем его тремя отдельными ордерами]].

Функция `arm_oco()` размещает два ордера на продажу через [[bybit-order-adapter|адаптер Bybit]]:
1. **TP-лимит** — лимитный ордер Sell по цене тейк-профита (`place_limit_order`, orderType=Limit, timeInForce=GTC). (src/execution/bybit/adapter.py:275–304)
2. **SL-стоп** — рыночный стоп-ордер Sell по цене стоп-лосса (`place_stop_market_order`, orderType=Market, orderFilter=StopOrder, triggerBy=LastPrice). (src/execution/bybit/adapter.py:239–273)

FSM при этом идёт по шагам: `LONG_OPEN → OCO_ARMING` (после выставления TP), затем `OCO_ARMING → OCO_ARMED` (после выставления SL). (src/execution/state_machine.py:104–105)

**Важный нюанс с комиссией.** При покупке BTC/USDT биржа берёт комиссию из купленного BTC, а не из USDT. Поэтому количество монет, которые можно продать, немного меньше, чем было куплено. Функция `compute_oco_qty()` вычитает комиссию из исполненного количества и округляет вниз до минимального шага:

```python
# src/execution/bracket.py:130
net = cum_exec_qty - cum_exec_fee if fee_currency == base_coin else cum_exec_qty
return (net / qty_step).quantize(Decimal("1"), rounding=ROUND_DOWN) * qty_step
```

(src/execution/bracket.py:116–133)

#### Шаг 6. Один из ордеров срабатывает

Теперь позиция защищена. Возможны два исхода:

**Вариант А: TP исполнился (цена выросла до цели)**

WS-событие: `{orderStatus: "Filled", orderLinkId: "oco-...-tp-..."}`.

`on_order_event()` определяет роль `tp`, переход: `OCO_ARMED → EXIT_SIBLING_CANCELLING`.

Затем вызывается `_cancel_sibling(role_to_cancel="sl")` — отменяем SL-ордер через `adapter.cancel_order()`. Если биржа отвечает кодом `110001` (ордер уже завершён) — это нормальная гонка, считается успехом.

После успешной отмены: `EXIT_SIBLING_CANCELLING → FLAT`. Позиция закрыта с прибылью. (src/execution/coordinator.py:446–448, 913–931)

**Вариант Б: SL сработал (цена упала до стопа)**

WS-событие: `{orderStatus: "Triggered", orderLinkId: "oco-...-sl-..."}`.

Обратите внимание: на Bybit Spot стоп-ордер сначала переходит в статус `Triggered`, и только потом исполняется как `Filled`. Промежуток между ними — нулевой (0 мс). Поэтому отменять TP надо именно на `Triggered`, иначе TP может успеть самостоятельно исполниться и создать ложную «короткую позицию» (phantom short).

Переход: `OCO_ARMED → EXIT_SIBLING_CANCELLING`, отмена TP, затем `EXIT_SIBLING_CANCELLING → FLAT`. (src/execution/coordinator.py:443–445, 913–931)

---

### Принудительный выход по сигналу FLAT

Второй путь выхода: стратегия сама решает продать до срабатывания TP/SL.

Если сигнал `FLAT` и позиция в одном из «живых» состояний (`LONG_OPEN`, `OCO_ARMING`, `OCO_ARMED`):

```python
# src/runtime/manager.py:363-370
if signal.side == SignalSide.FLAT:
    if state is not None and state in _FLATTENABLE_STATES:
        self._coordinator.flatten(reason=self._exit_reason(signal.reason))
    return
```

Метод [[emergency-flatten-and-residual|`flatten()`]] — аварийный «выход из всего»:
1. Отменяет все открытые ордера (`cancel_all_orders`).
2. Читает актуальный баланс кошелька (`get_wallet_balance`) — узнаём, сколько монет осталось.
3. Округляет количество вниз до [[bybit-filters|минимального шага]] (`step_floor`).
4. Отправляет рыночный ордер Sell.
5. При неудаче — одна повторная попытка с `qty - qty_step`.
6. При второй неудаче — переход в `HALTED`.

(src/execution/coordinator.py:687–739)

---

### Фоновые страховки каждый тик

Помимо основной логики, каждый тик выполняются две дополнительные проверки:

#### Страховка 1: reconcile_arming_ttl — защита от «зависшего» арминга

Если после выставления TP что-то пошло не так и SL так и не был выставлен, система застрянет в состоянии `OCO_ARMING`. Без страховки позиция оказалась бы без стопа на неопределённое время.

Каждый тик вызывается:
```python
# src/runtime/manager.py:177
self._coordinator.reconcile_arming_ttl(ttl_seconds=self._settings.oco_arming_ttl_seconds)
```

Если `OCO_ARMING` длится дольше 60 секунд (значение по умолчанию: `oco_arming_ttl_seconds = 60`, src/platform/config.py:177) — FSM переходит: `OCO_ARMING → HALTED` с кодом `HALT_OCO_ARM_TIMEOUT` (состояние `HALTED` и все прочие [[safety-stops-and-halts|тормоза бота]] требуют вмешательства оператора). (src/execution/coordinator.py:877–901)

#### Страховка 2: reconcile — восстановление после разрыва связи

Если WebSocket-соединение с биржей обрывается (или бот перезапускается), нельзя просто продолжить работу — реальное состояние позиции могло измениться.

`BybitPrivateWSConsumer` устанавливает хук на закрытие соединения и вызывает `coordinator.on_ws_reconnect()`. Также `check_alive()` периодически проверяет «живость» соединения по времени последнего пинга. (src/execution/bybit/ws_private.py:126–171, 178–202)

`on_ws_reconnect()` запускает [[reconcile-as-truth|`Reconciler`]], который через REST API запрашивает:
- баланс кошелька (это «источник истины» о наличии позиции на Bybit Spot — нет аналога `get_position`)
- список открытых ордеров

По результатам reconciler выносит один из четырёх вердиктов:

| Вердикт | Смысл | Действие |
|---|---|---|
| `AGREE` | Всё совпадает | → `OCO_ARMED` (продолжаем) |
| `HEAL_ENTRY_FILLED` | Вход исполнился пока мы были офлайн | → `LONG_OPEN` (TP/SL будут выставлены на следующем тике стратегии) |
| `EXITED` | Позиция закрылась пока мы были офлайн | → `FLAT` |
| `DIVERGENCE` | Расхождение необъяснимо | → `HALTED` (нужен оператор) |

(src/execution/reconciler.py:299–335, src/execution/coordinator.py:174–226)

Важная деталь: балансы ниже порога `dust_threshold = 0.00001` (src/execution/reconciler.py:84) считаются нулём — это защита от «пыли» (крошечных остатков, которые нельзя продать).

---

### Модули: кто за что отвечает

| Модуль | Файл | Роль |
|---|---|---|
| `RuntimeManager` | `src/runtime/manager.py` | [[main-loop-tick\|Главный цикл]] жизни бота (тики, запуск, остановка) |
| [[coordinator-orchestration\|`Coordinator`]] | `src/execution/coordinator.py` | Оркестратор сделки — ведёт её от входа до выхода |
| [[execution-state-machine\|FSM]] | `src/execution/state_machine.py` | Таблица переходов — «права» на действия в каждом состоянии |
| [[oco-bracket-emulation\|`build_bracket`]] | `src/execution/bracket.py` | Конструктор трёх ордеров + именование по шаблону `oco-{id}-{role}-{attempt}` |
| [[reconcile-as-truth\|`Reconciler`]] | `src/execution/reconciler.py` | Сверка с биржей после разрыва связи |
| [[bybit-private-websocket\|`BybitPrivateWSConsumer`]] | `src/execution/bybit/ws_private.py` | Слушатель WebSocket-событий от Bybit |
| [[bybit-order-adapter\|`BybitMarketAdapter`]] | `src/execution/bybit/adapter.py` | REST-клиент для отправки ордеров на Bybit |

---

## Формулы и расчёты

### Количество монет для TP/SL (fee-aware OCO qty)

При покупке 1.0 BTC биржа может взять комиссию в BTC — например, 0.001 BTC. Тогда на счёт пришло только 0.999 BTC. Если выставить TP на продажу ровно 1.0 BTC — биржа откажет (нет столько монет). Поэтому:

```
oco_qty = floor((cum_exec_qty - fee_if_in_base_coin) / qty_step) × qty_step
```

Простыми словами: берём исполненное количество, вычитаем комиссию (если она была в основной монете), делим на минимальный шаг лота и округляем вниз до целого числа шагов.

(src/execution/bracket.py:116–133)

### Порог «пыли» (dust_threshold)

Wallet balance < 0.00001 → считается нулём (позиции нет).

(src/execution/reconciler.py:84)

---

## Примеры / сценарии

### Сценарий А: нормальная сделка с TP

1. Стратегия даёт сигнал LONG. Бот в состоянии `FLAT`.
2. RiskManager одобряет: qty = 0.01 BTC, TP = 70 000 USDT, SL = 65 000 USDT.
3. RuntimeManager вызывает `coordinator.start_bracket()`. Отправляется Market BUY 0.01 BTC. FSM: `FLAT → ENTRY_PENDING`.
4. Биржа исполняет покупку по рыночной цене. Комиссия 0.00001 BTC (0.1% тейкера) удерживается из купленного. WS приходит событие `Filled`.
5. FSM: `ENTRY_PENDING → LONG_OPEN`. Сразу вызывается `_arm_oco_after_entry_fill()`.
6. `compute_oco_qty`: net = 0.01 − 0.00001 = 0.00999 BTC; floor(0.00999 / 0.000001) × 0.000001 = 9990 шагов × 0.000001 = oco_qty = 0.009990 BTC.
7. Выставляется TP Limit Sell 0.009990 BTC @ 70 000. FSM: `LONG_OPEN → OCO_ARMING`.
8. Выставляется SL Stop Market Sell 0.009990 BTC @ trigger 65 000. FSM: `OCO_ARMING → OCO_ARMED`.
9. Цена вырастает до 70 000. WS: `TP Filled`.
10. FSM: `OCO_ARMED → EXIT_SIBLING_CANCELLING`. Отменяется SL-ордер.
11. FSM: `EXIT_SIBLING_CANCELLING → FLAT`. Сделка завершена с прибылью.

### Сценарий Б: нормальная сделка с SL

Шаги 1–8 — как выше. Затем:

9. Цена падает до 65 000. WS: `SL Triggered` (статус «сработал»).
10. FSM: `OCO_ARMED → EXIT_SIBLING_CANCELLING`. Немедленно отменяется TP-ордер. (Важно: отмена до исполнения SL, пока биржа ещё не перевела его в `Filled`.)
11. FSM: `EXIT_SIBLING_CANCELLING → FLAT`. Сделка завершена с убытком (стоп-лосс сработал).

### Сценарий В: зависший арминг

После шага 7 (TP выставлен) сеть оборвалась — SL не дошёл до биржи. Состояние `OCO_ARMING` зависает.

Каждый тик RuntimeManager вызывает `reconcile_arming_ttl()`. Через 60 секунд:
- FSM: `OCO_ARMING → HALTED` (HALT_OCO_ARM_TIMEOUT).
- Оператор видит алерт и разбирается вручную.

### Сценарий Г: разрыв WS-соединения при открытой позиции

Позиция открыта, OCO_ARMED. Интернет оборвался.

1. `on_disconnect()` → `coordinator.on_ws_reconnect()`.
2. FSM: `OCO_ARMED → RECONCILING`.
3. REST-запросы к бирже: wallet balance = 0.009990 BTC (есть позиция!), открытые ордера = два (TP + SL).
4. Reconciler: qty совпадает, ордера на месте → вердикт `AGREE`.
5. FSM: `RECONCILING → OCO_ARMED`. Продолжаем работу как ни в чём не бывало.

---

## Подводные камни / что важно понимать

### 1. Bybit Spot не имеет нативного OCO

На Bybit Spot V5 нет встроенного механизма «один отменяет другой». Мы эмулируем его тремя отдельными ордерами: Market BUY на вход + Limit Sell на TP + Stop Market Sell на SL. Это значит, что теоретически оба ордера (TP и SL) могут сработать почти одновременно, если рынок ведёт себя аномально. Именно поэтому отмена «партнёра» происходит максимально быстро — в том же обработчике WS-события.

### 2. Нулевой промежуток Triggered → Filled на Bybit Spot

Когда стоп-ордер переходит в `Triggered`, биржа тут же начинает его исполнять как рыночный. Промежуток — буквально 0 мс. Поэтому обработчик `on_order_event()` реагирует на `Triggered` (а не на `Filled`) для SL-ордеров, чтобы успеть отменить TP. Это тонкость, специфичная именно для Bybit Spot.

(src/execution/coordinator.py:406–408, 443–445)

### 3. Один поток для тиков, другой для WS

Основной цикл бота работает в одном потоке (тики), а события с биржи приходят в другом (поток pybit WebSocket). Все критические операции в `Coordinator` защищены блокировкой `RLock` (`self._lock`), чтобы эти два потока не конфликтовали. `RLock` — «повторно входимый» замок: один и тот же поток может захватить его несколько раз без взаимоблокировки (deadlock). (src/execution/coordinator.py:139)

### 4. Идентификаторы ордеров — не случайные

Каждый ордер получает детерминированный `orderLinkId` вида `oco-{bracket_id}-{role}-{attempt}` (для TP/SL/entry) или `flat-{bracket_id}-{kind}-{attempt}` (для аварийных продаж). Если биржа получила ордер, но подтверждение потерялось в сети — повторная отправка с тем же `orderLinkId` будет корректно отклонена биржей как дубликат, без двойного исполнения. (src/execution/bracket.py:52–77)

### 5. Комиссия берётся из купленной монеты

На Bybit Spot комиссия за покупку BTC вычитается из полученного BTC, а не из USDT. Если ввести в TP/SL-ордер «сырое» количество куплено (без учёта комиссии) — биржа откажет, так как монет недостаточно. Функция `compute_oco_qty()` всегда вычитает комиссию перед выставлением TP/SL. (src/execution/bracket.py:116–133)

### 6. Блокировка не держится во время длинных REST-запросов

Reconciliation делает REST-запросы к бирже, которые при [[bybit-rest-client-and-backoff|ограничении скорости]] могут занимать до ~15 секунд. Если держать блокировку `RLock` всё это время — WS-поток не сможет обработать срабатывание SL в нулевом промежутке, что создаст «фантомную короткую позицию». Поэтому blocking REST-вызовы намеренно выполняются без блокировки (ARCH-02 fix), а блокировка захватывается только на короткие интервалы для мутаций состояния. (src/execution/coordinator.py:184–226)

---

## Связанные документы

Зона исполнения (раздел 05) — модули, которые ведут сделку:

- [[coordinator-orchestration]] — детальный разбор Coordinator: все методы, переходы состояний, обработка ошибок
- [[execution-state-machine]] — полная таблица переходов FSM с объяснением каждого состояния
- [[oco-bracket-emulation]] — как и почему мы эмулируем OCO тремя ордерами на Bybit Spot (build_bracket, orderLinkId, fee-aware qty)
- [[reconcile-as-truth]] — восстановление после разрыва связи: все четыре вердикта (AGREE/HEAL/EXITED/DIVERGENCE) и heal-механизм
- [[emergency-flatten-and-residual]] — каскад `flatten()` и остаток после частичного стопа: самый опасный денежный путь
- [[bybit-order-adapter]] — адаптер, превращающий `start_bracket`/`arm_oco` в реальные REST-вызовы Bybit V5
- [[bybit-private-websocket]] — источник событий `Filled`/`Triggered`, который двигает FSM в `on_order_event`
- [[bybit-rest-client-and-backoff]] — REST-слой и защита от лимитов частоты (почему reconcile-вызовы идут без блокировки)
- [[execution-state-persistence-and-halt-audit]] — как FSM-состояние переживает перезапуск и как ведётся журнал аварийных остановок

Что происходит до входа и вокруг него:

- [[main-loop-tick]] — тик RuntimeManager: единственный инициатор входа, вызывает `start_bracket` и фоновые страховки каждый тик
- [[end-to-end-overview]] — карта всего потока «свеча → сигнал → риск → ордер»; этот обзор — детализация её последнего звена
- [[signal-architecture]] — объект Signal (LONG/FLAT), с которого начинается каждая сделка
- [[bar-model]] — свеча (bar), которую стратегия получает на вход перед выдачей сигнала
- [[risk-overview-decision-pipeline]] — как RiskManager рассчитывает qty, TP и SL перед передачей Coordinator
- [[bybit-filters]] — минимальный шаг лота и округление (qty_step, dust), от которых зависит fee-aware OCO qty

Остановки и аварийные пути:

- [[safety-stops-and-halts]] — все уровни защиты и состояние `HALTED`, куда FSM уходит при таймауте арминга или расхождении
- [[halt-gate-precommitted-criteria]] — «красные линии» демо-режима, пересечение которых полностью глушит торговлю
- [[kill-switch-emergency-stop]] — аварийный стоп оператора и состояние `KILLED` в перечислении FSM

Глоссарий:

- [[glossary-entry]] — краткие определения базовых терминов: ордер, позиция, вход, выход, стоп-лосс, тейк-профит

За техническими деталями ADR: `llm-wiki/wiki/project/decisions/` (ADR 0019, 0020, 0021, 0022).
