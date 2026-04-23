
# MVP v0.1 — Крипто-торговый бот: Полное описание

> **Версия:** MVP v0.1  
> **Дата:** 17 апреля 2026  
> **Статус:** Готов к реализации  
> **Базовая документация:** FINAL-CONSOLIDATED-DOCUMENT.md (30 агентов, 1877 строк)

---

## Что это

Алгоритмический торговый бот для BTC/USDT и ETH/USDT на Binance. Rust-ядро, 4-слойная архитектура сигналов, ML-фильтр, фундаментальный gate. Не предсказывает цену — фильтрует качество сигналов базовой стратегии.

---

## Ключевая идея

```
Слой 1: Микроструктура    → понимаем стакан и поток ордеров
Слой 2: Теханализ          → EMA + ADX + Supertrend дают направление
Слой 3: ML-фильтр         → XGBoost решает «исполнять или нет»
Слой 4: Фундаментал       → FOMC/CPI/unlocks → HALT
Слой 5: Риск-контроль     → ATR-SL/TP + Kelly + Circuit Breaker
```

Один индикатор не работает. Связка из 4 слоёв — работает.

---

## MVP Scope (что входит)

### Входит

| Компонент | Описание |
|-----------|---------|
| **Data Ingest** | Binance WebSocket (kline, trade, depth), zero-alloc JSON parsing |
| **Ring Buffer** | 1000 bars в памяти, O(1) обновления |
| **Индикаторы (Layer 1–2)** | EMA(20/50), ADX(14), RSI(14), MACD(12/26/9), ATR(14), OBV, VWAP, Bollinger(20,2) |
| **Микроструктура** | OBI (K=10, γ=0.5), TBSR, OCR (spoofing detection) |
| **Сигнал** | EMA crossover + ADX > 25 + RSI confirmation |
| **Риск** | ATR-SL/TP (k_SL=2.0, k_TP=3.0), Half-Kelly, MaxDD Circuit Breaker (L1=12%, L2=15%) |
| **Исполнение** | OCO orders, fixed slippage (5 bps), Binance REST API |
| **Бэктест** | Walk-Forward (train 80%, K≥5), Purged K-Fold, Monte Carlo Permutation |
| **Метрики** | Sharpe, Sortino, Calmar, MaxDD, CVaR, WinRate, Profit Factor |
| **Хранение** | QuestDB (тики/свечи), SQLite (конфиг/состояние) |
| **Конфиг** | YAML-based, все параметры настраиваемые |

### НЕ входит в MVP (v0.2+)

| Компонент | Версия |
|-----------|--------|
| ML meta-labeling (XGBoost) | v0.2 |
| Фундаментальный gate (FOMC/CPI/unlocks) | v0.2 |
| Order Flow (Kyle's Lambda, VPIN) | v0.3 |
| HMM regime detection | v0.3 |
| GARCH volatility | v0.3 |
| Options (Black-Scholes, Greeks) | v0.4 |
| Arbitrage (triangular, funding spread) | v0.4 |
| Sentiment (Fear & Greed, Twitter) | v0.4 |

---

## Архитектура

### Модули

```
┌─────────────────────────────────────────────────────────┐
│                    TRADING ENGINE                        │
│                                                          │
│  WebSocket ──→ Ring Buffer ──→ Indicator Engine          │
│  (Binance)     (1000 bars)     (O(1) updates)           │
│                                   │                      │
│                          ┌────────▼────────┐             │
│                          │ Signal Generator │             │
│                          │ EMA+ADX+RSI+OBI │             │
│                          └────────┬────────┘             │
│                                   │                      │
│                          ┌────────▼────────┐             │
│                          │  Risk Manager   │             │
│                          │ ATR+Kelly+MaxDD │             │
│                          └────────┬────────┘             │
│                                   │                      │
│                          ┌────────▼────────┐             │
│                          │ Order Executor  │             │
│                          │ OCO + Binance   │             │
│                          └────────┬────────┘             │
│                                   │                      │
│              QuestDB ◄────────────┘                      │
│              (тики, свечи, P&L)                           │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
Binance WebSocket (JSON)
    ↓ [zero-alloc parsing: serde &str, fast_float]
Ring Buffer (MaybeUninit<T>, no alloc after init)
    ↓ [параллельно все индикаторы обновляются O(1)]
    ├─ EMA:  new = price × α + old × (1−α)
    ├─ RSI:  new_avg_gain = (old × (N−1) + gain) / N
    ├─ ATR:  new = (old × (N−1) + TR) / N
    ├─ ADX:  TR → DM → DI → DX → ADX (Wilder smoothing)
    ├─ OBV:  cum += ±volume
    └─ VWAP: cum_vp += price×vol, cum_vol += vol
    ↓
Signal: EMA crossover AND ADX>25 AND RSI не перекуплен
    ↓
Risk: ATR-SL/TP → Kelly size → MaxDD check
    ↓
Execute: OCO order → Binance REST
    ↓
QuestDB: запись батчем (async, не блокирует цикл)
```

### State Machine

```
IDLE → ANALYZE → SIGNAL → RISK_CHK → EXECUTE → MONITOR
                                    ↘ HALT (MaxDD > 15%)
```

---

## Сигнальная логика

### Primary: EMA Crossover

```
LONG:   EMA(20) > EMA(50) AND prev EMA(20) ≤ prev EMA(50)
SHORT:  EMA(20) < EMA(50) AND prev EMA(20) ≥ prev EMA(50)
```

### Filter 1: ADX Trend Strength

```
ADX(14) > 25 → тренд есть, сигнал валиден
ADX(14) < 25 → флэт, сигнал блокируется
```

### Filter 2: RSI Confirmation

```
Для LONG:  RSI(14) < 70 (не перекуплен)
Для SHORT: RSI(14) > 30 (не перепродан)
```

### Filter 3: OBI (Order Book Imbalance)

```
OBI = (Σ w_k × Q_bid − Σ w_k × Q_ask) / (Σ w_k × (Q_bid + Q_ask))
w_k = e^{−0.5 × k}, K=10 уровней

|OBI| > 0.3 → значимый перекос → подтверждает направление
|OBI| > 0.7 + OCR > 0.7 → спуфинг → заблокировать сигнал
```

### Итоговый сигнал

```
LONG если:  EMA up AND ADX>25 AND RSI<70 AND (OBI>0 или OBI нейтральный)
SHORT если: EMA down AND ADX>25 AND RSI>30 AND (OBI<0 или OBI нейтральный)
FLAT иначе
```

---

## Риск-менеджмент

### Stop Loss / Take Profit

```
LONG:  SL = Entry − 2.0 × ATR(14),  TP = Entry + 3.0 × ATR(14)
SHORT: SL = Entry + 1.5 × ATR(14),  TP = Entry − 3.0 × ATR(14)

R:R long = 1.5:1,  R:R short = 2.0:1
```

### Position Sizing (Half-Kelly)

```
Kelly = (W × R − L) / R
Half-Kelly = Kelly × 0.5
PositionSize = min(Half-Kelly, 0.05) × Capital / SL_distance

Если Kelly ≤ 0 → не торговать
Если < 30 сделок → Fixed Fraction 2%
```

### Circuit Breaker

```
DD ≥ 12% → PositionSize × 0.5 (pre-warning)
DD ≥ 15% → HALT (4 часа или новый день)
PnL за свечу < −8% → немедленный HALT

CVaR > 10% Capital → HALT
CVaR > 5% Capital → сократить позицию на 50%
```

---

## Магические числа (все в одном месте)

| Константа | Значение | Где |
|-----------|---------|-----|
| EMA fast / slow | 20 / 50 | Сигнал |
| ADX threshold | 25 | Фильтр тренда |
| ADX confirmation | 3 бара | Подтверждение |
| RSI period / overbought / oversold | 14 / 70 / 30 | Фильтр |
| MACD fast / slow / signal | 12 / 26 / 9 | Осциллятор |
| ATR period | 14 | Волатильность |
| Bollinger period / multiplier | 20 / 2 | Волатильность |
| OBI depth K / decay γ | 10 / 0.5 | Микроструктура |
| OBI bias / extreme | ±0.3 / ±0.7 | Микроструктура |
| OCR spoof threshold | > 0.7 | Anti-spoofing |
| k_SL long / short | 2.0 / 1.5 | Стоп-лосс |
| k_TP | 3.0 | Тейк-профит |
| Kelly fraction | 0.5 | Сайзинг |
| MaxPct per trade | 5% | Сайзинг |
| MaxDD L1 / L2 | 12% / 15% | Circuit breaker |
| Flash crash threshold | −8% за свечу | Circuit breaker |
| VaR α | 0.05 | Риск |
| CVaR halt / reduce | 10% / 5% Capital | Риск |
| Ring buffer size | 1000 bars | Память |
| Slippage (backtest) | 5 bps | Бэктест |
| Walk-Forward train ratio | 0.8 | Валидация |
| MC permutations | 10,000 | Валидация |

---

## Технологический стек

```
Язык:           Rust 1.75+
Async:          tokio
WebSocket:      tokio-tungstenite (zero-alloc JSON via serde &str)
REST:           reqwest
Хранение:       QuestDB (ILP protocol, TCP batch) + SQLite (config)
Decimal:        rust_decimal (без потери точности)
Бэктест:        custom Rust engine
ML (будущее):   xgboost → ONNX → ort crate
Мониторинг:     prometheus + grafana
```

---

## Бэктестинг

### Walk-Forward Analysis

```
|===== TRAIN =====|== TEST ==|
|========= TRAIN =========|== TEST ==|

train_ratio = 0.8,  K ≥ 5 фолдов,  embargo = 2 × holding_period
```

### Анти-overfitting

```
1. Один набор параметров на все фолды
2. OOS Sharpe ≥ 1.0 (годовой)
3. Sensitivity: ±20% параметра → Sharpe не падает >50%
4. Monte Carlo Permutation: p-value < 0.05
5. Deflated Sharpe Ratio > 0 после коррекции
```

### Пороги прохождения

| Метрика | Минимум |
|---------|---------|
| Sharpe (годовой) | ≥ 1.0 |
| Sortino | ≥ 1.5 |
| Calmar | ≥ 1.0 |
| MaxDD | < 25% |
| WinRate | > безубыточность + 3 п.п. |
| Math Expectation | ≥ 0.1% за сделку |
| OOS Sharpe / IS Sharpe | ≥ 0.5 |

---

## Рой агентов для реализации

### Архитектура роя

Каждый агент — специализированный AI-помощник, работающий над своей задачей параллельно. Оркестратор (главный агент) управляет потоком работ и интеграцией.

```
                    ┌──────────────────┐
                    │   ОРКЕСТРАТОР    │
                    │ (главный агент)  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │ Агент A │         │ Агент B │         │ Агент C │
   │ Data    │         │ Indic-  │         │ Signal  │
   │ Pipeline│         │ ators   │         │ Engine  │
   └─────────┘         └─────────┘         └─────────┘
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │ Агент D │         │ Агент E │         │ Агент F │
   │ Risk    │         │ Order   │         │ Backtest│
   │ Manager │         │ Executor│         │ Engine  │
   └─────────┘         └─────────┘         └─────────┘
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │ Агент G │         │ Агент H │         │ Агент I │
   │ Micro-  │         │ Config  │         │ QA /    │
   │ struct. │         │ + YAML  │         │ Testing │
   └─────────┘         └─────────┘         └─────────┘
```

### Состав роя (9 агентов)

#### Агент A: Data Pipeline Engineer

**Задача:** Binance WebSocket ingest, ring buffer, QuestDB writer.

```
Вход: Binance kline/trade/depth streams
Выход: RingBuffer<Candle>, QuestDB batch writer
Модули:
  - src/data/ws_client.rs        — WebSocket клиент (tokio-tungstenite)
  - src/data/parser.rs           — zero-alloc JSON parsing (serde &str)
  - src/data/ring_buffer.rs      — RingBuffer<N, T> (MaybeUninit)
  - src/data/questdb_writer.rs   — async batch writer (ILP protocol)
  - src/data/validator.rs        — OHLCV consistency, gap detection
Зависимости: нет (первый модуль)
Время: 16 часов
```

#### Агент B: Indicator Engine Developer

**Задача:** Все O(1) индикаторы.

```
Вход: RingBuffer<Candle>
Выход: IndicatorState (все текущие значения)
Модули:
  - src/indicators/ema.rs        — EMA O(1) update
  - src/indicators/adx.rs        — ADX + DI (Wilder smoothing)
  - src/indicators/rsi.rs        — RSI (Wilder smoothing, clamp edge cases)
  - src/indicators/macd.rs       — MACD (2 EMA + signal EMA)
  - src/indicators/atr.rs        — ATR (True Range + Wilder)
  - src/indicators/obv.rs        — OBV (cumulative, winsorize)
  - src/indicators/vwap.rs       — VWAP (session reset 00:00 UTC)
  - src/indicators/bollinger.rs  — Bollinger Bands (SMA ± 2σ)
  - src/indicators/mod.rs        — IndicatorEngine (параллельные обновления)
Зависимости: Агент A (ring buffer)
Время: 20 часов
```

#### Агент C: Signal Generator

**Задача:** Комбинация сигналов, OBI, TBSR, anti-spoofing.

```
Вход: IndicatorState, OrderBook snapshot
Выход: Signal { direction, confidence, obi, tbsr }
Модули:
  - src/signal/ema_crossover.rs  — Primary: EMA(20)/EMA(50) crossover
  - src/signal/adx_filter.rs     — ADX > 25 filter
  - src/signal/rsi_filter.rs     — RSI confirmation filter
  - src/signal/obi.rs            — Order Book Imbalance (K=10, γ=0.5)
  - src/signal/tbsr.rs           — Taker Buy/Sell Ratio
  - src/signal/ocr.rs            — Order Cancellation Ratio (anti-spoofing)
  - src/signal/combiner.rs       — Signal combination: primary × filters
Зависимости: Агент B (indicators)
Время: 16 часов
```

#### Агент D: Risk Manager

**Задача:** ATR-SL/TP, Kelly sizing, circuit breaker.

```
Вход: Signal, ATR, Capital, Trade history
Выход: RiskDecision { sl, tp, size, action }
Модули:
  - src/risk/atr_levels.rs       — SL/TP calculation (k_SL=2.0, k_TP=3.0)
  - src/risk/kelly.rs            — Half-Kelly position sizing
  - src/risk/circuit_breaker.rs  — MaxDD monitor (L1=12%, L2=15%)
  - src/risk/var.rs              — Historical VaR/CVaR
  - src/risk/manager.rs          — RiskManager: chain of checks
Зависимости: Агент B (ATR), Агент F (trade history for Kelly)
Время: 12 часов
```

#### Агент E: Order Executor

**Задача:** OCO orders, Binance REST API, slippage model.

```
Вход: RiskDecision
Выход: OrderResult { fill_price, fill_qty, fees }
Модули:
  - src/executor/binance_rest.rs — Binance REST API client (reqwest)
  - src/executor/oco.rs          — OCO order (SL + TP одновременно)
  - src/executor/slippage.rs     — Fixed slippage model (5 bps)
  - src/executor/position.rs     — Position tracker (открытые позиции)
  - src/executor/executor.rs     — OrderExecutor: send → track → fill
Зависимости: Агент D (RiskDecision)
Время: 12 часов
```

#### Агент F: Backtest Engine Developer

**Задача:** Walk-Forward, Purged K-Fold, Monte Carlo, метрики.

```
Вход: Historical data (QuestDB/CSV)
Выход: BacktestReport { Sharpe, Sortino, MaxDD, trades, equity_curve }
Модули:
  - src/backtest/engine.rs       — BacktestEngine (replay + simulate)
  - src/backtest/walk_forward.rs — Walk-Forward Analysis (expanding)
  - src/backtest/purged_kfold.rs — Purged K-Fold с embargo
  - src/backtest/monte_carlo.rs  — Monte Carlo Permutation test
  - src/backtest/metrics.rs      — 15 ключевых метрик
  - src/backtest/report.rs       — Генерация отчёта (JSON + Markdown)
Зависимости: Агент A (data), B (indicators), C (signals), D (risk), E (executor)
Время: 20 часов
```

#### Агент G: Microstructure Specialist

**Задача:** L2 order book processing, OCR, spoofing detection.

```
Вход: Binance depth WebSocket stream
Выход: OrderBook state, OBI, OCR, spoof flags
Модули:
  - src/micro/l2_processor.rs    — L2 depth update parser
  - src/micro/order_book.rs      — OrderBook state (BTreeMap levels)
  - src/micro/obi_calc.rs        — OBI multi-level calculator
  - src/micro/ocr_tracker.rs     — Order Cancellation Ratio per level
  - src/micro/spoof_detector.rs  — Spoof detection logic
Зависимости: Агент A (WebSocket)
Время: 12 часов
```

#### Агент H: Config & Infrastructure

**Задача:** YAML config, SQLite state, Prometheus metrics, Docker.

```
Выход: Config struct, state management, monitoring
Модули:
  - src/config/mod.rs            — YAML config (serde), env overrides
  - src/config/state.rs          — SQLite state (positions, regime, CB)
  - src/monitor/prometheus.rs    — Prometheus metrics export
  - Dockerfile                   — multi-stage build
  - docker-compose.yml           — bot + QuestDB + Grafana
  - config.yaml                  — default configuration
Зависимости: нет (инфраструктура)
Время: 8 часов
```

#### Агент I: QA & Testing Engineer

**Задача:** Unit tests, integration tests, edge case validation.

```
Вход: все модули
Выход: test suite, coverage report
Модули:
  - tests/unit/test_indicators.rs  — EMA, RSI, ADX, ATR корректность
  - tests/unit/test_risk.rs        — Kelly, circuit breaker, VaR
  - tests/unit/test_obi.rs         — OBI edge cases (empty book, spoof)
  - tests/integration/test_flow.rs — полный цикл: tick → signal → order
  - tests/integration/test_backtest.rs — P&L reconciliation
  - tests/edge_cases/              — flash crash, gap, zero volume, NaN
Зависимости: все агенты
Время: 16 часов
```

### Порядок запуска (параллельные волны)

```
Волна 1 (параллельно):  A (Data) + H (Config) + G (Microstructure)
         ↓ после завершения
Волна 2 (параллельно):  B (Indicators) + C (Signals)
         ↓ после завершения
Волна 3 (параллельно):  D (Risk) + E (Executor)
         ↓ после завершения
Волна 4:                F (Backtest) — интеграция всех модулей
         ↓ после завершения
Волна 5:                I (QA) — тестирование всего

Общее время: ~5 дней (при параллельной работе 9 агентов)
             ~20 дней (при последовательной работе одного разработчика)
```

### Зависимости между агентами

```
A (Data) ──────→ B (Indicators) ──────→ C (Signals) ──────→ D (Risk) ──→ E (Executor)
  │                                        │                    │              │
  └──→ G (Micro) ──────────────────────────┘                    │              │
                                                                 │              │
  └──→ H (Config) ──────────────────────────────────────────────┘              │
                                                                                │
  └──→ F (Backtest) ◄──────────────────────────────────────────────────────────┘
                                                                                │
  └──→ I (QA) ◄────────────────────────────────────────────────────────────────┘
```

---

## MVP Timeline

| Неделя | Фокус | Deliverables |
|--------|-------|-------------|
| **1** | Data + Config + Microstructure | WebSocket работает, ring buffer, config.yaml, L2 парсинг |
| **2** | Indicators + Signals | Все O(1) индикаторы, EMA crossover, OBI, TBSR |
| **3** | Risk + Executor + Backtest | ATR-SL/TP, Kelly, OCO orders, первый бэктест |
| **4** | QA + Integration + Paper trading | Tests, integration, запуск в paper mode |
| **5** | Tuning + Live (small size) | Оптимизация параметров, запуск с минимальным капиталом |

---

## Config (полный YAML)

```yaml
# === MVP v0.1 Configuration ===

bot:
  pair: "BTCUSDT"
  secondary_pair: "ETHUSDT"
  timeframe: "1h"
  mode: "paper"                    # paper / live

data:
  websocket: "wss://stream.binance.com:9443/ws"
  ring_buffer_size: 1000
  questdb:
    host: "localhost"
    port: 9009
    batch_size: 500
    flush_interval_ms: 100

indicators:
  ema_fast: 20
  ema_slow: 50
  rsi_period: 14
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9
  atr_period: 14
  bollinger_period: 20
  bollinger_multiplier: 2.0
  adx_period: 14
  adx_threshold: 25
  adx_confirm_bars: 3

microstructure:
  obi:
    depth: 10
    decay: 0.5
    bias_threshold: 0.3
    extreme_threshold: 0.7
  ocr:
    min_order_usdt: 500000
    cancel_threshold: 3         # раз за 60 сек
    spoof_distance_bps: 10
    spoof_ocr_threshold: 0.7
  tbsr:
    window: 20
    overbought: 1.5
    oversold: 0.7

signal:
  primary: "ema_crossover"
  filters: ["adx_trend", "rsi_confirmation", "obi"]
  long_threshold: 0.3
  short_threshold: -0.3

risk:
  k_sl_long: 2.0
  k_sl_short: 1.5
  k_tp: 3.0
  kelly_fraction: 0.5
  max_pct_per_trade: 0.05
  maxdd_warning: 0.12
  maxdd_halt: 0.15
  flash_crash_pct: 0.08
  var_alpha: 0.05
  cvar_halt_pct: 0.10
  cvar_reduce_pct: 0.05
  min_sl_distance: "max(2*atr, 0.005*entry)"

execution:
  slippage_bps: 5.0
  order_type: "OCO"              # OCO / LIMIT / MARKET
  order_timeout_sec: 30
  max_retry: 3

backtest:
  walk_forward:
    train_ratio: 0.8
    min_folds: 5
    embargo_multiplier: 2
  monte_carlo:
    permutations: 10000
    p_value_threshold: 0.05
  thresholds:
    min_sharpe: 1.0
    min_sortino: 1.5
    min_calmar: 1.0
    max_drawdown: 0.25

monitoring:
  prometheus_port: 9090
  grafana_port: 3000
  log_level: "info"              # debug / info / warn / error
```

---

## Примечания

### Anti-patterns (запрещено)

- **Look-ahead bias:** никаких данных из будущего бара. StandardScaler на всём датасете — ЗАПРЕЩЁН. Только rolling/expanding window.
- **Data snooping:** один набор параметров на все фолды. Deflated Sharpe Ratio для коррекции.
- **Overfitting:** максимум 7 свободных параметров. OOS Sharpe ≥ 50% от IS.
- **Hard-coded params:** все числа в config.yaml, не в коде.

### Что дальше (после MVP)

| Версия | Что добавить |
|--------|-------------|
| **v0.2** | XGBoost meta-labeling, FOMC/CPI gate, Token Unlocks, VWAP, MFI, CVD |
| **v0.3** | HMM regimes, GARCH, HP filter, Wavelet denoising, Volume Profile, Kyle's Lambda |
| **v0.4** | VPIN, MVRV Z-Score, SOPR, Hilbert Transform, Johansen, Options (BS) |
| **v0.5** | Arbitrage (triangular, funding spread), Sentiment, RL, Online learning |

---

> **Детальная документация:** FINAL-CONSOLIDATED-DOCUMENT.md (30 агентов, 1877 строк)  
> **Исходные данные:** 31 файл агентов в `output/`  
> **Дата:** 17 апреля 2026
