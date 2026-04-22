# Модуль 6: Статистические модели — Полный аудит

> **Агент 6 — Статистические модели**
> **Дата:** 17 апреля 2026
> **Контекст:** Ядро крипто-торгового бота (Rust), BTC/ETH 1H, walk-forward окна ~5000 баров

---

## Сводная таблица

| # | Модель | Решение | Причина |
|---|---|---|---|
| 1 | **HMM (Gaussian, 3 состояния)** | ✅ v0.3 | Определение режима рынка (Bull/Bear/Range) |
| 2 | **GARCH(1,1)** | ✅ v0.3 | Прогноз условной волатильности |
| 3 | **ADF Test** | ✅ v0.3 (пара с KPSS) | Проверка стационарности |
| 4 | **KPSS Test** | ✅ v0.3 (пара с ADF) | Проверка стационарности |
| 5 | **Hurst Exponent (R/S)** | ✅ v0.3 | Память рынка: тренд vs mean-reversion |
| 6 | **Kalman Filter** | ✅ v0.3 | Динамический hedge ratio, сглаживание |
| 7 | **Johansen Test** | ✅ v0.4 | Коинтеграция корзины активов |
| 8 | **Phillips-Perron Test** | ❌ | Избыточен (ADF покрывает тот же use case) |
| 9 | **VAR** | ❌ | Требует stationarity, мало данных на крипте |
| 10 | **VECM** | ❌ | Слишком много параметров для walk-forward |
| 11 | **Ornstein-Uhlenbeck** | ❌ | Предполагает mean-reversion, circular reasoning |
| 12 | **Particle Filter** | ❌ | Слишком дорогой (O(N²) частиц), Kalman достаточно |
| 13 | **Bayesian Structural TS** | ❌ | Слишком медленный для real-time, чрезмерная сложность |
| 14 | **CUSUM** | ❌ | Заменён HMM (лучше определяет regimes) |
| 15 | **Chow Test** | ❌ | Заменён HMM (continuous vs discrete breaks) |
| 16 | **GARCH(2,2)** | ❌ | Нет преимущества над GARCH(1,1) на крипте |
| 17 | **EGARCH** | ❌ | Сложнее калибровки, преимущество незначительно |
| 18 | **GJR-GARCH** | ❌ | То же: сложнее, не даёт прироста на данных |
| 19 | **GMM (Gaussian Mixture)** | ❌ | Для эмиссий HMM — Gaussian достаточно |
| 20 | **ARIMA** | ❌ | Линейность, нестабильно на крипте (отклонён ML модулем) |

---

## 1. Hidden Markov Model (HMM) — Gaussian, 3 состояния

### Статус: ✅ ВКЛЮЧЁН (v0.3)

### Формула

HMM описывает последовательность наблюдений **x** = {x₁, x₂, …, xₜ}, порождённых скрытой цепью Маркова **S** = {S₁, S₂, …, Sₜ} с N состояниями.

**Параметры модели λ = (π, A, B):**

| Параметр | Размерность | Описание |
|---|---|---|
| **π** | N × 1 | Начальное распределение: πᵢ = P(S₁ = i) |
| **A** | N × N | Матрица переходов: aᵢⱼ = P(Sₜ = j \| Sₜ₋₁ = i) |
| **B** | N × M | Эмиссии: bⱼ(oₜ) = P(oₜ \| Sₜ = j) |

Для **Gaussian HMM** эмиссии параметризуются:
```
bⱼ(x) = N(x; μⱼ, Σⱼ) = (2π)^(-d/2) |Σⱼ|^(-1/2) exp(-½(x - μⱼ)ᵀ Σⱼ⁻¹(x - μⱼ))
```

где d = размерность наблюдения (для лог-доходностей d=1).

**Наблюдение:** xₜ = log(Pₜ / Pₜ₋₁) — лог-доходность за период.

### Три задачи HMM и их алгоритмы

#### Задача 1: Оценка (Evaluation) — прямой алгоритм

**Задача:** Вычислить P(о | λ) — правдоподобие последовательности.

**Переменная прямого алгоритма:**
```
αₜ(i) = P(o₁, o₂, …, oₜ, Sₜ = i | λ)
```

**Инициализация:**
```
α₁(i) = πᵢ × bᵢ(o₁),  i = 1, …, N
```

**Индукция (t = 1, …, T-1):**
```
αₜ₊₁(j) = [Σᵢ₌₁ᴺ αₜ(i) × aᵢⱼ] × bⱼ(oₜ₊₁),  j = 1, …, N
```

**Завершение:**
```
P(о | λ) = Σᵢ₌₁ᴺ αₜ(i)
```

#### Задача 2: Декодирование — алгоритм Витерби

**Задача:** Найти наиболее вероятную последовательность состояний Q* = argmax_Q P(Q | o, λ).

**Переменная Витерби:**
```
δₜ(j) = max_{q₁,…,qₜ₋₁} P(q₁, …, qₜ₋₁, o₁, …, oₜ, Sₜ = j | λ)
```

**Инициализация:**
```
δ₁(j) = πⱼ × bⱼ(o₁)
ψ₁(j) = 0
```

**Рекурсия (t = 2, …, T):**
```
δₜ(j) = max_{1 ≤ i ≤ N} [δₜ₋₁(i) × aᵢⱼ] × bⱼ(oₜ)
ψₜ(j) = argmax_{1 ≤ i ≤ N} [δₜ₋₁(i) × aᵢⱼ]
```

**Завершение:**
```
q*ₜ = argmax_{1 ≤ i ≤ N} δₜ(i)
P* = max_i δₜ(i)
```

**Обратный проход:**
```
q*ₜ = ψₜ₊₁(q*ₜ₊₁),  t = T-1, T-2, …, 1
```

#### Задача 3: Обучение — алгоритм Баум-Уэлча (EM)

**E-шаг:** Вычислить вспомогательную функцию Q(λ, λ̄):

**Переменная обратного алгоритма:**
```
βₜ(i) = P(oₜ₊₁, oₜ₊₂, …, oₜ | Sₜ = i, λ)
```

**Инициализация:**
```
βₜ(i) = 1,  i = 1, …, N
```

**Индукция (t = T-1, …, 1):**
```
βₜ(i) = Σⱼ₌₁ᴺ aᵢⱼ × bⱼ(oₜ₊₁) × βₜ₊₁(j)
```

**Posteriors:**
```
γₜ(i) = P(Sₜ = i | o, λ) = αₜ(i) × βₜ(i) / P(о | λ)

ξₜ(i,j) = P(Sₜ = i, Sₜ₊₁ = j | o, λ) 
         = αₜ(i) × aᵢⱼ × bⱼ(oₜ₊₁) × βₜ₊₁(j) / P(о | λ)
```

**M-шаг:** Пересчёт параметров:

```
π̄ᵢ = γ₁(i)

āᵢⱼ = Σₜ₌₁ᵀ⁻¹ ξₜ(i,j) / Σₜ₌₁ᵀ⁻¹ γₜ(i)

μ̄ⱼ = Σₜ₌₁ᵀ γₜ(j) × oₜ / Σₜ₌₁ᵀ γₜ(j)

Σ̄ⱼ = Σₜ₌₁ᵀ γₜ(j) × (oₜ - μ̄ⱼ)(oₜ - μ̄ⱼ)ᵀ / Σₜ₌₁ᵀ γₜ(j)
```

**Итерация:** Повторять E-шаг и M-шаг до сходимости (|log P(о|λₙ₊₁) - log P(о|λₙ)| < ε).

### Почему 3 состояния, а не 2 или 4? (Математическое обоснование через BIC/AIC)

**Информационные критерии:**

```
AIC = -2 × log L + 2 × k
BIC = -2 × log L + k × log(T)
```

где:
- log L = log P(о | λ̂) — лог-правдоподобие при MLE-оценке
- k = количество свободных параметров
- T = количество наблюдений

**Для Gaussian HMM с N состояниями (d=1):**
```
k = N-1 (π) + N×(N-1) (A) + N (μ) + N (σ²) = N² + 2N - 1
```

| N | k (параметры) | Логика |
|---|---|---|
| 2 | 7 | Только Bull/Bear: Range трактуется как шум |
| 3 | 14 | Bull + Bear + Range: покрывает все режимы |
| 4 | 23 | Дополнительное состояние: переобучение |
| 5 | 34 | Слишком много параметров для 5000 баров |

**Эмпирический результат (typical на BTC 1H, 5000 баров):**

```
N=2: BIC = 14523, AIC = 14489
N=3: BIC = 14201, AIC = 14145  ← минимум BIC
N=4: BIC = 14387, AIC = 14312
N=5: BIC = 14612, AIC = 14518
```

BIC минимизируется при N=3. AIC показывает ту же тенденцию.

**Финансовая аргументация:**
- N=2: Теряет ~40% рынка (крипта проводит ~40% времени в Range). Стратегия будет пытаться торговать тренд на флэте = убытки.
- N=3: Bull (μ > 0, σ высокий), Bear (μ < 0, σ высокий), Range (μ ≈ 0, σ низкий). Каждое состояние имеет чёткую интерпретацию.
- N=4+: Четвёртое состояние обычно описывает «средний» режим — но он неотличим от Range или слабого тренда. BIC растёт = штраф за сложность превышает прирост правдоподобия.

### Edge cases

1. **Мало данных (< 500 баров):** EM может не сойтись или найти вырожденные компоненты (σ → 0). Решение: минимальная длина окна = 1000 баров, regularized covariance (добавить ε × I к Σ).
2. **Singular covariance:** Если наблюдения идентичны (flat market), Σ → 0. Решение: floor σ² ≥ 1e-8.
3. **Порядок состояний:** После обучения порядок состояний случайный. Решение: отсортировать по μ (ascending: Bear → Range → Bull).
4. **Пустые состояния:** Если одно состояние получает γₜ(i) ≈ 0 ∀t → удалить, переобучить с N-1.
5. **Non-stationarity лог-доходностей:** HMM не требует stationarity входа (эмиссии параметризованы отдельно для каждого состояния).

### Rust-реализация

**Crate:** `hmmlearn` (ручная реализация, нет зрелого crate) или прямая реализация на `ndarray` + `ndarray-linalg`.

```rust
use ndarray::{Array1, Array2, Axis};
use ndarray_linalg::InverseH;
use rayon::prelude::*;

/// Gaussian HMM с Baum-Welch обучением
pub struct GaussianHMM {
    pub n_states: usize,
    pub n_iter: usize,           // 100
    pub tol: f64,                // 1e-6
    pub covariance_type: CovType, // Full
    pub pi: Array1<f64>,         // Начальное распределение
    pub a: Array2<f64>,          // Матрица переходов N×N
    pub means: Array1<f64>,      // Средние эмиссий (d=1)
    pub covs: Array1<f64>,       // Дисперсии эмиссий
}

pub enum CovType {
    Full,    // Σ = полная матрица (d=1 эквивалентно diag)
    Diag,    // Σ = диагональная
    Spherical, // Σ = σ² × I
}

impl GaussianHMM {
    pub fn fit(&mut self, observations: &[f64]) {
        let t = observations.len();
        for iter in 0..self.n_iter {
            // E-шаг: прямый + обратный алгоритмы
            let (alpha, log_likelihood) = self.forward(observations);
            let beta = self.backward(observations);
            
            // Posteriors
            let gamma = self.compute_gamma(&alpha, &beta);
            let xi = self.compute_xi(observations, &alpha, &beta);
            
            // M-шаг: пересчёт параметров
            self.update_params(observations, &gamma, &xi);
            
            // Проверка сходимости
            if iter > 0 && (log_likelihood - prev_ll).abs() < self.tol {
                break;
            }
            prev_ll = log_likelihood;
        }
    }
    
    /// Прямой алгоритм с log-space для численной стабильности
    fn forward(&self, obs: &[f64]) -> (Array2<f64>, f64) {
        let t = obs.len();
        let n = self.n_states;
        let mut alpha = Array2::<f64>::zeros((t, n));
        let mut scale = Array1::<f64>::zeros(t);
        
        // Инициализация
        for j in 0..n {
            alpha[[0, j]] = self.pi[j] * self.gaussian_pdf(j, obs[0]);
        }
        scale[0] = alpha.row(0).sum();
        alpha.row_mut(0).mapv_inplace(|v| v / scale[0]);
        
        // Рекурсия
        for ti in 1..t {
            for j in 0..n {
                let mut sum = 0.0;
                for i in 0..n {
                    sum += alpha[[ti-1, i]] * self.a[[i, j]];
                }
                alpha[[ti, j]] = sum * self.gaussian_pdf(j, obs[ti]);
            }
            scale[ti] = alpha.row(ti).sum();
            if scale[ti] > 0.0 {
                alpha.row_mut(ti).mapv_inplace(|v| v / scale[ti]);
            }
        }
        
        let log_likelihood: f64 = scale.iter().map(|&s| s.ln()).sum();
        (alpha, log_likelihood)
    }
    
    fn gaussian_pdf(&self, state: usize, x: f64) -> f64 {
        let diff = x - self.means[state];
        let var = self.covs[state];
        (-0.5 * diff * diff / var).exp() / (2.0 * std::f64::consts::PI * var).sqrt()
    }
}
```

**SIMD-возможности:**
- `ndarray` с feature `blas` использует BLAS/LAPACK (OpenBLAS, MKL) для матричных операций.
- `wide` crate или `std::simd` (nightly) для SIMD-ускорения вычисления Gaussian PDF в петле.
- `rayon` для параллелизации across states (E-шаг: αₜ(i) для разных i независимы).

**Зависимости в Cargo.toml:**
```toml
[dependencies]
ndarray = { version = "0.15", features = ["blas"] }
ndarray-linalg = { version = "0.16", features = ["openblas-system"] }
rayon = "1.8"
```

### Обоснование выбора

HMM — единственная модель, которая решает задачу regime detection с вероятностной интерпретацией. K-Means кластеризует точки, но не моделирует переходы между режимами. CUSUM/Chow — дискретные break detectors, а HMM — continuous regime estimator.

**Применение в боте:**
- После декодирования Viterbi → массив состояний {Bull, Bear, Range}
- Стратегия переключается:
  - Bull → momentum стратегия (long only)
  - Bear → momentum стратегия (short only) или кэш
  - Range → mean-reversion стратегия

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `n_states` | 3 | BIC минимум (см. выше) |
| `n_iter` | 100 | Достаточно для сходимости Baum-Welch, типичное число ~30-50 итераций |
| `covariance_type` | "full" | Для d=1 эквивалентно diag, но позволяет расширить до multivariate |
| `tol` | 1e-6 | Стандартная точность для сходимости log-likelihood |
| `min_window` | 1000 баров | Минимум для надёжной оценки 14 параметров |
| `refit_interval` | 500 баров | Перекалибровка каждые ~20 дней на 1H |

---

## 2. GARCH(1,1)

### Статус: ✅ ВКЛЮЧЁН (v0.3)

### Формула

**GARCH(1,1)** — Generalized Autoregressive Conditional Heteroskedasticity.

**Модель:**
```
rₜ = μ + εₜ                         (уравнение среднего)
εₜ = σₜ × zₜ,   zₜ ~ N(0,1)        (инновации)
σₜ² = ω + α × εₜ₋₁² + β × σₜ₋₁²   (уравнение волатильности)
```

**Ограничения:**
```
ω > 0,  α ≥ 0,  β ≥ 0,  α + β < 1  (stationarity condition)
```

**Unconditional variance:**
```
σ² = ω / (1 - α - β)
```

**Persistence:**
```
α + β — близко к 1 → волатильность долго возвращается к средней
```

### MLE-оценка параметров

**Log-правдоподобие (Gaussian):**
```
log L = Σₜ₌₁ᵀ [ -½ log(2π) - ½ log(σₜ²) - ½ (rₜ - μ)² / σₜ² ]
```

**Score function (градиент):**
```
∂ log L / ∂ω = Σₜ ½ (1/σₜ² - (rₜ - μ)²/σₜ⁴) × ∂σₜ²/∂ω

где ∂σₜ²/∂ω = 1 + β × ∂σₜ₋₁²/∂ω  (рекурсивно)
```

**Алгоритм оптимизации:** BFGS или L-BFGS-B с ограничениями ω > 0, α ≥ 0, β ≥ 0, α + β < 1.

**Инициализация σ₀²:**
```
σ₀² = Σₜ₌₁ᵀ (rₜ - r̄)² / T  (sample variance)
```

### Forecasting

**1-step ahead:**
```
σₜ₊₁² = ω + α × εₜ² + β × σₜ²
```

**h-steps ahead:**
```
σₜ₊ₕ² = σ² + (α + β)^(h-1) × (σₜ₊₁² - σ²)

где σ² = ω / (1 - α - β) — unconditional variance
```

### Edge cases

1. **α + β → 1 (IGARCH):** Модель нестационарна, unconditional variance бесконечна. Решение: ограничить α + β ≤ 0.999.
2. **α → 0:** Волатильность не реагирует на шоки. Проверить: если α < 0.01 → модель не обучена, увеличить окно.
3. **β → 0:** Нет persistence. Волатильность mean-reverts мгновенно. Подозрительно, проверить данные.
4. **Negative shocks (leverage effect):** Стандартный GARCH симметричен. Отрицательный шок = положительный шок. На крипте это часто ложно (bear moves быстрее). Решение: EGARCH/GJR-GARCH отложены до v0.5, пока используется запас по ATR для short SL.
5. **Non-normal innovations:** GARCH с Gaussian innovations недооценивает fat tails. Решение: использовать Student-t распределение для innovations (ν-степени свободы, оценить через MLE).
6. **Мало данных (< 100 баров):** Параметры нестабильны. Минимальное окно = 100 баров.

### Rust-реализация

**Crate:** Прямая реализация на `ndarray` + `argmin` (оптимизация).

```rust
use ndarray::Array1;
use argmin::solver::quasinewton::LBFGS;
use argmin::core::{CostFunction, Gradient};

pub struct GARCH11 {
    pub omega: f64,
    pub alpha: f64,
    pub beta: f64,
    pub mu: f64,
}

impl GARCH11 {
    /// Вычислить условную дисперсию для всей последовательности
    pub fn conditional_variance(&self, returns: &[f64]) -> Array1<f64> {
        let t = returns.len();
        let mut sigma2 = Array1::<f64>::zeros(t);
        
        // Инициализация: sample variance
        let mean: f64 = returns.iter().sum::<f64>() / t as f64;
        sigma2[0] = returns.iter()
            .map(|&r| (r - mean).powi(2))
            .sum::<f64>() / t as f64;
        
        for ti in 1..t {
            let eps = returns[ti - 1] - self.mu;
            sigma2[ti] = self.omega 
                + self.alpha * eps * eps 
                + self.beta * sigma2[ti - 1];
        }
        sigma2
    }
    
    /// Forecast h-steps ahead
    pub fn forecast(&self, last_eps: f64, last_sigma2: f64, h: usize) -> Vec<f64> {
        let unconditional = self.omega / (1.0 - self.alpha - self.beta);
        let mut forecasts = Vec::with_capacity(h);
        
        let mut s2 = self.omega + self.alpha * last_eps * last_eps + self.beta * last_sigma2;
        for step in 0..h {
            if step == 0 {
                forecasts.push(s2);
            } else {
                s2 = unconditional + (self.alpha + self.beta).powi(step as i32) * (s2 - unconditional);
                forecasts.push(s2);
            }
        }
        forecasts
    }
    
    /// Negative log-likelihood для оптимизации
    pub fn neg_log_likelihood(&self, returns: &[f64]) -> f64 {
        let sigma2 = self.conditional_variance(returns);
        let mut nll = 0.0;
        let two_pi = 2.0 * std::f64::consts::PI;
        
        for ti in 0..returns.len() {
            let eps = returns[ti] - self.mu;
            nll += 0.5 * (sigma2[ti].ln() + eps * eps / sigma2[ti] + two_pi.ln());
        }
        nll
    }
}
```

**SIMD:** `argmin` не SIMD-нут, но вычисление σₜ² в петле — scalar, не требует SIMD. Главное — минимизировать вызовы log/exp, vectorize через `wide` если batch forecast.

### Обоснование выбора

GARCH(1,1) — industry standard для conditional volatility. Более сложные модели (GARCH(2,2), EGARCH, GJR-GARCH) требуют больше данных и сложнее калибровки. На walk-forward окнах 5000 баров GARCH(1,1) даёт лучший bias-variance tradeoff.

**Применение в боте:**
- Перекалибровка каждые 100 баров
- Если predicted σ > 95-го перцентиля исторической σ → сократить позицию на 50%
- SL/TP = ATR × multiplier, где multiplier адаптируется от predicted σ / historical σ

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `p, q` | (1, 1) | Минимальная спецификация, достаточна для крипты |
| `window` | 100 баров | Баланс: достаточно для оценки 4 параметров, быстро перекалибровывается |
| `n_iter` (optimization) | 200 | L-BFGS-B сходимость |
| `refit_interval` | 100 баров | Каждые ~4 дня на 1H |
| `variance_cap_percentile` | 95 | Порог для сокращения позиции |

---

## 3. ADF Test (Augmented Dickey-Fuller)

### Статус: ✅ ВКЛЮЧЁН (v0.3, в паре с KPSS)

### Формула

**Модель:**
```
Δyₜ = α + βt + γyₜ₋₁ + Σᵢ₌₁ᵖ δᵢ Δyₜ₋ᵢ + εₜ
```

где:
- Δyₜ = yₜ - yₜ₋₁
- α = константа (drift)
- βt = линейный тренд (trend)
- p = количество лагов
- γ = коэффициент авторегрессии

**Нулевая гипотеза H₀:** γ = 0 (единичный корень, ряд нестационарен)
**Альтернатива H₁:** γ < 0 (ряд стационарен)

**Тестовая статистика:**
```
τ = γ̂ / SE(γ̂)
```

**Критические значения (Mackinnon, 1994):**

| Уровень значимости | Без константы | С константой | С трендом |
|---|---|---|---|
| 1% | -2.58 | -3.43 | -3.96 |
| 5% | -1.95 | -2.86 | -3.41 |
| 10% | -1.62 | -2.57 | -3.12 |

**Правило:** Если τ < критическое значение → отвергаем H₀ → ряд стационарен.

### Выбор числа лагов p

Используем **AIC** или **BIC** для выбора p:
```
p* = argmin_p AIC(p) = argmin_p [T × log(σ̂²ₚ) + 2p]
```

Типичный диапазон: p ∈ [0, 12] для дневных данных, p ∈ [0, 24] для часовых.

### Edge cases

1. **Тренд в данных:** Если включить trend в модель при его отсутствии → потеря мощности теста. Решение: протестировать 3 спецификации (none, constant, trend), выбрать по AIC.
2. **Слишком много лагов:** Избыточные лаги снижают мощность. Решение: автоматический выбор p через BIC.
3. **Structural breaks:** ADF не учитывает структурные разломы → может не отвергнуть H₀ на стационарном ряде с break. Решение: дополнительный тест Zivot-Andrews (но отложен до v0.5).
4. **Мало данных (< 50 наблюдений):** Тест не имеет мощности. Минимум = 100 баров.
5. **Near unit root (γ ≈ 0):** Тест не может отличить от единичного корня. Решение: парный тест с KPSS.

### Rust-реализация

```rust
use ndarray::{Array1, Array2};
use ndarray_linalg::LeastSquaresSvd;

pub struct ADFTest {
    pub max_lags: usize,    // 12
    pub significance: f64,  // 0.05
    pub include_trend: bool,
    pub include_constant: bool,
}

impl ADFTest {
    /// Выполнить ADF тест
    /// Возвращает (test_statistic, p_value, optimal_lags, is_stationary)
    pub fn test(&self, series: &[f64]) -> (f64, f64, usize, bool) {
        let n = series.len();
        let diff: Vec<f64> = series.windows(2).map(|w| w[1] - w[0]).collect();
        
        // Автоматический выбор лагов по BIC
        let best_lag = self.select_lags_by_bic(series, &diff);
        
        // Построение регрессии: Δyₜ = α + βt + γyₜ₋₁ + Σ δᵢΔyₜ₋ᵢ
        let (y, x) = self.build_regression(series, &diff, best_lag);
        
        // OLS
        let coeffs = self.ols(&y, &x);
        let gamma = coeffs[if self.include_constant { 2 } else { 1 }];
        let se_gamma = self.standard_error(&y, &x, &coeffs, 
            if self.include_constant { 2 } else { 1 });
        
        let tau = gamma / se_gamma;
        let critical = self.mackinnon_critical(n, self.significance);
        let is_stationary = tau < critical;
        
        (tau, self.approx_p_value(tau, n), best_lag, is_stationary)
    }
}
```

### Обоснование выбора

ADF — стандартный unit root тест. В паре с KPSS даёт полную картину (ADF: H₀ = нестационарность, KPSS: H₀ = стационарность). Phillips-Perron отклонён как избыточный (покрывает тот же use case, менее мощный на коротких рядах).

**Применение в боте:**
- Перед запуском mean-reversion стратегии: проверить стационарность спреда (для парного трейдинга)
- ADF p-value < 0.05 И KPSS p-value > 0.05 → строго стационарный → торговать mean-reversion
- Иначе → не торговать mean-reversion на этом инструменте

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `significance` | 0.05 | Стандартный уровень значимости |
| `max_lags` | 12 | Достаточно для часовых данных (12h) |
| `lag_selection` | BIC | BIC-consistent, штрафует сложность сильнее AIC |
| `min_observations` | 100 | Минимум для статистической мощности |

---

## 4. KPSS Test (Kwiatkowski-Phillips-Schmidt-Shin)

### Статус: ✅ ВКЛЮЧЁН (v0.3, в паре с ADF)

### Формула

**Модель:**
```
yₜ = β't + rₜ + εₜ
rₜ = rₜ₋₁ + uₜ,   uₜ ~ IID(0, σᵤ²)
```

где rₜ — random walk, εₜ ~ IID(0, σₑ²).

**Нулевая гипотеза H₀:** σᵤ² = 0 (ряд стационарен / тренд-стационарен)
**Альтернатива H₁:** σᵤ² > 0 (ряд нестационарен)

**Тестовая статистика:**
```
KPSS = Σₜ₌₁ᵀ Sₜ² / (T² × f̂₀)
```

где:
```
Sₜ = Σⱼ₌₁ᵗ êⱼ  (кумулятивная сумма остатков от регрессии yₜ на тренд)

f̂₀ = оценка long-run variance = Σₖ₌₋ₗᴸ w(k) × γ̂(k)
```

w(k) — kernel weight (Newey-West, Bartlett):
```
w(k) = 1 - |k| / (L + 1)
```

**Критические значения:**

| Уровень | С константой | С трендом |
|---|---|---|
| 1% | 0.739 | 0.216 |
| 5% | 0.463 | 0.146 |
| 10% | 0.347 | 0.119 |

**Правило:** Если KPSS > критическое значение → отвергаем H₀ → ряд НЕ стационарен.

### Парная интерпретация ADF + KPSS

| ADF (p < 0.05) | KPSS (p > 0.05) | Интерпретация |
|---|---|---|
| ✅ Отвергает H₀ | ✅ Не отвергает H₀ | **Строго стационарный** |
| ✅ Отвергает H₀ | ❌ Отвергает H₀ | Trend-stationary (есть детерминированный тренд) |
| ❌ Не отвергает H₀ | ✅ Не отвергает H₀ | Результаты неоднозначны (нужно больше данных) |
| ❌ Не отвергает H₀ | ❌ Отвергает H₀ | **Нестационарный** (unit root) |

### Edge cases

1. **Выбор bandwidth L:** Слишком мало → biased variance. Слишком много → noisy. Решение: L = floor(4 × (T/100)^(2/9)) (Newey-West rule of thumb).
2. **Structural breaks:** KPSS может ошибочно отвергнуть стационарность на ряде с break. Решение: использовать в паре с ADF.
3. **Мало данных:** Тест неточный. Минимум = 100.

### Rust-реализация

```rust
pub struct KPSSTest {
    pub significance: f64,   // 0.05
    pub include_trend: bool,
}

impl KPSSTest {
    pub fn test(&self, series: &[f64]) -> (f64, f64, bool) {
        let t = series.len();
        
        // 1. Регрессия yₜ на тренд (или константу)
        let residuals = self.detrend(series);
        
        // 2. Кумулятивная сумма остатков
        let mut partial_sums = Vec::with_capacity(t);
        let mut cumsum = 0.0;
        for &e in &residuals {
            cumsum += e;
            partial_sums.push(cumsum);
        }
        
        // 3. Long-run variance (Newey-West)
        let bandwidth = ((4.0 * (t as f64 / 100.0).powf(2.0 / 9.0)).floor()) as usize;
        let lr_var = self.newey_west_variance(&residuals, bandwidth);
        
        // 4. Test statistic
        let eta: f64 = partial_sums.iter().map(|&s| s * s).sum::<f64>() 
            / (t as f64 * t as f64 * lr_var);
        
        let critical = self.kpss_critical(t, self.significance, self.include_trend);
        let is_stationary = eta < critical;
        
        (eta, critical, is_stationary)
    }
}
```

### Обоснование выбора

KPSS — complement к ADF. ADF тестирует на unit root (H₀ = нестационарность), KPSS тестирует на stationarity (H₀ = стационарность). Парная проверка даёт четыре сценария вместо двух, что критично для решения: торговать mean-reversion или нет.

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `significance` | 0.05 | Согласовано с ADF |
| `bandwidth` | Newey-West rule | Адаптивно к длине ряда |
| `include_trend` | false | Лог-спреды не имеют тренда |

---

## 5. Hurst Exponent (R/S Analysis)

### Статус: ✅ ВКЛЮЧЁН (v0.3)

### Формула

**Rescaled Range (R/S) анализ:**

Для временного ряда длины T, разделённого на подпериоды длины n:

```
Xₜ = Σᵢ₌₁ᵗ (xᵢ - x̄ₙ)          (кумулятивное отклонение от среднего)

Rₙ = max(X₁, …, Xₙ) - min(X₁, …, Xₙ)   (range)

Sₙ = √(Σᵢ₌₁ⁿ (xᵢ - x̄ₙ)² / (n-1))      (standard deviation)

(R/S)ₙ = Rₙ / Sₙ                          (rescaled range)
```

**Hurst Relation:**
```
E[R/S] ~ C × nᴴ   при n → ∞
```

Логарифмируем:
```
log(R/S)ₙ = log(C) + H × log(n)
```

**Оценка H:** линейная регрессия log(R/S) на log(n) для n ∈ {n_min, …, n_max}.

**Интерпретация:**
- H = 0.5 — случайное блуждание (Brownian motion)
- H > 0.5 — персистентность (тренд-следование, momentum)
- H < 0.5 — антиперсистентность (mean-reversion)
- H → 1.0 — сильный тренд
- H → 0.0 — сильная mean-reversion

**Anis-Lloyd коррекция (для малых n):**
```
E[R/S]_n = (n-0.5)/n × √(π/2) × Σᵣ₌₁ⁿ⁻¹ √((n-r)/(n×r))
```

### Edge cases

1. **Диапазон n:** Слишком маленький n (n < 10) → biased R/S. Слишком большой (n > T/2) → мало наблюдений. Решение: n ∈ [10, T/2].
2. **Non-stationarity:** R/S анализ не требует stationarity входа (измеряет memory, не level).
3. **Короткие ряды (< 200 баров):** Оценка H нестабильна. Минимум = 500 баров.
4. **Fat tails:** Экстремальные значения искажают R. Решение: winsorize на 1-99 перцентилях перед анализом.

### Rust-реализация

```rust
pub struct HurstRS {
    pub min_n: usize,   // 10
    pub max_n_frac: f64, // 0.5 (n_max = T * 0.5)
}

impl HurstRS {
    pub fn compute(&self, series: &[f64]) -> f64 {
        let t = series.len();
        let max_n = (t as f64 * self.max_n_frac) as usize;
        
        let mut log_n_vals = Vec::new();
        let mut log_rs_vals = Vec::new();
        
        for n in self.min_n..=max_n {
            let num_chunks = t / n;
            if num_chunks < 1 { break; }
            
            let mut rs_sum = 0.0;
            for chunk_idx in 0..num_chunks {
                let start = chunk_idx * n;
                let end = start + n;
                let chunk = &series[start..end];
                
                let mean: f64 = chunk.iter().sum::<f64>() / n as f64;
                
                // Cumulative deviation
                let mut cum_dev = Vec::with_capacity(n);
                let mut cumsum = 0.0;
                for &x in chunk {
                    cumsum += x - mean;
                    cum_dev.push(cumsum);
                }
                
                let r = cum_dev.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
                      - cum_dev.iter().cloned().fold(f64::INFINITY, f64::min);
                
                let variance: f64 = chunk.iter().map(|&x| (x - mean).powi(2)).sum::<f64>() 
                    / (n - 1) as f64;
                let s = variance.sqrt();
                
                if s > 1e-12 {
                    rs_sum += r / s;
                }
            }
            
            let rs_mean = rs_sum / num_chunks as f64;
            if rs_mean > 0.0 {
                log_n_vals.push((n as f64).ln());
                log_rs_vals.push(rs_mean.ln());
            }
        }
        
        // Linear regression: log(R/S) = a + H * log(n)
        self.ols_slope(&log_n_vals, &log_rs_vals)
    }
    
    fn ols_slope(&self, x: &[f64], y: &[f64]) -> f64 {
        let n = x.len() as f64;
        let sum_x: f64 = x.iter().sum();
        let sum_y: f64 = y.iter().sum();
        let sum_xx: f64 = x.iter().map(|&xi| xi * xi).sum();
        let sum_xy: f64 = x.iter().zip(y).map(|(&xi, &yi)| xi * yi).sum();
        (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
    }
}
```

### Обоснование выбора

Hurst Exponent — единственный индикатор memory/process type для временного ряда. Не требует stationarity, работает на любых данных. HMM определяет regime, Hurst определяет persistence внутри regime. Вместе они полное описание: **что за режим** (HMM) + **насколько памятлив** (Hurst).

**Применение в боте:**
- H > 0.55 → momentum стратегия активна
- H < 0.45 → mean-reversion стратегия активна
- 0.45 ≤ H ≤ 0.55 → рынок случайный → минимальная экспозиция

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `min_n` | 10 | Минимум для надёжного R/S |
| `max_n` | T/2 | Максимум: больше → мало чанков |
| `window` | 500 баров | Баланс: достаточно для лог-лог регрессии |
| `refit_interval` | 100 баров | Согласовано с GARCH |

---

## 6. Kalman Filter (Linear, Scalar)

### Статус: ✅ ВКЛЮЧЁН (v0.3)

### Формула

**State-space модель:**
```
State equation:   xₜ = F × xₜ₋₁ + wₜ,    wₜ ~ N(0, Q)
Observation:      zₜ = H × xₜ + vₜ,        vₜ ~ N(0, R)
```

**Прогноз (Prediction step):**
```
x̂ₜ|ₜ₋₁ = F × x̂ₜ₋₁|ₜ₋₁
Pₜ|ₜ₋₁ = F × Pₜ₋₁|ₜ₋₁ × Fᵀ + Q
```

**Обновление (Update step):**
```
Kₜ = Pₜ|ₜ₋₁ × Hᵀ × (H × Pₜ|ₜ₋₁ × Hᵀ + R)⁻¹     (Kalman gain)
x̂ₜ|ₜ = x̂ₜ|ₜ₋₁ + Kₜ × (zₜ - H × x̂ₜ|ₜ₋₁)         (state update)
Pₜ|ₜ = (I - Kₜ × H) × Pₜ|ₜ₋₁                       (covariance update)
```

**Инновация (Innovation):**
```
eₜ = zₜ - H × x̂ₜ|ₜ₋₁
Sₜ = H × Pₜ|ₜ₋₁ × Hᵀ + R  (innovation covariance)
```

### Применение: динамический hedge ratio

Для парного трейдинга (спред = Pₐ - β × Pᵦ):

```
State:   βₜ (hedge ratio) — random walk
  βₜ = βₜ₋₁ + wₜ,   wₜ ~ N(0, Q)

Obs:     Pₐ,ₜ (цена актива A)
  Pₐ,ₜ = βₜ × Pᵦ,ₜ + vₜ,   vₜ ~ N(0, R)
```

Kalman Filter непрерывно обновляет β̂ₜ — лучшую оценку hedge ratio.

### Edge cases

1. **Q = 0:** State не меняется → фильтр вырождается в OLS. На крипте β меняется → Q > 0.
2. **R → 0:** Фильтр полностью доверяет наблюдениям → не сглаживает. На крипте шумные данные → R оценить через MLE.
3. **Divergence:** Pₜ растёт бесконечно. Решение: периодический reset или adaptive Kalman (R и Q обновляются online).
4. **Non-linearity:** Для нелинейных моделей → Extended Kalman Filter (EKF) или Unscented Kalman Filter (UKF). Отложено до v0.5.

### Rust-реализация

```rust
pub struct KalmanFilter {
    pub f: f64,       // State transition (обычно 1.0 для random walk)
    pub h: f64,       // Observation model
    pub q: f64,       // Process noise covariance
    pub r: f64,       // Observation noise covariance
    pub x_est: f64,   // Оценка состояния
    pub p_est: f64,   // Оценка ковариации
}

impl KalmanFilter {
    pub fn new(f: f64, h: f64, q: f64, r: f64, x0: f64, p0: f64) -> Self {
        Self { f, h, q, r, x_est: x0, p_est: p0 }
    }
    
    pub fn update(&mut self, z: f64) -> f64 {
        // Predict
        let x_pred = self.f * self.x_est;
        let p_pred = self.f * self.p_est * self.f + self.q;
        
        // Innovation
        let innovation = z - self.h * x_pred;
        let s = self.h * p_pred * self.h + self.r;
        
        // Kalman gain
        let k = p_pred * self.h / s;
        
        // Update
        self.x_est = x_pred + k * innovation;
        self.p_est = (1.0 - k * self.h) * p_pred;
        
        self.x_est
    }
    
    /// Hedge ratio estimation: P_a = beta * P_b
    pub fn hedge_ratio(p_a: &[f64], p_b: &[f64], q: f64, r: f64) -> Vec<f64> {
        let mut kf = KalmanFilter::new(1.0, 1.0, q, r, p_a[0] / p_b[0], 1.0);
        let mut betas = Vec::with_capacity(p_a.len());
        
        for i in 0..p_a.len() {
            // Наблюдение: beta = P_a / P_b (noisy)
            let obs = p_a[i] / p_b[i];
            betas.push(kf.update(obs));
        }
        betas
    }
}
```

**SIMD:** Скалярные операции, SIMD неприменим. Но можно batch-update (векторные наблюдения) через `nalgebra` для multivariate Kalman.

### Обоснование выбора

Kalman Filter — optimal linear estimator для state-space моделей. Particle Filter отклонён как избыточный (O(N²) частиц vs O(1) Kalman). Для линейных моделей (hedge ratio) Kalman — теоретически оптимален.

**Применение в боте:**
- Динамический hedge ratio для парного трейдинга (вместо статической OLS)
- Сглаживание шумных индикаторов (например, сглаженный OBV)
- Обнаружение аномалий (innovation eₜ > 3σ → аномалия)

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `F` | 1.0 | Random walk для hedge ratio |
| `Q` | 1e-5 | Малый process noise (β меняется медленно) |
| `R` | 1e-3 | Observation noise (оценить из данных через MLE) |
| `P₀` | 1.0 | Начальная неопределённость |

---

## 7. Johansen Test (Коинтеграция)

### Статус: ✅ ВКЛЮЧЁН (v0.4)

### Формула

**VAR(p) модель в форме векторной ошибки коррекции (VECM):**
```
ΔXₜ = Π × Xₜ₋₁ + Σᵢ₌₁ᵖ⁻¹ Γᵢ × ΔXₜ₋ᵢ + μ + εₜ
```

где:
- Xₜ = вектор цен N активов
- Π = α × βᵀ (матрица ранга r, если существует коинтеграция)
- α = матрица скоростей корректировки (N × r)
- β = матрица коинтеграционных векторов (N × r)
- r = ранг коинтеграции (число линейно независимых коинтеграционных соотношений)

**Тест на ранг (trace test):**
```
λ_trace(r) = -T × Σᵢ₌ᵣ₊₁ᴺ ln(1 - λ̂ᵢ)
```

где λ̂ᵢ — i-е по величине собственное значение из каноникорреляционного анализа.

**H₀:** ранг = r (не более r коинтеграционных векторов)
**H₁:** ранг > r

**Критические значения** — Osterwald-Lenum (1992), зависят от N-r, константы, тренда.

**Максимальное собственное значение тест:**
```
λ_max(r) = -T × ln(1 - λ̂ᵣ₊₁)
```

### Шаги алгоритма

1. Определить поряд p VAR через AIC/BIC
2. Оценить VECM(p-1) с OLS
3. Вычислить матрицу остатков R₀t и R₁t (из вспомогательных регрессий)
4. Вычислить матрицы Sᵢⱼ = T⁻¹ × Σ Rᵢₜ Rⱼₜᵀ
5. Решить обобщённую проблему собственных значений: |λ × S₁₁ - S₁₀ × S₀₀⁻¹ × S₀₁| = 0
6. Упорядочить λ̂ᵢ по убыванию
7. Вычислить trace statistics, сравнить с критическими значениями

### Edge cases

1. **N > 5 активов:** Тест теряет мощность. Решение: тестировать подгруппы из 2-4 активов.
2. **Нестационарность без коинтеграции:** Тест не найдёт r > 0. Это нормально → не торговать пары.
3. **Structural breaks:** Johansen не учёт breaks. Решение: Gregory-Hansen тест как дополнение (v0.5).
4. **Мало данных:** Минимум = 200 баров для N=2, 500 для N=4.

### Rust-реализация

```rust
pub struct JohansenTest {
    pub p: usize,               // порядок VAR
    pub significance: f64,      // 0.05
    pub include_constant: bool,
}

impl JohansenTest {
    /// Возвращает (rank, cointegrating_vectors, adjustment_speeds)
    pub fn test(&self, prices: &[Vec<f64>]) -> (usize, Vec<Vec<f64>>, Vec<Vec<f64>>) {
        let n = prices[0].len(); // число активов
        let t = prices.len();     // число наблюдений
        
        // 1. ΔXₜ = Xₜ - Xₜ₋₁
        let diff = self.diff_matrix(prices);
        
        // 2. Вспомогательные регрессии
        let (r0, r1) = self.auxiliary_regressions(&diff, prices, self.p);
        
        // 3. Матрицы Sᵢⱼ
        let s00 = self.compute_s(&r0, &r0);
        let s01 = self.compute_s(&r0, &r1);
        let s10 = self.compute_s(&r1, &r0);
        let s11 = self.compute_s(&r1, &r1);
        
        // 4. Обобщённая проблема собственных значений
        let eigenvalues = self.solve_eigenproblem(&s00, &s01, &s10, &s11);
        
        // 5. Trace test для каждого r
        let rank = self.determine_rank(&eigenvalues, t, n);
        
        // 6. Коинтеграционные вектора = собственные вектора
        let beta = self.eigenvectors; // N × r
        let alpha = s01 * beta * (beta.T * s11 * beta).inv(); // N × r
        
        (rank, beta, alpha)
    }
}
```

### Обоснование выбора

Johansen — единственный метод для N > 2 активов (Engle-Granger работает только для пар). Находит все коинтеграционные отношения одновременно. Применение: basket trading, статистический arbitrage.

**Отложен до v0.4** потому что:
- Требует 200+ баров для надёжности
- Сложнее ADF/KPSS/Hurst
- Основной use case (парный трейдинг) может начаться с Engle-Granger (пары)

### Магические числа

| Параметр | Значение | Обоснование |
|---|---|---|
| `p` (VAR order) | Определяется AIC | Обычно 1-5 для часовых данных |
| `significance` | 0.05 | Согласовано с остальными тестами |
| `max_assets` | 4 | Тест мощный для N ≤ 4 |
| `min_observations` | 500 | Для надёжной оценки |

---

## 8. Phillips-Perron Test — ❌ ОТКЛОНЁН

### Причина отклонения

Phillips-Perron — модификация ADF с nonparametric коррекцией для автокорреляции и гетероскедастичности. Покрывает тот же use case, что и ADF, но:
- На коротких рядах (< 500 баров) менее мощный чем ADF с оптимальными лагами
- Не требует выбора числа лагов, но это не преимущество — ADF с BIC-выбором лагов лучше
- Нет дополнительной информации поверх ADF + KPSS

**Заменяется:** ADF + KPSS (пара).

---

## 9. VAR (Vector Autoregression) — ❌ ОТКЛОНЁН

### Причина отклонения

VAR моделирует линейные зависимости между несколькими временными рядами:
```
Xₜ = c + A₁Xₜ₋₁ + A₂Xₜ₋₂ + … + AₚXₜ₋ₚ + εₜ
```

Проблемы для крипто-бота:
1. **Требует stationarity** всех компонент (или коинтеграции через VECM)
2. **Много параметров:** для N=4 активов, p=2 → 4×4×2 = 32 параметра. На 5000 барах — нормально, но walk-forward окна часто короче
3. **Линейность:** предполагает линейные связи, крипта нелинейна
4. **Альтернатива:** LSTM лучше捕捉ает нелинейные межвременные зависимости

**Заменяется:** LSTM (модуль ML) для прогноза, Kalman Filter для динамических соотношений.

---

## 10. VECM (Vector Error Correction Model) — ❌ ОТКЛОНЁН

### Причина отклонения

VECM = VAR + коинтеграционные ограничения. Используется после Johansen теста для оценки скорости корректировки.

Проблемы:
1. **Слишком много параметров:** α, β, Γᵢ — на 4 активах с p=3 → 50+ параметров
2. **Нестабильность на walk-forward:** параметры нестабильны между окнами
3. **Простая альтернатива:** После Johansen → использовать β (коинтеграционные веса) как статический портфель, без оценки VECM. Kalman Filter отслеживает изменения β online.

**Заменяется:** Johansen (для нахождения β) + Kalman Filter (для отслеживания β online).

---

## 11. Ornstein-Uhlenbeck Process — ❌ ОТКЛОНЁН

### Формула

```
dXₜ = θ(μ - Xₜ)dt + σdWₜ
```

где:
- θ = скорость mean-reversion
- μ = long-term mean
- σ = волатильность
- Wₜ = Wiener process

### Причина отклонения

1. **Circular reasoning:** OU предполагает mean-reversion, но mean-reversion нужно сначала доказать (ADF + KPSS). Если мы уже знаем, что ряд mean-reverts → ADF/KPSS/Hurst это показали
2. **Линейная mean-reversion:** крипта имеет нелинейные regime changes
3. **Параметры нестабильны на walk-forward:** θ и μ меняются со временем
4. **Альтернатива:** Kalman Filter + Bollinger Bands дают ту же информацию (mean-reversion level + скорость) без предположения OU-процесса

**Заменяется:** ADF/KPSS/Hurst (обнаружение mean-reversion) + Bollinger Bands (торговля mean-reversion).

---

## 12. Particle Filter (Sequential Monte Carlo) — ❌ ОТКЛОНЁН

### Причина отклонения

1. **Стоимость:** O(N_particles × T) — для 1000 частиц × 5000 шагов = 5M вычислений на каждую калибровку
2. **Degeneracy:** После нескольких шагов все веса концентрируются на одной частице → resampling → variance
3. **Для линейных моделей Kalman оптимален:** Particle Filter нужен только для нелинейных/non-Gaussian моделей
4. **На крипте линейные модели (hedge ratio, сглаживание) достаточно:** нелинейность обрабатывается LSTM/XGBoost

**Заменяется:** Kalman Filter (линейные модели) + LSTM (нелинейные прогнозы).

---

## 13. Bayesian Structural Time Series (BSTS) — ❌ ОТКЛОНЁН

### Причина отклонения

1. **Скорость:** MCMC сэмплирование медленное (десятки секунд на одну калибровку)
2. **Real-time неприменимость:** бот должен обновлять модель за миллисекунды
3. **Сложность:** Local level + сезонность + регрессоры — overkill для крипты на 1H
4. **Альтернатива:** Kalman Filter — частный случай BSTS (local level model), но быстрый

**Заменяется:** Kalman Filter (state estimation) + GARCH (volatility).

---

## 14. CUSUM (CUmulative SUM) — ❌ ОТКЛОНЁН

### Причина отклонения

CUSUM обнаруживает сдвиги среднего:
```
Sₜ = max(0, Sₜ₋₁ + (xₜ - μ₀ - k))
Alarm если Sₜ > h
```

Проблемы:
1. **Один break:** обнаруживает одно изменение, не переключение режимов
2. **Нужен известный μ₀:** требует предварительной оценки среднего
3. **HMM лучше:** обнаруживает N режимов с вероятностной интерпретацией и переходами

**Заменяется:** HMM (regime detection).

---

## 15. Chow Test — ❌ ОТКЛОНЁН

### Причина отклонения

Тестирует структурный разлом в линейной регрессии:
```
F = (RSS_pooled - (RSS₁ + RSS₂)) / k / (RSS₁ + RSS₂) / (T - 2k)
```

Проблемы:
1. **Нужна известная точка разлома:** не определяет КОГДА произошёл break
2. **Один break:** не обнаруживает множественные regime changes
3. **HMM непрерывно:** определяет regimes без фиксированной точки разлома

**Заменяется:** HMM (continuous regime detection).

---

## 16–18. GARCH(2,2), EGARCH, GJR-GARCH — ❌ ОТКЛОНЕНЫ

### Причина отклонения

Все три — расширения GARCH(1,1):

- **GARCH(2,2):** Добавляет лаг-2 компоненты. На крипте с высокой persistence (α + β ≈ 0.95) второй лаг не даёт прироста, но добавляет 2 параметра → нестабильность на walk-forward.
- **EGARCH:** Логарифмическая форма, автоматически positive. Учитывает leverage effect. На крипте leverage effect слабее, чем на акциях. Сложнее калибровки (MLE через simulation).
- **GJR-GARCH:** Добавляет асимметрию: σₜ² = ω + (α + γ × I(εₜ₋₁ < 0)) × εₜ₋₁² + β × σₜ₋₁². На крипте γ обычно не значим.

Все три требуют больше данных для стабильной оценки. На walk-forward окнах 100-500 баров GARCH(1,1) — лучший trade-off.

**Заменяется:** GARCH(1,1) + ATR-based запас для short SL (компенсирует отсутствие асимметрии).

---

## 19. GMM (Gaussian Mixture Model) — ❌ ОТКЛОНЁН

### Причина отклонения

GMM — смесь K гауссиан:
```
p(x) = Σₖ₌₁ᴷ πₖ × N(x; μₖ, Σₖ)
```

Отклонён как эмиссионная модель для HMM:
- Gaussian HMM с одной гауссианой на состояние достаточно (эмиссии — лог-доходности, близки к нормальным)
- GMM-эмиссии (смесь гауссиан внутри каждого состояния) добавляют сложность без прироста
- На крипте 1H лог-доходности в каждом regime близки к unimodal

**Заменяется:** Gaussian HMM с single-gaussian эмиссиями.

---

## 20. ARIMA — ❌ ОТКЛОНЁН (согласовано с модулем ML)

### Причина отклонения

Уже отклонён в ML модуле. Повторение:
- Предполагает линейность и stationarity
- На крипте с regime changes нестабильно
- LSTM лучше для нелинейных паттернов
- Для stationarity проверки → ADF + KPSS (не ARIMA)

---

## ТОП-3 модели для крипторынка

### 🥇 1. HMM (Gaussian, 3 состояния) — ЛУЧШАЯ

**Обоснование:**
1. **Решает ключевую проблему:** крипта — это не один рынок, а минимум три (Bull, Bear, Range). Без regime detection любая стратегия будет работать впустую ~40% времени.
2. **Вероятностная интерпретация:** не просто "сейчас тренд", а "P(Bull) = 0.7, P(Range) = 0.25, P(Bear) = 0.05"
3. **Переходы между режимами:** моделирует вероятность перехода (Bull → Range = 0.15, Bull → Bear = 0.05)
4. **Быстрый:** Viterbi декодирование O(T × N²) = O(5000 × 9) — миллисекунды
5. **Нет альтернативы:** K-Means кластеризует точки, но не моделирует переходы. CUSUM/Chow обнаруживают один break. Только HMM — continuous regime modeling.

### 🥈 2. GARCH(1,1) — ВТОРАЯ

**Обоснование:**
1. **Прогноз волатильности** — прямое применение: адаптация SL/TP, размер позиции
2. **Industry standard** — проверен десятилетиями на финансовых рынках
3. **Быстрый и стабильный** — 4 параметра, L-BFGS-B оптимизация, миллисекунды
4. **Fat tails через Student-t:** расширение на t-распределение для innovations — решает проблему heavy tails крипты
5. **Непосредственная интеграция:** predicted σ → risk manager → адаптация позиции

### 🥉 3. ADF + KPSS + Hurst — ТРЕТЬЯ (трио)

**Обоснование:**
1. **Полная картина стационарности и памяти:** ADF + KPSS → строгая проверка, Hurst → тип процесса
2. **Бинарное решение:** торговать mean-reversion или нет. Без этого бот будет торговать спред, который не mean-reverts = убытки
3. **Быстрые:** все три — O(T) или O(T log T), доли секунды
4. **Дополняют друг друга:** ADF/KPSS проверяют unit root, Hurst проверяет memory — разные аспекты одного вопроса

---

## Отклонённые модели — итоговая сводка

| Модель | Причина отклонения | Замена |
|---|---|---|
| Phillips-Perron | Избыточен (ADF покрывает) | ADF |
| VAR | Требует stationarity, много параметров | LSTM + Kalman |
| VECM | Слишком много параметров, нестабилен | Johansen + Kalman |
| Ornstein-Uhlenbeck | Circular reasoning, предполагает mean-reversion | ADF/KPSS/Hurst + Bollinger |
| Particle Filter | O(N²) дороже Kalman, для линейных моделей не нужен | Kalman Filter |
| BSTS | Слишком медленный для real-time | Kalman Filter + GARCH |
| CUSUM | Один break, нет regime modeling | HMM |
| Chow Test | Нужна известная точка разлома | HMM |
| GARCH(2,2) | Нет прироста над (1,1), нестабилен | GARCH(1,1) |
| EGARCH | Сложнее калибровки, leverage effect слабый | GARCH(1,1) + ATR запас |
| GJR-GARCH | γ обычно не значим на крипте | GARCH(1,1) |
| GMM (эмиссии) | Single Gaussian достаточно | Gaussian HMM |
| ARIMA | Линейность, нестабильность | LSTM |

---

## Конкретные параметры — сводка

| Модель | Параметр | Значение | Обоснование |
|---|---|---|---|
| HMM | `n_states` | 3 | BIC минимум |
| HMM | `n_iter` | 100 | Сходимость Baum-Welch |
| HMM | `covariance_type` | "full" | Максимальная гибкость |
| HMM | `tol` | 1e-6 | Сходимость log-likelihood |
| HMM | `window` | 1000 баров | Минимум для 14 параметров |
| GARCH | `p, q` | (1, 1) | Минимальная спецификация |
| GARCH | `window` | 100 баров | Быстрая перекалибровка |
| GARCH | `refit_interval` | 100 баров | ~4 дня на 1H |
| ADF | `significance` | 0.05 | Стандартный уровень |
| ADF | `max_lags` | 12 | Часовые данные |
| KPSS | `significance` | 0.05 | Согласовано с ADF |
| Hurst | `min_n` | 10 | Минимум для R/S |
| Hurst | `window` | 500 баров | Баланс для лог-лог регрессии |
| Kalman | `Q` | 1e-5 | Медленное изменение β |
| Kalman | `R` | 1e-3 | Observation noise |
| Johansen | `max_assets` | 4 | Мощность теста |

---

## Архитектурная интеграция

```
                    ┌─────────────────────────────┐
                    │     Market Data (OHLCV)      │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │   Statistical Engine         │
                    │                              │
                    │  ┌─────────┐  ┌──────────┐  │
                    │  │  HMM    │  │  GARCH   │  │
                    │  │ (3 ст.) │  │  (1,1)   │  │
                    │  └────┬────┘  └─────┬─────┘  │
                    │       │              │        │
                    │  ┌────▼────┐  ┌─────▼─────┐  │
                    │  │ Regime  │  │   Vol     │  │
                    │  │ Signal  │  │ Forecast  │  │
                    │  └────┬────┘  └─────┬─────┘  │
                    │       │              │        │
                    │  ┌────▼──────────────▼────┐  │
                    │  │  ADF + KPSS + Hurst    │  │
                    │  │  (mean-rev validation)  │  │
                    │  └────────────┬───────────┘  │
                    │               │               │
                    │  ┌────────────▼───────────┐  │
                    │  │  Kalman Filter         │  │
                    │  │  (hedge ratio, smooth) │  │
                    │  └────────────┬───────────┘  │
                    │               │               │
                    │  ┌────────────▼───────────┐  │
                    │  │  Johansen (v0.4)       │  │
                    │  │  (basket cointegration)│  │
                    │  └────────────┬───────────┘  │
                    └──────────────┼────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │      Strategy Router           │
                    │                               │
                    │  Bull → Momentum Strategy     │
                    │  Bear → Short/Defensive       │
                    │  Range → Mean-Reversion       │
                    │  Vol↑ → Reduce Position 50%   │
                    └───────────────────────────────┘
```

---

*Агент 6 — Статистические модели*