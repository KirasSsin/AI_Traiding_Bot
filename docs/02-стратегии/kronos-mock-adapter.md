---
title: "MockKronosAdapter: как тесты работают без нейросети"
section: "02-стратегии"
status: filled
updated: 2026-06-26
money_core: false
source_files: src/ml/kronos_adapter.py
---

# MockKronosAdapter: как тесты работают без нейросети

**TL;DR:** Когда бот запускает автотесты, он не загружает настоящую нейросеть Kronos (это 400 МБ весов). Вместо неё используется заглушка — `MockKronosAdapter`: маленький класс, который выдаёт придуманный, но предсказуемый прогноз. Так тесты работают быстро и одинаково на любом компьютере.

## Простыми словами

Представьте, что вы тренируете авиадиспетчеров на тренажёре. Настоящий самолёт туда не загонишь — слишком дорого и сложно. Поэтому делают симулятор: поведение похоже на настоящее, зато всегда одинаковое и управляемое.

`MockKronosAdapter` — это именно такой симулятор для нашей нейросети Kronos (о том, что такое сама стратегия Kronos, читайте в [[kronos-what-is-it]]).

Зачем это нужно:

- **Нейросеть Kronos весит ~400 МБ** и требует особого режима работы с Apple Silicon (Metal Performance Shaders, MPS). Загрузить её в автотест — слишком долго и невозможно на сервере CI (системе автоматических проверок, которая запускает тесты при каждом изменении кода).
- **Заглушка работает без нейросети вообще** — никакого PyTorch, никаких весов. Берёт последнюю известную цену и прибавляет фиксированный процент за каждый будущий шаг.
- **Результат всегда одинаков**: один и тот же входной набор свечей → один и тот же список прогнозных цен. Это называется **детерминизм** (воспроизводимость результата) — важнейшее свойство для тестов, потому что нестабильный тест бесполезен.

Важно: заглушка не претендует быть точной. Её задача — убедиться, что весь остальной код ([[kronos-signal-rule|стратегия]], [[kronos-backtest-runner|бэктест]], [[kronos-offline-predict-cache|кэш]]) правильно принимает и обрабатывает список прогнозных цен.

## Как это работает у нас

### Общая структура модуля

В файле `src/ml/kronos_adapter.py` живут три сущности (src/ml/kronos_adapter.py:1–189):

| Сущность | Что делает |
|---|---|
| `KronosAdapter` (Protocol) | Описывает контракт — какие методы должен иметь любой адаптер |
| `KronosModelAdapter` | Настоящий адаптер — загружает модель Kronos, требует torch |
| `MockKronosAdapter` | Заглушка — без torch, детерминированная |

### Шаг 1. Контракт — KronosAdapter Protocol

**Protocol** — это способ сказать Python: «мне не важно, какой именно объект ты передал, главное, чтобы у него был метод `predict` с правильными аргументами». Если у класса есть такой метод — он автоматически считается реализующим Protocol.

```python
@runtime_checkable
class KronosAdapter(Protocol):
    def predict(self, ohlcv_df: pd.DataFrame, lookback: int, horizon: int) -> list[Decimal]:
        ...
```
(src/ml/kronos_adapter.py:26–47)

- `ohlcv_df` — таблица исторических свечей (OHLCV: Open, High, Low, Close, Volume — открытие, максимум, минимум, закрытие, объём).
- `lookback` — сколько последних свечей передать модели в качестве контекста.
- `horizon` — сколько будущих баров (свечей) нужно спрогнозировать.
- Возвращает: список предсказанных цен закрытия — строго `list[Decimal]` (не float, не tensor).

Декоратор `@runtime_checkable` означает, что можно проверить принадлежность объекта Protocol прямо во время работы программы через `isinstance(adapter, KronosAdapter)`. Тест `test_mock_satisfies_protocol` явно делает эту проверку (tests/unit/test_kronos_adapter.py:68–70).

### Шаг 2. Заглушка — MockKronosAdapter

```python
class MockKronosAdapter:
    _DRIFT_PER_STEP: Decimal = Decimal("1.001")

    def predict(self, ohlcv_df, lookback, horizon):
        last_close = Decimal(str(ohlcv_df["close"].iloc[-1]))
        forecast: list[Decimal] = []
        price = last_close
        for _ in range(horizon):
            price = price * self._DRIFT_PER_STEP
            forecast.append(price)
        return forecast
```
(src/ml/kronos_adapter.py:166–189)

Алгоритм буквально в четырёх строках:

1. Берём последнюю цену закрытия из таблицы свечей (`ohlcv_df["close"].iloc[-1]`).
2. Конвертируем в `Decimal` через `str()` — это важный трюк, объяснённый ниже.
3. В цикле `horizon` раз умножаем текущую цену на `_DRIFT_PER_STEP = Decimal("1.001")`.
4. Каждый результат добавляем в список и возвращаем.

Параметр `lookback` принимается, но не используется — это намеренно: заглушка должна совпадать с сигнатурой Protocol. В коде это помечено явным комментарием `# noqa: ARG002 — part of the KronosAdapter contract` (src/ml/kronos_adapter.py:179).

### Шаг 3. C1-изоляция — torch нигде снаружи src/ml/

Ключевое архитектурное решение: `import torch` разрешён **только внутри** `KronosModelAdapter`. Шесть других стратегий бота работают вообще без знания о существовании torch.

Проверка командой grep по всему `src/` (за исключением самого `kronos_adapter.py`) даёт ноль результатов — torch нигде не просачивается. Это и есть **C1-изоляция** (ограничение тяжёлой зависимости одним файлом) (src/ml/kronos_adapter.py:8–11).

Если torch отсутствует и кто-то пытается создать `KronosModelAdapter` (настоящий адаптер, который грузит модель и [[kronos-security-weights-hash|проверяет подлинность её весов]]), поднимается чистая ошибка с инструкцией из двух шагов: инициализировать git-субмодуль и установить `pip install -e '.[ml]'` (src/ml/kronos_adapter.py:108–116). Тест `test_model_adapter_raises_clean_importerror_without_torch` фиксирует это поведение (tests/unit/test_kronos_adapter.py:96–104).

### Шаг 4. C6-граница — только Decimal на выходе

Любой результат, покидающий `src/ml/`, обязан быть `Decimal`, а не float, numpy-числом или tensor. Это **C6-контракт** (src/ml/kronos_adapter.py:6–7). Тот же принцип «только точный тип на границе» действует и дальше по цепочке: [[signal-architecture|объект `Signal`]] тоже несёт денежные поля строго в `Decimal`.

Почему это важно: float в Python имеет ограниченную точность и может накапливать ошибки при денежных расчётах. `Decimal` — точный тип для работы с деньгами без потерь при умножении.

Конвертация через строку (`Decimal(str(value))`) вместо прямого `Decimal(float_value)` — намеренная защита. Прямой `Decimal(0.1)` выдаст `Decimal('0.1000000000000000055511151231257827021181583404541015625')` из-за неточности float. Конвертация через `str` даёт `Decimal('0.1')` — то, что ожидает трейдерская логика.

## Формулы и расчёты

**Расчёт прогнозной цены за шаг:**

```text
price[i] = price[i-1] × 1.001
```

где `price[0] = last_close` (последняя цена закрытия из таблицы свечей).

Иными словами: каждый следующий прогнозный бар — это предыдущий, увеличенный на 0.1%.

Константа `_DRIFT_PER_STEP = Decimal("1.001")` задаётся явно (src/ml/kronos_adapter.py:174). Она никогда не меняется — это и обеспечивает детерминизм.

**Пример для horizon=3:**

Пусть последняя известная цена = 100.00 USDT.

| Шаг | Вычисление | Результат |
|---|---|---|
| 1 | 100.00 × 1.001 | 100.1000 |
| 2 | 100.1000 × 1.001 | 100.2001 |
| 3 | 100.2001 × 1.001 | 100.3003001 |

Реальная нейросеть Kronos возвращала бы свой прогноз, построенный на паттернах из тысяч исторических данных. Заглушка возвращает простое геометрическое прогрессирование — но этого достаточно, чтобы проверить, что весь остальной код (стратегия, кэш, бэктест) корректно обрабатывает список `list[Decimal]` нужной длины.

## Примеры / сценарии

### Сценарий 1: тест проверяет, что вывод всегда Decimal

```python
def test_mock_returns_list_of_decimal_length_horizon() -> None:
    df = _make_ohlcv_df()              # синтетическая таблица свечей
    adapter = MockKronosAdapter()
    out = adapter.predict(df, lookback=32, horizon=3)

    assert isinstance(out, list)
    assert len(out) == 3
    for value in out:
        assert isinstance(value, Decimal)
        assert not isinstance(value, float)
```
(tests/unit/test_kronos_adapter.py:40–49)

Тест проверяет три вещи: результат — список, длина совпадает с `horizon`, каждый элемент — Decimal (и явно не float).

### Сценарий 2: тест проверяет детерминизм

```python
def test_mock_is_deterministic() -> None:
    df = _make_ohlcv_df()
    adapter = MockKronosAdapter()
    first = adapter.predict(df, lookback=32, horizon=5)
    second = adapter.predict(df, lookback=32, horizon=5)
    assert first == second
```
(tests/unit/test_kronos_adapter.py:60–65)

Один и тот же DataFrame, один и тот же `horizon` → два вызова дают абсолютно одинаковый список. Это гарантирует, что тест не «мигает» (не даёт разные результаты без причины).

### Сценарий 3: тест проверяет соответствие контракту Protocol

```python
def test_mock_satisfies_protocol() -> None:
    adapter = MockKronosAdapter()
    assert isinstance(adapter, KronosAdapter)
```
(tests/unit/test_kronos_adapter.py:68–70)

`isinstance` работает, потому что `KronosAdapter` объявлен с `@runtime_checkable`. Если в будущем сигнатура `predict` изменится, этот тест упадёт — заглушку придётся синхронизировать.

### Сценарий 4: интеграционный тест кэша

В `tests/integration/test_kronos_ml.py` заглушка используется для предзаполнения кэша (offline-словаря прогнозов), чтобы тест не требовал реальной нейросети (tests/integration/test_kronos_ml.py:103–158). Подробнее об offline-кэше — в [[kronos-offline-predict-cache]].

## Подводные камни / что важно понимать

**1. Заглушка не тестирует точность прогнозов**
Она проверяет только архитектурный контракт: правильный тип, правильная длина, правильная изоляция зависимостей. Точность прогноза реальной модели — предмет отдельного тестирования, описанного в [[kronos-backtest-runner]].

**2. `_DRIFT_PER_STEP` нельзя менять между тестами**
Это константа класса, а не параметр конструктора. Если в тесте нужен другой drift — нужно создавать подкласс. Как есть сейчас, это намеренное решение: константа обеспечивает, что никто случайно не сделает заглушку нестабильной.

**3. Lookback игнорируется, но должен передаваться**
`predict(df, lookback=32, horizon=5)` — аргумент `lookback` молча проигнорируется заглушкой (src/ml/kronos_adapter.py:179). Но его обязательно нужно передавать, иначе код, который вызывает адаптер через абстракцию Protocol, сломается.

**4. Конвертация через str — не случайность**
`Decimal(str(ohlcv_df["close"].iloc[-1]))` — строго через строку (src/ml/kronos_adapter.py:183). Обойти это и написать `Decimal(float_value)` напрямую — тихая ошибка: Decimal унаследует неточность float и денежные расчёты поплывут.

**5. C1-изоляция защищает 6 других стратегий**
Если torch сломается или будет недоступен — [[ema-crossover-strategy|EMA]], [[atr-breakout-strategy|ATR-Breakout]], [[donchian-breakout-strategy|Donchian]], [[mean-reversion-strategy|Mean Reversion]], [[supertrend-strategy|Supertrend]], [[volume-breakout-strategy|Volume Breakout]] продолжат работать. Kronos сообщит чистую ошибку. Это намеренное архитектурное решение, а не случайность.

## Связанные документы

**Кластер Kronos:**

- [[kronos-what-is-it]] — что такое стратегия Kronos и зачем вообще нейросеть в боте
- [[kronos-ml-strategy]] — торговая логика: как прогноз превращается в сигнал на покупку/продажу
- [[kronos-signal-rule]] — V3-правило: потребитель контракта `list[Decimal]`, который проверяет заглушка
- [[kronos-offline-predict-cache]] — offline-кэш прогнозов, который заглушка помогает наполнять в тестах
- [[kronos-cache-build-script]] — скрипт наполнения кэша через настоящую модель (контраст с Mock в интеграционном тесте)
- [[kronos-backtest-runner]] — как прогоняется бэктест стратегии (использует те же адаптеры через Protocol)
- [[kronos-exploratory-runner]] — разведочный прогон ML-стратегии через тот же Protocol адаптера
- [[kronos-dashboard-dispatch]] — дэшборд тоже читает кэш вместо запуска 400-МБ нейросети (та же идея, что у заглушки)
- [[kronos-security-weights-hash]] — проверка подлинности весов: живёт в том же `kronos_adapter.py`, но только у настоящего `KronosModelAdapter`
- [[kronos-data-leakage]] — почему изоляция lookback/horizon принципиальна для честного бэктеста

**Архитектура и контекст:**

- [[signal-architecture]] — тот же принцип «только `Decimal` на границе» (C6) и защита от look-ahead в объекте `Signal`
- [[strategies-overview]] — карта всех 7 стратегий; C1-изоляция torch защищает 6 из них

**Шесть стратегий, защищённых C1-изоляцией** (работают, даже если torch недоступен):

- [[ema-crossover-strategy]] — EMA-пересечение с фильтрами ADX/RSI
- [[atr-breakout-strategy]] — ATR-прорыв (волатильный пробой)
- [[donchian-breakout-strategy]] — прорыв канала Дончиана (Turtle)
- [[mean-reversion-strategy]] — возврат к среднему (RSI + Bollinger)
- [[supertrend-strategy]] — Supertrend (Lazybear)
- [[volume-breakout-strategy]] — прорыв канала с подтверждением объёма

> За техническими деталями (ADR 0068, C1/C2/C6-контракты, KronosVariant конфигурации): `llm-wiki/wiki/project/components/kronos-adapter.md` (если создан) или `llm-wiki/wiki/project/decisions/`.
