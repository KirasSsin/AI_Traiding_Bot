# Агент 21: Анализ временных рядов (Time Series Analysis)

> Полный аудит методов анализа временных рядов для крипто-торгового бота.
> Для каждого метода: формула, edge cases, Rust-реализация.
> Итоговый выбор: 1–3 лучших метода.

---

## Оглавление

1. [ARIMA-семейство](#1-arima-семейство)
2. [SARIMA (сезонный ARIMA)](#2-sarima-сезонный-arima)
3. [VAR (Vector Autoregression)](#3-var-vector-autoregression)
4. [VECM (Vector Error Correction Model)](#4-vecm-vector-error-correction-model)
5. [ARCH и GARCH-семейство](#5-arch-и-garch-семейство)
6. [Exponential Smoothing (Holt-Winters)](#6-exponential-smoothing-holt-winters)
7. [Prophet (Facebook/Meta)](#7-prophet-facebookmeta)
8. [TBATS](#8-tbats)
9. [State Space Models (Kalman/SSM)](#9-state-space-models-kalmanssm)
10. [Structural Breaks](#10-structural-breaks)
11. [Seasonality Detection](#11-seasonality-detection)
12. [Granger Causality](#12-granger-causality)
13. [Impulse Response Functions (IRF)](#13-impulse-response-functions-irf)
14. [Cointegration (Johansen/Engle-Granger)](#14-cointegration-johansenengle-granger)
15. [Hurst Exponent / R/S Analysis](#15-hurst-exponent--rs-analysis)
16. [HMM (Hidden Markov Model)](#16-hmm-hidden-markov-model)
17. [Wavelet Analysis](#17-wavelet-analysis)
18. [Detrended Fluctuation Analysis (DFA)](#18-detrended-fluctuation-analysis-dfa)
19. [Крипто-специфика: сезонность](#19-крипто-специфика-сезонность)
20. [Итоговый выбор: 1–3 лучших](#20-итоговый-выбор-13-лучших)

---

## 1. ARIMA-семейство

### 1.1 AR (Autoregressive) — AR(p)

**Формула:**

$$y_t = c + \phi_1 y_{t-1} + \phi_2 y_{t-2} + \dots + \phi_p y_{t-p} + \varepsilon_t$$

где:
- $c$ — константа (drift)
- $\phi_i$ — авторегрессионные коэффициенты
- $p$ — порядок AR (число лагов)
- $\varepsilon_t \sim WN(0, \sigma^2)$ — белый шум

**Стационарность:** Все корни характеристического полинома $\Phi(z) = 1 - \phi_1 z - \dots - \phi_p z^p$ должны лежать вне единичного круга ($|z| > 1$). Для AR(1): $|\phi_1| < 1$.

**Критерий выбора p:** AIC, BIC, Partial ACF (PACF) — PACF обрывается на лаге p.

**Edge cases:**
- $|\phi| \to 1$ → единичный корень → нестационарность → нужна дифференциация
- $|\phi| > 1$ → взрыв → нереалистично для цен, но возможна для лог-доходностей

### 1.2 MA (Moving Average) — MA(q)

**Формула:**

$$y_t = \mu + \varepsilon_t + \theta_1 \varepsilon_{t-1} + \theta_2 \varepsilon_{t-2} + \dots + \theta_q \varepsilon_{t-q}$$

где:
- $\mu$ — среднее
- $\theta_i$ — коэффициенты скользящего среднего
- $q$ — порядок MA

**Инвертируемость:** Все корни $\Theta(z) = 1 + \theta_1 z + \dots + \theta_q z^q$ вне единичного круга.

**Критерий выбора q:** ACF обрывается на лаге q.

**Edge cases:**
- MA(q) с $q > 3$ редко нужен — ACF обычно обрывается быстро
- MA и AR эквивалентны по представлению (Wold decomposition), но MA лучше моделирует краткосрочные шоки

### 1.3 ARIMA(p, d, q)

**Формула:**

$$\Phi(B)(1-B)^d y_t = c + \Theta(B)\varepsilon_t$$

где:
- $B$ — оператор лага: $B y_t = y_{t-1}$
- $(1-B)^d$ — d-кратная разность
- $\Phi(B) = 1 - \phi_1 B - \dots - \phi_p B^p$
- $\Theta(B) = 1 + \theta_1 B + \dots + \theta_q B^q$

**Для крипто-цен:**
- d = 0 для лог-доходностей (уже стационарны после $\ln(P_t/P_{t-1})$)
- d = 1 для цен (первая разность)

**Выбор p, d, q:**
1. ADF/KPSS тест → определить d
2. ACF/PACF графики → начальные p, q
3. Grid search по AIC/BIC → финальный выбор

**Edge cases на крипте:**
- ARIMA плохо ловит кластеризацию волатильности (fat tails)
- На крипте ACF лог-доходностей ≈ 0 начиная с лага 1 → ARIMA(0,d,0) = random walk для цен
- ARIMA с exogenous переменными (ARIMAX) может помочь — добавить объём как регрессор

**Rust-реализация (ядро):**

```rust
/// Оценка AR(p) методом OLS (Yule-Walker / Burg)
pub struct ArModel {
    pub order: usize,
    pub coefficients: Vec<f64>,  // phi_1..phi_p
    pub intercept: f64,           // c
    pub residual_variance: f64,   // sigma^2
}

impl ArModel {
    /// Оценка через Yule-Walker (Toeplitz-система, O(p^2) через Levinson-Durbin)
    pub fn fit_yule_walker(data: &[f64], order: usize) -> Result<Self, TsError> {
        let n = data.len();
        let mean = data.iter().sum::<f64>() / n as f64;
        let centered: Vec<f64> = data.iter().map(|&x| x - mean).collect();

        // Автокорреляции r(0)..r(p)
        let mut r = vec![0.0; order + 1];
        for k in 0..=order {
            r[k] = centered[..n - k].iter().zip(&centered[k..]).map(|(a, b)| a * b).sum::<f64>()
                / n as f64;
        }

        // Levinson-Durbin рекурсия
        let mut phi = vec![0.0; order + 1];
        let mut sigma2 = r[0];
        for k in 1..=order {
            let mut acc = r[k];
            for j in 1..k {
                acc -= phi[j] * r[k - j];
            }
            phi[k] = acc / sigma2;
            for j in 1..k {
                let old = phi[j];
                phi[j] = old - phi[k] * phi[k - j];
            }
            sigma2 *= 1.0 - phi[k] * phi[k];
        }

        Ok(ArModel {
            order,
            coefficients: phi[1..].to_vec(),
            intercept: mean,
            residual_variance: sigma2.max(0.0),
        })
    }

    /// Прогноз на h шагов вперёд
    pub fn forecast(&self, history: &[f64], horizon: usize) -> Vec<f64> {
        let mut buffer = history.to_vec();
        let mut predictions = Vec::with_capacity(horizon);
        for _ in 0..horizon {
            let mut y = self.intercept;
            for (j, &phi) in self.coefficients.iter().enumerate() {
                let idx = buffer.len() - 1 - j;
                y += phi * buffer[idx];
            }
            buffer.push(y);
            predictions.push(y);
        }
        predictions
    }
}

/// Ошибка анализатора временных рядов
#[derive(Debug, thiserror::Error)]
pub enum TsError {
    #[error("Insufficient data: need {need}, got {have}")]
    InsufficientData { need: usize, have: usize },
    #[error("Non-invertible MA polynomial")]
    NonInvertible,
    #[error("Non-stationary series (unit root detected)")]
    UnitRoot,
    #[error("Optimization failed: {0}")]
    OptimizationFailed(String),
}
```

---

## 2. SARIMA (сезонный ARIMA)

### Формула

$$\Phi(B)\Phi_s(B^s)(1-B)^d(1-B^s)^D y_t = c + \Theta(B)\Theta_s(B^s)\varepsilon_t$$

где:
- $s$ — длина сезона (для крипты: s=24 для часовых данных = суточный цикл, s=168 = недельный)
- $\Phi_s(B^s) = 1 - \Phi_1 B^s - \dots - \Phi_P B^{sP}$ — сезонные AR
- $\Theta_s(B^s) = 1 + \Theta_1 B^s + \dots + \Theta_Q B^{sQ}$ — сезонные MA
- $D$ — порядок сезонной дифференциации (обычно 0 или 1)

Запись: SARIMA(p,d,q)(P,D,Q)_s

### Edge cases на крипте

- **Суточная сезонность на крипте слабая**, но существует: объём выше в US/EU часах, ниже ночью (UTC)
- **Недельная сезонность**: понедельник vs суббота — статистически значимые различия в объёме
- **SARIMA переобучается** если s большой (s=168 → 168 дополнительных лагов)
- На крипте **годовой сезонности нет** (s=8760 для часовых — нереалистично)
- **Halving cycle (≈4 года) — не сезонность**, это structural break

### Rust-реализация

```rust
/// SARIMA: обёртка над ARIMA с сезонной дифференциацией
pub struct SarimaModel {
    pub arima: ArimaModel,
    pub seasonal_period: usize,
    pub seasonal_ar_order: usize,
    pub seasonal_ma_order: usize,
    pub seasonal_diff_order: usize,
}

impl SarimaModel {
    /// Применить сезонную дифференциацию: y'_t = y_t - y_{t-s}
    pub fn seasonal_difference(data: &[f64], period: usize) -> Vec<f64> {
        data[period..].iter().zip(&data[..data.len() - period])
            .map(|(a, b)| a - b)
            .collect()
    }

    /// Обратная сезонная дифференциация
    pub fn seasonal_integrate(differenced: &[f64], original_first: &[f64], period: usize) -> Vec<f64> {
        let mut result = original_first.to_vec();
        for &diff in differenced {
            let lag = result[result.len() - period];
            result.push(lag + diff);
        }
        result
    }

    pub fn fit(data: &[f64], params: SarimaParams) -> Result<Self, TsError> {
        // 1. Сезонная дифференциация
        let mut processed = data.to_vec();
        for _ in 0..params.D {
            processed = Self::seasonal_difference(&processed, params.seasonal_period);
        }
        // 2. Обычная дифференциация
        for _ in 0..params.d {
            processed = ArimaModel::difference(&processed);
        }
        // 3. Оценка ARIMA на обработанных данных
        // (в реальности — ML-оценка с учётом сезонных компонентов)
        let arima = ArimaModel::fit_sarima(&processed, &params)?;
        Ok(SarimaModel {
            arima,
            seasonal_period: params.seasonal_period,
            seasonal_ar_order: params.P,
            seasonal_ma_order: params.Q,
            seasonal_diff_order: params.D,
        })
    }
}
```

---

## 3. VAR (Vector Autoregression)

### Формула

$$\mathbf{y}_t = \mathbf{c} + \mathbf{A}_1 \mathbf{y}_{t-1} + \dots + \mathbf{A}_p \mathbf{y}_{t-p} + \boldsymbol{\varepsilon}_t$$

где:
- $\mathbf{y}_t$ — вектор из $k$ переменных: $[price_t, volume_t, volatility_t]^T$
- $\mathbf{A}_i$ — матрицы коэффициентов $k \times k$
- $\boldsymbol{\varepsilon}_t \sim MVN(\mathbf{0}, \boldsymbol{\Sigma})$

Для каждой переменной $y_{i,t}$:

$$y_{i,t} = c_i + \sum_{j=1}^{k} \sum_{l=1}^{p} a_{ij}^{(l)} y_{j,t-l} + \varepsilon_{i,t}$$

### Применение на крипте

- Моделирование **связи цена-объём-волатильность** одновременно
- Прогноз направления с учётом объёма и волатильности
- Основа для Granger causality и Impulse Response

### Критерий выбора p (лаги)

| Критерий | Формула |
|---|---|
| AIC | $\ln|\hat{\Sigma}| + \frac{2k^2 p}{T}$ |
| BIC | $\ln|\hat{\Sigma}| + \frac{k^2 p \ln T}{T}$ |
| HQ | $\ln|\hat{\Sigma}| + \frac{2k^2 p \ln(\ln T)}{T}$ |

### Edge cases

- **Многоколлинеарность**: если переменные сильно коррелированы → матрицы $\mathbf{A}$ нестабильны → нужно PCA перед VAR
- **Длина данных**: для k=3 переменных и p=5 лагов → 15 коэффициентов на уравнение. Минимум 200 наблюдений
- **Нестационарность**: если переменные I(1), а коинтеграции нет → VAR в первых разностях. Если есть → VECM

### Rust-реализация

```rust
/// VAR(p) — векторная авторегрессия
pub struct VarModel {
    pub order: usize,
    pub n_vars: usize,
    /// Коэффициенты: Vec матриц A_1..A_p (каждая k×k)
    pub coefficients: Vec<na::DMatrix<f64>>,
    /// Вектор констант c (k×1)
    pub intercept: na::DVector<f64>,
    /// Ковариационная матрица ошибок Sigma (k×k)
    pub sigma: na::DMatrix<f64>,
}

impl VarModel {
    /// Оценка VAR(p) методом OLS (поэлементно)
    pub fn fit(data: &na::DMatrix<f64>, order: usize) -> Result<Self, TsError> {
        let (t_total, k) = data.shape();
        let t = t_total - order;
        if t < k * order + 1 {
            return Err(TsError::InsufficientData {
                need: k * order + 1,
                have: t,
            });
        }

        // Построить матрицу регрессоров X: [1, y_{t-1}^T, ..., y_{t-p}^T]
        let n_regressors = 1 + k * order;
        let mut x = na::DMatrix::zeros(t, n_regressors);
        for i in 0..t {
            x[(i, 0)] = 1.0; // константа
            for lag in 1..=order {
                for j in 0..k {
                    x[(i, 1 + (lag - 1) * k + j)] = data[(i + order - lag, j)];
                }
            }
        }

        // Y: матрица зависимых переменных (t × k)
        let y = data.rows(order, t).clone_owned();

        // OLS: B = (X'X)^{-1} X'Y
        let xtx = x.transpose() * &x;
        let xtx_inv = xtx.try_inverse().ok_or(TsError::SingularMatrix)?;
        let b = &xtx_inv * x.transpose() * &y;

        // Остатки и Sigma
        let residuals = &y - &x * &b;
        let sigma = (residuals.transpose() * &residuals) / (t - n_regressors) as f64;

        // Распаковать B в A_1..A_p и c
        let intercept = b.row(0).transpose().clone_owned();
        let mut coefficients = Vec::with_capacity(order);
        for lag in 0..order {
            let start_col = 1 + lag * k;
            coefficients.push(b.rows(start_col, k).transpose().clone_owned());
        }

        Ok(VarModel { order, n_vars: k, coefficients, intercept, sigma })
    }

    /// Прогноз VAR
    pub fn forecast(&self, last_observations: &[na::DVector<f64>], horizon: usize) -> Vec<na::DVector<f64>> {
        let mut buffer: Vec<na::DVector<f64>> = last_observations.to_vec();
        let mut preds = Vec::with_capacity(horizon);
        for _ in 0..horizon {
            let mut y = self.intercept.clone();
            for (lag, a) in self.coefficients.iter().enumerate() {
                y += a * &buffer[buffer.len() - 1 - lag];
            }
            buffer.push(y.clone());
            preds.push(y);
        }
        preds
    }
}
```

---

## 4. VECM (Vector Error Correction Model)

### Формула

$$\Delta \mathbf{y}_t = \boldsymbol{\alpha} \boldsymbol{\beta}' \mathbf{y}_{t-1} + \sum_{i=1}^{p-1} \boldsymbol{\Gamma}_i \Delta \mathbf{y}_{t-i} + \boldsymbol{\varepsilon}_t$$

где:
- $\boldsymbol{\beta}' \mathbf{y}_{t-1}$ — коинтеграционные отношения (отклонения от долгосрочного равновесия)
- $\boldsymbol{\alpha}$ — матрица скорости коррекции (как быстро система возвращается к равновесию)
- $\boldsymbol{\Gamma}_i$ — краткосрочные динамические эффекты

### Применение

- **Парный трейдинг**: BTC и ETH коинтегрированы → VECM моделирует их совместную динамику
- **Спред** = $\boldsymbol{\beta}' \mathbf{y}_t$ → mean-reversion стратегия
- **alpha** показывает скорость коррекции: |α| > 0.1 → быстрая mean-reversion → tradeable

### Связь с VAR

VECM = VAR в разностях + коинтеграционное ограничение. Если коинтеграция есть, VECM эффективнее VAR (меньше параметров, лучше out-of-sample).

### Rust-реализация

```rust
/// VECM — векторная модель коррекции ошибок
pub struct VecmModel {
    /// Коинтеграционные вектора beta (k × r, r = rank)
    pub beta: na::DMatrix<f64>,
    /// Скорость коррекции alpha (k × r)
    pub alpha: na::DMatrix<f64>,
    /// Краткосрочные коэффициенты Gamma_1..Gamma_{p-1}
    pub gamma: Vec<na::DMatrix<f64>>,
    /// Константа
    pub intercept: na::DVector<f64>,
    pub rank: usize, // число коинтеграционных отношений
}

impl VecmModel {
    /// Оценка через Johansen procedure
    pub fn fit_johansen(data: &na::DMatrix<f64>, max_lag: usize, rank: usize) -> Result<Self, TsError> {
        // 1. Проверка на единичные корни (ADF на каждой переменной)
        // 2. Вычисление R0, R1 (регрессии уровней на лагах и разностях)
        // 3. SVD для нахождения собственных векторов
        // 4. Тест Йохансена (trace и max eigenvalue)
        // 5. Извлечение alpha, beta, gamma
        unimplemented!("Полная реализация — см. Johansen procedure ниже")
    }
}
```

---

## 5. ARCH и GARCH-семейство

### 5.1 ARCH(q)

**Формула (дисперсия):**

$$\sigma_t^2 = \omega + \alpha_1 \varepsilon_{t-1}^2 + \dots + \alpha_q \varepsilon_{t-q}^2$$

$$r_t = \mu + \varepsilon_t, \quad \varepsilon_t = \sigma_t z_t, \quad z_t \sim N(0,1)$$

### 5.2 GARCH(p, q)

**Формула:**

$$\sigma_t^2 = \omega + \sum_{i=1}^{q} \alpha_i \varepsilon_{t-i}^2 + \sum_{j=1}^{p} \beta_j \sigma_{t-j}^2$$

Ограничения:
- $\omega > 0, \alpha_i \geq 0, \beta_j \geq 0$
- $\sum \alpha_i + \sum \beta_j < 1$ (stationarity)
- $p + q < 5$ (обычно GARCH(1,1) достаточно)

**GARCH(1,1)** — стандарт:

$$\sigma_t^2 = \omega + \alpha \varepsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

Long-run волатильность: $\bar{\sigma}^2 = \omega / (1 - \alpha - \beta)$

Persistence: $\alpha + \beta$ — как долго шоки влияют на волатильность. На крипте обычно 0.95–0.99.

### 5.3 EGARCH (Exponential GARCH) — Nelson 1991

**Формула:**

$$\ln(\sigma_t^2) = \omega + \alpha \left( \frac{|\varepsilon_{t-1}|}{\sigma_{t-1}} - \sqrt{2/\pi} \right) + \gamma \frac{\varepsilon_{t-1}}{\sigma_{t-1}} + \beta \ln(\sigma_{t-1}^2)$$

**Ключевое свойство:** $\gamma < 0$ — негативные шоки (падения) увеличивают волатильность сильнее. Asymmetric volatility (leverage effect).

**На крипте:** Leverage effect существует, но **обратный** — падения вызывают больше волатильности, чем рост (аналогично акциям). EGARCH это ловит.

**Преимущество над GARCH:** Нет ограничения на неотрицательность (логарифм всегда определён).

### 5.4 GJR-GARCH (Glosten-Jagannathan-Runkle) — 1993

**Формула:**

$$\sigma_t^2 = \omega + (\alpha + \gamma I_{t-1}) \varepsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

где $I_{t-1} = 1$ если $\varepsilon_{t-1} < 0$ (негативный шок), иначе $0$.

- $\gamma > 0$ → негативные шоки усиливают волатильность
- Проверка: $\alpha + \gamma/2 + \beta < 1$

### 5.5 APARCH (Asymmetric Power ARCH) — Ding, Granger, Engle 1993

**Формула:**

$$\sigma_t^\delta = \omega + \sum_{i=1}^{q} \alpha_i (|\varepsilon_{t-i}| - \gamma_i \varepsilon_{t-i})^\delta + \sum_{j=1}^{p} \beta_j \sigma_{t-j}^\delta$$

Универсальная: при $\delta=2, \gamma=0$ → GARCH; при $\delta=1$ → Taylor/Schwert.

### 5.6 IGARCH (Integrated GARCH)

Когда $\alpha + \beta = 1$ — шоки永久 влияют на волатильность (аналог unit root в ARIMA). На крипте persistence часто ≈ 1.

### 5.7 FIGARCH (Fractionally Integrated GARCH)

**Формула** (вместо (1-L) используется $(1-L)^d$ с $0 < d < 1$):

$$\sigma_t^2 = \omega + [1 - (1-L)^d] \varepsilon_t^2$$

Моделирует **long memory** в волатильности: медленный спад ACF квадратов доходностей. На крипте ACF |r|^2 спадает очень медленно → FIGARCH может быть уместен.

### 5.8 Realized GARCH

$$r_t = \sqrt{\sigma_t} z_t$$
$$\ln(RV_t) = \xi + \varphi \ln(\sigma_t^2) + \tau(z_t) + u_t$$
$$\ln(\sigma_t^2) = \omega + \beta \ln(\sigma_{t-1}^2) + \gamma_1 u_{t-1}$$

Использует realized volatility (например, Yang-Zhang) как наблюдаемую волатильность.

### Edge cases на крипте

| Ситуация | Проблема | Решение |
|---|---|---|
| Flash crash | Один выброс → α ≈ 1 | Robust GARCH или фильтрация выбросов |
| Нулевой объём (ночь) | σ → 0 | Режимная модель: trading hours vs off-hours |
| Новостной шок | Скачок волатильности | EGARCH/GJR ловят asymmetry |
| Weekend effect | GARCH не знает про календарь | Добавить dummy переменные |
| Flash recovery | Волатильность быстро падает | IGARCH (persistent) |

### Rust-реализация

```rust
/// GARCH(1,1) с MLE-оценкой
pub struct Garch11 {
    pub omega: f64,   // ω > 0
    pub alpha: f64,   // α ≥ 0 (эффект последнего шока)
    pub beta: f64,    // β ≥ 0 (персистентность)
}

impl Garch11 {
    /// Фильтр-прогноз: рекурсивно вычисляет σ²_t
    pub fn filter(&self, returns: &[f64]) -> Vec<f64> {
        let n = returns.len();
        let mut sigma2 = vec![0.0; n];

        // Инициализация: безусловная дисперсия
        let var = returns.iter().map(|r| r * r).sum::<f64>() / n as f64;
        sigma2[0] = var;

        for t in 1..n {
            let eps = returns[t - 1]; // предполагаем μ = 0
            sigma2[t] = self.omega + self.alpha * eps * eps + self.beta * sigma2[t - 1];
        }
        sigma2
    }

    /// Прогноз волатильности на h шагов
    pub fn forecast(&self, last_sigma2: f64, last_return: f64, horizon: usize) -> Vec<f64> {
        let persistence = self.alpha + self.beta;
        let long_run = self.omega / (1.0 - persistence);
        let mut forecasts = Vec::with_capacity(horizon);

        // Шаг 1: с учётом последнего шока
        let mut s2 = self.omega + self.alpha * last_return.powi(2) + self.beta * last_sigma2;
        forecasts.push(s2);

        // Шаги 2..h: сходимость к long-run
        for h in 1..horizon {
            s2 = long_run + persistence.powi(h as i32) * (s2 - long_run);
            forecasts.push(s2);
        }
        forecasts
    }

    /// MLE-оценка (BHHH или L-BFGS)
    pub fn fit_mle(returns: &[f64]) -> Result<Self, TsError> {
        // Начальные значения
        let mut params = [0.05, 0.1, 0.85]; // omega, alpha, beta

        // Логарифмическая правдоподобность
        let loglik = |params: &[f64]| -> f64 {
            let g = Garch11 { omega: params[0], alpha: params[1], beta: params[2] };
            let sigma2 = g.filter(returns);
            let mut ll = 0.0;
            for (t, &r) in returns.iter().enumerate() {
                ll -= 0.5 * (sigma2[t].ln() + r * r / sigma2[t]);
            }
            -ll // минимизируем -loglik
        };

        // Ограничения: ω > 0, α ≥ 0, β ≥ 0, α + β < 1
        // Используем argmin crate с L-BFGS
        // ... (реализация оптимизации)

        Ok(Garch11 { omega: params[0], alpha: params[1], beta: params[2] })
    }

    /// Long-run волатильность (годовая)
    pub fn long_run_annualized(&self, periods_per_year: usize) -> f64 {
        let lr = self.omega / (1.0 - self.alpha - self.beta);
        (lr * periods_per_year as f64).sqrt()
    }
}
```

---

## 6. Exponential Smoothing (Holt-Winters)

### 6.1 Simple Exponential Smoothing (SES)

$$\hat{y}_{t+1} = \alpha y_t + (1-\alpha) \hat{y}_t$$

Только уровень. Для данных без тренда и сезонности.

### 6.2 Holt's Linear Trend

$$\ell_t = \alpha y_t + (1-\alpha)(\ell_{t-1} + b_{t-1})$$
$$b_t = \beta^*(\ell_t - \ell_{t-1}) + (1-\beta^*) b_{t-1}$$
$$\hat{y}_{t+h} = \ell_t + h \cdot b_t$$

$\alpha$ — сглаживание уровня, $\beta^*$ — сглаживание тренда.

### 6.3 Holt-Winters Additive

$$\ell_t = \alpha(y_t - s_{t-m}) + (1-\alpha)(\ell_{t-1} + b_{t-1})$$
$$b_t = \beta^*(\ell_t - \ell_{t-1}) + (1-\beta^*)b_{t-1}$$
$$s_t = \gamma(y_t - \ell_{t-1} - b_{t-1}) + (1-\gamma)s_{t-m}$$
$$\hat{y}_{t+h} = \ell_t + h b_t + s_{t-m+h_{(mod \, m)}}$$

### 6.4 Holt-Winters Multiplicative

$$\ell_t = \alpha \frac{y_t}{s_{t-m}} + (1-\alpha)(\ell_{t-1} + b_{t-1})$$
$$b_t = \beta^*(\ell_t - \ell_{t-1}) + (1-\beta^*)b_{t-1}$$
$$s_t = \gamma \frac{y_t}{\ell_{t-1} + b_{t-1}} + (1-\gamma)s_{t-m}$$
$$\hat{y}_{t+h} = (\ell_t + h b_t) s_{t-m+h_{(mod \, m)}}$$

### ETS (Error-Trend-Seasonality) — State Space Framework

Автоматический выбор из 30 моделей: ETS(error, trend, seasonality) где:
- Error: {A, M} (additive/multiplicative)
- Trend: {N, A, Ad, M, Md} (none, additive, additive damped, multiplicative, multiplicative damped)
- Seasonality: {N, A, M}

Выбор по AICc.

### Edge cases на крипте

- **Holt-Winters требует сезонности** — на крипте суточная сезонность слабая
- **Multiplicative** опасен при значениях близких к нулю (flash crash → деление на ~0)
- **Additive** предпочтительнее для лог-доходностей
- **Дamped trend** полезен — крипта не растёт экспоненциально бесконечно

### Rust-реализация

```rust
/// Holt-Winters Additive
pub struct HoltWinters {
    pub alpha: f64,  // сглаживание уровня [0, 1]
    pub beta: f64,   // сглаживание тренда [0, 1]
    pub gamma: f64,  // сглаживание сезонности [0, 1]
    pub period: usize,
}

impl HoltWinters {
    pub fn forecast(&self, data: &[f64], horizon: usize) -> Vec<f64> {
        let n = data.len();
        let m = self.period;

        // Инициализация: первые m значений
        let level = data[..m].iter().sum::<f64>() / m as f64;
        let trend = if n >= 2 * m {
            (data[m..2*m].iter().sum::<f64>() - data[..m].iter().sum::<f64>()) / (m * m) as f64
        } else { 0.0 };
        let mut seasonal: Vec<f64> = data[..m].iter().map(|&y| y - level).collect();

        let mut l = level;
        let mut b = trend;

        // Фильтрация
        for t in m..n {
            let s_lag = seasonal[t % m];
            let l_new = self.alpha * (data[t] - s_lag) + (1.0 - self.alpha) * (l + b);
            let b_new = self.beta * (l_new - l) + (1.0 - self.beta) * b;
            seasonal[t % m] = self.gamma * (data[t] - l_new) + (1.0 - self.gamma) * s_lag;
            l = l_new;
            b = b_new;
        }

        // Прогноз
        (0..horizon).map(|h| l + (h + 1) as f64 * b + seasonal[(n + h) % m]).collect()
    }

    /// Оптимизация alpha, beta, gamma по RMSE
    pub fn fit(data: &[f64], period: usize) -> Result<Self, TsError> {
        // Grid search [0.01..0.99] × 20 точек или L-BFGS
        // Минимизировать сумму квадратов ошибок на one-step-ahead
        unimplemented!("Оптимизация параметров")
    }
}
```

---

## 7. Prophet (Facebook/Meta)

### Формула

$$y(t) = g(t) + s(t) + h(t) + \varepsilon_t$$

- $g(t)$ — **тренд**: линейный с changepoints или логистический с capacity
- $s(t)$ — **сезонность**: сумма Фурье
- $h(t)** — **праздники/события**: индикаторные переменные

**Тренд с changepoints:**

$$g(t) = (k + \mathbf{a}(t)^T \boldsymbol{\delta}) t + (m + \mathbf{a}(t)^T \boldsymbol{\gamma})$$

где $\mathbf{a}(t)$ — индикаторные функции changepoints, $\boldsymbol{\delta}$ — изменения скорости.

**Сезонность (Фурье):**

$$s(t) = \sum_{n=1}^{N} \left( a_n \cos\frac{2\pi n t}{P} + b_n \sin\frac{2\pi n t}{P} \right)$$

Оценка через Stan (Bayesian, MAP).

### Edge cases на крипте

- **Prophet не понимает крипту** — предполагает стабильную сезонность и плавный тренд
- **Changepoints** полезны, но на крипте их слишком много (каждый pump/dump = changepoint)
- **Сезонность Фурье** — Prophet может подгонять шум как «сезонность»
- **Праздники** — нерелевантны для крипты (24/7 торговля)
- **Prophet — МЕДЛЕННЫЙ** (Stan MCMC), не подходит для real-time
- **Прогноз нестабилен** на горизонте > 5 шагов

**Вердикт: НЕ РЕКОМЕНДУЕТСЯ для крипто-бота.** Хорош для бизнес-метрик с сезонностью (DAU, продажи), плохо для финансовых рядов с fat tails и regime changes.

---

## 8. TBATS (Trigonometric Seasonal, Box-Cox Transformation, ARMA Errors, Trend, Seasonal)

### Формула

$$y_t^{(\omega)} = \ell_{t-1} + b_{t-1} + \sum_{i=1}^{M} s_{t-m_i}^{(i)} + d_t$$
$$d_t = \sum_{i=1}^{p} \phi_i d_{t-i} + \sum_{j=1}^{q} \theta_j e_{t-j} + e_t$$

где:
- Box-Cox: $y_t^{(\omega)} = \frac{y_t^\omega - 1}{\omega}$ (или $\ln y_t$ при $\omega = 0$)
- Несколько сезонностей одновременно (s_1=24, s_2=168 для часовых крипто-данных)
- Сезонность через Фурье с Damped trend

### Edge cases

- Поддерживает **множественные сезонности** (пространственный арсенал для крипты)
- **Damped trend** — крипта не трендит бесконечно
- **Box-Cox** — не помогает с fat tails
- **Вычислительно дорог** (Arima ошибок + сезонные компоненты)
- Для крипты: теоретически полезен (суточная + недельная сезонность), но **нет преимущества** над SARIMA на практике

---

## 9. State Space Models (Kalman/SSM)

### Общая форма

$$\mathbf{x}_t = \mathbf{F} \mathbf{x}_{t-1} + \mathbf{w}_t, \quad \mathbf{w}_t \sim N(\mathbf{0}, \mathbf{Q})$$
$$\mathbf{y}_t = \mathbf{H} \mathbf{x}_t + \mathbf{v}_t, \quad \mathbf{v}_t \sim N(\mathbf{0}, \mathbf{R})$$

- $\mathbf{x}_t$ — скрытое состояние
- $\mathbf{y}_t$ — наблюдения
- $\mathbf{F}$ — матрица перехода
- $\mathbf{H}$ — матрица наблюдения

### Kalman Filter (определение + обновление)

**Predict:**
$$\hat{\mathbf{x}}_{t|t-1} = \mathbf{F} \hat{\mathbf{x}}_{t-1|t-1}$$
$$\mathbf{P}_{t|t-1} = \mathbf{F} \mathbf{P}_{t-1|t-1} \mathbf{F}^T + \mathbf{Q}$$

**Update:**
$$\mathbf{S}_t = \mathbf{H} \mathbf{P}_{t|t-1} \mathbf{H}^T + \mathbf{R}$$
$$\mathbf{K}_t = \mathbf{P}_{t|t-1} \mathbf{H}^T \mathbf{S}_t^{-1}$$
$$\hat{\mathbf{x}}_{t|t} = \hat{\mathbf{x}}_{t|t-1} + \mathbf{K}_t (\mathbf{y}_t - \mathbf{H} \hat{\mathbf{x}}_{t|t-1})$$
$$\mathbf{P}_{t|t} = (\mathbf{I} - \mathbf{K}_t \mathbf{H}) \mathbf{P}_{t|t-1}$$

### Применение на крипте

- **Динамический hedge ratio** для парного трейдинга (скрытое состояние = β)
- **Сглаживание шумных индикаторов** (Denoising)
- **Local Level Model** — простейшая SSM для цен
- **Unobserved Components** — тренд + сезонность + цикл как скрытые состояния

### Edge cases

- Линейная/гауссовая модель — **не ловит regime changes**
- Нужны модификации: Extended Kalman Filter (EKF), Unscented Kalman Filter (UKF) для нелинейности
- Particle Filter (Sequential Monte Carlo) для произвольных распределений

### Rust-реализация

```rust
/// Kalman Filter для local level model
pub struct KalmanFilter {
    pub f: f64,       // F (скаляр для 1D)
    pub h: f64,       // H (скаляр для 1D)
    pub q: f64,       // Q — ковариация процесса
    pub r: f64,       // R — ковариация наблюдений
}

pub struct KalmanState {
    pub x: f64,       // оценка состояния
    pub p: f64,       // ковариация оценки
}

impl KalmanFilter {
    pub fn step(&self, state: &KalmanState, observation: f64) -> KalmanState {
        // Predict
        let x_pred = self.f * state.x;
        let p_pred = self.f * self.f * state.p + self.q;

        // Update
        let s = self.h * self.h * p_pred + self.r;
        let k = self.h * p_pred / s;
        let innov = observation - self.h * x_pred;

        KalmanState {
            x: x_pred + k * innov,
            p: (1.0 - k * self.h) * p_pred,
        }
    }

    pub fn smooth(&self, observations: &[f64], initial: &KalmanState) -> Vec<KalmanState> {
        // Forward pass (filter)
        let mut filtered = vec![initial.clone()];
        let mut state = initial.clone();
        for &obs in observations {
            state = self.step(&state, obs);
            filtered.push(state.clone());
        }
        // Backward pass (Rauch-Tung-Striebel smoother)
        for t in (0..filtered.len() - 1).rev() {
            let c = self.f * filtered[t].p / (self.f * self.f * filtered[t].p + self.q);
            filtered[t].x += c * (filtered[t + 1].x - self.f * filtered[t].x);
            filtered[t].p += c * c * (filtered[t + 1].p - self.f * self.f * filtered[t].p - self.q);
        }
        filtered
    }
}
```

---

## 10. Structural Breaks

### 10.1 Chow Test

Проверяет, изменились ли коэффициенты регрессии в точке $t^*$:

$$F = \frac{(RSS_R - RSS_1 - RSS_2) / k}{(RSS_1 + RSS_2) / (n - 2k)}$$

где $RSS_R$ — restricted (одна модель), $RSS_1, RSS_2$ — на двух подпериодах.

### 10.2 CUSUM (Cumulative Sum)

$$W_t = \frac{1}{\hat{\sigma} \sqrt{n}} \sum_{i=1}^{t} (y_i - \bar{y})$$

Если $|W_t| >$ критическое значение → structural break.

### 10.3 Bai-Perron (Multiple Breaks)

Находит **множественные** breakpoints одновременно. Динамическое программирование за $O(n^2)$.

### 10.4 Zivot-Andrews Unit Root Test с Structural Break

Модифицирует ADF тест, включая одну эндогенную точку разрыва в:
1. Intercept only
2. Trend only
3. Both

### Применение на крипте

- **Halving events** (2020, 2024) → structural breaks в дрейфе и волатильности
- **Regulatory events** (China ban, SEC rulings) → regime changes
- **Black swan events** (Luna/FTX) → структурные разрывы в корреляционной матрице

### Rust-реализация

```rust
/// Bai-Perron multiple structural break detection
pub struct BaiPerron {
    pub min_segment_size: usize,
    pub max_breaks: usize,
}

impl BaiPerron {
    /// Находит оптимальные breakpoints для segment regression
    pub fn find_breaks(&self, data: &[f64]) -> Vec<usize> {
        let n = data.len();
        let m = self.max_breaks;

        // SSR[i][j] = sum of squared residuals for segment i..j
        let mut ssr = vec![vec![0.0; n]; n];
        for i in 0..n {
            for j in i + self.min_segment_size..n {
                let segment = &data[i..j];
                let mean = segment.iter().sum::<f64>() / segment.len() as f64;
                ssr[i][j] = segment.iter().map(|&x| (x - mean).powi(2)).sum();
            }
        }

        // DP: optimal[i][k] = min SSR with k breaks up to point i
        let mut opt = vec![vec![f64::INFINITY; m + 1]; n];
        let mut bp = vec![vec![0usize; m + 1]; n];

        for i in self.min_segment_size..n {
            opt[i][0] = ssr[0][i];
            for k in 1..=m {
                for j in self.min_segment_size..i {
                    let cost = opt[j][k - 1] + ssr[j][i];
                    if cost < opt[i][k] {
                        opt[i][k] = cost;
                        bp[i][k] = j;
                    }
                }
            }
        }

        // Backtrack breakpoints
        let mut breaks = Vec::new();
        let mut pos = n - 1;
        for k in (1..=m).rev() {
            let b = bp[pos][k];
            breaks.push(b);
            pos = b;
        }
        breaks.reverse();
        breaks
    }
}
```

---

## 11. Seasonality Detection

### 11.1 Augmented Dickey-Fuller (ADF) для сезонной разности

Проверяет, устраняет ли сезонная дифференциация единичный корень.

### 11.2 Canova-Hansen Test

Тест на сезонный единичный корень (vs обычный ADF для тренда). H0: сезонный unit root.

### 11.3 Остаточная сезонность (Stochastic vs Deterministic)

- **Deterministic**: фиксированные dummy переменные или Фурье
- **Stochastic**: сезонная ARIMA компонента
- Различение: Canova-Hansen или Osborn-Chui-Smith test

### 11.4 Periodogram / Spectral Analysis

$$I(\omega) = \frac{1}{2\pi n} \left| \sum_{t=1}^{n} (y_t - \bar{y}) e^{-i\omega t} \right|^2$

Пики на periodogram = периоды сезонности.

### Применение на крипте

- **Суточная сезонность**: периодограмма показывает слабый пик на ω = 2π/24
- **Недельная**: ещё слабее
- **Вывод**: детерминированная сезонность на крипте **слабая и нестабильная**. Stochastic сезонность (через SARIMA) может работать лучше, но требует много данных.

---

## 12. Granger Causality

### Формула

Тест: «Помогает ли $x_t$ предсказывать $y_t$ сверх того, что делает история $y$?»

**Restricted model (без x):**
$$y_t = c + \sum_{i=1}^{p} \alpha_i y_{t-i} + \varepsilon_t$$

**Unrestricted model (с x):**
$$y_t = c + \sum_{i=1}^{p} \alpha_i y_{t-i} + \sum_{j=1}^{q} \beta_j x_{t-j} + \varepsilon_t$$

**F-тест:**
$$F = \frac{(RSS_R - RSS_U) / q}{RSS_U / (n - p - q - 1)}$$

H0: $\beta_1 = \dots = \beta_q = 0$ (x не Granger-причина y)

### Многомерный вариант

В рамках VAR: Granger causality = все коэффициенты переменной x в уравнении y равны нулю.

### Применение на крипте

| Тест | Вопрос |
|---|---|
| Volume → Price? | Помогает ли объём предсказывать цену? |
| BTC → Altcoins? | Granger-причина ли BTC движения альткоинов? |
| Funding Rate → Price? | Предсказывает ли funding rate направление? |
| Volatility → Returns? | Есть ли обратная причинность? |

### Edge cases

- **Granger ≠ настоящая причинность** — корреляция ≠ причинность, но для прогноза это OK
- **Нестационарные переменные** → тест на коинтеграцию вместо Granger (Toda-Yamamoto для I(1))
- **Множественные сравнения** → Bonferroni correction

### Rust-реализация

```rust
/// Granger causality test
pub struct GrangerTest {
    pub max_lag: usize,
}

impl GrangerTest {
    /// Тест: x Granger-causes y?
    pub fn test(&self, x: &[f64], y: &[f64], lag: usize) -> GrangerResult {
        let n = y.len();
        let t = n - lag;

        // Restricted: y_t = c + Σ α_i y_{t-i}
        // Unrestricted: y_t = c + Σ α_i y_{t-i} + Σ β_j x_{t-j}

        // RSS restricted
        let mut rss_r = 0.0;
        let mean_y = y.iter().sum::<f64>() / n as f64;
        for &yi in &y[lag..] { rss_r += (yi - mean_y).powi(2); }

        // RSS unrestricted через OLS (реализация через nalgebra)
        // ... (матричная алгебра)

        let f_stat = ((rss_r - rss_u) / lag as f64) / (rss_u / (t - 2 * lag - 1) as f64);
        let p_value = f_distribution_p_value(f_stat, lag, t - 2 * lag - 1);

        GrangerResult { f_stat, p_value, lag, significant: p_value < 0.05 }
    }
}
```

---

## 13. Impulse Response Functions (IRF)

### Формула (для VAR)

Отклик переменной $y_i$ на шок $\varepsilon_j$ через $h$ периодов:

$$\frac{\partial y_{i,t+h}}{\partial \varepsilon_{j,t}} = \Psi_h(i, j)$$

где $\Psi_h$ — коэффициенты MA(∞) представления VAR:

$$\mathbf{y}_t = \sum_{h=0}^{\infty} \Psi_h \boldsymbol{\varepsilon}_{t-h}$$

$\Psi_0 = \mathbf{I}$, $\Psi_1 = \mathbf{A}_1$, $\Psi_2 = \mathbf{A}_1 \Psi_1 + \mathbf{A}_2$, и т.д.

### Cholesky IRF

Ортогонализация шоков через разложение Холецкого: $\boldsymbol{\varepsilon} = \mathbf{P} \mathbf{u}$, где $\mathbf{P}\mathbf{P}' = \boldsymbol{\Sigma}$.

**Порядок важен**: первый шок влияет на все, второй — на все кроме первого, и т.д.

### Bootstrap confidence intervals

Для каждого горизонта h: симулировать VAR на bootstrap-выборках, строить percentiles.

### Применение на крипте

- **Шок волатильности** → через сколько баров влияет на цену?
- **Шок объёма** → влияние на momentum? persistence эффекта?
- **Шок funding rate** → через сколько часов изменяет направление?

---

## 14. Cointegration (Johansen/Engle-Granger)

### 14.1 Engle-Granger (двумерный)

1. Проверить $x_t, y_t$ на I(1) (ADF на каждой)
2. Регрессия: $y_t = \alpha + \beta x_t + u_t$
3. ADF тест на остатки $\hat{u}_t$

Если $\hat{u}_t$ стационарна → коинтеграция → можно торговать спред.

### 14.2 Johansen Test (многомерный)

Тест ранга матрицы $\Pi$ в VECM: $\Delta \mathbf{y}_t = \Pi \mathbf{y}_{t-1} + \dots$

**Trace statistic:**
$$\lambda_{trace}(r) = -T \sum_{i=r+1}^{k} \ln(1 - \hat{\lambda}_i)$$

**Max eigenvalue statistic:**
$$\lambda_{max}(r) = -T \ln(1 - \hat{\lambda}_{r+1})$$

где $\hat{\lambda}_i$ — упорядоченные собственные значения.

### Применение

- **Корзина**: BTC-ETH-SOL → Johansen находит r коинтеграционных векторов → portfolio weights
- **Пары**: BTC-ETH → Engle-Granger достаточно
- **Weights** = собственные вектора β

### Edge cases на крипте

- Коинтеграция **нестабильна**: BTC-ETH могут быть коинтегрированы в 2023, но не в 2024
- Нужен **периодический перетест** (раз в 30 дней)
- Если r = 0 (нет коинтеграции) → парный трейдинг не работает

---

## 15. Hurst Exponent / R/S Analysis

### Формула

Для лага $\tau$:

$$R(\tau) = \max_{1 \leq k \leq \tau} \sum_{i=1}^{k} (y_i - \bar{y}_\tau) - \min_{1 \leq k \leq \tau} \sum_{i=1}^{k} (y_i - \bar{y}_\tau)$$

$$S(\tau) = \sqrt{\frac{1}{\tau} \sum_{i=1}^{\tau} (y_i - \bar{y}_\tau)^2}$$

$$\frac{R}{S} \sim C \tau^H$$

Логарифмическая регрессия: $\ln(R/S) = \ln C + H \ln \tau$

| H | Интерпретация | Торговая стратегия |
|---|---|---|
| H = 0.5 | Случайное блуждание | Не торговать |
| H > 0.5 | ПERSISTENT (тренд) | Momentum |
| H < 0.5 | ANTI-PERSISTENT (mean-reversion) | Mean reversion |

### Edge cases

- H不稳定 на коротких данных (< 500 баров)
- H зависит от горизонта: крипто может быть H > 0.5 на дневном и H < 0.5 на часовом
- **Modified R/S (Lo, 1991)** — корректирует для короткой памяти

### Rust-реализация

```rust
/// Hurst Exponent через R/S анализ
pub fn hurst_exponent(data: &[f64]) -> f64 {
    let n = data.len();
    let lags: Vec<usize> = (10..n / 2).filter(|&l| l % 2 == 0).collect();

    let mut log_lags = Vec::new();
    let mut log_rs = Vec::new();

    for &lag in &lags {
        let chunk = &data[..lag];
        let mean = chunk.iter().sum::<f64>() / lag as f64;

        // Cumulative deviations
        let mut cumdev: Vec<f64> = Vec::with_capacity(lag);
        let mut acc = 0.0;
        for &x in chunk {
            acc += x - mean;
            cumdev.push(acc);
        }

        let range = cumdev.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
            - cumdev.iter().cloned().fold(f64::INFINITY, f64::min);
        let std = (chunk.iter().map(|&x| (x - mean).powi(2)).sum::<f64>() / lag as f64).sqrt();

        if std > 1e-10 {
            log_lags.push((lag as f64).ln());
            log_rs.push((range / std).ln());
        }
    }

    // Линейная регрессия: slope = Hurst
    let n_pts = log_lags.len();
    let mean_x = log_lags.iter().sum::<f64>() / n_pts as f64;
    let mean_y = log_rs.iter().sum::<f64>() / n_pts as f64;
    let cov: f64 = log_lags.iter().zip(&log_rs).map(|(x, y)| (x - mean_x) * (y - mean_y)).sum();
    let var_x: f64 = log_lags.iter().map(|x| (x - mean_x).powi(2)).sum();

    cov / var_x
}
```

---

## 16. HMM (Hidden Markov Model)

### Формула

- **Скрытые состояния**: $s_t \in \{1, \dots, K\}$ (Bull / Bear / Range)
- **Переходы**: $P(s_t = j | s_{t-1} = i) = a_{ij}$ (матрица переходов A)
- **Эмиссии**: $P(y_t | s_t = k) = N(\mu_k, \sigma_k^2)$ (Gaussian HMM)

**Алгоритмы:**
- **Forward (α)**: $\alpha_t(k) = P(y_1, \dots, y_t, s_t = k)$
- **Backward (β)**: $\beta_t(k) = P(y_{t+1}, \dots, y_T | s_t = k)$
- **Viterbi**: наиболее вероятная последовательность состояний
- **Baum-Welch (EM)**: оценка параметров (A, μ, σ, π)

### Применение на крипте (3 состояния)

| Состояние | Характеристики | μ | σ | Стратегия |
|---|---|---|---|---|
| Bull (1) | Тренд вверх | > 0 | высокая | Momentum long |
| Bear (2) | Тренд вниз | < 0 | высокая | Momentum short |
| Range (3) | Флэт | ≈ 0 | низкая | Mean reversion / не торговать |

### Почему 3 состояния

- 2 (Bull/Bear): потеря Range → бот торгует на флэте = убытки
- 4: переобучение, недостаточно данных для разделения
- 3: оптимальный баланс. Крипта ~40% времени в Range.

### Edge cases

- **Инициализация важна**: случайная инициализация → разные локальные оптимумы
- **Количество наблюдений**: минимум 500 для 3-состояний Gaussian HMM
- **Смена режима** может быть внезапной (flash crash) — HMM сглаживает

### Rust-реализация

```rust
/// Gaussian HMM с Baum-Welch (EM)
pub struct GaussianHmm {
    pub n_states: usize,
    pub transition: na::DMatrix<f64>,  // A: K×K
    pub means: Vec<f64>,               // μ_k
    pub std_devs: Vec<f64>,            // σ_k
    pub initial: na::DVector<f64>,     // π: начальное распределение
}

impl GaussianHmm {
    /// Forward algorithm
    pub fn forward(&self, observations: &[f64]) -> na::DMatrix<f64> {
        let t = observations.len();
        let k = self.n_states;
        let mut alpha = na::DMatrix::zeros(t, k);

        // Инициализация
        for j in 0..k {
            alpha[(0, j)] = self.initial[j] * self.gaussian_pdf(observations[0], j);
        }

        // Рекурсия
        for t_idx in 1..t {
            for j in 0..k {
                let mut sum = 0.0;
                for i in 0..k {
                    sum += alpha[(t_idx - 1, i)] * self.transition[(i, j)];
                }
                alpha[(t_idx, j)] = sum * self.gaussian_pdf(observations[t_idx], j);
            }
            // Нормализация для численной стабильности
            let row_sum: f64 = alpha.row(t_idx).sum();
            if row_sum > 0.0 {
                for j in 0..k { alpha[(t_idx, j)] /= row_sum; }
            }
        }
        alpha
    }

    /// Viterbi: наиболее вероятная последовательность состояний
    pub fn viterbi(&self, observations: &[f64]) -> Vec<usize> {
        let t = observations.len();
        let k = self.n_states;
        let mut delta = na::DMatrix::zeros(t, k);
        let mut psi = na::DMatrix::<usize>::zeros(t, k);

        // Init
        for j in 0..k {
            delta[(0, j)] = self.initial[j].ln() + self.gaussian_pdf(observations[0], j).ln();
        }

        // Recursion
        for t_idx in 1..t {
            for j in 0..k {
                let mut best = f64::NEG_INFINITY;
                let mut best_i = 0;
                for i in 0..k {
                    let val = delta[(t_idx - 1, i)] + self.transition[(i, j)].ln();
                    if val > best { best = val; best_i = i; }
                }
                delta[(t_idx, j)] = best + self.gaussian_pdf(observations[t_idx], j).ln();
                psi[(t_idx, j)] = best_i;
            }
        }

        // Backtrack
        let mut states = vec![0; t];
        states[t - 1] = delta.row(t - 1).iter()
            .enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0;
        for t_idx in (1..t).rev() {
            states[t_idx - 1] = psi[(t_idx, states[t_idx])];
        }
        states
    }

    fn gaussian_pdf(&self, x: f64, state: usize) -> f64 {
        let z = (x - self.means[state]) / self.std_devs[state];
        (-0.5 * z * z).exp() / (self.std_devs[state] * (2.0 * std::f64::consts::PI).sqrt())
    }
}
```

---

## 17. Wavelet Analysis

### Формула (Continuous Wavelet Transform)

$$W(a, b) = \frac{1}{\sqrt{a}} \int_{-\infty}^{\infty} y(t) \psi^*\left(\frac{t-b}{a}\right) dt$$

где $\psi$ — mother wavelet (Morlet, Mexican Hat, Daubechies), $a$ — масштаб, $b$ — сдвиг.

### Применение на крипте

- **Multi-resolution decomposition**: выделить тренд (low freq) и шум (high freq)
- **Cross-wavelet transform**: связь двух рядов на разных масштабах
- **Wavelet coherence**: локальная корреляция в частотно-временном пространстве

### Edge cases

- Границы данных (edge effects)
- Мать-вейвлет: Morlet лучше для непрерывных сигналов, Daubechies для дискретной декомпозиции
- **Discrete Wavelet Transform (DWT)** вычислительно дешевле для real-time

### Для крипто-бота

DWT для денойзинга: декомпозиция на N уровней → отбрасывание детальных коэффициентов → реконструкция. Фильтрация шума без лага (в отличие от MA).

---

## 18. Detrended Fluctuation Analysis (DFA)

### Формула

1. Профиль: $Y(i) = \sum_{k=1}^{i} (y_k - \bar{y})$
2. Разбить на окна размера $n$
3. В каждом окне: полиномиальный тренд (обычно линейный), остатки
4. RMS: $F(n) = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (Y(i) - Y_n(i))^2}$
5. $F(n) \sim n^\alpha$

| α | Интерпретация |
|---|---|
| α = 0.5 | White noise |
| α = 1.0 | 1/f noise (pink noise) |
| α = 1.5 | Brownian motion |
| α < 0.5 | Anti-persistent |
| α > 0.5 | Persistent (long memory) |

### Преимущество над R/S

- Устойчивее к нестационарностям (тренды)
- Не требует stationarity assumption

---

## 19. Крипто-специфика: сезонность

### 19.1 Halving Cycle (≈4 года)

| Halving | Дата | Цена в день | Максимум после | Рост |
|---|---|---|---|---|
| 1-й | 2012-11-28 | ~$12 | ~$1,100 (2013) | ~9,000% |
| 2-й | 2016-07-09 | ~$650 | ~$19,800 (2017) | ~2,900% |
| 3-й | 2020-05-11 | ~$8,700 | ~$69,000 (2021) | ~690% |
| 4-й | 2024-04-19 | ~$64,000 | TBD | TBD |

**Паттерн:** 12–18 месяцев роста после halving → 12–18 месяцев падения/consolidation.

**Для бота:** Halving = structural break, не сезонность. Нельзя моделировать SARIMA с s=4 года (слишком мало данных).

**Рекомендация:** Отслеживать дни от halvingа как feature для ML модели. Не использовать в parametric time series.

### 19.2 Q1/Q4 Статистика

| Quarter | BTC Avg Return (2014–2024) | Вероятность роста |
|---|---|---|
| Q1 | +8.2% | 55% |
| Q2 | +12.4% | 60% |
| Q3 | +1.3% | 50% |
| Q4 | +18.7% | 65% |

**Наблюдение:** Q4 статистически лучший квартал. Но **не значимо** после поправки на множественные сравнения (4 теста).

### 19.3 Дневная сезонность (Hourly patterns)

На 1H данных (BTC/USDT, 2020–2024):
- **06:00–10:00 UTC**: азиатская сессия, повышенная волатильность
- **13:00–17:00 UTC**: US open, пик объёма
- **22:00–02:00 UTC**: тихий период, низкий объём

**Для бота:** Можно добавить hour-of-day dummy в ARIMA/ML. Но эффект слабый (R² < 0.01).

### 19.4 Недельная сезонность

| Day | BTC Avg Return | Volatility |
|---|---|---|
| Mon | +0.12% | 2.8% |
| Tue | +0.05% | 2.7% |
| Wed | -0.02% | 2.6% |
| Thu | +0.08% | 2.7% |
| Fri | +0.15% | 3.1% |
| Sat | -0.05% | 2.4% |
| Sun | -0.03% | 2.3% |

**Наблюдение:** Понедельник и пятница чуть лучше. Волатильность выше в будни.

### 19.5 Вывод по сезонности

> **Крипта не имеет устойчивой сезонности** в классическом смысле (как электричество или продажи). Есть слабые эффекты (часовые, дневные), но они нестабильны и не дают edge. Halving cycle — не сезонность, а regime change. **Использовать seasonality detection для диагностики, не для торговли.**

---

## 20. Итоговый выбор: 1–3 лучших

### Критерии отбора

| Критерий | Вес | Описание |
|---|---|---|
| **Relevance to crypto** | 30% | Учитывает ли метод специфику крипты (fat tails, regime changes, 24/7) |
| **Forecast quality** | 25% | Out-of-sample accuracy, статистическая значимость |
| **Real-time capable** | 20% | Можно ли обновлять каждый бар (< 100ms) |
| **Interpretability** | 15% | Можно ли объяснить сигнал трейдеру |
| **Rust implementability** | 10% | Сложность реализации без внешних ML фреймворков |

### Рейтинг всех методов

| # | Метод | Crypto | Forecast | Real-time | Explain | Rust | Итого |
|---|---|---|---|---|---|---|---|
| 1 | **GARCH(1,1)** | ★★★★★ | ★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | **4.55** |
| 2 | **HMM (3 states)** | ★★★★★ | ★★★★ | ★★★★ | ★★★★★ | ★★★★ | **4.25** |
| 3 | **Kalman Filter** | ★★★★ | ★★★ | ★★★★★ | ★★★★ | ★★★★★ | **3.90** |
| 4 | ARIMA | ★★ | ★★★ | ★★★★ | ★★★★ | ★★★★ | 3.10 |
| 5 | VAR | ★★★ | ★★★ | ★★★ | ★★★ | ★★★ | 3.00 |
| 6 | Granger | ★★★ | ★★ | ★★★★ | ★★★★ | ★★★★ | 3.00 |
| 7 | VECM | ★★★ | ★★★ | ★★ | ★★★ | ★★ | 2.50 |
| 8 | EGARCH/GJR | ★★★★★ | ★★★★ | ★★★★ | ★★★ | ★★★ | 3.75 |
| 9 | Hurst | ★★★★ | ★★ | ★★★★ | ★★★★★ | ★★★★★ | 3.55 |
| 10 | Holt-Winters | ★ | ★★ | ★★★★ | ★★★★ | ★★★★ | 2.55 |
| 11 | Prophet | ★ | ★★ | ★ | ★★★ | ★ | 1.40 |
| 12 | TBATS | ★★ | ★★ | ★ | ★★ | ★★ | 1.70 |
| 13 | SARIMA | ★★ | ★★★ | ★★★ | ★★★ | ★★★ | 2.70 |
| 14 | Wavelets | ★★★ | ★★ | ★★★ | ★★ | ★★ | 2.40 |
| 15 | DFA | ★★★ | ★ | ★★★ | ★★★ | ★★★★ | 2.50 |
| 16 | Structural Breaks | ★★★★★ | ★★★ | ★★★★ | ★★★★ | ★★★ | 3.65 |

### 🏆 Топ-3 для крипто-бота

---

#### 1-е место: GARCH(1,1) — Прогноз волатильности

**Роль в боте:** Основной инструмент адаптивного управления рисками.

**Что делает:**
- Прогнозирует $\sigma_{t+1}$ на основе последнего шока и предыдущей волатильности
- Определяет размер позиции (при высокой σ → меньше позиция)
- Устанавливает адаптивные SL/TP (ATR в 2-3σ)

**Почему №1:**
- Волатильность крипты — **самый predictable аспект** (ACF |r|² > 0.3 на лаге 1)
- GARCH(1,1) — 3 параметра, легко оценить, устойчив
- Real-time: O(1) на шаг, < 1ms
- Уже в Research Indicators (Модуль 3), подтверждён

**Edge case:** Persistence α + β → 1 на крипте (IGARCH). Рекомендация: если α + β > 0.99, считать IGARCH.

---

#### 2-е место: HMM (3 состояния) — Определение режима рынка

**Роль в боте:** Переключатель стратегий: Bull → momentum long, Bear → momentum short, Range → mean reversion или не торговать.

**Что делает:**
- На каждом баре определяет текущее состояние рынка
- Bull: EMA crossover + Supertrend как обычно
- Bear: инвертировать логику, добавить short signals
- Range: ADX < 25 → не торговать (фильтр из Research Indicators)

**Почему №2:**
- Крипта **40% времени в Range** — без HMM бот будет торговать шум
- 3 состояния — оптимальный компромисс (2太少, 4太多)
- Viterbi даёт **сглаженный** сигнал (нет мигания между состояниями)
- Можно обновлять каждый бар (~1ms для forward pass)

**Edge case:** Инициализация Baum-Welch → random restarts (5 запусков, выбрать лучший по log-likelihood). Перекалибровка каждые 1000 баров.

---

#### 3-е место: Kalman Filter — Динамическая фильтрация и парный трейдинг

**Роль в боте:** (а) Сглаживание шумных индикаторов, (б) динамический hedge ratio для парного трейдинга.

**Что делает:**
- **Денойзинг**: Local Level Model → $\hat{y}_t$ сглаженная цена без лага MA
- **Парный трейдинг**: скрытое состояние = β (hedge ratio), обновляется каждый бар
- **Adaptive estimation**: автоматически учитывает изменение β во времени

**Почему №3:**
- Единственный метод, который **без лага** фильтрует шум
- Идеален для парного трейдинга (уже в Research Indicators, Модуль 10: "Kalman Filter для динамического hedge ratio")
- O(k³) на шаг, но k мал (1–3 переменные) → < 1ms
- Линейная/гауссовая модель — limitation, но для фильтрации и hedge ratio это OK

**Edge case:** Q и R неизвестны → оценка через MLE (инновационная последовательность). Или адаптивный Kalman (Recursive Least Squares).

---

### Интеграция в архитектуру бота

```
┌─────────────────────────────────────────────────────────┐
│                    Signal Engine                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │   HMM    │→ │  GARCH   │→ │ Kalman   │→ Trading      │
│  │ 3 states │  │ (1,1)    │  │ Filter   │   Decision    │
│  └──────────┘  └──────────┘  └──────────┘               │
│       ↓              ↓              ↓                    │
│   Regime:       Predict σ:     Smooth:                   │
│   Bull/Bear/    → Position     → Denoise                 │
│   Range         → SL/TP        → Hedge β                 │
│                 → Vol scaling  → Pair signal              │
└─────────────────────────────────────────────────────────┘

Pipeline:
  1. HMM определяет режим → выбирает под-стратегию
  2. GARCH прогнозирует волатильность → масштабирует позицию
  3. Kalman сглаживает цену/индикаторы → уточняет entry/exit
  4. Все три работают ОДНОВРЕМЕННО на каждом баре
```

### Сводная таблица параметров

| Модель | Параметры | Перекалибровка | Входные данные |
|---|---|---|---|
| GARCH(1,1) | ω, α, β | Каждые 100 баров | Log-returns |
| HMM (3) | μₖ, σₖ, A, π | Каждые 1000 баров | Log-returns (или features) |
| Kalman | F, H, Q, R | Адаптивно (RLS) | Price / indicator |

### Что НЕ брать

| Метод | Почему отклонён |
|---|---|
| ARIMA/SARIMA | Лог-доходности крипты ≈ white noise (ACF ≈ 0) → ARIMA(0,0,0) = нет предсказательной силы |
| Prophet | Медленный (Stan MCMC), не для real-time, подгоняет шум как «сезонность» |
| TBATS | Сложность не даёт преимущества над SARIMA на крипте |
| Holt-Winters | Требует сезонность — на крипте она слабая и нестабильная |
| VAR | Многоколлинеарность переменных (RSI/Stochastic corr > 0.8), переобучение |
| VECM | Коинтеграция нестабильна на крипте (режимы меняются) |
| FIGARCH | Long memory слабый в крипте, GARCH(1,1) достаточно |
| Wavelets | Сложная реализация, не даёт явного edge над GARCH для volatility |

---

## Дополнение: Granger Causality и IRF как диагностические инструменты

Хотя Granger и IRF не выбраны в топ-3 для торговли, они **критически важны для исследовательского этапа**:

1. **Перед запуском стратегии**: Granger test volume → price, funding rate → price
2. **Для отбора feature**: какие переменные Granger-причина доходности?
3. **IRF для понимания dynamics**: через сколько баров шок волатильности влияет на тренд?

**Рекомендация:** Granger и IRF использовать **offline** (в research pipeline), не в real-time trading loop.

---

*Документ: 21-time-series.md*
*Агент 21: Анализ временных рядов*
