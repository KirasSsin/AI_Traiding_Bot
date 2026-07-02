---
title: "ATR: измеритель волатильности рынка"
section: "03-индикаторы-и-расчёты"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/signalgen/indicators.py, src/backtest/indicators.py, src/signalgen/atr_breakout_strategy.py, src/signalgen/supertrend_strategy.py, src/signalgen/donchian_strategy.py, src/signalgen/volume_breakout_strategy.py
---

# ATR: измеритель волатильности рынка

**TL;DR:** ATR (Average True Range, средний истинный диапазон) — это число, которое показывает, насколько сильно цена «скачет» за одну свечу в среднем. Бот использует его как линейку для стоп-лоссов: чем рынок неспокойнее, тем дальше ставим страховочный уровень.

---

## Простыми словами

Представьте, что вы следите за ценой Биткоина в течение дня. Иногда она ходит плавно — скажем, в диапазоне 500 долларов за свечу. Иногда рынок «штормит» и цена за ту же свечу пролетает 2000 долларов. ATR усредняет эти «размахи» за последние N свечей и даёт одно число: «сейчас рынок в среднем ходит на X единиц за свечу».

Зачем это боту? Представьте, что вы ставите страховку (стоп-лосс — это и есть страховка: заранее решаем, при какой цене выходим, чтобы не потерять больше задуманного). Если рынок сейчас спокойный и ATR маленький — страховку можно поставить ближе. Если рынок штормит и ATR большой — страховка должна быть дальше, иначе нормальный «шум» цены выбьет нас раньше времени. ATR автоматически подстраивает стоп-лосс под текущую волатильность.

Важный нюанс: ATR учитывает **ценовые гэпы** (разрыв — когда цена открывается утром совсем не там, где закрылась вечером). Обычный диапазон «максимум минус минимум» гэп игнорирует. ATR — нет.

---

## Как это работает у нас

В проекте существуют **три семейства ATR** и в общей сложности семь конкретных реализаций (code-paths), которые намеренно не объединены в одну. Причина — каждая стратегия прошла проверку именно с тем вариантом, с которым запускалась в исследованиях, и менять его без повторной проверки запрещено.

| Семейство | Реализации | Где живут |
|---|---|---|
| **talib** | `atr()` через TA-Lib | `signalgen/indicators.py` |
| **Wilder RMA (ручная)** | `wilder_atr()` (пакет, Decimal); `_WilderATR` (инкрементальный класс); `_update_atr()` (метод); `backtest/indicators._wilder_atr()` (DRY-версия); `supertrend_runner._wilder_atr_vectorized()` (локальная) | разные модули |
| **EWM (pandas)** | `calculate_indicators()` → `true_range.ewm(alpha=1/period)` | `backtest/indicators.py`, используется через `replay_engine.py` |

Подробности — в шагах ниже.

### Шаг 1. Что такое True Range (истинный диапазон одной свечи)

Прежде чем усреднять, нужно посчитать диапазон каждой свечи. Просто взять `максимум − минимум` недостаточно, потому что это не учитывает гэп.

**True Range** = наибольшее из трёх чисел:

| Кандидат | Что он измеряет |
|---|---|
| `high − low` | Обычный размах свечи |
| `|high − предыдущее_закрытие|` | Гэп вверх: открылись выше вчерашнего закрытия |
| `|low − предыдущее_закрытие|` | Гэп вниз: открылись ниже вчерашнего закрытия |

Берём максимальное из трёх — это и есть истинный диапазон свечи.

Особый случай для **первой свечи**: у неё нет предыдущего закрытия, поэтому по конвенции проекта полагаем `prev_close[0] = close[0]`. Тогда два последних кандидата превращаются в 0, и TR первой свечи = `high − low`. (src/signalgen/indicators.py:110–117, src/signalgen/atr_breakout_strategy.py:161)

### Шаг 2. Вариант 1 — `atr()` через TA-Lib

```python
# src/signalgen/indicators.py:67–81
def atr(high, low, close, period=14):
    return talib.ATR(high, low, close, timeperiod=period)
```

Это готовая функция из библиотеки TA-Lib. Она тоже применяет сглаживание Уайлдера (см. ниже), но затравочное значение (seed) считается внутри TA-Lib по собственной формуле. Именно поэтому результат немного отличается от ручного варианта — на ~1.4% (src/signalgen/indicators.py:97).

**Кто использует:** стратегия [[donchian-breakout-strategy|Donchian]] (`donchian_strategy.py:29: from src.signalgen.indicators import atr`) и [[02-стратегии/volume-breakout-strategy|Volume Breakout]] (`volume_breakout_strategy.py:46: from src.signalgen.indicators import atr`). Volume Breakout зафиксирован на этом варианте по ADR 0059 (anti-snooping LOCKED) — менять нельзя без нового ADR.

### Шаг 3. Вариант 2 — `wilder_atr()` ручная рекурсия (пакетный режим)

```python
# src/signalgen/indicators.py:84–124
def wilder_atr(high, low, close, period):
    prev_close = concatenate([[close[0]], close[:-1]])
    tr = max(high-low, |high-prev_close|, |low-prev_close|)  # для всего массива
    atr_out[period - 1] = mean(tr[:period])          # seed = среднее первых period TR
    for i in range(period, n):
        atr_out[i] = (atr_out[i-1] * (period-1) + tr[i]) / period  # рекурсия
    return atr_out
```

Это ручная реализация алгоритма Уайлдера:

1. Считаем TR для всего массива свечей сразу (векторно).
2. Первые `period` значений накапливаем — ATR ещё не готов, это «прогрев» (NaN).
3. На баре с номером `period - 1` (нумерация с 0) вычисляем **seed** — простое среднее первых `period` значений TR.
4. Далее каждый следующий ATR = `(предыдущий_ATR × (period - 1) + новый_TR) / period`. Это сглаживание Уайлдера (RMA — Running Moving Average, рекурсивная скользящая). Новый бар вносит вклад `1/period`, история весит `(period-1)/period`.

**Кто использует:** только live-код и исследовательские скрипты. Сам по себе `wilder_atr()` из `signalgen/indicators.py` в бэктест-раннерах **не вызывается** — раннеры используют собственные копии с тем же алгоритмом (см. ниже). Это подтверждено отсутствием импортов функции в `src/backtest/`.

Алгоритмически идентичные варианты той же формулы живут в двух других местах:
- `backtest/indicators.py:_wilder_atr()` (строки 17–51) — общая DRY-копия, извлечённая в S55. Её импортируют раннеры ATR Breakout и Volume Breakout через алиас `_atr` (`src/backtest/atr_breakout_runner.py:35`, `src/backtest/volume_breakout_runner.py:38`) — это отдельная модель бэктеста, [[research-kernel-execution-model|research-ядро]].
- `backtest/supertrend_runner.py:_wilder_atr_vectorized()` (строки 73–96) — **локальная** копия того же алгоритма внутри раннера Supertrend; ничего из `backtest/indicators` не импортирует.

### Шаг 4. Вариант 3 — `_WilderATR` класс (инкрементальный, для live-режима)

Векторные функции выше получают весь массив свечей и пересчитывают всё с нуля. В live-режиме свечи приходят по одной, и пересчитывать всю историю каждый раз расточительно. Для этого создан класс:

```python
# src/signalgen/atr_breakout_strategy.py:135–180
class _WilderATR:
    def update(self, high, low, close):
        # вычисляем TR одной свечи
        # накапливаем seed-буфер до period баров
        # после seed: ATR = (prev_ATR * (period-1) + TR) / period
        self.current = new_atr
        self.previous = old_current  # ATR предыдущего бара
```

Класс хранит только два числа: `current` (ATR через последний поданный бар) и `previous` (ATR через предпоследний). Никакого пересчёта истории — один шаг рекурсии за O(1).

Аналогичная инкрементальная логика встроена прямо в метод `_update_atr()` класса `SupertrendStrategy` (src/signalgen/supertrend_strategy.py:208–242).

**Кто использует:** `ATRBreakoutStrategy` (живой бот, src/signalgen/atr_breakout_strategy.py:212–216) и `SupertrendStrategy` (живой бот, src/signalgen/supertrend_strategy.py:150).

### Шаг 4b. Вариант 4 — EWM-ATR в `calculate_indicators` (для replay_engine)

Этот вариант существует отдельно от всех вышеперечисленных и обслуживает только стратегии, которые прогоняются через универсальный [[replay-engine-bar-by-bar|replay_engine]] ([[02-стратегии/ema-crossover-strategy|EMA-crossover]], [[02-стратегии/mean-reversion-strategy|mean_reversion]], donchian в режиме dashboard, volume_breakout в dashboard-режиме).

Вместо формулы Уайлдера здесь используется **pandas EWM** (exponentially weighted moving average) с `alpha = 1/period`:

```python
# src/backtest/indicators.py:103–109
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1 / atr_period, adjust=False).mean()
atr.iloc[:atr_period] = np.nan   # маска первых period баров
out["atr"] = atr
```

Результат записывается в колонку `out["atr"]` датафрейма. `replay_engine.py` затем читает это значение при открытии позиции (строка 240: `atr = float(row["atr"])`) и использует его для вычисления уровней SL и TP в момент входа — то есть стоп фиксируется на момент входа и не плавает дальше (src/backtest/replay_engine.py:243–244).

Математически EWM с `alpha=1/period` и Wilder RMA — одна и та же рекурсия, когда оба применяются к уже готовым значениям TR. Разница возникает из способа инициализации: EWM pandas начинает с первого значения TR (нет явного seed-бара), Wilder вычисляет seed как простое среднее первых `period` значений. Поэтому результаты немного расходятся в начале ряда, но сходятся на длинных историях.

**Кто использует:** `replay_engine.py` через `calculate_indicators()` (src/backtest/indicators.py:107, src/backtest/replay_engine.py:141).

### Шаг 5. Как ATR превращается в стоп-лосс

Стоп-лосс на основе ATR работает по одной формуле, но **конкретное значение ATR, которое в неё подставляется, разное в live и в бэктесте** — это важный нюанс:

```
стоп_цена = цена_входа − atr_stop_mult × ATR
```

**В live-боте (`ATRBreakoutStrategy`):** ATR пересчитывается на каждом новом баре и подставляется «свежий» (`atr_stop_curr` — ATR через текущий бар T). Это означает, что **уровень стопа плавает** от бара к бару вместе с волатильностью. Если рынок успокоился — стоп подтягивается ближе; если штормит — уходит дальше (src/signalgen/atr_breakout_strategy.py:297–307).

**В бэктест-раннере (`atr_breakout_runner.py`):** ATR фиксируется в момент входа (`entry_atr = atr_stop[i-1]`) и больше не меняется всё время удержания позиции. Стоп-уровень вычисляется один раз: `stop_price = entry_price - entry_atr * atr_stop_mult` (src/backtest/atr_breakout_runner.py:201–209). То есть в бэктесте стоп **зафиксирован при входе**.

Из-за этой разницы пример ниже демонстрирует **бэктест-семантику** (стоп не меняется после входа). В live-боте та же позиция имела бы плавающий стоп, который мог немного сдвинуться к следующей свече.

Если цена падает до стоп_цены — бот выходит из позиции (фиксирует убыток).

Каждая стратегия имеет свой зафиксированный множитель:

| Стратегия | Период ATR для стопа | Множитель (`atr_stop_mult`) | Источник |
|---|---|---|---|
| ATR Breakout (BTCUSDT 240) | 21 | 1.5 | src/signalgen/atr_breakout_strategy.py:60–61 |
| ATR Breakout (BTCUSDT 60) | 21 | 3.0 | src/signalgen/atr_breakout_strategy.py:79–80 |
| ATR Breakout (BTCUSDT 15) | 14 | 3.0 | src/signalgen/atr_breakout_strategy.py:85–86 |
| ATR Breakout (BTCUSDT D) | 9 | 3.0 | src/signalgen/atr_breakout_strategy.py:91–92 |
| Donchian | 14 | 2.0 | src/signalgen/donchian_strategy.py:36–37 |
| Volume Breakout | 9 | 2.9663 | src/signalgen/volume_breakout_strategy.py:57–58 |

[[02-стратегии/supertrend-strategy|Supertrend]] использует ATR **двумя путями одновременно**:
1. **Смена тренда** (BULL → BEAR): стратегия эмитирует сигнал `EXIT_FLAT_SUPERTREND_FLIP` — выход по флипу полос (src/signalgen/supertrend_strategy.py:27–30).
2. **ATR bracket SL** (страховочный стоп): значение ATR передаётся в поле сигнала `atr_14`, откуда его забирает FSM/риск-слой и вычисляет аварийный стоп-уровень независимо от полос как часть [[oco-bracket-emulation|брекета из 3 ордеров]] (src/signalgen/supertrend_strategy.py:32–34: `"ATR bracket stop loss (no take-profit) is enforced downstream by the FSM/risk layer using atr_14 carried in the Signal"`).

Иными словами: бот выходит из Supertrend либо по смене тренда, либо по ATR-стопу — смотря что произойдёт раньше. Ни один из путей не исключает другой.

---

## Формулы и расчёты

### True Range (TR)

```
TR[i] = max(high[i] − low[i],  |high[i] − close[i−1]|,  |low[i] − close[i−1]|)
TR[0] = high[0] − low[0]  (первая свеча, prev_close = close[0])
```

Простыми словами: берём три «линейки», меряем ими свечу, выбираем самую длинную.

Реализация в проекте (одна для всех ручных вариантов):

```python
# src/signalgen/indicators.py:110–117
prev_close = np.concatenate([[close[0]], close[:-1]])
tr = np.maximum.reduce([
    high - low,
    np.abs(high - prev_close),
    np.abs(low - prev_close),
])
```

### Сглаживание Уайлдера (Wilder RMA)

```
ATR[period−1] = mean(TR[0 .. period−1])         # seed: простое среднее первых period TR
ATR[i]        = (ATR[i−1] × (period−1) + TR[i]) / period    # для i ≥ period
```

Простыми словами: каждый новый ATR — это «почти прежний ATR» плюс небольшое влияние нового бара. При period=9 вес нового бара = 1/9 ≈ 11%, история = 8/9 ≈ 89%. Это медленнее реагирует на резкие скачки, чем обычная скользящая средняя — специально, чтобы не «дёргаться» от единичных всплесков.

Реализация (ручной вариант): src/signalgen/indicators.py:121–123.

### Прогревочный период (warmup)

Первые `period − 1` баров ATR не определён (NaN). На баре с индексом `period − 1` вычисляется seed. Первый полностью «живой» ATR появляется на баре `period` (следующем за seed).

Для стратегий с двумя ATR (ATR Breakout: signal period + stop period) прогрев ещё длиннее:

```
warmup = max(atr_period, atr_stop_period) + 3
# пример: max(9, 21) + 3 = 24 бара
```

(src/signalgen/atr_breakout_strategy.py:205–206)

---

## Примеры / сценарии

### Пример 1. Вычисление TR для трёх свечей BTCUSDT

| Бар | High | Low | Close | prev_close | TR |
|---|---|---|---|---|---|
| 0 | 60 100 | 59 800 | 59 900 | 59 900 (=close[0]) | 300 |
| 1 | 60 400 | 59 850 | 60 200 | 59 900 | max(550, 500, 50) = **550** |
| 2 | 60 050 | 59 500 | 59 700 | 60 200 | max(550, 0, 700) = **700** |

На баре 1 гэп вверх на 500 (60 400 − 59 900) + размах 550 — берём 550. На баре 2 гэп вниз на 700 (|59 500 − 60 200|) перекрывает размах 550 — берём 700.

### Пример 2. Seed и первые шаги RMA при period=9

- Бары 0–8: накапливаем TR, ATR = NaN.
- Бар 8 (seed): ATR = mean(TR[0..8]).
  Допустим, среднее = **400**.
- Бар 9: TR = 350. ATR = (400 × 8 + 350) / 9 = (3200 + 350) / 9 ≈ **394**.
- Бар 10: TR = 500. ATR = (394 × 8 + 500) / 9 = (3152 + 500) / 9 ≈ **406**.

ATR плавно реагирует на рост волатильности (TR=500), но не прыгает резко.

### Пример 3. Стоп-лосс по ATR — бэктест-семантика (фиксированный стоп)

_(Этот пример показывает поведение бэктест-раннера, где стоп фиксируется в момент входа и не меняется. В live-боте стоп-уровень пересчитывается каждый бар — см. Шаг 5 выше.)_

Входим в позицию при закрытии свечи на 65 000 USDT. ATR стоп-периода (21) в момент входа = 800 USDT. Множитель atr_stop_mult = 1.5.

```
стоп_цена = 65 000 − 1.5 × 800 = 65 000 − 1 200 = 63 800 USDT
```

В **бэктесте** этот уровень остаётся 63 800 USDT на всё время удержания позиции (`entry_atr` зафиксирован при входе, src/backtest/atr_breakout_runner.py:201–209). Если хотя бы одна свеча даст `low ≤ 63 800` — раннер фиксирует выход по стопу.

В **live-боте** уровень пересчитывается каждый бар с актуальным ATR. Условие проверяется как `bar.low <= entry_close - atr_stop_mult * atr_stop_curr`, где `atr_stop_curr` — ATR текущего бара T (src/signalgen/atr_breakout_strategy.py:304–307).

---

## Подводные камни / что важно понимать

### Два варианта ATR дают разный результат — это нормально

`atr()` (TA-Lib) и `wilder_atr()` (ручная) отличаются примерно на **~1.4%** из-за разного способа вычисления seed-значения (src/signalgen/indicators.py:97). Это небольшое, но стабильное расхождение. Оно намеренно сохранено: каждая стратегия прошла исследование и проверку именно с тем вариантом, который зафиксирован в её коде. Смешивать нельзя.

Краткая таблица принадлежности (сверена по импортам в `src/`):

| Функция / класс | Модуль | Используется в |
|---|---|---|
| `atr()` (talib) | `signalgen/indicators.py` | `DonchianBreakoutStrategy` (live), `VolumeBreakoutStrategy` (live) |
| `wilder_atr()` (ручная, пакет) | `signalgen/indicators.py` | Только live-скрипты и исследовательский код. **Не используется** ни одним бэктест-раннером (нет импортов в `src/backtest/`) |
| `_WilderATR` (инкрементальный класс) | `signalgen/atr_breakout_strategy.py` | `ATRBreakoutStrategy` (live) |
| `_update_atr()` (метод) | `signalgen/supertrend_strategy.py` | `SupertrendStrategy` (live) |
| `backtest/indicators._wilder_atr()` (DRY-копия, S55) | `backtest/indicators.py` | Бэктест-раннеры ATR Breakout и Volume Breakout через алиас `_atr` (`atr_breakout_runner.py:35`, `volume_breakout_runner.py:38`) |
| `_wilder_atr_vectorized()` (локальная) | `backtest/supertrend_runner.py` | Только Supertrend-раннер (`supertrend_runner.py:199`) — не импортирует ничего из `backtest/indicators` |
| EWM-ATR в `calculate_indicators()` | `backtest/indicators.py` | `replay_engine.py` (dashboard-стратегии: ema_crossover, mean_reversion, donchian, volume_breakout в режиме replay) |

### Дефект D4 (S51): сдвигающееся окно пересевало RMA

Это историческая ошибка, которая была исправлена, но её важно понимать. До исправления `ATRBreakoutStrategy` хранила ATR в скользящем буфере фиксированной длины. Когда буфер переполнялся, RMA-рекурсия начиналась заново с нового seed — и ATR в live-режиме расходился с ATR в бэктесте до **~39%** (src/signalgen/atr_breakout_strategy.py:31). WFA-валидация проводилась на полной истории, а в live системе цифры были другими — сигналы оказывались несравнимы.

Исправление: теперь оба `_WilderATR` объекта ведут рекурсию над **полной историей** с момента старта стратегии (O(1) на каждый бар, без пересева). Тесты: `tests/unit/test_atr_breakout_parity.py`. Как каноническая формула Wilder ATR превращается в стоп-уровни именно в бэктест-раннерах — см. [[wilder-atr-and-stops]].

### Параметры LOCKED — менять запрещено без нового ADR

Все `atr_period` и `atr_stop_mult` зафиксированы через механизм anti-snooping: параметры были зарегистрированы до финальной проверки, чтобы исключить подгонку под данные. Именно от подгонки под многократные попытки защищает [[deflated-sharpe-ratio|Deflated Sharpe Ratio]]. Изменение любого числа делает результаты [[walk-forward-analysis|WFA]] недействительными. Подробнее: [[02-стратегии/atr-breakout-strategy]].

### Прогрев нужен всегда — и он длиннее, чем кажется

При `atr_period = 9` первые 8 баров ATR равен NaN. Seed появляется на 9-м баре (индекс 8), но это ещё не «боевой» ATR — это просто среднее. Первый рекурсивный ATR только на 10-м баре (индекс 9). Для стратегий с двумя ATR-периодами (signal + stop) прогрев = max + 3. Стратегия молчит всё это время — это нормальное поведение, не ошибка.

### ATR не предсказывает направление — только «шум»

ATR говорит лишь о величине колебаний, но не о том, куда пойдёт цена. Рост ATR = рынок стал более «нервным». Спад ATR = рынок успокоился. Бот использует это только для масштабирования стоп-уровней.

---

## Связанные документы

**Стратегии, которые используют ATR (для входа и/или для стопа):**

- [[02-стратегии/atr-breakout-strategy]] — стратегия, которая использует ATR и для входа (пробой зоны), и для стопа; здесь подробно объяснены LOCKED-параметры и дефект D4
- [[02-стратегии/supertrend-strategy]] — стратегия, где ATR формирует динамические «шины» тренда (полосы Supertrend) и одновременно даёт страховочный ATR-стоп
- [[02-стратегии/donchian-breakout-strategy]] — Donchian стратегия: использует `atr()` (talib) для стопа, `atr_stop_mult=2.0`
- [[02-стратегии/volume-breakout-strategy]] — Volume Breakout: talib-ATR зафиксирован по ADR 0059
- [[02-стратегии/kronos-ml-strategy]] — ещё одна пробойная/ML-стратегия, чей бэктест идёт через то же research-ядро, что и ATR-раннеры

**Индикаторы-соседи (тот же справочный раздел, часто считаются вместе):**

- [[03-индикаторы-и-расчёты/supertrend-indicator]] — как ATR превращается в полосы Lazybear Supertrend (ATR — его прямой строительный блок)
- [[technical-indicators]] — сводная справка по всем индикаторам (EMA, RSI, ATR, ADX, Bollinger): где ATR стоит в общем ряду
- [[ema-rsi-indicators]] — EMA и RSI: другие индикаторы, из которых собираются сигналы стратегий
- [[bollinger-bands-indicator]] — полосы Боллинджера: тоже канал волатильности, но на основе стандартного отклонения, а не True Range (контраст с ATR)
- [[donchian-channel-indicator]] — канал Дончиана: пробой исторического экстремума, к которому ATR-раннеры добавляют стоп
- [[adx-indicator]] — ADX: сила тренда; строится на сглаживании Уайлдера — той же рекурсии RMA, что и Wilder ATR

**Бэктест и валидация (где ATR-стопы работают и как проверяются параметры):**

- [[06-бэктест-и-валидация/wilder-atr-and-stops]] — детали стопов на основе ATR в бэктест-раннерах (каноническая формула Wilder ATR + стоп-уровни)
- [[research-kernel-execution-model]] — research-ядро `_backtest_single`: отдельная модель бэктеста, в которой ATR-раннеры фиксируют стоп при входе
- [[replay-engine-bar-by-bar]] — универсальный движок replay: читает EWM-ATR из `calculate_indicators` и вычисляет SL/TP в момент входа
- [[indicators-and-signals]] — обзор индикаторов и сигналов на стороне бэктеста (EMA, RSI, ATR, Bollinger, Donchian, объём)
- [[walk-forward-analysis]] — WFA: почему изменение LOCKED-параметров ATR делает результаты проверки недействительными
- [[deflated-sharpe-ratio]] — DSR: защита от подгонки под множественные попытки, ради которой параметры ATR зафиксированы (anti-snooping)
- [[acceptance-gates-t1-t6]] — ворота приёмки T1–T6: пороги, которые обязана пройти стратегия с ATR-стопом

**Исполнение (куда ATR-стоп уходит в реальной торговле):**

- [[oco-bracket-emulation]] — брекет из 3 ордеров: ATR-стоп Supertrend/пробоев превращается в реальный стоп-лосс-ордер
- [[risk-overview-decision-pipeline]] — риск-менеджер: слой, который применяет ATR-стоп при пропуске сделки в исполнение

За техническими деталями реализации: [`llm-wiki/wiki/project/components/`](../../llm-wiki/wiki/project/components/) (компоненты signalgen, backtest indicators).
