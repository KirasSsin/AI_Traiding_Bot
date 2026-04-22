# Агент 12: Bot Specification & MVP Logic

**Дата:** 17 апреля 2026  
**Назначение:** Полная спецификация логики криптовалютного торгового бота — MVP и production.  
**Исходники:** Trading Bot Specification.md, Research Indicators.md

---

## 1. MVP-версия

### Основная идея

MVP-бот реализует простые алгоритмы скользящих средних и осцилляторов для пары BTC/USDT. В основе — классические индикаторы (EMA, RSI, MACD), сигналы на основе пересечений или выходов за пороги, базовый риск-менеджмент.

### Архитектура модулей

```
Data Collector → Signal Generator → Risk Manager → Order Executor → Logger
```

| Модуль | Назначение | MVP реализация |
|--------|-----------|---------------|
| **Data Collector** | Получает и кэширует рыночные данные | Binance WebSocket + REST, ring buffer 1000 bars |
| **Signal Generator** | Вычисляет индикаторы, генерирует сигналы | EMA crossover + ADX filter + RSI confirmation |
| **Risk Manager** | Оценивает риски, фильтрует опасные сделки | ATR-SL/TP, Half-Kelly, MaxDD Circuit Breaker |
| **Order Executor** | Отправляет ордера на биржу | OCO orders через Binance REST API |
| **Logger** | Логирование сигналов, сделок, баланса | Structured logging → QuestDB + файл |

### Пайплайн сигналов (упрощённый)

```
Рынок → Data Collector читает последнюю свечу/ленту сделок
  → Signal Generator обновляет индикаторы
  → При выполнении триггерного условия формируется торговый сигнал
  → Risk Manager оценивает по капиталу/риск-параметрам
  → Если всё в порядке, Order Executor размещает ордер
  → Позиция открыта/закрыта → данные сохраняются в лог
```

---

## 2. Формулы индикаторов (базовый набор)

### SMA (Simple Moving Average)

```
SMA_t = (1/n) × Σ_{i=0}^{n-1} p_{t-i}
```

### EMA (Exponential Moving Average)

```
EMA_t = p_t × α + EMA_{t-1} × (1 - α)
α = 2 / (n + 1)
```

### RSI (Relative Strength Index)

```
RS = EMA_U / EMA_D       (сглаженные средние приростов и убытков)
RSI = 100 - 100 / (1 + RS)
Пороги: > 70 перекуплен, < 30 перепродан
```

### MACD

```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(MACD Line, 9)
Histogram = MACD Line - Signal Line
```

### Bollinger Bands

```
Upper = SMA(20) + 2 × σ(20)
Lower = SMA(20) - 2 × σ(20)
где σ = стандартное отклонение за N периодов
```

### ATR (Average True Range)

```
TrueRange = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
ATR = EMA(TrueRange, 14)
```

---

## 3. Сигнальная логика (MVP)

### Primary Signal: EMA Crossover

```
LONG:   EMA(20) > EMA(50) AND prev_EMA(20) <= prev_EMA(50)
SHORT:  EMA(20) < EMA(50) AND prev_EMA(20) >= prev_EMA(50)
FLAT:   иначе
```

### Filter 1: ADX Trend Strength

```
ADX(14) > 25 → тренд существует, сигнал валиден
ADX(14) < 25 → флэт, сигнал блокируется
```

### Filter 2: RSI Confirmation

```
Для LONG:  RSI(14) < 70 (не перекуплен)
Для SHORT: RSI(14) > 30 (не перепродан)
```

### Итоговый сигнал

```
Signal = Primary × Filter_ADX × Filter_RSI

LONG если:   EMA crossover up AND ADX > 25 AND RSI < 70
SHORT если:  EMA crossover down AND ADX > 25 AND RSI > 30
FLAT иначе
```

---

## 4. Риск-менеджмент (MVP)

### Position Sizing

```
PositionSize = min(Half_Kelly, MaxPct) × Capital / SL_distance
MaxPct = 0.05 (5% капитала на сделку)
```

### Stop Loss / Take Profit

```
LONG:  SL = Entry - 2 × ATR(14), TP = Entry + 3 × ATR(14)
SHORT: SL = Entry + 1.5 × ATR(14), TP = Entry - 3 × ATR(14)
```

### Circuit Breaker

```
MaxDD L1: 12% → PositionSize × 0.5
MaxDD L2: 15% → HALT (4 часа или новый день)
Flash crash: PnL за свечу < -8% → немедленный HALT
```

---

## 5. Probabilistic & Stochastic Models (энциклопедия)

### GBM (Geometric Brownian Motion)

```
dS_t = μ S_t dt + σ S_t dW_t

Решение (Itô):
S_t = S_0 × exp((μ - σ²/2)t + σ W_t)

Используется для: симуляции цен, расчёт VaR, ценообразование опционов
```

### HMM (Hidden Markov Model)

HMM применяют для обнаружения рыночных режимов (бычий/медвежий тренд). Скрытые состояния — режимы рынка, наблюдаемые переменные — котировки.

```
Параметры: π (начальное распределение), A (матрица переходов), B (эмиссии)
Обучение: алгоритм Баума-Велша (EM)
Декодирование: алгоритм Витерби
Наблюдение: x_t = log(P_t / P_{t-1}) — лог-доходность
```

---

## 6. Time Series Models (энциклопедия)

### ARIMA(p,d,q)

```
Φ(B)(1-B)^d y_t = c + Θ(B)ε_t

где B — оператор лага, d — порядок дифференцирования
Для крипто-цен: d=1 (первая разность), d=0 для лог-доходностей
```

### GARCH(1,1)

```
σ²_t = ω + α × u²_{t-1} + β × σ²_{t-1}

где α+β ≈ 0.97 для крипты (сильная кластеризация волатильности)
Используется для: адаптивный стоп-лосс, опционное ценообразование
```

### STL Decomposition

```
y_t = Trend_t + Seasonal_t + Residual_t

Seasonal–Trend decomposition using Loess
Полезно для: анализ регулярных циклов, удаление сезонности
```

---

## 7. Order Flow Analysis (энциклопедия)

### Time & Sales (лента сделок)

Каждая выполненная сделка: объём, цена, время. Анализ потока покупок/продаж в реальном времени.

### Footprint Charts (кластерные принты)

Агрегация объёмов заявок/сделок по ценовым уровням в каждом баре. Позволяет найти «сильные уровни» спроса/предложения.

### Order Book Analysis

Текущие лимитные ордера в глубине рынка. Наблюдая быстрые изменения спроса/предложения (например, внезапные поглощения крупных заявок), можно предсказывать краткосрочную реакцию цены.

---

## 8. ML Methods (энциклопедия)

### Supervised Learning

Регрессия и классификация на исторических данных (цены, индикаторы → будущее движение). Примеры: линейные модели, случайный лес, градиентный бустинг, нейросети.

### Reinforcement Learning

Агент получает состояние рынка и выбирает действие (buy/sell/hold), получает награду (PnL). Q-обучение, Policy Gradients, Deep RL (DQN, DDQN).

### Online Learning

Модели, обновляемые «на ходу» без полного переобучения (SGD-регрессия, Hoeffding tree). Полезны при непрерывном потоке данных.

### Hyperparameter Optimization

- Grid Search — полный перебор по сетке
- Random Search — случайный перебор (эффективнее grid)
- Bayesian Optimization — Gaussian Process для навигации по пространству параметров

---

## 9. Config

```yaml
bot:
  pair: "BTCUSDT"
  timeframe: "1h"
  mode: "paper"  # paper / live
  
indicators:
  ema_fast: 20
  ema_slow: 50
  rsi_period: 14
  macd: [12, 26, 9]
  atr_period: 14
  bollinger: [20, 2]
  adx_period: 14
  adx_threshold: 25

signal:
  primary: "ema_crossover"
  filters: ["adx_trend", "rsi_confirmation"]
  
risk:
  k_sl: 2.0
  k_tp: 3.0
  kelly_fraction: 0.5
  max_pct_per_trade: 0.05
  maxdd_warning: 0.12
  maxdd_halt: 0.15
  flash_crash_pct: 0.08
```