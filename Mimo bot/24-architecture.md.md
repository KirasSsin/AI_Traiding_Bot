# Системная архитектура — Crypto Trading Bot

**Агент 24 — Архитектор**
**Дата:** 17 апреля 2026
**Статус:** MVP (v0.1) → Production (v2.0)

---

## 1. Модульная архитектура

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  DataGateway │───▶│ SignalEngine │───▶│ RiskManager  │
│              │    │              │    │              │
│ WebSocket    │    │ Indicators   │    │ VaR/Kelly    │
│ REST/CSV     │    │ Rules Engine │    │ Circuit Brk  │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐
│   Reporter   │◀───│    Logger    │◀───│ ExecEngine   │
│              │    │              │    │              │
│ Metrics      │    │ Trade Log    │    │ Slippage     │
│ Equity Curve │    │ Signal Log   │    │ Commission   │
└──────────────┘    └──────────────┘    └──────────────┘
```

Поток данных: **однонаправленный**. Каждый модуль принимает данные только от предыдущего через канал.

## 2. Core Rust Types

```rust
use chrono::{DateTime, Utc};
use rust_decimal::Decimal;

#[derive(Debug, Clone)]
pub struct Candle {
    pub timestamp: DateTime<Utc>,
    pub open: Decimal,
    pub high: Decimal,
    pub low: Decimal,
    pub close: Decimal,
    pub volume: Decimal,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Side { Buy, Sell }

#[derive(Debug, Clone)]
pub struct Signal {
    pub timestamp: DateTime<Utc>,
    pub side: Side,
    pub strength: Decimal,       // 0.0 .. 1.0
    pub source: &'static str,    // "rsi_oversold", "ema_cross"
    pub price: Decimal,
}

#[derive(Debug, Clone)]
pub struct Order {
    pub id: u64,
    pub side: Side,
    pub quantity: Decimal,
    pub price: Decimal,          // limit price; market = 0
    pub stop_loss: Option<Decimal>,
    pub take_profit: Option<Decimal>,
}

#[derive(Debug, Clone)]
pub struct Fill {
    pub order_id: u64,
    pub price: Decimal,
    pub quantity: Decimal,
    pub commission: Decimal,
    pub slippage: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct Position {
    pub side: Side,
    pub entry_price: Decimal,
    pub quantity: Decimal,
    pub unrealized_pnl: Decimal,
    pub stop_loss: Decimal,
    pub take_profit: Decimal,
}

#[derive(Debug, Clone)]
pub struct Portfolio {
    pub cash: Decimal,
    pub positions: Vec<Position>,
    pub equity: Decimal,         // cash + unrealized
    pub peak_equity: Decimal,
    pub max_drawdown: Decimal,
}

#[derive(Debug, Clone)]
pub struct RiskDecision {
    pub allowed: bool,
    pub adjusted_qty: Decimal,
    pub reason: String,
}
```

## 3. Plugin Architecture — Индикаторы

```rust
use std::any::Any;

/// Базовый trait для всех индикаторов.
/// Новые индикаторы реализуют только этот trait.
pub trait Indicator: Send + Sync {
    /// Имя индикатора (для логов и отчётов)
    fn name(&self) -> &'static str;

    /// Сколько свечей нужно до первого значения
    fn warmup_period(&self) -> usize;

    /// Обновить состояние новой свечой, вернуть текущее значение
    fn update(&mut self, candle: &Candle) -> Option<Decimal>;

    /// Сбросить состояние (для повторного запуска)
    fn reset(&mut self);

    /// Downcast для доступа к специфичным полям (period, std_dev и т.д.)
    fn as_any(&self) -> &dyn Any;
}

// Реестр индикаторов — собирается при старте
pub struct IndicatorRegistry {
    indicators: Vec<Box<dyn Indicator>>,
}

impl IndicatorRegistry {
    pub fn new() -> Self {
        Self { indicators: Vec::new() }
    }

    pub fn register(&mut self, indicator: Box<dyn Indicator>) {
        self.indicators.push(indicator);
    }

    /// Обновить все индикаторы одной свечой
    pub fn update_all(&mut self, candle: &Candle) -> Vec<(&str, Option<Decimal>)> {
        self.indicators
            .iter_mut()
            .map(|ind| {
                let name = ind.name();
                let val = ind.update(candle);
                (name, val)
            })
            .collect()
    }
}
```

Базовые реализации (MVP):
- `SmaIndicator { period: usize }`
- `EmaIndicator { period: usize, alpha: Decimal }`
- `RsiIndicator { period: usize }`
- `MacdIndicator { fast, slow, signal }`
- `BollingerIndicator { period, std_dev }`
- `AtrIndicator { period }`

Добавление нового индикатора = написать struct + impl Indicator, вызвать `registry.register(...)`.

## 4. Async Pipeline (tokio channels)

```rust
use tokio::sync::mpsc;

/// Типы сообщений между модулями
pub enum PipelineMsg {
    Candle(Candle),
    Signal(Signal),
    Order(Order),
    Fill(Fill),
    Shutdown,
}

/// Связка каналов между модулями
pub struct Pipeline {
    data_to_signal: mpsc::UnboundedSender<Candle>,
    signal_to_risk: mpsc::UnboundedSender<Signal>,
    risk_to_exec: mpsc::UnboundedSender<Order>,
    exec_to_log: mpsc::UnboundedSender<Fill>,
}

/// Запуск пайплайна
pub async fn run_pipeline(mut pipeline: Pipeline) {
    let (tx_candle, mut rx_candle) = mpsc::unbounded_channel();
    let (tx_signal, mut rx_signal) = mpsc::unbounded_channel();
    let (tx_order,  mut rx_order)  = mpsc::unbounded_channel();
    let (tx_fill,   mut rx_fill)   = mpsc::unbounded_channel();

    // Задачи запускаются параллельно
    let data_task = tokio::spawn(async move {
        // DataGateway: читает свечи, шлёт в tx_candle
    });

    let signal_task = tokio::spawn(async move {
        // SignalEngine: принимает свечи, генерирует сигналы
        while let Some(candle) = rx_candle.recv().await {
            // indicators.update_all(&candle) → signal check → tx_signal.send(...)
        }
    });

    let risk_task = tokio::spawn(async move {
        // RiskManager: принимает сигналы, проверяет, отправляет ордера
        while let Some(signal) = rx_signal.recv().await {
            // risk_check → tx_order.send(...)
        }
    });

    let exec_task = tokio::spawn(async move {
        // ExecutionEngine: принимает ордера, симулирует/отправляет, шлёт fills
        while let Some(order) = rx_order.recv().await {
            // execute → tx_fill.send(...)
        }
    });

    let logger_task = tokio::spawn(async move {
        // Logger: записывает fills
        while let Some(fill) = rx_fill.recv().await {
            // persist fill
        }
    });

    // Ожидание завершения
    let _ = tokio::join!(data_task, signal_task, risk_task, exec_task, logger_task);
}
```

Каждый модуль — отдельная `tokio::spawn` задача. Коммуникация через `mpsc::unbounded_channel`. Бэкпрессура добавляется позже через `mpsc::channel(bounded_cap)`.

## 5. Anti-Patterns — Запреты

| # | Запрет | Почему |
|---|--------|--------|
| 1 | DataGateway → RiskManager напрямую | Нарушает однонаправленный поток. Данные идут только через SignalEngine. |
| 2 | ExecEngine → SignalEngine | Исполнение не должно влиять на генерацию сигналов. |
| 3 | Logger → любой модуль | Logger — только consumer. Никаких обратных вызовов. |
| 4 | Глобальный mutable state | Каждый модуль владеет своим состоянием. Обмен — только через каналы. |
| 5 | Look-ahead bias | На шаге N доступны только данные [0..N]. Ни одно значение из N+1 не используется. |
| 6 | Захардкоженные константы | Все пороги, комиссии, периоды — из конфига. |

### Правило зависимостей

```
DataGateway ──▶ SignalEngine ──▶ RiskManager ──▶ ExecEngine ──▶ Logger ──▶ Reporter
     │                │                │               │
     └────────────────┴────────────────┴───────────────┘
              ❌ НИКАКИХ обратных стрелок
```

Модуль **не знает** о существовании следующего модуля. Он просто отправляет сообщение в канал. Это обеспечивает:
- Лёгкую замену любого модуля (например, ExecutionSimulator → RealExchange)
- Независимое тестирование каждого модуля
- Возможность запустить модуль в отдельном процессе/контейнере (v2.0)

## 6. Конфигурация

```rust
pub struct BotConfig {
    pub pair: String,              // "BTC/USDT"
    pub timeframe: String,         // "1h"
    pub initial_balance: Decimal,  // 10000
    pub commission_rate: Decimal,  // 0.001
    pub slippage_pct: Decimal,     // 0.0005
    pub max_drawdown_pct: Decimal, // 0.20
    pub position_size_pct: Decimal,// 0.02
    pub indicators: Vec<IndicatorConfig>,
}

pub struct IndicatorConfig {
    pub name: String,              // "rsi"
    pub params: HashMap<String, Decimal>, // {"period": 14}
}
```

Конфиг загружается из YAML. Никаких магических чисел в коде.

## 7. MVP → Production миграция

| Аспект | MVP (v0.1) | Production (v2.0) |
|--------|-----------|-------------------|
| Язык | Python (прототип) | Rust core + Python bindings (PyO3) |
| Пайплайн | Синхронный | Async tokio channels |
| Хранение | CSV/SQLite | PostgreSQL / TimescaleDB |
| Источник данных | REST + CCXT | WebSocket (Binance + Bybit) |
| Архитектура | Монолит | gRPC микросервисы |
| Деплой | Локально | Docker / K8s |
| Мониторинг | Console + matplotlib | Prometheus + Grafana |

Ключевой принцип: **прогрессивное усложнение**. MVP модули имеют те же интерфейсы (traits), что и production. Переход = замена реализации, не переписывание архитектуры.

---

*Документ обновлён 17 апреля 2026. Связан: Core Architecture, MVP and Roadmap.*