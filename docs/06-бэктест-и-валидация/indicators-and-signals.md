---
title: "Индикаторы и сигналы: как стратегия решает, когда входить"
section: "06-бэктест-и-валидация"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/backtest/indicators.py
---

# Индикаторы и сигналы: как стратегия решает, когда входить

**TL;DR:** `calculate_indicators` — единственная точка, где из исторических свечей рождается торговый [[signal-architecture|сигнал]] (`+1 / 0 / −1`). Функция вычисляет нужные индикаторы, применяет правила выбранной стратегии и передаёт готовую таблицу в [[replay-engine-bar-by-bar|движок бэктеста]]. Главное свойство — честность: ни один расчёт не «видит» данные вперёд по времени.

## Простыми словами

Представьте, что вы пытаетесь понять, когда покупать акции на основе графика цен. Вы можете смотреть на сырые числа, но глазу сложно уловить закономерность в тысячах значений. Поэтому трейдеры придумали **технические индикаторы** — математические «линзы», которые превращают поток цен в понятные числа:

- одни показывают **направление тренда** (растёт или падает цена в среднем),
- другие — **перегрев рынка** (слишком быстро выросло — пора коррекции),
- третьи — **размах колебаний** (насколько нестабилен рынок прямо сейчас),
- четвёртые — **аномальный объём** (торгуют значительно больше обычного — что-то происходит).

**Индикатор** сам по себе — просто число на каждой свече. Чтобы из чисел получилось **торговое решение**, нужна **стратегия** — набор правил вида «если одновременно выполняются условие A и условие B — это сигнал на покупку». Например: «если быстрая скользящая средняя пересекла медленную снизу вверх — AND рынок ещё не перегрет — покупаем».

Именно этим и занимается функция `calculate_indicators`: берёт таблицу свечей, считает все нужные индикаторы, применяет правила стратегии и добавляет колонку `signal`:

| Значение | Смысл |
|---|---|
| `+1` | Сигнал на вход в покупку (лонг) |
| `0` | Нет сигнала, ждём |
| `−1` | Сигнал на выход из канала (шорт-кандидат) — только в `volume_breakout` |

Затем движок бэктеста (`replay_engine`) читает эту колонку бар за баром и «исполняет» сделки. Без `calculate_indicators` движок не знал бы, когда торговать.

## Как это работает у нас

### Функция `calculate_indicators` — диспетчер стратегий

`(src/backtest/indicators.py:54–198)`

Это главная функция файла. Она принимает таблицу свечей (`df`) и конфигурацию (`cfg`) и возвращает ту же таблицу, дополненную колонками индикаторов и колонкой `signal`.

```python
def calculate_indicators(df: pd.DataFrame, cfg: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
```

Первое что делает функция — определяет тип стратегии из конфига:

```python
strategy_type = str(cfg.get("strategy", {}).get("type", "ema_crossover")).lower()
```

`(src/backtest/indicators.py:74)`

Если тип не задан, по умолчанию берётся `"ema_crossover"`. После этого функция всегда вычисляет **общие индикаторы** (EMA, RSI, ATR) — независимо от стратегии — и затем направляет логику сигнала в нужную ветку (четыре типа стратегий).

---

### Общие индикаторы — вычисляются для всех стратегий

#### EMA — экспоненциальная скользящая средняя

**[[ema-rsi-indicators|Экспоненциальная скользящая средняя (EMA)]]** — это «текущая средняя температура» рынка: усреднённая цена за последние N баров, где свежие бары весят больше старых. В отличие от обычного среднего (все бары с равным весом), EMA быстрее реагирует на изменения.

Бот считает две EMA: **быструю** (меньший период, реагирует резче) и **медленную** (больший период, сглаживает шум). Пересечение быстрой над медленной — классический сигнал начала тренда.

```python
fast = int(ema_cfg.get("fast_period", 20))   # умолчание 20, в config.yaml = 12
slow = int(ema_cfg.get("slow_period", 50))   # умолчание 50, в config.yaml = 120
out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()
```

`(src/backtest/indicators.py:80–86)`

Метод `ewm(span=N, adjust=False)` применяет коэффициент сглаживания `α = 2/(N+1)` — это **классическая EMA**, не Уайлдер. Значения из [[configuration-and-settings|`config.yaml`]]: `fast_period = 12`, `slow_period = 120`. `(config.yaml:25–26)`

> **Внимание:** в `config.yaml` записаны `fast=12, slow=120`. Это настройки для `ema_crossover` стратегии. Другие стратегии (mean_reversion, donchian, volume_breakout) EMA для сигнала не используют, но столбцы `ema_fast`/`ema_slow` добавляются к таблице в любом случае.

#### RSI — индикатор относительной силы (с защитой от ложного прогрева)

**[[ema-rsi-indicators|RSI (Relative Strength Index)]]** — термометр «перегрева». Показывает, не слишком ли быстро рынок разогнался вверх или упал вниз. Шкала от 0 до 100:

- **> 70**: рынок «перекуплен» — покупали слишком много и слишком быстро, возможна коррекция вниз;
- **< 30**: рынок «перепродан» — продавали слишком активно, возможен отскок.

```python
rsi_period = int(rsi_cfg.get("period", 14))   # из config.yaml: 14
delta = out["close"].diff()
gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / rsi_period, adjust=False).mean()
loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / rsi_period, adjust=False).mean()
rs = gain / loss.replace(0, np.nan)
rsi = 100 - (100 / (1 + rs))
# Маскируем первые rsi_period баров как NaN — прогрев ещё не завершён
rsi.iloc[:rsi_period] = np.nan
out["rsi"] = rsi
```

`(src/backtest/indicators.py:82–100)`

Реализация использует сглаживание Уайлдера: `α = 1/rsi_period`, а не классическое `2/(n+1)`. Период по умолчанию из конфига — **14**.

**Важный нюанс (S27 T3 fix):** до исправления в Sprint 27 код делал `.fillna(50.0)` на первых барах — заменял NaN на «нейтральное» значение 50, как будто рынок ровный. Это создавало ложные сигналы: RSI < 68 выполнялось на нулевых барах, и стратегия могла входить до реального прогрева. Исправление — явная маска: первые `rsi_period` (= 14) баров становятся `NaN`. `NaN` никогда не удовлетворяет условию `< 68`, поэтому сигналы в период прогрева полностью подавляются. `(src/backtest/indicators.py:88–99)`

#### ATR — средний истинный диапазон (EWM-вариант)

**[[atr-indicator|ATR (Average True Range)]]** — линейка размаха рынка. Она измеряет, насколько широко «дышит» рынок в единицах цены. Если за последние 14 часов цена каждый час двигается в среднем на 500 USDT, ATR ≈ 500 USDT.

ATR нужен движку `replay_engine` для расчёта [[wilder-atr-and-stops|стоп-лосса и тейк-профита]]: `SL = entry_price − sl_mult × ATR`. Благодаря этому стопы ставятся «с учётом шума» рынка, а не жёсткой фиксированной суммой.

```python
atr_period = int(atr_cfg.get("period", 14))   # из config.yaml: 14
high_low = out["high"] - out["low"]
high_close = (out["high"] - out["close"].shift(1)).abs()
low_close  = (out["low"]  - out["close"].shift(1)).abs()
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1 / atr_period, adjust=False).mean()
atr.iloc[:atr_period] = np.nan
out["atr"] = atr
```

`(src/backtest/indicators.py:102–109)`

**True Range (истинный диапазон)** на каждом баре — максимум из трёх величин:
1. `high − low` — размах внутри бара;
2. `|high − close_предыдущего_бара|` — «прыжок» вверх от вчерашнего закрытия;
3. `|low − close_предыдущего_бара|` — «прыжок» вниз.

Это учитывает гэпы (разрывы цены между барами), которых нет в простой разнице high-low.

**Важное отличие от других ATR в проекте:** здесь используется EWM-вариант (`ewm(alpha=1/period)`), а не Wilder-вариант (SMA-seed + рекурсия). Они дают разные числа. Этот ATR используется только в `calculate_indicators` (бэктест-движок). Другие части системы (live-стратегии, `volume_breakout_runner`, `atr_breakout_runner`) используют отдельные реализации. `(src/backtest/indicators.py:24, 107)`

Так же как RSI, ATR маскирует первые `atr_period` баров через `NaN` — результат S27 T3 fix. `(src/backtest/indicators.py:108)`

---

### Ветка 1: `ema_crossover` — пересечение средних с фильтром RSI

`(src/backtest/indicators.py:181–196)`

Стратегия по умолчанию (live-версия — [[02-стратегии/ema-crossover-strategy|EMA Crossover]]). Логика: быстрая EMA пересекает медленную снизу вверх (признак начала роста) — и при этом рынок ещё не перегрет.

```python
# Пересечение: на предыдущем баре fast <= slow, на текущем fast > slow
cross_up = (out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)) & \
           (out["ema_fast"] > out["ema_slow"])
overbought = float(rsi_cfg.get("overbought", 68))   # из config.yaml: 68
signal[np.where(cross_up & (out["rsi"] < overbought))[0]] = 1
```

`(src/backtest/indicators.py:182–187)`

**Два условия одновременно (AND-логика):**
1. Быстрая EMA только что пересекла медленную снизу вверх — `.shift(1)` проверяет «вчера не пересекла», а сравнение без сдвига — «сегодня пересекла».
2. RSI < 68 — рынок не перегрет. Если RSI ≥ 68, сигнал подавляется: покупать в уже разогнанный рынок рискованно.

| Параметр | Значение в `config.yaml` | Значение по умолчанию в коде |
|---|---|---|
| `fast_period` | 12 | 20 |
| `slow_period` | 120 | 50 |
| `overbought` | 68 | 68 |

**Пересечение определяется строго:** `.shift(1)` проверяет состояние на предыдущем баре — это исключает ситуацию, когда fast > slow уже несколько баров подряд. Сигнал выдаётся только в момент первого пересечения.

---

### Ветка 2: `mean_reversion` — возврат к среднему (RSI + Bollinger Bands)

`(src/backtest/indicators.py:111–132)` | ADR 0030

**[[bollinger-bands-indicator|Bollinger Bands (полосы Боллинджера)]]** — «конверт нормальности» вокруг цены. Средняя линия — скользящее среднее за 20 баров. Верхняя и нижняя полосы — на расстоянии `k` стандартных отклонений. Цена редко выходит за полосы, поэтому падение ниже нижней полосы — аномалия.

**Идея стратегии (mean reversion — «возврат к среднему»):** если цена аномально упала (ниже нижней полосы) и рынок при этом явно «перепродан» (RSI в зоне перепроданности) — высока вероятность отскока. Входим в лонг.

```python
bb_period = int(bb_cfg.get("period", 20))   # умолчание
bb_k      = float(bb_cfg.get("k", 2.0))     # умолчание
oversold  = float(rsi_cfg.get("oversold", 30))  # умолчание; config.yaml: 32

rolling_mean = out["close"].rolling(window=bb_period, min_periods=bb_period).mean()
rolling_std  = out["close"].rolling(window=bb_period, min_periods=bb_period).std(ddof=0)
out["bb_middle"] = rolling_mean
out["bb_upper"]  = rolling_mean + bb_k * rolling_std
out["bb_lower"]  = rolling_mean - bb_k * rolling_std

long_mask = (out["rsi"] < oversold) & (out["close"] < out["bb_lower"])
signal[np.where(long_mask)[0]] = 1
```

`(src/backtest/indicators.py:113–123)`

**Два условия одновременно (AND-логика):**
1. `close < bb_lower` — цена упала ниже нижней полосы (аномальное падение);
2. `rsi < oversold` — рынок перепродан.

Заметьте `ddof=0` в расчёте стандартного отклонения. Это **генеральное** (не выборочное) стандартное отклонение — так, как изначально задал Боллинджер в 1980-х. По сравнению с `ddof=1` (выборочное) нижняя полоса получается чуть уже — примерно на 2–3% для периода 20. Это сделано намеренно: и `calculate_indicators`, и `signalgen/bollinger_bands.py` используют один и тот же `ddof=0`, чтобы бэктест и live-торговля давали согласованные сигналы.

**Параметр `oversold`:** в `config.yaml` задан `oversold: 32` (строка 31), код читает его через `rsi_cfg.get("oversold", 30)` — значение 30 является резервным умолчанием. При подключённом конфиге будет использоваться 32. Реальные «залоченные» параметры живут в live-стратегии `MeanReversionStrategy`. Подробнее — в [[mean-reversion-strategy]].

> Стратегия не выдаёт сигнал `-1` (выход из канала). Её выходы обрабатываются движком по стоп-лоссу и тейк-профиту, заданным через ATR-мультипликаторы в конфиге.

---

### Ветка 3: `donchian` — пробой канала Дончиана

`(src/backtest/indicators.py:133–151)` | ADR 0054 LOCKED

**[[donchian-channel-indicator|Канал Дончиана (Donchian channel)]]** — это «коридор рекордов»: верхняя граница — максимум цены за последние N баров. Если цена пробивает этот максимум вверх — это прорыв, признак сильного тренда.

```python
lookback_n = int(donchian_cfg.get("lookback_n", 20))
prior_high = out["high"].shift(1).rolling(window=lookback_n, min_periods=lookback_n).max()
out["donchian_high"] = prior_high

long_mask = out["close"] > prior_high
signal[np.where(long_mask.fillna(False))[0]] = 1
```

`(src/backtest/indicators.py:139–144)`

**Ключевой анти-look-ahead механизм:** `.shift(1)` перед `.rolling()`. Это означает, что окно из `lookback_n` баров **не включает текущий бар**. Иными словами, `prior_high` на баре `T` — это максимум ровно за `lookback_n` баров с `T−lookback_n` по `T−1` включительно.

Зачем? Без `.shift(1)` текущий бар мог бы одновременно быть и в окне (устанавливать рекорд) и пробивать его — это логический нонсенс и [[bar-source-live|«заглядывание вперёд» (look-ahead)]]. С `.shift(1)` сигнал строго честен: «вчера был рекорд X, сегодня цена превысила X — вот сигнал».

Параметр по умолчанию `lookback_n = 20` — канал из 20 баров. LOCKED означает, что параметры зафиксированы по результатам статистической оптимизации (ADR 0054) и не должны меняться в live-торговле без нового исследования. Подробнее — в [[donchian-breakout-strategy]] и [[donchian-runner-and-reference-run]].

---

### Ветка 4: `volume_breakout` — пробой с подтверждением объёмом

`(src/backtest/indicators.py:152–179)` | ADR 0059 LOCKED

Самая сложная ветка. Идея: пробой ценового уровня значим только если сопровождается аномальным объёмом торгов. Это фильтрует ложные пробои.

```python
lookback_n      = int(vb_cfg.get("lookback_n", 9))          # LOCKED=9
exit_lookback_n = int(vb_cfg.get("exit_lookback_n", 8))     # LOCKED=8
vol_window      = int(vb_cfg.get("vol_window", 10))         # LOCKED=10
vol_mult        = float(vb_cfg.get("vol_mult", 1.4563))     # LOCKED=1.4563
signal = compute_volume_breakout_signals(
    out, lookback_n=lookback_n, exit_lookback_n=exit_lookback_n,
    vol_window=vol_window, vol_mult=vol_mult, atr_period=atr_period,
)
```

`(src/backtest/indicators.py:157–168)`

Параметры `LOCKED` — результат автоматического перебора **4510 комбинаций** параметров в исследовательском режиме (autoresearch sweep). Победитель — конфигурация под номером **sweep#1644** (это порядковый индекс в переборе, а не количество комбинаций). Число `1.4563` — не округлённое, это дословный результат оптимизации. `(llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md:22)` Подробнее — в [[volume-breakout-strategy]].

#### Функция `compute_volume_breakout_signals`

`(src/backtest/indicators.py:201–263)`

```python
def compute_volume_breakout_signals(
    df, *, lookback_n, exit_lookback_n, vol_window, vol_mult, atr_period
) -> np.ndarray:
```

Функция возвращает массив `int8` той же длины, что таблица: `+1`, `0` или `−1`.

**Тройное окно против look-ahead:**

```python
roll_high = pd.Series(high).rolling(lookback_n, min_periods=lookback_n).max().to_numpy()
roll_low  = pd.Series(low).rolling(exit_lookback_n, min_periods=exit_lookback_n).min().to_numpy()
vol_mean  = pd.Series(volume).rolling(vol_window, min_periods=vol_window).mean().to_numpy()
```

`(src/backtest/indicators.py:245–247)`

Затем — цикл с явными индексами:

```python
warmup = max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2  # = 16 при вызове через calculate_indicators
for i in range(warmup, n):
    ref_h = roll_high[i - 2]   # ценовой максимум через ПОЗАПРОШЛЫЙ бар
    ref_l = roll_low[i - 2]    # ценовой минимум через ПОЗАПРОШЛЫЙ бар
    if close[i - 1] > ref_h and volume[i - 1] > vol_mean[i - 1] * vol_mult:
        signals[i] = 1          # вход: закрытие ПРЕДЫДУЩЕГО бара пробило максимум
    elif close[i - 1] < ref_l:
        signals[i] = -1         # выход: закрытие ПРЕДЫДУЩЕГО бара пробило минимум
```

`(src/backtest/indicators.py:250–261)`

**Почему `i-2` для цен и `i-1` для объёма и закрытия?**

Сигнал на баре `i` формируется из данных, которые были бы известны к моменту закрытия бара `i-1`:
- `close[i-1]` — цена закрытия предыдущего бара (уже известна на баре `i`);
- `roll_high[i-2]` — максимум ценового окна, рассчитанный до бара `i-1` включительно. Использование `[i-2]` гарантирует: ценовой эталон строится из баров, предшествующих предыдущему. Это точное зеркало логики из исследовательского кода (`research/strategies.py`), откуда стратегия была перенесена.
- `vol_mean[i-1]` — средний объём на баре `i-1` (включает сам `i-1`).

Итого: для каждого текущего бара `i`, принять решение можно только зная данные по бар `i-1` включительно. Никакого look-ahead.

**Сигнал `−1` (выход из канала):** если `close[i-1] < roll_low[i-2]` — цена ушла ниже нижней границы канала. Это сигнал слабости: пробой вниз. `replay_engine` по умолчанию обрабатывает его только если `long_only = False`. `(src/backtest/replay_engine.py:174)`

**Warmup при вызове через `calculate_indicators`:**
```
atr_period = atr_cfg.get("period", 14) = 14  (config.yaml не содержит volume_breakout.atr,
                                               читается общий strategy.indicators.atr.period)
warmup = max(9, 8, 14, 10) + 2 = 14 + 2 = 16 баров
```
Первые 16 баров пропускаются, сигналов нет. `(src/backtest/indicators.py:83, 250)`

> **Важно:** LOCKED-параметр `atr_period=9` (из `VOLUME_BREAKOUT_LOCKED_PARAMS`) применяется только когда стратегия запускается через `volume_breakout_runner.py` напрямую. В пути `calculate_indicators` → `compute_volume_breakout_signals` `atr_period` берётся из общего конфига (`strategy.indicators.atr.period = 14`), потому что `config.yaml` не содержит отдельной секции `volume_breakout.atr`. `(src/backtest/indicators.py:83; src/signalgen/volume_breakout_strategy.py:56)`

---

### Вспомогательная функция `_wilder_atr`

`(src/backtest/indicators.py:17–51)`

```python
def _wilder_atr(df: pd.DataFrame, period: int) -> np.ndarray:
```

Эта функция **не** вызывается из `calculate_indicators` — она вызывается в других раннерах: `volume_breakout_runner.py` и `atr_breakout_runner.py`, которые исполняют сделки через [[research-kernel-execution-model|отдельную research-модель]]. Она была извлечена в Sprint 55 (S55 PY-3) из дублированных копий в двух файлах (принцип DRY).

Алгоритм Уайлдера:
1. первые `period` значений TR усредняются обычным средним (SMA-сид);
2. каждый следующий ATR: `ATR[i] = (ATR[i-1] × (period-1) + TR[i]) / period`.

Это **другой** ATR, чем EWM-вариант в `calculate_indicators`. Их числа расходятся примерно на 1–4% в зависимости от периода и данных. Смешивать их нельзя — каждый раннер строго привязан к «своему» ATR.

## Формулы и расчёты

### EMA (экспоненциальная скользящая средняя)

```
EMA[t] = α × close[t] + (1 - α) × EMA[t-1]
α = 2 / (N + 1)    (классическая EMA, не Уайлдер)
```

Простыми словами: «сегодняшняя цена» весит долю `α`, вся прошлая история — долю `(1-α)`. При `N=12` вес сегодняшней свечи ≈ 15%, при `N=120` ≈ 1.6%. Быстрая EMA реагирует на движение за часы, медленная — за дни.

### RSI (индекс относительной силы)

```
avg_gain[t] = α × gain[t] + (1-α) × avg_gain[t-1]   α = 1/N (Уайлдер)
avg_loss[t] = α × loss[t] + (1-α) × avg_loss[t-1]
RS[t] = avg_gain[t] / avg_loss[t]
RSI[t] = 100 - (100 / (1 + RS))
```

Простыми словами: RSI сравнивает, насколько активно росли цены против того, насколько активно падали. Если RSI = 80, значит из последних N баров рост побеждал многократно — рынок «разогнан».

`(src/backtest/indicators.py:93–97)` | NaN-маска: строки 98–99.

### ATR (средний истинный диапазон, EWM-вариант)

```
TR[t] = max(high[t]-low[t], |high[t]-close[t-1]|, |low[t]-close[t-1]|)
ATR[t] = ewm_alpha(TR, α = 1/N)
```

Простыми словами: «настоящий» размах свечи учитывает не только internal диапазон high-low, но и гэпы между барами. ATR = среднее этих «настоящих» размахов.

`(src/backtest/indicators.py:103–108)`

### Bollinger Bands (полосы Боллинджера)

```
middle[t] = SMA(close, N=20)
σ[t]      = population_std(close, N=20, ddof=0)
upper[t]  = middle[t] + k × σ[t]
lower[t]  = middle[t] - k × σ[t]
```

При `N=20, k=2.0`: около 95% баров исторически попадают между полосами (при нормальном распределении). Выход за полосу — статистическая аномалия.

`(src/backtest/indicators.py:116–120)` | `ddof=0` — строка 117.

### Donchian channel (канал Дончиана)

```
prior_high[T] = max( high[T-lookback_n], ..., high[T-1] )
signal = 1  если close[T] > prior_high[T]
```

Обратите внимание: в числитель входят ровно `lookback_n` баров с индексами `T-lookback_n` по `T-1` включительно. Текущий бар `T` **исключён** через `.shift(1)`. Код `shift(1).rolling(window=lookback_n)` сдвигает ряд на одну позицию, а затем берёт окно из `lookback_n` элементов — итого `lookback_n`, не `lookback_n+1`. `(src/backtest/indicators.py:140)`

`(src/backtest/indicators.py:140–144)`

## Примеры / сценарии

### Пример 1: EMA-пересечение с фильтром RSI

Допустим, часовые свечи BTC/USDT. На баре номер 500 (уже далеко от прогрева):
- `ema_fast = 43 200`, `ema_slow = 43 150` — быстрая только что пересекла медленную снизу вверх (на баре 499: fast = 43 100 < slow = 43 120);
- `RSI = 55` — рынок не перегрет (< 68).

Результат: `signal[500] = 1`. Движок получает этот сигнал, и на следующем баре (501) планирует вход по цене открытия `open[501]`.

Если бы RSI был 70: `signal[500] = 0` — фильтр отклонил, несмотря на пересечение.

### Пример 2: Donchian — пробой с честным окном

Допустим, `lookback_n = 20`, анализируем бар `T = 100`:
- `prior_high[100]` = максимум `high` по барам `80..99` включительно (ровно 20 баров = `lookback_n`) = 44 000;
- `close[100]` = 44 200.

`44 200 > 44 000` → `signal[100] = 1`.

Почему именно `80..99`, а не `79..99`? Код `.shift(1).rolling(window=20)` на баре `T=100`: сначала сдвигает данные на 1 (high[100] уходит на позицию 101, high[99] — на 100, ..., high[80] — на 81), затем rolling берёт окно из 20 позиций заканчивающееся на текущей (100) — то есть позиции 81..100, что соответствует оригинальным барам 80..99. Бар 79 не входит.

Если бы мы не делали `.shift(1)` и включили бар `T=100` в окно: `max(high[81..100])`. Бар 100 с `high = 44 300` сам бы попал в окно и мог бы установить рекорд — тогда `close[100] = 44 200 < prior_high = 44 300` → нет сигнала, хотя по честной логике сигнал должен быть. Или наоборот — ложный сигнал. Это и есть look-ahead.

### Пример 3: Volume Breakout — двойная проверка

Бар `i = 18` (warmup = 16 при вызове через `calculate_indicators`, уже прошёл). LOCKED параметры: `lookback_n=9, vol_mult=1.4563`:
- `ref_h = roll_high[16]` (`i-2 = 16`) — максимум high за последние 9 баров, считанных до бара 16 включительно;
- `close[17]` (`i-1 = 17`) = 43 500, `ref_h` = 43 200 → пробой цены есть;
- `vol_mean[17]` = 10 000, `volume[17]` = 16 000 → 16 000 > 10 000 × 1.4563 = 14 563 → объём выше нормы.

Результат: `signals[18] = 1`. Оба условия выполнены — сигнал на вход.

Если объём был бы 12 000: `12 000 < 14 563` → сигнала нет (`signals[18] = 0`), несмотря на ценовой пробой.

### Пример 4: Warm-up — тихие первые бары

При `rsi_period = 14`:
- Бары `0..13` → `rsi.iloc[:14] = NaN`;
- На баре `14` RSI впервые даёт реальное значение;
- Условие `rsi < overbought` вернёт `False` для `NaN` (pandas не паникует, просто вернёт False при сравнении);
- Первый возможный EMA-сигнал — не раньше бара `14` по RSI. Но EMA-медленная (период 120) тоже ещё не установилась — фактически первые реальные сигналы появятся значительно позже.

## Подводные камни / что важно понимать

**Это бэктест-реализация, не live.** Функция `calculate_indicators` используется только в `replay_engine` (бэктест). Live-стратегии (`EmaCrossoverAdxRsiStrategy`, `MeanReversionStrategy` и другие) — отдельный код в `src/signalgen/`. Параметры там тоже могут отличаться: например, `overbought` в live-стратегии EMA = 70, а в `config.yaml` для бэктеста = 68. Всегда смотрите на исходный файл нужной версии.

**Пять ATR в проекте — умышленно разные.** В этом файле два: `_wilder_atr` (SMA-seed рекурсия, для ATR Breakout и Volume Breakout раннеров) и EWM-ATR внутри `calculate_indicators` (для EMA Crossover, Mean Reversion, Donchian). Ещё три — в signalgen: `wilder_atr(arrays)` (паритет-тесты), `_WilderATR`-класс (живая ATR Breakout стратегия) и `_wilder_atr_vectorized` ([[supertrend-indicator|Supertrend]] раннер). Первые четыре математически тождественны (Уайлдер); EWM-вариант даёт ~1.4% расхождение. Их нельзя смешивать — каждый привязан к своему потребителю.

**`ddof=0` в Bollinger намеренно.** Это не ошибка — это оригинальная спецификация Боллинджера. Менять на `ddof=1` без синхронного изменения в `signalgen/bollinger_bands.py` создаст расхождение между бэктестом и live.

**LOCKED-параметры не трогать.** Параметры `volume_breakout` (`lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563`) зафиксированы ADR 0059 по результатам sweep#1644. Любое изменение — это новая стратегия, требующая полного [[walk-forward-analysis|WFA-прогона]] и [[deflated-sharpe-ratio|DSR-верификации]]. Аналогично для `donchian` (ADR 0054).

**Сигнал строится на закрытии `T`, исполняется на открытии `T+1`.** Движок `replay_engine` читает `signal[i]` и планирует сделку на `open[i+1]`. Это honest-fill контракт: на момент сигнала цена открытия следующего бара ещё неизвестна. `(src/backtest/replay_engine.py:228–234)`

**Warmup ≠ «мусорные данные».** Первые N баров не попадают в сигналы, но EMA и ATR начинают вычисляться с первого бара. NaN-маска для RSI и ATR гарантирует, что незрелые значения не вызовут ложных сигналов. Это тонкое различие: индикатор «знает» историю с бара 0, но выдаёт результат только с бара N.

**Если `volume` отсутствует — `volume_breakout` молчит.** Строка 239: `if "volume" not in df.columns: return np.zeros(n, dtype=np.int8)`. Никаких ошибок, просто нулевой массив.

## Связанные документы

### Движок и модели исполнения (кто читает колонку `signal`)
- [[replay-engine-bar-by-bar]] — как движок читает колонку `signal` и исполняет сделки; контракт close(T)→open(T+1)
- [[replay-engine-metrics]] — какие метрики (Sharpe, Sortino, Profit Factor) считаются по итогам сделок из этих сигналов
- [[research-kernel-execution-model]] — ВТОРАЯ модель исполнения (`_backtest_single`); раннеры ATR/Volume Breakout, вызывающие `_wilder_atr` из этого файла
- [[vector-backtest-fast-approximation]] — быстрый безцикловый движок-альтернатива для грубой оценки той же логики
- [[trade-extractor-and-records]] — как DataFrame сделок из replay-пути превращается в `TradeRecord` для статистики (DSR)
- [[what-is-backtest-overview]] — карта всего раздела бэктеста, куда встроена эта функция

### Архитектура сигнала
- [[signal-architecture]] — что такое Signal/SignalSide и reason code; live-паттерн `on_bar → Signal | None` (контраст к векторной колонке `signal`)

### Индикаторы — математика в live-системе (signalgen/)
- [[02-стратегии/technical-indicators]] — математика индикаторов в live-системе (`signalgen/`); два варианта RSI и ATR (talib vs pandas)
- [[ema-rsi-indicators]] — EMA и RSI по отдельности: классический vs Wilder, NaN-прогрев (та же математика, что здесь)
- [[atr-indicator]] — ATR как измеритель волатильности; почему в проекте несколько версий ATR
- [[bollinger-bands-indicator]] — полосы Боллинджера: `ddof=0`, ветка `mean_reversion` использует те же формулы
- [[donchian-channel-indicator]] — канал Дончиана: скользящий максимум, тот же анти-look-ahead `.shift(1)`
- [[supertrend-indicator]] — Supertrend (Lazybear): использует `_wilder_atr_vectorized`, отдельный от EWM-ATR
- [[adx-indicator]] — ADX: индикатор силы тренда, который эта функция НЕ вычисляет (контраст к live-фильтру EMA)

### Стратегии-потребители сигналов
- [[02-стратегии/ema-crossover-strategy]] — EMA-стратегия в live-режиме: параметры, прогрев, NaN-guard
- [[02-стратегии/mean-reversion-strategy]] — Bollinger + RSI в live-режиме; залоченные параметры и их история
- [[02-стратегии/donchian-breakout-strategy]] — Donchian в live-режиме; почему LOCKED, что значит ADR 0054
- [[volume-breakout-strategy]] — Volume Breakout подробно: sweep#1644, почему 1.4563
- [[02-стратегии/atr-breakout-strategy]] — ATR Breakout: раннер использует общий `_wilder_atr` из этого файла
- [[02-стратегии/supertrend-strategy]] — Supertrend-стратегия: рекурсивная линия на базе Wilder-ATR

### Валидация и статистика (почему параметры LOCKED)
- [[walk-forward-analysis]] — честная проверка на невиданных данных; изменение LOCKED-параметров делает WFA невалидным
- [[deflated-sharpe-ratio]] — DSR-поправка на множественные проверки; sweep#1644 = 4510 комбинаций
- [[monte-carlo-permutation]] — тест перестановок: не случайна ли прибыль сигналов
- [[acceptance-gates-t1-t6]] — ворота приёмки T1-T6, которые обязана пройти стратегия на этих сигналах
- [[dsr-metric]] — DSR со стороны раздела метрик (обоснование anti-snooping для LOCKED-параметров)
- [[mc-permutation-test]] — Monte-Carlo со стороны раздела метрик (значимость сигнала)
- [[donchian-runner-and-reference-run]] — как Donchian-раннер использует `calculate_indicators` в WFA-прогоне

### Прочее
- [[wilder-atr-and-stops]] — сравнение EWM-ATR и Wilder-ATR: когда какой используется
- [[configuration-and-settings]] — откуда берутся параметры (`fast_period`, `overbought`, `oversold`) и какие защиты встроены
- [[bar-source-live]] — защита от look-ahead в live-режиме (тот же принцип честности сигнала)
- [[documentation-tab]] — вкладка дашборда с карточками индикаторов, рендерятся из того же кода

За техническими деталями реализации индикаторов в signalgen: `llm-wiki/wiki/project/components/indicators.md`
