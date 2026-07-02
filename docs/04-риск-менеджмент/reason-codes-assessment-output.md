---
title: "Словарь причин и итог решения: коды событий риска"
section: "04-риск-менеджмент"
status: filled
money_core: false
updated: 2026-06-26
source_files: src/risk/reason_codes.py, src/risk/models.py
---

# Словарь причин и итог решения: коды событий риска

**TL;DR:** Каждое решение риск-менеджера — одобрить сделку, отказать или остановить бота — записывается с машиночитаемой пометкой: кодом причины. Таких кодов сейчас 67, они никогда не переименовываются, и именно по ним можно восстановить картину произошедшего в любой момент — как по тахографу у грузовика.

---

## Простыми словами

Представьте, что каждое решение бота — это запись в судовом журнале корабля. Капитан (риск-менеджер) не просто говорит «не идём» — он пишет: «порт закрыт по причине шторма, код HALT_FLASH_CRASH». Или: «вышли из позиции, потому что сработал стоп-лосс, код EXIT_SL_HIT».

Зачем это нужно?

- **Пост-мортем** (разбор полётов после события) — если бот остановился, мы знаем точно почему, а не гадаем по логам. «Пост-мортем» — это анализ произошедшего уже после того, как что-то пошло не так.
- **Журнал аудита** (audit log) — полная история решений, машиночитаемая и неизменяемая. Это как банковская выписка: каждая операция пронумерована и помечена.
- **Атрибуция стратегий** — каждый вход в сделку несёт код, из которого видно, какая именно стратегия его сгенерировала. Без этого журнал превращается в кашу, где непонятно — это [[ema-crossover-strategy|EMA]] сработала или [[kronos-ml-strategy|Kronos]]?

Коды называют **reason codes** (коды причины), и главное правило: **IMMUTABLE** — они никогда не переименовываются. Если завтра потребуется новый код — нужно вносить поправку в ADR (Architecture Decision Record — внутренний документ-решение команды, фиксирующий «почему сделано именно так»). Это гарантирует, что исторические записи в журнале всегда читаются корректно, даже через год.

`(src/risk/reason_codes.py:1-8)`

---

## Как это работает у нас

### Структура: перечисление (enum)

Все коды собраны в один Python-класс `ReasonCode`, который является **перечислением** (enum) — закрытым списком допустимых значений. Ни один код не может быть строкой произвольного содержания: только то, что явно объявлено в списке. `(src/risk/reason_codes.py:45)`

```python
class ReasonCode(StrEnum):
    ENTRY_LONG_EMA_CROSS_UP = "ENTRY_LONG_EMA_CROSS_UP"
    EXIT_SL_HIT = "EXIT_SL_HIT"
    HALT_DRAWDOWN_L1 = "HALT_DRAWDOWN_L1"
    # ... всего 67 кодов
```

Тип `StrEnum` означает, что каждый код — одновременно и строка, и элемент перечисления. Это важно: код можно сохранить в базу как обычный текст и потом прочитать обратно.

### Категории кодов: 4 семейства

Всего **67 кодов** на момент Спринта 52. `(src/risk/reason_codes.py:38-39)`

| Семейство | Кол-во | Что обозначает |
|---|---|---|
| `ENTRY_*` | 11 | Вход в позицию (покупка) |
| `EXIT_*` и `SCALE_*` | 23 | Выход из позиции или частичная корректировка |
| `REJECT_*` | 9 | Отказ: сделка не прошла проверку |
| `HALT_*` и `KILL_SWITCH_REQUESTED` | 24 | Остановка бота на уровне системы |

---

### Семейство ENTRY — входы в сделку

Код ENTRY означает: «стратегия решила купить, риск-менеджер одобрил». У каждой стратегии — свой код, по которому в журнале сразу видно, кто принял решение.

| Код | Стратегия / условие |
|---|---|
| `ENTRY_LONG_EMA_CROSS_UP` | [[ema-crossover-strategy\|EMA-crossover]]: быстрая скользящая средняя пересекает медленную вверх |
| `ENTRY_LONG_MEANREV_RSI_BB` | [[mean-reversion-strategy\|Mean-reversion]]: [[ema-rsi-indicators\|RSI]] в зоне перепроданности и цена у нижней [[bollinger-bands-indicator\|полосы Боллинджера]] |
| `ENTRY_LONG_DONCHIAN_BREAKOUT` | [[donchian-breakout-strategy\|Donchian]]: цена пробила верхний [[donchian-channel-indicator\|канал]] |
| `ENTRY_LONG_VOLUME_BREAKOUT` | [[volume-breakout-strategy\|Volume breakout]]: объёмный пробой |
| `ENTRY_LONG_ATR_BREAKOUT` | [[atr-breakout-strategy\|ATR breakout]]: пробой с учётом волатильности |
| `ENTRY_LONG_SUPERTREND` | [[supertrend-strategy\|Supertrend]]: тренд переключился с медвежьего на бычий |
| `ENTRY_LONG_KRONOS` | [[kronos-ml-strategy\|Kronos]]: ML-модель прогнозирует рост выше порога |
| `ENTRY_LONG_TREND_FOLLOWING` | Общий трендовый вход (используется как fallback, подробнее ниже) |
| `ENTRY_LONG_PULLBACK` | Откат к тренду |
| `ENTRY_SHORT_TREND_FOLLOWING` | Короткая позиция — в v0.1 не используется |
| `ENTRY_SHORT_PULLBACK` | Откат по короткой — в v0.1 не используется |

`(src/risk/reason_codes.py:47-51, 122-152)`

Коды SHORT и `SCALE_IN_SHORT` объявлены, но не используются в v0.1: бот торгует только в лонг (только покупает). Это ограничение заложено в [[execution-state-machine|FSM]] (машине состояний исполнения) и проверяется в `manager.assess()`. `(src/risk/manager.py:213-218)`

---

### Семейство EXIT / SCALE — выходы и корректировки

EXIT-коды делятся на два подсемейства:

**Системные выходы** (без префикса `EXIT_FLAT_`) — наиболее частые в реальной торговле:

| Код | Что произошло |
|---|---|
| `EXIT_SL_HIT` | Сработал стоп-лосс — цена упала до уровня «больше не терпим потерю» |
| `EXIT_TP_HIT` | Сработал тейк-профит — цена достигла цели прибыли |
| `EXIT_TRAILING_STOP` | Трейлинг-стоп (стоп, следующий за растущей ценой) |
| `EXIT_SIGNAL_FLIP` | Общий код разворота сигнала (системный) |
| `EXIT_TIME_STOP` | Вышли по истечению времени, а не по цене |
| `EXIT_MANUAL_OVERRIDE` | Оператор [[manual-override-resume\|вручную]] закрыл позицию |
| `EXIT_CIRCUIT_BREAKER` | Экстренное закрытие из-за [[circuit-breakers-drawdown-flash\|circuit breaker]] |
| `EXIT_OCO_PARTIAL_TIMEOUT` | Частичная [[oco-bracket-emulation\|OCO]]-заявка истекла по таймауту |
| `EXIT_STOP_RESIDUAL_FLATTEN` | Закрытие [[emergency-flatten-and-residual\|остатка позиции после исполнения стопа]] |
| `EXIT_RECONCILE_DETECTED` | [[reconcile-as-truth\|Брокер подтвердил позицию]], которую бот считал открытой |

**Стратегийные выходы** (с префиксом `EXIT_FLAT_`) — как именно конкретная стратегия закрыла позицию:

| Код | Стратегия / условие |
|---|---|
| `EXIT_FLAT_SIGNAL_FLIP` | EMA: медвежье пересечение скользящих средних |
| `EXIT_FLAT_MEANREV_REVERT` | Mean-reversion: цена вернулась к средней полосе или RSI нормализовался |
| `EXIT_FLAT_ATR_STOP` | Donchian: ATR-трейлинг-стоп |
| `EXIT_FLAT_CHANNEL` | Donchian: цена ушла под нижний канал |
| `EXIT_FLAT_VOLUME_CHANNEL` | Volume breakout: Donchian-канальный выход |
| `EXIT_FLAT_ATR_STOP_VB` | Volume breakout: ATR-стоп внутри бара |
| `EXIT_FLAT_ATR_REVERSE` | ATR breakout: обратный пробой |
| `EXIT_FLAT_ATR_STOP_AB` | ATR breakout: ATR-стоп внутри бара |
| `EXIT_FLAT_SUPERTREND_FLIP` | Supertrend: тренд переключился с бычьего на медвежий |
| `EXIT_FLAT_KRONOS` | Kronos: ML-прогноз опустился ниже текущей цены |

`(src/risk/reason_codes.py:55-65, 123-152)`

Коды `SCALE_IN_LONG`, `SCALE_IN_SHORT`, `SCALE_OUT_PARTIAL` предназначены для частичных доборов и сокращений позиции; в v0.1 они объявлены, но в основном пути не задействованы. `(src/risk/reason_codes.py:51-55)`

---

### Семейство REJECT — отказы риск-менеджера

REJECT означает: «сигнал пришёл, но мы не входим в сделку». Позиция не открывается, деньги не тратятся. Всего 9 кодов:

| Код | Когда возникает |
|---|---|
| `REJECT_MIN_NOTIONAL` | После округления размера позиции получился ноль — сделка бессмысленна |
| `REJECT_RISK_EXCEEDED` | Резервный код для превышения риска (ближайший аналог «нулевого размера») |
| `REJECT_INSUFFICIENT_BALANCE` | Недостаточно средств на балансе |
| `REJECT_STALE_DATA` | Данные устарели — сигнал пришёл на основе старых свечей ([[data-quality-detector\|детектор качества данных]]) |
| `REJECT_RATE_LIMITED` | Биржа ограничила [[bybit-rest-client-and-backoff\|частоту запросов]] |
| `REJECT_CLOCK_DRIFT` | [[clock-drift-monitor\|Разница в часах]] между ботом и биржей — сигнал рискует прийти «из будущего» |
| `REJECT_FILTER_PRICE` | Цена не прошла [[bybit-filters\|биржевой фильтр]] (допустимый шаг цены, лимиты) |
| `REJECT_DUPLICATE_SIGNAL` | Сигнал уже был обработан ранее (дубликат) |
| `REJECT_ORDER_ALREADY_TERMINAL` | Ордер уже в конечном состоянии (исполнен или отменён) |

`(src/risk/reason_codes.py:67-75)`

В реальном коде `manager.assess()` **активно эмитирует только `REJECT_MIN_NOTIONAL`** — как первый отказ денежного пути при нулевом размере после округления до 8 знаков. Прочие REJECT-коды возникают в других частях системы: [[bybit-order-adapter|адаптер Bybit]], [[coordinator-orchestration|координатор]]. `(src/risk/manager.py:278-286)`

Вот как выглядит эта проверка в коде:

```python
qty = qty.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

if qty <= 0:
    return self._reject(
        signal,
        assessed_at,
        ReasonCode.REJECT_MIN_NOTIONAL,
        kelly_phase=phase,
        kelly_fraction=f,
    )
```

`(src/risk/manager.py:276-286)`

**Минимальный номинал ордера** (min notional) — требование биржи ([[bybit-filters|фильтры Bybit]]): сделка должна быть на сумму не менее определённого минимума. Если после округления объём слишком мал — ордер даже не отправляется на биржу.

---

### Семейство HALT и KILL_SWITCH — остановки бота

Halt (остановка) — это когда бот перестаёт торговать на уровне всей системы. Не «не входим в эту конкретную сделку», а «весь бот стоит до выяснения». Всего 24 кода.

#### Остановки по уровням просадки ([[circuit-breakers-drawdown-flash|circuit breaker]])

«Просадка» (drawdown) — насколько упал счёт от пика ([[equity-tracking|как бот измеряет просадку]]). Три уровня предохранителя, плюс flash-обвал:

| Код | Уровень |
|---|---|
| `HALT_DRAWDOWN_L1` | Просадка L1 — предупреждение, снижение размера позиций |
| `HALT_DRAWDOWN_L2` | Просадка L2 — торговля остановлена частично |
| `HALT_DRAWDOWN_L3` | Просадка L3 — полная остановка |
| `HALT_FLASH_CRASH` | Молниеносный обвал: цена за один бар упала более чем на заданное [[atr-indicator\|ATR]]-кратное |

Эти четыре кода выставляются через метод `_halt_to_reason()`, который переводит уровень предохранителя (`HaltState`) в код причины: `(src/risk/manager.py:354-360)`

```python
@staticmethod
def _halt_to_reason(state: HaltState) -> ReasonCode:
    return {
        HaltState.L1: ReasonCode.HALT_DRAWDOWN_L1,
        HaltState.L2: ReasonCode.HALT_DRAWDOWN_L2,
        HaltState.L3: ReasonCode.HALT_DRAWDOWN_L3,
        HaltState.FLASH: ReasonCode.HALT_FLASH_CRASH,
    }[state]
```

#### Остановки HaltGate ([[halt-gate-precommitted-criteria|предзафиксированные критерии]])

[[halt-gate-precommitted-criteria|HaltGate]] — «четыре красные линии», пересечение которых останавливает бота. Они записаны заранее, до начала торговли, как договорённость оператора с самим собой («если потеряем более N% — стоп»). `(src/risk/halt_gate.py:35-73)`

| Код | Триггер |
|---|---|
| `HALT_S36_DD_INTRADAY` | Внутридневная просадка достигла заданного порога |
| `HALT_S36_DD_MULTIDAY` | Многодневная накопленная просадка достигла порога |
| `HALT_S36_CONSECUTIVE_LOSSES` | Подряд идут N или более убыточных сделок |
| `HALT_S36_NO_TRADE_TIMEOUT` | Ни одной сделки за N или более месяцев (сигнальное голодание) |

Приоритет срабатывания (при нескольких нарушениях побеждает первый): внутридневная DD → многодневная DD → серия потерь → таймаут. `(src/risk/halt_gate.py:63-73)`

Диспетчеризация `HaltTrigger → ReasonCode` описана в `src/runtime/manager.py:44-49`.

#### Остановка [[kill-switch-emergency-stop|kill-switch]] (экстренная кнопка оператора)

| Код | Что это |
|---|---|
| `KILL_SWITCH_REQUESTED` | Оператор создал файл-sentinel `.kill_switch` — бот замечает его на следующем тике и останавливается |

`(src/runtime/manager.py:293)` — `coordinator.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)`

Kill-switch — это «красная кнопка» без программирования: просто создать файл в нужном месте, и бот сам встанет при очередной итерации цикла.

#### Остановка fail-closed при неизвестном символе

| Код | Когда возникает |
|---|---|
| `HALT_UNKNOWN_SYMBOL` | Символ, с которым работает бот, не найден в разрешённом белом списке — бот немедленно останавливается |

`(src/runtime/manager.py:206, 224)` — «fail-closed» означает «при малейшем сомнении — стой». Если биржа вернула символ, которого нет в разрешённом списке, это потенциальная ошибка конфигурации — безопаснее остановиться, чем торговать «непонятно чем».

#### Прочие технические остановки

| Код | Причина |
|---|---|
| `HALT_RUNTIME_CRASH` | Необработанное исключение в основном цикле RuntimeManager |
| `HALT_BAR_POLL_STALL` | N подряд провалившихся [[bar-source-live\|запросов свечей]] к REST API (по умолчанию N=24) |
| `HALT_DATA_QUALITY` | Плохое [[data-quality-detector\|качество рыночных данных]] |
| `HALT_EXCHANGE_OUTAGE` | Биржа недоступна |
| `HALT_KILL_SWITCH` | Ранний код остановки (не путать с `KILL_SWITCH_REQUESTED`) |
| `HALT_RECONCILE_DIVERGENCE` | [[reconcile-as-truth\|Расхождение]] между состоянием бота и данными биржи |
| `HALT_BRACKET_INCOMPLETE` | [[oco-bracket-emulation\|OCO-скобка]] не собрана полностью |
| `HALT_OCO_ARM_TIMEOUT` | OCO-заявка не активировалась за отведённое время |
| `HALT_OCO_SIBLING_STUCK` | Парная нога OCO «застряла» |
| `HALT_PARTIAL_FILL_BELOW_MIN` | Частичное исполнение оказалось ниже минимального номинала |
| `HALT_FLATTEN_FAILED` | [[emergency-flatten-and-residual\|Не удалось закрыть позицию]] при аварийном сглаживании |
| `HALT_PHANTOM_SL` | Стоп-ордер исчез на бирже без исполнения («призрак») |
| `HALT_BOOTSTRAP_AMBIGUOUS` | Неоднозначный запуск: неясно, была ли открытая позиция |
| `HALT_EXIT_RECONCILE_DIVERGENCE` | Расхождение при закрытии позиции |

`(src/risk/reason_codes.py:77-119)`

---

### Атрибуция стратегий: как `manager.assess()` резолвит код

Когда стратегия генерирует [[signal-architecture|торговый сигнал]], она включает строку с причиной (`signal.reason`). `manager.assess()` пытается найти эту строку в перечислении `ReasonCode`. Если находит — записывает точный код. Если нет (строка неизвестная) — записывает общий fallback `ENTRY_LONG_TREND_FOLLOWING`. `(src/risk/manager.py:297-300)`

```python
try:
    reason_code = ReasonCode(signal.reason)
except ValueError:
    reason_code = ReasonCode.ENTRY_LONG_TREND_FOLLOWING
```

**История этого механизма** (баг H6, Спринт 49):

До Спринта 39 код был жёстко прошит — все стратегии всегда получали `ENTRY_LONG_TREND_FOLLOWING` вне зависимости от реального источника. Атрибуция была полностью потеряна.

В Спринте 49 обнаружился баг HIGH: три стратегии (EMA, mean-reversion, Donchian) генерировали строки причины, которые отсутствовали в перечислении `ReasonCode` — поэтому resolver всегда падал на `ValueError` и записывал fallback. В рамках ADR 0023 добавили 7 новых кодов (57–63), и атрибуция была восстановлена.

`(src/risk/reason_codes.py:32-35, 133-136)`

---

## RiskAssessment — финальный «вердикт»

Итог работы `manager.assess()` — это объект `RiskAssessment` (оценка риска, «вердикт»). Он **immutable** (неизменяем): после создания его поля нельзя изменить. `(src/risk/models.py:25-60)`

### Поля вердикта

| Поле | Тип | Что означает |
|---|---|---|
| `signal_id` | UUID | Идентификатор сигнала, которому выдан вердикт |
| `approved` | bool | `True` — входим в сделку, `False` — отказ или стоп |
| `qty` | Decimal или None | Сколько единиц актива купить (None при отказе) |
| `sl_price` | Decimal или None | Цена стоп-лосса (None при отказе) |
| `tp_price` | Decimal или None | Цена тейк-профита (None при отказе) |
| `kelly_phase` | 1 / 2 / 3 / 4 | Текущая фаза [[position-sizing-kelly\|Kelly-критерия]] (от осторожной к полной) |
| `kelly_fraction` | Decimal | Доля капитала по Kelly (0 при отказе) |
| `halt_state` | HaltState | Текущий уровень предохранителя (L0 = норма) |
| `reason_code` | ReasonCode | Код причины данного решения |
| `assessed_at` | datetime | Метка времени принятия решения |

`(src/risk/models.py:31-39)`

### HaltState — уровень предохранителя в момент решения

`HaltState` — перечисление из пяти значений: `L0` (норма), `L1`, `L2`, `L3` (три уровня просадки), `FLASH` (молниеносный обвал). Вердикт всегда несёт снимок актуального уровня на момент принятия решения. `(src/risk/models.py:17-22)`

---

## Правила согласованности (consistency validator)

Вердикт нельзя создать логически противоречивым — Pydantic автоматически проверяет правила при каждом создании объекта. Если проверка не пройдена — объект не создаётся. `(src/risk/models.py:47-60)`

**Если одобрено (`approved=True`):**
- `qty` обязан быть > 0 — нельзя «одобрить» сделку без размера
- `sl_price` и `tp_price` обязаны быть заданы — нельзя войти без ориентиров выхода
- `tp_price` строго больше `sl_price` — тейк-профит всегда выше стоп-лосса

**Если отказ (`approved=False`):**
- `qty` обязан быть `None` или 0 — нельзя «отказать» и одновременно указать размер

---

## Примеры / сценарии

### Сценарий 1: нормальный вход по стратегии Kronos

Стратегия Kronos видит, что ML-модель прогнозирует рост на следующем баре. Генерирует сигнал с `reason="ENTRY_LONG_KRONOS"`.

`manager.assess()` проходит по цепочке:
1. Сторона: LONG — ок
2. Время: сигнал не из будущего — ок
3. Flash-CB: нет резкого обвала — ок
4. Halt-state: L0, торговля разрешена — ок
5. Kelly: phase=2, fraction рассчитана
6. Размер qty после округления вниз до 8 знаков: 0.00043200 — больше нуля
7. Резолвер: `ReasonCode("ENTRY_LONG_KRONOS")` — найдено в перечислении

**Вердикт в журнале:**

```text
approved=True
qty=0.00043200
sl_price=96800.00
tp_price=100200.00
kelly_phase=2
halt_state=L0
reason_code=ENTRY_LONG_KRONOS
```

### Сценарий 2: отказ из-за нулевого размера (REJECT_MIN_NOTIONAL)

Бот в самом начале работы, баланс очень мал. Kelly даёт крошечную долю, после округления `qty` = 0.

**Вердикт в журнале:**

```text
approved=False
qty=None
sl_price=None
tp_price=None
kelly_phase=1
halt_state=L0
reason_code=REJECT_MIN_NOTIONAL
```

Глядя на этот код, оператор сразу понимает: бот работает, стратегия видит сигнал, но денег пока недостаточно для минимального ордера.

### Сценарий 3: остановка по flash-crash

Цена BTC резко рухнула на 8% за один свечной бар, превысив ATR-порог flash-детектора. При следующем сигнале:

**Вердикт в журнале:**

```text
approved=False
qty=None
halt_state=FLASH
reason_code=HALT_FLASH_CRASH
```

По этой записи оператор мгновенно понимает: бот стоит из-за flash-обвала, а не из-за ошибки кода.

### Сценарий 4: потеря атрибуции (fallback)

Гипотетически: разработчик добавил новую стратегию, но не внёс её код в `ReasonCode`. Стратегия отправляет `reason="MY_NEW_STRATEGY"`. Resolver получает `ValueError`, перехватывает его, и записывает `ENTRY_LONG_TREND_FOLLOWING`.

Сделка одобряется, но в журнале теряется привязка к стратегии — именно это и произошло в баге H6. Именно поэтому при добавлении новой стратегии в код ADR-поправка на новый код обязательна.

---

## Подводные камни / что важно понимать

**1. Два разных EXIT_SIGNAL_FLIP.** Код `EXIT_SIGNAL_FLIP` (без `FLAT_`) — системный, выдаётся общей логикой разворота. Код `EXIT_FLAT_SIGNAL_FLIP` (с `FLAT_`) — специфичный для EMA-стратегии, именно её медвежье пересечение скользящих. `(src/risk/reason_codes.py:59, 139)` — не путайте при анализе журнала.

**2. `REJECT_ORDER_ALREADY_TERMINAL` живёт в адаптере Bybit, а не в риск-менеджере.** Запись с этим кодом означает событие на уровне исполнения ордера: Bybit ответил retCode 110001 («ордер уже завершён»). Адаптер Bybit использует свой *отдельный* внутренний enum `ReasonCode` (импортируется в координаторе как `AdapterReasonCode`), который не совпадает с канонічным `src/risk/reason_codes.py`. В том же адаптерном enum есть похожий код `REJECT_DUPLICATE_ORDER` (retCode 110072 — повтор размещения ордера с тем же `orderLinkId`), но это **адаптерный** код, а не канонічный. `(src/execution/bybit/errors.py:13, 22, 41, 45)`

Важно: канонічний `REJECT_DUPLICATE_SIGNAL` (src/risk/reason_codes.py:74) объявлен в перечислении, но нигде в `src/` не эмитируется — это зарезервированный слот, не активный путь кода. Если вы видите такой код в журнале — это артефакт ручного тестирования, а не штатный сигнал системы.

**3. `KILL_SWITCH_REQUESTED` и `HALT_KILL_SWITCH` — два разных кода.** `KILL_SWITCH_REQUESTED` (код 45 в хронологии) — операторский стоп через sentinel-файл. `HALT_KILL_SWITCH` — более ранний код, оба существуют в перечислении, но диспетчеризуются разными путями. `(src/risk/reason_codes.py:84, 109)`

**4. Коды SHORT в v0.1 объявлены, но не достижимы.** `ENTRY_SHORT_TREND_FOLLOWING`, `ENTRY_SHORT_PULLBACK`, `SCALE_IN_SHORT` существуют в перечислении, но `manager.assess()` принудительно проверяет сторону и выбрасывает ошибку при попытке обработать SHORT-сигнал. `(src/risk/manager.py:213-218)`

**5. Правило IMMUTABLE — это не просто слово.** Если код переименован, все исторические журнальные записи с прежним именем становятся нечитаемыми — никакой автоматической миграции нет. Именно поэтому история кодов (6 → 31 → 39 → 42 → 45 → 50 → 53 → 56 → 63 → 65 → 67) сохранена в комментарии модуля. `(src/risk/reason_codes.py:22-39)`

**6. Вердикт — снимок состояния, а не команда.** `RiskAssessment` фиксирует уровень предохранителя `halt_state`, фазу Kelly и fraction на момент принятия решения. Если между выдачей вердикта и реальным исполнением ордера что-то изменится — вердикт этого уже не увидит. Это сознательное упрощение v0.1.

---

## Связанные документы

### Риск-менеджмент (ядро)

- [[risk-overview-decision-pipeline]] — полная цепочка решений риск-менеджера, из которой reason_code — конечная метка
- [[circuit-breakers-drawdown-flash]] — механика HALT_DRAWDOWN_L1/L2/L3 и HALT_FLASH_CRASH
- [[halt-gate-precommitted-criteria]] — механика HALT_S36_* и предзафиксированных критериев HaltGate
- [[kill-switch-emergency-stop]] — KILL_SWITCH_REQUESTED и его жизненный путь от файла до остановки
- [[manual-override-resume]] — EXIT_MANUAL_OVERRIDE и снятие предохранителя оператором
- [[position-sizing-kelly]] — kelly_phase и kelly_fraction, которые несёт каждый вердикт
- [[equity-tracking]] — источник halt_state и просадки, по которой срабатывают HALT_DRAWDOWN_*
- [[trade-fill-history]] — где ENTRY-коды атрибуции физически оседают на закрытых сделках

### Откуда берётся код (вход в риск-менеджер)

- [[signal-architecture]] — Signal и signal.reason: строка причины, которую резолвер превращает в ReasonCode
- [[ema-crossover-strategy]] — источник ENTRY_LONG_EMA_CROSS_UP и EXIT_FLAT_SIGNAL_FLIP
- [[mean-reversion-strategy]] — источник ENTRY_LONG_MEANREV_RSI_BB и EXIT_FLAT_MEANREV_REVERT
- [[donchian-breakout-strategy]] — источник ENTRY_LONG_DONCHIAN_BREAKOUT, EXIT_FLAT_CHANNEL, EXIT_FLAT_ATR_STOP
- [[volume-breakout-strategy]] — источник ENTRY_LONG_VOLUME_BREAKOUT и семейства EXIT_FLAT_*_VB
- [[atr-breakout-strategy]] — источник ENTRY_LONG_ATR_BREAKOUT и EXIT_FLAT_ATR_REVERSE/*_AB
- [[supertrend-strategy]] — источник ENTRY_LONG_SUPERTREND и EXIT_FLAT_SUPERTREND_FLIP
- [[kronos-ml-strategy]] — источник ENTRY_LONG_KRONOS и EXIT_FLAT_KRONOS
- [[atr-indicator]] — ATR лежит в основе flash-детектора (HALT_FLASH_CRASH) и ATR-стопов
- [[ema-rsi-indicators]] — RSI как условие входа mean-reversion (ENTRY_LONG_MEANREV_RSI_BB)
- [[bollinger-bands-indicator]] — полосы Боллинджера как условие того же mean-reversion-входа
- [[donchian-channel-indicator]] — канал Дончиана как условие пробойных входов/выходов

### Где код возникает и оседает (исполнение и хранение)

- [[execution-state-machine]] — FSM запрещает SHORT (недостижимые ENTRY_SHORT_*) и порождает REJECT_ORDER_ALREADY_TERMINAL
- [[coordinator-orchestration]] — координатор эмитирует часть кодов и вызывает request_halt(ReasonCode)
- [[oco-bracket-emulation]] — HALT_BRACKET_INCOMPLETE, HALT_OCO_ARM_TIMEOUT, EXIT_OCO_PARTIAL_TIMEOUT
- [[emergency-flatten-and-residual]] — EXIT_STOP_RESIDUAL_FLATTEN, HALT_FLATTEN_FAILED, HALT_PHANTOM_SL
- [[reconcile-as-truth]] — EXIT_RECONCILE_DETECTED и HALT_RECONCILE_DIVERGENCE
- [[bybit-order-adapter]] — отдельный адаптерный enum ReasonCode (REJECT_ORDER_ALREADY_TERMINAL по retCode)
- [[bybit-rest-client-and-backoff]] — REJECT_RATE_LIMITED и HALT_BAR_POLL_STALL
- [[execution-state-persistence-and-halt-audit]] — где reason_code физически оседает в базе данных аудита

### Данные и качество (источник REJECT/HALT по данным)

- [[data-quality-detector]] — REJECT_STALE_DATA и HALT_DATA_QUALITY
- [[clock-drift-monitor]] — REJECT_CLOCK_DRIFT (сигнал «из будущего»)
- [[bybit-filters]] — REJECT_MIN_NOTIONAL и REJECT_FILTER_PRICE (минимальный номинал, шаг цены)
- [[bar-source-live]] — HALT_BAR_POLL_STALL при провале polling свечей

### Общая картина

- [[safety-stops-and-halts]] — обзорная карта всех тормозов бота, чьи события помечаются этими кодами
- [[main-loop-tick]] — где на каждом тике проверяются halt/kill-switch и потребляется вердикт RiskAssessment

За техническими деталями: `llm-wiki/wiki/project/components/risk-manager.md`
