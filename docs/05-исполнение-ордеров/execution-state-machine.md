---
title: "Конечный автомат исполнения (FSM): состояния и переходы ордера"
section: "05-исполнение-ордеров"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/execution/state_machine.py, src/execution/models.py
---

# Конечный автомат исполнения (FSM): состояния и переходы ордера

**TL;DR:** Каждый ордер бота живёт в строго определённом состоянии (например: «ждём исполнения», «позиция открыта и защищена»). Переходить из одного состояния в другое можно только по заранее прописанным правилам. Любая попытка нарушить правило — немедленная ошибка. Это защищает деньги от двойных входов, «призрачных» позиций и прочего хаоса.

## Простыми словами

Представьте светофор. Он всегда находится ровно в одном состоянии: «красный», «жёлтый» или «зелёный». Переключиться с зелёного сразу на красный невозможно — только через жёлтый. Если кто-то попытается прыгнуть через шаг — система ломается.

**Конечный автомат (FSM, Finite State Machine)** — это ровно та же идея, применённая к торговому ордеру. Бот всегда знает, в каком «цвете» находится каждая позиция, и какие переключения разрешены.

Зачем это нужно в трейдинге? Без этих правил могут произойти опасные ситуации:
- Бот попытается открыть сделку ещё раз, пока первая ещё не исполнена — «двойной вход».
- Защитные ордера (стоп-лосс и тейк-профит) сработают оба одновременно, продав монеты дважды.
- После разрыва интернет-соединения бот не поймёт, была ли позиция открыта, и начнёт действовать наугад.

FSM устроен так: у каждого состояния есть список разрешённых «команд» (событий), которые могут его изменить. Если приходит незнакомая команда — система немедленно выдаёт ошибку `IllegalTransitionError`, а не пытается угадать. [[coordinator-orchestration|Координатор]] перехватывает такую ошибку, записывает предупреждение в лог и отбрасывает событие: это защита от запоздавших дублирующихся сообщений биржи, которые не должны ронять бота.

**Простая аналогия для нашей торговли:**
```
Нет позиции (FLAT)
    → [решили войти] → Ждём исполнения (ENTRY_PENDING)
    → [биржа исполнила] → Позиция открыта, защита ставится (LONG_OPEN)
    → [стоп-лосс выставлен] → Позиция полностью защищена (OCO_ARMED)
    → [сработал стоп] → Закрываемся (EXIT_SIBLING_CANCELLING)
    → [отменили тейк-профит] → Снова без позиции (FLAT)
```

Все 76 разрешённых переходов прописаны в таблице `TRANSITIONS`. Всё остальное — запрещено.

## Как это работает у нас

### Файлы и структура

- `src/execution/state_machine.py` — три объекта: перечисление состояний `ExecutionState`, перечисление событий `ExecutionEvent`, таблица переходов `TRANSITIONS` и функция `apply()`.
- `src/execution/models.py` — доменные модели ордера: `Order`, `Fill`, типы и статусы.

### Состояния: 16 штук, сгруппированные по смыслу

Всего в системе **16 состояний** (`ExecutionState`), подтверждено кодом: `src/execution/state_machine.py:12-28`.

**Группа 1 — Спокойствие (нет позиции)**

| Состояние | Что это значит |
|---|---|
| `INIT` | Стартовое, только при запуске бота — инициализация. Сразу переходит в FLAT. |
| `FLAT` | Нет никакой открытой позиции. Бот готов к новой сделке. |
| `COOLDOWN` | Пауза после разрешения аварии. Бот «переводит дух» перед следующей сделкой. |

**Группа 2 — Вход в сделку**

| Состояние | Что это значит |
|---|---|
| `ENTRY_PENDING` | Ордер на покупку отправлен на биржу, ждём подтверждения исполнения. |
| `LONG_OPEN` | Биржа подтвердила покупку. Монеты у нас, но защитные ордера ещё не выставлены. Уязвимый момент! |

**Группа 3 — Позиция под защитой (OCO-броня)**

OCO (One Cancels the Other) — это когда мы выставляем одновременно и тейк-профит («продай, когда вырастет до X»), и стоп-лосс («продай, если упадёт до Y»). Когда одно исполняется — другое автоматически отменяется. На Bybit Spot эта функция эмулируется тремя раздельными ордерами (подробнее — [[oco-bracket-emulation]]).

| Состояние | Что это значит |
|---|---|
| `OCO_ARMING` | Тейк-профит уже выставлен, стоп-лосс ещё выставляется. TTL = 60 секунд. |
| `OCO_ARMED` | Оба защитных ордера активны. Позиция полностью под защитой. Нормальное рабочее состояние. |

**Группа 4 — Выход из сделки**

| Состояние | Что это значит |
|---|---|
| `EXIT_PENDING` | Ордер на закрытие отправлен, ждём исполнения биржи. |
| `EXIT_SIBLING_CANCELLING` | Один защитный ордер сработал (например, стоп-лосс), отменяем второй (тейк-профит). |
| `EXIT_SIBLING_CANCEL_FAILED` | Попытка отменить второй ордер не удалась с первого раза. Продолжаем пытаться. |
| `EXIT_SL_RESIDUAL` | Стоп-лосс исполнился частично (IOC — мгновенный). Остаток позиции надо дозакрыть рыночным ордером (см. [[emergency-flatten-and-residual]]). |

**Группа 5 — Восстановление**

| Состояние | Что это значит |
|---|---|
| `RECONCILING` | Связь с биржей была разорвана и восстановлена. Сверяем реальное состояние биржи с нашей базой (см. [[reconcile-as-truth]]). |
| `PARTIAL_FILL` | Устаревшее состояние (с версии S5). В новом коде недостижимо, но сохранено для совместимости с загруженными старыми данными. |

**Группа 6 — Аварийные состояния**

| Состояние | Что это значит |
|---|---|
| `HALTED` | Аварийная пауза. Бот ничего не делает. Оператор (или система рисков) остановили его. Можно возобновить. |
| `ERROR` | Ошибка протокола (например, биржа отвергла ордер на закрытие). Требует ручного сброса. |
| `KILLED` | Полная и необратимая остановка. Выходов нет — только перезапуск системы. |

### События: 30 «команд»

Событие (`ExecutionEvent`) — это входящий сигнал, меняющий состояние. Всего 30 событий (`src/execution/state_machine.py:31-64`):

**Управление жизненным циклом ордера:**
- `STATE_LOADED` — бот стартовал, загрузил состояние из базы.
- `ENTRY_PLACED` — ордер на покупку отправлен.
- `ENTRY_FILLED` — биржа подтвердила: ордер исполнен.
- `ENTRY_REJECTED` — биржа отвергла ордер на покупку (ошибку возвращает [[bybit-order-adapter|адаптер Bybit]]).
- `OCO_PLACED` — оба защитных ордера выставлены (устаревший путь S5).
- `TP_PLACED` — тейк-профит выставлен (новый путь v2).
- `SL_PLACED` — стоп-лосс выставлен (новый путь v2).
- `PARTIAL_FILL` — ордер исполнен частично.
- `EXIT_FILLED` — ордер на закрытие исполнен.
- `EXIT_REJECTED` — биржа отвергла ордер на закрытие.

**Срабатывание защитных ордеров** (эти факты приходят в реальном времени через [[bybit-private-websocket|приватный WebSocket]]):
- `SL_TRIGGERED` — стоп-лосс «взведён» (Triggered) биржей, ещё не исполнен — это окно для отмены тейк-профита.
- `SL_HIT` — стоп-лосс уже исполнен (Filled).
- `TP_HIT` — тейк-профит исполнен.
- `OCO_PARTIAL_TIMEOUT` — таймаут при частичном OCO.

**Аварийные события:**
- `BRACKET_TIMEOUT` — за 60 секунд оба защитных ордера не выставились.
- `SIBLING_CANCELLED` — второй ордер-«сосед» успешно отменён.
- `SIBLING_CANCEL_FAILED` — попытка отменить соседа не удалась.
- `RESIDUAL_FLATTENED` — остаток позиции закрыт.
- `FLATTEN_FAILED` — аварийное закрытие позиции провалилось.

**Системные события:**
- `WS_RECONNECT` — WebSocket-соединение с биржей восстановлено.
- `RECONCILE_OK` — сверка с биржей: всё совпадает.
- `RECONCILE_DIVERGENCE` — сверка с биржей: данные не совпадают.
- `RECONCILE_ENTRY_FILLED` — при сверке обнаружено: вход исполнился пока мы были офлайн.
- `RECONCILE_EXITED` — при сверке обнаружено: позиция закрылась пока мы были офлайн.
- `RISK_HALT` — [[risk-overview-decision-pipeline|система рисков]] требует остановки (например, сработал [[circuit-breakers-drawdown-flash|предохранитель просадки]]).
- `HALT_RESUME` — оператор возобновляет работу после HALTED.
- `COOLDOWN_DONE` — период охлаждения истёк, можно торговать.
- `KILL_SWITCH` — аварийный выключатель активирован.
- `KILL_SWITCH_REQUESTED` — оператор нажал «стоп» через CLI (не терминально, см. ниже).
- `MANUAL_RESET` — ручной сброс из ERROR в FLAT.

### Таблица переходов: 76 разрешённых маршрутов

`TRANSITIONS` — это словарь вида `(состояние, событие) → новое состояние`. Всего в нём **76 записей** (подтверждено кодом: `src/execution/state_machine.py:71-192`).

Ниже — полная таблица, сгруппированная по исходному состоянию. Она включает все 76 переходов, в том числе 6 из legacy-состояния `PARTIAL_FILL` (недостижимого в новом коде, но сохранённого для обратной совместимости со старыми данными в базе):

**INIT / FLAT / COOLDOWN — спокойные состояния**

| Откуда | Событие | Куда |
|---|---|---|
| INIT | STATE_LOADED | FLAT |
| FLAT | ENTRY_PLACED | ENTRY_PENDING |
| FLAT | KILL_SWITCH | KILLED |
| FLAT | KILL_SWITCH_REQUESTED | HALTED |
| FLAT | RISK_HALT | HALTED |
| COOLDOWN | COOLDOWN_DONE | FLAT |

**ENTRY_PENDING — ждём исполнения покупки**

| Откуда | Событие | Куда |
|---|---|---|
| ENTRY_PENDING | ENTRY_FILLED | LONG_OPEN |
| ENTRY_PENDING | ENTRY_REJECTED | FLAT |
| ENTRY_PENDING | WS_RECONNECT | RECONCILING |
| ENTRY_PENDING | RISK_HALT | HALTED |
| ENTRY_PENDING | KILL_SWITCH_REQUESTED | HALTED |

**LONG_OPEN — куплено, защита выставляется**

| Откуда | Событие | Куда |
|---|---|---|
| LONG_OPEN | TP_PLACED | OCO_ARMING |
| LONG_OPEN | OCO_PLACED | OCO_ARMED |
| LONG_OPEN | WS_RECONNECT | RECONCILING |
| LONG_OPEN | RISK_HALT | HALTED |
| LONG_OPEN | KILL_SWITCH | KILLED |
| LONG_OPEN | KILL_SWITCH_REQUESTED | HALTED |
| LONG_OPEN | FLATTEN_FAILED | HALTED |

**OCO_ARMING — тейк-профит выставлен, стоп-лосс ещё нет**

| Откуда | Событие | Куда |
|---|---|---|
| OCO_ARMING | SL_PLACED | OCO_ARMED |
| OCO_ARMING | BRACKET_TIMEOUT | HALTED |
| OCO_ARMING | ENTRY_REJECTED | HALTED |
| OCO_ARMING | PARTIAL_FILL | HALTED |
| OCO_ARMING | SL_TRIGGERED | HALTED |
| OCO_ARMING | WS_RECONNECT | RECONCILING |
| OCO_ARMING | RISK_HALT | HALTED |
| OCO_ARMING | KILL_SWITCH | KILLED |
| OCO_ARMING | KILL_SWITCH_REQUESTED | HALTED |
| OCO_ARMING | FLATTEN_FAILED | HALTED |

**OCO_ARMED — позиция под защитой (нормальное рабочее состояние)**

| Откуда | Событие | Куда |
|---|---|---|
| OCO_ARMED | SL_TRIGGERED | EXIT_SIBLING_CANCELLING |
| OCO_ARMED | TP_HIT | EXIT_SIBLING_CANCELLING |
| OCO_ARMED | SL_HIT | EXIT_PENDING |
| OCO_ARMED | PARTIAL_FILL | EXIT_SL_RESIDUAL |
| OCO_ARMED | OCO_PARTIAL_TIMEOUT | EXIT_PENDING |
| OCO_ARMED | WS_RECONNECT | RECONCILING |
| OCO_ARMED | RISK_HALT | HALTED |
| OCO_ARMED | KILL_SWITCH | KILLED |
| OCO_ARMED | KILL_SWITCH_REQUESTED | HALTED |
| OCO_ARMED | FLATTEN_FAILED | HALTED |

**EXIT_SIBLING_CANCELLING / EXIT_SIBLING_CANCEL_FAILED — отмена парного ордера**

| Откуда | Событие | Куда |
|---|---|---|
| EXIT_SIBLING_CANCELLING | SIBLING_CANCELLED | FLAT |
| EXIT_SIBLING_CANCELLING | SIBLING_CANCEL_FAILED | EXIT_SIBLING_CANCEL_FAILED |
| EXIT_SIBLING_CANCELLING | WS_RECONNECT | RECONCILING |
| EXIT_SIBLING_CANCELLING | RISK_HALT | HALTED |
| EXIT_SIBLING_CANCELLING | KILL_SWITCH | KILLED |
| EXIT_SIBLING_CANCELLING | KILL_SWITCH_REQUESTED | HALTED |
| EXIT_SIBLING_CANCEL_FAILED | SIBLING_CANCELLED | FLAT |
| EXIT_SIBLING_CANCEL_FAILED | WS_RECONNECT | RECONCILING |
| EXIT_SIBLING_CANCEL_FAILED | RISK_HALT | HALTED |
| EXIT_SIBLING_CANCEL_FAILED | KILL_SWITCH | KILLED |
| EXIT_SIBLING_CANCEL_FAILED | KILL_SWITCH_REQUESTED | HALTED |

**EXIT_SL_RESIDUAL — закрытие остатка позиции**

| Откуда | Событие | Куда |
|---|---|---|
| EXIT_SL_RESIDUAL | RESIDUAL_FLATTENED | FLAT |
| EXIT_SL_RESIDUAL | FLATTEN_FAILED | HALTED |
| EXIT_SL_RESIDUAL | WS_RECONNECT | RECONCILING |
| EXIT_SL_RESIDUAL | RISK_HALT | HALTED |
| EXIT_SL_RESIDUAL | KILL_SWITCH | KILLED |
| EXIT_SL_RESIDUAL | KILL_SWITCH_REQUESTED | HALTED |

**EXIT_PENDING — ждём исполнения ордера на закрытие**

| Откуда | Событие | Куда |
|---|---|---|
| EXIT_PENDING | EXIT_FILLED | FLAT |
| EXIT_PENDING | EXIT_REJECTED | ERROR |
| EXIT_PENDING | FLATTEN_FAILED | HALTED |
| EXIT_PENDING | WS_RECONNECT | RECONCILING |
| EXIT_PENDING | RISK_HALT | HALTED |
| EXIT_PENDING | KILL_SWITCH_REQUESTED | HALTED |

**RECONCILING — сверка после разрыва связи**

| Откуда | Событие | Куда |
|---|---|---|
| RECONCILING | RECONCILE_OK | OCO_ARMED |
| RECONCILING | RECONCILE_ENTRY_FILLED | LONG_OPEN |
| RECONCILING | RECONCILE_EXITED | FLAT |
| RECONCILING | RECONCILE_DIVERGENCE | HALTED |
| RECONCILING | RISK_HALT | HALTED |
| RECONCILING | KILL_SWITCH_REQUESTED | HALTED |

**PARTIAL_FILL (legacy) — устаревшее состояние, недостижимое в v2**

В новом коде это состояние недостижимо: событие `PARTIAL_FILL` из `OCO_ARMED` теперь ведёт в `EXIT_SL_RESIDUAL`, минуя `PARTIAL_FILL`. Однако переходы из него сохранены в таблице для корректной работы с данными, загруженными из старой базы (`src/execution/state_machine.py:82-84,88-89,93,99,190`).

| Откуда | Событие | Куда |
|---|---|---|
| PARTIAL_FILL | SL_HIT | EXIT_PENDING |
| PARTIAL_FILL | TP_HIT | EXIT_PENDING |
| PARTIAL_FILL | WS_RECONNECT | RECONCILING |
| PARTIAL_FILL | RISK_HALT | HALTED |
| PARTIAL_FILL | KILL_SWITCH | KILLED |
| PARTIAL_FILL | KILL_SWITCH_REQUESTED | HALTED |

**HALTED / ERROR / KILLED — аварийные состояния**

| Откуда | Событие | Куда |
|---|---|---|
| HALTED | HALT_RESUME | COOLDOWN |
| HALTED | KILL_SWITCH | KILLED |
| ERROR | MANUAL_RESET | FLAT |
| KILLED | _(нет исходящих переходов)_ | — |

### Функция apply() — «регулировщик»

`src/execution/state_machine.py:195-200`

```python
def apply(state: ExecutionState, event: ExecutionEvent) -> ExecutionState:
    """Apply event to state. Raise IllegalTransitionError if not in table."""
    try:
        return TRANSITIONS[(state, event)]
    except KeyError as e:
        raise IllegalTransitionError(f"{state} + {event} not allowed") from e
```

Логика предельно проста: ищем пару `(текущее состояние, событие)` в таблице. Нашли — возвращаем новое состояние. Не нашли — бросаем исключение `IllegalTransitionError`.

Это намеренная защита: исключение лучше, чем «угадывание». Вызывающий код — координатор — поймает `IllegalTransitionError`, запишет предупреждение в лог и **отбросит событие без изменения состояния** (`src/execution/coordinator.py:451-460`). Типичный случай: запоздавшее или дублирующееся сообщение от биржи о событии, которое уже было обработано ранее (например, «стоп-лосс сработал» приходит повторно). Переход в `HALTED` при этом **не происходит** — бот продолжает работу. Остановка через `HALTED` выполняется только явным вызовом `request_halt()` по другим путям (критический сбой, команда оператора, система рисков).

### Доменные модели ордера

`src/execution/models.py` содержит типы данных, которыми оперирует FSM:

**`OrderSide`** — сторона ордера (строки 10-12):
- `BUY` — покупка
- `SELL` — продажа

**`OrderType`** — тип ордера (строки 15-19):
- `MARKET` — рыночный (исполняется немедленно по текущей цене)
- `LIMIT` — лимитный (исполняется только при достижении указанной цены)
- `STOP_MARKET` — рыночный стоп (стоп-лосс: при достижении цены — немедленная продажа по рынку)
- `STOP_LIMIT` — лимитный стоп
- `TAKE_PROFIT` — тейк-профит

**`OrderStatus`** — статус ордера на бирже (строки 23-29):
- `NEW` — принят биржей, ожидает исполнения
- `PARTIALLY_FILLED` — исполнен частично
- `FILLED` — полностью исполнен
- `CANCELED` — отменён
- `EXPIRED` — истёк
- `REJECTED` — отвергнут биржей

**`Order`** — основная модель ордера (строки 32-51). Ключевые поля:
- `symbol`: только вид `XXXUSDT` (паттерн `^[A-Z]+USDT$` из строки 37)
- `orig_qty`: исходный объём > 0
- `executed_qty`: исполненный объём ≥ 0
- Встроенный валидатор строки 48-51: `executed_qty <= orig_qty` — нельзя исполнить больше, чем заказано.

**`Fill`** — запись об одной частичной сделке (строки 54-65). Неизменяемая (`frozen=True`). Хранит цену, количество, комиссию и признак `is_maker` (был ли ордер мейкером — важно для расчёта комиссии на Bybit).

## Примеры / сценарии

### Сценарий 1: Нормальная сделка (вход → стоп-лосс сработал)

```text
Начало дня:
  INIT → [STATE_LOADED] → FLAT

Стратегия дала сигнал "купить":
  FLAT → [ENTRY_PLACED] → ENTRY_PENDING

Биржа подтвердила покупку 0.1 BTC по 65 000 USDT:
  ENTRY_PENDING → [ENTRY_FILLED] → LONG_OPEN

Выставляем тейк-профит на 66 000 USDT:
  LONG_OPEN → [TP_PLACED] → OCO_ARMING

Выставляем стоп-лосс на 64 000 USDT:
  OCO_ARMING → [SL_PLACED] → OCO_ARMED

  --- позиция работает, рынок идёт против нас ---

Биржа сигнализирует: стоп-лосс «взведён» (Triggered):
  OCO_ARMED → [SL_TRIGGERED] → EXIT_SIBLING_CANCELLING

Отменяем тейк-профит, пока стоп-лосс ещё не исполнен:
  EXIT_SIBLING_CANCELLING → [SIBLING_CANCELLED] → FLAT

Позиция закрыта. Потеряли, сколько запланировали — не больше.
```

### Сценарий 2: Разрыв соединения во время сделки

```text
OCO_ARMED (позиция защищена) → [WS_RECONNECT] → RECONCILING

Бот запрашивает биржу: что на самом деле произошло?

Вариант А: всё цело, ничего не изменилось:
  RECONCILING → [RECONCILE_OK] → OCO_ARMED
  (продолжаем как ни в чём не бывало)

Вариант Б: стоп-лосс сработал, пока мы были офлайн:
  RECONCILING → [RECONCILE_EXITED] → FLAT
  (позиция уже закрыта — принимаем как факт)

Вариант В: данные биржи не сходятся с нашими:
  RECONCILING → [RECONCILE_DIVERGENCE] → HALTED
  (безопаснее остановиться и разобраться вручную)
```

### Сценарий 3: Оператор нажимает «стоп» через CLI

```text
OCO_ARMED → [KILL_SWITCH_REQUESTED] → HALTED
(Это НЕ терминально — оператор сможет возобновить работу)

HALTED → [HALT_RESUME] → COOLDOWN
(система «переводит дух»)

COOLDOWN → [COOLDOWN_DONE] → FLAT
(готовы к следующей сделке)
```

### Сценарий 4: Аварийный стоп-выключатель (терминальный)

```text
OCO_ARMED → [KILL_SWITCH] → KILLED
(Это терминально — выходов из KILLED нет в таблице переходов.
Требует полного перезапуска системы)
```

## Подводные камни / что важно понимать

### 1. Triggered ≠ Filled — у нас разные события для стоп-лосса

Когда стоп-лосс «взводится» на Bybit Spot, он проходит три стадии: `Untriggered → Triggered → Filled`. Это доказано в ходе тестирования биржевого API (ADR 0020 sub-decision 3, `src/execution/state_machine.py:41`).

Событие `SL_TRIGGERED` (взведён, но ещё не исполнен) — это критическое окно: именно в этот момент бот пытается отменить тейк-профит, чтобы не продать монеты дважды.

Событие `SL_HIT` (полностью исполнен) — это уже постфактум. Если дошли до `SL_HIT`, значит отменить TP не успели заранее, переходим к `EXIT_PENDING` напрямую.

Разница видна в таблице переходов из `OCO_ARMED`:
- `SL_TRIGGERED` → `EXIT_SIBLING_CANCELLING` (сначала отменяем TP)
- `SL_HIT` → `EXIT_PENDING` (TP уже не важен)

### 2. KILL_SWITCH и KILL_SWITCH_REQUESTED — принципиально разные вещи

**`KILL_SWITCH`** (9 переходов, все → `KILLED`) — это аварийный выключатель системы. Переход в `KILLED` необратим: из этого состояния нет ни одного выхода. Требует полного перезапуска бота (`src/execution/state_machine.py:96-100, 126, 166-168`).

**`KILL_SWITCH_REQUESTED`** (11 переходов, все → `HALTED`) — это оператор нажал «пауза» через командную строку (`python -m src kill`, подробнее — [[kill-switch-emergency-stop]]). Система пишет файл-сигнал `.kill_switch`, бот его замечает и переходит в `HALTED`. Из `HALTED` можно выйти через `HALT_RESUME → COOLDOWN → FLAT` (это делает [[manual-override-resume|ручное возобновление]]). Этот вариант не терминальный (ADR 0022 sub-decision 5, `src/execution/state_machine.py:57-59`).

### 3. OCO_ARMING — самый уязвимый момент, TTL = 60 секунд

Состояние `OCO_ARMING` означает: тейк-профит уже выставлен, стоп-лосс ещё нет. Позиция частично «голая». Если за 60 секунд стоп-лосс не выставится, срабатывает `BRACKET_TIMEOUT` → `HALTED`. Это намеренная защита от зависания в полузащищённом состоянии (ADR 0020 sub-decision 10, `src/execution/state_machine.py:45, 106`).

В этом состоянии любая нештатная ситуация (`PARTIAL_FILL`, `SL_TRIGGERED`, `ENTRY_REJECTED`, `FLATTEN_FAILED`) тоже ведёт в `HALTED` — лучше остановиться, чем рисковать.

### 4. PARTIAL_FILL — мёртвое состояние (legacy)

`PARTIAL_FILL` существует в коде только для обратной совместимости со старыми записями в базе данных (спринт S5). В версии v2 событие `PARTIAL_FILL` из состояния `OCO_ARMED` ведёт не в это состояние, а в `EXIT_SL_RESIDUAL`. Само состояние `PARTIAL_FILL` в новом коде недостижимо (`src/execution/state_machine.py:19`).

### 5. Незнакомое событие = предупреждение, не остановка бота

Если координатор попробует применить событие, которого нет в таблице переходов, функция `apply()` немедленно бросает `IllegalTransitionError`. Но это не приводит к остановке бота.

Координатор перехватывает исключение, записывает предупреждение в лог (`warning: on_order_event.illegal_transition_dropped`) и **тихо отбрасывает событие** — состояние FSM не меняется (`src/execution/coordinator.py:451-460`). Так устроена защита от запоздавших или дублирующихся эхо-сообщений биржи.

Пример: стоп-лосс уже сработал и был обработан, но WebSocket прислал ещё одно уведомление об этом же событии. Без этого перехвата бот бы упал. С ним — просто игнорирует дубликат.

Переход в `HALTED` выполняется только явно: через `request_halt()` из системы рисков, координатора или команды оператора.

### 6. ASCII-диаграмма основного happy path

```
                    STATE_LOADED
   INIT ─────────────────────────► FLAT
                                     │
                               ENTRY_PLACED
                                     │
                                     ▼
                              ENTRY_PENDING
                              │           │
                    ENTRY_FILLED      ENTRY_REJECTED
                              │           │
                              ▼           ▼
                          LONG_OPEN     FLAT
                              │
                          TP_PLACED
                              │
                              ▼
                          OCO_ARMING
                              │
                          SL_PLACED
                              │
                              ▼
                          OCO_ARMED ◄──── RECONCILE_OK ◄── RECONCILING
                          │       │                            ▲
                    SL_TRIGGERED  TP_HIT              WS_RECONNECT (из любого)
                          │       │
                          ▼       ▼
                   EXIT_SIBLING_CANCELLING
                          │
                   SIBLING_CANCELLED
                          │
                          ▼
                         FLAT

  Из почти любого состояния:
    [RISK_HALT / KILL_SWITCH_REQUESTED] ──► HALTED ──► COOLDOWN ──► FLAT
    [KILL_SWITCH] ──► KILLED (необратимо)
```

## Связанные документы

**Зона исполнения ордеров (05) — соседи FSM:**
- [[order-lifecycle-overview]] — общий обзор всей зоны исполнения; FSM — один из её компонентов (карта, куда встроен этот автомат)
- [[coordinator-orchestration]] — координатор, который вызывает `apply()`, ловит `IllegalTransitionError` и управляет переходами
- [[oco-bracket-emulation]] — как именно эмулируется OCO на Bybit Spot тремя ордерами (состояния `OCO_ARMING`/`OCO_ARMED`)
- [[reconcile-as-truth]] — детали сверки с биржей (ветка `RECONCILING` → `RECONCILE_OK`/`DIVERGENCE`/`EXITED`)
- [[emergency-flatten-and-residual]] — аварийное закрытие и ветка `EXIT_SL_RESIDUAL` (дозакрытие остатка после частичного стопа)
- [[execution-state-persistence-and-halt-audit]] — как текущее состояние FSM сохраняется в базе (переживает рестарт) и аудит-лог переходов
- [[bybit-order-adapter]] — слой, который отправляет ордера и возвращает отказы → события `ENTRY_REJECTED`/`EXIT_REJECTED`
- [[bybit-private-websocket]] — источник событий исполнения в реальном времени: `ENTRY_FILLED`, `SL_TRIGGERED`, `SL_HIT`, `TP_HIT`, `WS_RECONNECT`
- [[bybit-rest-client-and-backoff]] — синхронные запросы при сверке; `RATE_LIMIT_HIT` может привести координатор к переходу в `HALTED`

**Риск и аварийная остановка (события `RISK_HALT` / `KILL_SWITCH*`):**
- [[kill-switch-emergency-stop]] — как работает `python -m src kill` и разница между `KILL_SWITCH` (→ `KILLED`, необратимо) и `KILL_SWITCH_REQUESTED` (→ `HALTED`)
- [[manual-override-resume]] — снятие паузы и путь возобновления `HALTED → HALT_RESUME → COOLDOWN → FLAT`
- [[safety-stops-and-halts]] — все тормоза бота (стоп-файл, halt-пороги, аварийный выход), которые генерируют `RISK_HALT`/`KILL_SWITCH_REQUESTED`
- [[circuit-breakers-drawdown-flash]] — предохранители просадки и flash-обвала — один из источников события `RISK_HALT`
- [[risk-overview-decision-pipeline]] — риск-менеджер, который решает пускать ли сделку и может потребовать `RISK_HALT`

**Где FSM живёт в общем потоке (01):**
- [[main-loop-tick]] — главный цикл вызывает координатор/`apply()` каждый тик, ловит kill-switch и проверяет TTL «зависшего» `OCO_ARMING`
- [[end-to-end-overview]] — единая карта потока: Coordinator «ведёт FSM (машину состояний позиции)» между сигналом и биржей
- [[reconcile-and-monitor-commands]] — команда `reconcile-only`, запускающая вход в состояние `RECONCILING` без торговли
- [[run-modes-testnet-live-reconcile]] — режимы запуска, включая reconcile-контур, в котором отрабатывает сверка

За техническими деталями ADR: `llm-wiki/wiki/project/decisions/0019-sprint-5-execution-decisions.md`, `0020-sprint-6-execution-spot-oco-emulation.md`, `0021-sprint-7-resilience.md`, `0022-sprint-8a-live-runtime.md`.
