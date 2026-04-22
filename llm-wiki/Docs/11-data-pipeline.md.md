# Агент 11: Data Pipeline & Bars Engineering

**Дата:** 17 апреля 2026  
**Назначение:** Проектирование пайплайна сбора, агрегации и хранения рыночных данных для крипто-торгового бота.  
**Исходники:** Trading Bots and Indicators.md, Data Quality (Agent 22), Architecture (Agent 24)

---

## 1. Источники данных

### 1.1 Binance WebSocket (основной источник)

```
Подписки:
  - kline_1m: BTCUSDT, ETHUSDT (свечи 1 минута)
  - trade: BTCUSDT, ETHUSDT (каждая сделка)
  - depth@100ms: BTCUSDT, ETHUSDT (стакан, обновления каждые 100ms)
  - bookTicker: BTCUSDT, ETHUSDT (лучший бид/аск)

Формат: JSON через WebSocket (tokio-tungstenite)
Частота: непрерывный поток (100+ сообщений/сек для BTC/USDT)
```

### 1.2 Binance REST (исторические данные)

```
Endpoint: GET /api/v3/klines
Параметры: symbol=BTCUSDT, interval=1m, limit=1000
Использование: первоначальная загрузка исторических данных при старте
```

### 1.3 Deribit WebSocket (опционы, v0.4+)

```
Подписки:
  - book.BTC-PERPETUAL.100ms
  - trades.BTC-PERPETUAL.raw
  - ticker.BTC-PERPETUAL.100ms
```

---

## 2. Типы баров (Bar Types)

### 2.1 Time Bars (временные свечи)

Стандартные свечи фиксированной длительности.

```
Параметры: 1m, 5m, 15m, 1H, 4H, 1D
Агрегация: OHLCV за период
Назначение: основные индикаторы (EMA, RSI, MACD, ATR, Bollinger)
```

### 2.2 Volume Bars (объёмные бары)

Каждый бар содержит фиксированный суммарный объём. Важно для равномерности статистики.

```
Параметр: 100,000 USD объёма на бар (для BTC/USDT)
Агрегация: VWAP за объём, количество сделок
Назначение: статистический анализ, ML-фичи, CVD

Формула VWAP внутри бара:
  cum_vp += price × volume
  cum_vol += volume
  VWAP_bar = cum_vp / cum_vol
```

**Почему Volume Bars лучше Time Bars для статистики:**
- Бар в 100K объёма компенсирует разную активность в разное время дня
- Ночью (thin liquidity) один 1H бар может содержать 10 сделок, днём — 10,000
- Volume Bars дают одинаковое «информационное наполнение» на бар

### 2.3 Tick Bars (тиковые бары)

Каждый бар содержит фиксированное количество сделок.

```
Параметр: 100 контрактов для BTC perp
Назначение: footprint analysis, order flow, микроструктура
```

### 2.4 Range Bars (бары фиксированного диапазона)

Каждый бар содержит фиксированное ценовое движение.

```
Параметр: $100 движения для BTC/USDT
Назначение: волатильность-нормализованный анализ
```

---

## 3. Хранение данных

### 3.1 QuestDB / ClickHouse (тики и свечи)

```
Таблицы:
  ticks:       timestamp, exchange, pair, price, quantity, side, trade_id
  candles_1m:  timestamp, exchange, pair, open, high, low, close, volume, trades
  candles_1h:  timestamp, exchange, pair, open, high, low, close, volume, trades
  volume_bars: timestamp, exchange, pair, vwap, volume, trades, open, close
  order_book:  timestamp, exchange, pair, bids_json, asks_json

Протокол записи: ILP (InfluxDB Line Protocol) через TCP
Батчинг: 100–1000 тиков, flush каждые 100ms или по заполнению
Async: не блокирует торговый цикл
```

### 3.2 SQLite (конфигурация и состояние)

```
Таблицы:
  config:      key, value, updated_at
  positions:   pair, side, quantity, entry_price, entry_time, status
  state:       last_bar_timestamp, regime, circuit_breaker_status
  signals:     timestamp, pair, signal, confidence, action, executed
```

---

## 4. Валидация данных

### 4.1 Целостность потоков

```rust
fn detect_gaps(candles: &[Candle], expected_interval_ms: i64) -> Vec<Gap> {
    // Проверка разницы timestamp между соседними свечами
    // Если diff > expected + tolerance → gap
}

fn fill_strategy(gap: &Gap) -> FillStrategy {
    match gap.missing_candles {
        1 => ForwardFill,           // OHLC = prev_close, V=0
        2..=5 => LinearInterpolate, // линейная интерполяция OHLC
        6..=60 => MarkGapped,       // флаг, без заполнения
        _ => MarkIncomplete,        // участок непригоден
    }
}
```

### 4.2 Cross-exchange verification

Перекрёстная сверка объёмов между площадками для обнаружения:
- Пропущенных баров
- Аномальных расхождений цены
- Data feed disconnections

### 4.3 OHLCV consistency

```
Правила:
  High >= max(Open, Close, Low)
  Low <= min(Open, Close, High)
  Volume >= 0
  Timestamp строго монотонно возрастает
  Нет дубликатов по (exchange, pair, timestamp)
```

---

## 5. Конфигурация

```yaml
data_pipeline:
  exchanges:
    - name: binance
      websocket: "wss://stream.binance.com:9443/ws"
      pairs: ["btcusdt", "ethusdt"]
      streams: ["kline_1m", "trade", "depth@100ms"]
  
  bar_types:
    time_bars: [1m, 5m, 15m, 1h, 4h, 1d]
    volume_bars:
      btcusdt: 100000    # USD
      ethusdt: 50000     # USD
    tick_bars:
      btcusdt: 100       # trades
  
  storage:
    timeseries_db: questdb   # или clickhouse
    config_db: sqlite
    batch_size: 500
    flush_interval_ms: 100
  
  validation:
    max_gap_candles: 60
    outlier_z_threshold: 4.0
    min_volume_usd: 1000
```