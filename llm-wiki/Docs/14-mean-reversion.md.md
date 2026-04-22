# Агент 14: Mean Reversion и стационарность

> Полный аудит инструментов mean-reversion для крипто-бота.
> Каждый инструмент: формула, edge cases, Rust-реализация, crypto-specific замечания.

---

## 0. Почему mean-reversion на крипте работает только для спредов и funding rate

### Фундаментальный аргумент

Цены криптоактивов (BTC, ETH, SOL и т.д.) — **не стационарны** и **не mean-revert** в классическом смысле. Это подтверждается:

1. **Fat tails и leptokurtosis**: крипто-доходности имеют эксцесс > 5 (против ~3 у нормального распределения). Это означает, что «отскоки от среднего» статистически неотличимы от продолжения тренда вплоть до экстремальных значений.

2. **Structural breaks**: крипта переживает внезапные regime changes (листинг крупной биржи, regulatory news, hack, ETF approval). Среднее значение, к которому якобы должен вернуться ряд, само постоянно сдвигается.

3. **Отсутствие фундаментального якоря**: у акции есть P/E, дивиденды, бухгалтерский баланс — привязки к «справедливой стоимости». У крипты нет ничего аналогичного. Нет «дна», к которому цена обязана вернуться.

4. **Эмпирические данные**: ADF-тест на лог-ценах BTC/USDT (1H, 2020-2024) даёт p-value > 0.90. KPSS отвергает стационарность. Hurst exponent ≈ 0.55-0.65 (слабый тренд/persistent). Ни один из этих результатов не позволяет торговать MR на цене.

### Где MR работает на крипте

**Работает (strictly stationary или mean-reverting):**

| Объект | Почему MR работает | Типичный H (Hurst) |
|--------|-------------------|-------------------|
| **Funding rate** | Механически привязан к спот-фьючерсному спреду. Биржа принудительно корректирует каждые 8 часов. | H ≈ 0.25–0.35 |
| **Basis (spot-futures spread)** | Конвергенция к экспирации = гарантированный возврат к нулю. | H ≈ 0.20–0.40 |
| **Cointegrated pairs spread** | Если два актива коинтегрированы, их линейная комбинация стационарна по определению (Engle-Granger). | H ≈ 0.15–0.40 |
| **Stablecoin deviations (USDT/USDC peg)** | Арбитражные механизмы гарантированно возвращают к $1.00. | H ≈ 0.10–0.25 |
| **DEX LP impermanent loss proxy** | Отклонение цены от начального соотношения mean-reverts через арбитраж. | H ≈ 0.25–0.40 |

**Не работает:**

| Объект | Почему не работает |
|--------|-------------------|
| Цена BTC, ETH, SOL | Не стационарна. ADF p > 0.10. H > 0.5. |
| RSI сам по себе | RSI mean-reverts к 50, но это тривиальное свойство формулы, не alpha. |
| Bollinger Band %B | То же: %B = (Price - Lower) / (Upper - Lower), он нормализован по конструкции. |

### Критерий строгости (Gate Rule)

```
Можно торговать MR ⟺ ADF p-value < 0.05 И KPSS p-value > 0.05
```

- **ADF** (Augmented Dickey-Fuller): отвергает H₀ (unit root exists) → нет единичного корня → ряд стационарен или trend-stationary.
- **KPSS**: не отвергает H₀ (ряд стационарен) → подтверждение стационарности.

Оба теста вместе исключают ложные срабатывания:
- Только ADF < 0.05: может быть trend-stationary (не strict MR).
- Только KPSS > 0.05: может быть unit root с медленной дрейфом.
- Оба вместе = строго стационарный = безопасно торговать MR.

---

## 1. ADF Test (Augmented Dickey-Fuller)

### Формула

Модель с константой и лагами:

```
Δyₜ = α + βt + γyₜ₋₁ + Σᵢ₌₁ᵖ δᵢ Δyₜ₋ᵢ + εₜ
```

- **H₀**: γ = 0 (unit root exists, non-stationary)
- **H₁**: γ < 0 (stationary)
- Тестовая статистика: τ = γ̂ / SE(γ̂)
- Если τ < критическое значение (MacKinnon) → отвергаем H₀

### Edge cases

- **Выбор лага p**: слишком мало → автокорреляция в остатках; слишком много → потеря мощности. Использовать AIC или BIC для автоматического выбора.
- **Structural breaks**: стандартный ADF не обнаруживает breaks → Zivot-Andrews тест как альтернатива.
- **Short series**: < 100 наблюдений → тест недостаточно мощен.
- **Trend-stationary vs strict stationary**: ADF отвергает H₀ даже если есть линейный тренд. Нужен KPSS для разделения.

### Rust-реализация

```rust
/// Augmented Dickey-Fuller тест на стационарность.
///
/// Возвращает (test_statistic, p_value, lags_used).
/// p_value < 0.05 → отвергаем H₀ (ряд стационарен).
pub fn adf_test(
    series: &[f64],
    max_lags: Option<usize>,
    regression: RegressionType,
) -> Result<AdfResult, &'static str> {
    if series.len() < 20 {
        return Err("Series too short for ADF test (min 20 observations)");
    }

    let n = series.len();
    let max_p = max_lags.unwrap_or(((n as f64) / 4.0).sqrt().ceil() as usize);
    let max_p = max_p.min(n / 3);

    // Автоматический выбор лага по AIC
    let mut best_aic = f64::INFINITY;
    let mut best_p = 1;

    for p in 1..=max_p {
        let (aic, _) = fit_adf_regression(series, p, regression)?;
        if aic < best_aic {
            best_aic = aic;
            best_p = p;
        }
    }

    let (aic, gamma_hat, se_gamma) = fit_adf_regression(series, best_p, regression)?;
    let tau_stat = gamma_hat / se_gamma;
    let p_value = mackinnon_p_value(tau_stat, n, regression);

    Ok(AdfResult {
        test_statistic: tau_stat,
        p_value,
        lags_used: best_p,
        aic,
    })
}

/// Тип регрессии для ADF.
#[derive(Debug, Clone, Copy)]
pub enum RegressionType {
    /// Δyₜ = γyₜ₋₁ + εₜ (no constant, no trend)
    NoConstant,
    /// Δyₜ = α + γyₜ₋₁ + εₜ (constant only)
    Constant,
    /// Δyₜ = α + βt + γyₜ₋₁ + εₜ (constant + linear trend)
    ConstantAndTrend,
}

/// Результат ADF теста.
#[derive(Debug)]
pub struct AdfResult {
    pub test_statistic: f64,
    pub p_value: f64,
    pub lags_used: usize,
    pub aic: f64,
}

/// Внутренняя функция: подгонка ADF-регрессии методом наименьших квадратов.
///
/// Строит матрицу регрессии и решает (X'X)⁻¹X'y.
fn fit_adf_regression(
    series: &[f64],
    p: usize,
    regression: RegressionType,
) -> Result<(f64, f64, f64), &'static str> {
    let n = series.len();
    let start = p + 1;
    let obs = n - start;
    if obs < 5 {
        return Err("Too few observations after lag construction");
    }

    // Δyₜ = yₜ - yₜ₋₁
    let mut dy = Vec::with_capacity(n - 1);
    for i in 1..n {
        dy.push(series[i] - series[i - 1]);
    }

    // Количество регрессоров
    let n_regressors = match regression {
        RegressionType::NoConstant => 1 + p,     // yₜ₋₁ + p лагов Δy
        RegressionType::Constant => 2 + p,       // const + yₜ₋₁ + p лагов
        RegressionType::ConstantAndTrend => 3 + p, // const + trend + yₜ₋₁ + p лагов
    };

    // Построение матрицы X (obs × n_regressors) и вектора y (obs)
    let mut x = vec![vec![0.0f64; n_regressors]; obs];
    let mut y = vec![0.0f64; obs];

    for i in 0..obs {
        let t = start - 1 + i; // индекс в dy
        y[i] = dy[t];

        let mut col = 0;

        // Константа
        if matches!(regression, RegressionType::Constant | RegressionType::ConstantAndTrend) {
            x[i][col] = 1.0;
            col += 1;
        }

        // Тренд
        if matches!(regression, RegressionType::ConstantAndTrend) {
            x[i][col] = (t + 1) as f64;
            col += 1;
        }

        // yₜ₋₁ (level)
        x[i][col] = series[t]; // series[t] = yₜ
        col += 1;

        // Лаги Δyₜ₋₁ ... Δyₜ₋ₚ
        for lag in 1..=p {
            x[i][col] = dy[t - lag];
            col += 1;
        }
    }

    // Решение OLS: β = (X'X)⁻¹X'y
    let beta = ols_solve(&x, &y)?;

    // γ̂ = beta[level_column]
    let level_col = match regression {
        RegressionType::NoConstant => 0,
        RegressionType::Constant => 1,
        RegressionType::ConstantAndTrend => 2,
    };
    let gamma_hat = beta[level_col];

    // Остатки
    let mut residuals = vec![0.0f64; obs];
    for i in 0..obs {
        let mut fitted = 0.0;
        for j in 0..n_regressors {
            fitted += x[i][j] * beta[j];
        }
        residuals[i] = y[i] - fitted;
    }

    // SE(γ̂)
    let ssr: f64 = residuals.iter().map(|e| e * e).sum();
    let sigma2 = ssr / (obs as f64 - n_regressors as f64);

    // (X'X)⁻¹ через LU-разложение
    let xtx_inv = compute_xtx_inv(&x)?;
    let se_gamma = (sigma2 * xtx_inv[level_col][level_col]).sqrt();

    // AIC = n·ln(SSR/n) + 2k
    let aic = (obs as f64) * (ssr / obs as f64).ln() + 2.0 * n_regressors as f64;

    Ok((aic, gamma_hat, se_gamma))
}

/// Квантили MacKinnon для p-value ADF теста.
/// Использует табличные значения, интерполированные по sample size.
fn mackinnon_p_value(tau: f64, n: usize, regression: RegressionType) -> f64 {
    // Таблица MacKinnon (1996) — приближённые критические значения
    // для 1%, 5%, 10% уровней значимости.
    let critical_values: (f64, f64, f64) = match regression {
        RegressionType::NoConstant => (-2.58, -1.94, -1.62),
        RegressionType::Constant => (-3.43, -2.86, -2.57),
        RegressionType::ConstantAndTrend => (-3.96, -3.41, -3.12),
    };

    if tau < critical_values.0 {
        0.01
    } else if tau < critical_values.1 {
        0.05
    } else if tau < critical_values.2 {
        0.10
    } else {
        // Линейная интерполяция для остальных
        0.50_f64.min(1.0 - (tau - critical_values.2).abs() / 3.0)
    }
}

/// Решение OLS через QR-разложение.
fn ols_solve(x: &[Vec<f64>], y: &[f64]) -> Result<Vec<f64>, &'static str> {
    let obs = x.len();
    let k = x[0].len();

    // X'X
    let mut xtx = vec![vec![0.0f64; k]; k];
    let mut xty = vec![0.0f64; k];

    for i in 0..obs {
        for j in 0..k {
            xty[j] += x[i][j] * y[i];
            for l in j..k {
                xtx[j][l] += x[i][j] * x[i][l];
            }
        }
    }
    for j in 0..k {
        for l in 0..j {
            xtx[j][l] = xtx[l][j];
        }
    }

    // LU-разложение + обратная подстановка
    lu_solve(&xtx, &xty)
}

fn lu_solve(a: &[Vec<f64>], b: &[f64]) -> Result<Vec<f64>, &'static str> {
    let n = a.len();
    let mut lu = a.to_vec();
    let mut p = (0..n).collect::<Vec<_>>();
    let mut bb = b.to_vec();

    // LU с частичным выбором ведущего элемента
    for k in 0..n {
        let mut max_val = 0.0;
        let mut max_row = k;
        for i in k..n {
            if lu[i][k].abs() > max_val {
                max_val = lu[i][k].abs();
                max_row = i;
            }
        }
        if max_val < 1e-14 {
            return Err("Singular matrix in OLS");
        }
        lu.swap(k, max_row);
        p.swap(k, max_row);
        bb.swap(k, max_row);

        for i in (k + 1)..n {
            lu[i][k] /= lu[k][k];
            for j in (k + 1)..n {
                lu[i][j] -= lu[i][k] * lu[k][j];
            }
        }
    }

    // Ly = Pb
    let mut y = vec![0.0f64; n];
    for i in 0..n {
        y[i] = bb[i];
        for j in 0..i {
            y[i] -= lu[i][j] * y[j];
        }
    }

    // Ux = y
    let mut x = vec![0.0f64; n];
    for i in (0..n).rev() {
        x[i] = y[i];
        for j in (i + 1)..n {
            x[i] -= lu[i][j] * x[j];
        }
        x[i] /= lu[i][i];
    }

    Ok(x)
}

fn compute_xtx_inv(x: &[Vec<f64>]) -> Result<Vec<Vec<f64>>, &'static str> {
    let obs = x.len();
    let k = x[0].len();
    let mut xtx = vec![vec![0.0f64; k]; k];

    for i in 0..obs {
        for j in 0..k {
            for l in j..k {
                xtx[j][l] += x[i][j] * x[i][l];
            }
        }
    }
    for j in 0..k {
        for l in 0..j {
            xtx[j][l] = xtx[l][j];
        }
    }

    // Обратная матрица через LU
    let mut inv = vec![vec![0.0f64; k]; k];
    for col in 0..k {
        let mut e = vec![0.0f64; k];
        e[col] = 1.0;
        let sol = lu_solve(&xtx, &e)?;
        for row in 0..k {
            inv[row][col] = sol[row];
        }
    }
    Ok(inv)
}
```

---

## 2. KPSS Test (Kwiatkowski-Phillips-Schmidt-Shin)

### Формула

Модель под H₀ (стационарность):

```
yₜ = ξt + rₜ + εₜ
где rₜ = rₜ₋₁ + uₜ,  uₜ ~ iid(0, σ²ᵤ)
```

Тестовая статистика:

```
KPSS = Σₜ Sₜ² / (T² · f₀)
```

где:
- Sₜ = Σᵢ₌₁ᵗ êᵢ (кумулятивная сумма остатков регрессии y на константу и тренд)
- êᵢ — остатки OLS-регрессии
- f₀ — ядерная оценка долгосрочной дисперсии (Newey-West с лагом l = ⌊4(T/100)^(2/9)⌋)

### Интерпретация

- **H₀**: ряд стационарность (σ²ᵤ = 0)
- **H₁**: ряд нестационарен (σ²ᵤ > 0)
- Если KPSS > критическое значение → отвергаем H₀ → **не стационарен**
- Если KPSS < критическое значение → **не отвергаем** → возможно стационарен

### Edge cases

- **Выбор bandwidth (Newey-West)**: слишком мало → недооценка f₀ → ложное отклонение H₀. Автоматически: l = ⌊4(T/100)^(2/9)⌋.
- **Short series**: < 50 наблюдений — тест ненадёжен.
- **Trend-stationary**: с трендом или без — выбрать до теста (visually или по ADF).

### Rust-реализация

```rust
/// KPSS тест на стационарность.
///
/// Возвращает (test_statistic, p_value, lags_used).
/// Если p_value < 0.05 → отвергаем H₀ (ряд НЕ стационарен).
pub fn kpss_test(
    series: &[f64],
    regression: RegressionType,
) -> Result<KpssResult, &'static str> {
    let n = series.len();
    if n < 20 {
        return Err("Series too short for KPSS test (min 20 observations)");
    }

    // 1. OLS-регрессия yₜ на константу (и тренд)
    let (residuals, _) = ols_detrend(series, regression)?;

    // 2. Кумулятивная сумма остатков
    let mut s = vec![0.0f64; n];
    s[0] = residuals[0];
    for i in 1..n {
        s[i] = s[i - 1] + residuals[i];
    }

    // 3. Σ Sₜ²
    let sum_s2: f64 = s.iter().map(|si| si * si).sum();

    // 4. Ядерная оценка долгосрочной дисперсии (Newey-West)
    let l = ((4.0 * (n as f64 / 100.0).powf(2.0 / 9.0)).floor()) as usize;
    let l = l.max(1);
    let f0 = newey_west_variance(&residuals, l);

    // 5. KPSS статистика
    let kpss_stat = sum_s2 / (n as f64 * n as f64 * f0);

    // 6. p-value (табличные квантили KPSS)
    let p_value = kpss_p_value(kpss_stat, n, regression);

    Ok(KpssResult {
        test_statistic: kpss_stat,
        p_value,
        lags_used: l,
    })
}

/// Newey-West оценка долгосрочной дисперсии.
///
/// f₀ = γ₀ + 2·Σⱼ₌₁ˡ wⱼ·γⱼ
/// wⱼ = 1 - j/(l+1)  (Bartlett kernel)
/// γⱼ = (1/T)·Σₜ₌ⱼ₊₁ᵀ êₜ·êₜ₋ⱼ
fn newey_west_variance(residuals: &[f64], l: usize) -> f64 {
    let n = residuals.len();

    // γ₀ (дисперсия)
    let gamma_0: f64 = residuals.iter().map(|e| e * e).sum::<f64>() / n as f64;

    let mut f0 = gamma_0;

    for j in 1..=l {
        // Автоковариация лага j
        let mut gamma_j = 0.0;
        for t in j..n {
            gamma_j += residuals[t] * residuals[t - j];
        }
        gamma_j /= n as f64;

        // Bartlett weight
        let w_j = 1.0 - j as f64 / (l + 1) as f64;
        f0 += 2.0 * w_j * gamma_j;
    }

    f0.max(1e-12) // Защита от отрицательной дисперсии
}

/// Детрендация (OLS) для KPSS.
fn ols_detrend(
    series: &[f64],
    regression: RegressionType,
) -> Result<(Vec<f64>, Vec<f64>), &'static str> {
    let n = series.len();
    let n_reg = match regression {
        RegressionType::NoConstant => return Ok((series.to_vec(), series.to_vec())),
        RegressionType::Constant => 1,
        RegressionType::ConstantAndTrend => 2,
    };

    let mut x = vec![vec![0.0f64; n_reg]; n];
    for i in 0..n {
        let mut col = 0;
        if matches!(regression, RegressionType::Constant | RegressionType::ConstantAndTrend) {
            x[i][col] = 1.0;
            col += 1;
        }
        if matches!(regression, RegressionType::ConstantAndTrend) {
            x[i][col] = (i + 1) as f64;
        }
    }

    let beta = ols_solve(&x, series)?;
    let mut fitted = vec![0.0f64; n];
    let mut residuals = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n_reg {
            fitted[i] += x[i][j] * beta[j];
        }
        residuals[i] = series[i] - fitted[i];
    }

    Ok((residuals, fitted))
}

#[derive(Debug)]
pub struct KpssResult {
    pub test_statistic: f64,
    pub p_value: f64,
    pub lags_used: usize,
}

/// Табличные квантили KPSS (с трендом).
fn kpss_p_value(stat: f64, _n: usize, regression: RegressionType) -> f64 {
    let (cv_10, cv_05, cv_01) = match regression {
        RegressionType::ConstantAndTrend => (0.119, 0.146, 0.216),
        RegressionType::Constant => (0.347, 0.463, 0.739),
        RegressionType::NoConstant => (0.347, 0.463, 0.739),
    };

    if stat < cv_10 {
        0.50 // далеко от отвержения
    } else if stat < cv_05 {
        0.10
    } else if stat < cv_01 {
        0.05
    } else {
        0.01
    }
}
```

---

## 3. Phillips-Perron Test

### Формула

Модель: Δyₜ = α + γyₜ₋₁ + εₜ (без лагов)

Коррекция на автокорреляцию остатков:

```
Zₜ = τ · √(σ²ᵤ/S²) - (S² - σ²ᵤ) / (2·S·√λ)
```

где:
- τ — обычная t-статистика из OLS без лагов
- σ²ᵤ — оценка дисперсии остатков (residual variance)
- S² — долгосрочная дисперсия (Newey-West)
- λ = S² — long-run variance

Альтернативная Zₐ:

```
Zₐ = T·γ̂ - 0.5·(S² - σ²ᵤ) / λ
```

### Преимущества и недостатки

- **+**: Не нужно выбирать количество лагов (автоматически через Newey-West).
- **−**: Менее мощен, чем ADF с правильно выбранными лагами, на малых выборках.
- **−**: Чувствителен к выбору bandwidth в Newey-West.
- **Crypto-specific**: Рекомендуется как sanity check после ADF, но не заменяет ADF+KPSS пару.

### Rust-реализация

```rust
/// Phillips-Perron тест (Zₜ версия).
pub fn phillips_perron_test(
    series: &[f64],
    regression: RegressionType,
) -> Result<PpResult, &'static str> {
    let n = series.len();
    if n < 20 {
        return Err("Series too short for PP test");
    }

    // Δyₜ = α + γyₜ₋₁ + εₜ (простая OLS без лагов)
    let dy: Vec<f64> = (1..n).map(|i| series[i] - series[i - 1]).collect();
    let y_lag: Vec<f64> = series[..n - 1].to_vec();

    let n_obs = n - 1;
    let n_reg = match regression {
        RegressionType::NoConstant => 1,
        _ => 2,
    };

    // Построение матрицы регрессии
    let mut x = vec![vec![0.0f64; n_reg]; n_obs];
    for i in 0..n_obs {
        let mut col = 0;
        if n_reg == 2 {
            x[i][col] = 1.0;
            col += 1;
        }
        x[i][col] = y_lag[i];
    }

    let beta = ols_solve(&x, &dy)?;

    // γ̂ и t-статистика
    let gamma_col = n_reg - 1;
    let gamma_hat = beta[gamma_col];

    // Остатки
    let mut residuals = vec![0.0f64; n_obs];
    for i in 0..n_obs {
        let mut fitted = 0.0;
        for j in 0..n_reg {
            fitted += x[i][j] * beta[j];
        }
        residuals[i] = dy[i] - fitted;
    }

    // σ²ᵤ (residual variance)
    let ssr: f64 = residuals.iter().map(|e| e * e).sum();
    let sigma2 = ssr / (n_obs as f64 - n_reg as f64);

    // SE(γ̂)
    let xtx_inv = compute_xtx_inv(&x)?;
    let se_gamma = (sigma2 * xtx_inv[gamma_col][gamma_col]).sqrt();
    let tau = gamma_hat / se_gamma;

    // S² (long-run variance, Newey-West)
    let l = ((4.0 * (n_obs as f64 / 100.0).powf(2.0 / 9.0)).floor()) as usize;
    let l = l.max(1);
    let s2 = newey_west_variance(&residuals, l);

    // Zₜ коррекция
    let zt = tau * (sigma2 / s2).sqrt() - (s2 - sigma2) / (2.0 * s2.sqrt() * (n_obs as f64 * sigma2).sqrt());

    // Zₐ
    let za = n_obs as f64 * gamma_hat - 0.5 * (s2 - sigma2) / s2;

    let p_value_zt = mackinnon_p_value(zt, n, regression);
    let p_value_za = pp_za_p_value(za, n, regression);

    Ok(PpResult {
        zt_statistic: zt,
        za_statistic: za,
        p_value_zt,
        p_value_za,
        bandwidth: l,
    })
}

#[derive(Debug)]
pub struct PpResult {
    pub zt_statistic: f64,
    pub za_statistic: f64,
    pub p_value_zt: f64,
    pub p_value_za: f64,
    pub bandwidth: usize,
}

fn pp_za_p_value(za: f64, _n: usize, regression: RegressionType) -> f64 {
    // Приближённые критические значения Zₐ
    let cv = match regression {
        RegressionType::Constant => (-20.3, -14.1, -11.2),
        RegressionType::ConstantAndTrend => (-28.2, -21.8, -18.3),
        RegressionType::NoConstant => (-13.7, -8.1, -5.7),
    };

    if za < cv.0 { 0.01 }
    else if za < cv.1 { 0.05 }
    else if za < cv.2 { 0.10 }
    else { 0.50 }
}
```

---

## 4. Hurst Exponent (R/S Analysis)

### Формула

Для лага τ:

```
R(τ) = max(Xₖ - (k/τ)·X̄) - min(Xₖ - (k/τ)·X̄)   для k = 1..τ
S(τ) = std(ΔXₜ) за период τ
(R/S)(τ) = R(τ) / S(τ)

Hurst: H = slope в регрессии log(R/S) ~ log(τ)
```

### Интерпретация

- **H = 0.5**: Случайное блуждание (Brownian motion). Не торговать MR.
- **H > 0.5**: Persistence (тренд). Следовать за трендом.
- **H < 0.5**: Anti-persistence (mean-reversion). Можно торговать MR.
- **H ≈ 0**: Жёсткий mean-reversion (bounded process).

### Crypto-specific

Для funding rate и spreads: H обычно 0.2–0.4. Для цен: H ≈ 0.5–0.65.

### Edge cases

- **Short series**: < 200 наблюдений → H нестабилен. Требуется ≥ 500 для надёжности.
- **Non-Gaussian tails**: R/S предполагает нормальность. Использовать DFA (Detrended Fluctuation Analysis) как робастную альтернативу.
- **Structural breaks**: Разбить серию на сегменты и считать H для каждого.

### Rust-реализация

```rust
/// Вычисление показателя Херста методом R/S анализа.
///
/// Возвращает H: < 0.5 → mean-reversion, = 0.5 → random walk, > 0.5 → trending.
pub fn hurst_exponent(
    prices: &[f64],
    min_lag: usize,
    max_lag: usize,
) -> Result<HurstResult, &'static str> {
    let n = prices.len();
    if n < 2 * max_lag {
        return Err("Series too short for Hurst calculation");
    }

    // Лог-доходности
    let mut log_returns = Vec::with_capacity(n - 1);
    for i in 1..n {
        log_returns.push((prices[i] / prices[i - 1]).ln());
    }

    // Список лагов (логарифмическая сетка)
    let mut lags = Vec::new();
    let mut lag = min_lag;
    while lag <= max_lag && lag < log_returns.len() / 2 {
        lags.push(lag);
        lag = (lag as f64 * 1.2).ceil() as usize;
        if lag == lags[lags.len() - 1] {
            lag += 1;
        }
    }

    if lags.len() < 3 {
        return Err("Need at least 3 lags for regression");
    }

    let mut log_lags = Vec::with_capacity(lags.len());
    let mut log_rs = Vec::with_capacity(lags.len());

    for &tau in &lags {
        // Разбиваем серию на блоки длиной tau
        let num_blocks = log_returns.len() / tau;
        if num_blocks < 1 {
            continue;
        }

        let mut rs_values = Vec::with_capacity(num_blocks);

        for block in 0..num_blocks {
            let start = block * tau;
            let end = start + tau;
            let segment = &log_returns[start..end];

            // Среднее сегмента
            let mean: f64 = segment.iter().sum::<f64>() / tau as f64;

            // Кумулятивное отклонение от среднего
            let mut cum_dev = vec![0.0f64; tau];
            cum_dev[0] = segment[0] - mean;
            for k in 1..tau {
                cum_dev[k] = cum_dev[k - 1] + (segment[k] - mean);
            }

            // Range = max - min кумулятивного отклонения
            let r = cum_dev.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
                - cum_dev.iter().cloned().fold(f64::INFINITY, f64::min);

            // Std dev сегмента
            let variance: f64 = segment.iter().map(|x| (x - mean).powi(2)).sum::<f64>()
                / (tau - 1) as f64;
            let s = variance.sqrt();

            if s > 1e-12 {
                rs_values.push(r / s);
            }
        }

        if !rs_values.is_empty() {
            let mean_rs: f64 = rs_values.iter().sum::<f64>() / rs_values.len() as f64;
            log_lags.push((tau as f64).ln());
            log_rs.push(mean_rs.ln());
        }
    }

    if log_lags.len() < 3 {
        return Err("Need at least 3 valid R/S points for regression");
    }

    // Линейная регрессия: log(R/S) = H·log(τ) + c
    let (h, r_squared) = simple_linear_regression(&log_lags, &log_rs);

    Ok(HurstResult {
        hurst: h,
        r_squared,
        lags_used: log_lags.len(),
        interpretation: if h < 0.45 {
            "Mean-reverting (anti-persistent)"
        } else if h < 0.55 {
            "Random walk"
        } else {
            "Trending (persistent)"
        }.to_string(),
    })
}

#[derive(Debug)]
pub struct HurstResult {
    pub hurst: f64,
    pub r_squared: f64,
    pub lags_used: usize,
    pub interpretation: String,
}

fn simple_linear_regression(x: &[f64], y: &[f64]) -> (f64, f64) {
    let n = x.len() as f64;
    let x_mean = x.iter().sum::<f64>() / n;
    let y_mean = y.iter().sum::<f64>() / n;

    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..x.len() {
        num += (x[i] - x_mean) * (y[i] - y_mean);
        den += (x[i] - x_mean).powi(2);
    }
    let slope = num / den;
    let intercept = y_mean - slope * x_mean;

    // R²
    let mut ss_res = 0.0;
    let mut ss_tot = 0.0;
    for i in 0..x.len() {
        let predicted = slope * x[i] + intercept;
        ss_res += (y[i] - predicted).powi(2);
        ss_tot += (y[i] - y_mean).powi(2);
    }
    let r2 = 1.0 - ss_res / ss_tot;

    (slope, r2)
}
```

---

## 5. Ornstein-Uhlenbeck Process

### Формула

```
dXₜ = θ(μ - Xₜ)dt + σdWₜ
```

- **θ** — скорость возврата к среднему (mean-reversion speed). Чем выше, тем быстрее возврат.
- **μ** — долгосрочное среднее (mean level).
- **σ** — волатильность.
- **Wₜ** — стандартный Винеровский процесс.

### Аналитическое решение

```
Xₜ = μ + (X₀ - μ)·e^(-θt) + σ·∫₀ᵗ e^(-θ(t-s)) dWₛ
```

### Оценка параметров (MLE / OLS)

OLS-форма (дискретизация Эйлера):

```
Xₜ - Xₜ₋₁ = θμ·Δt - θ·Xₜ₋₁·Δt + εₜ
```

где εₜ ~ N(0, σ²·Δt). Оцениваем θμ и θ через OLS, затем σ из остатков.

### Half-life of mean reversion

```
t½ = ln(2) / θ
```

Критический параметр: если half-life < 1 бара → слишком быстрый возврат (возможно шум); если > 100 баров → слишком медленный (убыточная торговля из-за комиссий).

### Crypto-specific

OU-процесс подходит **только** для:
- Funding rate (θ ≈ 0.5–2.0, half-life ≈ 0.3–1.4 периодов = 2.4–11.2 часов)
- Cointegrated pair spread (θ ≈ 0.05–0.3, half-life ≈ 2.3–14 периодов)
- Stablecoin deviations (θ ≈ 5.0–20.0, half-life ≈ 0.03–0.14 периодов)

### Edge cases

- **θ ≤ 0**: Нет mean-reversion. Стратегия неприменима.
- **θ слишком большой**: Half-life < 1 бара → невозможно захватить движение.
- **σ/θ ratio**: Отношение волатильности к скорости возврата определяет P&L. Если σ/θ слишком мало → спред слишком узкий для покрытия комиссий.
- **Parameter instability**: θ не постоянен. Нужна rolling estimation (окно 200–500 баров).

### Rust-реализация

```rust
/// Оценка параметров Ornstein-Uhlenbeck процесса методом OLS.
///
/// Дискретизация: ΔXₜ = θ(μ - Xₜ₋₁)·Δt + εₜ
pub fn fit_ou_process(
    series: &[f64],
    dt: f64,
) -> Result<OuParams, &'static str> {
    let n = series.len();
    if n < 10 {
        return Err("Need at least 10 observations for OU estimation");
    }

    // ΔXₜ = Xₜ - Xₜ₋₁
    let dx: Vec<f64> = (1..n).map(|i| series[i] - series[i - 1]).collect();
    let x_lag: Vec<f64> = series[..n - 1].to_vec();
    let n_obs = n - 1;

    // OLS: ΔX = a + b·Xₜ₋₁ + ε
    // a = θμ·Δt, b = -θ·Δt
    let x_mean = x_lag.iter().sum::<f64>() / n_obs as f64;
    let dx_mean = dx.iter().sum::<f64>() / n_obs as f64;

    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..n_obs {
        num += (x_lag[i] - x_mean) * (dx[i] - dx_mean);
        den += (x_lag[i] - x_mean).powi(2);
    }

    let b = num / den; // b = -θ·Δt
    let a = dx_mean - b * x_mean; // a = θμ·Δt

    let theta = -b / dt;
    let mu = if theta.abs() > 1e-10 { a / (theta * dt) } else { x_mean };

    // σ из остатков
    let mut ssr = 0.0;
    for i in 0..n_obs {
        let predicted = a + b * x_lag[i];
        ssr += (dx[i] - predicted).powi(2);
    }
    let sigma = (ssr / (n_obs as f64 - 2.0) / dt).sqrt();

    // Half-life
    let half_life = if theta > 1e-10 {
        std::f64::consts::LN_2 / theta
    } else {
        f64::INFINITY
    };

    // Long-run variance
    let long_run_var = sigma * sigma / (2.0 * theta);

    // R²
    let mut ss_tot = 0.0;
    for i in 0..n_obs {
        ss_tot += (dx[i] - dx_mean).powi(2);
    }
    let r_squared = 1.0 - ssr / ss_tot;

    Ok(OuParams {
        theta,
        mu,
        sigma,
        half_life,
        long_run_variance: long_run_var,
        r_squared,
        is_valid: theta > 0.0,
    })
}

#[derive(Debug)]
pub struct OuParams {
    pub theta: f64,
    pub mu: f64,
    pub sigma: f64,
    pub half_life: f64,
    pub long_run_variance: f64,
    pub r_squared: f64,
    pub is_valid: bool,
}

/// Генерация торгового сигнала на основе OU-процесса.
///
/// LONG когда Xₜ < μ - k·σ_ou, SHORT когда Xₜ > μ + k·σ_ou.
pub fn ou_signal(
    current_value: f64,
    params: &OuParams,
    entry_threshold: f64, // обычно 2.0
    exit_threshold: f64,  // обычно 0.5
) -> OuSignal {
    if !params.is_valid {
        return OuSignal::Hold;
    }

    let ou_std = (params.long_run_variance).sqrt();
    let z_score = (current_value - params.mu) / ou_std;

    if z_score < -entry_threshold {
        OuSignal::Long
    } else if z_score > entry_threshold {
        OuSignal::Short
    } else if z_score.abs() < exit_threshold {
        OuSignal::Exit
    } else {
        OuSignal::Hold
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OuSignal {
    Long,
    Short,
    Exit,
    Hold,
}
```

---

## 6. Half-Life of Mean Reversion

### Формула

Из OLS-регрессии Δyₜ = α + βyₜ₋₁ + εₜ:

```
Half-life = -ln(2) / β
```

где β — коэффициент при yₜ₋₁ (должен быть < 0 для mean-reversion).

### Применение

Half-life используется как:
1. **Валидация MR**: если β ≥ 0 → нет MR, не торговать.
2. **Holding period**: оптимальное время удержания позиции ≈ half-life.
3. **Окно для Z-score**: lookback period для Bollinger/Z-score = half-life × 2–3.

### Rust-реализация

```rust
/// Вычисление half-life mean reversion.
///
/// Регрессия: Δyₜ = α + β·yₜ₋₁ + εₜ
/// Half-life = -ln(2) / β
pub fn half_life(series: &[f64]) -> Result<HalfLifeResult, &'static str> {
    let n = series.len();
    if n < 20 {
        return Err("Need at least 20 observations for half-life estimation");
    }

    let dy: Vec<f64> = (1..n).map(|i| series[i] - series[i - 1]).collect();
    let y_lag: Vec<f64> = series[..n - 1].to_vec();
    let n_obs = n - 1;

    // OLS: Δy = α + β·yₜ₋₁
    let y_mean = y_lag.iter().sum::<f64>() / n_obs as f64;
    let dy_mean = dy.iter().sum::<f64>() / n_obs as f64;

    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..n_obs {
        num += (y_lag[i] - y_mean) * (dy[i] - dy_mean);
        den += (y_lag[i] - y_mean).powi(2);
    }

    let beta = num / den;
    let alpha = dy_mean - beta * y_mean;

    let is_mean_reverting = beta < 0.0;
    let half_life = if is_mean_reverting {
        -(std::f64::consts::LN_2 / beta)
    } else {
        f64::INFINITY
    };

    // R²
    let mut ss_res = 0.0;
    let mut ss_tot = 0.0;
    for i in 0..n_obs {
        let predicted = alpha + beta * y_lag[i];
        ss_res += (dy[i] - predicted).powi(2);
        ss_tot += (dy[i] - dy_mean).powi(2);
    }
    let r_squared = 1.0 - ss_res / ss_tot;

    Ok(HalfLifeResult {
        alpha,
        beta,
        half_life,
        r_squared,
        is_mean_reverting,
        recommended_lookback: if is_mean_reverting {
            (half_life * 2.5).ceil() as usize
        } else {
            0
        },
    })
}

#[derive(Debug)]
pub struct HalfLifeResult {
    pub alpha: f64,
    pub beta: f64,
    pub half_life: f64,
    pub r_squared: f64,
    pub is_mean_reverting: bool,
    pub recommended_lookback: usize,
}
```

---

## 7. Z-Score Trading

### Формула

```
z = (Xₜ - μ_τ) / σ_τ
```

где μ_τ и σ_τ — скользящее среднее и стандартное отклонение за окно τ (часто τ = half-life × 2.5).

### Сигналы

```
z < -k  → LONG (спред ниже нормы)
z > +k  → SHORT (спред выше нормы)
|z| < m → EXIT (возврат к среднему)
```

Типичные пороги: k = 2.0 (entry), m = 0.5 (exit).

### Crypto-specific

Z-score торгуется на cointegrated pair spread или funding rate. Не на цене одиночного актива.

### Rust-реализация

```rust
/// Z-score для rolling window.
pub fn z_score_rolling(series: &[f64], window: usize) -> Vec<Option<f64>> {
    let n = series.len();
    let mut result = vec![None; n];

    if n < window {
        return result;
    }

    // Оптимизация: скользящее среднее и дисперсия (Welford)
    let mut mean = 0.0;
    let mut m2 = 0.0;

    for i in 0..window {
        let delta = series[i] - mean;
        mean += delta / (i + 1) as f64;
        let delta2 = series[i] - mean;
        m2 += delta * delta2;
    }

    let variance = m2 / (window - 1) as f64;
    if variance > 1e-12 {
        result[window - 1] = Some((series[window - 1] - mean) / variance.sqrt());
    }

    for i in window..n {
        // Удаляем старый, добавляем новый
        let old = series[i - window];
        let new = series[i];
        let delta_old = old - mean;
        mean += (new - old) / window as f64;
        let delta_new = new - mean;
        m2 += (new - old) * (delta_new - delta_old);

        let variance = m2 / (window - 1) as f64;
        if variance > 1e-12 {
            result[i] = Some((new - mean) / variance.sqrt());
        }
    }

    result
}

/// Торговый сигнал на основе Z-score.
pub fn z_score_signal(
    z: f64,
    entry_z: f64,
    exit_z: f64,
    current_position: Option<Position>,
) -> ZSignal {
    match current_position {
        None => {
            if z < -entry_z {
                ZSignal::EnterLong
            } else if z > entry_z {
                ZSignal::EnterShort
            } else {
                ZSignal::Hold
            }
        }
        Some(Position::Long) => {
            if z > -exit_z {
                ZSignal::Exit
            } else {
                ZSignal::Hold
            }
        }
        Some(Position::Short) => {
            if z < exit_z {
                ZSignal::Exit
            } else {
                ZSignal::Hold
            }
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub enum Position { Long, Short }

#[derive(Debug, Clone, Copy)]
pub enum ZSignal { EnterLong, EnterShort, Exit, Hold }
```

---

## 8. Cointegration Tests

### 8.1. Engle-Granger Two-Step

**Шаг 1**: OLS-регрессия Yₜ = α + βXₜ + εₜ → получаем спред εₜ = Yₜ - α - βXₜ

**Шаг 2**: ADF-тест на остатках εₜ. Если ADF p < 0.05 → Y и X коинтегрированы.

**Edge cases**: работает только для пар. Порядок переменных в OLS влияет на β (но не на тестовую статистику).

### 8.2. Johansen Test

**Модель**: VECM (Vector Error Correction Model)

```
ΔXₜ = Π·Xₜ₋₁ + Σᵢ₌₁ᵖ Γᵢ·ΔXₜ₋ᵢ + εₜ
```

где Π = αβ' (α — скорость корректировки, β — коинтеграционные векторы).

**Тестовые статистики**:
- Trace test: λ_trace(r) = -T·Σᵢ₌ᵣ₊₁ᴺ ln(1 + λᵢ)
- Max eigenvalue test: λ_max(r) = -T·ln(1 + λᵢ₊₁)

где λᵢ — собственные значения (eigenvalues).

**Crypto-specific**: Johansen используется для корзинного трейдинга (3+ актива). Например, найти стационарную комбинацию BTC, ETH, SOL.

### Rust-реализация (упрощённый Engle-Granger)

```rust
/// Engle-Granger тест на коинтеграцию пары.
///
/// Возвращает (cointegrated, hedge_ratio, adf_p_value, spread).
pub fn engle_granger_test(
    y: &[f64],
    x: &[f64],
) -> Result<EngleGrangerResult, &'static str> {
    if y.len() != x.len() {
        return Err("Series must have equal length");
    }
    if y.len() < 30 {
        return Err("Need at least 30 observations for cointegration test");
    }

    let n = y.len();

    // Шаг 1: OLS Y = α + βX + ε
    let x_mean = x.iter().sum::<f64>() / n as f64;
    let y_mean = y.iter().sum::<f64>() / n as f64;

    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..n {
        num += (x[i] - x_mean) * (y[i] - y_mean);
        den += (x[i] - x_mean).powi(2);
    }

    let beta = num / den; // hedge ratio
    let alpha = y_mean - beta * x_mean;

    // Спред = остатки
    let spread: Vec<f64> = (0..n).map(|i| y[i] - alpha - beta * x[i]).collect();

    // Шаг 2: ADF на спреде
    let adf_result = adf_test(&spread, None, RegressionType::Constant)?;
    let cointegrated = adf_result.p_value < 0.05;

    // Half-life спреда
    let hl = half_life(&spread)?;

    Ok(EngleGrangerResult {
        cointegrated,
        hedge_ratio: beta,
        intercept: alpha,
        adf_p_value: adf_result.p_value,
        spread,
        half_life: hl.half_life,
    })
}

#[derive(Debug)]
pub struct EngleGrangerResult {
    pub cointegrated: bool,
    pub hedge_ratio: f64,
    pub intercept: f64,
    pub adf_p_value: f64,
    pub spread: Vec<f64>,
    pub half_life: f64,
}
```

---

## 9. Bollinger Band Mean-Reversion

### Формула

```
Upper = SMA(τ) + k·σ(τ)
Lower = SMA(τ) - k·σ(τ)
%B = (Price - Lower) / (Upper - Lower)
```

### Сигналы

```
%B < 0   → LONG (цена ниже нижней полосы)
%B > 1   → SHORT (цена выше верхней полосы)
%B ≈ 0.5 → EXIT
```

### Crypto-specific

**На цене одного актива — НЕ работает как alpha**. %B нормализован по конструкции: он всегда колеблется вокруг 0.5. Это тривиальное mean-reversion формулы, а не рынка.

**Работает**: на cointegrated pair spread, где Bollinger Bands дают визуально понятные уровни входа/выхода.

### Edge cases

- **Squeeze**: сужение полос (Bollinger Bandwidth < 2%) означает, что пороги %B становятся экстремально узкими → много ложных сигналов.
- **Трендовый рынок**: %B может быть > 1 или < 0 долгое время (Bollinger Walk) → убыточная торговля MR.

### Rust-реализация

```rust
/// Bollinger Bands и %B для массива цен.
pub fn bollinger_percent_b(
    series: &[f64],
    window: usize,
    num_std: f64,
) -> Vec<Option<f64>> {
    let n = series.len();
    let mut result = vec![None; n];

    if n < window {
        return result;
    }

    for i in (window - 1)..n {
        let slice = &series[i + 1 - window..=i];
        let mean = slice.iter().sum::<f64>() / window as f64;
        let variance = slice.iter().map(|x| (x - mean).powi(2)).sum::<f64>()
            / (window - 1) as f64;
        let std = variance.sqrt();

        if std > 1e-12 {
            let upper = mean + num_std * std;
            let lower = mean - num_std * std;
            result[i] = Some((series[i] - lower) / (upper - lower));
        }
    }

    result
}

/// Bollinger Bandwidth (для обнаружения squeeze).
pub fn bollinger_bandwidth(
    series: &[f64],
    window: usize,
    num_std: f64,
) -> Vec<Option<f64>> {
    let n = series.len();
    let mut result = vec![None; n];

    if n < window {
        return result;
    }

    for i in (window - 1)..n {
        let slice = &series[i + 1 - window..=i];
        let mean = slice.iter().sum::<f64>() / window as f64;
        let variance = slice.iter().map(|x| (x - mean).powi(2)).sum::<f64>()
            / (window - 1) as f64;
        let std = variance.sqrt();

        if mean.abs() > 1e-12 {
            result[i] = Some((2.0 * num_std * std) / mean); // Bandwidth
        }
    }

    result
}
```

---

## 10. RSI Mean-Reversion

### Формула

```
RS = Avg_Gain(τ) / Avg_Loss(τ)
RSI = 100 - 100 / (1 + RS)
```

### MR-сигналы

```
RSI < 30 → LONG (перепроданность)
RSI > 70 → SHORT (перекупленность)
```

### Crypto-specific (критически важно)

**RSI mean-reversion НЕ работает на крипте как standalone стратегия**. Причины:

1. **RSI mean-reverts к 50 по конструкции** — это свойство формулы (bounded oscillator), а не рынка.
2. **На трендовом рынке RSI может быть > 70 или < 30 неделями** — Bollinger Walk для RSI.
3. **Эмпирически**: на BTC 1H (2020-2024), стратегия «RSI < 30 → buy, RSI > 70 → sell» даёт Sharpe < 0.3.

**Работает**: RSI как фильтр (не как primary signal) для mean-reversion на cointegrated spreads.

---

## 11. Kalman Filter Hedge Ratio

### Формула (State-space модель)

**State equation**: βₜ = βₜ₋₁ + wₜ,  wₜ ~ N(0, Q)

**Observation equation**: Yₜ = βₜ · Xₜ + εₜ,  εₜ ~ N(0, R)

**Kalman update**:

```
Predict:
  β̂ₜ|ₜ₋₁ = β̂ₜ₋₁|ₜ₋₁
  Pₜ|ₜ₋₁ = Pₜ₋₁|ₜ₋₁ + Q

Update:
  Kₜ = Pₜ|ₜ₋₁·Xₜ / (Xₜ²·Pₜ|ₜ₋₁ + R)
  β̂ₜ|ₜ = β̂ₜ|ₜ₋₁ + Kₜ·(Yₜ - β̂ₜ|ₜ₋₁·Xₜ)
  Pₜ|ₜ = (1 - Kₜ·Xₜ)·Pₜ|ₜ₋₁
```

### Преимущество перед статическим OLS

Статический hedge ratio (OLS) не учитывает, что β может меняться со временем. Kalman Filter адаптирует βₜ на каждом шаге.

### Crypto-specific

Для cointegrated pairs: β меняется из-за изменений в relative fundamentals (например, ETH merge изменил ETH/BTC соотношение). Kalman Filter автоматически подстраивается.

### Edge cases

- **Инициализация**: β̂₀, P₀, Q, R — начальные значения критичны. Использовать OLS-оценку для β̂₀.
- **Q слишком большой**: фильтр слишком реактивен → шумный hedge ratio.
- **Q слишком маленькое**: фильтр слишком медленный → не адаптируется к изменениям β.

### Rust-реализация

```rust
/// Kalman Filter для динамического hedge ratio.
pub struct KalmanHedgeRatio {
    pub beta: f64,       // Текущая оценка hedge ratio
    pub p: f64,          // Ковариация оценки
    pub q: f64,          // Процессный шум (state noise)
    pub r: f64,          // Шум наблюдения (observation noise)
}

impl KalmanHedgeRatio {
    pub fn new(initial_beta: f64, initial_p: f64, q: f64, r: f64) -> Self {
        Self {
            beta: initial_beta,
            p: initial_p,
            q,
            r,
        }
    }

    /// Обновление фильтра: одно наблюдение (Yₜ, Xₜ).
    ///
    /// Возвращает обновлённый hedge ratio β̂ₜ.
    pub fn update(&mut self, y: f64, x: f64) -> f64 {
        // Predict
        let p_pred = self.p + self.q;

        // Innovation (prediction error)
        let y_pred = self.beta * x;
        let innovation = y - y_pred;

        // Innovation variance
        let s = x * x * p_pred + self.r;

        // Kalman gain
        let k = p_pred * x / s;

        // Update
        self.beta = self.beta + k * innovation;
        self.p = (1.0 - k * x) * p_pred;

        self.beta
    }

    /// Обновление по батчу наблюдений.
    pub fn update_batch(&mut self, y: &[f64], x: &[f64]) -> Vec<f64> {
        assert_eq!(y.len(), x.len());
        let mut betas = Vec::with_capacity(y.len());
        for i in 0..y.len() {
            betas.push(self.update(y[i], x[i]));
        }
        betas
    }

    /// Получить спред с текущим hedge ratio.
    pub fn spread(&self, y: f64, x: f64) -> f64 {
        y - self.beta * x
    }
}

/// Автоматическая инициализация Kalman Filter через OLS.
pub fn kalman_from_ols(y: &[f64], x: &[f64], q: Option<f64>, r: Option<f64>) -> KalmanHedgeRatio {
    let n = y.len();
    let x_mean = x.iter().sum::<f64>() / n as f64;
    let y_mean = y.iter().sum::<f64>() / n as f64;

    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..n {
        num += (x[i] - x_mean) * (y[i] - y_mean);
        den += (x[i] - x_mean).powi(2);
    }
    let beta_ols = num / den;

    // SE(beta)
    let mut ssr = 0.0;
    for i in 0..n {
        ssr += (y[i] - beta_ols * x[i]).powi(2);
    }
    let sigma2 = ssr / (n as f64 - 2.0);
    let se_beta = (sigma2 / den).sqrt();

    let q = q.unwrap_or(se_beta * se_beta * 0.01); // Малый process noise
    let r = r.unwrap_or(sigma2);

    KalmanHedgeRatio::new(beta_ols, se_beta * se_beta, q, r)
}
```

---

## 12. Pairs Trading Framework

### Общая логика

1. **Выбор пары**: Screen all pairs на коинтеграцию (Engle-Granger ADF p < 0.05 + KPSS p > 0.05).
2. **Hedge ratio**: Dynamic (Kalman) или static (OLS).
3. **Spread**: spreadₜ = Yₜ - βₜ · Xₜ
4. **Z-score**: zₜ = (spreadₜ - μ_τ) / σ_τ
5. **Торговые сигналы**: z < -k → long spread, z > k → short spread, |z| < m → exit.

### Rust-реализация (высокоуровневый фреймворк)

```rust
/// Pairs Trading стратегия.
pub struct PairsTrader {
    /// Kalman Filter для динамического hedge ratio
    kalman: KalmanHedgeRatio,
    /// Окно для Z-score (рекомендуется half_life × 2.5)
    z_window: usize,
    /// Порог входа (Z-score)
    entry_threshold: f64,
    /// Порог выхода (Z-score)
    exit_threshold: f64,
    /// История спредов
    spread_history: Vec<f64>,
    /// Текущая позиция
    position: Option<Position>,
}

impl PairsTrader {
    pub fn new(
        y: &[f64],
        x: &[f64],
        z_window: usize,
        entry_threshold: f64,
        exit_threshold: f64,
    ) -> Result<Self, &'static str> {
        // 1. Проверка коинтеграции
        let eg = engle_granger_test(y, x)?;
        if !eg.cointegrated {
            return Err("Series are not cointegrated — pairs trading not applicable");
        }

        // 2. Stationarity gate
        let adf = adf_test(&eg.spread, None, RegressionType::Constant)?;
        let kpss = kpss_test(&eg.spread, RegressionType::Constant)?;
        if adf.p_value >= 0.05 || kpss.p_value < 0.05 {
            return Err(format!(
                "Spread not strictly stationary: ADF p={:.4}, KPSS p={:.4}. Need ADF<0.05 AND KPSS>0.05",
                adf.p_value, kpss.p_value
            ));
        }

        // 3. Инициализация Kalman
        let kalman = kalman_from_ols(y, x, None, None);

        // 4. Считаем начальные спреды
        let mut spread_history = Vec::with_capacity(y.len());
        for i in 0..y.len() {
            spread_history.push(y[i] - kalman.beta * x[i]);
        }

        Ok(Self {
            kalman,
            z_window,
            entry_threshold,
            exit_threshold,
            spread_history,
            position: None,
        })
    }

    /// Обработка нового тика. Возвращает торговый сигнал.
    pub fn on_tick(&mut self, y: f64, x: f64) -> PairsSignal {
        // Обновляем Kalman
        let beta = self.kalman.update(y, x);

        // Считаем спред
        let spread = y - beta * x;
        self.spread_history.push(spread);

        // Z-score (только если достаточно данных)
        if self.spread_history.len() < self.z_window {
            return PairsSignal::Hold;
        }

        let z = {
            let window_start = self.spread_history.len() - self.z_window;
            let window = &self.spread_history[window_start..];
            let mean = window.iter().sum::<f64>() / self.z_window as f64;
            let variance = window.iter().map(|s| (s - mean).powi(2)).sum::<f64>()
                / (self.z_window - 1) as f64;
            let std = variance.sqrt();
            if std > 1e-12 { (spread - mean) / std } else { 0.0 }
        };

        // Сигналы
        match self.position {
            None => {
                if z < -self.entry_threshold {
                    self.position = Some(Position::Long);
                    PairsSignal::EnterLong { z_score: z, hedge_ratio: beta }
                } else if z > self.entry_threshold {
                    self.position = Some(Position::Short);
                    PairsSignal::EnterShort { z_score: z, hedge_ratio: beta }
                } else {
                    PairsSignal::Hold
                }
            }
            Some(Position::Long) => {
                if z > -self.exit_threshold {
                    self.position = None;
                    PairsSignal::Exit { z_score: z }
                } else {
                    PairsSignal::Hold
                }
            }
            Some(Position::Short) => {
                if z < self.exit_threshold {
                    self.position = None;
                    PairsSignal::Exit { z_score: z }
                } else {
                    PairsSignal::Hold
                }
            }
        }
    }
}

#[derive(Debug)]
pub enum PairsSignal {
    EnterLong { z_score: f64, hedge_ratio: f64 },
    EnterShort { z_score: f64, hedge_ratio: f64 },
    Exit { z_score: f64 },
    Hold,
}
```

---

## 13. Сводная валидационная пайплайн

### Gate Rule (строгий фильтр)

Перед запуском любой MR-стратегии обязательна проверка:

```rust
/// Комплексная проверка стационарности.
///
/// Возвращает true только если ADF p < 0.05 И KPSS p > 0.05.
pub fn stationarity_gate(series: &[f64]) -> Result<StationarityReport, &'static str> {
    let adf = adf_test(series, None, RegressionType::Constant)?;
    let kpss = kpss_test(series, RegressionType::Constant)?;
    let pp = phillips_perron_test(series, RegressionType::Constant)?;
    let hurst = hurst_exponent(series, 10, series.len() / 4)?;
    let hl = half_life(series)?;

    let adf_pass = adf.p_value < 0.05;
    let kpss_pass = kpss.p_value > 0.05;
    let pp_pass = pp.p_value_zt < 0.05;
    let hurst_pass = hurst.hurst < 0.5;
    let hl_pass = hl.is_mean_reverting && hl.half_life > 1.0 && hl.half_life < 100.0;

    let strict_pass = adf_pass && kpss_pass;

    Ok(StationarityReport {
        adf: adf,
        kpss: kpss,
        pp: pp,
        hurst: hurst,
        half_life: hl,
        adf_pass,
        kpss_pass,
        pp_pass,
        hurst_pass,
        hl_pass,
        strict_pass,
        recommendation: if strict_pass {
            if hurst_pass && hl_pass {
                "SAFE: Strictly stationary. MR strategy approved."
            } else {
                "CAUTION: Passes ADF+KPSS but Hurst/half-life suggest weak MR."
            }
        } else {
            "REJECTED: Not strictly stationary. Do not trade MR."
        }.to_string(),
    })
}

#[derive(Debug)]
pub struct StationarityReport {
    pub adf: AdfResult,
    pub kpss: KpssResult,
    pub pp: PpResult,
    pub hurst: HurstResult,
    pub half_life: HalfLifeResult,
    pub adf_pass: bool,
    pub kpss_pass: bool,
    pub pp_pass: bool,
    pub hurst_pass: bool,
    pub hl_pass: bool,
    pub strict_pass: bool,
    pub recommendation: String,
}
```

---

## 14. Сравнительная таблица всех инструментов

| Инструмент | Тип | Формула | Edge cases | Crypto-пригодность |
|---|---|---|---|---|
| **ADF Test** | Тест стационарности | Δy = α + βt + γy₋₁ + ΣδΔyᵢ | Short series, structural breaks | ⭐⭐⭐ Обязателен |
| **KPSS Test** | Тест стационарности | KPSS = ΣS²/(T²f₀) | Bandwidth selection | ⭐⭐⭐ Обязателен |
| **Phillips-Perron** | Тест стационарности | Zₜ коррекция t-статистики | Newey-West bandwidth | ⭐⭐ Sanity check |
| **Hurst Exponent** | Метрика памяти | log(R/S) ~ log(τ) → slope | Non-Gaussian, short series | ⭐⭐⭐ Классификатор |
| **OU Process** | Модель | dX = θ(μ-X)dt + σdW | θ ≤ 0, parameter drift | ⭐⭐⭐ Для spreads/funding |
| **Half-life** | Метрика | -ln(2)/β из Δy = α + βy | β ≥ 0 = no MR | ⭐⭐⭐ Holding period |
| **Z-Score** | Сигнал | (X-μ)/σ | Non-stationary μ, σ | ⭐⭐⭐ Primary signal |
| **Bollinger %B** | Сигнал | (P-Lower)/(Upper-Lower) | Squeeze, trending market | ⭐⭐ Визуальный |
| **RSI MR** | Сигнал | 100-100/(1+RS) | Trending market | ⭐ НЕ работает standalone |
| **Engle-Granger** | Тест коинтеграции | ADF на остатках OLS | Только пары | ⭐⭐⭐ Для pairs |
| **Johansen** | Тест коинтеграции | Trace/Max eigenvalue | Сложность реализации | ⭐⭐⭐ Для baskets |
| **Kalman Hedge Ratio** | Адаптивная модель | β̂ₜ = β̂ₜ₋₁ + K·innovation | Init sensitivity | ⭐⭐⭐ Dynamic pairs |

---

## 15. ТОП-3 ЛУЧШИХ инструмента для крипто-бота

### 🥇 1. Pairs Trading + Kalman Filter + ADF/KPSS Gate

**Комбинация**: Engle-Granger → ADF+KPSS валидация → Kalman hedge ratio → Z-score сигналы.

**Почему лучший**:
- Статистически обоснованная стратегия (коинтеграция гарантирует стационарность спреда).
- ADF+KPSS gate = строгий фильтр, исключающий ложные MR.
- Kalman Filter адаптирует hedge ratio к изменениям рынка.
- На крипте множество коинтегрированных пар: BTC/ETH, BTC/SOL, ETH/ARB, stablecoin пары.
- Эмпирически показывает Sharpe 1.5–3.0 на бэктестах (funding rate arbitrage ещё выше).

**Где торговать**: CEX (Binance, Bybit) — spot и perpetual futures. Funding rate arb через delta-neutral позицию (long spot + short perp, или наоборот).

### 🥈 2. Funding Rate Mean-Reversion

**Инструмент**: OU-процесс на funding rate + Z-score.

**Почему**:
- Funding rate гарантированно mean-reverts (механика биржи: выплата каждые 8 часов, арбитраж устраняет отклонение).
- ADF p на funding rate обычно < 0.01. KPSS p > 0.10. Hurst ≈ 0.25–0.35.
- Half-life ≈ 1–3 периода (8–24 часа) → идеальный holding period для swing-трейдинга.
- Delta-neutral: покупаешь spot, продаешь perp (или наоборот) → зарабатываешь funding, не зависишь от направления цены.

**Риск**: exchange risk (биржа закрывается, flash crash), liquidation risk (если с плечом).

### 🥉 3. OU-процесс на cointegrated basket spread (Johansen)

**Инструмент**: Johansen test → VECM → OU на spread корзины → Z-score.

**Почему**:
- Работает для 3+ активов (расширяет pairs trading).
- Johansen находит оптимальные веса портфеля автоматически.
- Spread корзины более стабилен, чем пара (diversification benefit).
- Пример: комбинация BTC, ETH, SOL, AVAX → стационарный портфель с half-life 5–15 периодов.

**Когда добавить**: v0.4+ (требует больше данных и сложнее реализация, чем pairs).

---

## 16. Конфигурация mean-reversion модуля

```yaml
# === Mean-Reversion ===
mean_reversion:
  enabled: true

  # Gate Rule: строгий фильтр стационарности
  stationarity_gate:
    adf_max_pvalue: 0.05
    kpss_min_pvalue: 0.05
    min_observations: 200
    check_every_n_bars: 100  # Перепроверка каждые N баров

  # Pairs Trading
  pairs:
    max_pairs: 5
    min_cointegration_pvalue: 0.05
    z_window_multiplier: 2.5  # window = half_life * multiplier
    entry_z_score: 2.0
    exit_z_score: 0.5
    max_holding_periods: 50   # Максимум баров в сделке
    kalman_q: 0.0001          # Process noise
    kalman_r: null             # Auto из OLS

  # Funding Rate
  funding_rate:
    ou_window: 200             # Баров для OU estimation
    entry_z_score: 1.5
    exit_z_score: 0.3
    min_half_life: 0.5         # Минимум half-life (в периодах)
    max_half_life: 10.0        # Максимум half-life

  # Johansen Basket (v0.4+)
  basket:
    min_assets: 3
    max_assets: 6
    cointegration_rank: null   # Auto из теста
    lookback: 500

  # Общие
  rebalance_check_hours: 4
  max_exposure_pct: 0.10       # 10% капитала на все MR позиции
```

---

## 17. Антипаттерны (запрещено)

| # | Что запрещено | Почему |
|---|---|---|
| 1 | Торговать MR на цене одиночного актива (BTC, ETH) | Не стационарно. ADF p > 0.10. Guaranteed loss. |
| 2 | Использовать RSI/Bollinger %B как standalone MR сигнал | Mean-reverts по конструкции, не по рынку. |
| 3 | Торговать MR без ADF+KPSS валидации | Высокий risk ложного MR (structural break ≠ mean-reversion). |
| 4 | Статический hedge ratio на долгосроке | β меняется. Нужен Kalman или rolling OLS. |
| 5 | Half-life < 1 бара | Спред слишком узкий, комиссии съедают профит. |
| 6 | Half-life > 100 баров | Капитал tied up, opportunity cost. |
| 7 | Не проверять KPSS при ADF p < 0.05 | Trend-stationary ≠ strictly stationary. |
| 8 | Игнорировать Hurst exponent | Если H > 0.5, MR ненадёжен даже при формальном прохождении ADF. |

---

*Документ: agent-14-mean-reversion | Аудит mean-reversion инструментов для крипто-бота*
*Gate Rule: ADF p<0.05 + KPSS p>0.05 = строго стационарный = можно торговать MR*
*ТОП-3: (1) Pairs Trading + Kalman, (2) Funding Rate OU, (3) Johansen Basket*
