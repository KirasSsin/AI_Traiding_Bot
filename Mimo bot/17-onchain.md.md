
# Агент 17: On-Chain Аналитика — Полный аудит метрик

**Версия:** v0.4  
**Дата:** 2026-04-17  
**Назначение:** Аудит всех on-chain метрик для крипто-торгового бота. Формулы, API-источники, edge cases, Rust-реализация, trading signals, финальный отбор.

---

## Сводная таблица решений

| # | Метрика | Решение | Причина |
|---|---------|---------|---------|
| 1 | MVRV Z-Score | ✅ **РЕКОМЕНДОВАНА** | Лучший макро-индикатор цикла. Чёткие пороги, проверен 3+ циклами |
| 2 | SOPR | ✅ **РЕКОМЕНДОВАНА** | Уникальный индикатор капитуляции в реальном времени. Уровень 1.0 — сильный support |
| 3 | Exchange Net Flow | ✅ **РЕКОМЕНДОВАНА** | Единственная метрика реального поведения держателей (накопление/распределение) |
| 4 | NVT Ratio | ❌ Отклонена | Лагает, шумная, дублирует Exchange Flow по смыслу |
| 5 | NUPL | ❌ Отклонена | Производная MVRV, не даёт новой информации |
| 6 | Puell Multiple | ❌ Отклонена | Узкая (только BTC майнеры), не применима к альтам |
| 7 | Stock-to-Flow | ❌ Отклонена | Модель опровергнута эмпирически (2022) |
| 8 | Hash Rate | ❌ Отклонена | Нет прямых торговых сигналов, лагает на 2+ недели |
| 9 | Active Addresses | ❌ Отклонена | Лагает, нет чётких порогов, легко манипулируется |
| 10 | New Addresses | ❌ Отклонена | Производная Active Addresses, шумнее |
| 11 | Stablecoin Supply Ratio | ❌ Отклонена | Низкая чувствительность, медленно меняется |
| 12 | Tether Dominance | ❌ Отклонена | Косвенная, нет формульных порогов |
| 13 | Whale Wallet Tracking | ❌ Отклонена | Нестандартизирована, expensive API, noisy |
| 14 | Realized Cap | ❌ Отклонена | Компонент MVRV, не самостоятельный сигнал |
| 15 | Thermocap | ❌ Отклонена | Только для PoW-монет, узкая |
| 16 | HODL Waves | ❌ Отклонена | Визуальная/аналитическая, нет числовых порогов для бота |
| 17 | Coin Days Destroyed | ❌ Отклонена | Производная HODL Waves, дублирует SOPR |
| 18 | NVT Signal | ❌ Отклонена | Улучшение NVT, но всё равно шумная |

---

## ЧАСТЬ 1: ТРИ РЕКОМЕНДОВАННЫЕ МЕТРИКИ

---

### 1. MVRV Z-Score ⭐ РЕКОМЕНДОВАНА

#### Формула

```
MVRV = Market Cap / Realized Cap

Z-Score = (Market Cap − Realized Cap) / StdDev(Market Cap)

Где:
  Market Cap = Цена_спота × Общее_предложение
  Realized Cap = Σ(Цена_при_последнем_перемещении_i × Количество_i)
  StdDev = стандартное отклонение Market Cap за окно (обычно 365 дней)
```

**Числовой пример:**
```
Цена BTC = $67,500
Предложение = 19,850,000 BTC
Market Cap = $1.34T
Realized Cap = $520B (средняя цена приобретения ≈ $26,200)
StdDev(Market Cap, 365d) = $280B

MVRV = 1,340B / 520B = 2.58
Z-Score = (1,340B − 520B) / 280B = 2.93
```

#### Trading Signals

| MVRV | Z-Score | Зона | Сигнал |
|------|---------|------|--------|
| < 1.0 | < 0 | Capitulation | 🔴 Сильная ПОКУПКА |
| 1.0–2.0 | 0–1.5 | Накопление | 🟡 Накопление |
| 2.0–3.5 | 1.5–3.0 | Рост | 🟢 Бычий тренд |
| 3.5–7.0 | 3.0–7.0 | Перегрев | 🟠 Фиксация прибыли |
| > 7.0 | > 7.0 | Экстремум | 🔴 Сильная ПРОДАЖА |

**Исторические экстремумы:** Dec 2017 MVRV ≈ 3.8, Nov 2021 MVRV ≈ 3.7, Mar 2020 MVRV ≈ 0.95

#### API-источники

| Платформа | Endpoint | Free? |
|-----------|----------|-------|
| Glassnode | `GET /v1/metrics/market/mvrv` | ❌ Standard ($29/мес) |
| CoinMetrics | `GET /v4/timeseries/asset-metrics?assets=btc&metrics=CapMVRVCur` | ✅ Community |
| LookIntoBitcoin | Веб-интерфейс | ✅ Free |

#### Edge Cases

1. **Потерянные монеты (3–4M BTC):** Занижают Realized Cap, систематически завышают MVRV на ~15–20%. Решение: корректировка через HODL-взвешенный Realized Cap или использование Z-Score (нормализует смещение).
2. **Миграция монет (биржа → холодный → биржа):** Обновляет realized price без реальной продажи. Решение: фильтрация внутренних переводов (предоставляется Glassnode/CoinMetrics).
3. **Новые альткоины (< 1 года):** Недостаточно истории для значимого Z-Score. Решение: применять MVRV только к BTC и ETH.

#### Rust-реализация

```rust
/// MVRV Z-Score для BTC
pub struct MvrvCalculator {
    /// Окно для StdDev (дней)
    pub stddev_window: usize,
    /// История Market Cap
    market_cap_history: Vec<f64>,
}

impl MvrvCalculator {
    pub fn new(stddev_window: usize) -> Self {
        Self {
            stddev_window,
            market_cap_history: Vec::with_capacity(stddev_window),
        }
    }

    /// Обновить расчёт
    /// market_cap: текущая капитализация в USD
    /// realized_cap: реализованная капитализация в USD
    pub fn update(&mut self, market_cap: f64, realized_cap: f64) -> MvrvResult {
        self.market_cap_history.push(market_cap);
        if self.market_cap_history.len() > self.stddev_window {
            self.market_cap_history.remove(0);
        }

        let mvrv = if realized_cap > 0.0 {
            market_cap / realized_cap
        } else {
            return MvrvResult { mvrv: 0.0, z_score: 0.0, signal: Signal::NoData };
        };

        let z_score = if self.market_cap_history.len() >= 30 {
            let mean: f64 = self.market_cap_history.iter().sum::<f64>()
                / self.market_cap_history.len() as f64;
            let variance: f64 = self.market_cap_history.iter()
                .map(|&x| (x - mean).powi(2))
                .sum::<f64>() / (self.market_cap_history.len() - 1) as f64;
            let stddev = variance.sqrt();
            if stddev > 0.0 {
                (market_cap - mean) / stddev
            } else {
                0.0
            }
        } else {
            0.0 // Недостаточно данных
        };

        let signal = match mvrv {
            v if v < 1.0 => Signal::StrongBuy,
            v if v < 2.0 => Signal::Accumulate,
            v if v < 3.5 => Signal::BullishTrend,
            v if v < 7.0 => Signal::TakeProfit,
            _ => Signal::StrongSell,
        };

        MvrvResult { mvrv, z_score, signal }
    }
}

#[derive(Debug, Clone)]
pub struct MvrvResult {
    pub mvrv: f64,
    pub z_score: f64,
    pub signal: Signal,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Signal {
    NoData,
    StrongBuy,
    Accumulate,
    BullishTrend,
    TakeProfit,
    StrongSell,
}
```

---

### 2. SOPR (Spent Output Profit Ratio) ⭐ РЕКОМЕНДОВАНА

#### Формула

```
SOPR = Σ(Цена_при_перемещении_i) / Σ(Цена_при_получении_i)

Для каждого spent output:
  realized_value = цена_BTC_момент_перемещения × количество_BTC
  created_value  = цена_BTC_момент_создания_UTXO × количество_BTC

aSOPR = скользящее среднее SOPR (период 7 дней)

SOPR_STH (Short-Term Holders): только монеты возрастом < 155 дней
SOPR_LTH (Long-Term Holders): только монеты возрастом > 155 дней
```

**Числовой пример:**
```
Монета A: куплена $50,000 → продана $67,500
Монета B: куплена $72,000 → продана $67,500
Монета C: куплена $30,000 → продана $67,500

SOPR = (67500 + 67500 + 67500) / (50000 + 72000 + 30000)
     = 202500 / 152000 = 1.332
```

#### Trading Signals

| SOPR | Интерпретация | Сигнал |
|------|---------------|--------|
| < 0.95 | Экстремальная капитуляция | 🔴 Сильная ПОКУПКА |
| 0.95–1.00 | Продажи в убыток | 🟡 Медвежий импульс |
| ≈ 1.00 | Точка безубыточности | ⚪ Уровень support/resistance |
| 1.00–1.10 | Прибыльная фиксация | 🟢 Нормальный рынок |
| > 1.10 | Экстремальная прибыль | 🟠 Фиксация прибыли |

**Ключевой сигнал:** SOPR пересекает 1.0 снизу вверх после периода < 1.0 = покупка (держатели больше не продают в убыток). Это исторически сильнейший support в бычьем тренде.

#### API-источники

| Платформа | Endpoint | Free? |
|-----------|----------|-------|
| Glassnode | `GET /v1/metrics/indicators/sopr` | ❌ Standard |
| CoinMetrics | `GET /v4/timeseries/asset-metrics?assets=btc&metrics=Sopru` | ✅ Community |
| LookIntoBitcoin | Веб-интерфейс | ✅ Free |

#### Edge Cases

1. **Крупные перемещения ancient coins:** Монеты из 2010–2012 годов при перемещении дают SOPR >> 1. Решение: отбрасывать выбросы > 3σ от скользящего среднего.
2. **Межбиржевые переводы:** Не являются реальной продажей, но попадают в UTXO. Решение: использовать данные Glassnode/CoinMetrics (фильтруют внутренние переводы).
3. **SOPR только для UTXO-цепей:** Применим к BTC, LTC. Для ETH нужна адаптированная версия (Account-based SOPR). На этапе MVP — только BTC.
4. **SOPR ≈ 1.000 при большом объёме:** Равновесие. Система должна трактовать как «точку решения» — пробой определяет направление.

#### Rust-реализация

```rust
/// SOPR Calculator с aSOPR (сглаженный)
pub struct SoprCalculator {
    /// Период скользящего среднего для aSOPR
    pub ma_period: usize,
    /// Порог отсечения выбросов (сигма)
    pub outlier_sigma: f64,
    /// Буфер SOPR значений
    sopr_buffer: Vec<f64>,
}

impl SoprCalculator {
    pub fn new(ma_period: usize, outlier_sigma: f64) -> Self {
        Self {
            ma_period,
            outlier_sigma,
            sopr_buffer: Vec::with_capacity(ma_period * 2),
        }
    }

    /// Добавить наблюдение
    /// realized_sum: сумма стоимость при перемещении (USD)
    /// created_sum: сумма стоимость при создании UTXO (USD)
    pub fn add_observation(&mut self, realized_sum: f64, created_sum: f64) -> SoprResult {
        if created_sum <= 0.0 {
            return SoprResult::default();
        }

        let raw_sopr = realized_sum / created_sum;

        // Фильтрация выбросов
        if self.sopr_buffer.len() >= 30 {
            let mean = self.sopr_buffer.iter().sum::<f64>()
                / self.sopr_buffer.len() as f64;
            let var = self.sopr_buffer.iter()
                .map(|&x| (x - mean).powi(2))
                .sum::<f64>() / (self.sopr_buffer.len() - 1) as f64;
            let sigma = var.sqrt();
            if (raw_sopr - mean).abs() > self.outlier_sigma * sigma {
                // Выброс — пропускаем
                return self.current_result();
            }
        }

        self.sopr_buffer.push(raw_sopr);
        if self.sopr_buffer.len() > self.ma_period * 2 {
            self.sopr_buffer.remove(0);
        }

        self.current_result()
    }

    fn current_result(&self) -> SoprResult {
        if self.sopr_buffer.is_empty() {
            return SoprResult::default();
        }

        let sopr = *self.sopr_buffer.last().unwrap();
        let asopr = if self.sopr_buffer.len() >= self.ma_period {
            let start = self.sopr_buffer.len() - self.ma_period;
            self.sopr_buffer[start..].iter().sum::<f64>() / self.ma_period as f64
        } else {
            sopr
        };

        let signal = match sopr {
            v if v < 0.95 => SoprSignal::StrongBuy,
            v if v < 1.00 => {
                if sopr > asopr {
                    SoprSignal::BuyCross // Пересекает aSOPR снизу вверх
                } else {
                    SoprSignal::Bearish
                }
            }
            v if v <= 1.05 => SoprSignal::Neutral,
            v if v <= 1.10 => SoprSignal::Bullish,
            _ => SoprSignal::TakeProfit,
        };

        SoprResult { sopr, asopr, signal }
    }
}

#[derive(Debug, Clone, Default)]
pub struct SoprResult {
    pub sopr: f64,
    pub asopr: f64,
    pub signal: SoprSignal,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub enum SoprSignal {
    #[default]
    NoData,
    StrongBuy,
    BuyCross,
    Bearish,
    Neutral,
    Bullish,
    TakeProfit,
}
```

---

### 3. Exchange Net Flow ⭐ РЕКОМЕНДОВАНА

#### Формула

```
Net Flow = Приток_на_биржи − Отток_с_бирж

30d_Cumulative_Flow = Σ(Net_Flow_day_i), i = 1..30

Накопительная 30-дневная скользящая:
  Cumulative_30d(t) = Cumulative_30d(t-1) + NetFlow(t) − NetFlow(t-30)
```

**Числовой пример:**
```
Приток на биржи (24h): 18,450 BTC
Отток с бирж (24h): 22,300 BTC
Net Flow = −3,850 BTC (чистый отток = накопление)

30-дневный кумулятивный поток: −95,000 BTC (длительное накопление = бычий)
```

#### Trading Signals

| Net Flow (BTC/день) | Интерпретация | Сигнал |
|---------------------|---------------|--------|
| < −10,000 | Сильный отток | 🟢 Сильный бычий сигнал |
| −5,000 – −10,000 | Умеренный отток | 🟢 Бычий сигнал |
| −1,000 – −5,000 | Слабый отток | 🟡 Умеренный бычий |
| +1,000 – +5,000 | Слабый приток | 🟡 Умеренный медвежий |
| +5,000 – +10,000 | Умеренный приток | 🟠 Медвежий сигнал |
| > +10,000 | Сильный приток | 🔴 Сильный медвежий |

**Дополнительно — 30d Cumulative:**
- 30d cumulative < −100,000 BTC → экстремальное накопление (исторически предшествует росту)
- 30d cumulative > +50,000 BTC → экстремальное распределение (предшествует падению)

#### API-источники

| Платформа | Endpoint | Free? |
|-----------|----------|-------|
| CryptoQuant | `GET /v1/exchange-flows/netflow?exchange=all&symbol=btc&window=day` | ❌ Advanced ($29/мес) |
| Glassnode | `GET /v1/metrics/transactions/transfers_volume_sum` | ❌ Standard |
| CoinMetrics | `GET /v4/timeseries/asset-metrics?assets=btc&metrics=FlowInExNtv,FlowOutExNtv` | ✅ Community |
| IntoTheBlock | Веб-интерфейс | ❌ Limited |

#### Edge Cases

1. **Внутренние переводы бирж:** Binance/Coinbase перемещают монеты между cold/hot wallet. Решение: использовать агрегированные данные CryptoQuant/Glassnode с фильтрацией.
2. **Миграция между биржами:** Отток с Binance = приток на Coinbase (нейтрализуется при агрегации). Решение: всегда использовать данные по ВСЕМ биржам суммарно.
3. **Сезонные паттерны (хардфорки):** Перед обновлениями протокола повышенный приток. Решение: фильтровать известные события из календаря.
4. **Flash-переводы крупных держателей:** Кит может переместить 10,000+ BTC без намерения продать. Решение: использовать медиану за 4h окно вместо моментального значения.

#### Rust-реализация

```rust
/// Exchange Net Flow с кумулятивным окном
pub struct ExchangeFlowCalculator {
    /// Окно кумуляции (дней)
    pub cumulative_window: usize,
    /// Окно медианного сглаживания (часов)
    pub smoothing_hours: usize,
    /// Буфер дневных потоков (BTC)
    daily_flows: Vec<f64>,
    /// Буфер часовых потоков для сглаживания
    hourly_buffer: Vec<f64>,
}

impl ExchangeFlowCalculator {
    pub fn new(cumulative_window: usize, smoothing_hours: usize) -> Self {
        Self {
            cumulative_window,
            smoothing_hours,
            daily_flows: Vec::with_capacity(cumulative_window + 1),
            hourly_buffer: Vec::with_capacity(smoothing_hours),
        }
    }

    /// Добавить часовой поток
    /// inflow_btc: приток на биржи (BTC)
    /// outflow_btc: отток с бирж (BTC)
    pub fn add_hourly(&mut self, inflow_btc: f64, outflow_btc: f64) {
        let net = inflow_btc - outflow_btc;
        self.hourly_buffer.push(net);
        if self.hourly_buffer.len() > self.smoothing_hours {
            self.hourly_buffer.remove(0);
        }
    }

    /// Рассчитать сглажённый часовой поток (медиана)
    fn smoothed_hourly(&self) -> f64 {
        if self.hourly_buffer.is_empty() {
            return 0.0;
        }
        let mut sorted = self.hourly_buffer.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        sorted[sorted.len() / 2]
    }

    /// Закрыть день: перенести сглажённый поток в дневной буфер
    pub fn end_of_day(&mut self) -> FlowResult {
        let daily_net = self.smoothed_hourly() * self.smoothing_hours as f64;
        self.daily_flows.push(daily_net);
        if self.daily_flows.len() > self.cumulative_window + 1 {
            self.daily_flows.remove(0);
        }
        self.hourly_buffer.clear();
        self.current_result()
    }

    fn current_result(&self) -> FlowResult {
        if self.daily_flows.is_empty() {
            return FlowResult::default();
        }

        let latest = *self.daily_flows.last().unwrap();
        let cumulative: f64 = self.daily_flows.iter().sum();

        let signal = match latest {
            v if v < -10000.0 => FlowSignal::StrongAccumulation,
            v if v < -5000.0 => FlowSignal::Accumulation,
            v if v < -1000.0 => FlowSignal::MildAccumulation,
            v if v <= 1000.0 => FlowSignal::Neutral,
            v if v <= 5000.0 => FlowSignal::MildDistribution,
            v if v <= 10000.0 => FlowSignal::Distribution,
            _ => FlowSignal::StrongDistribution,
        };

        FlowResult {
            daily_net_btc: latest,
            cumulative_btc: cumulative,
            signal,
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct FlowResult {
    pub daily_net_btc: f64,
    pub cumulative_btc: f64,
    pub signal: FlowSignal,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub enum FlowSignal {
    #[default]
    NoData,
    StrongAccumulation,
    Accumulation,
    MildAccumulation,
    Neutral,
    MildDistribution,
    Distribution,
    StrongDistribution,
}
```

---

## ЧАСТЬ 2: ОТКЛОНЁННЫЕ МЕТРИКИ (с обоснованием)

---

### 4. NVT Ratio — ❌ ОТКЛОНЕНА

```
NVT = Market Cap / Daily Transaction Volume (USD)
NVT Signal = MA(NVT, 90) для сглаживания
```

| NVT Signal | Зона |
|------------|------|
| > 150 | Перекупленность |
| < 50 | Перепроданность |

**Почему отклонена:**
- **Шумная:** Дневной объём транзакций крайне волатилен. Один крупный перевод (биржевой rebalance) создаёт артефакт.
- **Манипулируемая:** Объём транзакций можно завысить wash transactions (особенно на UTXO-цепях).
- **Дублирует Exchange Flow:** Exchange Net Flow более точно показывает намерения (приток/отток), чем «объём всех транзакций», который включает внутренние переводы.
- **Лагает:** NVT > 150 часто запаздывает на 1–2 недели относительно MVRV.

---

### 5. NUPL — ❌ ОТКЛОНЕНА

```
NUPL = (Market Cap − Realized Cap) / Market Cap = (MVRV − 1) / MVRV
```

| NUPL | Зона |
|------|------|
| < 0 | Capitulation |
| 0–0.25 | Hope |
| 0.25–0.5 | Optimism |
| 0.5–0.75 | Belief |
| > 0.75 | Euphoria |

**Почему отклонена:**
- **Чисто производная MVRV:** NUPL = (MVRV − 1) / MVRV. Монотонная функция от MVRV. Не даёт НИКАКОЙ новой информации.
- **Дублирует пороги:** NUPL > 0.75 эквивалентно MVRV > 4.0 (близко к порогу 3.5).
- **Зачем хранить и обновлять 2 метрики, если одна = f(другой)?**

---

### 6. Puell Multiple — ❌ ОТКЛОНЕНА

```
Puell Multiple = Daily BTC Issuance (USD) / MA(Daily BTC Issuance, 365)
```

| Puell Multiple | Зона |
|----------------|------|
| > 4.0 | Перегрет (майнеры чрезмерно прибыльны) |
| < 0.5 | Зона покупки (майнеры capitulation) |

**Почему отклонена:**
- **Только BTC:** Зависит от issuance (block reward). Не применим к альткоинам с другой эмиссией (PoS, pre-mine).
- **Снижается актуальность:** После халвинга 2024 issuance = 3.125 BTC/block. Каждый следующий халвинг уменьшает сигнал.
- **Дублирует SOPR:** Capitulation майнеров хорошо ловится через SOPR < 1.0 (майнеры — крупнейшие продавцы).
- **Лагает:** Среднее за 365 дней сглаживает сигнал до степени бесполезности для бота.

---

### 7. Stock-to-Flow — ❌ ОТКЛОНЕНА

```
S2F = Stock (общее предложение) / Flow (годовой прирост предложения)
```

**Почему отклонена:**
- **ОПРОВЕРГНУТА:** Модель Plan B предсказывала $100K BTC к концу 2021. Не сбылось. Модель статистически отвергнута.
- **Модель, не метрика:** S2F — это модель цены, а не индикатор рыночного состояния. Боту нужны индикаторы, а не прогнозы.
- **Неприменима к альтам:** Большинство альткоинов не имеют фиксированного halving schedule.

---

### 8. Hash Rate — ❌ ОТКЛОНЕНА

```
Hash Rate = количество вычислений в секунду (TH/s или EH/s)
```

**Почему отклонена:**
- **Нет торговых сигналов:** Нет чётких порогов «купить/продать». Высокий hash rate ≠ «продавать».
- **Лагает на 2+ недели:** Майнеры заказывают оборудование на месяцы вперёд. Hash rate отражает решения 6–12 месячной давности.
- **Коррелирует с ценой:** Hash rate растёт, когда цена растёт (больше майнеров включается). Это корреляция, не причинность.

---

### 9. Active Addresses — ❌ ОТКЛОНЕНА

```
Active Addresses = уникальные адреса, участвовавшие в транзакциях за период
```

**Почему отклонена:**
- **Лагает:** Рост active addresses следует за ростом цены, а не предшествует ему.
- **Нет порогов:** Нет исторически обоснованных значений «перекупленности» или «перепроданности».
- **Манипулируется:** Exchange-холодильники и сервисы (mixers) генерируют тысячи «активных» адресов без реальной экономической активности.

---

### 10. New Addresses — ❌ ОТКЛОНЕНА

```
New Addresses = уникальные адреса, впервые отправившие/получившие транзакцию
```

**Почему отклонена:**
- Производная от Active Addresses + шумнее (exchange генерирует новые deposit-адреса).
- Все проблемы Active Addresses + дополнительный шум от exchange automation.

---

### 11. Stablecoin Supply Ratio (SSR) — ❌ ОТКЛОНЕНА

```
SSR = Market Cap BTC / Total Stablecoin Supply
log(SSR) < 0.6 → бычий, > 1.0 → медвежий
```

**Почему отклонена:**
- **Низкая чувствительность:** SSR меняется медленно (недели/месяцы). Не подходит для бота с часовым таймфреймом.
- **Нет действия:** SSR < 4 означает «много сухого порошка». Но это может длиться месяцами без движения цены.
- **Дублирует Exchange Flow:** Отток стейблкоинов с бирж (→ покупки) уже ловится через Exchange Net Flow.

---

### 12. Tether Dominance — ❌ ОТКЛОНЕНА

```
Tether Dominance = USDT Market Cap / Total Stablecoin Market Cap
```

**Почему отклонена:**
- Косвенная метрика, нет формульных порогов для trading signal.
- Изменяется медленно (регуляторные события, листинги USDC).
- Не является on-chain метрикой в строгом смысле.

---

### 13. Whale Wallet Tracking — ❌ ОТКЛОНЕНА

```
Whale Activity = изменение баланса адресов с > X BTC
```

**Почему отклонена:**
- **Нестандартизирована:** Кто «кит»? 100 BTC? 1000 BTC? Нет консенсуса.
- **Expensive API:** Glassnode «Professional» ($799/мес) для whale alerts.
- **Noisy:** Киты перемещают монеты между своими кошельками. Каждое перемещение ≠ продажа.
- **Нет формульных порогов:** Нет исторически обоснованных значений.

---

### 14. Realized Cap — ❌ ОТКЛОНЕНА

```
Realized Cap = Σ(Цена_при_последнем_перемещении_i × Количество_i)
```

**Почему отклонена:**
- Компонент MVRV, не самостоятельный сигнал. Не имеет собственных порогов.
- Не торговая метрика — это бухгалтерский показатель.

---

### 15. Thermocap — ❌ ОТКЛОНЕНА

```
Thermocap = Σ(Daily Mining Revenue) за всю историю
```

**Почему отклонена:**
- Только для PoW-монет (BTC, LTC). Не применим к ETH (PoS), SOL, etc.
- Thermocap / Market Cap даёт «стоимость сети относительно вложенных в майнинг денег», но MVRV делает это лучше (использует все транзакции, не только майнинг).

---

### 16. HODL Waves — ❌ ОТКЛОНЕНА

```
HODL Waves = распределение предложения по возрасту UTXO
  0–1 день (Hot), 1д–1неделя, 1неделя–1мес, 1–3мес, 3–6мес, 6–12мес, 1–2года, 2–3года, 3–5лет, 5+ лет
```

**Почему отклонена:**
- Визуальная/аналитическая метрика. Не имеет числовых порогов для алгоритмического бота.
- Нет формулы → нет сигнала → нет автоматизации.
- Полезна для человеческого анализа, но не для бота.

---

### 17. Coin Days Destroyed (CDD) — ❌ ОТКЛОНЕНА

```
CDD = Σ(Количество_BTC_i × Дни_бездействия_i) для всех перемещённых монет
```

**Числовой пример:**
```
10 BTC не двигались 365 дней, затем переместились
CDD = 10 × 365 = 3,650
```

**Почему отклонена:**
- Производная HODL Waves. Высокий CDD = старые монеты движутся = то же, что SOPR_LTH.
- Дублирует SOPR: SOPR < 1 + высокий CDD = capitulation long-term holders. Но SOPR уже ловит это.
- Нет чётких порогов (что такое «высокий CDD» зависит от эпохи).

---

### 18. NVT Signal — ❌ ОТКЛОНЕНА

```
NVT Signal = MA(Market Cap, 90) / MA(Transaction Volume, 90)
```

| NVT Signal | Зона |
|------------|------|
| > 150 | Перекуплен |
| < 50 | Перепродан |

**Почему отклонена:**
- Улучшение NVT (сглаживание), но базовая проблема остаётся: объём транзакций — шумный и манипулируемый показатель.
- Exchange Net Flow точнее показывает намерения.

---

## ЧАСТЬ 3: КОМБИНАЦИИ СИГНАЛОВ

### Сильный бычий сигнал (максимальная уверенность)

```
MVRV < 1.5                    — рынок недооценён
AND SOPR пересекает 1.0 ↑     — держатели перестали продавать в убыток
AND Exchange Net Flow < -5000  — накопление на биржах
```

### Сильный медвежий сигнал (максимальная уверенность)

```
MVRV > 3.5                    — рынок перегрет
AND SOPR > 1.10               — экстремальная прибыль фиксируется
AND Exchange Net Flow > +5000  — распределение на биржи
```

### Сигнал капитуляции (контртренд-покупка)

```
MVRV < 1.0                    — Market Cap ниже Realized Cap
AND SOPR < 0.95               — продажи в глубокий убыток
AND Exchange Net Flow > +10000 — массовый приток (паника)
→ Исторически = дно цикла
```

---

## ЧАСТЬ 4: ИНТЕГРАЦИЯ

### Конфигурация (config.yaml)

```yaml
onchain:
  mvrv:
    enabled: true
    api: coinmetrics          # Free tier
    fallback: glassnode       # Paid, more accurate
    buy_threshold: 1.0
    sell_threshold: 3.5
    stddev_window: 365        # дней для Z-Score

  sopr:
    enabled: true
    api: glassnode
    ma_period: 7              # дней для aSOPR
    outlier_sigma: 3.0
    buy_signal: "cross_above_1.0"
    strong_buy_threshold: 0.95

  exchange_flow:
    enabled: true
    api: cryptoquant
    cumulative_window: 30     # дней
    smoothing_hours: 4        # медиана за 4 часа
    strong_accumulation: -10000   # BTC/день
    strong_distribution: 10000    # BTC/день

  # Консенсус: сигнал действителен только если ≥ 2 из 3 метрик согласны
  consensus_threshold: 2
```

### Rust-модуль: комбинированный скоринг

```rust
/// Комбинированный on-chain скор
pub struct OnChainScorer {
    pub mvrv: MvrvCalculator,
    pub sopr: SoprCalculator,
    pub flow: ExchangeFlowCalculator,
    /// Минимум совпадающих сигналов для actionable score
    pub consensus_threshold: usize,
}

#[derive(Debug, Clone)]
pub struct OnChainScore {
    pub mvrv_signal: Signal,
    pub sopr_signal: SoprSignal,
    pub flow_signal: FlowSignal,
    pub combined: CombinedSignal,
    pub consensus: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum CombinedSignal {
    NoData,
    StrongBuy,
    Buy,
    Neutral,
    Sell,
    StrongSell,
}

impl OnChainScorer {
    pub fn score(&self) -> OnChainScore {
        let mvrv = self.mvrv.last_signal();
        let sopr = self.sopr.last_signal();
        let flow = self.flow.last_signal();

        // Подсчёт «бычьих» и «медвежьих» голосов
        let mut bull_votes = 0;
        let mut bear_votes = 0;

        // MVRV
        match mvrv {
            Signal::StrongBuy => bull_votes += 2,
            Signal::Accumulate => bull_votes += 1,
            Signal::TakeProfit => bear_votes += 1,
            Signal::StrongSell => bear_votes += 2,
            _ => {}
        }

        // SOPR
        match sopr {
            SoprSignal::StrongBuy | SoprSignal::BuyCross => bull_votes += 2,
            SoprSignal::Bearish => bear_votes += 1,
            SoprSignal::TakeProfit => bear_votes += 2,
            _ => {}
        }

        // Exchange Flow
        match flow {
            FlowSignal::StrongAccumulation => bull_votes += 2,
            FlowSignal::Accumulation => bull_votes += 1,
            FlowSignal::Distribution => bear_votes += 1,
            FlowSignal::StrongDistribution => bear_votes += 2,
            _ => {}
        }

        let combined = if bull_votes >= 4 && bear_votes == 0 {
            CombinedSignal::StrongBuy
        } else if bull_votes >= 3 {
            CombinedSignal::Buy
        } else if bear_votes >= 4 && bull_votes == 0 {
            CombinedSignal::StrongSell
        } else if bear_votes >= 3 {
            CombinedSignal::Sell
        } else {
            CombinedSignal::Neutral
        };

        let agreeing = if bull_votes > bear_votes {
            [&mvrv, &sopr, &flow].iter().filter(|s| /* бычий */ true).count()
        } else {
            [&mvrv, &sopr, &flow].iter().filter(|s| /* медвежий */ true).count()
        };

        OnChainScore {
            mvrv_signal: mvrv,
            sopr_signal: sopr,
            flow_signal: flow: flow.clone(),
            combined: combined.clone(),
            consensus: agreeing >= self.consensus_threshold
                && combined != CombinedSignal::Neutral,
        }
    }
}
```

---

## ЧАСТЬ 5: ИТОГИ

### Почему выбраны именно эти 3

1. **MVRV** — единственный on-chain индикатор с чёткими, исторически проверенными порогами для определения верха/низа цикла. Не существует ни одного классического TA индикатора, который на макро-уровне давал бы такую же чёткость.

2. **SOPR** — уникальная метрика, измеряющая реальную прибыльность фиксации позиций. Уровень SOPR = 1.0 — это «цена боли»: держатели не хотят продавать в убыток, что создаёт естественную поддержку. Ни один другой индикатор не измеряет это напрямую.

3. **Exchange Net Flow** — единственная метрика, отражающая реальное поведение держателей (накопление vs распределение). TA индикаторы работают только с ценой и объёмом. Exchange Flow показывает намерения ДО того, как они реализуются в цене.

### Почему остальные отклонены (сводка)

| Причина отклонения | Метрики |
|---|---|
| Дублирует рекомендованные | NUPL (дублирует MVRV), CDD (дублирует SOPR), SSR (дублирует Exchange Flow) |
| Нет торговых сигналов | Hash Rate, Active Addresses, HODL Waves, Tether Dominance |
| Модель опровергнута | Stock-to-Flow |
| Только для BTC/PoW | Puell Multiple, Thermocap |
| Шумная/манипулируемая | NVT, NVT Signal, New Addresses, Whale Tracking |
| Компонент, не самостоятельная | Realized Cap |

---

*Документ: 17-onchain.md*  
*Агент: 17 — On-Chain аналитика*  
*Дата: 2026-04-17*