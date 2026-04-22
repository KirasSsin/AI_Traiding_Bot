# Модуль 15: Арбитражные стратегии (Arbitrage Strategies)

> Аудит всех арбитражных стратегий для крипто-торгового бота.
> Формула (с комиссиями, slippage, latency) → Обоснование → Edge cases → Rust-код → Пороговые значения.

---

## Обзор: классификация арбитражных стратегий

| # | Стратегия | Статус | Сложность | Латентность | Капитал | Рейтинг |
|---|---|---|---|---|---|---|
| 1 | Triangular Arbitrage | ✅ Выбрана | Средняя | < 100ms | Средний | ⭐⭐⭐⭐⭐ |
| 2 | Statistical Arbitrage (Pairs) | ✅ Выбрана | Высокая | Минуты–часы | Высокий | ⭐⭐⭐⭐ |
| 3 | Basis Arbitrage (Cash-and-Carry) | ✅ Выбрана | Средняя | Минуты | Высокий | ⭐⭐⭐⭐ |
| 4 | Funding Rate Harvesting | ❌ Отклонена | Низкая | Дни | Высокий | ⭐⭐⭐ |
| 5 | Cross-Exchange Arbitrage | ❌ Отклонена | Высокая | < 50ms | Средний | ⭐⭐ |
| 6 | Latency Arbitrage | ❌ Отклонена | Экстремальная | < 1ms | Любой | ⭐ |
| 7 | DEX-CEX Arbitrage | ❌ Отклонена | Высокая | Секунды | Средний | ⭐⭐ |
| 8 | Options Put-Call Parity | ❌ Отклонена | Высокая | Минуты | Высокий | ⭐⭐ |
| 9 | Cross-Exchange Triangular | ❌ Отклонена | Высокая | < 50ms | Средний | ⭐⭐ |

---

## 1. ✅ Triangular Arbitrage (Треугольный арбитраж)

### Суть

Три валюты на одной бирже формируют треугольник. Если произведение кросс-курсов ≠ 1, есть безрисковый профит.

### Формула

Замкнутый цикл: `A → B → C → A`

```
Profit = A_start × rate(A→B) × rate(B→C) × rate(C→A) − A_start
```

**С учётом комиссий и slippage:**

```
A_after_leg1 = A_start × rate(A→B) × (1 − fee) × (1 − slippage_AB)
A_after_leg2 = A_after_leg1 × rate(B→C) × (1 − fee) × (1 − slippage_BC)
A_final      = A_after_leg2 × rate(C→A) × (1 − fee) × (1 − slippage_CA)

Net_Profit = A_final − A_start
Net_Profit_% = (A_final / A_start − 1) × 100
```

**С учётом latency (линейная модель проскальзывания):**

```
Slippage = k × latency_sec × volatility_per_sec
```

где `k = 0.5–2.0` — эмпирический коэффициент, зависящий от глубины стакана.

**Условие входа:**

```
Net_Profit_% > MIN_PROFIT_THRESHOLD + SAFETY_MARGIN
```

### Обоснование

- Все 3 ноги исполняются на **одной** бирже → нет межбиржевого риска перевода.
- Крипта имеет > 500 торговых пар на крупных биржах (Binance, OKX) → тысячи треугольников.
- Latency < 100ms на co-located серверах → арбитраж реально исполним.

### Edge cases

1. **Slippage на illiquid парах**: если одна из ног — тонкий рынок, slippage может уничтожить профит. Решение: фильтр по `order_book_depth > MIN_DEPTH_USD`.
2. **Race condition**: несколько ботов одновременно видят одну возможность → кто первый, тот и съел. Решение: atomic execution через batch order или OCO.
3. **Partial fill**: одна нога исполнилась частично → открытый риск. Решение: использовать `FOK` (Fill-or-Kill) ордера.
4. **API rate limit**: слишком частые запросы → бан. Решение: WebSocket для стаканов, REST только для исполнения.
5. **Flash crash**: цена резко сдвинулась между получением котировки и исполнением. Решение: max latency timeout = 50ms.

### Пороговые значения

| Параметр | Значение | Комментарий |
|---|---|---|
| `MIN_PROFIT_%` | 0.05% | Минимальная нетто-прибыль после всех издержек |
| `MAX_LATENCY_MS` | 100 | Максимальная задержка от получения котировки до исполнения |
| `MIN_DEPTH_USD` | $50,000 | Минимальная глубина стакана на каждую ногу |
| `MAX_SLIPPAGE_PER_LEG` | 0.02% | Макс. проскальзывание на ногу |
| `FEE_MAKER` | 0.10% | Binance VIP0 maker fee |
| `FEE_TAKER` | 0.10% | Binance VIP0 taker fee |
| `FEE_TOTAL_3_LEGS` | 0.30% | 3 × taker (worst case) |

### Rust-реализация

```rust
use std::collections::HashMap;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;

/// Конфигурация треугольного арбитража
#[derive(Debug, Clone)]
pub struct TriangularArbConfig {
    /// Минимальная нетто-прибыль в процентах (0.05 = 0.05%)
    pub min_profit_pct: Decimal,
    /// Максимальная латентность в миллисекундах
    pub max_latency_ms: u64,
    /// Минимальная глубина стакана в USD на ногу
    pub min_depth_usd: Decimal,
    /// Макс. проскальзывание на ногу в долях (0.0002 = 0.02%)
    pub max_slippage_per_leg: Decimal,
    /// Комиссия taker за сделку (0.001 = 0.1%)
    pub fee_taker: Decimal,
}

impl Default for TriangularArbConfig {
    fn default() -> Self {
        Self {
            min_profit_pct: dec!(0.05),
            max_latency_ms: 100,
            min_depth_usd: dec!(50000),
            max_slippage_per_leg: dec!(0.0002),
            fee_taker: dec!(0.001),
        }
    }
}

/// Одна нога треугольного арбитража
#[derive(Debug, Clone)]
pub struct ArbLeg {
    pub pair: String,          // e.g. "ETH/BTC"
    pub side: OrderSide,       // Buy или Sell
    pub price: Decimal,        // Цена исполнения
    pub depth_usd: Decimal,    // Глубина стакана в USD
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OrderSide {
    Buy,
    Sell,
}

/// Результат расчёта треугольного арбитража
#[derive(Debug, Clone)]
pub struct TriangularArbResult {
    pub cycle: Vec<String>,           // e.g. ["USDT", "ETH", "BTC", "USDT"]
    pub legs: Vec<ArbLeg>,
    pub gross_profit_pct: Decimal,
    pub total_fees_pct: Decimal,
    pub estimated_slippage_pct: Decimal,
    pub net_profit_pct: Decimal,
    pub is_profitable: bool,
    pub required_capital_usd: Decimal,
}

/// Рассчитать треугольный арбитраж для замкнутого цикла A→B→C→A
///
/// Аргументы:
///   - start_amount: начальная сумма в валюте A
///   - leg_ab: (цена покупки B за A, глубина в USD, slippage)
///   - leg_bc: (цена покупки C за B, глубина в USD, slippage)
///   - leg_ca: (цена продажи C за A, глубина в USD, slippage)
///   - config: конфигурация стратегии
///
/// Возвращает: TriangularArbResult с расчётом прибыльности
pub fn calculate_triangular_arbitrage(
    start_amount: Decimal,
    leg_ab: (Decimal, Decimal, Decimal),  // (price, depth_usd, slippage)
    leg_bc: (Decimal, Decimal, Decimal),
    leg_ca: (Decimal, Decimal, Decimal),
    config: &TriangularArbConfig,
) -> TriangularArbResult {
    let fee = config.fee_taker;

    // Leg 1: A → B (покупаем B за A)
    let after_leg1 = start_amount * leg_ab.0 * (Decimal::ONE - fee) * (Decimal::ONE - leg_ab.2);

    // Leg 2: B → C (покупаем C за B)
    let after_leg2 = after_leg1 * leg_bc.0 * (Decimal::ONE - fee) * (Decimal::ONE - leg_bc.2);

    // Leg 3: C → A (продаём C за A)
    let final_amount = after_leg2 * leg_ca.0 * (Decimal::ONE - fee) * (Decimal::ONE - leg_ca.2);

    let gross_profit = (final_amount / start_amount - Decimal::ONE) * dec!(100);
    let total_fees = dec!(3) * fee * dec!(100);
    let total_slippage = (leg_ab.2 + leg_bc.2 + leg_ca.2) * dec!(100);
    let net_profit = gross_profit - total_fees - total_slippage;

    // Проверка глубины стакана
    let min_depth = leg_ab.1.min(leg_bc.1).min(leg_ca.1);
    let is_profitable = net_profit > config.min_profit_pct
        && min_depth >= config.min_depth_usd;

    TriangularArbResult {
        cycle: vec!["A".into(), "B".into(), "C".into(), "A".into()],
        legs: vec![],
        gross_profit_pct: gross_profit,
        total_fees_pct: total_fees,
        estimated_slippage_pct: total_slippage,
        net_profit_pct: net_profit,
        is_profitable,
        required_capital_usd: start_amount,
    }
}

/// Перебор всех треугольников из списка пар
/// Возвращает отсортированный по прибыльности список
pub fn find_all_triangles(
    pairs: &HashMap<String, (String, String)>, // pair → (base, quote)
    prices: &HashMap<String, Decimal>,          // pair → mid_price
    config: &TriangularArbConfig,
) -> Vec<TriangularArbResult> {
    let mut results = Vec::new();

    // Строим граф: валюта → [(валюта, пара)]
    let mut graph: HashMap<&str, Vec<(&str, &str)>> = HashMap::new();
    for (pair, (base, quote)) in pairs {
        graph.entry(base.as_str()).or_default().push((quote.as_str(), pair.as_str()));
        graph.entry(quote.as_str()).or_default().push((base.as_str(), pair.as_str()));
    }

    // BFS для поиска треугольников
    for &start in graph.keys() {
        for &(mid, pair1) in graph.get(start).unwrap_or(&vec![]) {
            for &(end, pair2) in graph.get(mid).unwrap_or(&vec![]) {
                if end == start {
                    continue;
                }
                // Проверяем, есть ли пара end → start
                if let Some(pair3_list) = graph.get(end) {
                    for &(_, pair3) in pair3_list {
                        if pair3_list.iter().any(|(n, _)| *n == start) {
                            // Найден треугольник start → mid → end → start
                            if let (Some(&p1), Some(&p2), Some(&p3)) = (
                                prices.get(pair1),
                                prices.get(pair2),
                                prices.get(pair3),
                            ) {
                                let result = calculate_triangular_arbitrage(
                                    dec!(10000), // $10k тестовая сумма
                                    (p1, config.min_depth_usd, config.max_slippage_per_leg),
                                    (p2, config.min_depth_usd, config.max_slippage_per_leg),
                                    (p3, config.min_depth_usd, config.max_slippage_per_leg),
                                    config,
                                );
                                if result.is_profitable {
                                    results.push(result);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    results.sort_by(|a, b| b.net_profit_pct.cmp(&a.net_profit_pct));
    results
}
```

### Пример: USDT → ETH → BTC → USDT

```
Дано:
  ETH/USDT = 3,200 (buy ETH за USDT)
  BTC/ETH  = 0.025 (buy BTC за ETH)
  BTC/USDT = 80,000 (sell BTC за USDT)

Расчёт (start = 10,000 USDT):
  Leg 1: 10000 / 3200 = 3.125 ETH     × (1-0.001) = 3.121875 ETH
  Leg 2: 3.121875 × 0.025 = 0.078 BTC  × (1-0.001) = 0.077926 BTC
  Leg 3: 0.077926 × 80000 = 6234 USD   × (1-0.001) = 6227.84 USDT

  Profit = 6227.84 − 10000 = −3772.16 USDT (−37.7%)
  → НЕ выгодно. Курс BTC/USDT совпадает с кросс-курсом.
```

Арбитраж появляется, когда `BTC/USDT` отклоняется от `ETH/USDT × BTC/ETH`. Например:

```
BTC/USDT = 79,500 (спред −0.625%)
  Leg 3: 0.077926 × 79500 = 6195.10 USDT × 0.999 = 6188.91 USDT
  Profit = 6188.91 − 10000 = −3811.09 USDT
  → всё ещё убыток из-за комиссий
```

Нужен спред > 0.3% для покрытия 3 ног комиссий (0.3%).

---

## 2. ✅ Statistical Arbitrage — Pairs Trading (Статистический арбитраж)

### Суть

Два скоррелированных актива (например, ETH и BTC) имеют стабильное соотношение цен. Когда соотношение отклоняется от среднего — шортим переоценённый, лонгуем недооценённый.

### Формула

**Spread:**

```
Spread = Price_A − β × Price_B
```

где `β` — коэффициент хеджирования (hedge ratio), рассчитанный через OLS-регрессию:

```
β = Cov(Price_A, Price_B) / Var(Price_B)
```

**Z-score (нормализованный спред):**

```
Z = (Spread − μ_spread) / σ_spread
```

где `μ_spread` и `σ_spread` — скользящее среднее и стд. отклонение спреда за окно `N` периодов.

**Сигналы:**

```
ENTRY LONG A, SHORT B:  Z < −Z_entry  (спред ниже среднего → A недооценён)
ENTRY SHORT A, LONG B:  Z > +Z_entry  (спред выше среднего → A переоценён)
EXIT:                   |Z| < Z_exit   (спред вернуся к среднему)
STOP LOSS:              |Z| > Z_stop   (спред расходится → коинтеграция нарушена)
```

**С учётом комиссий:**

```
Net_Profit = |ΔSpread| × Position_Size − 4 × Fee × Position_Size × Price
           − 2 × Slippage × Position_Size × Price
```

(4 транзакции: open A, open B, close A, close B)

**Half-life возврата (проверка коинтеграции):**

```
Spread_t = α + γ × Spread_{t−1} + ε
Half_life = −ln(2) / ln(γ)
```

Если `Half_life > MAX_HALF_LIFE` → спред не возвращается → не торгуем.

### Обоснование

- Крипто-пары (ETH/BTC, SOL/ETH, AVAX/ETH) исторически коинтегрированы.
- Средний спред возврата: 2–5 дней на 1H таймфрейме.
- Профит 2–8% за сделку при правильных порогах.

### Edge cases

1. **Нарушение коинтеграции**: фундаментальное изменение (например, Ethereum Merge) → спред расходится навсегда. Решение: rolling window + ADF тест + stop loss на `Z_stop = 4.0`.
2. **Долгий возврат**: спред не возвращается 30+ дней → капитал заморожен. Решение: `MAX_HOLD_DAYS = 14`, затем принудительный выход.
3. **Асимметричная ликвидность**: один актив высоколиквиден, другой — нет. Решение: `MIN_LIQUIDITY_RATIO = 0.5` (менее ликвидный должен иметь ≥ 50% ликвидности более ликвидного).
4. **Каскадные ликвидации**: в крипте крупные движения ликвидируют оба актива одновременно. Решение: фильтр по `MAX_CORRELATION_DURING_CRASH`.

### Пороговые значения

| Параметр | Значение | Комментарий |
|---|---|---|
| `Z_entry` | 2.0 | Вход при отклонении на 2σ |
| `Z_exit` | 0.5 | Выход при возврате к 0.5σ |
| `Z_stop` | 4.0 | Стоп-лосс при 4σ |
| `LOOKBACK_WINDOW` | 100 (1H) | ~4 дня для расчёта μ и σ |
| `MIN_HALF_LIFE` | 5 (часов) | Минимальный half-life (слишком быстрый → шум) |
| `MAX_HALF_LIFE` | 72 (часа) | Максимальный (слишком медленный → капитал простаивает) |
| `ADF_P_VALUE` | 0.05 | Порог теста коинтеграции |
| `MAX_HOLD_DAYS` | 14 | Принудительный выход |

### Rust-реализация

```rust
use rust_decimal::Decimal;
use rust_decimal_macros::dec;

/// Параметры статистического арбитража (pairs trading)
#[derive(Debug, Clone)]
pub struct PairsArbConfig {
    pub z_entry: Decimal,           // Порог входа (2.0)
    pub z_exit: Decimal,            // Порог выхода (0.5)
    pub z_stop: Decimal,            // Стоп-лосс (4.0)
    pub lookback_window: usize,     // Окно для расчёта (100 периодов)
    pub max_half_life_hours: u64,   // Макс. half-life (72 часа)
    pub max_hold_days: u64,         // Макс. время в сделке (14 дней)
    pub fee_taker: Decimal,         // Комиссия taker (0.1%)
}

impl Default for PairsArbConfig {
    fn default() -> Self {
        Self {
            z_entry: dec!(2.0),
            z_exit: dec!(0.5),
            z_stop: dec!(4.0),
            lookback_window: 100,
            max_half_life_hours: 72,
            max_hold_days: 14,
            fee_taker: dec!(0.001),
        }
    }
}

/// Состояние спреда
#[derive(Debug, Clone)]
pub struct SpreadState {
    pub spread: Decimal,
    pub z_score: Decimal,
    pub half_life: Decimal,
    pub mean: Decimal,
    pub std: Decimal,
}

/// Сигнал парного арбитража
#[derive(Debug, Clone, PartialEq)]
pub enum PairsSignal {
    EnterLongA,   // Z < -Z_entry: лонг A, шорт B
    EnterShortA,  // Z > +Z_entry: шорт A, лонг B
    Exit,         // |Z| < Z_exit
    StopLoss,     // |Z| > Z_stop
    Hold,         // Нет действия
}

/// Рассчитать спред и z-score
///
/// Аргументы:
///   - prices_a: массив цен актива A
///   - prices_b: массив цен актива B
///   - beta: коэффициент хеджирования (из OLS)
///   - window: окно для расчёта среднего и стд. отклонения
pub fn calculate_spread_state(
    prices_a: &[Decimal],
    prices_b: &[Decimal],
    beta: Decimal,
    window: usize,
) -> SpreadState {
    assert!(prices_a.len() >= window && prices_b.len() >= window);

    let n = window;
    let start = prices_a.len() - n;

    // Расчёт спредов
    let spreads: Vec<Decimal> = (start..prices_a.len())
        .map(|i| prices_a[i] - beta * prices_b[i])
        .collect();

    // Среднее
    let mean = spreads.iter().sum::<Decimal>() / Decimal::from(n);

    // Стандартное отклонение
    let variance = spreads.iter()
        .map(|s| (*s - mean) * (*s - mean))
        .sum::<Decimal>() / Decimal::from(n - 1);
    let std = variance.sqrt().unwrap_or(dec!(1));

    // Текущий спред
    let current_spread = *spreads.last().unwrap();

    // Z-score
    let z_score = if std > dec!(0) {
        (current_spread - mean) / std
    } else {
        dec!(0)
    };

    // Half-life: γ = corr(spread_t, spread_{t-1})
    // Упрощённый расчёт
    let mut sum_xy = dec!(0);
    let mut sum_xx = dec!(0);
    for i in 1..spreads.len() {
        let diff = spreads[i] - spreads[i - 1];
        sum_xy += diff * spreads[i - 1];
        sum_xx += spreads[i - 1] * spreads[i - 1];
    }
    let gamma = if sum_xx > dec!(0) { dec!(1) + sum_xy / sum_xx } else { dec!(0) };
    let half_life = if gamma > dec!(0) && gamma < dec!(1) {
        (-Decimal::from(2).ln().unwrap() / gamma.ln().unwrap()).abs()
    } else {
        Decimal::MAX
    };

    SpreadState {
        spread: current_spread,
        z_score,
        half_life,
        mean,
        std,
    }
}

/// Определить сигнал на основе состояния спреда
pub fn get_pairs_signal(
    state: &SpreadState,
    config: &PairsArbConfig,
    is_in_position: bool,
) -> PairsSignal {
    let z_abs = state.z_score.abs();

    if is_in_position {
        if z_abs < config.z_exit {
            PairsSignal::Exit
        } else if z_abs > config.z_stop {
            PairsSignal::StopLoss
        } else {
            PairsSignal::Hold
        }
    } else {
        // Проверка коинтеграции
        if state.half_life > Decimal::from(config.max_half_life_hours) {
            return PairsSignal::Hold; // Нет коинтеграции
        }

        if state.z_score < -config.z_entry {
            PairsSignal::EnterLongA
        } else if state.z_score > config.z_entry {
            PairsSignal::EnterShortA
        } else {
            PairsSignal::Hold
        }
    }
}

/// Рассчитать нетто-прибыль парной сделки с учётом комиссий
pub fn calculate_pairs_net_profit(
    entry_spread: Decimal,
    exit_spread: Decimal,
    position_size: Decimal,
    price_a: Decimal,
    price_b: Decimal,
    fee: Decimal,
) -> Decimal {
    // Прибыль от движения спреда
    let gross_pnl = (exit_spread - entry_spread).abs() * position_size;

    // Комиссии: 4 транзакции (open A, open B, close A, close B)
    let total_fees = dec!(4) * fee * position_size * (price_a + price_b) / dec!(2);

    // Slippage: ~2 транзакции (open + close)
    let slippage = dec!(2) * dec!(0.0002) * position_size * (price_a + price_b) / dec!(2);

    gross_pnl - total_fees - slippage
}
```

---

## 3. ✅ Basis Arbitrage — Cash-and-Carry (Базисный арбитраж)

### Суть

Разница между ценой perpetual futures и spot — это «базис». Если базис положительный и достаточный — покупаем spot, продаём perp (short), ждём сходимости.

### Формула

**Годовой базис (annualized basis):**

```
Basis = (Perp_Price − Spot_Price) / Spot_Price × (365 / Funding_Interval_Days) × 100
```

Для 8-часового funding (3 раза в день):

```
Basis_annualized = (Perp − Spot) / Spot × 365/3 × 100
                 = (Perp − Spot) / Spot × 121.67 × 100
```

**Вход (Cash-and-Carry):**

```
IF Basis_annualized > MIN_BASIS_THRESHOLD (15%):
    BUY spot
    SELL perp (short)
```

**Нетто-доход за период funding:**

```
Funding_Income = Position_Size × Perp_Price × Funding_Rate
Net_per_period = Funding_Income − Spot_Carry_Cost − Fees
```

**С учётом комиссий (полный цикл вход + удержание + выход):**

```
Entry_Cost  = Spot_Price × (fee_spot_buy + slippage) + Perp_Price × (fee_perp_open + slippage)
Exit_Cost   = Spot_Price × (fee_spot_sell + slippage) + Perp_Price × (fee_perp_close + slippage)
Total_Fees  = Entry_Cost + Exit_Cost

Net_Annual_Profit = Basis_annualized − Total_Fees_as_%
```

**Funding Rate Harvesting (подмножество):**

```
IF Funding_Rate > 0.05% за 8ч (≈ 54.75% годовых):
    LONG spot + SHORT perp → получаем funding каждые 8ч
    IF Funding_Rate < -0.05%:
    SHORT spot + LONG perp → получаем funding (отрицательный = выплачивают лонгам)
```

### Обоснование

- На крипто-рынке perp часто торгуется с премией к spot (contango) — 15–50% годовых.
- Минимальный рыночный риск: хеджированная позиция (long spot = short perp = нулевая дельта).
- Funding выплачивается каждые 8 часов → доходность предсказуема.

### Edge cases

1. **Basis collapse**: при flash crash perp и spot сходятся мгновенно → невозможно закрыть с профитом. Решение: `Basis` при входе должен быть > 15% с запасом.
2. **Funding rate flip**: если funding станет отрицательным, позиция начнёт терять деньги. Решение: мониторинг + закрытие при `funding < break_even`.
3. **Margin call на perp**: если spot вырос, short perp в минусе. Решение: `margin_ratio > 50%` всегда.
4. **Exchange insolvency**: биржа закрывается с замороженными средствами. Решение: диверсификация по биржам, `MAX_EXPOSURE_PER_EXCHANGE = 30%`.
5. **Opportunity cost**: капитал заморожен на дни/недели. Решение: `MAX_HOLD_DAYS = 30`, затем принудительная рокировка.

### Пороговые значения

| Параметр | Значение | Комментарий |
|---|---|---|
| `MIN_BASIS_ANNUALIZED` | 15% | Мин. годовой базис для входа |
| `MIN_FUNDING_RATE` | 0.05% | Мин. funding за 8ч для harvesting |
| `BREAK_EVEN_FUNDING` | −0.01% | Закрытие, если funding ушёл в минус |
| `MAX_HOLD_DAYS` | 30 | Макс. время удержания позиции |
| `MIN_MARGIN_RATIO` | 50% | Мин. обеспечение на perp |
| `MAX_EXPOSURE_PER_EXCHANGE` | 30% | Макс. экспозиция на одну биржу |
| `FUNDING_INTERVAL_HOURS` | 8 | Стандартный интервал funding |

### Rust-реализация

```rust
use rust_decimal::Decimal;
use rust_decimal_macros::dec;

/// Конфигурация базисного арбитража
#[derive(Debug, Clone)]
pub struct BasisArbConfig {
    pub min_basis_annualized: Decimal,    // 15%
    pub min_funding_rate: Decimal,        // 0.05%
    pub break_even_funding: Decimal,      // -0.01%
    pub max_hold_days: u64,              // 30
    pub min_margin_ratio: Decimal,       // 50%
    pub fee_taker: Decimal,              // 0.1%
    pub funding_interval_hours: u64,     // 8
}

impl Default for BasisArbConfig {
    fn default() -> Self {
        Self {
            min_basis_annualized: dec!(15),
            min_funding_rate: dec!(0.05),
            break_even_funding: dec!(-0.01),
            max_hold_days: 30,
            min_margin_ratio: dec!(50),
            fee_taker: dec!(0.001),
            funding_interval_hours: 8,
        }
    }
}

/// Состояние базиса
#[derive(Debug, Clone)]
pub struct BasisState {
    pub spot_price: Decimal,
    pub perp_price: Decimal,
    pub funding_rate: Decimal,          // текущий funding rate (%)
    pub basis_absolute: Decimal,        // Perp − Spot
    pub basis_pct: Decimal,             // (Perp − Spot) / Spot × 100
    pub basis_annualized: Decimal,      // годовой базис
    pub is_profitable: bool,
}

/// Рассчитать состояние базиса
pub fn calculate_basis_state(
    spot_price: Decimal,
    perp_price: Decimal,
    funding_rate: Decimal,
    config: &BasisArbConfig,
) -> BasisState {
    let basis_abs = perp_price - spot_price;
    let basis_pct = if spot_price > dec!(0) {
        basis_abs / spot_price * dec!(100)
    } else {
        dec!(0)
    };

    // Годовой базис: 365 дней / funding_interval_hours / 24 = кол-во funding в году
    let fundings_per_year = Decimal::from(365 * 24) / Decimal::from(config.funding_interval_hours);
    let basis_annualized = basis_pct * fundings_per_year / dec!(100) * dec!(100);
    // = (Perp−Spot)/Spot × fundings_per_year × 100

    let is_profitable = basis_annualized >= config.min_basis_annualized
        && funding_rate >= config.min_funding_rate;

    BasisState {
        spot_price,
        perp_price,
        funding_rate,
        basis_absolute: basis_abs,
        basis_pct,
        basis_annualized,
        is_profitable,
    }
}

/// Рассчитать нетто-доход за один funding-период
pub fn funding_income_per_period(
    position_size_usd: Decimal,
    funding_rate: Decimal,
) -> Decimal {
    position_size_usd * funding_rate / dec!(100)
}

/// Рассчитать совокупный доход за N funding-периодов с учётом комиссий
pub fn calculate_basis_total_return(
    position_size_usd: Decimal,
    funding_rate: Decimal,
    num_periods: u64,
    spot_price: Decimal,
    perp_price: Decimal,
    config: &BasisArbConfig,
) -> Decimal {
    // Доход от funding
    let total_funding = funding_income_per_period(position_size_usd, funding_rate)
        * Decimal::from(num_periods);

    // Комиссии: вход (spot buy + perp sell) + выход (spot sell + perp buy)
    let entry_fees = position_size_usd * config.fee_taker * dec!(2); // spot + perp
    let exit_fees = position_size_usd * config.fee_taker * dec!(2);
    let total_fees = entry_fees + exit_fees;

    // Slippage (оценка)
    let total_slippage = position_size_usd * dec!(0.0002) * dec!(4);

    total_funding - total_fees - total_slippage
}

/// Определить: стоит ли входить в basis arb?
pub fn should_enter_basis_arb(
    state: &BasisState,
    config: &BasisArbConfig,
) -> bool {
    // Проверка порога базиса
    if state.basis_annualized < config.min_basis_annualized {
        return false;
    }

    // Проверка funding rate
    if state.funding_rate < config.min_funding_rate {
        return false;
    }

    // Проверка что perp > spot (contango)
    if state.basis_absolute <= dec!(0) {
        return false;
    }

    true
}
```

### Пример: BTC basis arb

```
Дано:
  BTC Spot  = $80,000
  BTC Perp  = $80,800 (премия +1%)
  Funding   = 0.03% за 8ч

Basis_annualized = (80800−80000)/80000 × (365/3) × 100
                 = 0.01 × 121.67 × 100 = 121.67%

  → 121.67% > 15% → ВХОДИМ

Доход за 30 дней:
  Funding per 8h = $100,000 × 0.03% = $30
  Funding per day = $90
  Funding per 30 days = $2,700
  
  Комиссии (вход + выход): $100,000 × 0.001 × 4 = $400
  
  Нетто: $2,700 − $400 = $2,300 за 30 дней = 2.3% за месяц
```

---

## 4. ❌ Funding Rate Harvesting — отдельно от Basis Arb

### Причина отклонения

Funding Rate Harvesting — это **подмножество** Basis Arbitrage. Отдельная стратегия не нужна: всё, что делает funding harvesting (long spot + short perp при funding > 0.05%), уже включено в раздел Basis Arb.

**Разделение вредно**, потому что:
- Дублирование логики
- Разные пороги → путаница
- Funding rate является **компонентом** базиса, а не отдельным сигналом

**Решение:** Funding Rate Harvesting реализован как `should_enter_basis_arb()` с порогом `min_funding_rate = 0.05%` внутри модуля Basis Arb.

---

## 5. ❌ Cross-Exchange Arbitrage (Межбиржевой арбитраж)

### Причина отклонения

| Фактор | Проблема |
|---|---|
| **Latency** | Перевод между биржами: 1–30 минут. За это время спред исчезает в 95% случаев. |
| **Withdrawal fees** | Комиссия вывода BTC ~$2–10, ETH ~$1–5 → уничтожает мелкий профит. |
| **Withdrawal limits** | Дневные лимиты вывода (даже на VIP) ограничивают объём. |
| **Counterparty risk** | Одна биржа может заморозить средства (FTX, 2022). |
| **Capital efficiency** | Нужен капитал на ОБЕИХ биржах одновременно → 2× капитал. |

**Математика:** средний cross-exchange спред на BTC: 0.01–0.05%. Комиссия вывода + 2 транзакции + latency slippage = 0.1–0.3%. Нетто: **убыток**.

**Единственный случай**, когда работает: pre-funded accounts (деньги уже на обеих биржах) + co-located серверы + спред > 0.3%. Но это не масштабируется.

---

## 6. ❌ Latency Arbitrage

### Причина отклонения

| Фактор | Проблема |
|---|---|
| **HFT infrastructure** | Требуется co-location, FPGA, прямые оптоволоконные линии. Стоимость: $500K–$5M. |
| **Regulatory** | На регулируемых рынках latency arb может квалифицироваться как market manipulation. |
| **Exchange anti-latency** | Биржи (Binance, Coinbase) активно борются: random delays, batch auctions, speed bumps. |
| **Zero-sum** | Latency arb = taking liquidity от других участников. Это не создаёт ценности, а извлекает ренту из инфраструктуры. |
| **Unsustainable** | Каждый миллисекундный спред арбитражируется за < 1 секунды. Окно возможностей: < 100ms. |

**Для розничного/полупрофессионального бота это физически невозможно.**

---

## 7. ❌ DEX-CEX Arbitrage

### Причина отклонения

| Фактор | Проблема |
|---|---|
| **Gas fees** | Транзакция на Ethereum: $2–50+. На Solana: $0.001, но мем-пулы MEV-ботов. |
| **MEV (Maximal Extractable Value)** | MEV-боты (Flashbots, Jito) front-run DEX-CEX арбитраж в < 1 секунду. |
| **Impermanent loss** | Если LP в пуле DEX → IL может уничтожить профит. |
| **Smart contract risk** | Баги в смарт-контрактах DEX → потеря средств. |
| **Slippage на DEX** | AMM-цена отклоняется от рыночной на крупных объёмах → x*y=k формула даёт нелинейное проскальзывание. |

**Математика для Uniswap V2:**

```
Effective_Price = x_out / y_in = (y × x) / (x + y_in × (1 − fee))
Slippage = 1 − Effective_Price / Spot_Price
```

При объёме $10K на пуле $1M: slippage ≈ 1%. При комиссии DEX 0.3% + CEX 0.1% + gas $5 = **убыток**.

**Единственный вариант:** Solana DEX (низкий gas) + MEV-защита (Jito bundles) + pre-funded CEX. Но это нишевый и рискованный вариант.

---

## 8. ❌ Options Put-Call Parity (Паритет пут-колл опционов)

### Причина отклонения

| Фактор | Проблема |
|---|---|
| **Ликвидность опционов в крипто** | Только BTC и ETH имеют ликвидные опционы (Deribit). Остальные альткоины — нет. |
| **Bid-ask spread** | Спред на опционах Deribit: 2–10% → невозможно зафиксировать безрисковый профит. |
| **Маржинальные требования** | Для short опционов нужна огромная маржа → капитал неэффективен. |
| **Put-Call Parity формула** | `C − P = S − K × e^(−rT)`. Любое отклонение арбитражируется маркет-мейкерами за < 1 секунды. |

**Формула для справки:**

```
C − P = S − K × e^(−r×T)

где:
  C = цена колл-опциона
  P = цена пут-опциона
  S = цена базового актива (spot)
  K = страйк-цена
  r = безрисковая ставка
  T = время до экспирации (в годах)

Если C − P > S − K × e^(−rT): продать колл, купить пут, купить spot
Если C − P < S − K × e^(−rT): купить колл, продать пут, продать spot
```

**Проблема:** на крипто-рынках `r` не определён (какой безрисковый rate использовать для BTC?). Bid-ask на опционах > спред паритета. Невозможно.

---

## 9. ❌ Cross-Exchange Triangular Arbitrage

### Причина отклонения

Это комбинация Cross-Exchange + Triangular. Страдает от **обеих** проблем:

- Latency между биржами: 50–500ms
- Withdrawal fees + время
- Нужен капитал на 2+ биржах

Математически: треугольный арбитраж внутри одной биржи имеет спред ~0.05–0.3%. Межбиржевой треугольный — нужно > 0.5% спреда для покрытия withdrawal costs. Это бывает < 1% времени.

**Решение:** используйте Triangular Arbitrage (раздел 1) внутри одной биржи с pre-funded мультивалютным балансом.

---

## Итог: выбранные стратегии

### ⭐ Triangular Arbitrage (основная стратегия)

**Почему:**
- Мгновенное исполнение на одной бирже
- Нет межбиржевого риска
- Тысячи треугольников на крупных биржах
- Профит 0.05–0.5% за сделку × 100+ сделок/день = 5–50%/день теоретически

**Риски:** slippage, race condition, API limits

### ⭐ Statistical Arbitrage — Pairs Trading (стратегия 2)

**Почему:**
- Коинтегрированные пары (ETH/BTC, SOL/ETH) дают стабильный alpha
- Профит 2–8% за сделку
- Среднее время в сделке: 2–5 дней
- Низкая корреляция с рынком (рыночно-нейтральная)

**Риски:** нарушение коинтеграции, долгий возврат, капиталозатратность

### ⭐ Basis Arbitrage — Cash-and-Carry (стратегия 3)

**Почему:**
- Минимальный рыночный риск (дельта-нейтральная позиция)
- Годовая доходность 15–120% в contango-рынках
- Предсказуемый доход (funding каждые 8ч)
- Подходит для крупного капитала ($100K+)

**Риски:** basis collapse, funding flip, капиталозатратность

---

## Сводная таблица порогов

| Параметр | Triangular | Pairs Trading | Basis Arb |
|---|---|---|---|
| Мин. профит | 0.05% | 2σ отклонение | 15% годовых |
| Макс. latency | 100ms | Нет (длительные) | Нет (длительные) |
| Мин. ликвидность | $50K/ногу | Сравнимая | $100K позиция |
| Стоп-лосс | Не нужен (мгновенный) | Z > 4.0 | Funding < −0.01% |
| Таймфрейм | Секунды | Часы–дни | Дни–месяцы |
| Капитал | $5K–$50K | $50K–$500K | $100K+ |
| Сложность реализации | Средняя | Высокая | Средняя |

---

## Интеграция с архитектурой бота

Все три стратегии реализуют трейт `ArbitrageStrategy`:

```rust
/// Базовый трейт для всех арбитражных стратегий
#[async_trait]
pub trait ArbitrageStrategy: Send + Sync {
    /// Имя стратегии
    fn name(&self) -> &str;

    /// Сканировать рынок на наличие арбитражных возможностей
    async fn scan(&self, market_data: &MarketSnapshot) -> Vec<ArbOpportunity>;

    /// Оценить прибыльность возможности с учётом всех издержек
    fn evaluate(&self, opportunity: &ArbOpportunity, config: &ArbConfig) -> Option<ArbResult>;

    /// Исполнить арбитражную сделку
    async fn execute(&self, opportunity: &ArbOpportunity) -> Result<ArbExecution, ArbError>;

    /// Текущий P&L стратегии
    fn current_pnl(&self) -> Decimal;
}

/// Единая точка входа — сканирует все стратегии
pub struct ArbScanner {
    triangular: TriangularArbStrategy,
    pairs: PairsTradingStrategy,
    basis: BasisArbStrategy,
}

impl ArbScanner {
    pub async fn scan_all(&self, market: &MarketSnapshot) -> Vec<ArbOpportunity> {
        let mut opportunities = Vec::new();

        // Параллельный скан всех стратегий
        let (tri, pairs, basis) = tokio::join!(
            self.triangular.scan(market),
            self.pairs.scan(market),
            self.basis.scan(market),
        );

        opportunities.extend(tri);
        opportunities.extend(pairs);
        opportunities.extend(basis);

        // Сортировка по ожидаемой прибыльности
        opportunities.sort_by(|a, b| b.expected_profit.cmp(&a.expected_profit));
        opportunities
    }
}
```

---

## Заключение

Из 9 рассмотренных арбитражных стратегий **3 выбраны** как жизнеспособные для крипто-торгового бота:

1. **Triangular Arbitrage** — основа: высокая частота, низкий риск, быстрое исполнение
2. **Pairs Trading** — alpha-источник: рыночно-нейтральная доходность 2–8% за сделку
3. **Basis Arb (Cash-and-Carry)** — стабильный доход: 15–120% годовых на contango

Остальные 6 отклонены: latency arb невозможен без HFT-инфраструктуры, cross-exchange убыточен из-за withdrawal costs, DEX-CEX подавлен MEV-ботами, options parity недоступна из-за illiquidity, funding harvesting — подмножество basis arb.

**Ключевой инсайт:** крипто-арбитраж выигрывает не от сложности стратегий, а от скорости исполнения и контроля издержек. Все формулы выше содержат комиссии, slippage и latency — без них «безрисковый» профит на бумаге превращается в убыток в реальности.
