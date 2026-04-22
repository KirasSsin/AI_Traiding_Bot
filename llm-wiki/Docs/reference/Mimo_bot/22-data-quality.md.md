# Агент 22: Качество данных и предобработка (Data Quality & Preprocessing)

**Дата:** 2026-04-17  
**Назначение:** Полный аудит проблем качества данных, методов очистки, выбор хранилища и дизайн pipeline для крипто-торгового бота (Rust).  
**Масштаб:** ~2000 пар × 1-min свечи × 5+ лет = ~5.3 млрд записей (~2 TB raw).

---

## Содержание

1. [Сводная таблица проблем качества](#сводная-таблица-проблем-качества)
2. [Missing Data (Пропуски в свечах)](#1-missing-data-пропуски-в-свечах)
3. [Outliers — Flash Crashes](#2-outliers--flash-crashes)
4. [Wash Trading Detection](#3-wash-trading-detection)
5. [Exchange Data Discrepancies](#4-exchange-data-discrepancies)
6. [Timezone Handling](#5-timezone-handling)
7. [Corporate Actions (Airdrops, Forks, Splits)](#6-corporate-actions-airdrops-forks-splits)
8. [Survivorship Bias](#7-survivorship-bias)
9. [Timestamp Alignment & Latency](#8-timestamp-alignment--latency)
10. [Duplicate Candles](#9-duplicate-candles)
11. [Volume Anomalies](#10-volume-anomalies)
12. [OHLCV Consistency Violations](#11-ohlcv-consistency-violations)
13. [Decimal Precision & Rounding](#12-decimal-precision--rounding)
14. [Delisted / Renamed Tokens](#13-delisted--renamed-tokens)
15. [Crypto-Specific: Binance Gap Filling](#14-crypto-specific-binance-gap-filling)
16. [Crypto-Specific: Wash Trading Cleanup](#15-crypto-specific-wash-trading-cleanup)
17. [Хранение данных: CSV vs Parquet vs SQLite vs PostgreSQL](#хранение-данных)
18. [Pipeline Design: ingest → validate → clean → store → serve](#pipeline-design)
19. [Rust-архитектура модуля](#rust-архитектура-модуля)
20. [Топ-5 рекомендаций](#топ-5-рекомендаций)

---

## Сводная таблица проблем качества

| # | Проблема | Severity | Обнаружение | MVP |
|---|----------|----------|-------------|-----|
| 1 | Missing Data (gaps) | 🔴 Critical | Gap detection по timestamp diff | 0.1 |
| 2 | Outliers / Flash Crashes | 🔴 Critical | Z-score + rate-of-change | 0.1 |
| 3 | Wash Trading | 🟠 High | Volume/Trade count ratio | 0.2 |
| 4 | Exchange Discrepancies | 🟠 High | Cross-exchange price diff | 0.3 |
| 5 | Timezone Issues | 🟡 Medium | UTC enforcement + DST check | 0.1 |
| 6 | Airdrops / Forks | 🟡 Medium | Price jump detection + event DB | 0.3 |
| 7 | Survivorship Bias | 🟠 High | Historical listing/delisting audit | 0.2 |
| 8 | Timestamp Latency | 🟡 Medium | Skew detection | 0.2 |
| 9 | Duplicates | 🟡 Medium | Dedup by (exchange, pair, timestamp) | 0.1 |
| 10 | Volume Anomalies | 🟡 Medium | Rolling z-score on volume | 0.2 |
| 11 | OHLCV Violations | 🔴 Critical | min(O)≤min(C)? H≥max(O,C)? | 0.1 |
| 12 | Decimal Precision | 🟢 Low | Tick-size validation | 0.3 |
| 13 | Delisted/Renamed | 🟡 Medium | Mapping table + cross-ref | 0.2 |

---

## 1. Missing Data (Пропуски в свечах)

### Проблема

На крипто-биржах пропуски в минутных/часовых свечах возникают когда:
- **WebSocket disconnect** — нет данных 30 сек → 2 мин → пропущена свеча
- **Exchange maintenance** — Binance плановые работы 1–4 часа
- **Low-liquidity pairs** — минутами нет ни одной сделки
- **API rate limiting** — REST-поллинг не успевает
- **Network partitions** — проблемы на стороне пользователя

**Масштаб:** На Binance для BTC/USDT (1-min) ~0.02% пропусков. Для мелких пар (MCAP) — до 5–15%.

### Метод обнаружения

```rust
/// Обнаружение пропусков по разнице timestamp между соседними свечами.
/// Для 1-min свечей ожидается diff = 60 секунд.
fn detect_gaps(
    candles: &[Candle],
    expected_interval_ms: i64,
    tolerance_ms: i64, // допуск (например, 1000ms)
) -> Vec<Gap> {
    let mut gaps = Vec::new();
    for window in candles.windows(2) {
        let diff = window[1].timestamp - window[0].timestamp;
        if diff > expected_interval_ms + tolerance_ms {
            let missing_count = (diff - expected_interval_ms) / expected_interval_ms;
            gaps.push(Gap {
                start: window[0].timestamp + expected_interval_ms,
                end: window[1].timestamp - expected_interval_ms,
                missing_candles: missing_count as usize,
                pair: window[0].pair.clone(),
            });
        }
    }
    gaps
}

struct Gap {
    start: i64,      // ms UTC
    end: i64,
    missing_candles: usize,
    pair: String,
}
```

### Метод исправления

**Стратегия выбора зависит от длины пропуска и типа данных:**

| Длина пропуска | Стратегия | Причина |
|----------------|-----------|---------|
| 1 свеча | Forward fill (OHLC = предыдущий Close, V=0) | Минимальное искажение |
| 2–5 свечей | Linear interpolation OHLC, V=0 | Сглаживание, но сохранение направления |
| 6–60 свечей (1 час) | Mark as `gapped`, интерполяция опциональна | Слишком много потенциальных искажений |
| >60 свечей | Не заполнять, флаг `incomplete` | Данные ненадёжны |

```rust
#[derive(Clone, Copy, Debug, PartialEq)]
enum FillStrategy {
    ForwardFill,       // OHLC = prev_close, Volume = 0
    LinearInterpolate, // линейная интерполяция OHLC
    MarkGapped,        // флаг, без заполнения
    MarkIncomplete,    // участок непригоден для торговли
}

fn select_fill_strategy(gap: &Gap, pair: &str) -> FillStrategy {
    match gap.missing_candles {
        0 => unreachable!(),
        1 => FillStrategy::ForwardFill,
        2..=5 => FillStrategy::LinearInterpolate,
        6..=60 => FillStrategy::MarkGapped,
        _ => FillStrategy::MarkIncomplete,
    }
}

fn forward_fill(prev: &Candle, timestamp: i64) -> Candle {
    Candle {
        timestamp,
        open: prev.close,
        high: prev.close,
        low: prev.close,
        close: prev.close,
        volume: Decimal::ZERO,
        trades: 0,
        is_filled: true, // флаг для downstream
        ..prev.clone()
    }
}
```

### Edge cases

- **Переход через полночь UTC** — не проблема если всё в UTC ms
- **Переход через DST** — не актуально для UTC, но если источник в локальном времени — проверить
- **Первый бар дня** — форвард-филл может создать вчерашний O=H=L=C в начале нового дня → фильтровать в индикаторах
- **Конкатенация разных источников** — пропуск может быть в одном источнике, но не в другом → merge по timestamp

### Crypto-Specific: Binance

Binance **не заполняет** пропуски в REST API ответах — свеча просто отсутствует в массиве. WebSocket `kline` стрим не шлёт данных для пропущенных свечей. **Мы обязаны сами обнаруживать и заполнять.**

---

## 2. Outliers — Flash Crashes

### Проблема

- **Flash crashes**: цена падает на 90% за секунду и возвращается (Binance BTC 2021, 2024)
- **Fat-finger trades**: один ордер сдвигает цену на 50%+
- **Liquidation cascades**: цепная ликвидация создаёт экстремальные wicks
- **Data glitches**: API возвращает `0` или `NaN`

### Метод обнаружения

**Комбинация трёх фильтров:**

```rust
struct OutlierDetector {
    z_threshold: f64,           // обычно 4.0
    rate_of_change_pct: f64,    // обычно 20% за 1 свечу
    min_volume_usd: Decimal,    // минимальный объём для доверия
}

fn is_outlier(
    candle: &Candle,
    window: &[Candle],  // последние N свечей
    params: &OutlierDetector,
) -> OutlierType {
    // 1. Z-score на лог-доходность
    let returns: Vec<f64> = window.windows(2)
        .map(|w| (w[1].close / w[0].close).ln().to_f64())
        .collect();
    let mean = returns.iter().sum::<f64>() / returns.len() as f64;
    let std = (returns.iter().map(|r| (r - mean).powi(2)).sum::<f64>()
               / returns.len() as f64).sqrt();
    let current_return = (candle.close / window.last().unwrap().close).ln().to_f64();
    let z_score = (current_return - mean) / std;

    // 2. Rate of change
    let roc = ((candle.high - candle.low) / candle.low * dec!(100)).to_f64();

    // 3. Zero/NaN check
    if candle.close <= Decimal::ZERO || candle.close.is_nan() {
        return OutlierType::Invalid;
    }

    if z_score.abs() > params.z_threshold && roc > params.rate_of_change_pct {
        if candle.volume_usd() < params.min_volume_usd {
            OutlierType::FlashCrashLowVolume // вероятный артефакт
        } else {
            OutlierType::FlashCrashReal // реальное событие
        }
    } else if z_score.abs() > params.z_threshold {
        OutlierType::StatisticalOutlier
    } else {
        OutlierType::Normal
    }
}

#[derive(Debug, Clone, PartialEq)]
enum OutlierType {
    Normal,
    StatisticalOutlier,
    FlashCrashLowVolume,  // удаляем/интерполируем
    FlashCrashReal,       // сохраняем с флагом (это реальная информация!)
    Invalid,              // OHLCV = 0 или NaN
}
```

### Метод исправления

| Тип | Действие | Причина |
|-----|----------|---------|
| `Invalid` | Заменить на интерполяцию | Битые данные не несут информации |
| `FlashCrashLowVolume` | Winsorize до 3σ | Скорее всего артефакт биржи |
| `FlashCrashReal` | **Оставить**, добавить флаг `is_flash_event` | Реальная ликвидация — полезна для стратегии |
| `StatisticalOutlier` | Оставить без изменений | Крипта волатильна, это нормально |

```rust
fn winsorize_candle(
    candle: &mut Candle,
    window: &[Candle],
    sigma_multiplier: f64,
) {
    let closes: Vec<f64> = window.iter().map(|c| c.close.to_f64()).collect();
    let mean = closes.iter().sum::<f64>() / closes.len() as f64;
    let std = (closes.iter().map(|c| (c - mean).powi(2)).sum::<f64>()
               / closes.len() as f64).sqrt();
    let upper = mean + sigma_multiplier * std;
    let lower = mean - sigma_multiplier * std;

    if candle.close.to_f64() > upper {
        candle.close = Decimal::from_f64(upper).unwrap();
        candle.high = candle.high.min(candle.close * dec!(1.001));
    }
    if candle.close.to_f64() < lower {
        candle.close = Decimal::from_f64(lower).unwrap();
        candle.low = candle.low.max(candle.close * dec!(0.999));
    }
}
```

### Edge cases

- **Каскадная ликвидация** — 10+ свечей с аномальными wicks. Z-score «привыкает» → **адаптивное окно** (HMM regime detection)
- **Листинг нового токена** — первые часы: огромная волатильность. Не outlier, а норма → исключить из обучающей выборки
- **Нулевой объём + нулевая цена** — Binance возвращает `[0,0,0,0,0,0,0]` для несуществующих свечей в batch-запросе

---

## 3. Wash Trading Detection

### Проблема

Wash trading — трейдер торгует сам с собой для создания искусственного объёма. На крипто-биржах особенно распространён на:
- Малых альткоинах (MCAP)
- DEX (автоматизированные wash-bots)
- Биржах с низкой комиссией (FTX до краха, OKX)

**Масштаб:** Исследования показывают 50–95% объёма на некоторых парах — wash trading.

### Метод обнаружения

```rust
/// Wash trading detection по нескольким сигналам
struct WashTradeScore {
    volume_consistency: f64,    // 0-1: насколько равномерен объём
    trade_size_distribution: f64, // 0-1: странное распределение размеров
    buy_sell_imbalance: f64,     // 0-1: нет естественного дисбаланса
    tick_pattern: f64,           // 0-1: trades occurring at regular intervals
    spread_anomaly: f64,         // 0-1: bid-ask spread аномалии
}

fn calculate_wash_score(trades: &[Trade], window_minutes: i64) -> WashTradeScore {
    // 1. Volume consistency — реальный рынок имеет неравномерный объём
    //    Wash trading имеет подозрительно равномерный объём (CV < 0.3)
    let volumes: Vec<f64> = /* агрегация по минутам */;
    let cv = coefficient_of_variation(&volumes);

    // 2. Trade size distribution — реальный рынок: смесь retail + whale
    //    Wash trading: один или два размера ордеров повторяются
    let sizes: Vec<f64> = trades.iter().map(|t| t.quantity.to_f64()).collect();
    let unique_ratio = unique_sizes_ratio(&sizes, tolerance: 0.001);

    // 3. Buy/Sell imbalance — реальный рынок: ~50/50 с трендом
    //    Wash trading: подозрительно идеальный 50/50
    let buy_count = trades.iter().filter(|t| t.is_buyer).count();
    let imbalance = (buy_count as f64 / trades.len() as f64 - 0.5).abs();

    // 4. Tick regularity — реальные trades приходят случайно
    //    Wash bot: trades через одинаковые интервалы
    let intervals: Vec<f64> = trades.windows(2)
        .map(|w| (w[1].timestamp - w[0].timestamp) as f64)
        .collect();
    let interval_cv = coefficient_of_variation(&intervals);

    WashTradeScore {
        volume_consistency: if cv < 0.3 { 1.0 } else { cv / 3.0 },
        trade_size_distribution: 1.0 - unique_ratio,
        buy_sell_imbalance: if imbalance < 0.02 { 1.0 } else { 0.0 },
        tick_pattern: if interval_cv < 0.2 { 1.0 } else { 0.0 },
        spread_anomaly: /* ... */,
    }
}

fn is_wash_trading(score: &WashTradeScore, threshold: f64) -> bool {
    let composite = score.volume_consistency * 0.25
        + score.trade_size_distribution * 0.25
        + score.buy_sell_imbalance * 0.20
        + score.tick_pattern * 0.15
        + score.spread_anomaly * 0.15;
    composite > threshold
}
```

### Метод исправления

**Не удалять wash trades из tick data** — мы не можем определить какие именно trades являются wash. Вместо этого:

1. **Пометить пару** флагом `wash_score: f64` (0.0 — чистая, 1.0 — 100% wash)
2. **Взвешенный volume** — `adjusted_volume = raw_volume × (1 - wash_score)`
3. **Фильтрация в стратегии** — не торговать пары с `wash_score > 0.7`
4. **При тренировке ML** — down-weight или exclude wash-пары

```rust
struct CleanedCandle {
    raw: Candle,
    wash_score: f64,
    adjusted_volume: Decimal,
    is_reliable: bool,
}

impl CleanedCandle {
    fn new(raw: Candle, wash_score: f64) -> Self {
        let adjusted = raw.volume * Decimal::from_f64(1.0 - wash_score).unwrap();
        CleanedCandle {
            raw,
            wash_score,
            adjusted_volume: adjusted,
            is_reliable: wash_score < 0.7,
        }
    }
}
```

### Edge cases

- **New listing pump** — объём высокий и «равномерный», но это не wash trading → использовать **listing date** как дополнительный фильтр
- **Market maker activity** — MM размещает обе стороны, это легитимно, но похоже на wash → проверять **spread** (MM spread узкий, wash spread может быть любым)
- **DEX wash bots** — on-chain прозрачность позволяет видеть self-trades напрямую → отдельный алгоритм

---

## 4. Exchange Data Discrepancies

### Проблема

Одна и та же пара (BTC/USDT) на разных биржах даёт разные:
- **Цены** — spread между биржами 0.01%–1%
- **Объёмы** — Binance > Coinbase > Kraken
- **Timestamps** — разная точность (ms vs sec), разное время закрытия свечи
- **OHLCV** — разные high/low из-за локальных ликвидаций

### Метод обнаружения

```rust
struct CrossExchangeValidator {
    max_price_deviation_pct: f64,  // обычно 2% для major pairs
    exchanges: Vec<ExchangeId>,
}

/// Сравнение одной свечи (timestamp) между биржами
fn detect_discrepancy(
    reference: &Candle,      // основная биржа (Binance)
    comparisons: &[Candle],  // другие биржи
    max_deviation: f64,
) -> Vec<Discrepancy> {
    let mut issues = Vec::new();
    for comp in comparisons {
        let price_diff = ((comp.close - reference.close) / reference.close)
            .abs().to_f64() * 100.0;
        if price_diff > max_deviation {
            issues.push(Discrepancy {
                timestamp: reference.timestamp,
                reference_exchange: reference.exchange,
                suspect_exchange: comp.exchange,
                price_diff_pct: price_diff,
                ref_price: reference.close,
                sus_price: comp.close,
            });
        }
    }
    issues
}
```

### Метод исправления

| Подход | Когда использовать |
|--------|-------------------|
| **Primary exchange only** | Стратегия работает на одной бирже |
| **Median price** | Arbitrage / мульти-биржевая стратегия |
| **Volume-weighted price** | Учитывает ликвидность каждой биржи |
| **Cross-validate, reject outliers** | Если одна биржа сильно отклоняется — пометить |

### Edge cases

- **Listing timing** — токен листится на Binance в 10:00, на Coinbase в 12:00 → до 12:00 данные несравнимы
- **Regional restrictions** — разные пары доступны в разных регионах (Binance US vs Global)
- **Stablecoin depeg** — USDT ≠ USDC ≠ DAI → цены в разных stablecoin несравнимы напрямую

---

## 5. Timezone Handling

### Проблема

- Биржи публикуют данные в **UTC** (Binance, Coinbase, Kraken)
- Некоторые агрегаторы (TradingView) могут использовать **локальное время пользователя**
- Фьючерсы CME — **Chicago time (CST/CDT)**
- Индикаторы с дневным периодом чувствительны к timezone (когда «день» начинается?)

### Правила

```rust
/// ВСЕГДА хранить в UTC миллисекундах
/// Конвертация только на уровне presentation/UI
struct Timestamp(i64); // UTC ms since epoch

impl Timestamp {
    fn now_utc() -> Self {
        Timestamp(chrono::Utc::now().timestamp_millis())
    }

    fn from_exchange(s: &str, exchange: &ExchangeConfig) -> Result<Self, TimeError> {
        // Конвертация из строки биржи в UTC ms
        // Учитываем формат каждой биржи
        match exchange.timezone {
            Tz::Utc => parse_utc(s),
            Tz::Cst => parse_cst_to_utc(s),
            _ => Err(TimeError::UnsupportedTimezone),
        }
    }
}
```

**Все внутренние расчёты в UTC ms. Никаких исключений.**

### Edge cases

- **DST переход** — если источник в локальном времени, DST создаёт «дублирующую» или «пропущенную» свечу
- **Дневные свечи** — «день» = 00:00–00:00 UTC. Если трейдер в GMT+8, его «день» начинается в 16:00 UTC → возможен расхождение с биржевым днём
- **CME futures** — закрытие в 16:00 CST ≠ полночь UTC

---

## 6. Corporate Actions (Airdrops, Forks, Splits)

### Проблема

В крипте нет «сплита акций», но есть аналогичные события:
- **Airdrops** — holders получают бесплатные токены (UNI для ETH holders)
- **Hard forks** — BTC → BCH (2017), ETH → ETH/ETC (2016)
- **Token swaps/migrations** — старый токен → новый (MATIC → POL)
- **Redenominations** — BTT old → BTT new (1:1000)
- **Rebases** — AMPL, OHM — supply меняется, цена корректируется

### Метод обнаружения

```rust
struct CorporateAction {
    action_type: ActionType,
    timestamp: i64,
    pair: String,
    ratio: Decimal,        // 1:N split / swap ratio
    source: ActionSource,  // Exchange API, CoinGecko, manual
}

#[derive(Debug, Clone)]
enum ActionType {
    Airdrop,
    HardFork,
    TokenSwap,
    Redenomination,
    Rebase,
}

/// Обнаружение: резкий gap в цене без объёма
/// (airdrop/fork создаёт gap, но не flash crash)
fn detect_corporate_action(
    candles: &[Candle],
    threshold_pct: f64,  // обычно >50%
) -> Vec<Candle> {
    candles.windows(2)
        .filter(|w| {
            let gap = ((w[1].open - w[0].close) / w[0].close)
                .abs().to_f64() * 100.0;
            gap > threshold_pct
        })
        .map(|w| w[1].clone())
        .collect()
}
```

### Метод исправления

**Для backtesting** — необходима **adjusted price series**:
- Pre-fork: цена делится на ratio
- Pre-airdrop: цена корректируется на стоимость airdrop
- Pre-swap: масштабируется по ratio

```rust
fn adjust_prices_for_action(
    candles: &mut [Candle],
    action: &CorporateAction,
) {
    // Все свечи ДО события корректируются
    for candle in candles.iter_mut() {
        if candle.timestamp < action.timestamp {
            candle.open = candle.open / action.ratio;
            candle.high = candle.high / action.ratio;
            candle.low = candle.low / action.ratio;
            candle.close = candle.close / action.ratio;
            candle.volume = candle.volume * action.ratio;
        }
    }
}
```

### Edge cases

- **Airdrop snapshot timing** — момент снимка ≠ момент получения токенов. Цена падает в момент snapshot (sell the news)
- **Contentious fork** — BCH/BSV split, где оба токена выживают. Нужно отслеживать оба
- **Rebase tokens** — цена и supply меняются одновременно. Использовать **market cap** вместо price для анализа

---

## 7. Survivorship Bias

### Проблема

Если backtest работает только на текущих списках токенов (Binance spot listing today), он **пропускает все токены, которые были удалены** (delisted). Это создаёт систематический upward bias:

- Delisted токены = плохие результаты → исключение = лучший backtest
- 50–80% токенов 2017 года — delisted или <1% от ATH

### Метод обнаружения

```rust
/// Список delisted токенов (исторический)
struct SurvivorshipAudit {
    /// Все токены, которые были когда-либо на бирже
    all_listed: HashMap<String, TokenListing>,
    /// Токены, которые сейчас активны
    currently_active: HashSet<String>,
    /// Delisted токены с датами
    delisted: Vec<DelistedToken>,
}

struct TokenListing {
    symbol: String,
    listing_date: NaiveDate,
    delisting_date: Option<NaiveDate>,
    delisting_price: Option<Decimal>,  // цена на момент delisting
}

impl SurvivorshipAudit {
    fn bias_report(&self) -> BiasReport {
        let total = self.all_listed.len();
        let delisted = self.delisted.len();
        let bias_factor = delisted as f64 / total as f64;

        BiasReport {
            total_ever_listed: total,
            currently_active: total - delisted,
            delisted_count: delisted,
            delisting_rate: bias_factor,
            // bias_factor > 0.3 = серьёзная проблема
            severity: if bias_factor > 0.5 { Severity::Critical }
                      else if bias_factor > 0.3 { Severity::High }
                      else { Severity::Low },
        }
    }

    /// Генерация universe на каждую дату в прошлом
    fn universe_at_date(&self, date: NaiveDate) -> Vec<String> {
        self.all_listed.values()
            .filter(|t| t.listing_date <= date)
            .filter(|t| t.delisting_date.map_or(true, |d| d >= date))
            .map(|t| t.symbol.clone())
            .collect()
    }
}
```

### Метод исправления

1. **Купить/собрать исторический listing data** — CoinGecko, CoinMarketCap исторические snapshots
2. **Backtest только на «живых на тот момент» токенах** — `universe_at_date(date)`
3. **Include delisted tokens** — собрать данные delisted токенов (они могут быть доступны в архивах)
4. **Report bias** — всегда указывать в отчёте: "X% токенов delisted, bias factor = Y"

### Edge cases

- **Exchange-level bias** — Binance vs Coinbase vs Kraken имеют разный delisting rate
- **Category bias** — DeFi токены delist быстрее, чем L1 chains
- **Surviving ≠ Performing** — токен может быть «живым», но 99.9% от ATH

---

## 8. Timestamp Alignment & Latency

### Проблема

- Binance закрывает 1-min свечу в `:00` секунду → свеча `[10:00:00, 10:00:59]` имеет timestamp `10:01:00`?
- Некоторые биржи закрывают свечу в `:59`, другие в `:00`
- WebSocket данные приходят с задержкой 50–500ms
- REST-поллинг каждые 5 секунд → может пропустить момент закрытия

### Правила

```rust
/// Стандартизация timestamp
/// Все свечи нормализуются к "началу периода"
/// 1-min свеча с open_time = 10:00:00 покрывает [10:00:00, 10:01:00)
fn normalize_candle_timestamp(candle: &mut Candle, interval_ms: i64) {
    // Округляем вниз до ближайшего интервала
    candle.timestamp = (candle.timestamp / interval_ms) * interval_ms;
}
```

### Edge cases

- **Leap seconds** — UTC включает leap seconds, но Unix timestamp их игнорирует. Практически не влияет
- **Биржа меняет формат** — Binance перешёл с `close_time` к `open_time` в некоторых API. Отслеживать версии API

---

## 9. Duplicate Candles

### Проблема

- WebSocket reconnect → те же данные дважды
- Batch API + stream → overlap
- Перезапись historical data биржей (редко, но бывает)

### Метод обнаружения

```rust
fn deduplicate(candles: &mut Vec<Candle>) -> usize {
    let before = candles.len();
    candles.sort_by_key(|c| (c.pair.clone(), c.timestamp, c.exchange.clone()));
    candles.dedup_by_key(|c| (c.pair.clone(), c.timestamp, c.exchange.clone()));
    before - candles.len()
}
```

**Ключ дедупликации:** `(exchange, pair, timestamp)`

Если один и тот же timestamp от одной биржи — **оставить более полную запись** (та, у которой volume > 0 или trades > 0).

---

## 10. Volume Anomalies

### Проблема

- **Zero volume candles** — нет сделок за период (нормально для мелких пар, аномально для BTC)
- **Volume spikes** — 100x от среднего (может быть реальным или wash trading)
- **Volume = 0, но цена изменилась** — баг API

### Метод обнаружения

```rust
fn detect_volume_anomaly(
    candle: &Candle,
    window: &[Candle],
) -> VolumeAnomaly {
    let volumes: Vec<f64> = window.iter().map(|c| c.volume.to_f64()).collect();
    let mean = volumes.iter().sum::<f64>() / volumes.len() as f64;
    let std = (volumes.iter().map(|v| (v - mean).powi(2)).sum::<f64>()
               / volumes.len() as f64).sqrt();

    let z = if std > 0.0 { (candle.volume.to_f64() - mean) / std } else { 0.0 };

    if candle.volume == Decimal::ZERO && candle.close != candle.open {
        VolumeAnomaly::ZeroVolumePriceChange
    } else if z > 5.0 {
        VolumeAnomaly::ExtremeSpike(z)
    } else if z < -3.0 && candle.volume == Decimal::ZERO {
        VolumeAnomaly::ZeroVolume(candle.pair.clone())
    } else {
        VolumeAnomaly::Normal
    }
}
```

---

## 11. OHLCV Consistency Violations

### Проблема

Фундаментальные правила OHLCV, которые **всегда** должны выполняться:

1. `High >= max(Open, Close)`
2. `Low <= min(Open, Close)`
3. `High >= Low`
4. `Open, Close ∈ [Low, High]`
5. `Volume >= 0`
6. `Timestamps уникальны` (в рамках одной пары/биржи)
7. `Price > 0`

```rust
fn validate_ohlcv(candle: &Candle) -> Vec<ValidationError> {
    let mut errors = Vec::new();

    if candle.high < candle.open || candle.high < candle.close {
        errors.push(ValidationError::HighBelowBody);
    }
    if candle.low > candle.open || candle.low > candle.close {
        errors.push(ValidationError::LowAboveBody);
    }
    if candle.high < candle.low {
        errors.push(ValidationError::HighBelowLow);
    }
    if candle.volume < Decimal::ZERO {
        errors.push(ValidationError::NegativeVolume);
    }
    if candle.close <= Decimal::ZERO {
        errors.push(ValidationError::ZeroOrNegativePrice);
    }
    errors
}
```

**Нарушения OHLCV = немедленное удаление свечи + замена интерполяцией.**

---

## 12. Decimal Precision & Rounding

### Проблема

Разные токены имеют разную точность:
- BTC/USDT: 2 знака (60000.00)
- SHIB/USDT: 10 знаков (0.0000123456)
- Binance tick size: 0.01 для BTC, 0.00000001 для SHIB

Float-арифметика (f64) теряет точность на малых ценах → использовать **Decimal** (rust_decimal).

```rust
use rust_decimal::Decimal;
use rust_decimal_macros::dec;

struct PriceConfig {
    tick_size: Decimal,    // минимальный шаг цены
    lot_size: Decimal,     // минимальный шаг количества
    min_notional: Decimal, // минимальная сумма ордера
}

fn round_to_tick(price: Decimal, config: &PriceConfig) -> Decimal {
    (price / config.tick_size).round() * config.tick_size
}
```

---

## 13. Delisted / Renamed Tokens

### Проблема

- **Переименование**: BTT (old) → BTT (new), MATIC → POL
- **Дублирование тикеров**: разные токены с одинаковым тикером на разных биржах
- **Delisting** без предупреждения (SEC enforcement)

### Решение: Mapping Table

```rust
/// Таблица маппинга токенов
struct TokenMapping {
    canonical_id: String,         // CoinGecko ID или внутренний UUID
    exchange_symbol: String,      // "BTC" на Binance
    exchange: ExchangeId,
    pair: String,                 // "BTCUSDT"
    valid_from: i64,              // когда этот маппинг стал действительным
    valid_to: Option<i64>,        // None = действующий
    renames: Vec<RenameEvent>,    // история переименований
}

struct RenameEvent {
    old_symbol: String,
    new_symbol: String,
    timestamp: i64,
}
```

---

## 14. Crypto-Specific: Binance Gap Filling

Binance-specific особенности:

| Аспект | Поведение Binance |
|--------|-------------------|
| REST API | Отсутствующие свечи **просто не включены** в ответ |
| WebSocket `kline` | Нет сообщения для пропущенной свечи |
| Historical data | Есть полные данные с listing date |
| Maintenance | Обычно 1–4 часа, с предупреждением на статус-странице |
| Zero trades | Свеча возвращается с `volume=0, trades=0` (не пропуск) |

**Рекомендация:** Для gap filling на Binance:
1. Использовать **WebSocket** как primary source (реал-тайм)
2. **REST fallback** — если WebSocket gap > 10 секунд, запрашивать REST `/api/v3/klines`
3. **Backfill из historical** — если пропуск > 1 часа, скачать исторический период
4. **Never interpolate without checking** — сначала проверить, есть ли данные в REST

---

## 15. Crypto-Specific: Wash Trading Cleanup

Специфичные паттерны wash trading на крипто-биржах:

### Binance
- **Менее проблематична** — комиссия 0.1% делает wash trading дорогим
- Но **Binance Zero-Fee events** (BTC/TUSD 2023) → всплеск wash trading

### DEX (Uniswap, PancakeSwap)
- **Арбитражные боты** создают огромный объём, но это не wash trading (разные адреса)
- **Sandwich attacks** — MEV боты создают «искусственные» trades
- **Метод**: проверять `tx.origin` vs `msg.sender` — если одно лицо обе стороны → wash

### Мелкие CEX
- **Наиболее проблематичны** — BitForex, ZB.com, и т.д.
- **Метод**: использовать **volume legitimacy scores** из независимых исследований (Bitwise 2019, CoinGecko trust score)

---

## Хранение данных

### Сравнительная таблица

| Критерий | CSV | Parquet | SQLite | PostgreSQL |
|----------|-----|---------|--------|------------|
| **Размер (2TB raw)** | ~2.5 TB | ~400 GB | ~1.8 TB | ~2.2 TB |
| **Скорость чтения** | 🟡 50 MB/s | 🟢 500 MB/s+ | 🟡 100 MB/s | 🟢 200 MB/s (indexed) |
| **Скорость записи** | 🟢 100 MB/s | 🟢 300 MB/s | 🟡 50 MB/s | 🟡 30 MB/s |
| **Columnar queries** | ❌ | 🟢 Нативный | ❌ | 🟡 Partial (BRIN) |
| **Schema evolution** | 🟢 Гибкий | 🟡 Добавление колонок OK | 🟡 ALTER TABLE | 🟢 ALTER TABLE |
| **Compression** | ❌ gzip отдельно | 🟢 Snappy/Zstd встроенный | ❌ | 🟢 TOAST |
| **Concurrent reads** | 🟢 Файлы | 🟢 Файлы | 🟡 WAL mode | 🟢 Отлично |
| **Concurrent writes** | ❌ | ❌ (immutable) | ❌ (один writer) | 🟢 MVCC |
| **Portability** | 🟢 Универсал | 🟡 Нужна библиотека | 🟢 Один файл | ❌ Сервер |
| **SQL queries** | ❌ | ❌ (DuckDB да) | 🟢 SQL | 🟢 SQL |
| **Incremental append** | 🟢 Дописать в конец | 🟢 Новый row group | 🟢 INSERT | 🟢 INSERT |
| **Time-series optimized** | ❌ | 🟡 Parquet с partitioning | ❌ | 🟡 TimescaleDB |

### Рекомендация: Гибридный подход

```
data/
├── raw/                          # Сырые данные (неизменяемые)
│   └── binance/
│       └── BTCUSDT/
│           ├── 2024/
│           │   ├── 01.parquet    # Parquet — колоночный, сжатый
│           │   ├── 02.parquet
│           │   └── ...
│           └── 2025/
├── clean/                        # Очищенные данные
│   └── binance/
│       └── BTCUSDT/
│           ├── 2024/
│           │   ├── 01.parquet    # С флагами качества
│           │   └── ...
├── features/                     # Рассчитанные фичи
│   └── binance/
│       └── BTCUSDT/
│           ├── 2024-01.arrow     # Apache Arrow для zero-copy
├── metadata/                     # Метаданные
│   ├── tokens.json               # Mapping таблица
│   ├── quality_report.json       # Отчёты по качеству
│   └── gaps.json                 # Индекс пропусков
└── index.db                      # SQLite — индекс поиска
```

**Обоснование:**

| Слой | Хранилище | Почему |
|------|-----------|--------|
| **Raw** | Parquet (partitioned by month) | Columnar compression, append-only, ~6x меньше CSV |
| **Clean** | Parquet | То же + флаги качества в колонках |
| **Features** | Apache Arrow / Parquet | Zero-copy чтение в Rust (arrow2 crate) |
| **Metadata** | JSON + SQLite | Быстрый поиск «есть ли данные для BTCUSDT за 2024-03?» |
| **Hot cache** | In-memory (HashMap) | Последние N свечей для стратегий в реальном времени |

**PostgreSQL** — **не рекомендуется** для primary storage на таком масштабе (2TB+):
- Требует тюнинга, индексов, партиционирования
- TimescaleDB помогает, но adds operational overhead
- Parquet + DuckDB даёт аналитический SQL поверх файлов без сервера

**PostgreSQL рекомендуется для:**
- Trade log (исполненные ордера) — < 1 GB, нужна ACID
- Configuration & state — настройки бота, позиции
- Alert history — лог алертов

---

## Pipeline Design

### Архитектура: ingest → validate → clean → store → serve

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐    ┌───────────┐
│   INGEST    │───▶│   VALIDATE   │───▶│    CLEAN    │───▶│   STORE   │───▶│   SERVE   │
│             │    │              │    │             │    │           │    │           │
│ WebSocket   │    │ OHLCV rules  │    │ Gap fill    │    │ Raw →     │    │ In-memory │
│ REST poll   │    │ Timestamp    │    │ Outliers    │    │ Parquet   │    │ cache     │
│ Historical  │    │ Duplicates   │    │ Duplicates  │    │ Clean →   │    │ Arrow     │
│ backfill    │    │ Gaps detect  │    │ Wash score  │    │ Parquet   │    │ queries   │
│             │    │ Volume check │    │ Normalize   │    │ Index →   │    │ REST API  │
│             │    │              │    │             │    │ SQLite    │    │           │
└─────────────┘    └──────────────┘    └─────────────┘    └───────────┘    └───────────┘
       │                  │                   │                  │                │
       ▼                  ▼                   ▼                  ▼                ▼
  ┌─────────┐      ┌───────────┐      ┌────────────┐    ┌───────────┐   ┌──────────────┐
  │ Metrics │      │ Validation│      │ Cleaning   │    │ Storage   │   │ Serving      │
  │ counter │      │ report    │      │ report     │    │ metrics   │   │ latency      │
  │ (Prom)  │      │ (JSON)    │      │ (JSON)     │    │ (Prom)    │   │ histogram    │
  └─────────┘      └───────────┘      └────────────┘    └───────────┘   └──────────────┘
```

### Стадия 1: INGEST

```rust
/// Сбор данных из разных источников
#[async_trait]
trait DataIngester {
    async fn fetch_candles(
        &self,
        pair: &str,
        interval: Interval,
        start: i64,
        end: i64,
    ) -> Result<Vec<Candle>, IngestError>;

    async fn subscribe_live(
        &self,
        pair: &str,
        interval: Interval,
    ) -> Result<mpsc::Receiver<Candle>, IngestError>;
}

struct BinanceIngester {
    ws_client: BinanceWsClient,
    rest_client: BinanceRestClient,
    rate_limiter: RateLimiter,
}

/// Historical backfill — загрузка данных с listing date
async fn backfill(
    &self,
    pair: &str,
    interval: Interval,
) -> Result<Vec<Candle>, IngestError> {
    let listing_date = self.get_listing_date(pair).await?;
    let mut all_candles = Vec::new();
    let mut cursor = listing_date;

    while cursor < Utc::now().timestamp_millis() {
        let batch = self.fetch_candles(pair, interval, cursor, cursor + 1000 * 60 * 1000).await?;
        all_candles.extend(batch);
        cursor += 1000 * 60 * 1000; // 1000 минут за запрос
        self.rate_limiter.wait().await;
    }
    Ok(all_candles)
}
```

### Стадия 2: VALIDATE

```rust
struct ValidationPipeline {
    validators: Vec<Box<dyn Validator>>,
}

trait Validator {
    fn name(&self) -> &str;
    fn validate(&self, candles: &[Candle]) -> ValidationReport;
}

struct ValidationReport {
    total_candles: usize,
    passed: usize,
    failed: usize,
    issues: Vec<ValidationIssue>,
    severity_counts: HashMap<Severity, usize>,
}

/// Валидаторы (порядок важен!)
fn build_validation_pipeline() -> ValidationPipeline {
    ValidationPipeline {
        validators: vec![
            Box::new(TimestampValidator),      // 1. Хронологический порядок
            Box::new(DuplicateValidator),       // 2. Дубликаты
            Box::new(OhlcvConsistencyValidator),// 3. H≥max(O,C), L≤min(O,C)
            Box::new(PriceValidator),           // 4. Цена > 0
            Box::new(VolumeValidator),          // 5. Volume ≥ 0
            Box::new(GapDetector),              // 6. Пропуски
            Box::new(OutlierDetector),          // 7. Статистические выбросы
            Box::new(VolumeAnomalyDetector),    // 8. Объёмные аномалии
        ],
    }
}
```

### Стадия 3: CLEAN

```rust
struct CleaningPipeline {
    cleaners: Vec<Box<dyn Cleaner>>,
}

trait Cleaner {
    fn name(&self) -> &str;
    fn clean(&self, candles: &mut Vec<Candle>, report: &ValidationReport) -> CleaningReport;
}

fn build_cleaning_pipeline() -> CleaningPipeline {
    CleaningPipeline {
        cleaners: vec![
            Box::new(DuplicateCleaner),        // Удаление дубликатов
            Box::new(OhlcvRepairCleaner),       // Исправление H/L нарушений
            Box::new(GapFillCleaner),           // Заполнение пропусков
            Box::new(OutlierCleaner),           // Winsorize или flag
            Box::new(WashScoreCleaner),         // Расчёт wash trading score
            Box::new(TimestampNormalizer),      // Нормализация timestamps
        ],
    }
}
```

### Стадия 4: STORE

```rust
struct StoragePipeline {
    raw_writer: ParquetWriter,      // raw/ exchange/pair/year/month.parquet
    clean_writer: ParquetWriter,    // clean/ exchange/pair/year/month.parquet
    index_db: SqliteIndex,          // metadata/index.db
    metadata_writer: MetadataWriter,// metadata/tokens.json, quality_report.json
}

impl StoragePipeline {
    async fn store(&self, pair: &str, raw: &[Candle], clean: &[Candle], report: &CleaningReport) {
        // 1. Raw → Parquet (append to monthly file)
        self.raw_writer.append(pair, raw).await?;

        // 2. Clean → Parquet (append to monthly file)
        self.clean_writer.append(pair, clean).await?;

        // 3. Update index
        self.index_db.upsert_range(pair, raw[0].timestamp, raw.last().unwrap().timestamp).await?;

        // 4. Store quality report
        self.metadata_writer.save_report(pair, report).await?;
    }
}
```

### Стадия 5: SERVE

```rust
/// Интерфейс для стратегий — чтение очищенных данных
trait DataProvider {
    /// Последние N свечей (in-memory cache)
    fn latest(&self, pair: &str, n: usize) -> &[Candle];

    /// Диапазон свечей (из Parquet)
    async fn range(
        &self,
        pair: &str,
        start: i64,
        end: i64,
    ) -> Result<Vec<Candle>, DataError>;

    /// Свеча по точному timestamp
    async fn at(&self, pair: &str, timestamp: i64) -> Result<Option<Candle>, DataError>;

    /// Есть ли данные для диапазона?
    async fn has_data(&self, pair: &str, start: i64, end: i64) -> Result<bool, DataError>;
}
```

---

## Rust-архитектура модуля

### Структура crates

```
crates/
├── data-quality/
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── validate/
│       │   ├── mod.rs
│       │   ├── ohlcv.rs          # OHLCV consistency checks
│       │   ├── gaps.rs           # Gap detection
│       │   ├── outliers.rs       # Statistical outlier detection
│       │   ├── volume.rs         # Volume anomaly detection
│       │   ├── duplicates.rs     # Deduplication
│       │   └── wash_trading.rs   # Wash trading scoring
│       ├── clean/
│       │   ├── mod.rs
│       │   ├── gap_fill.rs       # Forward fill, interpolation
│       │   ├── outlier_clean.rs  # Winsorization, flagging
│       │   ├── dedup.rs          # Duplicate removal
│       │   └── normalize.rs      # Timestamp, decimal normalization
│       ├── store/
│       │   ├── mod.rs
│       │   ├── parquet.rs        # Parquet read/write
│       │   ├── sqlite_index.rs   # SQLite metadata index
│       │   └── metadata.rs       # JSON metadata management
│       ├── pipeline/
│       │   ├── mod.rs
│       │   ├── ingest.rs         # Data ingestion from exchanges
│       │   ├── validate.rs       # Validation pipeline orchestrator
│       │   ├── clean.rs          # Cleaning pipeline orchestrator
│       │   └── serve.rs          # Data serving / provider
│       └── types/
│           ├── mod.rs
│           ├── candle.rs         # Candle struct (Decimal OHLCV)
│           ├── error.rs          # Error types
│           └── quality.rs        # Quality report structs
```

### Зависимости (Cargo.toml)

```toml
[dependencies]
rust_decimal = "1"              # Точная арифметика цен
rust_decimal_macros = "1"
chrono = "0.4"                  # Время
arrow2 = "0.18"                 # Apache Arrow (zero-copy)
parquet2 = "0.18"               # Parquet чтение/запись
rusqlite = { version = "0.31", features = ["bundled"] }  # SQLite
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
tracing = "0.1"                 # Structured logging
statrs = "0.17"                 # Статистические функции
```

### Key structs

```rust
/// Свеча — основная единица данных
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candle {
    pub exchange: ExchangeId,
    pub pair: String,
    pub timestamp: i64,           // UTC ms, начало периода
    pub interval: Interval,       // 1m, 5m, 1h, 1d
    pub open: Decimal,
    pub high: Decimal,
    pub low: Decimal,
    pub close: Decimal,
    pub volume: Decimal,
    pub quote_volume: Decimal,
    pub trades: u64,
    pub taker_buy_volume: Decimal,
    pub taker_buy_quote_volume: Decimal,

    // Quality flags (added during cleaning)
    pub quality: CandleQuality,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CandleQuality {
    pub is_filled: bool,          // Forward-filled / interpolated
    pub is_adjusted: bool,        // Adjusted for corporate action
    pub wash_score: f64,          // 0.0 = clean, 1.0 = 100% wash
    pub outlier_score: f64,       // Z-score at time of validation
    pub source_count: u8,         // Сколько источников подтвердили
    pub flags: Vec<QualityFlag>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum QualityFlag {
    GapFilled,
    OutlierWinsorized,
    FlashEvent,          // Реальный flash crash, не артефакт
    LowVolume,
    CrossValidated,      // Проверено на другой бирже
    CorporateAction,
    SurvivorshipWarning,
}
```

---

## Топ-5 рекомендаций

| # | Рекомендация | Приоритет | Обоснование |
|---|-------------|-----------|-------------|
| 1 | **Все цены в Decimal, все timestamps в UTC ms** | ⭐⭐⭐ | Предотвращает 80% precision и timezone багов |
| 2 | **Raw data immutable, clean data отдельно** | ⭐⭐⭐ | Возможность пересоздать clean при изменении алгоритма |
| 3 | **Wash trading score на уровне пары, не свечи** | ⭐⭐ | Невозможно определить конкретный wash trade; score на уровне пары достаточно |
| 4 | **Parquet для хранения, SQLite для индекса** | ⭐⭐⭐ | Оптимальное сочетание для 2TB+ time-series |
| 5 | **Validation pipeline как отдельный crate** | ⭐⭐ | Возможность запускать standalone, CI/CD integration, перезапуск при изменении правил |

---

## Связи с другими модулями

| Модуль | Связь |
|--------|-------|
| **Агент 1–5 (Индикаторы)** | Потребляют clean OHLCV, получают флаг `is_filled` |
| **Агент 6 (Статистика)** | HMM/GARCH требуют clean данные без outlier-артефактов |
| **Агент 9 (Метрики)** | Sharpe/Sortino чувствительны к survivorship bias |
| **Агент 10 (Execution)** | Wash trading score влияет на выбор пар для торговли |
| **Агент 16 (Crypto-specific)** | Funding rate / OI данные требуют отдельной валидации |
| **Агент 17 (On-chain)** | Альтернативный источник для cross-validation |
