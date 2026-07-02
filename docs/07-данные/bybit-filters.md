---
title: "Фильтры биржи: минимальные размеры ордеров и округление"
section: "07-данные"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/marketdata/filters.py
---

# Фильтры биржи: минимальные размеры ордеров и округление

**TL;DR:** Биржа Bybit не принимает ордера произвольного размера — у каждой торговой пары есть жёсткие правила: минимальная и максимальная сумма, допустимый шаг количества и шаг цены. Бот хранит эти правила в модели `BybitFilters` и проверяет каждый ордер перед отправкой через `validate_order()`. Округление количества до допустимого шага в живом коде выполняет `_step_floor()` в [[coordinator-orchestration|координаторе]]; округление цены до шага тика (`round_price`) в production-цепочке не задействовано.

## Простыми словами

Представьте, что вы покупаете яблоки на рынке. Продавец говорит: «Меньше 100 граммов не продаю, больше 50 кг не возьмите — не унесёте. И взвешиваю только с точностью до 10 граммов». Это и есть фильтры.

На Bybit у каждой торговой пары (например, BTCUSDT — биткоин за доллары USDT) установлены аналогичные правила:

- **Шаг лота (step_size)** — минимальная «единица измерения» количества монет, которую биржа готова принять. Нельзя купить 0.00123456789 BTC — только кратное шагу. Для BTC на Bybit это 0.000001 BTC (одна миллионная доля).
- **Шаг цены (tick_size)** — минимальная «единица» цены, с которой работает биржа. Цену в ордере нельзя указать с точностью до долей копейки. Для BTCUSDT это 0.01 USDT — то есть цена всегда с двумя знаками после запятой.
- **Минимальное количество (min_order_qty)** — самая маленькая порция монет, которую биржа вообще принимает к торговле.
- **Максимальное количество (max_order_qty)** — верхний предел одного ордера.
- **Минимальный номинал (min_order_amt)** — минимальная сумма сделки в USDT (котируемая валюта). Даже если монет технически достаточно, сделка на 0.50 USDT может быть отклонена.

Если ордер нарушает хотя бы одно из этих правил, биржа его молча отклонит — и позиция не откроется. Для торгового бота это катастрофа: стратегия думает, что купила, а на самом деле нет.

Модуль `src/marketdata/filters.py` решает эту проблему: он хранит правила биржи и проверяет каждый ордер через `validate_order()` до отправки. Вспомогательные методы округления `round_qty()` и `round_price()` тоже определены в этом модуле, однако в production-цепочке они не вызываются (подробнее — в разделах «Шаг 3» и «Шаг 4»).

## Как это работает у нас

### Шаг 1. Модель данных — `BybitFilters`

Все правила хранятся в одной модели данных (`src/marketdata/filters.py:13-23`):

```python
class BybitFilters(BaseModel):
    symbol: str
    step_size: Decimal   # шаг количества базовой валюты (basePrecision)
    tick_size: Decimal   # шаг цены
    min_order_qty: Decimal
    max_order_qty: Decimal
    min_order_amt: Decimal   # минимальный номинал в котируемой валюте (USDT)
```

Модель объявлена «замороженной» (`frozen=True`) и запрещает лишние поля (`extra="forbid"`). Это значит: однажды загруженные правила биржи нельзя случайно изменить в процессе работы — они постоянны на всё время жизни объекта.

Тип `Decimal` (десятичное число с точной арифметикой) используется вместо обычного `float` намеренно: при торговле недопустимы округления вида `0.1 + 0.2 = 0.30000000000000004`, которые случаются с плавающей точкой.

### Шаг 2. Загрузка правил с биржи — `from_instruments_info()`

Реальные правила загружаются через [[bybit-rest-source|Bybit REST API]]: метод `/v5/market/instruments-info` возвращает JSON с двумя блоками — `lotSizeFilter` (правила для количества) и `priceFilter` (правила для цены).

Метод-конструктор `from_instruments_info()` парсит этот ответ (`src/marketdata/filters.py:26-46`):

```python
lot = item["lotSizeFilter"]
price = item["priceFilter"]
return cls(
    symbol=item["symbol"],
    step_size=Decimal(lot["basePrecision"]),
    tick_size=Decimal(price["tickSize"]),
    min_order_qty=Decimal(lot["minOrderQty"]),
    max_order_qty=Decimal(lot["maxOrderQty"]),
    min_order_amt=Decimal(lot["minOrderAmt"]),
)
```

Важная деталь — защита от «сдвига схемы» биржи (S49 B2). Исторически код обращался к `response["result"]["list"][0]` напрямую — и если Bybit вдруг вернул бы пустой список или изменил структуру ответа, возникло бы голое исключение `IndexError` или `KeyError`, сложное для диагностики. Теперь используется вспомогательная функция `_safe_extract_list()` из `src/marketdata/bybit/rest.py:106-124`, которая при любой проблеме с форматом ответа выбрасывает типизированный `BybitAPIError` с понятным сообщением вместо безликой ошибки индексирования.

[[bybit-rest-client-and-backoff|REST-клиент]] предоставляет удобный метод-обёртку для запроса фильтров (`src/marketdata/bybit/rest.py:156-163`):

```python
def get_filters(self, symbol: str) -> BybitFilters:
    """Fetch `/v5/market/instruments-info?category=spot&symbol=X` → filters."""
    resp = _retry_with_backoff(
        lambda: self._http.get_instruments_info(category="spot", symbol=symbol)
    )
    return BybitFilters.from_instruments_info(resp)
```

> **Текущее состояние (важно):** при [[startup-and-wiring|старте бота]] фильтры пока что задаются в виде жёстко прописанных значений-заглушек прямо в коде запуска (`src/__main__.py:114-121`), а не загружаются с биржи через `get_filters()`. Комментарий в коде объясняет: «production wiring will load filters via BybitRESTClient.get_filters(symbol) (deferred S12+)». Инфраструктура для загрузки с биржи уже готова (`get_filters` реализован), но интеграция в цепочку старта запланирована в следующих спринтах.

### Шаг 3. Вспомогательный метод `round_qty()` — что делает и где реально используется

Метод `round_qty()` определён в `src/marketdata/filters.py:48-50` и обрезает количество монет до ближайшего допустимого шага **снизу**:

```python
def round_qty(self, qty: Decimal) -> Decimal:
    """Round down to step_size (never exceed user-intended qty)."""
    return (qty / self.step_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * self.step_size
```

Логика округления вниз (`ROUND_DOWN`) правильная: если округлять вверх, бот мог бы купить чуть больше, чем планировала стратегия риска.

**Важно: `round_qty()` не вызывается нигде в production-коде.** Поиск по всему `src/` даёт ровно одно вхождение — само определение метода в `filters.py:48`. В живой цепочке ордеров округление количества до допустимого шага делает `_step_floor()` в координаторе (`src/execution/coordinator.py:549, 704, 728`):

```python
@staticmethod
def _step_floor(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0 or value <= 0:
        return Decimal("0")
    return (value / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step
```
(`src/execution/coordinator.py:872-875`)

Алгоритм у `round_qty()` и `_step_floor()` идентичен, но вызывается в production только `_step_floor()`. `round_qty()` используется только в тестах (`tests/unit/test_filters.py:40-41`).

### Шаг 4. Вспомогательный метод `round_price()` — определён, но не подключён

Метод `round_price()` определён в `src/marketdata/filters.py:52-54`:

```python
def round_price(self, price: Decimal) -> Decimal:
    """Round to tick_size (DOWN keeps us on the safe side for BUY limits)."""
    return (price / self.tick_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * self.tick_size
```

Идея верная: для лимитного ордера на покупку (BUY LIMIT) цену безопаснее округлять вниз — так мы платим не дороже запланированного.

**Однако `round_price()` — мёртвый код в production.** Поиск по всему `src/` не обнаруживает ни одного вызова: только определение в `filters.py:52`. Адаптер (`src/execution/bybit/adapter.py:215, 253, 285`) передаёт цену в `validate_order()` без предварительного округления. Это означает, что в живом коде цена ордера **не приводится к шагу тика автоматически** — за корректность цены отвечает вызывающая сторона. `round_price()` покрыт тестами (`tests/unit/test_filters.py:44-46`), но в production-цепочку не встроен.

### Шаг 5. Проверка перед отправкой — `validate_order()`

Перед каждой отправкой ордера — это ключевой шаг в [[order-lifecycle-overview|жизненном цикле ордера]] — вызывается `validate_order()`, который проверяет три условия (`src/marketdata/filters.py:56-69`):

```python
def validate_order(self, qty: Decimal, price: Decimal | None = None) -> None:
    if qty < self.min_order_qty:
        raise FilterViolation(f"qty {qty} < min_order_qty {self.min_order_qty}")
    if qty > self.max_order_qty:
        raise FilterViolation(f"qty {qty} > max_order_qty {self.max_order_qty}")
    if price is not None:
        notional = qty * price
        if notional < self.min_order_amt:
            raise FilterViolation(f"qty*price={notional} < min_order_amt {self.min_order_amt}")
```

Параметр `price` — необязательный. Для рыночных ордеров (MARKET) цена в момент формирования ордера неизвестна — она определяется только в момент исполнения. Поэтому проверка минимального номинала для рыночных ордеров пропускается: передаётся `price=None`.

Если проверка не пройдена, выбрасывается `FilterViolation` — типизированное исключение (`src/marketdata/filters.py:9-10`), наследующее от `ValueError`. Это позволяет координатору поймать именно нарушение фильтров и отреагировать корректно, не путая с другими ошибками.

### Как фильтры встроены в цепочку ордеров

[[bybit-order-adapter|Адаптер `BybitMarketAdapter`]] принимает `BybitFilters` при создании и вызывает `validate_order()` перед каждым типом ордера (`src/execution/bybit/adapter.py:152-155`):

- **Рыночный ордер** (MARKET buy при открытии): `self._filters.validate_order(qty=qty)` — без цены (`src/execution/bybit/adapter.py:215`)
- **Стоп-рыночный ордер** (SL): `self._filters.validate_order(qty=qty)` — тоже без цены (`src/execution/bybit/adapter.py:253`)
- **Лимитный ордер** (TP, часть [[oco-bracket-emulation|OCO-брекета]]): `self._filters.validate_order(qty=qty, price=price)` — с ценой, проверяется минимальный номинал (`src/execution/bybit/adapter.py:285`)

Координатор обращается к фильтрам через публичные свойства адаптера, а не напрямую в модель фильтров (S55 ARCH-03): `self._adapter.step_size` и `self._adapter.min_order_qty` (`src/execution/coordinator.py:859-869`). Это инкапсуляция: координатор не знает о внутренней структуре `BybitFilters`, он просто спрашивает у адаптера «какой шаг лота?».

## Формулы и расчёты

### Округление вниз к шагу

Общая формула (используется в `round_qty`, `round_price` и `_step_floor`):

```
результат = floor(значение / шаг) × шаг
```

**Что это считает:** делим на шаг, отбрасываем дробную часть (берём целую часть вниз), умножаем обратно на шаг. Получаем ближайшее допустимое значение, не превышающее исходное.

**Реализация в Python** — через `Decimal.quantize(Decimal("1"), rounding=ROUND_DOWN)` (`src/marketdata/filters.py:50, 54`; `src/execution/coordinator.py:875`).

**Кто что вызывает в production:** только `_step_floor()` из `coordinator.py` встроен в живую цепочку ордеров. `round_qty()` и `round_price()` из `BybitFilters` покрыты тестами, но в production не вызываются.

### Проверка минимального номинала

```
qty × price ≥ min_order_amt
```

**Что это считает:** сумма сделки в котируемой валюте (USDT) должна быть не меньше порога. Для BTCUSDT этот порог — 1 USDT (`tests/unit/test_filters.py:18`).

Проверяется только для ордеров с известной ценой (`src/marketdata/filters.py:66-69`).

## Примеры / сценарии

### Пример 1: как работает формула округления и проверки (иллюстрация методов)

Параметры BTCUSDT из тестовой фикстуры (`tests/unit/test_filters.py:15-23`):
- `step_size = 0.000001` (шаг — одна миллионная BTC)
- `tick_size = 0.01` (шаг цены — 1 цент)
- `min_order_qty = 0.000048` BTC
- `min_order_amt = 1` USDT

**Иллюстрация `round_qty()` (метод `filters.py:48-50`, в тестах):**
```
qty = 0.0012345678
qty / step_size = 0.0012345678 / 0.000001 = 1234.5678
floor(1234.5678) = 1234
qty_rounded = 1234 × 0.000001 = 0.001234 BTC
```
Результат: 0.001234 BTC (проверено: `tests/unit/test_filters.py:40`).
В production та же формула выполняется через `_step_floor()` координатора.

**Иллюстрация `round_price()` (метод `filters.py:52-54`, в тестах; в production не вызывается):**
```
price = 60123.456
price / tick_size = 60123.456 / 0.01 = 6012345.6
floor(6012345.6) = 6012345
price_rounded = 6012345 × 0.01 = 60123.45 USDT
```
Результат: 60 123.45 USDT (проверено: `tests/unit/test_filters.py:46`).

**Проверка `validate_order()` (активна в production):**
- qty = 0.001234 ≥ min_order_qty 0.000048 ✓
- qty = 0.001234 ≤ max_order_qty 71.73956243 ✓
- notional = 0.001234 × 60123.45 = **74.19 USDT** ≥ min_order_amt 1 ✓

Ордер проходит — биржа его примет.

---

### Пример 2: крошечный ордер отклоняется по min_order_qty

Стратегия сигналит купить 0.00001 BTC (меньше минимума 0.000048):
```
qty = 0.00001
0.00001 < 0.000048  →  FilterViolation: "qty 0.00001 < min_order_qty 0.000048"
```
Ордер не отправляется на биржу. (Проверено: `tests/unit/test_filters.py:49-52`)

---

### Пример 3: ордер отклоняется по минимальному номиналу

0.0001 BTC при цене 0.01 USDT (гипотетический сценарий):
```
notional = 0.0001 × 0.01 = 0.000001 USDT
0.000001 < 1  →  FilterViolation: "qty*price=0.000001 < min_order_amt 1"
```
(Проверено: `tests/unit/test_filters.py:55-59`)

---

### Пример 4: рыночный ордер без цены

При открытии позиции рыночным ордером вызов:
```python
self._filters.validate_order(qty=Decimal("0.001"))  # price=None
```
Проверяются только min/max количества; проверка номинала пропускается, потому что рыночная цена определяется биржей в момент исполнения (`src/execution/bybit/adapter.py:215`, `src/marketdata/filters.py:60`).

## Подводные камни / что важно понимать

**1. Фильтры — заглушки при старте, и они расходятся с реальными данными биржи (временно)**

В текущей версии бот стартует с жёстко прописанными значениями-заглушками (`src/__main__.py:114-121`):

```
min_order_qty = 0.00001
max_order_qty = 100
```

Реальные параметры BTCUSDT на Bybit, зафиксированные в тестовой фикстуре (`tests/unit/test_filters.py:17-18`), отличаются:

```
minOrderQty  = 0.000048   (биржа)  vs  0.00001  (заглушка)
maxOrderQty  = 71.73956243 (биржа)  vs  100      (заглушка)
```

Практическое последствие: с заглушкой `min_order_qty=0.00001` бот признает валидным ордер qty=0.00003, но биржа его отклонит — настоящий порог 0.000048. Заглушки не загружаются с биржи динамически. Инфраструктура загрузки (`get_filters()` в `src/marketdata/bybit/rest.py:156-163`) уже готова, но интеграция в цепочку старта запланирована в следующих спринтах. До подключения динамической загрузки любое изменение правил биржи потребует обновления кода вручную.

**2. Округление количества в production — только через `_step_floor()` координатора**

В живой цепочке ордеров округление количества монет до шага биржи выполняет `_step_floor()` в координаторе (`src/execution/coordinator.py:549, 704, 728`) — в том числе при [[emergency-flatten-and-residual|аварийном закрытии позиции и обработке остатка-«пыли»]] ниже `min_order_qty` — а не `round_qty()` из `BybitFilters`. Оба метода используют одну формулу с `ROUND_DOWN` — но вызывается только `_step_floor()`. `round_qty()` существует в модели и покрыт тестами, однако в production-путь не встроен.

Что касается `round_price()`: метод определён, но не подключён ни к одному production-пути. Цена ордера перед отправкой к шагу тика не приводится автоматически. Это означает, что координатор или стратегия должны сами следить за корректностью цены.

**3. Фильтры в production-цепочке: только валидация, не мутация**

Адаптер `BybitMarketAdapter` подключает из `BybitFilters` исключительно `validate_order()` (`src/execution/bybit/adapter.py:215, 253, 285`). Метод проверяет — но не изменяет — количество и цену. Само по себе значение qty/price адаптер не округляет: он либо пропускает ордер, либо выбрасывает `FilterViolation`.

**4. Пустой список от биржи = понятная ошибка**

До спринта S49 при пустом ответе биржи (пустой `result.list`) возникал голый `IndexError` без контекста. Теперь `_safe_extract_list()` (`src/marketdata/bybit/rest.py:106-124`) проверяет структуру ответа и при проблемах выбрасывает `BybitAPIError` с понятным сообщением и кодом -1. Тесты покрывают все сценарии: пустой список, отсутствующий ключ `result`, нечисловой тип (`tests/unit/test_bybit_schema_guards.py`).

**5. `FilterViolation` — не критическая ошибка**

`FilterViolation` сигнализирует о попытке отправить заведомо невалидный ордер. Это «ожидаемое» нарушение контракта, которое код выше по стеку должен обработать корректно (например, пропустить сигнал). Оно не приводит к аварийной остановке бота напрямую, в отличие от ошибок сети или API.

**6. Модель `BybitFilters` — иммутабельна**

`frozen=True` в `ConfigDict` означает, что попытка изменить любое поле после создания объекта вызовет ошибку. Это намеренное решение: правила биржи загружаются один раз при старте и должны оставаться неизменными на всё время жизни компонента.

## Связанные документы

- [[bybit-order-adapter]] — адаптер ордеров: как `BybitFilters` используется при размещении каждого из трёх типов ордеров (MARKET, StopMarket, Limit)
- [[coordinator-orchestration]] — координатор: как `_step_floor()` применяется при аварийном закрытии позиции и работе с «пылью» (dust — остаток ниже min_order_qty)
- [[bybit-rest-client-and-backoff]] — REST-клиент: `get_filters()` и `_safe_extract_list()` — как именно загружаются фильтры с биржи
- [[bybit-rest-source]] — источник данных по REST: тот же слой `rest.py` и защита от «сдвига схемы» ответа Bybit, через который приходят и свечи, и фильтры
- [[data-pipeline]] — общий поток данных: как фильтры вписаны в цепочку инициализации бота
- [[startup-and-wiring]] — сборка бота при старте: где сейчас задаются фильтры-заглушки (`__main__.py`) и почему динамическая загрузка через `get_filters()` пока отложена
- [[order-lifecycle-overview]] — жизненный цикл ордера: `validate_order()` как обязательная проверка на пути сигнал → ордер → биржа
- [[oco-bracket-emulation]] — OCO-эмуляция: почему для лимитного TP ордера проверяется `qty*price ≥ min_order_amt`, а для стоп-рыночного SL — нет
- [[emergency-flatten-and-residual]] — аварийное закрытие и остаток-«пыль»: как `min_order_qty` определяет неторгуемый residual, а `_step_floor()` округляет закрывающее количество

За техническими деталями: `llm-wiki/wiki/project/components/marketdata.md`
