# Агент 16: Крипто-специфичные метрики (Crypto-Specific)

**Дата:** 2026-04-17  
**Назначение:** Полный аудит крипто-специфичных метрик для торгового бота. Формулы, API-источники, edge cases, Rust-реализация, сигналы.  
**Исходники:** Crypto Metrics.md, Crypto Onchain.md, Research Indicators.md

---

## Содержание

1. [Сводная таблица аудита](#сводная-таблица-аудита)
2. [Деривативные метрики (7)](#деривативные-метрики)
3. [On-chain метрики (7)](#on-chain-метрики)
4. [Индексные/сентимент-метрики (2)](#индексные-метрики)
5. [Funding Rate — глубокий разбор](#funding-rate-глубокий-разбор)
6. [Open Interest — глубокий разбор](#open-interest-глубокий-разбор)
7. [Liquidation Clusters — глубокий разбор](#liquidation-clusters-глубокий-разбор)
8. [Топ-3 рекомендации](#топ-3-рекомендации)
9. [Межметричные комбинации](#межметричные-комбинации)
10. [Rust-архитектура](#rust-архитектура)

---

## Сводная таблица аудита

| # | Метрика | Категория | Решение | MVP | Приоритет |
|---|---------|-----------|---------|-----|-----------|
| 1 | Funding Rate | Деривативы | ✅ | 0.1 | ⭐⭐⭐ |
| 2 | Open Interest | Деривативы | ✅ | 0.1 | ⭐⭐⭐ |
| 3 | Liquidation Clusters | Деривативы | ✅ | 0.4 | ⭐⭐ |
| 4 | Futures Basis | Деривативы | ✅ | 0.3 | ⭐ |
| 5 | Long/Short Ratio | Деривативы | ✅ | 0.2 | ⭐⭐ |
| 6 | Taker Buy/Sell Ratio | Деривативы | ✅ | 0.3 | ⭐ |
| 7 | Exchange Net Flow | Деривативы+On-chain | ✅ | 0.4 | ⭐ |
| 8 | NVT Ratio | On-chain | ✅ | 0.4 | ⭐ |
| 9 | MVRV Z-Score | On-chain | ✅ | 0.3 | ⭐⭐ |
| 10 | SOPR | On-chain | ✅ | 0.4 | ⭐ |
| 11 | NUPL | On-chain | ✅ | 0.3 | ⭐ |
| 12 | SSR (Stablecoin Supply Ratio) | On-chain | ✅ | 0.4 | ⭐ |
| 13 | Active Addresses | On-chain | ❌ | — | — |
| 14 | Puell Multiple | On-chain | ❌ | — | — |
| 15 | Stock-to-Flow | On-chain | ❌ | — | — |
| 16 | Hash Rate | On-chain | ❌ | — | — |
| 17 | Fear & Greed Index | Сентимент | ⚠️ | 0.3 | ⭐ |
| 18 | Whale Alerts | Микроструктура | ⚠️ | 0.4 | ⭐ |

**Легенда:** ⭐⭐⭐ = MVP-критичный, ⭐⭐ = высокий приоритет, ⭐ = полезный, ❌ = отклонён, ⚠️ = упрощённая версия

---

## Деривативные метрики

### 1. Funding Rate (Ставка финансирования)

**Статус:** ✅ MVP 0.1 (критичный)

#### Формула

```
Funding Rate = Premium Index + Clamp(BaseInterestRate − PremiumIndex, −0.05%, +0.05%)

Premium Index = (Max(0, ImpactBidPrice − IndexPrice) − Max(0, IndexPrice − ImpactAskPrice)) / IndexPrice
Base Interest Rate = 0.01% за 8 часов (~10.95% годовых на Binance)
```

#### Сигнальная модель

**Positive funding → longs платят shorts → перекупленность.**

```
Z-score = (FR_current − μ_FR) / σ_FR

| Z-score | Интерпретация |
|---------|---------------|
| Z > +2.0 | Экстремальная перекупленность → сигнал шорта |
| Z > +1.0 | Повышенный оптимизм |
| Z ∈ [-1, +1] | Норма |
| Z < −1.0 | Пессимизм (шорты доминируют) |
| Z < −2.0 | Экстремальная перепроданность → сигнал лонга |
```

**Пороговые значения абсолюта:**
- FR > 0.05%/8h — умеренная перекупленность
- FR > 0.10%/8h — сильная перекупленность
- FR > 0.75%/8h — cap (Binance лимит), истинный дисбаланс выше
- FR < −0.03%/8h — шорты доминируют

#### Источники данных (API)

| Биржа | Endpoint | Формат |
|-------|----------|--------|
| Binance | `GET /fapi/v1/fundingRate?symbol=BTCUSDT&limit=1000` | JSON массив |
| Binance (текущая) | `GET /fapi/v1/premiumIndex?symbol=BTCUSDT` | JSON объект |
| Bybit | `GET /v5/market/funding/history?category=linear&symbol=BTCUSDT` | JSON |
| OKX | `GET /api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP` | JSON |
| CoinGlass | `https://open-api.coinglass.com/public/v2/funding?symbol=BTC` | JSON |

#### Edge Cases

1. **FR = 0.000%**: рынок в равновесии. Z-score ≈ 0, сигнал отсутствует. При σ < 0.001% — отложить сигнал.
2. **FR на cap (0.75%)**: истинный дисбаланс неизвестен. Флаг `cap_reached`, не использовать для Z-score (или обрезать).
3. **Резкий скачок при экспирации квартала**: фильтровать даты экспирации (март, июнь, сентябрь, декабрь).
4. **Менее 30 наблюдений**: использовать абсолютные пороги вместо Z-score.
5. **Разные интервалы**: Binance = 8h, Bybit = 8h, OKX = 8h, но некоторые биржи — 4h. Нормализовать.

#### Rust-реализация

```rust
/// Структура для хранения исторических ставок финансирования.
#[derive(Debug, Clone)]
pub struct FundingRateData {
    pub timestamp: i64,
    pub rate: f64,  // доля, например 0.0001 = 0.01%
}

/// Расчёт Z-score для ставки финансирования.
pub fn funding_rate_zscore(
    history: &[FundingRateData],
    window: usize,
    current_rate: f64,
) -> Option<f64> {
    if history.len() < window {
        return None;
    }
    let recent: Vec<f64> = history.iter()
        .rev()
        .take(window)
        .map(|d| d.rate)
        .collect();
    
    let mean = recent.iter().sum::<f64>() / recent.len() as f64;
    let variance = recent.iter()
        .map(|r| (r - mean).powi(2))
        .sum::<f64>() / recent.len() as f64;
    let std_dev = variance.sqrt();
    
    if std_dev < 1e-6 {
        return None;  // недостаточная вариативность
    }
    
    Some((current_rate - mean) / std_dev)
}

/// Генерация сигнала на основе Z-score.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FundingSignal {
    ExtremeOverbought,  // Z > +2.0
    Overbought,         // Z > +1.0
    Neutral,
    Oversold,           // Z < −1.0
    ExtremeOversold,    // Z < −2.0
    CapReached,         // FR на лимите биржи
}

pub fn funding_signal(zscore: Option<f64>, raw_rate: f64, cap: f64) -> FundingSignal {
    // Проверка cap
    if raw_rate.abs() >= cap * 0.95 {
        return FundingSignal::CapReached;
    }
    match zscore {
        None => FundingSignal::Neutral,
        Some(z) if z > 2.0 => FundingSignal::ExtremeOverbought,
        Some(z) if z > 1.0 => FundingSignal::Overbought,
        Some(z) if z < -2.0 => FundingSignal::ExtremeOversold,
        Some(z) if z < -1.0 => FundingSignal::Oversold,
        _ => FundingSignal::Neutral,
    }
}

/// Mean-reversion сигнал: ожидание возврата Z через порог ±1.0.
pub fn mean_reversion_trigger(
    prev_zscore: f64,
    curr_zscore: f64,
    threshold: f64,
) -> Option<bool> {
    // Вернуться за порог после экстремума
    if prev_zscore.abs() > 2.0 && curr_zscore.abs() <= threshold {
        return Some(prev_zscore < 0.0); // true = лонг-сигнал
    }
    None
}
```

---

### 2. Open Interest (Открытый интерес)

**Статус:** ✅ MVP 0.1 (критичный)

#### Формула

```
ΔOI = OI_current − OI_previous
ΔOI% = (ΔOI / OI_previous) × 100%

OI-Weighted Price = Σ(Price_i × OI_i) / Σ(OI_i)  (по биржам)
```

#### Сигнальная матрица (Цена × OI)

| Цена | OI | Интерпретация | Сигнал |
|------|----|--------------|--------|
| ↗ | ↗ | Новый капитал + быки | ✅ Подтверждение тренда |
| ↗ | ↘ | Short squeeze | ⚠️ Слабый рост |
| ↘ | ↗ | Новый капитал в шорты | ✅ Подтверждение падения |
| ↘ | ↘ | Уход капитала | ⚠️ Возможен разворот |

#### Источники данных

| Биржа | Endpoint |
|-------|----------|
| Binance | `GET /fapi/v1/openInterest?symbol=BTCUSDT` |
| Binance (история) | `GET /futures/data/openInterestHist?symbol=BTCUSDT&period=1h&limit=500` |
| Bybit | `GET /v5/market/open-interest?category=linear&symbol=BTCUSDT&interval=1h` |
| OKX | `GET /api/v5/public/open-interest?instId=BTC-USDT-SWAP` |
| CoinGlass | `https://open-api.coinglass.com/public/v2/open_interest?symbol=BTC&interval=1h` |

#### Edge Cases

1. **OI растёт без движения цены** → «накопление», направление неопределено, не генерировать направленный сигнал.
2. **OI обнуляется при экспирации** → исключить даты экспирации из расчёта дивергенций.
3. **Крупный ордер меняет OI** → использовать медианное изменение за 4h вместо моментального.
4. **Разные единицы измерения** (контракты vs BTC vs USD) → приводить к долларовому эквиваленту.

#### Пороговые значения

| Порог | ΔOI за день | Действие |
|-------|-------------|----------|
| Нормальный | < +10% | Стандарт |
| Накопление | > +15% | Внимание |
| Каскад-риск | > +30% | Высокий риск ликвидаций |
| Массовое закрытие | < −20% | Возможен разворот |

#### Rust-реализация

```rust
#[derive(Debug, Clone)]
pub struct OiSnapshot {
    pub timestamp: i64,
    pub oi_usd: f64,
    pub price: f64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PriceOiRegime {
    NewCapitalBullish,   // цена ↗ OI ↗
    ShortSqueeze,        // цена ↗ OI ↘
    NewCapitalBearish,   // цена ↘ OI ↗
    CapitalFlight,       // цена ↘ OI ↘
    Accumulation,        // цена ~ OI ↗
}

pub fn classify_regime(
    price_delta_pct: f64,
    oi_delta_pct: f64,
    price_threshold: f64,  // например 0.5%
    oi_threshold: f64,     // например 5%
) -> PriceOiRegime {
    let price_up = price_delta_pct > price_threshold;
    let price_down = price_delta_pct < -price_threshold;
    let oi_up = oi_delta_pct > oi_threshold;
    let oi_down = oi_delta_pct < -oi_threshold;

    match (price_up, price_down, oi_up, oi_down) {
        (true, _, true, _)  => PriceOiRegime::NewCapitalBullish,
        (true, _, _, true)  => PriceOiRegime::ShortSqueeze,
        (_, true, true, _)  => PriceOiRegime::NewCapitalBearish,
        (_, true, _, true)  => PriceOiRegime::CapitalFlight,
        (false, false, true, _) => PriceOiRegime::Accumulation,
        _ => PriceOiRegime::CapitalFlight, // default
    }
}

/// Сглаживание OI медианой за окно (фильтр выбросов).
pub fn smoothed_oi_change(snapshots: &[OiSnapshot], window_hours: usize) -> Option<f64> {
    if snapshots.len() < window_hours + 1 {
        return None;
    }
    let mut changes: Vec<f64> = Vec::new();
    for i in 1..=window_hours {
        let idx = snapshots.len() - i;
        let prev = snapshots[idx - 1].oi_usd;
        let curr = snapshots[idx].oi_usd;
        if prev > 0.0 {
            changes.push((curr - prev) / prev * 100.0);
        }
    }
    changes.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let mid = changes.len() / 2;
    Some(changes[mid])  // медиана
}
```

---

### 3. Liquidation Clusters (Ликвидационные каскады)

**Статус:** ✅ v0.4

#### Модель детектирования

```
Шаг 1: Подсчёт ликвидаций в скользящем окне W секунд
  Каскад = count(ликвидации в W) > K

Шаг 2: Совокупный объём
  Σ_ликвидаций = Σ(price_i × quantity_i)

Шаг 3: Доминирующая сторона
  Доминирование = Σ_long_liquidations / (Σ_long + Σ_short)
  > 0.7 → ликвидация лонгов (цена падает)
  < 0.3 → ликвидация шортов (цена растёт)
```

#### Параметры

| Параметр | Значение | Описание |
|----------|----------|----------|
| W (окно) | 60 сек | Скользящее окно |
| K (порог каскада) | 10 событий | Минимум для активации |
| Завершение каскада | < 3 событий за 60 сек | Возможная точка входа |

#### Источники данных (WebSocket)

| Биржа | URL / Топик |
|-------|-------------|
| Binance | `wss://fstream.binance.com/ws/btcusdt@forceOrder` |
| Bybit | `wss://stream.bybit.com/v5/public/linear` (топик `liquidation`) |
| OKX | `wss://ws.okx.com:8443/ws/v5/public` (топик `liquidation-orders`) |
| CoinGlass REST | `GET /public/v2/liquidation?symbol=BTC&time_type=all` |

#### Edge Cases

1. **Iceberg liquidations** → крупные позиции ликвидируются частями. Учитывать кумулятивный объём за 30 сек (если > $500K →潜在ная скрытая ликвидация).
2. **Малоликвидные пары** → работать только с парами, у которых объём > $100M/день.
3. **Задержка WebSocket** → сортировать по timestamp события (поле `E`), не по времени приёма.
4. **Дубли** → дедуплицировать по `E + p + q`.

#### Rust-реализация

```rust
use std::collections::VecDeque;

#[derive(Debug, Clone)]
pub struct LiquidationEvent {
    pub timestamp: i64,     // мс
    pub symbol: String,
    pub side: LiquidationSide,
    pub price: f64,
    pub quantity: f64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LiquidationSide {
    LongLiquidated,   // SELL force order
    ShortLiquidated,  // BUY force order
}

pub struct CascadeDetector {
    window_ms: i64,
    cascade_threshold: usize,
    completion_threshold: usize,
    events: VecDeque<LiquidationEvent>,
}

impl CascadeDetector {
    pub fn new(window_ms: i64, cascade_threshold: usize) -> Self {
        Self {
            window_ms,
            cascade_threshold,
            completion_threshold: 3,
            events: VecDeque::new(),
        }
    }

    pub fn add_event(&mut self, event: LiquidationEvent) -> CascadeStatus {
        // Удалить устаревшие события
        let cutoff = event.timestamp - self.window_ms;
        while self.events.front().map_or(false, |e| e.timestamp < cutoff) {
            self.events.pop_front();
        }
        // Дедупликация
        if self.events.iter().any(|e| {
            e.timestamp == event.timestamp
                && (e.price - event.price).abs() < 0.01
                && (e.quantity - event.quantity).abs() < 1e-8
        }) {
            return CascadeStatus::Duplicate;
        }
        self.events.push_back(event);
        let count = self.events.len();
        
        if count >= self.cascade_threshold {
            let long_vol: f64 = self.events.iter()
                .filter(|e| e.side == LiquidationSide::LongLiquidated)
                .map(|e| e.price * e.quantity)
                .sum();
            let short_vol: f64 = self.events.iter()
                .filter(|e| e.side == LiquidationSide::ShortLiquidated)
                .map(|e| e.price * e.quantity)
                .sum();
            let total = long_vol + short_vol;
            let dominance = if total > 0.0 { long_vol / total } else { 0.5 };
            CascadeStatus::Cascade { count, dominance, total_volume_usd: total }
        } else if count >= self.cascade_threshold / 2 {
            CascadeStatus::Accumulating(count)
        } else {
            CascadeStatus::Normal
        }
    }
}

#[derive(Debug)]
pub enum CascadeStatus {
    Normal,
    Duplicate,
    Accumulating(usize),
    Cascade {
        count: usize,
        dominance: f64,  // > 0.7 = longs liquidated
        total_volume_usd: f64,
    },
    Completion,  // < completion_threshold после каскада
}
```

---

### 4. Futures Basis (Базис фьючерсов)

**Статус:** ✅ v0.3

#### Формула

```
Basis = Цена_фьючерса − Цена_спота
Basis% = ((Futures − Spot) / Spot) × 100%
Annualized Basis = Basis% × (365 / days_to_expiry)

Term Structure Spread = Basis_дальний − Basis_ближний
```

#### Сигналы

| Базис (годовых) | Состояние | Сигнал |
|-----------------|-----------|--------|
| 0%–5% | Норма | — |
| 5%–15% | Повышенный оптимизм | Осторожность |
| > 15% | Перегрев | Медвежий |
| < 0% | Бэквардация | Бычий (перевёрнутый рынок) |

#### API

- Binance: `GET /fapi/v1/premiumIndex` (mark price + index price)
- Bybit: `GET /v5/market/tickers?category=linear`
- OKX: `GET /api/v5/public/funding-rate?instId=BTC-USDT-SWAP`

#### Edge Cases

1. Базис → 0 при экспирации (< 7 дней) — не генерировать сигналы.
2. Разные номиналы контрактов → приводить к USD.
3. Разные спот-цены между биржами → использовать индекс (5 площадок).

---

### 5. Long/Short Ratio

**Статус:** ✅ v0.2

#### Формула

```
L/S Ratio = Long positions / Short positions

Divergence_топов_vs_ритейла = L/S_топы − L/S_все
```

#### Сигналы

| L/S Ratio | Сигнал |
|-----------|--------|
| 0.9–1.1 | Нейтраль |
| > 1.3 или < 0.7 | Внимание |
| > 2.0 или < 0.5 | Контарианский сигнал |
| \|Δ топы vs ритейл\| > 0.5 | Сильный сигнал против ритейла |

#### API

- Binance: `GET /futures/data/topLongShortPositionRatio?symbol=BTCUSDT&period=1h`
- Binance (все): `GET /futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h`
- Bybit: `GET /v5/market/account-ratio?category=linear&symbol=BTCUSDT`

---

### 6. Taker Buy/Sell Volume Ratio

**Статус:** ✅ v0.3

#### Формула

```
Taker Buy/Sell Ratio = Taker Buy Volume / Taker Sell Volume
Buy Dominance% = (Taker Buy / Total) × 100%
```

#### Сигналы

| Ratio | Сигнал |
|-------|--------|
| 0.95–1.05 | Нейтраль |
| > 1.1 | Бычий импульс |
| < 0.9 | Медвежий импульс |
| > 1.5 или < 0.67 | Экстремальный перекос |

#### API

- Binance Futures: `GET /futures/data/takerlongshortRatio?symbol=BTCUSDT&period=1h`
- Binance Spot: `GET /api/v3/aggTrades` (поле `m`: true = buyer is taker)

---

### 7. Exchange Net Flow (Чистый поток на биржи)

**Статус:** ✅ v0.4

#### Формула

```
Net Flow = Приток_на_биржи − Отток_с_бирж
30d Cumulative = Σ(Net_Flow_day_i)
```

#### Сигналы (BTC)

| Net Flow / день | Сигнал |
|-----------------|--------|
| −1K до −5K BTC | Умеренный бычий |
| −5K до −10K BTC | Бычий |
| < −10K BTC | Сильный бычий (накопление) |
| +1K до +5K BTC | Умеренный медвежий |
| > +10K BTC | Сильный медвежий (распределение) |

#### API

- Glassnode: `GET /v1/metrics/transactions/transfers_volume_sum` (платный)
- CryptoQuant: `GET /v1/exchange-flows/netflow?exchange=all&symbol=btc&window=day`
- CoinMetrics: `GET /v4/timeseries/asset-metrics?assets=btc&metrics=FlowInExNtv,FlowOutExNtv`

#### Edge Cases

1. Внутренние переводы бирж (Binance cold→hot) → фильтруются провайдерами.
2. Миграция между биржами → нейтрализуется при агрегации.
3. Сезонные паттерны перед хардфорками → фильтровать известные события.

---

## On-chain метрики

### 8. NVT Ratio (Network Value to Transactions)

**Статус:** ✅ v0.4

#### Формула

```
NVT = Market Cap / Daily Transaction Volume (USD)
NVT Signal = SMA(NVT, 90)  // сглажённая версия
```

#### Сигналы

| NVT Signal | Сигнал |
|------------|--------|
| < 50 | Бычий (сеть недооценена) |
| 50–150 | Нейтраль |
| > 150 | Медвежий (переоценка) |

**Аналог P/E для крипты.** Высокий NVT = капитализация растёт быстрее транзакций.

#### API

- CoinMetrics: `GET /v4/timeseries/asset-metrics?assets=btc&metrics=NVTAdj`
- Glassnode: `GET /v1/metrics/indicators/nvt` (платный)

#### Edge Cases

1. **Batching** (exchange sends) → один tx содержит сотни выводов, NVT занижается. Использовать NVT на основе adjusted volume.
2. **SegWit/Lightning** → часть объёма уходит off-chain, NVT завышается.
3. **Молодой альткоин** → NVT нестабилен первые 6 месяцев, не использовать.

#### Rust-реализация

```rust
pub fn nvt_signal(market_cap: f64, daily_tx_volume: f64, nvt_history: &[f64], period: usize) -> Option<f64> {
    if daily_tx_volume <= 0.0 {
        return None;
    }
    let nvt = market_cap / daily_tx_volume;
    if nvt_history.len() < period {
        return Some(nvt); // без сглаживания
    }
    let sma: f64 = nvt_history.iter().rev().take(period).sum::<f64>() / period as f64;
    Some(sma)
}
```

---

### 9. MVRV Z-Score

**Статус:** ✅ v0.3

#### Формула

```
MVRV = Market Cap / Realized Cap
Z-Score = (Market Cap − Realized Cap) / StdDev(Market Cap)
```

Где Realized Cap = Σ(цена_при_последнем_перемещении_i × количество_BTC_i)

#### Сигналы

| MVRV / Z | Сигнал |
|----------|--------|
| MVRV < 1.0 (Z < 0) | Зона покупки (дно) |
| MVRV 1.0–2.5 | Нейтраль |
| MVRV > 2.5 | Осторожность |
| MVRV > 3.5 (Z > 7) | Зона продажи (исторический верх) |

#### API

- Glassnode: `GET /v1/metrics/market/mvrv`
- CoinMetrics: `GET /v4/timeseries/asset-metrics?assets=btc&metrics=CapMVRVCur`
- LookIntoBitcoin: веб-интерфейс (бесплатно)

#### Edge Cases

1. Только BTC и ETH — короткая история альткоинов не даёт надёжного MVRV.
2. Миграция монет обновляет realized price без реальной продажи.
3. 3–4M потерянных BTC систематически занижают realized cap → MVRV завышен. Корректировка через циклические пороги.

---

### 10. SOPR (Spent Output Profit Ratio)

**Статус:** ✅ v0.4

#### Формула

```
SOPR = Σ(цена_при_перемещении_i) / Σ(цена_при_получении_i)
aSOPR = SMA(SOPR, 7)  // сглаженная
```

#### Сигналы

| SOPR | Сигнал |
|------|--------|
| < 0.95 | Капитуляция → покупка |
| ≈ 1.00 | Уровень поддержки/сопротивления |
| > 1.10 | Экстремальная прибыль → осторожность |

**Ключевой insight:** SOPR = 1.0 в бычьем тренде — сильный уровень поддержки (держатели не продают в убыток).

#### API

- Glassnode: `GET /v1/metrics/indicators/sopr`
- CoinMetrics: `GET /v4/timeseries/asset-metrics?assets=btc&metrics=Sopru`
- LookIntoBitcoin: бесплатно

---

### 11. NUPL (Net Unrealized Profit/Loss)

**Статус:** ✅ v0.3

#### Формула

```
NUPL = (Market Cap − Realized Cap) / Market Cap
NUPL = (MVRV − 1) / MVRV  (эквивалентно)
```

#### Зоны

| NUPL | Зона | Сигнал |
|------|------|--------|
| < 0 | Capitulation | Покупка |
| 0–0.25 | Hope | Накопление |
| 0.25–0.5 | Optimism | Нейтраль |
| 0.5–0.75 | Belief | Осторожность |
| > 0.75 | Euphoria | Продажа |

---

### 12. SSR (Stablecoin Supply Ratio)

**Статус:** ✅ v0.4

#### Формула

```
SSR = BTC Market Cap / Total Stablecoin Supply
log_SSR = ln(SSR)
```

**Логика:** низкий SSR = много «сухого порошка» (стейблкоинов), готового к покупке → бычий.

#### Сигналы

| SSR | Сигнал |
|-----|--------|
| < 4 (log < 0.6) | Заряженный рынок → бычий |
| 4–10 | Нейтраль |
| > 10 (log > 1.0) | Разряженный → медвежий |

#### API

- CoinGecko: supply USDT + USDC + DAI
- CoinMetrics: `GET /v4/timeseries/asset-metrics?assets=btc&metrics=SplySSR`
- Glassnode: `GET /v1/metrics/stableserv/ssr`

---

### 13. Active Addresses — ❌ ОТКЛОНЁНО

**Причина:** Лагает за ценой (не опережающий), нет чётких торговых сигналов. Адресная активность коррелирует с ценой, а не предсказывает её.

### 14. Puell Multiple — ❌ ОТКЛОНЁНО

**Формула:** `Puell = Daily Issuance (USD) / 365-day MA of Daily Issuance`  
**Причина:** Специфичен только для PoW монет (BTC). После перехода ETH на PoS потерял универсальность. Заменён на MVRV/NUPL.

### 15. Stock-to-Flow — ❌ ОТКЛОНЁНО

**Причина:** Модель PlanB предсказывала $100K BTC к концу 2021. Не сбылось. Модель опровергнута эмпирически. Не использовать.

### 16. Hash Rate — ❌ ОТКЛОНЁНО

**Причина:** Лагирующий индикатор, зависит от энергетических рынков, а не от спроса. Не даёт торговых сигналов.

---

## Индексные метрики

### 17. Fear & Greed Index — ⚠️ Упрощённая версия (v0.3)

**Источник:** Alternative.me API (`https://api.alternative.me/fng/?limit=0`)

| Значение | Интерпретация | Сигнал |
|----------|--------------|--------|
| 0–25 | Extreme Fear | Контарианский лонг |
| 25–45 | Fear | Осторожный лонг |
| 45–55 | Neutral | — |
| 55–75 | Greed | Осторожный шорт |
| 75–100 | Extreme Greed | Контарианский шорт |

**Использовать только как secondary фильтр**, не primary сигнал. Источники: объём Google Trends, Twitter/X, волатильность, доминирование BTC, опросы.

### 18. Whale Alerts — ⚠️ Упрощённая версия (v0.4)

**Источник:** Whale Alert API или мониторинг крупных переводов через blockchain explorers.

```
Порог: перевод > $10M на биржу =潜在ный selling pressure
Перевод > $10M с биржи =潜在ное накопление
```

**Edge case:** внутренние переводы бирж фильтровать по known addresses.

---

## Funding Rate — глубокий разбор

### Как positive funding работает как сигнал перекупленности

```
Positive Funding (FR > 0):
  → Держатели LONG платят держателям SHORT
  → Стоимость удержания лонга растёт
  → Рынок перекошен в сторону покупок
  → Контарианский сигнал: перекупленность

Negative Funding (FR < 0):
  → Держатели SHORT платят держателям LONG
  → Рынок перекошен в сторону продаж
  → Контарианский сигнал: перепроданность
```

### Пороговые значения (3 уровня)

| Уровень | FR (8h) | Z-score | Действие |
|---------|---------|---------|----------|
| ⚠️ V0 | > 0.03% | Z > 1.0 | Мониторинг |
| 🟡 V1 | > 0.05% | Z > 1.5 | Готовность к шорту |
| 🔴 V2 | > 0.10% | Z > 2.0 | Активный шорт-сигнал |
| 💀 V3 | > 0.75% | cap | Экстремум, сильный mean-reversion |

### Term Structure

```
Spread = FR_квартальный − FR_бессрочный
Spread > 0 → контанго (здоровый рынок)
Spread < 0 → инверсия (аномалия → разворот)
```

---

## Open Interest — глубокий разбор

### Растущий OI + растущая цена = новый капитал

Это классический «здоровый» тренд: новые деньги входят в рынок, подтверждая движение. В отличие от short squeeze (растущая цена + падающий OI), где рост вызван закрытием позиций, а не новым спросом.

### Сигнальная логика

```rust
// Основной сигнал подтверждения тренда
fn oi_confirming_trend(price_change: f64, oi_change: f64) -> bool {
    // Бычий тренд: оба растут
    if price_change > 0.0 && oi_change > 0.0 {
        return true; // новый капитал подтверждает
    }
    // Медвежий тренд: цена падает, OI растёт
    if price_change < 0.0 && oi_change > 0.0 {
        return true; // новые шорты подтверждают
    }
    false
}

// Детекция short squeeze
fn is_short_squeeze(price_change: f64, oi_change: f64) -> bool {
    price_change > 0.0 && oi_change < -5.0 // цена растёт, OI падает
}
```

### Дивергенция OI vs Цена

```
Медвежья дивергенция: новый ценовой high + снижающийся OI
  → рост без капитала → сигнал продажи

Бычья дивергенция: новый ценовой low + растущий OI  
  → капитал накапливается на дне → сигнал покупки
```

---

## Liquidation Clusters — глубокий разбор

### Как использовать данные о ликвидациях

#### 1. Карта ликвидаций (Liquidation Map)

На основе открытых позиций с известными уровнями ликвидации:

```
Liquidation Density(price) = Σ(positions_liquidated_at_price) / шаг_цены

Cluster = ценовая зона, где Liquidation Density > порога
```

#### 2. Тактическое использование

| Фаза | Действие |
|------|----------|
| До каскада | Не открывать позицию «против» скопления ликвидаций |
| Во время каскада | Приостановить все входы |
| После каскада (< 3 ликвидаций/60с) | Mean-reversion вход в направлении, обратном каскаду |

#### 3. Уровни ликвидаций как поддержка/сопротивление

```
Если > $50M ликвидаций сконцентрировано на уровне X:
  → уровень X = магнит для цены
  → после прохождения X = каскад → ускорение
  → перед X = поддержка/сопротивление
```

#### 4. Rust-реализация карты

```rust
use std::collections::BTreeMap;

pub struct LiquidationMap {
    /// цена → суммарный объём ликвидаций (USD)
    levels: BTreeMap<i64, f64>,  // цена × 100 как ключ
}

impl LiquidationMap {
    pub fn add_position(&mut self, liquidation_price: f64, volume_usd: f64) {
        let key = (liquidation_price * 100.0) as i64;
        *self.levels.entry(key).or_insert(0.0) += volume_usd;
    }

    /// Найти ближайший кластер ликвидаций к текущей цене.
    pub fn nearest_cluster(&self, current_price: f64, min_volume: f64) -> Option<(f64, f64)> {
        let key = (current_price * 100.0) as i64;
        // Ищем в обе стороны от текущей цены
        let below = self.levels.range(..=key).rev()
            .find(|(_, &vol)| vol >= min_volume);
        let above = self.levels.range(key..)
            .find(|(_, &vol)| vol >= min_volume);
        
        match (below, above) {
            (Some((&k, &v)), Some((&k2, &v2))) => {
                let d1 = (k as f64 / 100.0 - current_price).abs();
                let d2 = (k2 as f64 / 100.0 - current_price).abs();
                if d1 < d2 { Some((k as f64 / 100.0, v)) }
                else { Some((k2 as f64 / 100.0, v2)) }
            }
            (Some((&k, &v)), _) => Some((k as f64 / 100.0, v)),
            (_, Some((&k, &v))) => Some((k as f64 / 100.0, v)),
            _ => None,
        }
    }
}
```

---

## Топ-3 рекомендации

### 🥇 #1: Funding Rate

**Почему лучший:**
- Единственная метрика, напрямую измеряющая **стоимость удержания позиции** и **дисбаланс long/short**
- Бесплатные API, данные каждые 8 часов — нет зависимости от платных провайдеров
- Z-score даёт нормализованный сигнал, сравнимый между периодами и активами
- Mean-reversion свойство — экстремальные значения исторически возвращаются к среднему
- Уже в MVP 0.1 — минимальная интеграционная сложность
- **Сигнальная сила:** контарианский сигнал (перекупленность/перепроданность), подтверждённый на множестве циклов

**Ключевой use case:** фильтр против тренда. Если стратегия даёт лонг-сигнал, а FR Z-score > +2.0 → подавить или уменьшить позицию.

### 🥈 #2: Open Interest (с матрицей Цена × OI)

**Почему второй:**
- Единственная метрика, показывающая **суммарное вовлечение капитала** в деривативы
- Матрица 2×2 (Цена × OI) даёт 4 чётких режима рынка: подтверждение тренда, short squeeze, накопление, уход капитала
- Детекция short squeeze — уникальная возможность, недоступная в классическом ТА
- Бесплатные API, данные в реальном времени
- Комбинация с Funding Rate = мощнейший дуэт: FR показывает перекупленность, OI подтверждает/опровергает капиталом

**Ключевой use case:** определение «здоровья» тренда. Растущая цена + растущий OI = тренд жив. Растущая цена + падающий OI = squeeze, осторожность.

### 🥉 #3: MVRV Z-Score

**Почему третий:**
- Наиболее надёжная метрика для **определения циклических верхов и низов** BTC
- Использует ончейн-данные (реальные цены приобретения) — невозможно подделать
- Чёткие исторические пороги: Z < 0 = дно (2015, 2018, 2022), Z > 7 = верх (2017, 2021)
- Никакой классический ТА-индикатор не даёт такой картины «справедливой стоимости» на макроуровне
- NUPL и SOPR — его «родственники», но MVRV более устойчив

**Ключевой use case:** макро-фильтр. Если MVRV > 3.5 → уменьшить общий экспозишн, даже если краткосрочные сигналы bullish. Если MVRV < 1.0 → агрессивное накопление.

### Почему не другие

| Метрика | Почему не топ-3 |
|---------|----------------|
| Liquidation Clusters | Требует WebSocket, сложнее в реализации, данные неполные |
| Long/Short Ratio | Полезен, но менее уникален (дублирует часть Funding Rate) |
| NVT | Молод для альткоинов, batched transactions искажают |
| SOPR | Производная от on-chain, менее устойчив чем MVRV |
| Exchange Net Flow | Требует платных API (Glassnode) |
| Fear & Greed | Субъективный индекс, не даёт точных порогов |

---

## Межметричные комбинации

### Сильный бычий сигнал (максимальная уверенность)

```
Funding Rate: Z-score < −2.0 (шорты перегружены, платят лонгам)
  И
Open Interest: растёт (новый капитал входит)
  И
MVRV: < 1.5 (рынок недооценён)
→ Тройное подтверждение: контарианский + капитал + стоимость
```

### Сильный медвежий сигнал

```
Funding Rate: Z-score > +2.0 (лонги перегружены)
  И
Open Interest: падает при растущей цене (short squeeze, не новый капитал)
  И
MVRV: > 3.5 (переоценка)
→ Тройное предупреждение: перекупленность + слабый рост + переоценка
```

### Предупреждение о каскаде ликвидаций

```
OI: растёт > +15% за день
  И
L/S Ratio: топы vs ритейл расходятся (Δ > 0.5)
  И
Basis: > 10% годовых (перегретый рынок)
  И
Funding Rate: на cap-уровне
→ Каскад-риск: приостановить входы
```

### Комбинационная скоринг-модель

```rust
pub struct CryptoSignalScore {
    pub funding_zscore: Option<f64>,      // -3..+3
    pub oi_regime: Option<PriceOiRegime>,
    pub mvrv: Option<f64>,
    pub nupl: Option<f64>,
    pub sopr: Option<f64>,
}

impl CryptoSignalScore {
    /// Композитный скор от -1.0 (сильный шорт) до +1.0 (сильный лонг).
    pub fn composite_score(&self) -> f64 {
        let mut score = 0.0;
        let mut weight_sum = 0.0;

        // Funding Rate: вес 0.35 (самый надёжный)
        if let Some(z) = self.funding_zscore {
            let s = -z / 3.0; // инвертируем: высокий FR = шорт-скор
            score += s * 0.35;
            weight_sum += 0.35;
        }

        // OI Regime: вес 0.25
        if let Some(ref regime) = self.oi_regime {
            let s = match regime {
                PriceOiRegime::NewCapitalBullish => 0.8,
                PriceOiRegime::ShortSqueeze => -0.3,
                PriceOiRegime::NewCapitalBearish => -0.8,
                PriceOiRegime::CapitalFlight => 0.2,
                PriceOiRegime::Accumulation => 0.4,
            };
            score += s * 0.25;
            weight_sum += 0.25;
        }

        // MVRV: вес 0.20
        if let Some(mvrv) = self.mvrv {
            let s = if mvrv < 1.0 { 1.0 } else if mvrv > 3.5 { -1.0 }
                    else { (2.5 - mvrv) / 2.5 };
            score += s * 0.20;
            weight_sum += 0.20;
        }

        // NUPL: вес 0.10
        if let Some(nupl) = self.nupl {
            let s = if nupl < 0.0 { 1.0 } else if nupl > 0.75 { -1.0 }
                    else { (0.5 - nupl) / 0.5 };
            score += s * 0.10;
            weight_sum += 0.10;
        }

        // SOPR: вес 0.10
        if let Some(sopr) = self.sopr {
            let s = if sopr < 0.95 { 0.8 } else if sopr > 1.10 { -0.8 }
                    else { (1.05 - sopr) / 0.1 };
            score += s * 0.10;
            weight_sum += 0.10;
        }

        if weight_sum > 0.0 { score / weight_sum } else { 0.0 }
    }
}
```

---

## Rust-архитектура

### Структура модуля

```
src/
├── metrics/
│   ├── mod.rs
│   ├── funding_rate.rs      // MVP 0.1
│   ├── open_interest.rs     // MVP 0.1
│   ├── long_short.rs        // v0.2
│   ├── mvrv.rs              // v0.3
│   ├── nupl.rs              // v0.3
│   ├── basis.rs             // v0.3
│   ├── taker_ratio.rs       // v0.3
│   ├── sopr.rs              // v0.4
│   ├── nvt.rs               // v0.4
│   ├── ssr.rs               // v0.4
│   ├── exchange_flow.rs     // v0.4
│   └── liquidation.rs       // v0.4
├── sentiment/
│   ├── mod.rs
│   ├── fear_greed.rs        // v0.3
│   └── whale_alerts.rs      // v0.4
├── signal/
│   ├── mod.rs
│   └── crypto_composite.rs  // композитный скор
└── api/
    ├── mod.rs
    ├── binance.rs
    ├── bybit.rs
    ├── okx.rs
    └── providers/
        ├── glassnode.rs     // v0.3+
        ├── coinglass.rs
        └── cryptoquant.rs
```

### Трейт-абстракция

```rust
use async_trait::async_trait;

/// Абстракция для любой крипто-метрики.
#[async_trait]
pub trait CryptoMetric: Send + Sync {
    /// Название метрики.
    fn name(&self) -> &str;

    /// Обновить данные (запрос к API).
    async fn refresh(&mut self) -> Result<(), MetricError>;

    /// Получить текущее значение (нормализованное).
    fn current_value(&self) -> Option<f64>;

    /// Получить сигнал.
    fn signal(&self) -> MetricSignal;

    /// Вес в композитном скоре (0.0–1.0).
    fn weight(&self) -> f64;
}

#[derive(Debug, Clone, Copy)]
pub enum MetricSignal {
    StrongBuy,
    Buy,
    Neutral,
    Sell,
    StrongSell,
    InsufficientData,
}

#[derive(Debug, thiserror::Error)]
pub enum MetricError {
    #[error("API error: {0}")]
    ApiError(String),
    #[error("Insufficient data: need {need}, have {have}")]
    InsufficientData { need: usize, have: usize },
    #[error("Rate limited, retry after {retry_after_ms}ms")]
    RateLimited { retry_after_ms: u64 },
}
```

### Конфигурация (YAML)

```yaml
crypto_metrics:
  funding_rate:
    enabled: true
    z_score_window: 30
    z_score_threshold_long: -2.0
    z_score_threshold_short: 2.0
    api_source: binance_futures
    weight: 0.35

  open_interest:
    enabled: true
    change_threshold_alert: 0.15
    change_threshold_cascade: 0.30
    aggregation_window: 4h
    weight: 0.25

  mvrv:
    enabled: false  # v0.3
    buy_threshold: 1.0
    sell_threshold: 3.5
    weight: 0.20

  liquidation:
    enabled: false  # v0.4
    websocket_url: "wss://fstream.binance.com/ws/btcusdt@forceOrder"
    cascade_threshold: 10
    window_seconds: 60
```

---

## Итоги

1. **Аудитировано 18 метрик:** 12 принято (7 деривативных + 5 on-chain), 2 упрощены (Fear & Greed, Whale Alerts), 4 отклонены (Active Addresses, Puell Multiple, Stock-to-Flow, Hash Rate).

2. **Топ-3:** Funding Rate (контарианский, Z-score нормализация), Open Interest (капитал + матрица 2×2), MVRV Z-Score (макро-оценка цикла).

3. **Stock-to-Flow отклонён** — модель опровергнута в 2022.

4. **Композитный скор** на основе взвешенной комбинации Funding Rate (35%), OI (25%), MVRV (20%), NUPL (10%), SOPR (10%).

5. **Интеграция:** поэтапная от MVP 0.1 (FR + OI) до v0.4 (полный набор с WebSocket и платными API).

---

*Документ: 16-crypto-specific.md*  
*Агент: 16 — Crypto-Specific Metrics Specialist*  
*Дата: 2026-04-17*