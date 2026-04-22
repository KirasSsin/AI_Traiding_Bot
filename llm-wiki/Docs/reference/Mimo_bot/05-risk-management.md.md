# Модуль 5: Риск-менеджмент — Полный аудит и выбор

> Агент 5: Risk Management  
> Дата: 2026-04-17  
> Статус: Финальная версия для MVP v0.1

---

## Содержание

1. [Аудит всех инструментов](#1-аудит-всех-инструментов)
2. [Выбор лучших инструментов](#2-выбор-лучших-инструментов)
3. [Отклонённые инструменты](#3-отклонённые-инструменты)
4. [Cross-check: Агент 1 (Trend) и Агент 4 (Volatility)](#4-cross-check)
5. [Конфликты](#5-конфликты)
6. [Итоговая конфигурация](#6-итоговая-конфигурация)
7. [Rust-специфика](#7-rust-специфика)

---

## 1. Аудит всех инструментов

### 1.1 ATR-based Stop Loss / Take Profit

**Классификация:** Position Sizing + Exit Management  
**Источник:** Research Indicators, Модуль 5; Risk Document, Секция 7

#### Формула

```
LONG:
  SL = Entry − k_SL × ATR(14)
  TP = Entry + k_TP × ATR(14)
  SL_distance = k_SL × ATR
  Reward_distance = k_TP × ATR
  R:R = k_TP / k_SL

SHORT:
  SL = Entry + k_SL_short × ATR(14)
  TP = Entry − k_TP × ATR(14)
```

Где:
- `k_SL = 2.0` (long), `k_SL_short = 1.5` (short — падения быстрее)
- `k_TP = 3.0` → R:R = 1.5:1 (long), 2.0:1 (short)
- `ATR(14) = SMA(TrueRange, 14)`
- `TrueRange = max(High−Low, |High−PrevClose|, |Low−PrevClose|)`

#### Промежуточные вычисления

```
TrueRange_i = max(
    High_i − Low_i,
    |High_i − Close_{i-1}|,
    |Low_i − Close_{i-1}|
)

ATR_14 = (1/14) × Σ_{j=i-13}^{i} TrueRange_j    // SMA-based
// Альтернатива (Wilder's smoothing):
ATR_i = (ATR_{i-1} × 13 + TrueRange_i) / 14
```

#### Position Size (интеграция с ATR)

```
PositionSize = min(FractionalKelly, MaxPct) × Capital / SL_distance

где:
  MaxPct = 0.05 (5% капитала на сделку)
  SL_distance = k_SL × ATR(14)
```

#### Числовой пример

```
Entry = 42,000 USD (BTC)
ATR_14 = 1,200 USD
k_SL = 2.0, k_TP = 3.0
Capital = 10,000 USD
FractionalKelly = 0.1464, MaxPct = 0.05

SL = 42,000 − 2.0 × 1,200 = 39,600
TP = 42,000 + 3.0 × 1,200 = 45,600
SL_distance = 2,400
PositionSize = min(0.1464, 0.05) × 10,000 / 2,400 = 0.2083 BTC
MaxLoss = 0.2083 × 2,400 = 500 USD (5% от капитала)
MaxGain = 0.2083 × 3,600 = 750 USD (7.5% от капитала)
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | ATR → 0 (экстремально низкая волатильность) | SL_distance → 0, PositionSize → ∞. **Fix:** минимальный SL_distance = max(2×ATR, 0.5%×Entry) |
| 2 | ATR > 50% Entry (мемкоины) | SL = Entry − 2×ATR может быть < 0. **Fix:** переключиться на % stop: SL = Entry × (1 − 0.05) |
| 3 | Flash crash (свеча пробивает SL и TP одновременно) | Исполнение по худшей цене. **Fix:** использовать OCO ордер + slippage cap |
| 4 | ATR резко меняется между свечами | SL/TP «прыгают». **Fix:** пересчёт SL только при входе, trailing — по отдельной логике |

#### Rust-оптимизация

```rust
/// Wilder-smoothed ATR — O(1) обновление, без аллокаций
pub struct ATR {
    period: usize,
    smoothed: f64,
    count: usize,
}

impl ATR {
    pub fn new(period: usize) -> Self {
        Self { period, smoothed: 0.0, count: 0 }
    }

    pub fn update(&mut self, high: f64, low: f64, prev_close: f64) -> f64 {
        let tr = (high - low)
            .max((high - prev_close).abs())
            .max((low - prev_close).abs());

        self.count += 1;
        if self.count <= self.period {
            self.smoothed += tr;
            if self.count == self.period {
                self.smoothed /= self.period as f64;
            }
        } else {
            self.smoothed = (self.smoothed * (self.period - 1) as f64 + tr) 
                / self.period as f64;
        }
        self.smoothed
    }

    /// Вычислить SL/TP без аллокаций
    pub fn calc_levels(&self, entry: f64, k_sl: f64, k_tp: f64, is_long: bool) 
        -> (f64, f64) 
    {
        if is_long {
            (entry - k_sl * self.smoothed, entry + k_tp * self.smoothed)
        } else {
            (entry + k_sl * self.smoothed, entry - k_tp * self.smoothed)
        }
    }
}
```

**Оценка: ★★★★★ — ВЫБРАН. Адаптивность к волатильности критична для крипты.**

---

### 1.2 Fractional Kelly (Half-Kelly)

**Классификация:** Position Sizing  
**Источник:** Research Indicators, Модуль 5; Risk Document, Секция 6

#### Формула (полный Kelly)

```
Kelly = (W × R − L) / R

где:
  W = WinRate = Wins / TotalTrades
  L = LossRate = 1 − W
  R = AvgWin / AvgLoss (profit ratio)
```

#### Fractional Kelly

```
FractionalKelly = Kelly × f   (f = 0.5 для Half-Kelly, f = 0.25 для Quarter-Kelly)
```

#### Скорректированный Kelly (с учётом skewness)

```
f* = Kelly × (1 − S / (3W) × Kelly)

где S — skewness доходности на сделку
```

#### Числовой пример

```
W = 0.55, L = 0.45, AvgWin = 350, AvgLoss = 200
R = 350 / 200 = 1.75

Kelly = (0.55 × 1.75 − 0.45) / 1.75 = 0.5125 / 1.75 = 0.2929 (29.29%)
Half-Kelly = 0.2929 × 0.5 = 0.1464 (14.64%)
Quarter-Kelly = 0.2929 × 0.25 = 0.0732 (7.32%)

С коррекцией (S = −1.5):
f* = 0.2929 × (1 − (−1.5)/(3×0.55) × 0.2929) = 0.2929 × 1.2663 = 0.3709
Quarter-Kelly скорр. = 0.3709 × 0.25 = 0.0927 (9.27%)
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | Kelly ≤ 0 (нет edge) | Не торговать. Автостоп. |
| 2 | Kelly > 1 (>100% капитала) | Cap на 25% (Quarter-Kelly × 2) |
| 3 | Недостаточно сделок (< 30) | Kelly ненадёжен. Использовать Fixed Fraction (2%) до набора статистики |
| 4 | Резкая смена win rate | Скользящее окно 50 сделок, не накопительный расчёт |
| 5 | S = 0 (симметрия) | f* = Kelly, поправка вырождается |

#### Почему Half-Kelly, а не Full Kelly

- Full Kelly: максимальный геометрический рост, **но** просадки ~50% капитала
- Half-Kelly: ~75% доходности при ~25% просадке
- Quarter-Kelly: ~50% доходности при ~12% просадке
- На крипте с fat tails (excess kurtosis ~6–9) Half-Kelly — **максимум допустимого**

#### Почему не Optimal f (Ralph Vince)

```
Optimal f = (HPR_max − 1) / (HPR_max × LargestLoss / TradeUnit)

где HPR_max = max по f от ∏(1 + f × (−Trade_i / LargestLoss))
```

- Требует точного знания Largest Loss
- На крипте flash crash может переписать рекорд Largest Loss → Optimal f резко меняется
- Fractional Kelly устойчивее: зависит от средних, не от экстремума
- Сложнее реализации: нужен перебор f от 0.01 до 1.0 с шагом 0.01

**Оценка: ★★★★★ — ВЫБРАН. Устойчивость + теоретическое обоснование.**

---

### 1.3 VaR (Value at Risk) — Historical

**Классификация:** Портфельный риск  
**Источник:** Research Indicators, Модуль 5; Risk Document, Секция 1.1

#### Формула

```
VaR_Historical = −Percentile(PnL_window, α)

где:
  PnL_window — массив дневных P&L за N дней (окно)
  α = 0.05 для 95% доверительного интервала
  Percentile — линейная интерполяция между элементами
```

#### Алгоритм (percentile через линейную интерполяцию)

```
sorted_PnL = sort(PnL_window) ascending
index = α × (N − 1)  // 0-indexed
lower = floor(index)
upper = ceil(index)
frac = index − lower

VaR = −(sorted_PnL[lower] + frac × (sorted_PnL[upper] − sorted_PnL[lower]))
```

#### Числовой пример (30 дней)

```
PnL = [-500, -450, -400, -370, -350, -300, -280, -200, -180, -150,
       -120, -110, -90, -60, -50, +75, +80, +90, +100, +130,
       +150, +160, +170, +180, +200, +200, +250, +290, +350, +420]

α = 0.05, N = 30
index = 0.05 × 29 = 1.45
lower = 1 (sorted_PnL[1] = -450), upper = 2 (sorted_PnL[2] = -400)
frac = 0.45

VaR = −(-450 + 0.45 × (-400 − (-450))) = −(-450 + 22.5) = 427.5 USD

VaR = 427.5 USD (4.275% от капитала 10,000)
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | N < 20 наблюдений | Перцентиль ненадёжен. Минимум 60 наблюдений (2 месяца). |
| 2 | Все PnL ≈ 0 (низкая волатильность) | VaR ≈ 0, ложная безопасность. Использовать min VaR = 1% Capital. |
| 3 | Один экстремальный выброс | VaR нестабилен при удалении/добавлении 1 дня. Использовать скользящее окно + bootstrap. |
| 4 | Окно содержит только прибыли | VaR = 0 или положительный → CVaR тоже. Опасно: нет данных о хвостах. |

**Оценка: ★★★★☆ — ВЫБРАН как дополнительная метрика мониторинга (не primary).**

---

### 1.4 VaR — Parametric

**Классификация:** Портфельный риск  
**Источник:** Risk Document, Секция 1.2

#### Формула

```
VaR_Parametric = μ − z_α × σ

где:
  μ = среднее дневной доходности
  σ = стандартное отклонение дневной доходности
  z_α = 1.645 (для α = 5%)
```

#### Числовой пример

```
μ = -32.83 USD, σ = 228.5 USD
VaR = −32.83 − 1.645 × 228.5 = −408.71 USD
VaR ≈ 409 USD
```

#### Почему ОТКЛОНЁН

- **Предполагает нормальное распределение** — крипта имеет kurtosis ~9 (vs 3 нормального)
- На крипте событие на 4σ происходит несколько раз в год (vs «раз в 31,500 лет» по нормальному)
- **Систематически недооценивает риск**: VaR_parametric = 409 vs Historical VaR = 428
- Не учитывает отрицательную асимметрию (skewness ~ -1.2)
- Fat tails на крипте → реальные потери в 2–3 раза превышают параметрическую оценку

**Оценка: ★★☆☆☆ — ОТКЛОНЁН. Неприемлем для крипты.**

---

### 1.5 VaR — Cornish-Fisher

**Классификация:** Портфельный риск  
**Источник:** Risk Document, Секция 1.3

#### Формула

```
z* = z + (z² − 1)/6 × S + (z³ − 3z)/24 × K − (2z³ − 5z)/36 × S²

VaR_CF = μ + σ × z*

где:
  z = -1.645 (левый хвост, 95%)
  S = skewness выборки
  K = excess kurtosis выборки (kurtosis − 3)
```

#### Пошаговый расчёт

```
z = -1.645, S = -1.2, K = 6.0

Шаг 1: Базовый z = -1.645
Шаг 2: (z² − 1)/6 × S = (2.706 − 1)/6 × (-1.2) = -0.3412
Шаг 3: (z³ − 3z)/24 × K = (-4.457 + 4.935)/24 × 6.0 = 0.1195
Шаг 4: (2z³ − 5z)/36 × S² = (-8.914 + 8.225)/36 × 1.44 = -0.0276
Шаг 5: z* = -1.645 - 0.3412 + 0.1195 + 0.0276 = -1.8391
Шаг 6: VaR_CF = -32.83 + 228.5 × (-1.8391) = -453.08 USD

VaR_CF = 453 USD (на 11% выше параметрического VaR)
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | S = 0 (симметрия) | Сводится к Parametric VaR. Не бывает на крипте. |
| 2 | \|S\| > 3 | Ряд Тейлора расходится. Переход к GPD для хвостов. |
| 3 | K < 0 (platykurtic) | Редко на крипте. VaR < Parametric — корректно, но осторожно. |

#### Почему ОТКЛОНЁН (для MVP)

- Сложнее Historical VaR (расчёт 4-го момента на малой выборке нестабилен)
- При |S| > 3 аппроксимация второго порядка расходится
- Historical VaR проще, надёжнее, не требует предположений о распределении
- На практике Cornish-Fisher даёт схожий с Historical результат, но с дополнительной ошибкой оценки моментов

**Оценка: ★★★☆☆ — ОТКЛОНЁН для MVP. Запланировать на v0.3+ с N > 250.**

---

### 1.6 VaR — Monte Carlo

**Классификация:** Портфельный риск  
**Источник:** Research Indicators, Модуль 10

#### Формула

```
Для каждой симуляции i = 1..M:
  PnL_i = Σ_{t=1}^{T} (w_t × simulated_return_{i,t})

  simulated_return = μ + σ × Z    // если GBM
  или
  simulated_return = μ + σ × Z × (1 + jump × Bernoulli(p_jump))  // GBM с jumps

  Z ~ N(0,1) или Student-t(ν)

VaR_MC = −Percentile({PnL_1, ..., PnL_M}, α)
```

#### Почему ОТКЛОНЁН (для MVP)

- Требует выбора модели распределения (GBM? GBM+jumps? GARCH-filtered?)
- M = 10,000+ симуляций → вычислительно дорого для paper backtester
- Качество зависит от точности оценки параметров (μ, σ, jump intensity)
- Для MVP Historical VaR покрывает 90% потребностей без сложностей
- Запланировать на v1.5 с Levy jumps

**Оценка: ★★★☆☆ — ОТКЛОНЁН для MVP. Запланировать на v1.5.**

---

### 1.7 CVaR / Expected Shortfall

**Классификация:** Портфельный риск  
**Источник:** Research Indicators, Модуль 5; Risk Document, Секция 2

#### Формула

```
CVaR_α = E[PnL | PnL ≤ VaR_α]

Для дискретной выборки:
  CVaR_α = (1/k) × Σ_{i=1}^{k} sorted_PnL[i]

где k = ⌈α × N⌉ (количество наблюдений в худших α%)
```

#### Числовой пример

```
N = 250 дней, VaR = 500 USD
k = ⌈0.05 × 250⌉ = 13 худших дней

Худшие 13 дней:
[-1800, -1500, -1350, -1200, -1100, -980, -870, -750, -690, -620, -580, -540, -510]

CVaR = (-1800 - 1500 - ... - 510) / 13 = -12490 / 13 = -961.54 USD

CVaR = 961.54 USD (почти вдвое > VaR = 500!)
```

#### Почему важнее VaR

- VaR: «с вероятностью 5% убыток > X»
- CVaR: «**если** убыток > X, в среднем он будет Y»
- CVaR — когерентная мера (субаддитивность: риск портфеля ≤ сумме рисков)
- VaR — некогерентный (может нарушать субаддитивность)

#### Применение в боте

```
Если CVaR > 10% Capital → стоп-торговля
Если CVaR > 5% Capital → сократить позицию на 50%
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | VaR = 0 (все прибыльные дни) | CVaR = 0. Красный флаг о качестве данных. |
| 2 | Все худшие наблюдения идентичны | CVaR = VaR. Проверить slippage за пределами стопа. |
| 3 | α = 1%, N = 30 → k = 0.3 | CVaR не определён. Увеличить N или использовать параметрический подход. |

**Оценка: ★★★★★ — ВЫБРАН. Критичный дополнительный уровень защиты.**

---

### 1.8 MaxDD Circuit Breaker

**Классификация:** Emergency Stop  
**Источник:** Research Indicators, Модуль 5; Risk Document, Секция 8

#### Формула

```
CurrentDD = (Peak − CurrentCapital) / Peak

Уровни:
  L1 (Pre-warning): CurrentDD ≥ 12% → PositionSize × 0.5
  L2 (Full Stop):   CurrentDD ≥ 15% → halt all trading

Peak = max(Capital_t) for all t ≤ now
```

#### Условия восстановления

```
Торговля возобновляется при:
  1. Новый торговый день (00:00 UTC), ИЛИ
  2. CurrentDD < 10% (зона безопасности), ИЛИ
  3. Timeout 4 часа после Full Stop
```

#### Числовой пример

```
День 5:  Capital = 10,800 (пик), DD = 0% → Normal
День 10: Capital = 9,500, DD = (10800−9500)/10800 = 12.04% → PRE-WARNING: ×0.5
День 13: Capital = 9,100, DD = 15.74% → FULL STOP
День 14: 00:00 UTC → возобновление
```

#### Flash Crash подмодуль

```
Если PnL за 1 свечу (5 мин) < −8% Capital:
  → Немедленно закрыть все позиции market order
  → Независимо от проскальзывания
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | Flash crash: 0% → 20% за минуту | Flash Crash Stop (8% за свечу) |
| 2 | Whipsaw: частое срабатывание | Cooldown 24ч после Full Stop |
| 3 | Разворот рынка во время Full Stop | «Стоимость страховки» — принимаемо. Частота продолжения падения > разворота. |
| 4 | MaxDD в % некорректен при выводе средств | Использовать High Water Mark (HWM) в абсолютных $ |

**Оценка: ★★★★★ — ВЫБРАН. Последняя линия обороны. Незаменим.**

---

### 1.9 Risk of Ruin

**Классификация:** Стратегическая валидация  
**Источник:** Research Indicators, Модуль 5; Risk Document, Секция 5

#### Формула

```
Edge = W × AvgWin − L × AvgLoss    // матожидание на сделку
Ratio = Edge / Risk_per_trade

P_ruin = ((1 − Ratio) / (1 + Ratio))^(Capital / Risk_per_trade)
```

#### Числовой пример (безопасный)

```
Capital = 10,000, Risk = 200, W = 0.55, AvgWin = 350, AvgLoss = 200
Edge = 0.55 × 350 − 0.45 × 200 = 102.5
Ratio = 102.5 / 200 = 0.5125
(1−0.5125)/(1+0.5125) = 0.3223
P_ruin = 0.3223^50 ≈ 1.14 × 10⁻²⁵  (практически 0)
```

#### Числовой пример (агрессивный)

```
Capital = 5,000, Risk = 1,000 (20%!), W = 0.50, AvgWin = 1,200, AvgLoss = 1,000
Edge = 100, Ratio = 0.1
P_ruin = 0.8182^5 = 0.368 = 36.8%  (ОПАСНО!)
```

#### Применение

```
P_ruin > 5% → стратегия забракована
P_ruin > 1% → предупреждение, сократить position size
```

#### Edge Cases

| # | Ситуация | Решение |
|---|---------|---------|
| 1 | Edge = 0 | P_ruin = 1 (100%). Автостоп. |
| 2 | Edge < 0 | P_ruin = 100%. Гарантированное разорение. |
| 3 | Risk = 0 | P_ruin = 0. Тривиально. |

**Оценка: ★★★★☆ — ВЫБРАН как gate при запуске (pre-trade validation).**

---

### 1.10 Fixed Fraction (Fixed % Risk)

**Классификация:** Position Sizing  
**Источник:** MVP and Roadmap

#### Формула

```
PositionSize = RiskPct × Capital / SL_distance

где RiskPct — фиксированный процент (1–5%)
```

#### Числовой пример

```
RiskPct = 2%, Capital = 10,000, SL_distance = 2,400
PositionSize = 0.02 × 10,000 / 2,400 = 0.0833 BTC
```

#### Почему ОТКЛОНЁН (заменён Fractional Kelly)

- Не адаптируется к качеству стратегии (одинаковый % для win rate 45% и 65%)
- Не использует информацию о матожидании
- Fixed 2% → может быть слишком агрессивным для плохой стратегии и слишком консервативным для хорошей
- Fractional Kelly делает то же самое, но с обоснованием

**Оценка: ★★★☆☆ — ОТКЛОНЁН. Оставлен как fallback при < 30 сделок.**

---

### 1.11 Trailing Stop (Price-based)

**Классификация:** Exit Management

#### Формула

```
TrailingStop = max(TrailingStop_prev, EntryPrice × (1 − TrailPct))

для LONG:  TS = max(TS_prev, High_since_entry × (1 − TrailPct))
для SHORT: TS = min(TS_prev, Low_since_entry × (1 + TrailPct))
```

#### Почему ОТКЛОНЁН (заменён ATR-based trailing)

- Fixed % trailing не адаптируется к волатильности
- На спокойном рынке: слишком тесный → преждевременный выход
- На volatile: слишком широкий → теряет прибыль
- ATR-based (Supertrend, Chandelier Exit) делает это лучше

**Оценка: ★★☆☆☆ — ОТКЛОНЁН.**

---

### 1.12 Chandelier Exit

**Классификация:** Exit Management

#### Формула

```
LONG:
  ChandelierExit = HighestHigh(N) − k × ATR(N)
  
SHORT:
  ChandelierExit = LowestLow(N) + k × ATR(N)

где N = 22 (типично), k = 3.0
```

#### Числовой пример

```
HighestHigh(22) = 45,000, ATR(22) = 1,200, k = 3.0
ChandelierExit = 45,000 − 3.0 × 1,200 = 41,400
```

#### Почему ОТКЛОНЁН (как отдельный инструмент)

- Логика уже встроена в Supertrend (Агент 1), который использует ATR
- Supertrend(10, 3) ≈ Chandelier Exit(10, 3) с дополнительной фильтрацией
- Дублирование функционала
- Если Supertrend не будет реализован — Chandelier Exit как fallback

**Оценка: ★★★☆☆ — ОТКЛОНЁН как самостоятельный. Supertrend покрывает.**

---

### 1.13 Dynamic Stops (HMM-regime switching)

**Классификация:** Exit Management  
**Источник:** MVP and Roadmap, v1.5

#### Формула

```
Если HMM_state == BULL:
  k_SL = 2.5 (шире стоп, тренд сильный)
  k_TP = 4.0
Если HMM_state == BEAR:
  k_SL = 1.5 (теснее стоп, хрупкий рынок)
  k_TP = 2.0
Если HMM_state == RANGE:
  k_SL = 1.0 (очень тесно)
  k_TP = 1.5
```

#### Почему ОТКЛОНЁН (для MVP)

- Зависит от HMM, который запланирован на v0.3
- MVP не имеет статистических моделей
- На v0.1–v0.2: фиксированные k_SL = 2.0, k_TP = 3.0
- На v0.3: добавить regime-aware переключение

**Оценка: ★★★★☆ — ОТКЛОНЁН для MVP. Запланировать на v0.3.**

---

### 1.14 Portfolio VaR

**Классификация:** Портфельный риск

#### Формула

```
Portfolio_VaR = √(wᵀ × Σ × w)

где:
  w — вектор весов позиций
  Σ — ковариационная матрица доходностей активов

С поправкой на VaR:
  Portfolio_VaR_α = z_α × √(wᵀ × Σ × w) × √T
```

#### Почему ОТКЛОНЁН для MVP

- MVP: одна пара BTC/USDT → портфельный VaR = позиционный VaR
- На v0.2+ с несколькими парами (BTC, ETH, SOL) — критически важен
- Ковариационная матрица 3×3 требует минимум 60 наблюдений
- Корреляция → 1.0 во время кризиса (диверсификация не работает)

**Оценка: ★★★★☆ — ОТКЛОНЁН для MVP. Критичен для v0.2+ (multi-pair).**

---

### 1.15 Correlation-based Hedging

**Классификация:** Портфельный риск  
**Источник:** Research Indicators, Модуль 11

#### Формула

```
corr_matrix[i,j] = Corr(returns_i, returns_j)

Правило:
  Если corr(A, B) > 0.8 → не открывать обе позиции
  Или: PositionSize_combined = PositionSize / 2 для каждой
```

#### Почему ОТКЛОНЁН для MVP

- Одна пара → нечего хеджировать
- На v0.2+: критически важно
- Кризисная корреляция → 1.0 → хедж не работает в самый важный момент

**Оценка: ★★★☆☆ — ОТКЛОНЁН для MVP. Запланировать на v0.2.**

---

### 1.16 Position Sizing — % Volatility

**Классификация:** Position Sizing

#### Формула

```
PositionSize = (RiskPct × Capital) / (VolMultiplier × σ_daily × Entry)
```

#### Почему ОТКЛОНЁН

- ATR-based sizing покрывает тот же функционал, но в ценах (удобнее для расчёта SL/TP)
- % Volatility требует конвертации σ → цену → обратно
- ATR уже использует True Range, который ближе к реальному исполнению

**Оценка: ★★☆☆☆ — ОТКЛОНЁН. ATR-based лучше.**

---

### 1.17 GARCH-based Risk Adjustment

**Классификация:** Динамический риск  
**Источник:** Research Indicators, Модуль 3

#### Формула

```
σ²_t = ω + α × ε²_{t-1} + β × σ²_{t-1}

где:
  ω — константа (long-run variance)
  α — вес последнего шока (ARCH term)
  β — persistence (GARCH term)
  α + β < 1 (stationarity condition)

Если predicted_σ > P95(historical_σ):
  → PositionSize × 0.5
```

#### Статус

- Запланирован на v0.3 (GARCH в модуле волатильности)
- Для MVP: ATR(14) покрывает оценку текущей волатильности
- GARCH даёт **прогноз** будущей волатильности — ценно, но не MVP-critical

**Оценка: ★★★★☆ — ОТКЛОНЁН для MVP. Запланировать на v0.3.**

---

### 1.18 Ulcer Index-based Risk

**Классификация:** Метрика  
**Источник:** Risk Document, Секция 3

#### Формула

```
UI = √(Σ DD_i² / N)

где DD_i = (Peak − Current_i) / Peak × 100%
```

#### Статус

- Используется как метрика (в отчёте), не как торговый инструмент
- Включение в reporting, не в risk manager

**Оценка: ★★★☆☆ — МЕТРИКА. Не инструмент. В reporting.**

---

### 1.19 Calmar / Sterling / Burke Ratios

**Классификация:** Метрики эффективности  
**Источник:** Risk Document, Секция 4

```
Calmar  = CAGR / MaxDD
Sterling = CAGR / (MaxDD − AvgDD)
Burke   = CAGR / √(Σ DD_i²)
```

#### Статус

- Метрики для отчёта, не торговые инструменты
- Calmar ≥ 1.0 — порог качества стратегии
- Не используются для принятия торговых решений в реальном времени

**Оценка: ★★★★☆ — МЕТРИКИ. В reporting. Calmar ≥ 1.0 как gate.**

---

### 1.20 Slippage Model

**Классификация:** Execution Quality  
**Источник:** Research Indicators, Модуль 8

#### Формула

```
Slippage = κ × σ_daily × √(Q / V_daily)

где:
  κ = 0.1 (эмпирическая константа)
  σ_daily = дневная волатильность
  Q = размер ордера
  V_daily = средний дневной объём
```

#### Статус

- Часть Execution Simulator, не Risk Manager
- Но влияет на реальный SL/TP: SL_actual = SL_theoretical + Slippage

**Оценка: ★★★★☆ — В Execution Simulator. Учитывается при расчёте SL.**

---

## 2. Выбор лучших инструментов

### Выбранные инструменты (3 шт.)

| # | Инструмент | Роль | Параметры |
|---|-----------|------|-----------|
| **1** | **ATR-based SL/TP + Position Sizing** | Primary: стопы, тейк-профиты, размер позиции | k_SL = 2.0 (long), 1.5 (short); k_TP = 3.0; MaxPct = 5% |
| **2** | **Fractional Kelly (Half-Kelly)** | Primary: оптимальный размер позиции | f = 0.5; Min 30 сделок; Cap = 25% |
| **3** | **MaxDD Circuit Breaker** | Emergency: аварийная остановка | Pre-warning 12% (×0.5), Full Stop 15%, Flash Stop 8%/свеча |

### Дополнительные (secondary, не primary)

| # | Инструмент | Роль | Когда |
|---|-----------|------|-------|
| 4 | CVaR / Expected Shortfall | Мониторинг хвостового риска | CVaR > 10% → halt; > 5% → reduce |
| 5 | Historical VaR (95%) | Ежедневный мониторинг | VaR > 5% → предупреждение |
| 6 | Risk of Ruin | Gate при запуске стратегии | P_ruin > 5% → reject |

### Почему именно эти три

**1. ATR-based SL/TP** — единственный инструмент, который адаптируется к волатильности. На крипте, где волатильность меняется в 5–10 раз, фиксированные стопы — это катастрофа. ATR автоматически расширяет стопы при турбулентности и сужает при штиле.

**2. Fractional Kelly** — теоретически оптимальный размер позиции с контролируемым риском. Half-Kelly даёт ~75% от максимальной доходности при ~25% просадке. Единственный метод с обоснованием из теории информации (максимизация log-utility).

**3. MaxDD Circuit Breaker** — последняя линия обороны. Без него бот может потерять 50–100% капитала в «смертельной спирали» (пытается отыграться →加倍 убытки). 15% threshold — эмпирически оптимальный: достаточно, чтобы дать рынку «подышать», но достаточно tight, чтобы сохранить >85% капитала.

---

## 3. Отклонённые инструменты

| # | Инструмент | Причина отклонения |
|---|-----------|-------------------|
| 1 | Parametric VaR | Предполагает нормальность. Крипта: kurtosis ~9. Систематически недооценивает риск. |
| 2 | Cornish-Fisher VaR | Сложнее Historical, не даёт преимуществ на малой выборке. \|S\| > 3 → расхождение. |
| 3 | Monte Carlo VaR | Слишком computationally expensive для MVP. Запланирован v1.5. |
| 4 | Fixed Fraction | Не адаптируется к качеству стратегии. Kelly делает то же лучше. |
| 5 | Full Kelly | Просадки 50%+. Margin call на крипте. **ЗАПРЕЩЁНО.** |
| 6 | Optimal f (Vince) | Зависит от Largest Loss → нестабилен на крипте (flash crash). |
| 7 | Trailing Stop (fixed %) | Не адаптируется к волатильности. ATR-based лучше. |
| 8 | Chandelier Exit | Дублирует Supertrend (Агент 1). |
| 9 | Dynamic Stops (HMM) | Зависит от HMM (v0.3). Не для MVP. |
| 10 | Portfolio VaR | Одна пара в MVP. Не нужен до v0.2 (multi-pair). |
| 11 | Correlation Hedging | Одна пара в MVP. Не нужен до v0.2. |
| 12 | % Volatility Sizing | ATR-based покрывает лучше. |
| 13 | GARCH Risk Adj. | Запланирован v0.3. ATR пока sufficient. |
| 14 | VaR Monte Carlo (Levy) | Запланирован v1.5. Сложность не оправдана для MVP. |

---

## 4. Cross-check: Агент 1 (Trend) и Агент 4 (Volatility)

### 4.1 Агент 1 (Trend) — выбранные инструменты

Из Research Indicators, Модуль 1:

| # | Индикатор | Параметры | Потенциальный риск |
|---|-----------|-----------|-------------------|
| 1 | EMA (20/50) | Crossover | ⚠️ Ложные сигналы во флэте → whipsaw убытки |
| 2 | ADX (14) | threshold 25 | ✅ Фильтр, снижает whipsaw |
| 3 | Supertrend (10, 3) | ATR-based trailing | ⚠️ **ПОТЕНЦИАЛЬНЫЙ КОНФЛИКТ** |
| 4 | KAMA (30) | Adaptive | ✅ Адаптивная, минимум ложных |
| 5 | Ichimoku (9/26/52/26) | Cloud system | ⚠️ Сложность, 5 линий → запаздывание |
| 6 | Parabolic SAR (0.02, 0.2) | Acceleration | ⚠️ **ПОТЕНЦИАЛЬНЫЙ КОНФЛИКТ** |

### 4.2 Агент 4 (Volatility) — выбранные инструменты

Из Research Indicators, Модуль 3:

| # | Инструмент | Параметры | Потенциальный риск |
|---|-----------|-----------|-------------------|
| 1 | ATR (14) | Base vol | ✅ Основа для всех расчётов |
| 2 | Bollinger Bands (20, 2) | Std-based | ⚠️ Squeeze → breakout может быть ложным |
| 3 | Keltner Channel (20, 1.5) | ATR-based | ✅ Подтверждение squeeze |
| 4 | GARCH(1,1) | Прогноз vol | ✅ v0.3 |
| 5 | Yang-Zhang | Realized vol | ✅ v0.3 |

### 4.3 Выявленные конфликты

**См. секцию [5. Конфликты](#5-конфликты) ниже.**

---

## 5. Конфликты

### CONFLICT-001: Supertrend как trailing stop + ATR-based SL — дублирование

**Кому:** Агент 1 (Trend)  
**Серьёзность:** СРЕДНЯЯ  
**Описание:**

Агент 1 выбрал Supertrend(10, 3) как динамический trailing stop. Risk Manager использует ATR-based SL = Entry − 2×ATR. **Проблема:** Supertrend = HighestHigh − 3×ATR(10) — это по сути Chandelier Exit. При одновременном использовании:
- ATR-based SL (фиксированный при входе) vs Supertrend (динамический)
- Два стопа могут конфликтовать: какой срабатывает первым?
- Если Supertrend «шире» (3×ATR vs 2×ATR для SL) → SL первым → Supertrend бесполезен
- Если Supertrend «теснее» → преждевременный выход из тренда

**Рекомендация:**
- **Вариант А (предпочтительный):** Supertrend = primary trailing stop. ATR-based SL используется только как initial stop до активации trailing. После переключения: Supertrend управляет, ATR-SL отключается.
- **Вариант Б:** Оставить только ATR-based SL/TP (k_SL = 2.0, k_TP = 3.0), убрать Supertrend из функционала Risk Manager. Supertrend остаётся как signal indicator, не stop.

```
Реализация (Вариант А):
  if not trailing_active:
      active_stop = ATR_SL    // фиксированный при входе
  else:
      active_stop = max(ATR_SL, Supertrend_value)  // Supertrend берёт управление
      // Для SHORT: active_stop = min(ATR_SL, Supertrend_value)
```

**Статус:** Требует согласования с Агентом 1.

---

### CONFLICT-002: Parabolic SAR acceleration — риск whipsaw на крипте

**Кому:** Агент 1 (Trend)  
**Серьёзность:** ВЫСОКАЯ  
**Описание:**

Parabolic SAR с параметрами (0.02, 0.2) имеет жёсткое ускорение: шаг растёт на 0.02 каждый бар, максимум 0.2. На крипте с длинными wicks (тенями) SAR «прыгает» между направлениями → серия ложных выходов → **накопленные убытки от whipsaw могут превысить 15% MaxDD threshold**.

Пример: BTC 1H, флэт 5% диапазон, 10 дней:
```
SAR flip #1: Long → Short, убыток 1: 1.2%
SAR flip #2: Short → Long, убыток 2: 0.8%
...
SAR flip #8: накопленный убыток: ~8%
```

При 8 flip за 10 дней → ~8% убыток **только от whipsaw**, не считая остальных.

**Рекомендация:**
- **SAR НЕ должен быть primary exit signal.** Только secondary confirmation.
- SAR flip + Supertrend flip **одновременно** = сильный сигнал.
- SAR flip **один** = игнорировать.
- Добавить фильтр: SAR flip действителен только если ADX > 25.

```
Разворотный сигнал = SAR_flip AND Supertrend_flip AND ADX > 25
Один SAR_flip без подтверждения = НЕ ТОРГОВАТЬ
```

**Статус:** ⛔ **КРИТИЧЕСКИЙ КОНФЛИКТ.** Если Агент 1 использует SAR как primary exit — это создаёт фатальный риск просадки через whipsaw. Требуется немедленное изменение: SAR только как confirmation.

---

### CONFLICT-003: Bollinger Squeeze → Breakout может быть ложным

**Кому:** Агент 4 (Volatility)  
**Серьёзность:** НИЗКАЯ  
**Описание:**

Bollinger Squeeze (сужение полос) используется как предвестник импульса. Но на крипте ~40% squeeze'ей дают ложные breakout'ы. Если бот входит по squeeze breakout без дополнительного подтверждения → убытки.

**Рекомендация:**
- Squeeze breakout подтверждается: (1) объём > 1.5× average, (2) ADX > 20, (3) закрытие за пределами Keltner Channel.
- Без тройного подтверждения → squeeze игнорируется.

**Статус:** Низкий. Агент 4 уже использует Keltner как подтверждение.

---

### CONFLICT-004: EMA crossover во флэте — whipsaw через MaxDD

**Кому:** Агент 1 (Trend)  
**Серьёзность:** СРЕДНЯЯ  
**Описание:**

EMA20/50 crossover без ADX фильтра генерирует ~60% ложных сигналов во флэте. Каждый ложный сигнал = SL hit = 2% потерь. При 5 ложных crossover за неделю → 10% потерь → **приближение к MaxDD Circuit Breaker**.

**Рекомендация:**
- Агент 1 уже выбрал ADX > 25 как фильтр — это правильно.
- Дополнительно: EMA crossover действителен только если |EMA20 − EMA50| > 0.5% от цены (минимальный gap).

**Статус:** Частично разрешён (ADX фильтр есть). Добавить минимальный gap.

---

### CONFLICT-005: Корреляция ATR(14) в Risk Manager и Агенте 4

**Кому:** Агент 4 (Volatility)  
**Серьёзность:** ИНФОРМАЦИЯ  
**Описание:**

Risk Manager и Агент 4 оба используют ATR(14). Убедиться, что:
- Используется **один и тот же** ATR (Wilder's smoothing), не два разных расчёта
- Период одинаковый: 14
- Обновление синхронное на каждой свече

**Рекомендация:** Единый ATR-сервис. Risk Manager потребляет, не пересчитывает.

**Статус:** Процессуальный. Архитектурное решение.

---

## 6. Итоговая конфигурация

```yaml
# === Риск-менеджмент (MVP v0.1) ===
risk:
  # --- Primary: Position Sizing & Stops ---
  sl_atr_multiplier: 2.0           # k_SL для LONG
  sl_atr_multiplier_short: 1.5     # k_SL для SHORT (падения быстрее)
  tp_atr_multiplier: 3.0           # k_TP (R:R = 1.5 для long, 2.0 для short)
  atr_period: 14                   # период ATR (Wilder's smoothing)
  
  # --- Primary: Fractional Kelly ---
  kelly_fraction: 0.5              # Half-Kelly
  kelly_cap: 0.25                  # максимум 25% капитала
  kelly_min_trades: 30             # минимум сделок для расчёта Kelly
  max_position_pct: 0.05           # 5% от депозита на сделку (absolute cap)
  
  # --- Primary: Circuit Breaker ---
  max_drawdown_warning: 0.12       # Pre-warning: позиция × 0.5
  max_drawdown_halt: 0.15          # Full Stop: halt до 00:00 UTC
  flash_crash_threshold: 0.08      # 8% за свечу → закрыть всё market order
  cb_cooldown_hours: 24            # cooldown после Full Stop
  
  # --- Secondary: VaR/CVaR ---
  var_confidence: 0.95             # 95% доверительный интервал
  var_window: 30                   # окно в днях
  cvar_halt_threshold: 0.10        # CVaR > 10% → halt
  cvar_reduce_threshold: 0.05      # CVaR > 5% → reduce position × 0.5
  
  # --- Gate: Risk of Ruin ---
  max_risk_of_ruin: 0.05           # P_ruin > 5% → reject strategy
  
  # --- Supertrend integration (Conflict-001) ---
  trailing_mode: "supertrend_activated"
  # initial_stop = ATR_SL, после активации trailing → Supertrend
  
  # --- SAR integration (Conflict-002) ---
  sar_confirmation_only: true      # SAR только подтверждение, не primary exit
```

---

## 7. Rust-специфика

### 7.1 Общие принципы

Все расчёты риск-менеджмента — **горячий путь** (hot path). На каждом тике:
1. Обновить ATR
2. Пересчитать SL/TP
3. Проверить MaxDD
4. Проверить VaR/CVaR (раз в день)
5. Обновить Kelly (раз в N сделок)

### 7.2 ATR (уже в секции 1.1)

```rust
// O(1) обновление, zero-alloc
pub struct ATR { period: usize, smoothed: f64, count: usize }
```

### 7.3 Fractional Kelly

```rust
pub struct KellySizer {
    window: Vec<TradeResult>,  // ring buffer
    capacity: usize,
}

pub struct TradeResult {
    pub pnl: f64,
    pub is_win: bool,
}

impl KellySizer {
    pub fn new(capacity: usize) -> Self {
        Self { window: Vec::with_capacity(capacity), capacity }
    }

    pub fn add_trade(&mut self, result: TradeResult) {
        if self.window.len() >= self.capacity {
            self.window.remove(0);
        }
        self.window.push(result);
    }

    pub fn calc_fraction(&self, fraction: f64, cap: f64) -> f64 {
        if self.window.len() < 30 { return 0.02; } // fallback: 2% fixed

        let wins: Vec<_> = self.window.iter().filter(|t| t.is_win).collect();
        let losses: Vec<_> = self.window.iter().filter(|t| !t.is_win).collect();

        if losses.is_empty() { return cap; }

        let w = wins.len() as f64 / self.window.len() as f64;
        let avg_win: f64 = wins.iter().map(|t| t.pnl).sum::<f64>() / wins.len() as f64;
        let avg_loss: f64 = losses.iter().map(|t| t.pnl.abs()).sum::<f64>() 
            / losses.len() as f64;

        let r = avg_win / avg_loss;
        let kelly = (w * r - (1.0 - w)) / r;

        (kelly * fraction).max(0.0).min(cap)
    }
}
```

### 7.4 Circuit Breaker

```rust
pub struct CircuitBreaker {
    peak_capital: f64,
    state: CBState,
    triggered_at: Option<std::time::Instant>,
    cooldown_hours: u64,
}

#[derive(Clone, Copy, PartialEq)]
pub enum CBState {
    Normal,
    PreWarning,
    FullStop,
}

impl CircuitBreaker {
    pub fn check(&mut self, current_capital: f64) -> CBState {
        if current_capital > self.peak_capital {
            self.peak_capital = current_capital;
        }

        let dd = (self.peak_capital - current_capital) / self.peak_capital;

        // Cooldown check
        if self.state == CBState::FullStop {
            if let Some(t) = self.triggered_at {
                if t.elapsed().as_secs() > self.cooldown_hours * 3600 {
                    self.state = CBState::Normal;
                } else {
                    return CBState::FullStop;
                }
            }
        }

        self.state = if dd >= 0.15 {
            self.triggered_at = Some(std::time::Instant::now());
            CBState::FullStop
        } else if dd >= 0.12 {
            CBState::PreWarning
        } else {
            CBState::Normal
        };

        self.state
    }

    pub fn position_multiplier(&self) -> f64 {
        match self.state {
            CBState::Normal => 1.0,
            CBState::PreWarning => 0.5,
            CBState::FullStop => 0.0,
        }
    }
}
```

### 7.5 VaR/CVaR (ежедневный)

```rust
/// Historical VaR и CVaR — вызывается раз в день, не hot path
pub fn calc_var_cvar(pnl_window: &[f64], alpha: f64) -> (f64, f64) {
    let mut sorted = pnl_window.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let n = sorted.len();
    let index = alpha * (n - 1) as f64;
    let lower = index.floor() as usize;
    let upper = index.ceil() as usize;
    let frac = index - lower as f64;

    // VaR via linear interpolation
    let var_val = -(sorted[lower] + frac * (sorted[upper] - sorted[lower]));

    // CVaR: average of worst k observations
    let k = (alpha * n as f64).ceil() as usize;
    let cvar_val = if k > 0 {
        -(sorted[..k].iter().sum::<f64>() / k as f64)
    } else {
        var_val
    };

    (var_val, cvar_val)
}
```

### 7.6 Risk of Ruin (gate, не hot path)

```rust
pub fn risk_of_ruin(
    win_rate: f64,
    avg_win: f64,
    avg_loss: f64,
    capital: f64,
    risk_per_trade: f64,
) -> f64 {
    let edge = win_rate * avg_win - (1.0 - win_rate) * avg_loss;
    if edge <= 0.0 { return 1.0; }
    
    let ratio = edge / risk_per_trade;
    let base = (1.0 - ratio) / (1.0 + ratio);
    let exponent = capital / risk_per_trade;
    
    base.powf(exponent)
}
```

---

## Итоговая сводка

### Выбранные инструменты

| Приоритет | Инструмент | Роль | Параметры |
|-----------|-----------|------|-----------|
| **PRIMARY** | ATR-based SL/TP + Position Size | Стопы, тейки, размер | k_SL=2.0/1.5, k_TP=3.0, MaxPct=5% |
| **PRIMARY** | Fractional Kelly (Half-Kelly) | Оптимальный position size | f=0.5, cap=25%, min 30 trades |
| **PRIMARY** | MaxDD Circuit Breaker | Emergency stop | 12% warn, 15% halt, 8% flash |
| SECONDARY | CVaR / Expected Shortfall | Tail risk monitoring | >10% halt, >5% reduce |
| SECONDARY | Historical VaR (95%) | Daily monitoring | >5% warning |
| GATE | Risk of Ruin | Pre-trade validation | >5% reject |

### Отклонённые

Parametric VaR, Cornish-Fisher VaR, Monte Carlo VaR, Fixed Fraction, Full Kelly, Optimal f, Trailing Stop (fixed %), Chandelier Exit, Dynamic Stops (HMM), Portfolio VaR, Correlation Hedging, % Volatility Sizing, GARCH Risk Adjustment.

### Конфликты

| ID | Кому | Серьёзность | Описание | Решение |
|----|------|------------|---------|---------|
| C-001 | Агент 1 | СРЕДНЯЯ | Supertrend + ATR-SL дублирование | Supertrend = trailing после активации, ATR-SL = initial |
| C-002 | Агент 1 | **КРИТИЧЕСКИЙ** | SAR как primary exit → whipsaw → фатальная просадка | SAR только подтверждение. SAR + Supertrend + ADX. |
| C-003 | Агент 4 | НИЗКАЯ | Bollinger Squeeze ложные breakout | Тройное подтверждение (vol + ADX + Keltner) |
| C-004 | Агент 1 | СРЕДНЯЯ | EMA crossover whipsaw во флэте | ADX > 25 + минимальный gap EMA |
| C-005 | Агент 4 | ИНФО | ATR двойной расчёт | Единый ATR-сервис |

### Рекомендации для других агентов

1. **Агент 1 (Trend):** ⛔ **СРОЧНО** пересмотреть роль Parabolic SAR. Только как confirmation, не primary exit. Без этого — фатальный риск через whipsaw.

2. **Агент 4 (Volatility):** Убедиться что ATR используется единообразно. Добавить тройное подтверждение для Bollinger Squeeze.

3. **Агент 2 (Oscillators):** Убедиться что RSI/MACD сигналы не отменяют Circuit Breaker. Risk Manager имеет veto power.

4. **Агент 6 (Stats):** HMM (v0.3) будет интегрирован с Dynamic Stops. Подготовить interface: `hmm_state() -> {Bull, Bear, Range}`.

---

*Документ: 05-risk-management.md*  
*Агент: Risk Management (Agent 5)*  
*Статус: ФИНАЛЬНЫЙ — готов к интеграции*
