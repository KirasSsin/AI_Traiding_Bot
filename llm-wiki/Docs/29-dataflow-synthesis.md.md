# Документ 29: Синтез Data Flow и Торговой Логики

> **Мета-агент 29: Data Flow & Trading Logic Synthesis**
> Дата: 2026-04-17
> Назначение: полная карта потока данных от WebSocket-тика до PnL, иерархия сигналов, конфликт-резолюция, state machine ордеров, конкретная стратегия v0.1.
> Источники: Trading Bots and Indicators.md, Xiaomi MiMo Studio Dataflow.md, Trading Bot Specification.md, + 7 выходных документов агентов 01–16.

---

## Содержание

1. [Полный Data Flow Pipeline](#1-полный-data-flow-pipeline)
2. [Signal Hierarchy (Иерархия сигналов)](#2-signal-hierarchy)
3. [Conflict Resolution (Разрешение конфликтов)](#3-conflict-resolution)
4. [State Machine: Order Lifecycle](#4-state-machine-order-lifecycle)
5. [Стратегия v0.1: RSI + EMA Crossover — полный цикл](#5-стратегия-v01-rsi--ema-crossover)
6. [Конфигурация (config.yaml)](#6-конфигурация)
7. [Латентность и производительность](#7-латентность-и-производительность)
8. [Сводная матрица индикаторов по слоям](#8-сводная-матрица-индикаторов)

---

## 1. Полный Data Flow Pipeline

### 1.1 Архитектура сверху вниз

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Binance WebSocket                               │
│              wss://fstream.binance.com/ws/btcusdt@aggTrade             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ JSON: {e,p,q,T,m}
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 1: SOURCE LAYER (Парсинг тиков)                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────────────┐  │
│  │ JSON → Tick   │  │ Валидация     │  │ Decimal конвертация        │  │
│  │ {symbol,price,│  │ полей, ts,    │  │ price,volume → Decimal     │  │
│  │  volume,side, │  │ дедуп tradeId │  │ (не float!)                │  │
│  │  timestamp}   │  │               │  │                            │  │
│  └───────┬───────┘  └───────────────┘  └────────────────────────────┘  │
│          │ 5 мс                                                         │
└──────────┼──────────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 2: AGGREGATION LAYER (Агрегация в бары)                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│  │ Volume Bars      │  │ Time Bars 1m     │  │ Time Bars 1h       │    │
│  │ порог 100K USD   │  │ 60 сек интервал  │  │ 3600 сек интервал  │    │
│  │ VWAP за бар      │  │ OHLCV            │  │ OHLCV              │    │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬───────────┘    │
│           │ 0.05 мс             │                      │                │
└───────────┼─────────────────────┼──────────────────────┼────────────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 3: STORAGE LAYER (Хранение)                                      │
│  ┌──────────────────────────┐  ┌─────────────────────────────────────┐ │
│  │ Parquet (data/{symbol}/  │  │ TimescaleDB                         │ │
│  │   {bar_type}/YYYY-MM-DD) │  │ hypertable: ohlcv_1m, ohlcv_1h     │ │
│  │   snappy compression     │  │ idx: (symbol, time DESC)            │ │
│  │   batch 1000 строк       │  │ batch insert 100 строк / 1 сек     │ │
│  └──────────────────────────┘  └─────────────────────────────────────┘ │
│  (Асинхронно, не блокирует pipeline)                                    │
└─────────────────────────────────────────────────────────────────────────┘
           │
           │ 1m TimeBar (главный поток)
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 4: INDICATOR LAYER (Индикаторы)                                  │
│                                                                         │
│  Порядок вычисления (каждый O(1) на бар):                              │
│                                                                         │
│  4a. TREND (вес 0.30):                                                  │
│      ├─ EMA(20)  ← close                                               │
│      ├─ EMA(50)  ← close                                               │
│      ├─ VWAP     ← typical_price × volume (кумулятивно, сброс 00:00)  │
│      ├─ Supertrend(10, 3) ← ATR уже есть                              │
│      └─ ADX(14)  ← High, Low, Close                                    │
│                                                                         │
│  4b. MOMENTUM (вес 0.25):                                               │
│      ├─ RSI(14)  ← close (Wilder smoothing)                            │
│      ├─ MACD(12,26,9) ← EMA12, EMA26, Signal EMA9                     │
│      ├─ StochasticRSI(14,14,3,3) ← RSI → Stoch → K/D                 │
│      ├─ Fisher Transform(9) ← High, Low                                │
│      └─ CCI(20) ← typical_price, SMA, Mean Deviation                  │
│                                                                         │
│  4c. VOLATILITY (вес 0.10):                                            │
│      ├─ ATR(14) ← True Range                                           │
│      └─ Bollinger Bands(20,2) ← SMA ± 2σ                              │
│                                                                         │
│  4d. VOLUME (вес 0.20):                                                 │
│      ├─ CVD ← signed volume (tick rule, обновляется на каждый тик)     │
│      ├─ MFI(14) ← typical_price × volume                               │
│      └─ OBV ← кумулятивный volume-дельта (для дивергенций)             │
│                                                                         │
│  4e. CRYPTO-SPECIFIC (вес 0.15):                                        │
│      ├─ Open Interest ← REST API каждые 60 сек                         │
│      └─ Funding Rate ← REST API каждые 60 сек                          │
│                                                                         │
│  4f. RISK METRICS (отдельно, раз в час):                                │
│      ├─ Sharpe(rolling 30d)                                             │
│      ├─ VaR(95%, historical)                                            │
│      └─ CVaR(95%)                                                       │
│                                                                         │
│  Выход: IndicatorSnapshot (50+ полей)                                   │
│  Латентность: ≤ 2 мс                                                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 5: SIGNAL LAYER (Генерация сигналов)                             │
│                                                                         │
│  Этап 5a: Нормализация в баллы [-1, +1]                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ EMA cross:    +1 если EMA20 > EMA50, −1 если <                  │   │
│  │ VWAP:         +1 если close > VWAP                               │   │
│  │ Supertrend:   +1 если direction = 1 (бычий)                     │   │
│  │ RSI:          (RSI − 50) / 50, клип в [−1, +1]                 │   │
│  │ MACD hist:    clip(histogram / atr, −1, +1)                     │   │
│  │ Bollinger:    (close − mid) / (upper − lower) × 2, clip         │   │
│  │ CVD:          sign(delta_CVD) × min(1, |delta| / threshold)     │   │
│  │ MFI:          (MFI − 50) / 50, clip                             │   │
│  │ OI:           sign(delta_OI) × min(1, |delta| / threshold)      │   │
│  │ Funding:      clip(funding_rate / max_funding, −1, +1)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Этап 5b: Агрегация по категориям                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Trend:      0.30 × mean(EMA, VWAP, Supertrend)                 │   │
│  │ Momentum:   0.25 × mean(RSI, MACD, StochRSI, Fisher, CCI)      │   │
│  │ Volatility: 0.10 × mean(Bollinger_position)                    │   │
│  │ Volume:     0.20 × mean(CVD, MFI)                              │   │
│  │ Crypto:     0.15 × mean(OI, Funding)                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  composite = Σ(category_weight × category_score)                       │
│                                                                         │
│  Этап 5c: Булевы условия                                               │
│  IF composite > +0.30 AND confirming_categories >= 3 → BUY             │
│  IF composite < −0.30 AND confirming_categories >= 3 → SELL            │
│  ELSE → HOLD                                                           │
│                                                                         │
│  Фильтры:                                                              │
│  ├─ RSI < 85 (не покупать при экстремальной перекупленности)           │
│  ├─ RSI > 15 (не продавать при экстремальной перепроданности)          │
│  ├─ ATR > min_threshold (волатильность достаточна)                     │
│  └─ Cooldown: не более 1 сигнала в том же направлении за 5 мин        │
│                                                                         │
│  Выход: SignalDecision {action, confidence, composite_score, ...}      │
│  Латентность: ≤ 1 мс                                                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 6: RISK LAYER (Управление рисками)                               │
│                                                                         │
│  ┌──────────────────────────────┐                                       │
│  │ 6a. VETO CHECK               │  ← Risk Manager имеет АБСОЛЮТНОЕ    │
│  │ ┌──────────────────────────┐ │    право вето на любой сигнал        │
│  │ │ Circuit Breaker:         │ │                                       │
│  │ │ ├─ MaxDD >= 15%? → HALT │ │                                       │
│  │ │ ├─ MaxDD >= 12%? → ×0.5 │ │                                       │
│  │ │ ├─ Flash crash 8%/bar?  │ │                                       │
│  │ │ │  → CLOSE ALL          │ │                                       │
│  │ │ ├─ Trades today >= 50?  │ │                                       │
│  │ │ │  → REJECT             │ │                                       │
│  │ │ ├─ Open positions >= 5? │ │                                       │
│  │ │ │  → REJECT             │ │                                       │
│  │ │ └─ API errors > 5/10m?  │ │                                       │
│  │ │    → PAUSE 15min        │ │                                       │
│  │ └──────────────────────────┘ │                                       │
│  └──────────────────────────────┘                                       │
│           │                                                              │
│           │ (approved)                                                   │
│           ▼                                                              │
│  ┌──────────────────────────────┐                                       │
│  │ 6b. POSITION SIZING          │                                       │
│  │ Fractional Kelly (Half):     │                                       │
│  │   kelly = W×R − L / R       │                                       │
│  │   fraction = kelly × 0.25    │  ← Quarter-Kelly для крипты          │
│  │   position = balance ×       │                                       │
│  │     fraction × confidence    │                                       │
│  │   Cap: min(5%, fraction)     │                                       │
│  │   Min: 100 USD               │                                       │
│  └──────────────────────────────┘                                       │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────┐                                       │
│  │ 6c. SL/TP CALCULATION        │                                       │
│  │ SL = Entry ± k_SL × ATR(14) │  k_SL = 2.0 (long), 1.5 (short)     │
│  │ TP = Entry ± k_TP × ATR(14) │  k_TP = 3.0 (R:R = 1.5:1)          │
│  │ Trailing: Supertrend после   │                                       │
│  │   активации trailing mode    │                                       │
│  └──────────────────────────────┘                                       │
│                                                                         │
│  Выход: RiskDecision {approved, position_size, SL, TP, ...}            │
│  Латентность: ≤ 5 мс                                                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ (if approved)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 7: EXECUTION LAYER (Исполнение ордеров)                          │
│                                                                         │
│  7a. Формирование ордера:                                               │
│      POST /fapi/v1/order                                                │
│      symbol, side, type(LIMIT/MARKET), quantity, price,                 │
│      timeInForce(GTC/IOC), newClientOrderId=bot_{timestamp}            │
│                                                                         │
│  7b. MVP: Market Order (простой)                                        │
│      → Гарантия fill, taker fee 0.04%                                   │
│                                                                         │
│  7c. Production: Limit Order + OCO                                      │
│      → Limit по цене, maker fee 0.02%                                   │
│      → OCO = TP limit + SL stop-loss                                    │
│                                                                         │
│  7d. Мониторинг:                                                        │
│      ├─ WebSocket user stream (listenKey) → мгновенные fills            │
│      └─ REST polling каждые 2 сек (fallback)                           │
│                                                                         │
│  7e. Таймаут: 60 сек для limit, затем cancel                           │
│                                                                         │
│  Выход: ExecutionResult {order_id, status, filled_price, commission}   │
│  Латентность: ≤ 200 мс (сеть)                                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 8: LOGGING LAYER (Логирование)                                   │
│                                                                         │
│  8a. Структурированный JSON-лог (stdout → Loki/Promtail)               │
│  8b. CSV торговый журнал (trades/trades_YYYY-MM-DD.csv)                │
│  8c. TimescaleDB: trade_metrics, system_metrics                        │
│  8d. Trace ID: сквозной идентификатор тик→бар→сигнал→ордер            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  СЛОЙ 9: REPORTING LAYER (Дашборд)                                     │
│  Streamlit + Plotly на порту 8501                                       │
│  ├─ Состояние системы (WebSocket, latency, circuit breakers)            │
│  ├─ Ценовой график + индикаторы + маркеры сделок                       │
│  ├─ P&L (кумулятивный, по сделкам, max drawdown)                       │
│  ├─ VaR / CVaR / Sharpe                                                 │
│  ├─ Журнал сделок (real-time таблица)                                   │
│  └─ Volume Profile (POC, Value Area)                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Общий бюджет латентности

| Слой | Операция | Бюджет | Кумулятив |
|------|----------|--------|-----------|
| 1. Source | JSON parse + validate + Decimal | 5 мс | 5 мс |
| 2. Aggregation | Tick → Bar update | 0.05 мс | 5.05 мс |
| 3. Storage | Async write (не блокирует) | 0 мс | 5.05 мс |
| 4. Indicators | Все 15+ индикаторов O(1) | 2 мс | 7.05 мс |
| 5. Signals | Нормализация + composite + решение | 1 мс | 8.05 мс |
| 6. Risk | Veto check + Kelly + SL/TP | 5 мс | 13.05 мс |
| 7. Execution | REST API roundtrip | 200 мс | 213 мс |
| 8. Logging | Async (buffered) | 0 мс | 213 мс |
| **Итого: тик → ордер** | | | **≈ 213 мс** |

**Целевая латентность: ≤ 500 мс.** Текущий бюджет имеет запас 287 мс.

---

## 2. Signal Hierarchy

### 2.1 Четырёхуровневая модель

Иерархия сигналов определяет порядок принятия решений: каждый уровень должен быть пройден, прежде чем сигнал будет передан дальше.

```
                    ┌──────────────────────┐
                    │  PRIMARY TREND       │  ← Определяет НАПРАВЛЕНИЕ
                    │                      │
                    │  EMA(20) > EMA(50)   │
                    │  EMA rising ≥ 2 bars │
                    │  Supertrend = BULL   │
                    └──────────┬───────────┘
                               │ direction = LONG
                               ▼
                    ┌──────────────────────┐
                    │  FILTER (сила)       │  ← Проверяет есть ли ТРЕНД
                    │                      │
                    │  ADX(14) > 25        │
                    │  VWAP: price > VWAP  │
                    │  KAMA: ER > 0.3      │  (v0.2+)
                    └──────────┬───────────┘
                               │ filter passed
                               ▼
                    ┌──────────────────────┐
                    │  CONFIRMATION        │  ← Подтверждает моментум
                    │  (осцилляторы)       │
                    │                      │
                    │  RSI(14) < 70        │  не перекуплен
                    │  MACD histogram > 0  │  моментум вверх
                    │  MFI(14) < 80        │  объёмный осциллятор
                    │  CCI(20) > -100      │  не в зоне перепродан
                    │  CVD растёт          │  давление покупателей
                    └──────────┬───────────┘
                               │ confirmation passed
                               ▼
                    ┌──────────────────────┐
                    │  TIMING (вход)       │  ← ТОЧНАЯ ТОЧКА ВХОДА
                    │                      │
                    │  StochRSI K > D      │  K пересекает D снизу
                    │  StochRSI из < 20    │  выход из перепродан
                    │  Fisher < −1.5       │  разворот снизу
                    │  и поворачивает вверх│
                    └──────────┬───────────┘
                               │ timing signal
                               ▼
                         ╔═══════════════╗
                         ║  EXECUTE BUY  ║
                         ╚═══════════════╝
```

### 2.2 Роли каждого модуля в иерархии

| Уровень | Модуль | Индикаторы | Роль | Пример условия |
|---------|--------|-----------|------|----------------|
| **PRIMARY** | Trend (Agent 01) | EMA(20/50), Supertrend, VWAP | Определяет НАПРАВЛЕНИЕ тренда | EMA20 > EMA50 AND rising |
| **FILTER** | Trend + Crypto | ADX(14), KAMA, OI regime | Проверяет НАЛИЧИЕ тренда и капитал | ADX > 25 AND OI regime bullish |
| **CONFIRMATION** | Oscillators (Agent 02) + Volume (Agent 03) | RSI, MACD, MFI, CCI, CVD | Подтверждает моментум и объём | RSI < 70 AND MACD hist > 0 AND CVD rising |
| **TIMING** | Oscillators (Agent 02) | StochRSI, Fisher | Точная точка входа | StochRSI K crosses D from oversold |

### 2.3 Почему именно такой порядок

**Тренд → Фильтр → Подтверждение → Тайминг** — потому что:

1. **Без направления бесполезно знать тайминг.** Осциллятор «покупай» в медвежьем тренде = потеря.
2. **Без силы тренда — шум.** EMA может кроссовернуть во флэте 5 раз за день. ADX > 25 фильтрует эти ложные сигналы.
3. **Без подтверждения — одиночный сигнал.** RSI < 30 один не гарантирует разворот. RSI < 30 + MFI < 20 + CVD растёт = тройное подтверждение.
4. **Тайминг — последний шаг.** StochRSI выход из зоны < 20 — это конкретная свеча для входа, не общий тренд.

### 2.4 Модуль-специфичные сигналы по фазам

| Фаза | PRIMARY | FILTER | CONFIRMATION | TIMING |
|------|---------|--------|-------------|--------|
| **v0.1** | EMA(20/50) crossover | ADX(14) > 25 | RSI(14) < 70 | — (простой вход по crossover) |
| **v0.2** | + Supertrend direction | + KAMA rising | + MACD histogram > 0 | + StochRSI K > D |
| **v0.3** | + Kumo position | + OI regime bullish | + CCI, CVD, MFI | + Fisher Transform |
| **v0.4** | + Ichimoku Tenkan/Kijun | + VPIN < 0.25 | + OBI > 0.3 | + Liquidation cascade completion |

---

## 3. Conflict Resolution

### 3.1 Принцип: Veto System

**Risk Manager имеет абсолютное право вето.** Никакой сигнал не может быть исполнен, если Risk Manager его отклонил.

```
Signal Engine: "BUY BTC"
         │
         ▼
Risk Manager: check ──→ approved: true/false
         │                        │
         ▼                        ▼
    Execution               REJECTED
                              reason: "MaxDD 15%"
```

### 3.2 Иерархия разрешения конфликтов

| Приоритет | Модуль | Право | Пример |
|-----------|--------|-------|--------|
| **1 (высший)** | Risk Manager | Veto любой сигнал | Circuit breaker сработал → reject |
| **2** | Trend | Определяет направление | EMA bearish → не покупать, даже если RSI < 20 |
| **3** | Oscillators | Фильтрует перекупленность | RSI > 85 → не покупать, даже если EMA bullish |
| **4** | Volume | Подтверждает/опровергает | CVD падает при растущей цене → ослабить сигнал |
| **5** | Crypto | Контарианский фильтр | FR Z-score > +2 → уменьшить позицию 50% |
| **6 (низший)** | Timing | Только тайминг | StochRSI < 20 без PRIMARY → не торговать |

### 3.3 Конкретные конфликты и решения

#### CONFLICT-001: EMA bullish vs RSI overbought
```
Ситуация: EMA20 > EMA50 (бычий тренд), но RSI = 78 (перекуплен)
Решение:   Oscillators (уровень 3) выше Trend (уровень 2)?
НЕТ.       Trend определяет НАПРАВЛЕНИЕ. RSI только ФИЛЬТР.
Результат: HOLD. Не покупать при RSI > 70, даже если тренд вверх.
           Ждать RSI < 70 для повторного входа.
```

#### CONFLICT-002: CVD растёт vs MFI > 80
```
Ситуация: CVD показывает давление покупателей, но MFI > 80 (перекуплен)
Решение:   MFI (нормализованный) приоритетнее CVD (сырой).
Результат: Не входить. MFI > 80 = объёмное подтверждение перекупленности.
```

#### CONFLICT-003: Supertrend flip vs SAR flip (не одновременно)
```
Ситуация: Supertrend flipнул в bearish, SAR ещё не flipнул
Решение:   Supertrend primary (ATR-based, устойчив к wicks).
           SAR только confirmation (Conflict-002 из Agent 05).
Результат: Подавить. Ждать двойной flip (Supertrend + SAR) для reversal.
```

#### CONFLICT-004: Trend bullish vs Funding Rate Z-score > +2.0
```
Ситуация: Все индикаторы говорят BUY, но FR Z-score = +2.5 (экстремальная перекупленность)
Решение:   Crypto (уровень 5) не может veto, но может уменьшить позицию.
Результат: BUY с position_size × 0.5. Не veto, но уменьшенная экспозиция.
```

#### CONFLICT-005: Все индикаторы противоречивы
```
Ситуация: Trend = BUY, Momentum = SELL, Volume = HOLD
Решение:   composite_score ≈ 0 → правило: |composite| < 0.30 → HOLD
Результат: HOLD. Не торговать при конфликте ≥ 2 категорий.
```

### 3.4 Правила приоритизации (decision matrix)

| Сценарий | Действие | Обоснование |
|----------|----------|-------------|
| Risk veto | REJECT | Абсолютный приоритет |
| PRIMARY + FILTER + CONFIRMATION + TIMING | EXECUTE (полноразмерный) | Все 4 уровня пройдены |
| PRIMARY + FILTER + CONFIRMATION (без TIMING) | EXECUTE (×0.7) | Нет точного тайминга |
| PRIMARY + FILTER (без CONFIRMATION) | HOLD | Нет подтверждения моментума |
| PRIMARY (без FILTER) | HOLD | Нет силы тренда |
| Только CONFIRMATION или TIMING | HOLD | Нет направления |
| Противоречие ≥ 2 категорий | HOLD | Нет консенсуса |

---

## 4. State Machine: Order Lifecycle

### 4.1 Состояния ордера

```
                              ┌─────────────┐
                              │   NEW       │  Создан локально,
                              │  (Pending)  │  ещё не отправлен
                              └──────┬──────┘
                                     │ POST /fapi/v1/order → 200
                                     ▼
                              ┌─────────────┐
                              │ SUBMITTED   │  Отправлен на биржу,
                              │  (Sent)     │  ожидает подтверждение
                              └──────┬──────┘
                              ╱       │       ╲
                             ╱        │        ╲
                            ▼         │         ▼
                   ┌────────────┐     │    ┌────────────┐
                   │PARTIALLY   │     │    │  REJECTED  │
                   │FILLED      │     │    │  (Error)   │
                   └─────┬──────┘     │    └────────────┘
                         │            │
                    fill > 0      fill = qty
                         │            │
                         ▼            ▼
                   ┌─────────────────────┐
                   │     FILLED          │  Полностью исполнен
                   │   (Completed)       │
                   └────────┬────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │   TRADE LOGGED      │  Записан в CSV/DB,
                   │   (Recorded)        │  PnL рассчитан
                   └─────────────────────┘
```

### 4.2 Расширенная state machine (с отменами и таймаутами)

```
                              ┌─────────────┐
                    ┌─────────│   CREATED   │
                    │         └──────┬──────┘
                    │                │
                    │                │ submit()
                    │                ▼
                    │         ┌─────────────┐     ┌──────────────┐
                    │         │  SUBMITTED  │────→│   TIMEOUT    │
                    │         └──────┬──────┘     │ (60 сек)     │
                    │                │            └──────┬───────┘
                    │           ┌────┴────┐              │
                    │           │         │              ▼
                    │           │    fill │         ┌──────────┐
                    │      cancel        │         │ CANCEL   │──────┐
                    │           │         ▼         │ SENT     │      │
                    │           ▼   ┌──────────┐    └──────────┘      │
                    │    ┌──────────┐│ PARTIAL  │                     │
                    │    │ CANCELED ││ FILLED   │                     │
                    │    │          │└────┬─────┘                     │
                    │    └──────────┘     │ fill remaining            │
                    │                     ▼                           │
                    │              ┌───────────┐    ┌──────────────┐  │
                    │              │   FILLED  │    │ CANCELLED    │◀─┘
                    │              └─────┬─────┘    │ (final)      │
                    │                    │          └──────────────┘
                    │                    ▼
                    │              ┌───────────┐
                    └─────────────→│  LOGGED   │
                                   │ (recorded)│
                                   └───────────┘
```

### 4.3 Таблица переходов

| Текущее состояние | Событие | Новое состояние | Действия |
|-------------------|---------|-----------------|----------|
| CREATED | `submit()` | SUBMITTED | POST /fapi/v1/order, start timeout timer |
| CREATED | `cancel()` | CANCELLED | Удалить из очереди |
| SUBMITTED | Exchange `ACK` (status=NEW) | SUBMITTED | Обновить order_id |
| SUBMITTED | Exchange `FILL` (partial) | PARTIALLY_FILLED | Обновить filled_qty, filled_avg_price |
| SUBMITTED | Exchange `FILL` (full) | FILLED | Рассчитать commission, записать в log |
| SUBMITTED | Exchange `REJECT` | REJECTED | Логировать причину, уведомить оператора |
| SUBMITTED | Timeout (60 сек) | TIMEOUT → CANCEL SENT | DELETE /fapi/v1/order |
| PARTIALLY_FILLED | Exchange `FILL` (remaining) | FILLED | Рассчитать итоговую комиссию |
| PARTIALLY_FILLED | Timeout (60 сек) | CANCEL SENT | Отменить неисполненную часть |
| FILLED | `log_trade()` | LOGGED | Записать в CSV + DB + обновить PnL |
| CANCEL SENT | Exchange `ACK` cancel | CANCELLED | Логировать отмену |
| REJECTED | `log_error()` | LOGGED (error) | Логировать ошибку |

### 4.4 State machine код (упрощённый)

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OrderState {
    Created,          // Локально создан
    Submitted,        // Отправлен на биржу
    PartiallyFilled,  // Частично исполнен
    Filled,           // Полностью исполнен
    CancelSent,       // Запрос на отмену отправлен
    Cancelled,        // Отменён
    Rejected,         // Отклонён биржей
    Logged,           // Записан в журнал
}

pub struct Order {
    pub client_order_id: String,   // bot_{timestamp}
    pub exchange_order_id: Option<String>,
    pub symbol: String,
    pub side: Side,
    pub order_type: OrderType,
    pub quantity: Decimal,
    pub price: Option<Decimal>,    // None для Market
    pub state: OrderState,
    pub filled_qty: Decimal,
    pub filled_avg_price: Option<Decimal>,
    pub commission: Decimal,
    pub created_at: Instant,
    pub submitted_at: Option<Instant>,
    pub filled_at: Option<Instant>,
    pub stop_loss: Decimal,
    pub take_profit: Decimal,
    pub trace_id: String,          // Сквозной ID
}

impl Order {
    pub fn transition(&mut self, event: OrderEvent) -> Result<OrderState, OrderError> {
        self.state = match (self.state, event) {
            (Created,     OrderEvent::Submit)      => Submitted,
            (Created,     OrderEvent::Cancel)      => Cancelled,
            (Submitted,   OrderEvent::Ack { id })  => { self.exchange_order_id = Some(id); Submitted }
            (Submitted,   OrderEvent::Fill(p, q))  => self.apply_fill(p, q),
            (Submitted,   OrderEvent::Reject(r))   => { log::error!("Rejected: {r}"); Rejected }
            (Submitted,   OrderEvent::Timeout)     => CancelSent,
            (PartialFill, OrderEvent::Fill(p, q))  => self.apply_fill(p, q),
            (PartialFill, OrderEvent::Timeout)     => CancelSent,
            (CancelSent,  OrderEvent::CancelAck)   => Cancelled,
            (Filled,      OrderEvent::Log)         => Logged,
            (Rejected,    OrderEvent::Log)         => Logged,
            (Cancelled,   OrderEvent::Log)         => Logged,
            _ => return Err(OrderError::InvalidTransition(self.state, event)),
        };
        Ok(self.state)
    }

    fn apply_fill(&mut self, price: Decimal, qty: Decimal) -> OrderState {
        let total_value = self.filled_avg_price.unwrap_or_default() * self.filled_qty + price * qty;
        self.filled_qty += qty;
        self.filled_avg_price = Some(total_value / self.filled_qty);
        self.commission += price * qty * Decimal::from_str("0.0004").unwrap(); // taker
        if self.filled_qty >= self.quantity {
            self.filled_at = Some(Instant::now());
            OrderState::Filled
        } else {
            OrderState::PartiallyFilled
        }
    }
}
```

### 4.5 OCО (One-Cancels-Other) для SL/TP

```
После FILLED:
  ┌───────────────────────────────────────────────────┐
  │ OCO Order:                                        │
  │   Leg 1: LIMIT (Take Profit) = Entry + 3×ATR     │
  │   Leg 2: STOP_LOSS = Entry − 2×ATR               │
  │                                                   │
  │   Если Leg 1 fill → cancel Leg 2 → PnL = +3×ATR  │
  │   Если Leg 2 fill → cancel Leg 1 → PnL = −2×ATR  │
  └───────────────────────────────────────────────────┘
```

---

## 5. Стратегия v0.1: RSI + EMA Crossover

### 5.1 Описание стратегии

**Цель:** Простая, воспроизводимая стратегия для MVP. EMA crossover определяет направление, RSI фильтрует перекупленность/перепроданность.

**Пара:** BTC/USDT (Binance Futures USDⓈ-M)
**Таймфрейм:** 1 час (1H)
**Тип ордера:** Market order (MVP), Limit order (production)

### 5.2 Правила входа

#### LONG (покупка):
```
ВСЕ условия должны быть истинны одновременно:

1. EMA(20) > EMA(50)                           ← Primary: бычий тренд
2. EMA(20) > EMA(20, 1 бар назад)              ← Подтверждение: EMA растёт
3. ADX(14) > 25                                 ← Filter: тренд существует
4. RSI(14) < 70                                 ← Confirmation: не перекуплен
5. RSI(14) > 30                                 ← Confirmation: не в зоне перепродан
                                               (не ловить падающий нож)
6. Цена > VWAP(session)                         ← Filter: цена выше справедливой
7. ATR(14) > 0.5% от цены                      ← Volatility sufficient
```

#### SHORT (продажа):
```
1. EMA(20) < EMA(50)                           ← Primary: медвежий тренд
2. EMA(20) < EMA(20, 1 бар назад)              ← Подтверждение: EMA падает
3. ADX(14) > 25                                 ← Filter: тренд существует
4. RSI(14) > 30                                 ← Confirmation: не перепродан
5. RSI(14) < 70                                 ← Confirmation: не в зоне перекуплен
6. Цена < VWAP(session)                         ← Filter: цена ниже справедливой
7. ATR(14) > 0.5% от цены                      ← Volatility sufficient
```

### 5.3 Правила выхода

```
EXIT LONG:
  (a) SL: Entry − 2.0 × ATR(14)                ← ATR-based stop loss
  (b) TP: Entry + 3.0 × ATR(14)                ← ATR-based take profit
  (c) EMA(20) < EMA(50)                         ← Тренд сменился
  (d) RSI(14) > 85                              ← Экстремальная перекупленность

EXIT SHORT:
  (a) SL: Entry + 1.5 × ATR(14)
  (b) TP: Entry − 3.0 × ATR(14)
  (c) EMA(20) > EMA(50)
  (d) RSI(14) < 15                              ← Экстремальная перепроданность
```

### 5.4 Position sizing

```
До набора 30 сделок: Fixed Fraction = 2% от капитала
После 30 сделок:     Quarter-Kelly (f = 0.25)
Max position:        5% от капитала
```

### 5.5 Полный цикл: от свечи до PnL

Рассмотрим конкретный сценарий по шагам:

#### Шаг 1: Приходит свеча (1H bar closes)

```
Timestamp: 2026-04-17T14:00:00Z
OHLCV:
  Open:  67,000
  High:  67,350
  Low:   66,800
  Close: 67,280
  Volume: 1,245 BTC
  Quote Volume: 83,760,000 USDT
```

#### Шаг 2: Обновление индикаторов (~2 мс)

```python
# EMA
ema_20 = 0.095238 * 67280 + 0.904762 * prev_ema_20
# Result: ema_20 = 67,150

ema_50 = 0.039216 * 67280 + 0.960784 * prev_ema_50
# Result: ema_50 = 66,980

# RSI
change = 67280 - prev_close  # = +280
avg_gain = (prev_avg_gain * 13 + max(0, 280)) / 14
avg_loss = (prev_avg_loss * 13 + max(0, -280)) / 14  # = 0
RS = avg_gain / avg_loss
RSI = 100 - 100 / (1 + RS)
# Result: RSI = 62.3

# ADX
TR = max(67350-66800, |67350-prev_close|, |66800-prev_close|) = 550
# Wilder smoothed → ADX = 28.5

# VWAP
typical = (67350 + 66800 + 67280) / 3 = 67143.33
cum_vp += 67143.33 * 1245
cum_vol += 1245
VWAP = cum_vp / cum_vol
# Result: VWAP = 67,050

# ATR
ATR = (prev_ATR * 13 + 550) / 14
# Result: ATR = 480
```

#### Шаг 3: Проверка условий LONG

```
1. EMA(20) > EMA(50)?
   67,150 > 66,980 → ✅ YES (бычий кроссовер активен)

2. EMA(20) > EMA(20, prev)?
   67,150 > 67,080 (prev) → ✅ YES (растёт)

3. ADX > 25?
   28.5 > 25 → ✅ YES (тренд есть)

4. RSI < 70?
   62.3 < 70 → ✅ YES (не перекуплен)

5. RSI > 30?
   62.3 > 30 → ✅ YES (не перепродан)

6. Цена > VWAP?
   67,280 > 67,050 → ✅ YES

7. ATR > 0.5% от цены?
   480 > 0.005 × 67,280 = 336.4 → ✅ YES

РЕЗУЛЬТАТ: Все 7 условий выполнены → BUY SIGNAL
```

#### Шаг 4: Signal Decision

```python
SignalDecision = {
    "action": "BUY",
    "confidence": 0.73,
    "signal_scores": {
        "trend": 0.65,       # EMA crossover + VWAP
        "momentum": 0.42,    # RSI 62.3, MACD hist > 0
        "volatility": 0.10,  # ATR sufficient
        "volume": 0.55,      # MFI 58, CVD rising
        "crypto": 0.30,      # OI stable, FR neutral
    },
    "composite_score": 0.45,
    "active_conditions": [
        "ema_cross_bullish",
        "ema_rising",
        "adx_trending",
        "rsi_not_overbought",
        "above_vwap",
        "atr_sufficient"
    ],
    "reasoning": "EMA20=67150 > EMA50=66980, ADX=28.5, RSI=62.3, Price=67280 > VWAP=67050"
}
```

#### Шаг 5: Risk Manager

```python
# Circuit Breaker Check
current_dd = (peak_capital - current_capital) / peak_capital
# = (10,800 - 10,500) / 10,800 = 2.78% → Normal ✅

# Position Sizing (Fixed 2% до 30 сделок)
risk_pct = 0.02
capital = 10,500  # USDT
sl_distance = 2.0 * ATR = 2.0 * 480 = 960
position_size_usd = risk_pct * capital / (sl_distance / 67280)
# = 0.02 * 10,500 / (960 / 67280) = 0.02 * 10,500 / 0.01427
# = 0.02 * 735,809 → capped at 5% of capital
# = 0.05 * 10,500 = 525 USDT

position_qty = 525 / 67280 = 0.00780 BTC

# SL/TP
stop_loss = 67280 - 2.0 * 480 = 66,320
take_profit = 67280 + 3.0 * 480 = 68,720
max_loss = 0.00780 * (67280 - 66320) = 0.00780 * 960 = 7.49 USDT
max_gain = 0.00780 * (68720 - 67280) = 0.00780 * 1440 = 11.23 USDT

RiskDecision = {
    "approved": True,
    "position_size_usd": 525.00,
    "position_size_qty": 0.00780,
    "leverage": 1,
    "stop_loss": 66320,
    "take_profit": 68720,
    "max_loss_usd": 7.49,
    "rejection_reason": None
}
```

#### Шаг 6: Execution

```python
# Market Order
POST /fapi/v1/order
  symbol=BTCUSDT
  side=BUY
  type=MARKET
  quantity=0.00780
  newClientOrderId=bot_1713360000001
  timestamp=1713360000000
  signature=HMAC-SHA256(...)

# Response:
{
    "orderId": 28456789012,
    "symbol": "BTCUSDT",
    "status": "FILLED",
    "executedQty": "0.00780",
    "fills": [{
        "price": "67278.50",
        "qty": "0.00780",
        "commission": "0.2099",
        "commissionAsset": "USDT"
    }]
}

# ExecutionResult:
{
    "order_id": "28456789012",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "filled_qty": 0.00780,
    "filled_price": 67278.50,
    "commission": 0.2099,
    "latency_ms": 185
}
```

#### Шаг 7: OCO Placement (SL + TP)

```python
POST /api/v3/orderList/oco
  symbol=BTCUSDT
  side=SELL
  quantity=0.00780
  # Take Profit leg
  price=68720              # LIMIT sell
  # Stop Loss leg
  stopPrice=66320          # STOP trigger
  stopLimitPrice=66300     # STOP-LIMIT execution
```

#### Шаг 8: Логирование

```python
# CSV
2026-04-17T14:00:05Z,BTCUSDT,BUY,0.00780,67278.50,0.2099,,0.45,"ema20=67150,ema50=66980,rsi=62.3,adx=28.5,vwap=67050"

# DB INSERT
INSERT INTO trade_metrics (time, symbol, action, quantity, price, commission, composite_score, indicators)
VALUES ('2026-04-17T14:00:05Z', 'BTCUSDT', 'BUY', 0.00780, 67278.50, 0.2099, 0.45, '{"ema20":67150,"ema50":66980,"rsi":62.3}')
```

#### Шаг 9: Ожидание (часы...)

```
14:00 — Позиция открыта. OCO активен.
15:00 — Свеча. EMA20 = 67,200, EMA50 = 67,000. Тренд продолжается. HOLD.
16:00 — Свеча. EMA20 = 67,350, EMA50 = 67,050. Цена = 67,800. RSI = 68. HOLD.
17:00 — Свеча. Цена = 68,750 > TP (68,720).
        OCO Leg 1 (TP) fills: SELL 0.00780 @ 68,720
```

#### Шаг 10: PnL расчёт

```python
Entry price:   67,278.50
Exit price:    68,720.00
Quantity:      0.00780 BTC

Gross PnL = (68720 - 67278.50) × 0.00780
          = 1441.50 × 0.00780
          = 11.24 USDT

Commission (entry):  0.2099 USDT
Commission (exit):   68720 × 0.00780 × 0.0004 = 0.2140 USDT
Total commission:    0.4239 USDT

Net PnL = 11.24 - 0.4239 = 10.82 USDT
PnL% = 10.82 / 525.00 = 2.06%

# Обновление метрик:
win_count += 1
total_trades += 1
current_capital += 10.82  # = 10,510.82
peak_capital = max(peak_capital, current_capital)
daily_pnl += 10.82
```

#### Шаг 11: Запись результата

```python
# Trade Log (CSV)
2026-04-17T17:00:02Z,BTCUSDT,SELL,0.00780,68720.00,0.2140,10.82,0.45,"ema20=67350,ema50=67050,rsi=68.1,tp_hit"

# Обновление Kelly (для будущего position sizing)
# После 30 сделок → Quarter-Kelly
kelly_window.append(TradeResult(pnl=10.82, is_win=True))
```

### 5.6 Timeline всего цикла

```
T+0ms     Свеча закрывается (1H bar)
T+5ms     Тик парсится, Decimal конвертация
T+5ms     Агрегация в 1m/1h бар
T+7ms     Индикаторы обновлены (EMA, RSI, ADX, VWAP, ATR)
T+8ms     Сигнал сгенерирован: BUY
T+13ms    Risk Manager одобрил
T+13ms    Ордер сформирован
T+200ms   Ордер исполнен (FILLED)
T+205ms   OCO размещён
T+210ms   Лог записан
T+213ms   Готово

До TP: 3 часа (T+10,800,000ms)
```

---

## 6. Конфигурация

### 6.1 Полный config.yaml для v0.1

```yaml
# ============================================
# Xiaomi MiMo Studio Trading Bot — v0.1
# ============================================

general:
  symbol: "BTCUSDT"
  exchange: "binance_futures"
  timeframe: "1h"
  dry_run: true          # Paper trading для v0.1

# --- Data Layer ---
data:
  websocket:
    url: "wss://fstream.binance.com/ws/btcusdt@aggTrade"
    reconnect_delay_sec: [1, 2, 4, 8, 16, 32, 60]
    max_reconnect: 7
  aggregation:
    volume_bar_threshold_usd: 100000
    time_bars: ["1m", "1h"]
  storage:
    parquet_path: "data/{symbol}/{bar_type}/{date}.parquet"
    parquet_batch_size: 1000
    timescale_dsn: "postgresql://bot:pass@localhost:5432/trading"
    timescale_batch_size: 100

# --- Indicators ---
indicators:
  trend:
    ema_fast_period: 20
    ema_slow_period: 50
    vwap_reset_hour_utc: 0
    supertrend_atr_period: 10
    supertrend_multiplier: 3.0
    adx_period: 14
    adx_threshold: 25
  momentum:
    rsi_period: 14
    rsi_overbought: 70
    rsi_oversold: 30
    rsi_extreme_ob: 85
    rsi_extreme_os: 15
    macd_fast: 12
    macd_slow: 26
    macd_signal: 9
    stoch_rsi_period: 14
    stoch_rsi_smooth_k: 3
    stoch_rsi_smooth_d: 3
    fisher_period: 9
    cci_period: 20
  volatility:
    atr_period: 14
    atr_min_pct: 0.005        # 0.5% от цены
    bollinger_period: 20
    bollinger_std: 2.0
  volume:
    mfi_period: 14
    mfi_overbought: 80
    mfi_oversold: 20
    cvd_outlier_sigma: 3.0
    cvd_outlier_window: 20
  crypto:
    funding_rate:
      api: "binance"
      refresh_sec: 60
      z_score_window: 30
      z_score_threshold: 2.0
    open_interest:
      api: "binance"
      refresh_sec: 60
      oi_threshold_alert: 0.15

# --- Signal Engine ---
signal:
  composite_threshold: 0.30
  min_confirming_categories: 3
  cooldown_sec: 300           # 5 минут
  category_weights:
    trend: 0.30
    momentum: 0.25
    volume: 0.20
    crypto: 0.15
    volatility: 0.10

# --- Risk Manager ---
risk:
  # Circuit Breaker
  max_drawdown_warning: 0.12
  max_drawdown_halt: 0.15
  flash_crash_threshold: 0.08
  max_trades_per_day: 50
  max_open_positions: 5
  cb_cooldown_hours: 24

  # Position Sizing
  position_mode: "fixed_fraction"  # → "quarter_kelly" после 30 сделок
  fixed_fraction: 0.02
  kelly_fraction: 0.25
  kelly_cap: 0.25
  kelly_min_trades: 30
  max_position_pct: 0.05

  # SL/TP
  sl_atr_multiplier_long: 2.0
  sl_atr_multiplier_short: 1.5
  tp_atr_multiplier: 3.0

  # VaR/CVaR
  var_confidence: 0.95
  var_window_days: 30
  cvar_halt_threshold: 0.10
  cvar_reduce_threshold: 0.05

# --- Execution ---
execution:
  order_type: "MARKET"         # MVP: Market. Production: LIMIT
  max_slippage_bps: 10
  order_timeout_sec: 60
  oco_enabled: true
  commission:
    maker_fee: 0.0002
    taker_fee: 0.0004
    use_bnb: true
    bnb_discount: 0.75

# --- Logging ---
logging:
  level: "INFO"
  format: "json"
  trade_log_path: "trades/trades_{date}.csv"
  log_rotation_mb: 100
  log_retention_days: 30

# --- Reporting ---
reporting:
  dashboard_port: 8501
  refresh_sec: 5
  auth_user: "admin"
  auth_pass: "${DASHBOARD_PASSWORD}"
```

---

## 7. Латентность и производительность

### 7.1 Профилирование hot path

| Операция | Компоненты | Время | Оптимизация |
|----------|-----------|-------|-------------|
| JSON parse | serde_json | 0.5 мс | SIMD-парсинг (simd-json) |
| Decimal conversion | rust_decimal | 0.2 мс | Pre-allocated |
| Tick → Bar | min/max/add | 0.05 мс | Inline |
| EMA update | mul + add + sub | 0.001 мс | #[inline(always)] |
| RSI update | 2 mul + 1 div | 0.001 мс | Wilder formula |
| ADX update | 6 operations | 0.002 мс | Pre-computed 1/period |
| All indicators | 15+ ind. | 2 мс | Parallel per-pair |
| Signal composite | weighted sum | 0.1 мс | Branchless |
| Risk check | 6 checks | 0.5 мс | Early exit on veto |
| Order format | HMAC-SHA256 | 0.1 мс | |
| **Total (tick→decision)** | | **≈ 8 мс** | |
| Network (REST API) | roundtrip | 200 мс | WebSocket user stream |
| **Total (tick→fill)** | | **≈ 213 мс** | |

### 7.2 Memory footprint

| Компонент | Память | Примечание |
|-----------|--------|-----------|
| EMA(20) | 24 байт | 3 × f64 |
| EMA(50) | 24 байт | 3 × f64 |
| RSI(14) | 48 байт | avg_gain, avg_loss, prev_close, buffer |
| MACD | 72 байт | 3 EMA |
| ADX | 72 байт | 9 × f64 |
| ATR | 24 байт | smoothed, count |
| Bollinger | 200 байт | SMA + Welford variance |
| VWAP | 24 байт | cum_vp, cum_vol |
| CVD | 16 байт | value, prev_price |
| MFI(14) | 224 байт | ring buffer |
| **Все индикаторы** | **~728 байт** | **< 1 KB на пару** |
| Tick buffer (10K) | 800 KB | кольцевой буфер дедупликации |
| Bar buffers | 10 KB | 1m + 1h + Volume |
| **Итого на пару** | **~811 KB** | |

### 7.3 Multi-pair scaling

```
1 пара:   8 мс на свечу, 811 KB памяти
10 пар:   80 мс на свечу (sequential), 8 MB памяти
10 пар:   12 мс на свечу (parallel, 8 cores), 8 MB памяти
100 пар:  120 мс (parallel), 80 MB памяти
```

---

## 8. Сводная матрица индикаторов

### 8.1 Финальный набор индикаторов по модулям (из агентов 01–16)

| # | Индикатор | Модуль | Роль | Фаза | Основание |
|---|-----------|--------|------|------|-----------|
| 1 | EMA(20/50) | Trend | PRIMARY direction | v0.1 | Экспоненциальные веса, O(1), стандарт |
| 2 | VWAP | Trend | Fair price filter | v0.1 | Институциональная привязка, объём-взвешенная |
| 3 | Supertrend(10,3) | Trend | Trailing stop | v0.2 | ATR-адаптивный |
| 4 | ADX(14) | Trend | Trend/Flat filter | v0.1 | Определяет наличие тренда |
| 5 | KAMA(30) | Trend | Adaptive filter | v0.2 | ER фильтрует флэт |
| 6 | SAR(0.02,0.2) | Trend | Confirmation reversal | v0.2 | Только подтверждение, не primary |
| 7 | RSI(14) | Momentum | Overbought/oversold filter | v0.1 | Стандарт, чёткие пороги 30/70 |
| 8 | MACD(12,26,9) | Momentum | Momentum + divergence | v0.1 | Двойная функция |
| 9 | StochRSI(14,14,3,3) | Momentum | Timing entry | v0.2 | Чувствительный тайминг |
| 10 | Fisher Transform(9) | Momentum | Reversal detection | v0.2 | Гауссова трансформация |
| 11 | CCI(20) | Momentum | Deviation from mean | v0.3 | Комплементарен RSI |
| 12 | ATR(14) | Volatility | SL/TP base | v0.1 | Основа всех расчётов |
| 13 | Bollinger(20,2) | Volatility | Squeeze/breakout | v0.2 | Волатильностные каналы |
| 14 | CVD | Volume | Order flow lite | v0.3 | Агрессия покупателей/продавцов |
| 15 | MFI(14) | Volume | Volume-weighted RSI | v0.2 | Нормализованный, пороги |
| 16 | OBV | Volume | Divergence | v0.1 | Простейший, дивергенция |
| 17 | Funding Rate | Crypto | Contrarian filter | v0.1 | Z-score нормализация |
| 18 | Open Interest | Crypto | Capital flow confirmation | v0.1 | Матрица 2×2 (цена × OI) |
| 19 | MVRV Z-Score | Crypto | Macro cycle filter | v0.3 | Циклические верхи/низы |
| 20 | VaR(95%) | Risk | Daily monitoring | v0.1 | Historical, simple |
| 21 | CVaR(95%) | Risk | Tail risk | v0.1 | Когерентная мера |
| 22 | Sharpe(30d) | Risk | Strategy quality | v0.2 | Rolling metric |
| 23 | MaxDD Circuit Breaker | Risk | Emergency stop | v0.1 | 12%/15% пороги |

### 8.2 Индикаторы по версиям

**v0.1 (MVP):** EMA, VWAP, ADX, RSI, MACD, ATR, OBV, Funding Rate, Open Interest, VaR, CVaR, MaxDD CB

**v0.2:** + Supertrend, KAMA, SAR, StochRSI, Fisher, Bollinger, MFI, Sharpe

**v0.3:** + CCI, CVD, Volume Profile, MVRV, NVT, Ichimoku, GARCH

**v0.4:** + OBI, Kyle's Lambda, VPIN, Liquidation Clusters, SOPR, NVT

---

## Заключение

Данный документ представляет полный синтез data flow и торговой логики криптобота на основе результатов 7 специализированных агентов (01, 02, 03, 05, 07, 10, 16) и 3 исходных документов.

**Ключевые архитектурные решения:**

1. **9-слойный pipeline** от WebSocket до дашборда с общим бюджетом латентности 213 мс.
2. **Четырёхуровневая иерархия сигналов:** Primary → Filter → Confirmation → Timing.
3. **Veto system:** Risk Manager имеет абсолютное право вето на любой сигнал.
4. **State machine с 7 состояниями** для жизненного цикла ордера.
5. **Конкретная стратегия v0.1:** EMA crossover + RSI + ADX фильтр — полный цикл от свечи до PnL за 213 мс.
6. **Постепенная эволюция:** v0.1 (12 индикаторов) → v0.2 (20) → v0.3 (25) → v0.4 (30+).

**Общий бюджет:** tick → fill ≈ 213 мс, память < 1 KB на пару для индикаторов, масштабируется до 100+ пар.

---

*Документ: 29-dataflow-synthesis.md*
*Мета-агент: 29 — Data Flow & Trading Logic Synthesis*
*Дата: 2026-04-17*
*Источники: Agent 01 (Trend), Agent 02 (Oscillators), Agent 03 (Volume), Agent 05 (Risk), Agent 07 (Order Flow), Agent 10 (Execution), Agent 16 (Crypto-Specific)*