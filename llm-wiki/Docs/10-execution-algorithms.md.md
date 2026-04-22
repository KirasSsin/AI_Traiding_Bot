# Агент 10: Алгоритмы исполнения ордеров (Execution Algorithms)

**Дата:** 17 апреля 2026  
**Контекст:** Крипто-торговый бот, Binance spot/futures  
**Назначение:** Полный каталог алгоритмов исполнения с математикой, edge cases и Rust-реализациями

---

## Содержание

1. [Модели проскальзывания (Slippage Models)](#1-модели-проскальзывания-slippage-models)
2. [Каталог алгоритмов исполнения](#2-каталог-алгоритмов-исполнения)
3. [Crypto-specific: Комиссии и типы ордеров](#3-crypto-specific-комиссии-и-типы-ордеров)
4. [Рекомендации: MVP vs Production](#4-рекомендации-mvp-vs-production)
5. [Магические числа и конфигурация](#5-магические-числа-и-конфигурация)
6. [Сводная таблица сравнения](#6-сводная-таблица-сравнения)

---

## 1. Модели проскальзывания (Slippage Models)

### 1.1 Fixed (Basis Points)

**Формула:**
```
slippage_cost = |side| × price × Q × bps / 10000

где:
  side = +1 (buy), -1 (sell)
  price = reference price
  Q = order quantity (в базовой валюте)
  bps = проскальзывание в базисных пунктах (например, 5 bps = 0.05%)
```

**Обоснование:** Самая простая модель. Предполагает постоянное процентное отклонение от reference price. Подходит для бэктестинга при малых объёмах.

**Edge cases:**
- `Q → ∞`: slippage линейно растёт, не реалистично для крупных ордеров
- `bps = 0`: пренебрежение slippage — опасно для доверия бэктесту
- Flash crash: не улавливает аномальные движения

**Rust-реализация:**
```rust
/// Fixed basis points slippage model
#[derive(Debug, Clone)]
pub struct FixedSlippageModel {
    /// Slippage in basis points (e.g., 5.0 = 0.05%)
    pub bps: f64,
}

impl FixedSlippageModel {
    pub fn new(bps: f64) -> Self {
        assert!(bps >= 0.0, "bps must be non-negative");
        Self { bps }
    }

    /// Calculate execution price after slippage
    pub fn execution_price(&self, reference_price: f64, side: Side) -> f64 {
        let sign = match side {
            Side::Buy => 1.0,
            Side::Sell => -1.0,
        };
        reference_price * (1.0 + sign * self.bps / 10000.0)
    }

    /// Calculate total slippage cost in quote currency
    pub fn slippage_cost(&self, reference_price: f64, quantity: f64, side: Side) -> f64 {
        let exec_price = self.execution_price(reference_price, side);
        (exec_price - reference_price).abs() * quantity
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Side {
    Buy,
    Sell,
}
```

**Магические числа:**
| Параметр | Значение | Комментарий |
|---|---|---|
| `bps` | 5.0 | Типично для BTC/USDT при объёмах < 0.1% от daily volume |

---

### 1.2 Square Root (Квадратичная модель)

**Формула:**
```
slippage_price = κ × σ × √(Q / V)

где:
  κ = 0.1 (эмпирическая константа)
  σ = дневная волатильность (standard deviation of returns)
  Q = размер ордера (в базовой валюте)
  V = средний дневной объём торгов (в базовой валюте)

execution_price = reference_price × (1 ± slippage_price)
  "+" для покупки, "−" для продажи
```

**Обоснование:** Основана на модели квадратичного market impact (Almgren, 2005). Корень из отношения объёма ордера к дневному объёму отражает нелинейность воздействия на рынок. Рекомендуется в документации проекта.

**Edge cases:**
1. **Q > V** (ордер больше дневного объёма): slippage → ∞.  
   **Решение:** clamp `Q/V ≤ 0.1`.
2. **σ = 0** (flat рынок): slippage = 0. Корректно.
3. **V = 0** (неликвидный актив): деление на ноль.  
   **Решение:** `V = max(V, epsilon)`.
4. **Q = 0**: slippage = 0. Корректно.

**Rust-реализация:**
```rust
/// Square-root slippage model: κ × σ × √(Q / V)
#[derive(Debug, Clone)]
pub struct SqrtSlippageModel {
    /// Empirical constant (default: 0.1)
    pub kappa: f64,
    /// Maximum allowed Q/V ratio (default: 0.1)
    pub max_impact_ratio: f64,
    /// Minimum volume floor to prevent division by zero
    pub volume_floor: f64,
}

impl SqrtSlippageModel {
    pub fn new(kappa: f64) -> Self {
        Self {
            kappa,
            max_impact_ratio: 0.1,
            volume_floor: 1.0,
        }
    }

    /// Calculate slippage as fraction of price
    pub fn slippage_fraction(
        &self,
        daily_volatility: f64,
        order_quantity: f64,
        daily_volume: f64,
    ) -> f64 {
        let v = daily_volume.max(self.volume_floor);
        let impact_ratio = (order_quantity / v).min(self.max_impact_ratio);
        self.kappa * daily_volatility * impact_ratio.sqrt()
    }

    /// Calculate execution price
    pub fn execution_price(
        &self,
        reference_price: f64,
        quantity: f64,
        side: Side,
        daily_volatility: f64,
        daily_volume: f64,
    ) -> f64 {
        let slippage = self.slippage_fraction(daily_volatility, quantity, daily_volume);
        match side {
            Side::Buy => reference_price * (1.0 + slippage),
            Side::Sell => reference_price * (1.0 - slippage),
        }
    }

    /// Cost in quote currency
    pub fn slippage_cost(
        &self,
        reference_price: f64,
        quantity: f64,
        side: Side,
        daily_volatility: f64,
        daily_volume: f64,
    ) -> f64 {
        let exec_price = self.execution_price(reference_price, quantity, side, daily_volatility, daily_volume);
        (exec_price - reference_price).abs() * quantity
    }
}
```

**Магические числа:**
| Параметр | Значение | Источник |
|---|---|---|
| `κ` | 0.1 | Эмпирическая константа (Almgren, 2005) |
| `max_impact_ratio` | 0.1 | Q/V ограничение |
| `volume_floor` | 1.0 | Защита от деления на 0 |

---

### 1.3 Linear Slippage

**Формула:**
```
slippage_fraction = α × (Q / V)

где:
  α = коэффициент линейной зависимости (эмпирический)
  Q = размер ордера
  V = дневной объём

execution_price = reference_price × (1 ± slippage_fraction)
```

**Обоснование:** Линейная аппроксимация для малых ордеров (Q/V < 0.01). При малых Q/V квадратичная и линейная модели совпадают, т.к. √x ≈ x при x→0. Проще вычислять.

**Edge cases:**
- Q/V > 1: slippage > 100%, что абсурдно. Ограничивать `Q/V ≤ 0.5`.
- Менее точна для крупных ордеров по сравнению с sqrt-моделью.

**Rust-реализация:**
```rust
/// Linear slippage model: α × (Q / V)
#[derive(Debug, Clone)]
pub struct LinearSlippageModel {
    pub alpha: f64,
    pub max_impact_ratio: f64,
}

impl LinearSlippageModel {
    pub fn new(alpha: f64) -> Self {
        Self {
            alpha,
            max_impact_ratio: 0.5,
        }
    }

    pub fn slippage_fraction(
        &self,
        order_quantity: f64,
        daily_volume: f64,
    ) -> f64 {
        let impact_ratio = (order_quantity / daily_volume.max(1.0)).min(self.max_impact_ratio);
        self.alpha * impact_ratio
    }
}
```

---

### 1.4 Almgren-Chriss (Permanent + Temporary Impact)

**Формула:**
```
Total Cost = Permanent Impact + Temporary Impact + Timing Risk

Permanent Impact:
  S(t) = S(0) + γ × Σ v(k) + σ × W(t)
  γ = постоянный impact-коэффициент

Temporary Impact:
  g(v) = ε × sgn(v) + η × v
  ε = полукруговой спред (fixed cost per trade)
  η = temporary impact-коэффициент

Optimal Trajectory (minimizes E[cost] + λ × Var[cost]):
  x(k) = sinh(κ × (T - t(k))) / sinh(κ × T) × X
  κ = √(λ × σ² / η)  (risk aversion parameter)
  λ = risk aversion коэффициент трейдера

Total expected cost:
  E[C] = η × X² / T × (1 + (λ × σ² × T²) / (3 × η))
       + ε × N  (N = количество трейдов)
```

**Обоснование:** Золотой стандарт в execution для институциональных трейдеров. Оптимально балансирует между market impact (быстрое исполнение = больше impact) и timing risk (медленное исполнение = больше риска движения цены).

**Edge cases:**
- `λ → 0` (безразличный к риску): агрессивное исполнение (всё сразу)
- `λ → ∞` (极度 risk-averse): медленное исполнение (равномерно)
- `σ = 0` (flat рынок): оптимально исполнить всё сразу
- Требует точную оценку γ, η, σ — малые ошибки дают субоптимальное исполнение

**Rust-реализация:**
```rust
/// Almgren-Chriss optimal execution model
#[derive(Debug, Clone)]
pub struct AlmgrenChrissModel {
    /// Permanent impact coefficient
    pub gamma: f64,
    /// Temporary impact coefficient
    pub eta: f64,
    /// Fixed cost per trade (half-spread)
    pub epsilon: f64,
    /// Risk aversion parameter
    pub lambda: f64,
    /// Volatility (annualized or per-period)
    pub sigma: f64,
}

impl AlmgrenChrissModel {
    pub fn new(gamma: f64, eta: f64, epsilon: f64, lambda: f64, sigma: f64) -> Self {
        Self { gamma, eta, epsilon, lambda, sigma }
    }

    /// Calculate optimal trading trajectory
    /// Returns vector of (time_step, quantity_to_trade)
    pub fn optimal_trajectory(
        &self,
        total_quantity: f64,
        num_periods: usize,
    ) -> Vec<(usize, f64)> {
        if num_periods == 0 {
            return vec![];
        }
        
        // κ = √(λ × σ² / η)
        let kappa = (self.lambda * self.sigma.powi(2) / self.eta).sqrt();
        let t_total = num_periods as f64;
        
        let mut trajectory = Vec::with_capacity(num_periods);
        let mut remaining = total_quantity;
        
        for k in 0..num_periods {
            let t_k = k as f64;
            // Optimal remaining at time k: x(k) = X × sinh(κ(T-t)) / sinh(κT)
            let x_k = if kappa.abs() < 1e-10 {
                // Linear decay when kappa → 0
                total_quantity * (1.0 - t_k / t_total)
            } else {
                total_quantity * (kappa * (t_total - t_k)).sinh() / (kappa * t_total).sinh()
            };
            
            // Quantity to trade in this period
            let x_next = if k + 1 < num_periods {
                let t_next = (k + 1) as f64;
                if kappa.abs() < 1e-10 {
                    total_quantity * (1.0 - t_next / t_total)
                } else {
                    total_quantity * (kappa * (t_total - t_next)).sinh() / (kappa * t_total).sinh()
                }
            } else {
                0.0
            };
            
            let trade_qty = (x_k - x_next).min(remaining).max(0.0);
            remaining -= trade_qty;
            trajectory.push((k, trade_qty));
        }
        
        trajectory
    }

    /// Expected total execution cost
    pub fn expected_cost(&self, total_quantity: f64, num_periods: usize) -> f64 {
        let t = num_periods as f64;
        let x = total_quantity;
        
        // E[C] = η × X² / T × (1 + λσ²T² / 3η) + ε × N
        let impact_cost = self.eta * x.powi(2) / t 
            * (1.0 + self.lambda * self.sigma.powi(2) * t.powi(2) / (3.0 * self.eta));
        let fixed_cost = self.epsilon * num_periods as f64;
        
        impact_cost + fixed_cost
    }

    /// Variance of execution cost (timing risk)
    pub fn cost_variance(&self, total_quantity: f64, num_periods: usize) -> f64 {
        let t = num_periods as f64;
        let x = total_quantity;
        
        // Var[C] = σ² × X² × T / 3 × (1 - λσ²T² / (5η))
        // Simplified for practical use
        self.sigma.powi(2) * x.powi(2) * t / 3.0
    }
}
```

**Магические числа:**
| Параметр | Значение | Комментарий |
|---|---|---|
| `γ` (permanent impact) | 2.5e-7 | Для BTC/USDT, зависит от liquidity |
| `η` (temporary impact) | 1.0e-6 | Временный impact |
| `ε` (half-spread) | 0.5 | В тиках |
| `λ` (risk aversion) | 1e-6 | Умеренная risk aversion |
| `σ` (volatility) | 0.02 | Дневная vol ~2% для BTC |

---

## 2. Каталог алгоритмов исполнения

### 2.1 Market Order

**Формула:**
```
execution_price = best_ask (buy) | best_bid (sell)
actual_price = execution_price × (1 ± slippage_model)
total_cost = actual_price × Q + commission(Q × actual_price)
```

**Обоснование:** Мгновенное исполнение по лучшей доступной цене. Гарантия fill, но максимальный market impact. Самый дорогой способ.

**Edge cases:**
- **Thin liquidity:** малый стакан → огромное проскальзывание
- **Flash crash:** покупка на пике/продажа на дне
- **Partial fills:** на spot Binance может быть частичное исполнение при малой ликвидности

**Rust-реализация:**
```rust
use std::time::Duration;
use tokio::time::timeout;

/// Market order executor
pub struct MarketOrderExecutor {
    pub slippage_model: SqrtSlippageModel,
    pub commission_rate: f64, // 0.0004 for Binance taker
    pub max_order_timeout: Duration,
}

impl MarketOrderExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
        side: Side,
        quantity: f64,
        reference_price: f64,
        daily_volatility: f64,
        daily_volume: f64,
    ) -> Result<FillReport, ExecutionError> {
        // Pre-flight: estimate cost
        let est_price = self.slippage_model.execution_price(
            reference_price, quantity, side, daily_volatility, daily_volume,
        );
        let est_commission = est_price * quantity * self.commission_rate;
        
        // Place order with timeout
        let order_result = timeout(
            self.max_order_timeout,
            exchange.place_market_order(symbol, side, quantity),
        ).await;
        
        match order_result {
            Ok(Ok(fill)) => {
                let commission = fill.price * fill.filled_qty * self.commission_rate;
                Ok(FillReport {
                    requested_qty: quantity,
                    filled_qty: fill.filled_qty,
                    avg_price: fill.price,
                    commission,
                    slippage: (fill.price - reference_price) / reference_price,
                    timestamp: fill.timestamp,
                })
            }
            Ok(Err(e)) => Err(ExecutionError::ExchangeError(e.to_string())),
            Err(_) => Err(ExecutionError::Timeout),
        }
    }
}
```

---

### 2.2 Limit Order

**Формула:**
```
buy_limit_price = reference_price × (1 - offset)
sell_limit_price = reference_price × (1 + offset)

Fill probability (модель):
  P(fill, t) = 1 - exp(-λ × t × distance_to_touch)

где:
  offset = желаемое отклонение от reference price
  λ = intensity параметр (зависит от волатильности)
  distance_to_touch = |limit_price - best_opposite|
```

**Обоснование:** Ордер по указанной цене или лучше. Maker fee (0.02%) вместо taker (0.04%). Нет гарантии исполнения. Подходит для терпеливых стратегий.

**Edge cases:**
- **Не исполнен:** ордер висит → opportunity cost
- **Частичное исполнение:** часть Q fill, остаток pending
- **Flash crash:** buy limit fill на аномально низкой цене → "free money" или "catching a falling knife"
- **Stale order:** цена ушла, ордер никогда не fill

**Rust-реализация:**
```rust
/// Limit order with time-in-force and fill tracking
#[derive(Debug, Clone)]
pub enum TimeInForce {
    GTC,  // Good Till Cancelled
    IOC,  // Immediate Or Cancel
    FOK,  // Fill Or Kill
    GTX,  // Good Till Crossing (post-only)
}

pub struct LimitOrderExecutor {
    pub commission_rate: f64,       // 0.0002 for Binance maker
    pub default_tif: TimeInForce,
    pub max_pending_duration: Duration,
}

impl LimitOrderExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
        side: Side,
        quantity: f64,
        limit_price: f64,
        tif: Option<TimeInForce>,
    ) -> Result<FillReport, ExecutionError> {
        let tif = tif.unwrap_or(self.default_tif.clone());
        
        let order_id = exchange.place_limit_order(
            symbol, side, quantity, limit_price, tif,
        ).await?;
        
        // Poll for fill with timeout
        let result = timeout(self.max_pending_duration, async {
            loop {
                let status = exchange.order_status(symbol, &order_id).await?;
                match status.state {
                    OrderState::Filled => return Ok(status),
                    OrderState::PartiallyFilled => {
                        // Could decide to cancel remaining or wait
                    }
                    OrderState::Cancelled => {
                        return Err(ExecutionError::OrderCancelled);
                    }
                    _ => {}
                }
                tokio::time::sleep(Duration::from_millis(500)).await;
            }
        }).await;
        
        match result {
            Ok(Ok(status)) => Ok(FillReport {
                requested_qty: quantity,
                filled_qty: status.filled_qty,
                avg_price: status.avg_price,
                commission: status.avg_price * status.filled_qty * self.commission_rate,
                slippage: (status.avg_price - limit_price).abs() / limit_price,
                timestamp: status.update_time,
            }),
            Ok(Err(e)) => Err(e),
            Err(_) => {
                // Timeout: cancel unfilled portion
                let _ = exchange.cancel_order(symbol, &order_id).await;
                Err(ExecutionError::Timeout)
            }
        }
    }
}
```

---

### 2.3 VWAP Execution (Volume-Weighted Average Price)

**Формула:**
```
Target: execute total Q such that avg_price ≈ VWAP_session

VWAP_session = Σ(price_i × volume_i) / Σ(volume_i)

Slice schedule:
  Q_i = Q_total × (V_i / V_expected)
  
где:
  V_i = observed volume in interval i
  V_expected = predicted total session volume

Implementation shortfall vs VWAP:
  IS = side × (avg_fill_price - VWAP) / VWAP
```

**Обоснование:** Разбивает крупный ордер на части пропорционально объёму торгов. Стремится к средневзвешенной цене сессии. Стандарт institutional execution.

**Edge cases:**
- **Непредсказуемый объём:** если V_real ≫ V_expected → недоисполнение
- **Трендовый рынок:** VWAP может быть худшей ценой (buy VWAP в uptrend = дорого)
- **Thin intervals:** мало объёма → невозможно исполнить slice
- **End of session rush:** большой объём в конце → давление на цену

**Rust-реализация:**
```rust
use std::collections::VecDeque;

/// VWAP execution algorithm
pub struct VwapExecutor {
    /// Total quantity to execute
    pub total_quantity: f64,
    /// Number of time slices
    pub num_slices: usize,
    /// Duration of each slice
    pub slice_duration: Duration,
    /// Historical volume profile (fraction per slice, sums to 1.0)
    pub volume_profile: Vec<f64>,
    /// Tolerance: execute if within ±tolerance of target
    pub participation_tolerance: f64,
}

impl VwapExecutor {
    pub fn new(
        total_quantity: f64,
        session_duration: Duration,
        slice_duration: Duration,
        historical_volume_profile: Vec<f64>,
    ) -> Self {
        let num_slices = (session_duration.as_secs() / slice_duration.as_secs()) as usize;
        
        // Normalize volume profile
        let total: f64 = historical_volume_profile.iter().sum();
        let profile: Vec<f64> = if total > 0.0 {
            historical_volume_profile.iter().map(|v| v / total).collect()
        } else {
            vec![1.0 / num_slices as f64; num_slices]
        };
        
        Self {
            total_quantity,
            num_slices,
            slice_duration,
            volume_profile: profile,
            participation_tolerance: 0.2, // 20% tolerance
        }
    }

    /// Calculate target quantity for slice i based on volume
    pub fn target_quantity_for_slice(
        &self,
        slice_index: usize,
        observed_slice_volume: f64,
        total_session_volume_so_far: f64,
        expected_total_volume: f64,
    ) -> f64 {
        if slice_index >= self.volume_profile.len() {
            return 0.0;
        }
        
        let expected_slice_volume = self.volume_profile[slice_index] * expected_total_volume;
        
        // Volume-adaptive: if more volume than expected, trade more
        let volume_ratio = if expected_slice_volume > 0.0 {
            (observed_slice_volume / expected_slice_volume)
                .min(1.0 + self.participation_tolerance)
                .max(1.0 - self.participation_tolerance)
        } else {
            1.0
        };
        
        let base_quantity = self.total_quantity * self.volume_profile[slice_index];
        base_quantity * volume_ratio
    }

    /// Track VWAP of the session so far
    pub fn update_session_vwap(
        prices: &VecDeque<f64>,
        volumes: &VecDeque<f64>,
    ) -> f64 {
        let total_volume: f64 = volumes.iter().sum();
        if total_volume == 0.0 {
            return 0.0;
        }
        let pv_sum: f64 = prices.iter().zip(volumes.iter()).map(|(p, v)| p * v).sum();
        pv_sum / total_volume
    }
}
```

**Магические числа:**
| Параметр | Значение | Комментарий |
|---|---|---|
| `num_slices` | 20–48 | Зависит от таймфрейма (1H → 24 слайса за день) |
| `participation_tolerance` | 0.20 | ±20% от ожидаемого объёма слайса |
| `slice_duration` | 15min–1H | Для крипто 24/7 рынка |

---

### 2.4 TWAP Execution (Time-Weighted Average Price)

**Формула:**
```
Target: execute Q_total uniformly over time T

Q_slice = Q_total / N

где N = number of time slices

TWAP = (1/N) × Σ price(slice_i)

Execution variance:
  Var[IS] = σ² × T / N  (уменьшается с ростом N)
```

**Обоснование:** Самый простой алгоритм разбиения. Равномерное распределение ордера по времени. Не требует предсказания объёма. Хуже VWAP по impact, но проще и надёжнее.

**Edge cases:**
- **Резкий spike в одном слайсе:** часть ордера fill по плохой цене
- **Thin liquidity в ночное время:** малый стакан → проскальзывание на ночных слайсах
- **Конец таймера:** если не всё исполнено → market order на остаток

**Rust-реализация:**
```rust
/// TWAP execution algorithm
pub struct TwapExecutor {
    pub total_quantity: f64,
    pub num_slices: usize,
    pub slice_duration: Duration,
    /// Strategy for unfilled remainder at end
    pub end_strategy: EndStrategy,
}

#[derive(Debug, Clone)]
pub enum EndStrategy {
    /// Convert remaining to market order
    MarketOnClose,
    /// Leave as GTC limit order
    LeaveGTC,
    /// Cancel everything
    Cancel,
}

impl TwapExecutor {
    pub fn new(
        total_quantity: f64,
        session_duration: Duration,
        slice_duration: Duration,
    ) -> Self {
        let num_slices = (session_duration.as_secs() / slice_duration.as_secs()).max(1) as usize;
        Self {
            total_quantity,
            num_slices,
            slice_duration,
            end_strategy: EndStrategy::MarketOnClose,
        }
    }

    /// Fixed quantity per slice
    pub fn quantity_per_slice(&self) -> f64 {
        self.total_quantity / self.num_slices as f64
    }

    /// Execute one slice
    pub async fn execute_slice(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
        side: Side,
        slice_index: usize,
        remaining: f64,
    ) -> Result<FillReport, ExecutionError> {
        let qty = if slice_index == self.num_slices - 1 {
            remaining // Last slice: take everything remaining
        } else {
            self.quantity_per_slice().min(remaining)
        };
        
        if qty <= 0.0 {
            return Err(ExecutionError::ZeroQuantity);
        }
        
        // Use IOC limit order for each slice
        exchange.place_limit_order(
            symbol, side, qty,
            Self::aggressive_limit_price(exchange, symbol, side).await?,
            TimeInForce::IOC,
        ).await?;
        
        // ... (fill tracking logic)
        todo!()
    }

    async fn aggressive_limit_price(
        exchange: &dyn ExchangeClient,
        symbol: &str,
        side: Side,
    ) -> Result<f64, ExecutionError> {
        let book = exchange.order_book(symbol, 1).await?;
        match side {
            Side::Buy => Ok(book.asks[0].price * 1.001), // Slightly above best ask
            Side::Sell => Ok(book.bids[0].price * 0.999), // Slightly below best bid
        }
    }
}
```

---

### 2.5 Implementation Shortfall (IS) / Arrival Price

**Формула:**
```
IS = side × (VWAP_execution - Arrival_Price) / Arrival_Price × Q

Decomposition:
  IS = Delay_Cost + Market_Impact_Cost + Opportunity_Cost

  Delay_Cost = Q_filled × (price_at_fill - arrival_price)
  Opportunity_Cost = Q_unfilled × (current_price - arrival_price)
  Market_Impact = IS - Delay_Cost - Opportunity_Cost

Target: minimize E[IS] + λ × Var[IS]
```

**Обоснование:** Универсальная метрика качества исполнения. Измеряет отклонение от цены в момент принятия решения (arrival price). Включает все источники издержек: задержку, impact и упущенную возможность.

**Edge cases:**
- **Полностью неисполнен:** IS = unrealized PnL на полный объём
- **Быстрое движение рынка:** large delay cost даже без impact
- **Невозможно измерить без benchmarks:** нужна фиксация arrival price

**Rust-реализация:**
```rust
/// Implementation Shortfall calculator and optimizer
pub struct ISExecutor {
    pub arrival_price: f64,
    pub total_quantity: f64,
    pub side: Side,
    pub fills: Vec<FillEvent>,
}

#[derive(Debug, Clone)]
pub struct FillEvent {
    pub timestamp: i64,
    pub price: f64,
    pub quantity: f64,
}

#[derive(Debug, Clone)]
pub struct ISReport {
    pub delay_cost: f64,
    pub market_impact: f64,
    pub opportunity_cost: f64,
    pub total_is: f64,
    pub is_bps: f64,
    pub filled_qty: f64,
    pub unfilled_qty: f64,
    pub vwap: f64,
}

impl ISExecutor {
    pub fn new(arrival_price: f64, total_quantity: f64, side: Side) -> Self {
        Self {
            arrival_price,
            total_quantity,
            side,
            fills: Vec::new(),
        }
    }

    pub fn record_fill(&mut self, fill: FillEvent) {
        self.fills.push(fill);
    }

    pub fn calculate_is(&self, current_price: f64) -> ISReport {
        let sign = match self.side {
            Side::Buy => 1.0,
            Side::Sell => -1.0,
        };
        
        let filled_qty: f64 = self.fills.iter().map(|f| f.quantity).sum();
        let unfilled_qty = self.total_quantity - filled_qty;
        
        // VWAP of fills
        let vwap = if filled_qty > 0.0 {
            self.fills.iter().map(|f| f.price * f.quantity).sum::<f64>() / filled_qty
        } else {
            self.arrival_price
        };
        
        // Delay cost: filled qty × (VWAP - arrival)
        let delay_cost = sign * (vwap - self.arrival_price) * filled_qty;
        
        // Opportunity cost: unfilled qty × (current - arrival)
        let opportunity_cost = sign * (current_price - self.arrival_price) * unfilled_qty;
        
        // Total IS
        let total_is = delay_cost + opportunity_cost;
        let is_bps = total_is / (self.arrival_price * self.total_quantity) * 10000.0;
        
        ISReport {
            delay_cost,
            market_impact: 0.0, // Requires separate estimation
            opportunity_cost,
            total_is,
            is_bps,
            filled_qty,
            unfilled_qty,
            vwap,
        }
    }
}
```

---

### 2.6 Iceberg Orders

**Формула:**
```
visible_quantity = min(chunk_size, remaining_quantity)
chunk_size = total_quantity × chunk_fraction

где:
  chunk_fraction = 0.20 (20% от общего объёма)

Refresh logic:
  if visible_qty_filled → next_chunk = min(chunk, remaining)
  until remaining = 0 or timeout
```

**Обоснование:** Скрывает истинный размер ордера. Показывает только "кусок айсберга". Уменьшает market impact крупного ордера. На Binance — через API с параметром `icebergQty`.

**Edge cases:**
- **Частичное исполнение чанка:** refill visible portion
- **Цена ушла:** остаток не fill (для limit iceberg)
- **Detected by HFT:** pattern-matching обнаруживает повторяющиеся чанки → adverse selection
- **API rate limits:** множество replace-запросов может hit rate limit

**Rust-реализация:**
```rust
/// Iceberg order executor
pub struct IcebergExecutor {
    pub total_quantity: f64,
    pub chunk_fraction: f64,  // 0.20 = 20%
    pub min_chunk_size: f64,
    pub side: Side,
    pub order_type: IcebergOrderType,
}

#[derive(Debug, Clone)]
pub enum IcebergOrderType {
    /// Limit order at fixed price, iceberg chunks
    Limit { price: f64 },
    /// Market order split into timed chunks
    Market { interval: Duration },
    /// Pegged to best bid/ask
    Pegged { offset_bps: f64 },
}

impl IcebergExecutor {
    pub fn new(
        total_quantity: f64,
        chunk_fraction: f64,
        side: Side,
        order_type: IcebergOrderType,
    ) -> Self {
        Self {
            total_quantity,
            chunk_fraction,
            min_chunk_size: 0.0001, // Binance minimum
            side,
            order_type,
        }
    }

    pub fn next_chunk_size(&self, remaining: f64) -> f64 {
        let chunk = (self.total_quantity * self.chunk_fraction).max(self.min_chunk_size);
        chunk.min(remaining)
    }

    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
    ) -> Result<Vec<FillReport>, ExecutionError> {
        let mut remaining = self.total_quantity;
        let mut fills = Vec::new();
        let mut chunk_index = 0u64;
        
        while remaining > self.min_chunk_size {
            let chunk_qty = self.next_chunk_size(remaining);
            
            let fill = match &self.order_type {
                IcebergOrderType::Limit { price } => {
                    exchange.place_limit_order(
                        symbol, self.side, chunk_qty, *price, TimeInForce::GTC,
                    ).await?;
                    // Wait for fill...
                    self.wait_for_fill(exchange, symbol, chunk_qty).await?
                }
                IcebergOrderType::Market { interval } => {
                    let f = exchange.place_market_order(symbol, self.side, chunk_qty).await?;
                    tokio::time::sleep(*interval).await;
                    f
                }
                IcebergOrderType::Pegged { offset_bps } => {
                    let book = exchange.order_book(symbol, 1).await?;
                    let peg_price = match self.side {
                        Side::Buy => book.bids[0].price * (1.0 - offset_bps / 10000.0),
                        Side::Sell => book.asks[0].price * (1.0 + offset_bps / 10000.0),
                    };
                    exchange.place_limit_order(
                        symbol, self.side, chunk_qty, peg_price, TimeInForce::IOC,
                    ).await?;
                    self.wait_for_fill(exchange, symbol, chunk_qty).await?
                }
            };
            
            remaining -= fill.filled_qty;
            fills.push(fill);
            chunk_index += 1;
        }
        
        Ok(fills)
    }
}
```

**Магические числа:**
| Параметр | Значение | Комментарий |
|---|---|---|
| `chunk_fraction` | 0.20 | 20% от total — компромисс между stealth и fill speed |
| `min_chunk_size` | 0.0001 | Binance minimum order size |
| `refresh_interval` | 1–5 сек | Задержка между чанками |

---

### 2.7 Sniper Orders

**Формула:**
```
trigger_condition:
  if best_ask ≤ target_price (buy) OR best_bid ≥ target_price (sell)
  → execute immediately as market/limit order

target_price = reference_price × (1 - sniper_offset)  [buy]
             = reference_price × (1 + sniper_offset)  [sell]
```

**Обоснование:** "Ждёт" точную цену и стреляет при достижении. Минимизирует slippage — исполняет только когда цена "пришла". Аналог limit order с агрессивным мониторингом.

**Edge cases:**
- **Цена проскочила мимо (price gapped through):** missed opportunity
- **Flash spike:** сработал на мгновение → fill по плохой цене если market order
- **Latency:** запоздалый снайпер → цена уже ушла

**Rust-реализация:**
```rust
/// Sniper order: wait for target price, then execute aggressively
pub struct SniperExecutor {
    pub target_price: f64,
    pub quantity: f64,
    pub side: Side,
    /// Use limit order slightly better than target if possible
    pub use_limit: bool,
    pub check_interval: Duration,
    pub max_wait: Duration,
}

impl SniperExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
    ) -> Result<FillReport, ExecutionError> {
        let start = tokio::time::Instant::now();
        
        loop {
            if start.elapsed() > self.max_wait {
                return Err(ExecutionError::Timeout);
            }
            
            let book = exchange.order_book(symbol, 1).await?;
            
            let triggered = match self.side {
                Side::Buy => book.asks[0].price <= self.target_price,
                Side::Sell => book.bids[0].price >= self.target_price,
            };
            
            if triggered {
                if self.use_limit {
                    // Place aggressive limit at target
                    return exchange.place_limit_order(
                        symbol, self.side, self.quantity,
                        self.target_price, TimeInForce::IOC,
                    ).await;
                } else {
                    return exchange.place_market_order(
                        symbol, self.side, self.quantity,
                    ).await;
                }
            }
            
            tokio::time::sleep(self.check_interval).await;
        }
    }
}
```

---

### 2.8 Pegged Orders

**Формула:**
```
buy_price = best_bid × (1 - offset)
sell_price = best_ask × (1 + offset)

Refix logic:
  on_book_update → recalculate peg_price
  if |new_price - old_price| > threshold → cancel & replace
```

**Обоснование:** Динамически отслеживает лучшую цену в стакане. Автоматически обновляется при движениях рынка. "Passive posting" — всегда на краю стакана.

**Edge cases:**
- **Rapid book updates:** слишком частые cancel/replace → rate limit
- **Adverse selection:** pegged buy на best bid → всегда fill перед падением цены
- **Latency:** обновление peg отстаёт → stale order

**Rust-реализация:**
```rust
/// Pegged order: dynamically tracks best bid/ask
pub struct PeggedExecutor {
    pub offset_bps: f64,
    pub quantity: f64,
    pub side: Side,
    pub re_peg_threshold_bps: f64, // Min move to trigger re-peg
}

impl PeggedExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
    ) -> Result<FillReport, ExecutionError> {
        let mut current_order_id: Option<String> = None;
        let mut last_peg_price = 0.0;
        
        loop {
            let book = exchange.order_book(symbol, 1).await?;
            let peg_price = match self.side {
                Side::Buy => book.bids[0].price * (1.0 - self.offset_bps / 10000.0),
                Side::Sell => book.asks[0].price * (1.0 + self.offset_bps / 10000.0),
            };
            
            // Check if re-peg needed
            let price_moved = if last_peg_price > 0.0 {
                (peg_price - last_peg_price).abs() / last_peg_price * 10000.0
            } else {
                f64::MAX
            };
            
            if price_moved > self.re_peg_threshold_bps {
                // Cancel old order
                if let Some(id) = &current_order_id {
                    let _ = exchange.cancel_order(symbol, id).await;
                }
                
                // Place new order at peg price
                let order = exchange.place_limit_order(
                    symbol, self.side, self.quantity,
                    peg_price, TimeInForce::GTC,
                ).await?;
                
                current_order_id = Some(order.order_id);
                last_peg_price = peg_price;
            }
            
            // Check fill
            if let Some(id) = &current_order_id {
                let status = exchange.order_status(symbol, id).await?;
                if status.state == OrderState::Filled {
                    return Ok(FillReport {
                        requested_qty: self.quantity,
                        filled_qty: status.filled_qty,
                        avg_price: status.avg_price,
                        commission: status.avg_price * status.filled_qty * 0.0002,
                        slippage: 0.0, // Pegged = zero slippage from reference
                        timestamp: status.update_time,
                    });
                }
            }
            
            tokio::time::sleep(Duration::from_millis(200)).await;
        }
    }
}
```

---

### 2.9 Adaptive Orders (Guerrilla, Snack)

#### Guerrilla Orders

**Формула:**
```
Strategy: hide intent through randomized placement

chunk_size = uniform_random(min_chunk, max_chunk)
interval = uniform_random(min_interval, max_interval)
price = reference + random_offset(-max_offset, +max_offset)

Detection evasion:
  - Варьировать размер чанков (не паттерн)
  - Случайные задержки между ордерами
  - Менять side (иногда buy, иногда sell через spread)
  - Разные типы ордеров (limit, market, IOC mix)
```

**Обоснование:** Anti-gaming алгоритм. Специально маскирует крупный ордер под хаотичную торговлю. Противодействует детекции айсберг-ордеров HFT-алгоритмами.

**Rust-реализация:**
```rust
use rand::Rng;

/// Guerrilla order: randomized placement to evade detection
pub struct GuerrillaExecutor {
    pub total_quantity: f64,
    pub side: Side,
    pub min_chunk_fraction: f64,  // 0.05
    pub max_chunk_fraction: f64,  // 0.15
    pub min_interval_ms: u64,     // 500
    pub max_interval_ms: u64,     // 5000
    pub max_offset_bps: f64,      // 5.0
}

impl GuerrillaExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
    ) -> Result<Vec<FillReport>, ExecutionError> {
        let mut rng = rand::thread_rng();
        let mut remaining = self.total_quantity;
        let mut fills = Vec::new();
        
        while remaining > 0.0001 {
            // Random chunk size
            let chunk_frac = rng.gen_range(self.min_chunk_fraction..=self.max_chunk_fraction);
            let chunk_qty = (self.total_quantity * chunk_frac).min(remaining);
            
            // Random delay
            let delay_ms = rng.gen_range(self.min_interval_ms..=self.max_interval_ms);
            tokio::time::sleep(Duration::from_millis(delay_ms)).await;
            
            // Random order type
            let use_market = rng.gen_bool(0.3);
            let fill = if use_market {
                exchange.place_market_order(symbol, self.side, chunk_qty).await?
            } else {
                // Random offset from current price
                let book = exchange.order_book(symbol, 1).await?;
                let offset = rng.gen_range(-self.max_offset_bps..=self.max_offset_bps) / 10000.0;
                let price = match self.side {
                    Side::Buy => book.asks[0].price * (1.0 + offset),
                    Side::Sell => book.bids[0].price * (1.0 + offset),
                };
                exchange.place_limit_order(
                    symbol, self.side, chunk_qty, price, TimeInForce::IOC,
                ).await?
            };
            
            remaining -= fill.filled_qty;
            fills.push(fill);
        }
        
        Ok(fills)
    }
}
```

#### Snack Orders

**Формула:**
```
Opportunistic: take liquidity only when spread < threshold

execute_if:
  spread_bps = (best_ask - best_bid) / mid_price × 10000
  spread_bps < max_spread_bps AND book_depth > min_depth

  → place IOC limit at best opposite
```

**Обоснование:** "Перекусывает" ликвидность только при благоприятных условиях. Минимизирует cost через торговлю в узком спреде. Подходит для market-making стратегий.

**Rust-реализация:**
```rust
/// Snack order: opportunistic execution when spread is tight
pub struct SnackExecutor {
    pub quantity: f64,
    pub side: Side,
    pub max_spread_bps: f64,   // Max spread to execute
    pub min_depth: f64,         // Min book depth at best level
    pub check_interval: Duration,
}

impl SnackExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
    ) -> Result<Option<FillReport>, ExecutionError> {
        let book = exchange.order_book(symbol, 5).await?;
        let mid = (book.asks[0].price + book.bids[0].price) / 2.0;
        let spread_bps = (book.asks[0].price - book.bids[0].price) / mid * 10000.0;
        
        if spread_bps > self.max_spread_bps {
            return Ok(None); // Spread too wide, skip
        }
        
        let depth = match self.side {
            Side::Buy => book.asks[0].quantity,
            Side::Sell => book.bids[0].quantity,
        };
        
        if depth < self.min_depth {
            return Ok(None); // Not enough depth
        }
        
        let fill = exchange.place_limit_order(
            symbol, self.side, self.quantity,
            match self.side {
                Side::Buy => book.asks[0].price,
                Side::Sell => book.bids[0].price,
            },
            TimeInForce::IOC,
        ).await?;
        
        Ok(Some(fill))
    }
}
```

---

### 2.10 Smart Order Routing (SOR)

**Формула:**
```
For each venue i:
  effective_price_i = quoted_price_i + fee_i + slippage_model(volume_i)
  available_qty_i = book_depth_at_price(venue_i)

Optimization:
  minimize Σ effective_price_i × q_i
  subject to:
    Σ q_i = Q_total
    0 ≤ q_i ≤ available_qty_i
    q_i ≥ min_order_size_i  OR  q_i = 0
```

**Обоснование:** Разделяет ордер между несколькими биржами для лучшей цены. В крипто: Binance + Bybit + OKX + Coinbase. Учитывает fees, latency и depth каждой площадки.

**Edge cases:**
- **Latency между площадками:** цена изменилась пока ордер летит
- **Partial fill на одной бирже:** rebalance на ходу
- **Withdraw fees:** если нужен арбитраж между spot-биржами

**Rust-реализация:**
```rust
/// Smart Order Router across multiple exchanges
pub struct SmartOrderRouter {
    pub exchanges: Vec<Arc<dyn ExchangeClient>>,
    pub fee_schedule: HashMap<String, FeeSchedule>,
    pub latency_estimates: HashMap<String, Duration>,
}

#[derive(Debug, Clone)]
pub struct FeeSchedule {
    pub maker_fee: f64,
    pub taker_fee: f64,
    pub withdrawal_fee: f64,
}

#[derive(Debug, Clone)]
pub struct VenueAllocation {
    pub exchange: String,
    pub quantity: f64,
    pub expected_price: f64,
    pub expected_fee: f64,
}

impl SmartOrderRouter {
    pub async fn route(
        &self,
        symbol: &str,
        side: Side,
        total_quantity: f64,
    ) -> Result<Vec<VenueAllocation>, ExecutionError> {
        // Collect order books from all venues
        let mut venue_quotes = Vec::new();
        for exchange in &self.exchanges {
            if let Ok(book) = exchange.order_book(symbol, 10).await {
                let name = exchange.name();
                let fees = self.fee_schedule.get(&name).cloned().unwrap_or_default();
                venue_quotes.push((name, book, fees));
            }
        }
        
        // Greedy allocation: fill cheapest venue first
        venue_quotes.sort_by(|a, b| {
            let cost_a = Self::effective_cost(&a.1, &a.2, side, 1.0);
            let cost_b = Self::effective_cost(&b.1, &b.2, side, 1.0);
            cost_a.partial_cmp(&cost_b).unwrap()
        });
        
        let mut remaining = total_quantity;
        let mut allocations = Vec::new();
        
        for (name, book, fees) in &venue_quotes {
            if remaining <= 0.0 { break; }
            
            let available = match side {
                Side::Buy => book.asks.iter().take(5).map(|l| l.quantity).sum::<f64>(),
                Side::Sell => book.bids.iter().take(5).map(|l| l.quantity).sum::<f64>(),
            };
            
            let alloc_qty = remaining.min(available);
            if alloc_qty > 0.0 {
                let price = match side {
                    Side::Buy => book.asks[0].price,
                    Side::Sell => book.bids[0].price,
                };
                allocations.push(VenueAllocation {
                    exchange: name.clone(),
                    quantity: alloc_qty,
                    expected_price: price,
                    expected_fee: price * alloc_qty * fees.taker_fee,
                });
                remaining -= alloc_qty;
            }
        }
        
        Ok(allocations)
    }
    
    fn effective_cost(
        book: &OrderBook,
        fees: &FeeSchedule,
        side: Side,
        qty: f64,
    ) -> f64 {
        let price = match side {
            Side::Buy => book.asks[0].price,
            Side::Sell => book.bids[0].price,
        };
        price * (1.0 + fees.taker_fee)
    }
}
```

---

### 2.11 Participation of Volume (POV)

**Формула:**
```
Target participation rate: ρ (e.g., 10%)

At each interval i:
  observed_volume_i = market volume in interval i
  target_qty_i = ρ × observed_volume_i
  
  if target_qty_i > remaining:
      target_qty_i = remaining
  if target_qty_i < min_order_size:
      skip interval

Fill rate:
  actual_participation = filled_qty_i / observed_volume_i
  adjust ρ if actual_participation deviates from target
```

**Обоснование:** Адаптивный алгоритм: торгует фиксированной долей от наблюдаемого объёма. Автоматически замедляется при thin liquidity и ускоряется при активном рынке.

**Edge cases:**
- **Volume spike:** execution ускоряется → potential over-execution
- **Volume dry-up:** execution замирает → may not finish in time
- **POV rate too high:** dominates market → high impact

**Rust-реализация:**
```rust
/// Participation of Volume (POV) executor
pub struct PovExecutor {
    pub total_quantity: f64,
    pub target_participation: f64,  // e.g., 0.10 = 10%
    pub max_participation: f64,     // Cap at e.g., 25%
    pub min_order_size: f64,
    pub observation_window: Duration,
}

impl PovExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
        side: Side,
        market_volume_stream: &mut dyn VolumeStream,
    ) -> Result<Vec<FillReport>, ExecutionError> {
        let mut remaining = self.total_quantity;
        let mut fills = Vec::new();
        
        while remaining > self.min_order_size {
            let observed_volume = market_volume_stream
                .next_window(self.observation_window)
                .await?;
            
            // Calculate target quantity
            let participation = self.target_participation.min(self.max_participation);
            let target_qty = (participation * observed_volume)
                .min(remaining)
                .max(self.min_order_size);
            
            if target_qty < self.min_order_size {
                continue; // Not enough volume this window
            }
            
            // Execute via IOC limit
            let book = exchange.order_book(symbol, 1).await?;
            let price = match side {
                Side::Buy => book.asks[0].price,
                Side::Sell => book.bids[0].price,
            };
            
            let fill = exchange.place_limit_order(
                symbol, side, target_qty, price, TimeInForce::IOC,
            ).await?;
            
            remaining -= fill.filled_qty;
            fills.push(fill);
        }
        
        Ok(fills)
    }
}
```

**Магические числа:**
| Параметр | Значение | Комментарий |
|---|---|---|
| `target_participation` | 0.10 | 10% от volume |
| `max_participation` | 0.25 | Не более 25% |
| `observation_window` | 1–5 min | Окно наблюдения за объёмом |

---

### 2.12 OCO Orders (One-Cancels-Other)

**Формула:**
```
OCO = { limit_order, stop_loss_order }

Buy OCO:
  take_profit_price = entry × (1 + tp_offset)
  stop_loss_price = entry × (1 - sl_offset)
  
  if price ≥ take_profit_price → fill TP, cancel SL
  if price ≤ stop_loss_price → fill SL, cancel TP

Sell OCO:
  take_profit_price = entry × (1 - tp_offset)  
  stop_loss_price = entry × (1 + sl_offset)
```

**Обоснование:** Комбинированный ордер: TP + SL одновременно. Binance поддерживает native OCO. Необходим для позиционного risk management.

**Rust-реализация:**
```rust
/// OCO (One-Cancels-Other) order executor
pub struct OcoExecutor {
    pub quantity: f64,
    pub side: Side,
    pub take_profit_price: f64,
    pub stop_loss_price: f64,
    pub stop_limit_price: f64,  // Limit price after stop triggers
}

impl OcoExecutor {
    pub async fn execute(
        &self,
        exchange: &dyn ExchangeClient,
        symbol: &str,
    ) -> Result<OcoResult, ExecutionError> {
        // Binance native OCO
        let oco_order = exchange.place_oco_order(
            symbol,
            self.side,
            self.quantity,
            self.take_profit_price,   // limit price (TP)
            self.stop_loss_price,     // stop price (SL trigger)
            self.stop_limit_price,    // stop-limit price
        ).await?;
        
        // Monitor until one leg fills
        loop {
            let status = exchange.oco_status(symbol, &oco_order.order_list_id).await?;
            
            match status {
                OcoStatus::Leg1Filled { price, qty } => {
                    return Ok(OcoResult::TakeProfitFilled { price, qty });
                }
                OcoStatus::Leg2Filled { price, qty } => {
                    return Ok(OcoResult::StopLossFilled { price, qty });
                }
                OcoStatus::BothCancelled => {
                    return Err(ExecutionError::OrderCancelled);
                }
                _ => {
                    tokio::time::sleep(Duration::from_secs(1)).await;
                }
            }
        }
    }
}

#[derive(Debug)]
pub enum OcoResult {
    TakeProfitFilled { price: f64, qty: f64 },
    StopLossFilled { price: f64, qty: f64 },
}
```

---

## 3. Crypto-specific: Комиссии и типы ордеров

### 3.1 Binance Fee Schedule

| Уровень | Maker Fee | Taker Fee | Условие (30d volume) |
|---|---|---|---|
| Regular | 0.02% (0.0002) | 0.04% (0.0004) | Default |
| VIP 1 | 0.018% | 0.036% | ≥ 1M BUSD |
| VIP 2 | 0.016% | 0.032% | ≥ 5M BUSD |
| VIP 3 | 0.014% | 0.028% | ≥ 20M BUSD |

**BNB discount:** 25% скидка при оплате комиссией BNB.

### 3.2 Типы ордеров (Binance)

| Тип | API параметр | Maker/Taker | Гарантия fill | Комментарий |
|---|---|---|---|---|
| Market | `MARKET` | Taker | ✅ Да | Мгновенное исполнение |
| Limit | `LIMIT` | Maker (post-only) | ❌ Нет | По указанной цене или лучше |
| Limit IOC | `LIMIT_IOC` | Taker (if crosses) | Частичная | Fill или cancel |
| Limit FOK | `LIMIT_FOK` | Taker | Полная или ничего | All-or-nothing |
| Stop-Loss | `STOP_LOSS` | Taker | ❌ Нет | Market после trigger |
| Stop-Loss Limit | `STOP_LOSS_LIMIT` | Maker/Taker | ❌ Нет | Limit после trigger |
| Take-Profit | `TAKE_PROFIT` | Taker | ❌ Нет | Market после trigger |
| Take-Profit Limit | `TAKE_PROFIT_LIMIT` | Maker/Taker | ❌ Нет | Limit после trigger |
| OCO | `OCO` | Mixed | Partial | TP + SL комбинация |
| Trailing Stop | `TRAILING_STOP_MARKET` | Taker | ❌ Нет | Динамический stop |

### 3.3 Комиссия: Формула расчёта

```rust
/// Commission calculator for Binance
pub struct CommissionCalculator {
    pub maker_fee: f64,    // 0.0002 (0.02%)
    pub taker_fee: f64,    // 0.0004 (0.04%)
    pub bnb_discount: f64, // 0.75 (25% discount)
    pub use_bnb: bool,
}

impl CommissionCalculator {
    pub fn calculate(&self, side: OrderType, quantity: f64, price: f64) -> f64 {
        let notional = quantity * price;
        let fee_rate = match side {
            OrderType::Market => self.taker_fee,
            OrderType::Limit => self.maker_fee,
            OrderType::LimitIOC => self.taker_fee,
            OrderType::LimitFOK => self.taker_fee,
        };
        
        let discount = if self.use_bnb { self.bnb_discount } else { 1.0 };
        notional * fee_rate * discount
    }
}
```

---

## 4. Рекомендации: MVP vs Production

### 4.1 MVP (v0.1) — Топ-3 алгоритма

| # | Алгоритм | Причина выбора |
|---|---|---|
| **1** | **Market Order + Fixed Slippage** | Простейший: гарантированное исполнение. Для paper backtester — идеален. Slippage = 5 bps + commission = 4 bps taker. |
| **2** | **Limit Order (GTC)** | Базовая альтернатива: maker fee (2 bps vs 4 bps). Post-only = всегда maker. Для стратегий с терпением. |
| **3** | **TWAP (простой)** | Разбиение крупных ордеров на N равных частей по времени. Не требует volume profile. Тривиально реализовать. |

**Почему именно эти три:**
- Market Order = baseline для всех бэктестов
- Limit Order = контроль over cost (maker vs taker)
- TWAP = минимум кода, максимум пользы для крупных ордеров

**Что НЕ включать в MVP:**
- Almgren-Chriss: слишком много параметров, сложная калибровка
- SOR: нет мульти-биржевой инфраструктуры
- Guerrilla/Snack: нет live order flow для маскировки

### 4.2 Production (v1.0) — Топ-3 алгоритма

| # | Алгоритм | Причина выбора |
|---|---|---|
| **1** | **VWAP + Sqrt Slippage** | Institutional-grade. Sqrt model (κ=0.1) для реалистичного impact estimation. VWAP для минимизации проскальзывания. |
| **2** | **Iceberg Orders** | Сокрытие крупных ордеров. chunk=20%. Комбинация с limit price для контроля cost. |
| **3** | **Adaptive POV** | Самый интеллектуальный простой алгоритм: адаптируется к реальному volume. Не пере-impact-ит thin market. |

**Production upgrade path:**
```
MVP: Market + Fixed Slippage
  ↓ replace slippage model
v0.4: Market + Sqrt Slippage
  ↓ add execution algos
v1.0: VWAP + Iceberg + POV
  ↓ add multi-venue
v2.0: SOR + Almgren-Chriss
```

---

## 5. Магические числа и конфигурация

### 5.1 Единый конфиг-файл

```yaml
# execution_config.yaml

slippage:
  model: "sqrt"          # fixed | sqrt | linear
  kappa: 0.1             # sqrt model constant
  fixed_bps: 5.0         # for fixed model
  alpha: 2.0             # for linear model
  max_impact_ratio: 0.1  # Q/V cap

commission:
  maker_fee: 0.0002      # 0.02% Binance regular
  taker_fee: 0.0004      # 0.04% Binance regular
  use_bnb_discount: true
  bnb_discount_rate: 0.75

iceberg:
  chunk_fraction: 0.20   # 20% of total per chunk
  min_chunk_size: 0.0001
  refresh_interval_ms: 2000

twap:
  default_slice_duration_sec: 900  # 15 minutes
  end_strategy: "market_on_close"

vwap:
  participation_tolerance: 0.20    # ±20%
  volume_lookback_days: 20

pov:
  target_participation: 0.10       # 10%
  max_participation: 0.25          # 25% cap
  observation_window_sec: 60

sniper:
  check_interval_ms: 100
  max_wait_sec: 300

guerrilla:
  min_chunk_fraction: 0.05
  max_chunk_fraction: 0.15
  min_interval_ms: 500
  max_interval_ms: 5000
  max_offset_bps: 5.0
```

### 5.2 Сводная таблица магических чисел

| Константа | Значение | Применение |
|---|---|---|
| `κ` (slippage) | 0.1 | Sqrt impact model |
| `maker_fee` | 0.02% | Binance limit order |
| `taker_fee` | 0.04% | Binance market order |
| `iceberg_chunk` | 20% | Iceorder chunk size |
| `POV_target` | 10% | Volume participation |
| `POV_max` | 25% | Volume participation cap |
| `TWAP_slices` | 20–48 | Time slices per session |
| `fixed_slippage` | 5 bps | Backtest default |
| `max_impact_ratio` | 0.10 | Q/V ≤ 10% |
| `sniper_timeout` | 300s | Max wait for target price |
| `guerrilla_min_interval` | 500ms | Min delay between chunks |
| `guerrilla_max_interval` | 5000ms | Max delay between chunks |

---

## 6. Сводная таблица сравнения

| Алгоритм | Сложность | Cost Control | Fill Guarantee | Stealth | MVP | Production |
|---|---|---|---|---|---|---|
| Market Order | ⭐ | ❌ Low | ✅ 100% | ❌ | ✅ | ✅ |
| Limit Order | ⭐ | ✅ High | ❌ None | ❌ | ✅ | ✅ |
| VWAP | ⭐⭐⭐ | ✅ High | ⚠️ Partial | ⚠️ | ❌ | ✅ |
| TWAP | ⭐⭐ | ⚠️ Medium | ⚠️ Partial | ⚠️ | ✅ | ✅ |
| Almgren-Chriss | ⭐⭐⭐⭐⭐ | ✅ Highest | ⚠️ Partial | ⚠️ | ❌ | ⭐⭐⭐ |
| IS / Arrival | ⭐⭐⭐ | ✅ High | ⚠️ Partial | ⚠️ | ❌ | ⭐⭐⭐ |
| Iceberg | ⭐⭐⭐ | ⚠️ Medium | ⚠️ Partial | ✅ High | ❌ | ✅ |
| Sniper | ⭐⭐ | ✅ High | ❌ Conditional | ✅ Medium | ❌ | ⭐⭐ |
| Pegged | ⭐⭐⭐ | ✅ High | ❌ Conditional | ✅ Medium | ❌ | ⭐⭐ |
| Guerrilla | ⭐⭐⭐⭐ | ⚠️ Medium | ⚠️ Partial | ✅ Highest | ❌ | ⭐⭐⭐ |
| Snack | ⭐⭐ | ✅ High | ❌ Conditional | ✅ Medium | ❌ | ⭐⭐ |
| SOR | ⭐⭐⭐⭐ | ✅ Highest | ⚠️ Partial | ❌ | ❌ | ✅ |
| POV | ⭐⭐⭐ | ✅ High | ⚠️ Partial | ✅ Medium | ❌ | ✅ |
| OCO | ⭐⭐ | ✅ High | ⚠️ Conditional | ❌ | ❌ | ✅ |

---

## 7. Единый типаж и архитектура (Rust)

```rust
/// Unified fill report from any execution algorithm
#[derive(Debug, Clone)]
pub struct FillReport {
    pub requested_qty: f64,
    pub filled_qty: f64,
    pub avg_price: f64,
    pub commission: f64,
    pub slippage: f64,       // Fractional slippage from reference
    pub timestamp: i64,
}

/// Execution error types
#[derive(Debug, thiserror::Error)]
pub enum ExecutionError {
    #[error("Order timed out")]
    Timeout,
    #[error("Order cancelled")]
    OrderCancelled,
    #[error("Zero quantity")]
    ZeroQuantity,
    #[error("Insufficient liquidity: need {need}, available {available}")]
    InsufficientLiquidity { need: f64, available: f64 },
    #[error("Exchange error: {0}")]
    ExchangeError(String),
    #[error("Slippage exceeds limit: {actual_bps} bps > {limit_bps} bps")]
    SlippageLimitExceeded { actual_bps: f64, limit_bps: f64 },
}

/// Trait for all execution algorithms
#[async_trait]
pub trait ExecutionAlgorithm: Send + Sync {
    /// Algorithm name for logging
    fn name(&self) -> &str;
    
    /// Execute an order
    async fn execute(
        &self,
        context: &ExecutionContext,
    ) -> Result<Vec<FillReport>, ExecutionError>;
    
    /// Estimate expected cost before execution
    fn estimate_cost(
        &self,
        context: &ExecutionContext,
    ) -> CostEstimate;
}

#[derive(Debug, Clone)]
pub struct ExecutionContext {
    pub symbol: String,
    pub side: Side,
    pub quantity: f64,
    pub reference_price: f64,
    pub daily_volatility: f64,
    pub daily_volume: f64,
}

#[derive(Debug, Clone)]
pub struct CostEstimate {
    pub expected_slippage: f64,
    pub expected_commission: f64,
    pub expected_total_cost: f64,
    pub expected_fill_probability: f64,
    pub expected_duration: Duration,
}
```

---

*Агент 10 — Алгоритмы исполнения*  
*Дата: 17 апреля 2026*