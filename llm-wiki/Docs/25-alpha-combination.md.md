# Агент 25: Комбинация альфа-сигналов (Alpha Combination)

> **Специалист:** Agent 25 — Alpha Signal Combination  
> **Дата:** 17 апреля 2026  
> **Статус:** Финальный отчёт  
> **Источники:** Research Indicators.md, 01-trend-indicators.md, 02-oscillators-momentum.md, 05-risk-management.md, López de Prado (Advances in Financial Machine Learning), Bailey & López de Prado (2014)

---

## Содержание

1. [Архитектурная роль комбинации сигналов](#1-архитектурная-роль)
2. [Полный аудит методов комбинации](#2-полный-аудит-методов)
3. [Проблема конфликтов: приоритеты и veto rules](#3-конфликты-и-veto)
4. [Meta-labeling: подробный разбор](#4-meta-labeling)
5. [Финальный выбор: 1–3 лучших метода](#5-финальный-выбор)
6. [Rust-архитектура](#6-рус-архитектура)
7. [Конфигурация](#7-конфигурация)

---

## 1. Архитектурная роль

### Контекст: что выходят другие агенты

| Агент | Роль | Сигнал | Направление |
|-------|------|--------|-------------|
| **Агент 1 (Trend)** | Primary направление | EMA20 > EMA50 + ADX > 25 + VWAP filter | LONG / SHORT / NEUTRAL |
| **Агент 2 (Oscillators)** | Тайминг + фильтр перекупленности | StochRSI, Fisher, CCI — зоны перекупленности | CONFIRM / WARN / BLOCK |
| **Агент 3 (Volatility)** | Размер позиции | ATR, Bollinger Squeeze | SCALE_UP / SCALE_DOWN |
| **Агент 4 (Volume)** | Подтверждение объёмом | OBV divergence, VWAP, CVD | CONFIRM / DIVERGE |
| **Агент 5 (Risk)** | Контроль риска | Circuit Breaker, VaR/CVaR, Kelly | HALT / REDUCE / NORMAL |

### Задача Агента 25

Принять **N сигналов** от разных агентов и выдать **одно торговое решение**: `{direction: LONG|SHORT|FLAT, confidence: [0,1], size_modifier: f64}`.

Это **не** тривиальное усреднение. Сигналы:
- Разной природы (тренд vs. осциллятор vs. объём)
- Разной уверенности (ADX 40 vs ADX 26 — оба > 25, но разная сила)
- Конфликтуют (тренд LONG, но осциллятор перекуплен)

---

## 2. Полный аудит методов комбинации

### 2.1 Simple Weighted Average

**Формула:**
```
Score_final = Σᵢ (wᵢ × signalᵢ) / Σwᵢ

где:
  signalᵢ ∈ [-1, +1]  (−1 = SHORT, 0 = NEUTRAL, +1 = LONG)
  wᵢ > 0 — вес i-го сигнала
  Score_final > threshold_long  → LONG
  Score_final < threshold_short → SHORT
  иначе → FLAT
```

**Пример:**
```
w_trend = 0.40, signal_trend = +1 (EMA кроссовер бычий)
w_osc   = 0.25, signal_osc   = −0.5 (StochRSI перекуплен, но не экстремум)
w_vol   = 0.15, signal_vol   = +0.3 (squeeze, направление неясно)
w_volume = 0.20, signal_vol  = +0.7 (CVD растёт)

Score = (0.40×1 + 0.25×(−0.5) + 0.15×0.3 + 0.20×0.7) / 1.0
      = (0.40 − 0.125 + 0.045 + 0.14) = 0.46

Score > 0.3 → LONG с confidence 0.46
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Все сигналы = 0 (нет информации) | Score = 0 → FLAT. Корректно. | — |
| Один экстремальный сигнал (+1), остальные = 0 | Score = wᵢ — доминирует один | Нормализация весов |
| Сигналы противоположны (+1, −1, +1, −1) | Score ≈ 0 → FLAT. Потеря волатильности. | Majority Vote как fallback |
| Нет данных от одного агента | Пропущенный вес → искажение | `score = Σ(wᵢ×sᵢ) / Σwᵢ для доступных` |

**Rust-реализация:**
```rust
pub struct WeightedAverage {
    weights: Vec<f64>,  // предвычисленные, сумма = 1.0
    thresholds: (f64, f64), // (long_threshold, short_threshold)
}

impl WeightedAverage {
    pub fn combine(&self, signals: &[Option<f64>]) -> CombinedSignal {
        let mut score = 0.0;
        let mut total_weight = 0.0;

        for (i, sig) in signals.iter().enumerate() {
            if let Some(s) = sig {
                score += self.weights[i] * s;
                total_weight += self.weights[i];
            }
        }

        if total_weight < f64::EPSILON {
            return CombinedSignal::flat();
        }

        let normalized = score / total_weight;

        if normalized > self.thresholds.0 {
            CombinedSignal::long(normalized)
        } else if normalized < self.thresholds.1 {
            CombinedSignal::short(normalized.abs())
        } else {
            CombinedSignal::flat()
        }
    }
}
```

**Вердикт: ⚠️ БАЗОВЫЙ — работает, но теряет информацию о конфликтах.**

---

### 2.2 Majority Vote (Мажоритарное голосование)

**Формула:**
```
Votes_long  = count(signalsᵢ > 0)
Votes_short = count(signalsᵢ < 0)
Votes_flat  = count(signalsᵢ == 0)

Decision = argmax(Votes_long, Votes_short, Votes_flat)

Confidence = max_votes / total_votes
```

**Пример:**
```
Trend:      +1  (LONG)
Oscillator: −1  (SHORT — перекуплен)
Volume:     +1  (LONG — CVD растёт)
Volatility:  0  (NEUTRAL — squeeze)

Votes: LONG=2, SHORT=1, FLAT=1 → LONG (50% confidence)
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Равное число голосов (2-2) | Нет победителя → FLAT | Корректно: нет консенсуса |
| 3 сигнала LONG, но все с confidence 0.1 | Majority, но слабый | Weighted vote: учитывать силу |
| 1 сигнал LONG с высокой уверенностью, 3 NEUTRAL | Majority FLAT, но теряется сильный сигнал | Threshold: 1 сильный > 3 слабых |
| Нечётное число агентов (5) | Нет ничьей | Предпочтительно |

**Rust-реализация:**
```rust
pub struct MajorityVote {
    min_votes_required: usize, // минимум голосов для решения
}

impl MajorityVote {
    pub fn combine(&self, signals: &[Option<SignalStrength>]) -> CombinedSignal {
        let (mut long, mut short, mut flat) = (0usize, 0, 0);
        let mut long_conf = 0.0f64;
        let mut short_conf = 0.0f64;

        for sig in signals.iter().flatten() {
            match sig.direction {
                Direction::Long => { long += 1; long_conf += sig.confidence; }
                Direction::Short => { short += 1; short_conf += sig.confidence; }
                Direction::Flat => { flat += 1; }
            }
        }

        let total = long + short + flat;
        if total < self.min_votes_required {
            return CombinedSignal::flat();
        }

        if long > short && long > flat {
            CombinedSignal::long(long_conf / long as f64)
        } else if short > long && short > flat {
            CombinedSignal::short(short_conf / short as f64)
        } else {
            CombinedSignal::flat()
        }
    }
}
```

**Вердикт: ⚠️ ПРОСТОЙ — не учитывает силу сигналов. Только направление.**

---

### 2.3 Confidence-Weighted Signals

**Формула:**
```
Score_final = Σᵢ (confidenceᵢ × signalᵢ) / Σconfidenceᵢ

где:
  confidenceᵢ ∈ [0, 1] — степень уверенности i-го агента
  signalᵢ ∈ {-1, 0, +1} — направление

  confidenceᵢ вычисляется каждым агентом индивидуально:
    Trend:    confidence = min(1.0, (ADX - 25) / 15)  — ADX 25→0%, ADX 40→100%
    Oscillator: confidence = 1.0 - |RSI - 50| / 50    — RSI 50→100%, RSI 0/100→0%
    Volume:   confidence = min(1.0, |CVD_slope| / threshold)
```

**Пример (конкретный):**
```
Trend:      signal=+1, ADX=38 → conf = (38-25)/15 = 0.867
Oscillator: signal=−0.5, RSI=65 → conf = 1.0 - |65-50|/50 = 0.70
Volume:     signal=+1, CVD_slope=high → conf = 0.90
Volatility: signal=0, ATR stable → conf = 0.50

Score = (0.867×1 + 0.70×(−0.5) + 0.90×1 + 0.50×0) / (0.867 + 0.70 + 0.90 + 0.50)
      = (0.867 − 0.35 + 0.90 + 0) / 2.967
      = 1.417 / 2.967
      = 0.478

Score > 0.3 → LONG с confidence 0.478
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Один агент conf=1.0, остальные conf≈0 | Доминирование одного | Cap: max weight = 0.5 |
| Все conf=0 | Деление на 0 | Возврат FLAT |
| ADX < 25 → conf_trend = 0 | Трендовый сигнал «молчит» | Корректно: тренд не подтверждён |

**Rust-реализация:**
```rust
pub struct ConfidenceWeighted {
    max_weight_cap: f64, // 0.5 — максимум влияния одного агента
}

impl ConfidenceWeighted {
    pub fn combine(&self, signals: &[SignalWithConfidence]) -> CombinedSignal {
        let mut score = 0.0;
        let mut total_conf = 0.0;

        for s in signals {
            let capped_conf = s.confidence.min(self.max_weight_cap);
            score += capped_conf * s.direction;
            total_conf += capped_conf;
        }

        if total_conf < f64::EPSILON {
            return CombinedSignal::flat();
        }

        CombinedSignal::from_score(score / total_conf)
    }
}
```

**Вердикт: ✅ УЛУЧШЕННЫЙ — учитывает силу, но не решает конфликты.**

---

### 2.4 Bayesian Ensemble

**Формула:**
```
P(LONG | signals) ∝ P(signals | LONG) × P(LONG)

где:
  P(LONG) = prior probability (базовая вероятность тренда)
  P(signals | LONG) = ∏ᵢ P(signalᵢ | LONG) — likelihood каждого сигнала

  P(signalᵢ | LONG) оценивается из исторических данных:
    Если signalᵢ = LONG и рынок был LONG → P = accuracyᵢ
    Если signalᵢ = SHORT и рынок был LONG → P = 1 - accuracyᵢ

  Posterior:
    P(LONG | s) = P(s|LONG)×P(LONG) / [P(s|LONG)×P(LONG) + P(s|SHORT)×P(FLAT)]

С упрощением (naive Bayes):
  log_odds(LONG) = log(P(LONG)/P(FLAT)) + Σᵢ log(P(sᵢ|LONG)/P(sᵢ|FLAT))
```

**Числовой пример:**
```
Priors: P(LONG) = 0.35, P(SHORT) = 0.25, P(FLAT) = 0.40
(kрипта: ~35% времени в тренде вверх)

Сигналы:
  Trend (EMA crossover): LONG
    P(LONG | trend_says_LONG) = 0.65  (историческая точность)
    P(FLAT | trend_says_LONG) = 0.20
    P(SHORT | trend_says_LONG) = 0.15

  Oscillator (StochRSI > 80): SHORT warning
    P(LONG | osc_says_SHORT) = 0.20
    P(FLAT | osc_says_SHORT) = 0.50
    P(SHORT | osc_says_SHORT) = 0.30

  Volume (CVD rising): LONG
    P(LONG | vol_says_LONG) = 0.60
    P(FLAT | vol_says_LONG) = 0.25
    P(SHORT | vol_says_LONG) = 0.15

Posterior:
  P(LONG) = 0.35 × 0.65 × 0.20 × 0.60 = 0.0273
  P(SHORT) = 0.25 × 0.15 × 0.30 × 0.15 = 0.00169
  P(FLAT) = 0.40 × 0.20 × 0.50 × 0.25 = 0.01

  Нормализация: sum = 0.03899
  P(LONG|s) = 0.0273/0.03899 = 0.700 → LONG с confidence 0.70
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Новый агент без истории | P(signal|state) = 0.5 (неинформативный prior) | Laplace smoothing: (k+1)/(n+2) |
| Все P = 0 (один сигнал невозможен) | Posterior = 0/0 | Log-space вычисление + epsilon |
| Концепт-drift (рынок меняется) | P из старых данных неактуальны | Rolling window для likelihood |
| Сильный prior (P(FLAT) = 0.8) | Даже сильные сигналы не пробивают prior | Prior update через online learning |

**Rust-реализация:**
```rust
pub struct BayesianEnsemble {
    /// likelihood_matrix[signal_idx][state] = P(signal | state)
    likelihood: Vec<Vec<f64>>,
    /// prior[state] = P(state)
    prior: [f64; 3], // [LONG, SHORT, FLAT]
}

#[derive(Clone, Copy)]
pub enum MarketState { Long, Short, Flat }

impl BayesianEnsemble {
    pub fn combine(&self, signal_indices: &[usize]) -> (MarketState, f64) {
        let mut log_posterior = [0.0f64; 3];

        for (i, &state) in [MarketState::Long, MarketState::Short, MarketState::Flat].iter().enumerate() {
            log_posterior[i] = self.prior[i].ln();

            for (sig_idx, &observed) in signal_indices.iter().enumerate() {
                let p = self.likelihood[sig_idx][observed]
                    .max(1e-10); // epsilon для log
                log_posterior[i] += p.ln();
            }
        }

        // Log-sum-exp для нормализации
        let max_lp = log_posterior.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let mut posteriors = [0.0f64; 3];
        let mut sum = 0.0;
        for i in 0..3 {
            posteriors[i] = (log_posterior[i] - max_lp).exp();
            sum += posteriors[i];
        }
        for i in 0..3 { posteriors[i] /= sum; }

        // Выбор лучшего
        let best = posteriors.iter().copied().enumerate()
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap()).unwrap();

        let state = match best.0 {
            0 => MarketState::Long,
            1 => MarketState::Short,
            _ => MarketState::Flat,
        };

        (state, best.1) // (направление, confidence)
    }
}
```

**Вердикт: ✅ ТЕОРЕТИЧЕСКИ СИЛЬНЫЙ — но требует исторических likelihood, которые на MVP могут быть неточными.**

---

### 2.5 Stacking (Stacked Generalization)

**Формула:**
```
Level-0 (base models):
  f₁(x) = Trend signal     → {LONG, SHORT, FLAT}
  f₂(x) = Oscillator signal → {CONFIRM, WARN, BLOCK}
  f₃(x) = Volume signal     → {CONFIRM, DIVERGE}
  f₄(x) = Volatility signal → {HIGH, LOW, NORMAL}

Level-1 (meta-model):
  F(x) = g(f₁(x), f₂(x), f₃(x), f₄(x), x)

  где g — обученная модель (logistic regression, XGBoost, или нейросеть)
  Вход: предсказания base models + дополнительные фичи
  Выход: {LONG, SHORT, FLAT} с вероятностями
```

**Архитектура:**
```
                    ┌──────────────┐
  Market Data ─────►│  Trend Model │─────┐
                    └──────────────┘     │
                    ┌──────────────┐     │   ┌──────────────┐
  Market Data ─────►│  Oscillator  │─────┼──►│  Meta-Model  │──► FINAL DECISION
                    └──────────────┘     │   │  (XGBoost)   │
                    ┌──────────────┐     │   └──────────────┘
  Market Data ─────►│   Volume     │─────┤
                    └──────────────┘     │
                    ┌──────────────┐     │
  Market Data ─────►│ Volatility   │─────┘
                    └──────────────┘
```

**Обучение:**
```
1. Разделить данные на K фолдов
2. Для каждого фолда:
   a. Обучить base models на K-1 фолдах
   b. Получить предсказания base models на hold-out фолде
   c. Записать предсказания как фичи для meta-model
3. Обучить meta-model на всех out-of-fold предсказаниях
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Base model не обучен (MVP) | Нет предсказаний для stacking | Использовать rule-based как base |
| Overfitting на Level-1 | Meta-model меморизирует шум | Purged K-Fold (López de Prado) |
| Несбалансированные классы | Meta-model偏向 FLAT | Class weights в XGBoost |
| Концепт-drift | Старый meta-model | Retrain каждые N баров |

**Rust-реализация:**
```rust
/// Stacking combiner — вызывает внешний XGBoost через FFI или subprocess
pub struct StackingCombiner {
    base_signals: Vec<Box<dyn SignalGenerator>>,
    meta_model_path: String, // путь к обученной модели (ONNX/XGBoost)
}

impl StackingCombiner {
    pub fn combine(&self, market_data: &MarketData) -> CombinedSignal {
        // Level-0: собрать предсказания base models
        let mut features: Vec<f64> = Vec::new();
        for base in &self.base_signals {
            let (direction, confidence) = base.predict(market_data);
            features.push(direction as f64); // LONG=1, SHORT=-1, FLAT=0
            features.push(confidence);
        }

        // Добавить raw фичи (индикаторные значения)
        features.extend_from_slice(&market_data.indicator_values());

        // Level-1: meta-model prediction
        // В MVP — rule-based fallback; в production — XGBoost через FFI
        self.meta_model_predict(&features)
    }

    fn meta_model_predict(&self, features: &[f64]) -> CombinedSignal {
        // Placeholder: в production загружается обученная модель
        // Для MVP используем confidence-weighted как fallback
        ConfidenceWeighted::default().combine_from_features(features)
    }
}
```

**Вердикт: ⚠️ МОЩНЫЙ, но требует ML-инфраструктуры. Не для MVP. Запланировать на v0.5.**

---

### 2.6 Boosting Signals (Sequential Ensemble)

**Формула:**
```
Signal₀ = base_signal (тренд)

Для каждого следующего агента i = 1..N:
  error_i = actual_return - predicted_return(Signal_{i-1})
  weight_i = f(error_i)  — вес корректирующего сигнала
  Signal_i = Signal_{i-1} + weight_i × correction_i

где:
  correction_i ∈ [-1, +1] — коррекция от i-го агента
  weight_i зависит от исторической точности коррекций агента i
```

**Пример:**
```
Signal₀ = +1 (Trend: LONG)

Oscillator: correction = −0.5 (перекуплен)
  weight_osc = 0.3 (исторически: oscillator corrections уменьшают убытки на 15%)
  Signal₁ = +1 + 0.3 × (−0.5) = +0.85

Volume: correction = +0.2 (CVD подтверждает)
  weight_vol = 0.2
  Signal₂ = +0.85 + 0.2 × 0.2 = +0.89

Final: +0.89 → LONG (confidence 0.89)
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Агенты дают противоположные коррекции | Они гасят друг друга → ≈ 0 | Нормализация после каждого шага |
| «Bad actor» агент постоянно портит | Систематическая деградация | Online weight update (убрать неэффективного) |
| Коррекция > базового сигнала | Сигнал меняет знак | Clamp: final ∈ [−1, +1] |

**Вердикт: ⚠️ ИНТЕРЕСНАЯ ИДЕЯ, но сложнее валидации. Риск каскадных ошибок.**

---

### 2.7 Regime-Conditional Weighting

**Формула:**
```
Определить regime r ∈ {TRENDING_UP, TRENDING_DOWN, RANGING, HIGH_VOL}

Для каждого regime — свой набор весов:
  wᵢ(r) — вес i-го сигнала в режиме r

Score(r) = Σᵢ wᵢ(r) × signalᵢ

Определение regime:
  TRENDING_UP:   ADX > 30 AND EMA20 > EMA50 AND Hurst > 0.55
  TRENDING_DOWN: ADX > 30 AND EMA20 < EMA50 AND Hurst > 0.55
  RANGING:       ADX < 25 AND Hurst < 0.45
  HIGH_VOL:      ATR > P95(historical_ATR)
```

**Таблица весов:**

| Агент | TRENDING_UP | TRENDING_DOWN | RANGING | HIGH_VOL |
|-------|-------------|---------------|---------|----------|
| Trend (EMA/ADX) | **0.50** | **0.50** | 0.10 | 0.30 |
| Oscillator | 0.20 | 0.20 | **0.45** | 0.15 |
| Volume | 0.20 | 0.20 | 0.25 | 0.20 |
| Volatility | 0.10 | 0.10 | 0.20 | **0.35** |

**Логика:**
- В тренде: трендовые индикаторы доминируют (вес 0.50)
- Во флэте: осцилляторы становятся primary (вес 0.45) — mean-reversion
- В high vol: волатильность становится важнее (вес 0.35) — risk management

**Числовой пример:**
```
Regime = TRENDING_UP (ADX=35, EMA20>EMA50, Hurst=0.58)

Weights: Trend=0.50, Osc=0.20, Vol=0.20, Volume=0.10
Signals: Trend=+1, Osc=−0.5, Vol=+0.3, Volume=+0.7

Score = 0.50×1 + 0.20×(−0.5) + 0.20×0.3 + 0.10×0.7
      = 0.50 − 0.10 + 0.06 + 0.07 = 0.53

→ LONG (confidence 0.53)
```

Тот же набор сигналов в RANGING:
```
Weights: Trend=0.10, Osc=0.45, Vol=0.20, Volume=0.25

Score = 0.10×1 + 0.45×(−0.5) + 0.20×0.3 + 0.25×0.7
      = 0.10 − 0.225 + 0.06 + 0.175 = 0.11

→ FLAT (confidence 0.11 — ниже порога)
```

**Edge Cases:**

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Regime определён неправильно | Неверные веса → плохой сигнал | Ensemble regime detection (HMM + ADX + Hurst) |
| Regime меняется часто | Веса скачут → нестабильный сигнал | Smoothing: EWMA на regime probabilities |
| Regime не определён (пограничный) | Какие веса использовать? | Blend: w_final = Σ P(r) × w(r) |

**Rust-реализация:**
```rust
pub struct RegimeConditional {
    /// weights[regime_idx][signal_idx]
    weights: [[f64; 4]; 4], // 4 regimes × 4 signals
    regime_detector: RegimeDetector,
}

pub struct RegimeDetector {
    adx: ADX,
    ema_fast: EMA,
    ema_slow: EMA,
    hurst: HurstExponent,
    atr_percentile: RollingPercentile,
}

#[derive(Clone, Copy, PartialEq)]
pub enum Regime { TrendUp, TrendDown, Range, HighVol }

impl RegimeDetector {
    pub fn detect(&self) -> (Regime, f64) { // (regime, confidence)
        let adx = self.adx.current();
        let trend_up = self.ema_fast.current() > self.ema_slow.current();
        let hurst = self.hurst.current();
        let high_vol = self.atr_percentile.current() > 0.95;

        if high_vol {
            return (Regime::HighVol, 0.8);
        }
        if adx > 30.0 && hurst > 0.55 {
            if trend_up { (Regime::TrendUp, 0.9) }
            else { (Regime::TrendDown, 0.9) }
        } else if adx < 25.0 && hurst < 0.45 {
            (Regime::Range, 0.7)
        } else {
            // Пограничный: blend
            (Regime::Range, 0.4) // неуверенный
        }
    }
}

impl RegimeConditional {
    pub fn combine(&self, signals: &[f64; 4]) -> CombinedSignal {
        let (regime, regime_conf) = self.regime_detector.detect();
        let regime_idx = regime as usize;

        let mut score = 0.0;
        for (i, &sig) in signals.iter().enumerate() {
            score += self.weights[regime_idx][i] * sig;
        }

        CombinedSignal::from_score(score * regime_conf)
    }
}
```

**Вердикт: ✅ СИЛЬНЫЙ — адаптирует веса к рыночному режиму. Решает проблему «тренд vs. осциллятор».**

---

### 2.8 Meta-Labeling (López de Prado)

**Формула (подробный разбор в §4):**
```
Model 1 (Primary): Генерирует сигнал {LONG, SHORT}
  Это «что торговать»

Model 2 (Meta): Предсказывает, будет ли Model 1 прав
  P(correct | features) — «стоит ли торговать этот сигнал»

Финальное решение:
  IF Model1 = LONG AND Model2(confidence) > threshold:
      EXECUTE LONG
  ELSE:
      SKIP (не торговать)

Meta-label = 1 если Model1 был прав (trading was profitable)
Meta-label = 0 если Model1 был wrong (trading was losing)
```

**Вердикт: см. §4 полный разбор.**

---

### 2.9 Hierarchical Decision Tree

**Формула:**
```
Level 1 — Gate: Risk Manager
  IF circuit_breaker == HALT → FLAT (veto)
  IF circuit_breaker == REDUCE → size *= 0.5

Level 2 — Direction: Trend
  IF EMA20 > EMA50 AND ADX > 25 → direction = LONG
  IF EMA20 < EMA50 AND ADX > 25 → direction = SHORT
  ELSE → FLAT

Level 3 — Filter: Oscillator
  IF direction == LONG AND RSI > 70 → WARN (уменьшить confidence)
  IF direction == LONG AND StochRSI < 20 → STRONG (увеличить confidence)
  ELSE → NEUTRAL

Level 4 — Confirmation: Volume
  IF direction == LONG AND CVD rising → CONFIRM
  IF direction == LONG AND CVD falling → DIVERGE (уменьшить confidence)

Level 5 — Size: Volatility
  position_size = Kelly × ATR_factor × regime_modifier
```

**Вердикт: ⚠️ ИНТУИТИВНЫЙ, но жёсткий порядок теряет информацию. Комбинация лучше.**

---

### 2.10 Veto Rules (Hard Constraints)

**Формула:**
```
FINAL = base_signal

VETO conditions (любой = FLAT):
  1. RiskManager.state == HALT
  2. Trend.confidence < min_threshold (ADX < 20)
  3. VaR > max_var
  4. Kelly <= 0 (нет edge)
  5. Количество сделок сегодня > max_daily_trades

REDUCE conditions (все применяются к size):
  1. RiskManager.state == WARNING → size *= 0.5
  2. Oscillator.overbought AND direction == LONG → size *= 0.7
  3. Volume.divergence → size *= 0.5
  4. High_volatility → size *= 0.6
```

**Вердикт: ✅ ОБЯЗАТЕЛЬНЫЙ элемент любой системы. Не заменяет комбинацию, а дополняет.**

---

### 2.11 Online Learning / Adaptive Weights

**Формула:**
```
wᵢ(t+1) = wᵢ(t) × exp(η × rewardᵢ(t))

где:
  η = learning rate (0.01–0.1)
  rewardᵢ(t) = sign(signalᵢ(t)) × return(t+1)
    reward > 0 если агент предсказал правильно
    reward < 0 если агент ошибся

Нормализация: wᵢ(t+1) /= Σⱼ wⱼ(t+1)
```

**Вердикт: ⚠️ АДАПТИВНЫЙ, но требует много данных для сходимости. Нестабилен на коротких окнах. Запланировать на v0.5.**

---

### 2.12 Portfolio-Level Combination (Mean-Variance)

**Формула:**
```
Оптимальные веса (Markowitz):
  w* = Σ⁻¹ × μ / (1ᵀ × Σ⁻¹ × μ)

где:
  μ = вектор ожидаемых доходностей сигналов
  Σ = ковариационная матрица сигналов
```

**Вердикт: ❌ НЕПРИМЕНИМ. Комбинация сигналов ≠ комбинация активов. Сигналы не имеют «доходности» в смысле портфельной теории.**

---

### 2.13 Copula-Based Combination

**Формула:**
```
Зависимость между сигналами описывается copula-функцией:
  C(u₁, u₂, ..., uₙ) = F(F₁⁻¹(u₁), F₂⁻¹(u₂), ..., Fₙ⁻¹(uₙ))

где uᵢ = CDF(signalᵢ)
```

**Вердикт: ❌ СЛИШКОМ СЛОЖНО для MVP. Copula описывает зависимость, но не даёт торговое решение. Требует оценки параметров на 500+ наблюдениях.**

---

### 2.14 Dempster-Shafer Theory (Evidence Theory)

**Формула:**
```
mᵢ(A) = «mass» — степень доверия агента i к гипотезе A

Bel(A) = Σ_{B⊆A} m(B)   — верхняя граница доверия
Pl(A) = Σ_{B∩A≠∅} m(B)  — нижняя граница

Комбинация (Dempster's rule):
  m₁₂(A) = Σ_{B∩C=A} m₁(B) × m₂(C) / (1 − K)

где K = Σ_{B∩C=∅} m₁(B) × m₂(C) — конфликт
```

**Вердикт: ⚠️ ТЕОРЕТИЧЕСКИ ИНТЕРЕСНЫЙ. Обрабатывает неопределённость и конфликты. Но: сложная реализация, нет стандартных библиотек в Rust. Запланировать на v0.5+.**

---

### 2.15 Fuzzy Logic Combination

**Формула:**
```
Определить fuzzy sets:
  LONG:   signal ∈ [0.3, 1.0]  (степень принадлежности μ)
  SHORT:  signal ∈ [-1.0, -0.3]
  FLAT:   signal ∈ [-0.3, 0.3]

Правила (fuzzy inference):
  IF Trend IS StrongLong AND Osc IS NOT Overbought THEN Action IS Long (0.8)
  IF Trend IS Long AND Osc IS Overbought THEN Action IS LongButSmall (0.4)
  IF Trend IS Flat AND Osc IS Oversold THEN Action IS LongCounter (0.6)

Defuzzification (centroid):
  output = Σ(μᵢ × valueᵢ) / Σμᵢ
```

**Вердикт: ⚠️ ГИБКИЙ, но правила нужно вручную писать. Субъективность. Для MVP — проще rule-based.**

---

### 2.16 Snippet Summary

| # | Метод | Сложность | Конфликты | Адаптивность | MVP? | Вердикт |
|---|-------|-----------|-----------|-------------|------|---------|
| 1 | Weighted Average | 🟢 Low | ❌ | ❌ | ✅ | ⚠️ Базовый |
| 2 | Majority Vote | 🟢 Low | ❌ | ❌ | ✅ | ⚠️ Простой |
| 3 | Confidence-Weighted | 🟡 Med | ❌ | ❌ | ✅ | ✅ Улучшенный |
| 4 | Bayesian Ensemble | 🔴 High | ✅ | ⚠️ | ❌ | ✅ Сильный (v0.5) |
| 5 | Stacking | 🔴 High | ✅ | ✅ | ❌ | ⚠️ ML (v0.5) |
| 6 | Boosting | 🟡 Med | ⚠️ | ✅ | ❌ | ⚠️ Каскад ошибок |
| 7 | **Regime-Conditional** | 🟡 Med | **✅** | **✅** | **✅** | **⭐ ТОП-1** |
| 8 | **Meta-Labeling** | 🟡 Med | **✅** | **✅** | **✅** | **⭐ ТОП-2** |
| 9 | Hierarchical Tree | 🟢 Low | ⚠️ | ❌ | ✅ | ⚠️ Жёсткий |
| 10 | **Veto Rules** | 🟢 Low | **✅** | ❌ | **✅** | **⭐ ТОП-3 (доп.)** |
| 11 | Online Learning | 🟡 Med | ✅ | ✅ | ❌ | ⚠️ v0.5 |
| 12 | Mean-Variance | 🟡 Med | ❌ | ❌ | ❌ | ❌ Неприменим |
| 13 | Copula | 🔴 High | ✅ | ❌ | ❌ | ❌ Сложно |
| 14 | Dempster-Shafer | 🔴 High | ✅ | ❌ | ❌ | ⚠️ v0.5+ |
| 15 | Fuzzy Logic | 🟡 Med | ⚠️ | ❌ | ❌ | ⚠️ Субъективен |

---

## 3. Конфликты и Veto Rules

### 3.1 Главный конфликт: Тренд LONG vs. Осциллятор перекуплен

**Ситуация:**
```
Trend (EMA20 > EMA50, ADX=32):  signal = LONG
Oscillator (RSI=75, StochRSI=85): signal = BLOCK (перекуплен)
```

**Возможные решения:**

| Стратегия | Действие | Результат |
|-----------|----------|-----------|
| Trend priority | LONG игнорируя RSI | ✅ Правильно в 60% случаев (тренд продолжается) |
| Oscillator priority | FLAT | ❌ Теряем тренд в 60% случаев |
| Compromise | LONG с уменьшенным size (×0.5) | ✅ Лучший компромисс |
| Regime-dependent | LONG если ADX > 35, иначе FLAT | ✅✅ Адаптивно |

**Рекомендация: Regime-dependent compromise**

```
IF Trend = LONG AND Osc = BLOCK:
    IF ADX > 35 (сильный тренд):
        direction = LONG
        size_modifier = 0.7  (70% от нормального размера)
        reason = "Strong trend overrides overbought"
    ELIF ADX > 25 (умеренный тренд):
        direction = LONG
        size_modifier = 0.4  (40% — осторожно)
        reason = "Moderate trend, overbought warning"
    ELSE:
        direction = FLAT
        reason = "Weak trend + overbought = no trade"
```

### 3.2 Конфликт: Объём дивергенция vs. Всё остальное LONG

**Ситуация:**
```
Trend: LONG
Oscillator: CONFIRM (StochRSI < 20, выход из перепроданности)
Volume: DIVERGE (OBV падает при растущей цене → умные деньги выходят)
```

**Решение:**
```
Volume divergence = WARNING, не VETO
  → direction = LONG (тренд + осциллятор подтверждают)
  → size_modifier = 0.5 (объём предупреждает)
  → если подтверждается 3+ бара → пересмотр

Volume divergence + CVD negative = VETO
  → direction = FLAT
  → агрессивные продавцы доминируют
```

### 3.3 Конфликт: High Volatility vs. Strong Trend

**Ситуация:**
```
Trend: LONG (ADX=45, очень сильный)
Volatility: HIGH (ATR > 95th percentile)
Risk: WARNING (VaR > 5%)
```

**Решение:**
```
direction = LONG (тренд сильный)
size_modifier = Kelly × 0.5 × 0.5 = 0.25×Kelly (high vol + risk warning)
SL_multiplier = 2.5 (расширить стоп для vol)
```

### 3.4 Полная иерархия приоритетов

```
ПРИОРИТЕТ 1 — VETO (абсолютный, не обсуждается):
  ├── RiskManager.state == HALT
  ├── Circuit Breaker triggered
  ├── Kelly <= 0 (нет edge)
  ├── P_ruin > 5%
  └── Max daily trades exceeded

ПРИОРИТЕТ 2 — DIRECTION (кто определяет направление):
  ├── Trend Model (50% голоса в trending regime)
  ├── Oscillator (45% голоса в ranging regime)
  └── Volume (confirmation, не direction)

ПРИОРИТЕТ 3 — MODIFIERS (кто корректирует размер):
  ├── Volatility → ATR-адаптация размера
  ├── Risk Manager → Kelly fraction
  ├── Oscillator overbought/oversold → reduce size
  └── Volume divergence → reduce size

ПРИОРИТЕТ 4 — TIMING (когда именно входить):
  ├── StochRSI exit from oversold (для LONG)
  ├── Fisher reversal
  └── MACD histogram flip
```

### 3.5 Veto Rules — формальная спецификация

```rust
#[derive(Debug, Clone, Copy)]
pub enum VetoReason {
    CircuitBreakerHalt,
    KellyNegative,
    RiskOfRuinHigh,
    MaxDailyTrades,
    InsufficientData,
}

#[derive(Debug, Clone)]
pub struct VetoCheck {
    pub is_vetoed: bool,
    pub reason: Option<VetoReason>,
}

pub fn check_vetoes(state: &TradingState) -> VetoCheck {
    if state.circuit_breaker == CBState::FullStop {
        return VetoCheck { is_vetoed: true, reason: Some(VetoReason::CircuitBreakerHalt) };
    }
    if state.kelly_fraction <= 0.0 {
        return VetoCheck { is_vetoed: true, reason: Some(VetoReason::KellyNegative) };
    }
    if state.risk_of_ruin > 0.05 {
        return VetoCheck { is_vetoed: true, reason: Some(VetoReason::RiskOfRuinHigh) };
    }
    if state.daily_trades >= state.max_daily_trades {
        return VetoCheck { is_vetoed: true, reason: Some(VetoReason::MaxDailyTrades) };
    }
    if !state.has_sufficient_data() {
        return VetoCheck { is_vetoed: true, reason: Some(VetoReason::InsufficientData) };
    }
    VetoCheck { is_vetoed: false, reason: None }
}
```

---

## 4. Meta-Labeling: подробный разбор

### 4.1 Что такое Meta-Labeling

Meta-labeling — техника из книги López de Prado «Advances in Financial Machine Learning» (2018). Ключевая идея:

> **Разделить задачу на две: (1) КАКОЕ направление торговать, (2) СТОИТ ли торговать.**

Первая модель определяет направление. Вторая модель (meta-model) решает, доверять ли первой.

### 4.2 Архитектура

```
Рыночные данные
     │
     ▼
┌──────────────────┐
│  PRIMARY MODEL   │──── Прогноз: LONG / SHORT
│  (Trend + Osc)   │     «ЧТО торговать»
└────────┬─────────┘
         │
         ▼ features для meta-model:
         │  - confidence primary model
         │  - RSI, ADX, ATR (текущие)
         │  - volatility regime
         │  - volume profile
         │  - время суток, день недели
         │
┌──────────────────┐
│   META-MODEL     │──── Прогноз: P(correct) ∈ [0, 1]
│   (Classifier)   │     «СТОИТ ли торговать»
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   DECISION       │──── IF P(correct) > threshold → EXECUTE
│                  │     ELSE → SKIP
└──────────────────┘
```

### 4.3 Создание Meta-Labels

```
Шаг 1: Получить предсказания Primary Model на исторических данных
  primary_pred[t] = {LONG, SHORT}

Шаг 2: Определить, был ли Primary прав
  actual_direction[t] = sign(close[t+N] - close[t])  (N = holding period)
  primary_correct[t] = (primary_pred[t] == actual_direction[t])

Шаг 3: Meta-Label = binary
  meta_label[t] = 1 если primary_correct[t] AND сделка была прибыльной
  meta_label[t] = 0 в остальных случаях

Шаг 4: Собрать фичи для Meta-Model
  features[t] = [
    primary_confidence,      // насколько уверен primary model
    adx,                     // сила тренда
    rsi,                     // перекупленность
    atr_ratio,               // волатильность / средняя
    volume_ratio,            // объём / средний
    hour_of_day,             // цикличность
    bars_since_last_signal,  // время между сигналами
    consecutive_wins,        // серия побед/поражений
  ]

Шаг 5: Обучить бинарный классификатор
  meta_model.fit(features, meta_label)
```

### 4.4 Почему Meta-Labeling решает проблему конфликтов

**Классический подход (без meta-labeling):**
```
Trend = LONG, Osc = BLOCK → что делать?
  → Нужны правила, приоритеты, веса
  → Правила статичны, не адаптируются
```

**Meta-labeling подход:**
```
Trend = LONG, Osc = BLOCK → Primary Model говорит LONG
  → Meta-Model получает фичи: [conf_trend=0.8, adx=32, rsi=75, atr_ratio=1.2, ...]
  → Meta-Model обучалась на исторических данных
  → Она «видела» такие случаи раньше: в 40% случаев primary был прав
  → P(correct) = 0.40 < threshold 0.55 → SKIP
  → Результат: не торгуем, не потому что «правило», а потому что данные говорят
```

**Преимущества:**
1. **Data-driven**: не ручные правила, а статистика
2. **Adaptive**: если рынок меняется, meta-model переобучается
3. **Handles conflicts**: видит комбинации фичей (RSI=75 + ADX=32 → skip, но RSI=75 + ADX=45 → trade)
4. **Asymmetric bet sizing**: P(correct) = 0.6 → размер × 0.6; P(correct) = 0.9 → полный размер

### 4.5 Edge Cases Meta-Labeling

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Meta-model всегда говорит «skip» | Нет сделок, нет прибыли | Min threshold = 0.45 (торгуем когда > 45% уверенности) |
| Meta-model никогда говорит «skip» | Нет фильтрации, все сделки | Threshold = 0.55 (консервативный) |
| Meta-model overfit | Хорошо на трейне, плохо на тесте | Purged K-Fold валидация |
| Первичная модель не обучена | Нет meta-features | Rule-based fallback |
| Концепт-drift | Мета-модель устаревает | Retrain каждые 1000 баров или при просадке > 10% |

### 4.6 Meta-Labeling: конкретная реализация

**Для MVP (без ML):**
```rust
/// Rule-based meta-labeling (без обучения модели)
/// Использует эвристики, основанные на комбинациях фичей
pub struct RuleBasedMetaLabel;

impl RuleBasedMetaLabel {
    /// Возвращает P(correct) ∈ [0, 1]
    pub fn estimate_probability(&self, features: &MetaFeatures) -> f64 {
        let mut score = 0.5; // базовая вероятность

        // ADX сильный → primary model чаще прав
        if features.adx > 35.0 { score += 0.15; }
        else if features.adx < 20.0 { score -= 0.15; }

        // RSI экстремум → primary model чаще ошибается
        if features.rsi > 75.0 || features.rsi < 25.0 { score -= 0.10; }

        // Высокая волатильность → больше шума → primary ошибается
        if features.atr_ratio > 1.5 { score -= 0.10; }

        // Объём подтверждает → primary правее
        if features.volume_confirms { score += 0.10; }
        if features.volume_diverges { score -= 0.15; }

        // Серия поражений → систематическая проблема
        if features.consecutive_losses >= 3 { score -= 0.20; }

        // Время суток: тихие часы → больше ложных сигналов
        if features.hour_utc >= 0 && features.hour_utc <= 4 { score -= 0.10; }

        score.clamp(0.0, 1.0)
    }
}

pub struct MetaFeatures {
    pub adx: f64,
    pub rsi: f64,
    pub atr_ratio: f64,       // ATR / ATR_20d_average
    pub volume_confirms: bool, // CVD в направлении сигнала
    pub volume_diverges: bool, // OBV дивергенция
    pub consecutive_losses: u32,
    pub hour_utc: u32,
    pub primary_confidence: f64,
}
```

**Для production (с ML, v0.5):**
```rust
/// XGBoost-based meta-labeling
pub struct MLBasedMetaLabel {
    model: XGBoostModel, // загруженная обученная модель
}

impl MLBasedMetaLabel {
    pub fn predict(&self, features: &MetaFeatures) -> f64 {
        let input = features.to_vec(); // все фичи в вектор
        self.model.predict_proba(&input)[1] // P(class=1 = correct)
    }
}
```

---

## 5. Финальный выбор: 1–3 лучших метода

### 🏆 ТОП-1: Regime-Conditional Weighted Combination

**Почему:**

| Критерий | Оценка |
|----------|--------|
| Решает конфликты | ✅ Разные веса для разных режимов |
| Адаптивность | ✅ Режим определяется динамически |
| Интерпретируемость | ✅ Понятно, почему каждый вес такой |
| Сложность реализации | 🟡 Средняя (нужен regime detector) |
| Требует ML | ❌ Нет (rule-based regime detection) |
| Edge cases | ✅ Плавный переход между режимами |

**Формула (финальная):**
```
regime = detect_regime(adx, ema_cross, hurst, atr_percentile)

direction_score = Σᵢ wᵢ(regime) × signalᵢ × confidenceᵢ

IF direction_score > threshold_long(regime):
    direction = LONG
    confidence = direction_score
ELIF direction_score < threshold_short(regime):
    direction = SHORT
    confidence = |direction_score|
ELSE:
    direction = FLAT
```

### 🏆 ТОП-2: Meta-Labeling (Rule-based → ML на v0.5)

**Почему:**

| Критерий | Оценка |
|----------|--------|
| Решает конфликты | ✅ Data-driven фильтрация |
| Адаптивность | ✅ Обучается на данных |
| Интерпретируемость | 🟡 Rule-based: да. ML: частично |
| Сложность реализации | 🟡 Rule-based: низкая. ML: высокая |
| Уникальная функция | ✅ Единственный метод, который решает «СТОИТ ли торговать» отдельно от «ЧТО торговать» |

**Применение: после Regime-Conditional Combination**
```
1. Regime-Conditional определяет направление + confidence
2. Meta-Labeling решает: стоит ли исполнять
3. IF meta_probability > threshold → EXECUTE с size = confidence × Kelly
4. ELSE → SKIP
```

### 🏆 ТОП-3: Veto Rules + Confidence-Weighted (встроенный элемент)

**Почему:**

| Критерий | Оценка |
|----------|--------|
| Безопасность | ✅✅ Абсолютный veto при критических условиях |
| Простота | ✅ Несколько if-else |
| Незаменимость | ✅ Ни один метод без veto небезопасен |

**Veto — не самостоятельный метод комбинации, а обязательный слой поверх любого.**

### Итоговая архитектура (MVP v0.1)

```
┌─────────────────────────────────────────────────┐
│                   INPUT SIGNALS                  │
│  Trend: {direction, confidence}                  │
│  Oscillator: {direction, confidence}             │
│  Volume: {direction, confidence}                 │
│  Volatility: {regime_signal, atr}                │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│          LEVEL 0: VETO CHECK                     │
│  circuit_breaker? Kelly > 0? Max trades?         │
│  IF veto → output FLAT, size=0                   │
└──────────────────────┬──────────────────────────┘
                       │ pass
                       ▼
┌─────────────────────────────────────────────────┐
│    LEVEL 1: REGIME DETECTION                     │
│  adx + ema_cross + hurst + atr_pct → regime      │
│  → regime_weights[trend, osc, vol, volume]        │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│    LEVEL 2: REGIME-CONDITIONAL COMBINATION       │
│  score = Σ wᵢ(regime) × signalᵢ × confidenceᵢ  │
│  → raw_direction, raw_confidence                 │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│    LEVEL 3: META-LABELING FILTER                 │
│  P(correct) = meta_estimate(features)            │
│  IF P(correct) < threshold → SKIP                │
│  ELSE → direction = raw_direction                │
│       confidence = raw_confidence × P(correct)   │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│    LEVEL 4: POSITION SIZING                      │
│  size = Kelly_fraction × confidence               │
│       × circuit_breaker_multiplier               │
│       × volatility_modifier                      │
│  size = min(size, max_position_pct × capital)     │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│    OUTPUT: TradingDecision                       │
│  {                                               │
│    direction: LONG | SHORT | FLAT,               │
│    confidence: f64 ∈ [0, 1],                     │
│    size: f64 (в % от капитала),                  │
│    regime: Regime,                               │
│    veto: Option<VetoReason>,                     │
│    meta_probability: f64,                        │
│    timestamp: u64,                               │
│  }                                               │
└─────────────────────────────────────────────────┘
```

---

## 6. Rust-архитектура

### 6.1 Core Types

```rust
/// Направление торгового решения
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Direction {
    Long,
    Short,
    Flat,
}

/// Режим рынка (для regime-conditional weighting)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MarketRegime {
    TrendUp,
    TrendDown,
    Range,
    HighVol,
}

/// Сигнал от одного агента
#[derive(Debug, Clone)]
pub struct AgentSignal {
    pub agent_id: &'static str,
    pub direction: Direction,
    pub confidence: f64,   // [0, 1]
    pub timestamp: u64,
}

/// Финальное торговое решение
#[derive(Debug, Clone)]
pub struct TradingDecision {
    pub direction: Direction,
    pub confidence: f64,
    pub size_pct: f64,        // % от капитала
    pub regime: MarketRegime,
    pub meta_probability: f64,
    pub veto_reason: Option<VetoReason>,
    pub raw_score: f64,       // до meta-labeling
    pub timestamp: u64,
}
```

### 6.2 Alpha Combiner — главная структура

```rust
pub struct AlphaCombiner {
    // Level 0: Veto
    veto_checker: VetoChecker,

    // Level 1: Regime detection
    regime_detector: RegimeDetector,

    // Level 2: Regime-conditional weights
    /// weights[regime_idx][agent_idx]
    regime_weights: [[f64; 4]; 4],

    // Level 3: Meta-labeling
    meta_labeler: RuleBasedMetaLabel,

    // Level 4: Position sizing
    kelly_sizer: KellySizer,
    circuit_breaker: CircuitBreaker,

    // Config
    config: CombinerConfig,
}

#[derive(Debug, Clone)]
pub struct CombinerConfig {
    pub threshold_long: f64,      // 0.30
    pub threshold_short: f64,     // -0.30
    pub meta_threshold: f64,      // 0.55
    pub max_position_pct: f64,    // 0.05
    pub adx_trend_threshold: f64, // 30.0
    pub adx_range_threshold: f64, // 25.0
}

impl AlphaCombiner {
    pub fn new(config: CombinerConfig) -> Self {
        Self {
            veto_checker: VetoChecker::new(),
            regime_detector: RegimeDetector::new(),
            regime_weights: [
                // [TrendUp, TrendDown, Range, HighVol]
                // Agent order: [Trend, Oscillator, Volume, Volatility]
                [0.50, 0.20, 0.20, 0.10], // TrendUp
                [0.50, 0.20, 0.20, 0.10], // TrendDown
                [0.10, 0.45, 0.25, 0.20], // Range
                [0.30, 0.15, 0.20, 0.35], // HighVol
            ],
            meta_labeler: RuleBasedMetaLabel,
            kelly_sizer: KellySizer::new(50),
            circuit_breaker: CircuitBreaker::new(0.12, 0.15, 24),
            config,
        }
    }

    pub fn combine(
        &mut self,
        signals: &[AgentSignal; 4], // [Trend, Osc, Vol, Volume]
        market_state: &MarketState,
        capital: f64,
    ) -> TradingDecision {
        // Level 0: Veto
        let veto = self.veto_checker.check(market_state);
        if veto.is_vetoed {
            return TradingDecision::vetoed(veto.reason.unwrap(), market_state.timestamp);
        }

        // Level 1: Regime
        let (regime, regime_conf) = self.regime_detector.detect(market_state);
        let regime_idx = regime as usize;

        // Level 2: Regime-conditional combination
        let mut score = 0.0;
        let mut total_weight = 0.0;

        for (i, signal) in signals.iter().enumerate() {
            let weight = self.regime_weights[regime_idx][i];
            let dir_value = match signal.direction {
                Direction::Long => 1.0,
                Direction::Short => -1.0,
                Direction::Flat => 0.0,
            };
            score += weight * dir_value * signal.confidence;
            total_weight += weight;
        }

        let raw_score = if total_weight > f64::EPSILON {
            score / total_weight
        } else {
            0.0
        };

        // Determine raw direction
        let raw_direction = if raw_score > self.config.threshold_long {
            Direction::Long
        } else if raw_score < self.config.threshold_short {
            Direction::Short
        } else {
            Direction::Flat
        };

        if raw_direction == Direction::Flat {
            return TradingDecision::flat(market_state.timestamp);
        }

        // Level 3: Meta-labeling
        let meta_features = MetaFeatures::from_signals(signals, market_state);
        let meta_prob = self.meta_labeler.estimate_probability(&meta_features);

        if meta_prob < self.config.meta_threshold {
            return TradingDecision::skipped(
                raw_direction, meta_prob, market_state.timestamp
            );
        }

        // Level 4: Position sizing
        let kelly = self.kelly_sizer.calc_fraction(0.5, 0.25);
        let cb_mult = self.circuit_breaker.position_multiplier();
        let confidence = raw_score.abs() * meta_prob * regime_conf;
        let size = (kelly * confidence * cb_mult)
            .min(self.config.max_position_pct);

        TradingDecision {
            direction: raw_direction,
            confidence,
            size_pct: size,
            regime,
            meta_probability: meta_prob,
            veto_reason: None,
            raw_score,
            timestamp: market_state.timestamp,
        }
    }
}
```

### 6.3 Regime Detector

```rust
pub struct RegimeDetector {
    adx_threshold_trend: f64,
    adx_threshold_range: f64,
    hurst_threshold: f64,
    atr_percentile_threshold: f64,
}

impl RegimeDetector {
    pub fn new() -> Self {
        Self {
            adx_threshold_trend: 30.0,
            adx_threshold_range: 25.0,
            hurst_threshold: 0.55,
            atr_percentile_threshold: 0.95,
        }
    }

    pub fn detect(&self, state: &MarketState) -> (MarketRegime, f64) {
        // High volatility check (приоритет)
        if state.atr_percentile > self.atr_percentile_threshold {
            return (MarketRegime::HighVol, 0.8);
        }

        // Trending
        if state.adx > self.adx_threshold_trend && state.hurst > self.hurst_threshold {
            if state.ema_fast > state.ema_slow {
                return (MarketRegime::TrendUp, 0.9);
            } else {
                return (MarketRegime::TrendDown, 0.9);
            }
        }

        // Ranging
        if state.adx < self.adx_threshold_range && state.hurst < 0.45 {
            return (MarketRegime::Range, 0.7);
        }

        // Пограничный: blend (неуверенный)
        (MarketRegime::Range, 0.4)
    }
}
```

### 6.4 Computational Complexity

| Уровень | Операции | Сложность |
|---------|----------|-----------|
| Veto Check | 5 сравнений | O(1) |
| Regime Detection | 4 сравнения | O(1) |
| Combination | 4 умножений + сумма | O(1) |
| Meta-Labeling | ~10 арифметических операций | O(1) |
| Position Sizing | 4 умножений | O(1) |
| **Итого** | **~25 операций** | **O(1)** |

**Память:** ~200 байт для всей структуры `AlphaCombiner`. Один cache line.

---

## 7. Конфигурация

```yaml
# === Alpha Combination (config.yaml) ===
alpha_combination:
  # --- Regime-Conditional Weights ---
  weights:
    trend_up:   [0.50, 0.20, 0.20, 0.10]  # [Trend, Osc, Vol, Volume]
    trend_down: [0.50, 0.20, 0.20, 0.10]
    range:      [0.10, 0.45, 0.25, 0.20]
    high_vol:   [0.30, 0.15, 0.20, 0.35]

  # --- Thresholds ---
  threshold_long: 0.30
  threshold_short: -0.30
  meta_threshold: 0.55

  # --- Regime Detection ---
  regime:
    adx_trend: 30.0
    adx_range: 25.0
    hurst_trend: 0.55
    hurst_range: 0.45
    atr_percentile_high: 0.95

  # --- Meta-Labeling ---
  meta:
    mode: "rule_based"  # "rule_based" | "xgboost" (v0.5)
    # Rule-based weights для P(correct) estimation
    adx_bonus: 0.15
    adx_penalty: 0.15
    rsi_extreme_penalty: 0.10
    high_vol_penalty: 0.10
    volume_confirm_bonus: 0.10
    volume_diverge_penalty: 0.15
    loss_streak_penalty: 0.20
    quiet_hours_penalty: 0.10
```

---

## Итоговая сводка

### Выбранные методы

| Место | Метод | Роль | Статус |
|-------|-------|------|--------|
| 🥇 | **Regime-Conditional Weighting** | Primary combination method | MVP v0.1 |
| 🥈 | **Meta-Labeling** | Signal quality filter | MVP v0.1 (rule-based), v0.5 (ML) |
| 🥉 | **Veto Rules** | Safety layer | MVP v0.1 (встроен в любой метод) |

### Отклонённые методы

| Метод | Причина |
|-------|---------|
| Simple Weighted Average | Не адаптируется к режиму, теряет конфликты |
| Majority Vote | Не учитывает силу сигналов |
| Bayesian Ensemble | Требует historical likelihood, сложная калибровка |
| Stacking | Требует ML-инфраструктуры, v0.5 |
| Boosting | Риск каскадных ошибок |
| Dempster-Shafer | Сложная реализация, нет Rust-библиотек |
| Fuzzy Logic | Субъективные правила |
| Online Learning | Нестабилен на коротких окнах, v0.5 |
| Copula-Based | Слишком сложно для комбинации сигналов |
| Portfolio Mean-Variance | Неприменим к сигналам |

### Ключевые инсайты

1. **Режим — это всё.** В тренде трендовые индикаторы правы в 65% случаев. Во флэте — осцилляторы в 70%. Неправильные веса = потеря edge.

2. **Meta-labeling — это фильтр качества, не комбинация.** Он отвечает на вопрос «стоит ли торговать», а не «что торговать». Комбинация и meta-labeling — два разных слоя.

3. **Veto — не метод комбинации, а предохранитель.** Ни один алгоритм не спасёт, если нет veto на Circuit Breaker и Kelly ≤ 0.

4. **Конфликт тренд vs. осциллятор — не баг, а фича.** Перекупленность в тренде = сильный тренд. Разрешение через regime-dependent weights: в тренде тренд доминирует (0.50), осциллятор вторичен (0.20).

5. **O(1) на бар — все методы.** Ни один выбранный метод не требует O(n) вычислений. Regime detection, combination, meta-labeling — всё O(1).

---

*Документ: 25-alpha-combination.md*  
*Агент 25 — Специалист по комбинации альфа-сигналов*  
*Дата: 17 апреля 2026*