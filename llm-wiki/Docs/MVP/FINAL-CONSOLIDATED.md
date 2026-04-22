
# УЛЬТИМАТИВНАЯ ТЕХНИЧЕСКАЯ ДОКУМЕНТАЦИЯ: КРИПТО-ТОРГОВЫЙ БОТ

> **Master Compiler:** Agent 31  
> **Дата компиляции:** 17 апреля 2026  
> **Входные файлы:** 30 файлов от агентов 1–30 + консилиум 4 улучшений  
> **Статус:** Финальная компиляция  
> **Язык реализации:** Rust (ядро), Python (бэктест/исследования)  
> **Целевая платформа:** Binance Spot/Futures, BTC/USDT, ETH/USDT, таймфрейм 1H  

---

## СОДЕРЖАНИЕ

1. [Executive Summary](#1-executive-summary)
2. [Asian Market Alpha — Микроструктурные сигналы](#2-asian-market-alpha--микроструктурные-сигналы)
3. [Core Engine Architecture](#3-core-engine-architecture)
4. [Ультимативный набор индикаторов и метрик](#4-ультимативный-набор-индикаторов-и-метрик)
5. [ML-слой: Meta-Labeling](#5-ml-слой-meta-labeling-фильтр-сигналов)
6. [Фундаментальный риск-фильтр](#6-фундаментальный-риск-фильтр)
7. [Риск-менеджмент и сайзинг](#7-риск-менеджмент-и-сайзинг)
8. [Бэктестинг и валидация](#8-бэктестинг-и-валидация)
9. [Конфликты между агентами и резолюции](#9-конфликты-между-агентами-и-резолюции)
10. [MVP v0.1 Implementation Plan](#10-mvp-v01-implementation-plan)
11. [Appendix: Magic Numbers Reference Table](#11-appendix-magic-numbers-reference-table)

---

## 1. Executive Summary

### Обзор проекта

Крипто-торговый бот — модульная алгоритмическая система на Rust, предназначенная для торговли BTC/USDT и ETH/USDT на Binance (spot + futures) с таймфреймом 1H (основной), 15M (тайминг), 4H/1D (контекст).

### Ключевые архитектурные решения

| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| Язык | Rust | O(1) обновления, zero-cost абстракции, SIMD, async WebSocket |
| Биржа | Binance | Ликвидность #1, низкие комиссии (0.1%), REST + WebSocket API |
| Таймфрейм | 1H primary | Баланс между шумом и латентностью |
| Стратегия | Trend-following + regime detection | Крипта — trending рынок ~60% времени |
| Риск-модель | ATR + Half-Kelly + MaxDD Circuit Breaker | Адаптивность к волатильности |
| Бэктест | Walk-Forward + Purged K-Fold | Anti-overfitting, realistic simulation |

### Технологический стек

```
Ядро:           Rust 1.75+, async (tokio), serde, rust_decimal
WebSocket:      tokio-tungstenite (Binance streaming), zero-alloc JSON parsing
REST:           reqwest (Binance REST API)
Хранение:       QuestDB/ClickHouse (тики, свечи, order book — columnar, SQL)
                SQLite — только конфигурация и состояние (позиции, настройки)
Индикаторы:     Ring buffer в памяти (1000 bars), O(1) обновления
                Никаких пересчётов массива (O(N) запрещено)
ML (inference): XGBoost → ONNX → Rust ort crate (<1ms на бар)
ML (training):  Python (xgboost, scikit-learn, Boruta) offline
Фундаменталы:   FRED API, TokenUnlocks API, CoinGlass WS, CryptoPanic
Бэктест:        Rust (custom engine) + Python (визуализация)
Мониторинг:     Prometheus + Grafana
```

### Сигнальная архитектура (4 слоя)

```
СЛОЙ 1 — МИКРОСТРУКТУРА (Агенты 7, 30):
  OBI + Kyle's Lambda + VPIN + Spoofing/OCR + Funding Delta + TBSR
  → понимание реального потока ордеров и манипуляций стаканом

СЛОЙ 2 — БАЗОВЫЙ ТЕХАНАЛИЗ (Агенты 1, 2, 3):
  EMA crossover + ADX > 25 + Supertrend + RSI/StochRSI + OBV + VWAP
  → направление тренда и точки входа

СЛОЙ 3 — ML-ФИЛЬТР (Section 5):
  XGBoost meta-labeling на фичах: лаговые доходности, ATR z-score,
  CVD slope, funding z-score, distance to VWAP, OBI, micro-price, beta
  → EXECUTE / BLOCK сигнал

СЛОЙ 4 — ФУНДАМЕНТАЛЬНЫЙ РИСК-ФИЛЬТР (Section 6):
  FOMC, CPI, token unlocks, hacks, regulatory news → HALT / RESUME
  → остановка перед событиями, которые ломают теханализ

СЛОЙ 5 — РИСК-КОНТРОЛЬ (Агент 5):
  ATR-SL/TP + Half-Kelly sizing + MaxDD Circuit Breaker + CVaR
  → контролирует размер и останавливает при превышении лимитов
```

### Фазы разработки

| Фаза | Версия | Содержание | Срок |
|------|--------|-----------|------|
| MVP | v0.1 | EMA crossover + ADX + OBV + ATR-SL + Kelly | Недели 1–3 |
| Alpha | v0.2 | StochRSI + Fisher + VWAP + MFI + VaR | Недели 4–6 |
| Beta | v0.3 | HMM regimes + GARCH + HP filter + CVD + Volume Profile | Недели 7–10 |
| Production | v0.4 | Order Flow (OBI, Kyle, VPIN) + Hilbert + Johansen | Недели 11–14 |
| Advanced | v0.5+ | Options + Sentiment + ML meta-labeling + Arbitrage | Недели 15+ |

---

## 2. Asian Market Alpha — Микроструктурные сигналы

> **Источник:** Агент 30 — APAC / Chinese Market Intelligence  
> **Исходники:** APAC Intelligence.md, Weibo/Zhihu парсинг, блоги разработчиков Binance/OKX Market Makers  
> **Философия:** Азиатские HFT-команды не торгуют голый RSI или MACD. Их алгоритмы строятся вокруг анализа ликвидности и механики биржи.

---

### 2.1 Детекция спуфинга в стакане (Order Book Spoofing Detection)

**Проблема:** Азиатские киты постоянно манипулируют стаканом Binance. Они ставят плиту на 500 BTC, чтобы толкнуть цену вниз, а за миллисекунду до исполнения снимают её. Классический теханализ (RSI, Bollinger) не видит эти манипуляции, потому что работает с ценой, а не со стаканом.

#### Метрика: Order Cancellation Ratio (OCR)

**Логика:** Бот анализирует поток L2 (Depth Update). Если на уровне N лимитный ордер объёмом > 10 BTC появляется и исчезает без сделок (Fill) более 3 раз за минуту, этот уровень помечается как Фейковый (Spoof).

```
Для каждого уровня стакана (bid/ask) на протяжении 60 секунд:
  1. Отслеживать каждый лимитный ордер > THRESHOLD (10 BTC / 500K USDT)
  2. Считать: сколько раз ордер появляется → исчезает без исполнения
  3. Если count_appear_disappear > 3 за 60 сек → уровень помечен как SPOOF

OCR_level = Cancel_Events(level) / Total_Events(level)
OCR_aggregate = Σ OCR_level × Volume_weight(level) для всех уровней

Spoof_Signal = OCR_aggregate > 0.7  И  |ΔOBI| > 0.3 за 500ms  И  Price_Δ ≈ 0
```

**Где:**
- `Cancel_Events(level)` — количество появлений и исчезновений ордера без исполнения
- `Total_Events(level)` — общее количество событий на уровне (появление + изменение + отмена + исполнение)
- `Volume_weight(level)` — вес уровня по объёму (ближайшие уровни важнее)
- `ΔOBI` — изменение Order Book Imbalance за 500ms
- `Price_Δ` — движение цены за тот же период (≈0 = ордер не исполнялся, значит был ложным)

#### Edge Cases

| Ситуация | Проблема | Решение |
|----------|----------|---------|
| Ордер снят, когда цена ушла далеко | Это обычный repricing маркет-мейкера, не спуфинг | Фильтр: считать спуфингом только если \|Price − Order_Level\| < 10 bps в момент снятия |
| Ордер снят, когда цена подошла вплотную (< 10 bps) | Классический спуфинг: создать видимость сопротивления, снять перед исполнением | Это SPOOF. Пометить уровень как фейковый на 5 минут |
| Частые обновления стакана (> 1000/сек) | Производительность: OCR-калькулятор не успевает | Ring buffer per level, O(1) обновление, batch processing каждые 500ms |
| DEX (AMM): нет лимитных ордеров | Неприменимо | Только для CEX с L2 order book |

#### Пороговые значения

| Порог | Значение | Интерпретация |
|-------|----------|---------------|
| Минимальный объём ордера для отслеживания | 10 BTC / 500K USDT | Ниже — шум от retail |
| Порог «исчезновение без сделки» | 3 раза за 60 сек | Более 3 раз — систематический спуфинг |
| Расстояние до цены для классификации | < 10 bps | Если ордер снят ближе 10 bps от цены — спуфинг |
| OCR aggregate порог | > 0.7 | Высокая вероятность манипуляции |
| Время пометки уровня как «спуф» | 5 минут | После пометки — игнорировать объём на этом уровне |

#### Применение для бота

```
OBI-сигнал (Агент 7) → Проверка OCR → Если спуфинг → Заблокировать сигнал
                    → Если нет спуфинга → Передать в Layer 2 (теханализ)
```

---

### 2.2 Cross-Exchange Funding Arbitrage (Zhihu Alpha)

**Что делают киты:** Они парсят Funding Rate на Binance, OKX и Bybit. Если на Binance шорты платят лонгам (Funding < −0.05%), а на Bybit лонги платят шортам (Funding > 0.05%), они открывают шорт на Bybit и лонг на Binance. Это рыночно-нейтральная дельта, приносящая до 40% годовых.

#### Формула

```
Funding_Delta_A_B = FR_exchange_A − FR_exchange_B

Для 3 бирж (Binance, OKX, Bybit):
  Δ_BINANCE_OKX   = FR_Binance − FR_OKX
  Δ_BINANCE_BYBIT = FR_Binance − FR_Bybit
  Δ_OKX_BYBIT     = FR_OKX − FR_Bybit

Weighted_Funding_Delta = (Δ_BINANCE_OKX × V_OKX + Δ_BINANCE_BYBIT × V_Bybit) 
                         / (V_OKX + V_Bybit)
где V — объём деривативов на бирже
```

#### Сигнальная логика для бота

**Нам не нужно торговать арбитраж сразу, но бот должен использовать Cross-Exchange Funding Delta как предиктор.**

```
Если |Δ| > 0.1% между Binance и Bybit:
  → Одна из бирж готовится к ликвидационному сквизу
  → Бот БЛОКИРУЕТ все трендовые сигналы
  → Потому что направление сквиза непредсказуемо

Если |Δ| > 0.02% но < 0.1%:
  → Значимое расхождение
  → Уменьшить confidence трендовых сигналов на 50%
  → Arb-возможность (информационная, не торговая)

Если |Δ| < 0.02%:
  → В пределах шума
  → Стандартная торговля
```

#### Пороговые значения

| Порог | Интерпретация |
|-------|---------------|
| \|Δ\| > 0.1% за 8ч | Экстремальное расхождение → БЛОКИРОВАТЬ трендовые сигналы |
| \|Δ\| > 0.05% за 8ч | Сильное расхождение → коррекция за 2–4ч |
| \|Δ\| > 0.02% за 8ч | Значимое расхождение → arb-возможность |
| \|Δ\| < 0.02% | В пределах шума → стандартная торговля |

#### OKX специфика

- **Контракты в USD (coin-margined):** OKX предлагает BTC/USD perpetual с расчётом в BTC. Китайские институционалы предпочитают это для cash-and-carry без USDT-риска.
- **Funding каждые 4 часа** (не 8 как Binance) на некоторых парах → более частые выплаты, но и более частые смены направления.
- **Block trading desk:** OKX имеет OTC-блок для крупных funding arb (> $10M), что недоступно на Binance.

---

### 2.3 Taker Buy/Sell Ratio (Binance Specific)

**Инструмент:** Анализ агрессивных рыночных сделок (Taker). Taker — это участник, который снимает ликвидность (ставит market order). Отношение покупок к продажам показывает, кто агрессивнее: быки или медведи.

#### Формула

```
TBSR = Taker_Buy_Volume / Taker_Sell_Volume   за окно N (N=20 баров)

TBSR_Z = (TBSR_current − μ_TBSR) / σ_TBSR   (Z-score по окну 20)

Divergence_Confirmation = Price ↑  И  TBSR ↓  → медвежья дивергенция (истощение покупателя)
Divergence_Reversal     = Price ↓  И  TBSR ↑  → бычья дивергенция (истощение продавца)
```

#### Паттерн «Истощение» (Exhaustion)

Если цена растёт, но Taker Buy Ratio падает (то есть рост идёт за счёт того, что маркет-мейкеры убирают аски, а не за счёт реальных покупок), это паттерн «Истощение». Азиатские трейдеры шортят такие движения.

```
Exhaustion Pattern:
  Цена:          ↗ ↗ ↗ ↗ (растёт)
  TBSR:          ↗ ↗ ↘ ↘ (падает)
  OBI:           стабильный или ↘ (маркет-мейкер убирает аски)
  
  Интерпретация: рост «на пустоте», нет реального покупательского давления
  Действие:      Заблокировать LONG-сигналы / подготовить SHORT
```

#### Пороговые значения

| TBSR | Значение |
|------|----------|
| > 1.5 | Покупатели доминируют (агрессивный спрос) |
| 1.2–1.5 | Умеренные покупки |
| 0.8–1.2 | Равновесие |
| 0.7–0.8 | Продавцы доминируют |
| < 0.7 | Агрессивные продажи |
| Divergence (Price↑ + TBSR↓ на 2+ бара) | Предупреждение о развороте |

#### Применение для бота

```
TBSR работает как «барометр агрессии»:
- Растёт цена + TBSR растёт   → тренд здоровый, продолжать
- Растёт цена + TBSR падает   → истощение покупателя, готовиться к развороту
- Падает цена + TBSR растёт   → накопление, возможен отскок
- Падает цена + TBSR падает   → медвежий тренд подтверждён

TBSR → передаётся в Layer 3 (ML) как фича для meta-labeling
```

---

### 2.4 Multi-Instrument CVD (практика китайских квантов)

Шанхайские HFT-фонды (Wintermute Asia, Amber Group, Nibbio Capital) строят **отдельные CVD** для каждого инструмента и сравнивают:

```
CVD_Spot_Binance vs CVD_Perp_OKX vs CVD_Options_Aevo

Если CVD_Spot > 0, а CVD_Perp < 0 → расхождение funding → закроется за 2–4ч
```

**Для бота:** Реализовать `MultiInstrumentCVD` — не один CVD, а вектор CVD по spot/perp/options каждой биржи.

### 2.5 VPIN + CVD связка

```
Если VPIN растёт И CVD расходится с ценой:
  → маркетмейкеры сужают спред или уходят с рынка
  → ликвидность падает → любой импульс усилится
  → СИГНАЛ: уменьшить позицию или выйти

VPIN > 0.4 + CVD_divergence = режим "toxic flow"
  → спреды расширяются до 0.15–0.3%
  → не торговать market orders
```

### 2.6 Биржи: ликвидность в азиатские часы

| Параметр | Binance | OKX | Bybit |
|----------|---------|-----|-------|
| **Аудитория** | Retail ЮВ-Азия (VN, PH, ID) | Институционалы HK/JP | Retail + SG |
| **Пик ликвидности UTC+8** | 14:00–17:00 | 10:00–16:00 | 10:00–18:00 |
| **Спред BTC/USDT** | 0.01–0.02% | 0.01–0.03% | 0.02–0.04% |

**Tier 1 пары (спред < 0.02%, глубина > $5M):** BTC/USDT, ETH/USDT  
**Tier 2 (0.02–0.05%, $1–5M):** SOL/USDT, XRP/USDT, DOGE/USDT

### 2.7 Временные паттерны азиатской сессии (UTC)

```
00:00–02:00 (Токио открытие):   ~60% от пика. Японские экономические данные.
02:00–06:00 ("тихие часы"):      30–40%. ⚠️ Thin liquidity + манипуляции MM.
06:00–09:00 ("power hours"):     80–100%. Шанхай закрывается → переток в крипто.
09:00–12:00 (Азия→Европа):       Высокая волатильность, расширение спредов.
```

### 2.8 Сезонность

| Праздник | Период | Объём | Стратегия |
|----------|--------|-------|-----------|
| **CNY (春节)** | 7–10 дней до + 3–5 после | −30–60% | Leverage ≤ 5x, SL +15–20% |
| **Golden Week** | 1–7 октября | −20–30% | Следить за PMI/GDP Китая |
| **Chuseok (Корея)** | Сен/Окт | −10–15% | Снижение Upbit/Bithumb |

---

## 3. Core Engine Architecture

### 3.1 Модульная архитектура

> **Синтез:** Агенты 24 (Architecture), 29 (Implementation Plan)

```
┌────────────────────────────────────────────────────────────────────────┐
│                           TRADING ENGINE                               │
│                                                                        │
│  ┌──────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ WebSocket Ingest │→│ Ring Buffer      │→│ Indicator Engine    │  │
│  │ (zero-alloc JSON │  │ (фиксированный   │  │ (O(1) обновления,  │  │
│  │  парсинг, in-place│  │  буфер, без      │  │  без пересчёта     │  │
│  │  десериализация) │  │  аллокаций)      │  │  всего массива)    │  │
│  └──────────────────┘  └─────────────────┘  └──────────┬──────────┘  │
│                                                          │             │
│  ┌──────────────────────────────────────────────────────▼──────────┐  │
│  │                    LAYER 1: МИКРОСТРУКТУРА                      │  │
│  │  OBI + Kyle's Lambda + VPIN + Spoofing/OCR + Funding Delta    │  │
│  └──────────────────────────────────────────────────────┬──────────┘  │
│                                                          │             │
│  ┌──────────────────────────────────────────────────────▼──────────┐  │
│  │                    LAYER 2: БАЗОВЫЙ ТЕХАНАЛИЗ                  │  │
│  │  EMA + ADX + Supertrend + RSI/StochRSI + OBV + VWAP          │  │
│  └──────────────────────────────────────────────────────┬──────────┘  │
│                                                          │             │
│  ┌──────────────────────────────────────────────────────▼──────────┐  │
│  │                    LAYER 3: ML-ФИЛЬТР (XGBoost)                │  │
│  │  Meta-labeling: EXECUTE / BLOCK на основе фичей               │  │
│  └──────────────────────────────────────────────────────┬──────────┘  │
│                                                          │             │
│  ┌──────────────────────────────────────────────────────▼──────────┐  │
│  │              LAYER 4: ФУНДАМЕНТАЛЬНЫЙ ФИЛЬТР                   │  │
│  │  FOMC / CPI / Token Unlocks / Hacks → HALT / RESUME          │  │
│  └──────────────────────────────────────────────────────┬──────────┘  │
│                                                          │             │
│  ┌──────────────────────────────────────────────────────▼──────────┐  │
│  │                    LAYER 5: РИСК-КОНТРОЛЬ                      │  │
│  │  ATR-SL/TP → Half-Kelly → MaxDD Circuit Breaker → CVaR       │  │
│  └──────────────────────────────────────────────────────┬──────────┘  │
│                                                          │             │
│  ┌──────────────────┐  ┌────────────────────────────────▼─────────┐  │
│  │ QuestDB/ClickHouse│ │ ORDER EXECUTOR                          │  │
│  │ (тики, свечи,    │ │ Square-Root Slippage → OCO → Binance    │  │
│  │  columnar storage)│ └─────────────────────────────────────────┘  │
│  └──────────────────┘                                                │
│  ┌──────────────────┐  ┌─────────────────────────────────────────┐  │
│  │ Regime Detector  │  │ Portfolio Manager (HRP)                 │  │
│  │ (HMM + ADX)      │  │ (5–7 assets, weekly rebalance)          │  │
│  └──────────────────┘  └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
Binance WebSocket (kline, trade, depth)
    ↓ [zero-alloc JSON parsing, in-place десериализация]
Ring Buffer (фиксированный буфер, 1000 bars, без аллокаций)
    ↓ [параллельно]
QuestDB / ClickHouse (columnar: тики, свечи, order book snapshots)
    ↓
Indicator Engine (параллельные O(1) обновления):
    ├─ Layer 1 — Микроструктура: OBI, Kyle, VPIN, OCR, Funding Delta, TBSR
    ├─ Layer 2 — Теханализ: EMA, ADX, Supertrend, RSI, StochRSI, OBV, VWAP
    ├─ Layer 3 — ML: XGBoost inference (<1ms, ONNX через Rust ort)
    ├─ Layer 4 — Фундаментал: calendar check → HALT/RESUME
    └─ Layer 5 — Риск: ATR, Kelly, Circuit Breaker, CVaR
    ↓
Order Executor (OCO, square-root slippage, Binance REST)
    ↓
Position Tracker + P&L → QuestDB
```

### 3.3 State Machine

```
         ┌──────────┐
         │  IDLE    │
         └────┬─────┘
              │ data_ready
         ┌────▼─────┐
         │ ANALYZE  │──→ regime detection, indicators (O(1))
         └────┬─────┘
              │ signal_generated (Layer 1+2)
         ┌────▼─────┐
         │ ML CHECK │──→ XGBoost meta-label (Layer 3)
         └────┬─────┘     P > 0.50?
              │ YES                    NO → DROP
         ┌────▼──────────┐
         │ FUNDAMENTAL   │──→ Calendar event? (Layer 4)
         │ CHECK         │     event → HALT
         └────┬──────────┘
              │ CLEAR
         ┌────▼─────┐     ┌──────────┐
         │  SIZE    │────→│ RISK_CHK │──→ circuit_breaker? (Layer 5)
         │ (Kelly)  │     └────┬─────┘         │
         └──────────┘          │ OK             │ HALT
                          ┌────▼─────┐    ┌────▼──────┐
                          │  EXECUTE │    │ SUSPENDED │
                          │  (OCO)   │    │ (4h timeout)
                          └────┬─────┘    └───────────┘
                               │ fill
                          ┌────▼─────┐
                          │ MONITOR  │──→ trailing stop, TP
                          └──────────┘
```

### 3.4 Ключевые модули Rust

```rust
// Основные структуры (референс)
pub struct TradingEngine {
    data_ingest: DataIngest,        // WebSocket + REST
    indicators: IndicatorEngine,    // все O(1) индикаторы
    signal_gen: SignalGenerator,    // комбинация сигналов (4 слоя)
    ml_filter: MetaLabelFilter,     // XGBoost inference (<1ms)
    fund_filter: CalendarFilter,    // FOMC/CPI/unlock gate
    risk_mgr: RiskManager,          // ATR + Kelly + CircuitBreaker
    executor: OrderExecutor,        // OCO + slippage
    regime: RegimeDetector,         // HMM + ADX
    portfolio: PortfolioManager,    // HRP allocation
    storage: TimeSeriesDB,          // QuestDB/ClickHouse client
}
```

### 3.5 Архитектура данных и производительность

> **Источник:** Рустам (Rust Performance Engineer), Марина (Data Engineer)

#### Хранение: QuestDB / ClickHouse (не SQLite)

**Проблема с SQLite:** Для MVP SQLite пойдёт, но для продакшена, когда мы будем считать Order Flow (сотни тиков в секунду), SQLite задохнётся из-за локов (Database is locked), а Parquet хорош только для чтения.

**Решение:**
- **QuestDB** — columnar time-series СУБД, написана на Java + C, оптимизирована для сверхбыстрой записи тиков
- **ClickHouse** — альтернатива от Yandex, SQL-совместимый, columnar, отличная компрессия
- **SQLite** — только конфигурация и состояние (текущие позиции, настройки)

```
QuestDB / ClickHouse:
  ├── Тики (trade data): timestamp, price, quantity, side, exchange
  ├── Свечи (OHLCV): timeframe, open, high, low, close, volume
  ├── Order Book snapshots: timestamp, bids[], asks[]
  ├── P&L journal: timestamp, position, pnl, fees
  └── Signal log: timestamp, signal, confidence, action

SQLite:
  ├── Config (YAML → SQLite для runtime)
  ├── Positions (текущие открытые позиции)
  └── State (last_bar_timestamp, regime, circuit_breaker_status)
```

#### In-Memory Ring Buffer

Все индикаторы (EMA, RSI, ADX) будут считаться «на лету» без обращения к базе данных. Rust будет хранить циклический буфер (Ring Buffer) на 1000 последних свечей в оперативной памяти.

```rust
/// Ring buffer фиксированного размера. Нет аллокаций после инициализации.
pub struct RingBuffer<const N: usize, T> {
    data: [MaybeUninit<T>; N],
    head: usize,      // следующая позиция для записи
    len: usize,       // текущее количество элементов
}

impl<const N: usize, T: Copy> RingBuffer<N, T> {
    #[inline(always)]
    pub fn push(&mut self, item: T) {
        self.data[self.head].write(item);
        self.head = (self.head + 1) % N;
        if self.len < N { self.len += 1; }
    }
    
    #[inline(always)]
    pub fn get(&self, index: usize) -> Option<&T> {
        if index >= self.len { return None; }
        let pos = (self.head + N - self.len + index) % N;
        Some(unsafe { self.data[pos].assume_init_ref() })
    }
    
    #[inline(always)]
    pub fn last(&self) -> Option<&T> {
        if self.len == 0 { return None; }
        let pos = (self.head + N - 1) % N;
        Some(unsafe { self.data[pos].assume_init_ref() })
    }
}
```

#### O(1) обновления индикаторов (запрещено O(N))

Когда приходит новый тик по WebSocket:

```
Шаг 1: Цена + Объём обновляют текущую свечу в памяти.
Шаг 2: Алгоритм O(1) обновляет значение каждого индикатора.

Пример — EMA:
  new_EMA = Price × alpha + old_EMA × (1 − alpha)    ← O(1), одно умножение + сложение

Пример — RSI:
  new_avg_gain = (old_avg_gain × (N−1) + gain) / N   ← O(1)
  new_avg_loss = (old_avg_loss × (N−1) + loss) / N   ← O(1)
  RSI = 100 − 100 / (1 + new_avg_gain / new_avg_loss) ← O(1)

Пример — ATR:
  new_ATR = (old_ATR × (N−1) + TrueRange) / N        ← O(1)

Никаких перерасчётов всего массива (O(N) ЗАПРЕЩЕНО).
```

#### Zero-Copy Deserialization (WebSocket)

При получении JSON от Binance WebSocket (он огромный — depth update может быть > 100KB), мы не выделяем память под строки. Rust использует `serde` с borrowing (`&str`), парся только нужные поля (price, quantity), экономя такты процессора и снижая аллокации.

```rust
/// Zero-copy десериализация kline сообщения от Binance.
/// Парсим только нужные поля, остальные игнорируются.
#[derive(Deserialize)]
struct KlineMessage<'a> {
    #[serde(rename = "e", borrow)]
    event_type: &'a str,
    #[serde(rename = "k")]
    kline: KlineData<'a>,
}

#[derive(Deserialize)]
struct KlineData<'a> {
    #[serde(rename = "t")]
    open_time: i64,
    #[serde(rename = "o", borrow)]
    open: &'a str,           // не аллоцируем String, используем &str
    #[serde(rename = "h", borrow)]
    high: &'a str,
    #[serde(rename = "l", borrow)]
    low: &'a str,
    #[serde(rename = "c", borrow)]
    close: &'a str,
    #[serde(rename = "v", borrow)]
    volume: &'a str,
    #[serde(rename = "x")]
    is_closed: bool,
}

/// Парсинг цены: str → f64 без аллокации
#[inline(always)]
fn parse_price(s: &str) -> f64 {
    // Быстрый парсер: ищем точку, целая и дробная части
    // Без создания String, без format!()
    fast_float::parse(s).unwrap_or(0.0)
}
```

#### Batching для записи в QuestDB

```rust
/// Батчинг тиков: собираем N тиков в буфер, отправляем одним TCP-пакетом
pub struct TickBatcher {
    buffer: Vec<Tick>,
    batch_size: usize,        // обычно 100–1000 тиков
    flush_interval: Duration, // или каждые 100ms, что наступит раньше
}

impl TickBatcher {
    pub fn add(&mut self, tick: Tick) {
        self.buffer.push(tick);
        if self.buffer.len() >= self.batch_size {
            self.flush();
        }
    }
    
    async fn flush(&mut self) {
        if self.buffer.is_empty() { return; }
        // Отправляем батч через TCP в QuestDB (ILP protocol)
        // Не блокируем торговый цикл (async)
        self.questdb_client.send_batch(&self.buffer).await;
        self.buffer.clear();
    }
}
```

#### Производительность (бенчмарк-цели)

| Операция | Цель | Метод |
|----------|------|-------|
| WebSocket parse (одно сообщение) | < 5µs | Zero-copy serde |
| Ring buffer push | < 10ns | Array-based, no alloc |
| EMA update (O(1)) | < 5ns | Single mul + add |
| RSI update (O(1)) | < 10ns | Wilder smoothing |
| ADX update (O(1)) | < 20ns | TR + DM + smoothing |
| XGBoost inference (ONNX) | < 1ms | ort crate, batch=1 |
| QuestDB batch write (100 ticks) | < 500µs | Async TCP, ILP protocol |
| Полный цикл (tick → signal → decision) | < 2ms | Все операции суммарно |

---

## 4. Ультимативный набор индикаторов и метрик

> Выжимка от Агентов 1–27.  
> Формат: **Инструмент → Применение → Забракованная альтернатива → Причина → Edge case**

---

### 4.1 Индикаторы тренда

**Источник:** Агент 1 — Trend Indicators

#### Финалисты

| Инструмент | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----------|--------------------------|-------------------|-----------|
| **EMA(20)/EMA(50) crossover** | Primary тренд-сигнал. EMA(20) > EMA(50) = LONG | SMA | Равные веса → запаздывает на 25–50% амплитуды. На крипте с движениями 10%/час потеря 2.5–5% критична | Flash crash (−15% за свечу): EMA(20) сдвигается на 1.43%, кроссовер запаздывает на 2–3 бара |
| **KAMA (Kaufman Adaptive MA)** | Adaptive фильтр тренд/флэт. Efficiency Ratio определяет скорость | DEMA | Двойное сглаживание создаёт осцилляции на флэте. Коэффициент 2 — эмпирическая подгонка. DEMA генерирует 2–3× больше ложных сигналов | Efficiency Ratio → 0 (флэт): KAMA = предыдущее значение (замирает) |
| **VWAP (00:00 UTC reset)** | «Справедливая цена» дня. Цена ниже VWAP = дёшево, выше = дорого | Anchored VWAP (AVWAP) | Требует ручного/полуавтоматического выбора якорной точки. Отложен до v0.3 | Нулевой объём в начале сессии: VWAP = NaN. Fallback: Typical Price первого тика |
| **Supertrend** | Trailing stop & разворот. ATR-based, подстраивается под волатильность | Parabolic SAR | SAR генерирует больше ложных сигналов на флэте (~40% vs ~25% у Supertrend). Не адаптируется к волатильности | ATR → 0: полосы сжимаются до линии. Min distance = max(2×ATR, 0.5%×Close) |
| **ADX(14) + DI** | Фильтр: ADX > 25 = есть тренд, < 25 = флэт. +DI > −DI = бычий | Aroon | Нечувствителен. Дублирует ADX. Нет нормализации 0–100 | ADX запаздывает ~N/2 баров. Комбинировать с EMA slope |
| **Ichimoku Kinko Hyo** | Комплексный: Kumo как support/resistance + Tenkan/Kijun crossover | — (уникальная) | Сложность (5 линий, 13/26/52 периоды). Но даёт уникальную информацию | Kumo twist: переход через облако → зона неопределённости |

#### Отклонённые индикаторы тренда

| Индикатор | Причина отклонения |
|-----------|-------------------|
| SMA | Равные веса, лаг 25–50% |
| DEMA | Осцилляции на флэте, эмпирический коэффициент |
| TEMA | Тройное сглаживание, ещё больше артефактов |
| WMA | Линейные веса без теоретического обоснования |
| HMA | Комбинация WMA+WMA, квадратичный корень без обоснования |
| T3 | 6 EMA, чрезмерная сложность |
| ZLEMA | Look-ahead bias (сдвиг на (n−1)/2) |
| Tillson T3 | Дублирует T3, сложная калибровка |
| Kaufman ER | Компонент KAMA, не standalone |
| VIDYA | Заменён на KAMA (лучше) |
| Jurik MA | Proprietary, не верифицируем |
| LSMA | Линейная регрессия — лаг |
| McGinley Dynamic | Нет порогов, нестабильный |
| FRAMA | Сложность фрактальной размерности |

---

### 4.2 Осцилляторы и моментум

**Источник:** Агент 2 — Oscillators & Momentum

#### ТОП-3 финалиста

| Инструмент | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----------|--------------------------|-------------------|-----------|
| **Stochastic RSI(14,3,3)** | Тайминг входа: выход из зоны перепроданности при бычьем тренде | Обычный Stochastic | StochRSI в 2× быстрее реагирует на развороты. Обычный Stochastic слишком сглажен | Все бары растут: RSI=100, StochRSI=100. Clamp при AvgLoss=0 |
| **Fisher Transform(9)** | Разворот: Fisher crossover = смена моментума. Нормализован [−2, +2] | TSI (True Strength Index) | Двойной лаг (двойное сглаживание). Fisher быстрее и чище | Экстремальные значения Fisher > ±3 редки и нестабильны |
| **CCI(20)** | Экстремумы: CCI > 100 = перекуплен, < −100 = перепродан | Williams %R | Инвертированный Stochastic. Не даёт нового. CCI лучше нормализован | H−L = 0 (doji): CCI = NaN. Защита: min(H−L) = tick_size |

#### Сохранённые (не ТОП-3, но в системе)

| Инструмент | Роль | Пороги |
|-----------|------|--------|
| **RSI(14)** | Фильтр перекупленности | < 30 перепродан, > 70 перекуплен, 50 — нейтраль |
| **MACD(12,26,9)** | Моментум + кроссовер + дивергенция | Histogram > 0 = бычий моментум |

#### Отклонённые осцилляторы

| Индикатор | Причина отклонения |
|-----------|-------------------|
| Awesome Oscillator | Нет порогов. Дублирует MACD |
| Elliott Wave | Субъективен. Не алгоритмизируем |
| DeMarker | Информативно беден. RSI лучше |
| PPO | Дублирует MACD. Нет сигнальной линии |
| KST | 13 параметров. Переобучение |
| Coppock Curve | Для месячных данных |
| Chande MO | CMO = 2×RSI − 100. Полная избыточность |
| Elder Ray | Нет нормализации, нет порогов |
| Aroon | Нечувствителен. Дублирует ADX |
| DPO | Look-ahead bias |
| Vortex | Дублирует ADX+DI |

---

### 4.3 Объёмные индикаторы

**Источник:** Агент 3 — Volume Indicators

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **OBV** | v0.1 | Дивергенция OBV vs цена → ранний разворот | Price Volume Trend (PVT) | Похож на OBV, но сложнее — без преимущества | Flash crash wick: OBV резко меняется. Winsorize при \|delta\| > 3σ |
| **VWAP** | v0.2 | Справедливая цена, S/R уровень | TWAP | Не учитывает объём. VWAP строго информативнее | Китовый тик ($10M): VWAP сдвигается. Использовать VWAP bands |
| **MFI(14)** | v0.2 | Объёмный RSI. MFI > 80 = перекупленность с объёмным подтверждением | Volume Weighted RSI | MFI уже делает это (RSI + объём) | Все TP растут: Negative MF = 0 → MFI = 100. Корректно |
| **CVD (Cumulative Volume Delta)** | v0.3 | Order flow lite: покупатель vs продавец | Up/Down Volume Ratio | Дублирует CVD | Tick rule неточность без L2: ~5–10% ошибок классификации |
| **Volume Profile** | v0.3 | POC, Value Area High/Low — уровни поддержки/сопротивления | VAP (Volume at Price) | VAP — упрощённый Volume Profile для dashboard, не для сигналов | Многоуровневый профиль: память O(N×bins). Использовать статистический аппроксиматор |

---

### 4.4 Волатильность

**Источник:** Агент 5 — Risk Management, Агент 6 — Statistical Models

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **ATR(14)** | v0.1 | SL/TP расстояние, position sizing, trailing stop | Historical Volatility (σ) | ATR использует True Range (учитывает gaps), σ — только Close. На крипте с gaps ATR точнее | ATR → 0: SL_distance → 0, PositionSize → ∞. Fix: min SL = max(2×ATR, 0.5%×Entry) |
| **Bollinger Bands(20,2)** | v0.2 | Squeeze detection (полосы сжимаются → breakout) | Keltner Channels | BB использует σ (чувствительнее), KC — ATR (плавнее). Для squeeze detection BB лучше | Полосы > 20% от цены (мемкоины): сигналы ненадёжны |
| **GARCH(1,1)** | v0.3 | Прогноз условной волатильности | EGARCH, GJR-GARCH | Сложнее калибровки, преимущество незначительно на крипте | α+β → 1 (IGARCH): волатильность не возвращается к средней |
| **Historical Volatility (σ)** | v0.2 | Нормализация, сравнение активов | — | Используется в GARCH, VaR, Kelly | Зависит от окна: 20 vs 60 дней даёт разные значения |

---

### 4.5 Order Flow и микроструктура

**Источник:** Агент 7 — Order Flow

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **OBI (multi-level, K=10, γ=0.5)** | v0.3 | Прямой предиктор движения цены (>60% дисперсии ΔP за 1 сек) | Book Pressure | Встроен в OBI (OBI — более полная версия) | Пустая книга (одна сторона): OBI = ±1. Проверять min_volume > 0 |
| **Kyle's Lambda** | v0.3 | Стоимость ликвидности, оптимальный размер ордера | Amihud Illiquidity | Не order flow, а метрика ликвидности. Kyle строго лучше для trading | Мало наблюдений (< 100): λ нестабилен. Rolling OLS с window ≥ 200 |
| **VPIN** | v0.4 | Детектор токсичности order flow, flash crash predictor | Hawkes Process | Высокая сложность, выгода < OBI+Kyle | Bucket size влияет на VPIN. Использовать_bulk_classification |

#### Отклонённые

| Инструмент | Причина |
|-----------|---------|
| Roll Spread | Предположения нарушены на крипте (noisy) |
| Queue Position | Нужен для HFT/market making, не для swing |
| Hidden Orders | Дубликат Iceberg Detection |
| Liquidity Heatmap | Визуализация, не quantitative |
| Almgren-Chriss | Модуль исполнения, не сигнализации |

---

### 4.6 Статистические модели

**Источник:** Агент 6 — Statistical Models

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **HMM (Gaussian, 3 состояния)** | v0.3 | Определение режима: Bull/Bear/Range | CUSUM, Chow Test | HMM лучше определяет regimes (continuous vs discrete breaks) | < 1000 баров: недооценка параметров. Multi-start EM (10+ запусков) |
| **GARCH(1,1)** | v0.3 | Прогноз условной волатильности | GARCH(2,2) | Нет преимущества над GARCH(1,1) на крипте | α+β ≈ 0.97: волатильность кластеризуется |
| **ADF + KPSS тесты** | v0.3 | Проверка стационарности (пара) | Phillips-Perron | Избыточен (ADF покрывает тот же use case) | Structural breaks: стандартный ADF не обнаруживает. Zivot-Andrews как альтернатива |
| **Hurst Exponent (R/S)** | v0.3 | Память рынка: H > 0.5 = тренд, H < 0.5 = mean-reversion | DFA | R/S проще и стандартнее | Короткие ряды (< 200): H нестабилен |
| **Kalman Filter** | v0.3 | Динамический hedge ratio, сглаживание | Particle Filter | O(N²) частиц, Kalman достаточно | Не-гауссовость: Kalman assumes Gaussian |
| **Johansen Test** | v0.4 | Коинтеграция корзины активов | VAR, VECM | Слишком много параметров для walk-forward | Нет stationarity → Johansen ненадёжен |

#### Отклонённые статистические модели

| Модель | Причина |
|--------|---------|
| ARIMA | Линейность, нестабильно на крипте |
| VAR | Требует stationarity, мало данных |
| VECM | Слишком много параметров |
| Ornstein-Uhlenbeck | Предполагает mean-reversion, circular reasoning |
| Particle Filter | Слишком дорогой |
| BSTS | Медленный для real-time |

---

### 4.7 Mean Reversion

**Источник:** Агент 14 — Mean Reversion

#### Gate Rule (критерий торгова)
```
Можно торговать MR ⟺ ADF p-value < 0.05 И KPSS p-value > 0.05
```

| Инструмент | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----------|--------------------------|-------------------|-----------|
| **Pairs Trading + Kalman Filter** | Коинтегрированные пары (BTC/ETH). Kalman для динамического hedge ratio | Ornstein-Uhlenbeck на цене | Предполагает MR, circular reasoning. Pairs + Kalman не требует a priori MR assumption | Hedge ratio расходится: ре-калибровка каждые 500 баров |
| **Funding Rate OU (Ornstein-Uhlenbeck)** | MR на funding rate (H ≈ 0.25–0.35, строго стационарный) | MR на цене BTC | Цена BTC нестационарна (ADF p > 0.90). Funding rate гарантированно возвращается к 0 каждые 8ч | FR на cap (0.75%): истинный дисбаланс неизвестен |
| **Johansen Basket** | Коинтеграция корзины (3+ актива) | Engle-Granger (2 актива) | Johansen обрабатывает 3+ актива. Engle-Granger только пары | < 3 коинтегрированных актива → fallback к pairs |

---

### 4.8 Арбитраж

**Источник:** Агент 15 — Arbitrage

| Инструмент | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----------|--------------------------|-------------------|-----------|
| **Triangular Arbitrage** | A→B→C→A на одной бирже. Безрисковый при Net_Profit > 0.05% | Cross-Exchange Arb | Нужен перевод между биржами (риск + latency). Triangular — на одной бирже | Partial fill: одна нога частично. Решение: FOK ордера |
| **Statistical Arbitrage (Pairs)** | Коинтегрированные пары с Kalman hedge ratio | Latency Arb | Требует < 1ms colocation. Недоступно для retail | Структурный break: коинтеграция распадается. Мониторинг ADF |
| **Basis Arbitrage (Cash-and-Carry)** | Покупка спот + продажа фьючерса. Конвергенция к экспирации | DEX-CEX Arb | Газ-fee + impermanent loss + smart contract risk | Ранняя экспирация: фьючерс не конвергирует |

#### Отклонённые

| Стратегия | Причина |
|-----------|---------|
| Funding Rate Harvesting | Долгий холдинг (дни), высокий капитал |
| Latency Arbitrage | Нужна colocation (< 1ms) |
| DEX-CEX Arbitrage | Газ, IL, smart contract risk |
| Options Put-Call Parity | Ликвидность опционов на крипте низкая |

---

### 4.9 Крипто-специфичные метрики

**Источник:** Агент 16 — Crypto-Specific

| Метрика | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|---------|-----|-----------|--------------------------|-------------------|-----------|
| **Funding Rate** | v0.1 | Z-score > +2 = перекупленность (шорт), < −2 = перепроданность (лонг) | Fear & Greed (как primary) | FNG обновляется раз в день, FR — каждые 8ч. FR точнее для деривативов | FR на cap (0.75%): истинный дисбаланс неизвестен. Флаг cap_reached |
| **Open Interest** | v0.1 | ΔOI + Price: OI↑+Price↑ = новые лонги (бычий), OI↑+Price↓ = новые шорты | Exchange Net Flow | OI — деривативный, Net Flow — on-chain. OI быстрее | Нет данных по OI на всех биржах. Агрегация через CoinGlass |
| **Liquidation Clusters** | v0.4 | Каскадные ликвидации → уровни support/resistance | — (уникальная) | — | Редкие события. Не для повседневной торговли |
| **Futures Basis** | v0.3 | Contango = оптимизм, Backwardation = пессимизм | Taker Buy/Sell Ratio | Basis даёт более прямой сигнал о настроениях деривативов | Экспирация квартала: basis → 0. Фильтровать даты экспирации |
| **Long/Short Ratio** | v0.2 | Дисбаланс: L/S > 1.5 = экстремальный лонг | Whale Alerts | L/S стандартизирована, Whale — нет | Разные биржи дают разные L/S |

---

### 4.10 On-Chain метрики

**Источник:** Агент 17 — On-Chain Analytics

| Метрика | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|---------|-----|-----------|--------------------------|-------------------|-----------|
| **MVRV Z-Score** | v0.3 | Z > 7 = продавать, Z < 0 = покупать. Лучший макро-индикатор цикла | NUPL | Производная MVRV, не даёт новой информации | Потерянные монеты (3–4M BTC) занижают Realized Cap на ~15–20% |
| **SOPR** | v0.4 | SOPR < 1 = капитуляция (покупка), SOPR > 1 = прибыль (осторожность) | Coin Days Destroyed | Производная HODL Waves, дублирует SOPR | SOPR = 1.0 — сильный support/resistance |
| **Exchange Net Flow** | v0.4 | Net inflow = распределение (медвежий), net outflow = накопление (бычий) | Active Addresses | Лагает, нет чётких порогов, легко манипулируется | Миграция биржа → холодный → биржа: обновляет realized price |

#### Отклонённые On-Chain метрики

| Метрика | Причина |
|---------|---------|
| NVT Ratio | Лагает, шумная, дублирует Exchange Flow |
| Puell Multiple | Только BTC майнеры, не применима к альтам |
| Stock-to-Flow | Модель опровергнута эмпирически (2022) |
| Hash Rate | Нет торговых сигналов, лагает на 2+ недели |
| SSR (Stablecoin Supply Ratio) | Низкая чувствительность |
| HODL Waves | Визуальная, нет числовых порогов для бота |

---

### 4.11 Сигнальная обработка

**Источник:** Агент 13 — Signal Processing

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **Hodrick-Prescott Filter (λ=6 для 1H)** | v0.3 | Разделение тренд/цикл. Цикл = mean-reversion точки | SSA (Singular Spectrum Analysis) | Сложная настройка (выбор L), HP проще и лучше | Граничные значения: mirror padding на 3 точки |
| **Wavelet Denoising (DWT + Soft Thresholding)** | v0.3 | Оптимальное удаление шума, сохраняет локальные фичи | Median Filter | Удаляет spikes, но сглаживает ценовые паттерны | Выбор wavelet: Daubechies db4 оптимален для цен |
| **Hilbert Transform → Instantaneous Phase** | v0.4 | Фаза рынка (экспансия/коррекция), уникальный сигнал | Bandpass Filter (Butterworth) | Требует a priori знания частот, неадаптивный | Фазовые сбои на границах: обрезать первые/последние 5% |

#### Отклонённые

| Метод | Причина |
|-------|---------|
| FFT / DFT | Assumes stationarity, ужасен для крипты |
| CWT | Слишком дорогой O(N·Nₛ) |
| EMD / EEMD | Mode mixing, нестабильные компоненты |
| Savitzky-Golay | Производная-ориентированный, лагает на крипте |
| Adaptive Wiener | Требует noise variance |

---

### 4.12 ML-модели

> **Источник:** Агент 25 (Alpha Combination), собственный синтез (Макс — ML-инженер, Дон — Статистик)

#### Спор: LSTM vs XGBoost

| Критерий | XGBoost | LSTM |
|----------|---------|------|
| **Тип данных** | Табличные фичи (идеально для нас) | Последовательности (временные ряды) |
| **Скорость inference** | <1ms на бар | 5–20ms на бар |
| **Устойчивость к шуму** | Высокая (bagging + subsampling) | Низкая (переобучается на шум финансовых данных) |
| **Интерпретируемость** | SHAP values — видим топ-фичи | Чёрный ящик |
| **Обучение** | Минуты (CPU) | Часы (GPU) |
| **Затухание градиента** | Нет (tree-based) | Да (на длинных последовательностях) |
| **Production deploy** | ONNX → Rust `ort` crate | Требует `tch-rs` или Python bridge |
| **Kaggle финансы** | Выигрывает в 90% соревнований | Редко побеждает на табличных данных |

**Резолюция спора:** Макс предлагал LSTM для работы с рядами. Дон забраковал: LSTM требует огромных вычислительных мощностей и страдает от затухания градиента на шумных финансовых данных. XGBoost на табличных, правильно отнормированных фичах (Lagged returns, Volatility Z-scores) бьёт LSTM в 90% Kaggle-соревнований по финансам.

**Итоговое решение: XGBoost (Binary: Logloss objective).**

#### Meta-Labeling: концепция

```
Primary Model (наш СЛОЙ 1 на Rust):  Генерирует сигналы LONG / SHORT по EMA + ADX
Secondary Model (ML XGBoost):         Получает этот сигнал и решает:
                                       Разрешить (1) или Заблокировать (0)

Ключевое: модель НЕ предсказывает направление.
Она отвечает на вопрос: «стоит ли исполнять этот конкретный сигнал?»
```

**Почему это работает:** Базовая стратегия (EMA + ADX) генерирует много сигналов. Часть из них прибыльны, часть убыточны. ML-модель учится отличать «хорошие» сигналы от «плохих» на основе контекста (фичей). Это не предсказание цены — это фильтрация качества.

#### Обучение

```
Данные: 2 года 1H баров BTC/USDT (~17,500 наблюдений)
Метка: y = 1 если |PnL_сделки| > ATR за период холда, иначе y = 0
Train: Purged K-Fold (K=5) с embargo = 2 × holding_period
Метрика: AUC-ROC (target ≥ 0.60 для production)

Параметры XGBoost:
  objective = binary:logistic
  max_depth = 6
  n_estimators = 200
  learning_rate = 0.1
  subsample = 0.8
  colsample_bytree = 0.8
  scale_pos_weight = auto (балансировка классов)
  eval_metric = auc

Inference: <1ms на бар → не bottleneck
Deploy: xgboost.save_model() → ONNX → Rust ort crate
```

#### Пороги

| P(прибыльный) | Действие |
|---------------|----------|
| > 0.65 | EXECUTE — высокая уверенность |
| 0.50–0.65 | EXECUTE с уменьшенным size (×0.5) |
| < 0.50 | BLOCK — модель не уверена |

#### Edge Cases в ML

| Проблема | Решение |
|----------|---------|
| **Look-ahead bias при Z-score** | Фича Z-score считается ТОЛЬКО на прошлых данных (expanding window или rolling window). Функция sklearn.preprocessing.StandardScaler на всём датасете строго ЗАПРЕЩЕНА |
| **Feature Importance шум** | Используем алгоритм Boruta для удаления фичей, которые вносят шум |
| **Data snooping** | Один набор параметров на все фолды. Никакого cherry-picking |
| **Regime shift** | Модель обученная на bull market, теряет силу на bear. Перекалибровка каждые 500 баров |
| **Class imbalance** | В bull market ~60% сигналов прибыльны. scale_pos_weight = n_negative / n_positive |

---

### 4.13 Feature Engineering (ТОП-10 фичей для XGBoost)

> **Источник:** Макс (ML-инженер), Дон (Статистик)

Вместо сырых цен, мы подаём стационарные (ADF-checked) фичи. Сырые цены запрещены — они нестационарны и приводят к spurious correlations.

#### ТОП-10 фичей

| # | Фича | Формула | Зачем | ADF p-value |
|---|------|---------|-------|-------------|
| 1 | **Return_Lag_1** | log(Close_t / Close_{t−1}) | Краткосрочная динамика, momentum | < 0.01 ✓ |
| 2 | **Return_Lag_3** | log(Close_t / Close_{t−3}) | Среднесрочная динамика | < 0.01 ✓ |
| 3 | **Return_Lag_5** | log(Close_t / Close_{t−5}) | Среднесрочная динамика | < 0.01 ✓ |
| 4 | **Return_Lag_10** | log(Close_t / Close_{t−10}) | Недельная динамика (на 1H) | < 0.01 ✓ |
| 5 | **Return_Lag_20** | log(Close_t / Close_{t−20}) | Долгосрочная динамика | < 0.01 ✓ |
| 6 | **Vol_Z_Score(20)** | (ATR(14) − μ_ATR) / σ_ATR, окно 20 | Нормализованная волатильность: squeeze или expansion | < 0.05 ✓ |
| 7 | **CVD_Slope(5)** | Наклон линейной регрессии CVD за 5 баров | Ускорение/замедление order flow | < 0.01 ✓ |
| 8 | **Funding_Z_Score** | (FR − μ_FR) / σ_FR, окно 30 | Перекупленность/перепроданность деривативов | < 0.01 ✓ |
| 9 | **Distance_to_VWAP_Pct** | (Price − VWAP) / VWAP × 100 | Насколько далеко цена от «справедливой» | < 0.05 ✓ |
| 10 | **StochRSI_K_D_Diff** | StochRSI_K − StochRSI_D | Скорость разворота осциллятора | < 0.01 ✓ |

#### Дополнительные фичи (для production v0.3+)

| # | Фича | Формула | Зачем |
|---|------|---------|-------|
| 11 | **Micro_Price_vs_Mid** | (Best_Ask×Q_bid + Best_Bid×Q_ask) / (Q_bid + Q_ask) − Mid | Смещение micro-price → направление краткосрочного движения |
| 12 | **Candle_Body_to_Wick_Ratio** | \|Close − Open\| / (High − Low) | Уверенность движения: 1.0 = полная свеча, 0.0 = доджи |
| 13 | **Order_Book_Imbalance_L5** | (Σ bids − Σ asks) / (Σ bids + Σ asks) на 5 уровнях | Перекос покупатели/продавцы в стакане |
| 14 | **BTC_Beta_Rolling(30)** | Cov(r_alt, r_BTC) / Var(r_BTC), окно 30 | (Только для альтов) Насколько зависим от BTC |
| 15 | **OCR_Aggregate** | Weighted OCR по уровням стакана | Уровень манипуляции стаканом |

#### Стационарность фичей

**Требование:** Каждая фича должна пройти ADF-тест (p-value < 0.05) перед подачей в XGBoost.

```
Фичи-кандидаты → ADF-тест → Прошли (p < 0.05) → Включены в модель
                         → Не прошли → Дифференциация → Повторный тест
                         → Всё ещё не прошли → Исключены
```

Лог-доходности (Return_Lag_*) — стационарны по определению (лог-разности цен). VWAP distance, Vol Z-score — нормализованы, поэтому стационарны. Funding Z-score — Z-score, стационарен.

#### Запрещённые фичи

| Фича | Причина запрета |
|------|----------------|
| Сырая цена (Close, Open, High, Low) | Нестационарна. ADF p > 0.10 |
| Сырой объём (Volume) | Нестационарен. Нужна нормализация (Z-score) |
| Сырой ATR | Нестационарен. Нужен Z-score (фича #6) |
| RSI без нормализации | Ограничен [0, 100], но нестационарен на коротких окнах |
| Сырой Funding Rate | Нестационарен. Нужен Z-score (фича #8) |

---

### 4.14 Опционы и деривативы

**Источник:** Агент 18 — Options & Derivatives

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **Black-Scholes-Merton** | v0.4 | Базовая модель ценообразования опционов. Все греки через BS | Monte Carlo GBM | BS аналитический (быстрее). MC нужен только для экзотиков | T → 0: C → max(S−K, 0). Greeks → step function |
| **Implied Volatility (Newton-Raphson)** | v0.4 | IV из рыночной цены. IV > HV → опционы дорогие | Historical Volatility | IV отражает рыночные ожидания, HV — прошлое | Newton-Raphson не сходится при extreme OTM: fallback к bisection |
| **Volatility Smile / Skew** | v0.4 | Кривая IV по страйкам → рыночные ожидания | — | — | Недостаточно ликвидных опционов: smile шумный |
| **Gamma Scalping** | v0.5 | Delta-neutral позиция + rebalance на движениях | Delta-Hedging (static) | Gamma scalping зарабатывает на волатильности, static hedge — нет | Комиссии rebalance могут превысить gamma profit |
| **Max Pain & Pinning** | v0.5 | Уровень Max Pain = где экспирация максимизирует убытки опционных держателей | — | — | Только вблизи экспирации |

#### Отклонённые опционные стратегии

| Стратегия | Причина |
|-----------|---------|
| Straddle/Strangle | Чистая ставка на волатильность, нет directional edge |
| Iron Condor | Чистая premium collection, нет alpha |
| Butterfly Spread | Слишком узкий профиль прибыли |
| Calendar Spread | Зависит от term structure vol, мало данных на крипте |

---

### 4.15 Sentiment Analysis

**Источник:** Агент 23 — Sentiment Analysis

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **Crypto Fear & Greed Index** | v0.3 | Contrarian: extreme fear (<20) = buy, extreme greed (>80) = sell | NVT как sentiment | NVT — on-chain метрика, не sentiment. FNG прямой sentiment | API обновляется раз в день. Только дневной контекст |
| **Twitter/X Sentiment (VADER/Transformer)** | v0.4 | Engagement-weighted sentiment. Spike → volatility warning | Google Trends | Trends lagging, нет направления | Боты: 30–50% крипто-твитов. Фильтр: account age > 30d, followers > 50 |
| **LunarCrush / Alternative Social** | v0.5 | Social volume + sentiment score | — | — | Pump groups: координированные твиты → spike без причины |

---

### 4.16 Управление портфелем

**Источник:** Агент 19 — Portfolio Management

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **Hierarchical Risk Parity (HRP)** | v0.2 | Аллокация активов. Не требует Σ⁻¹, не требует μ | Markowitz MVO | Estimation error убивает эффективность. Σ⁻¹ нестабильна | Singular matrix: HRP не требует обращения |
| **Inverse Volatility (Diagonal Risk Parity)** | v0.1 | Fallback для HRP. Простой, надёжный | Black-Litterman | Нет «мнений экспертов» для алгоритмического бота | Актив с σ ≈ 0: w → ∞. Max weight cap = 0.5 |
| **Fractional Kelly (Half-Kelly)** | v0.1 | Размер позиции. MaxDD ~25% vs 50% у Full Kelly | Optimal f (Vince) | Требует точного Largest Loss. Flash crash переписывает рекорд | Kelly ≤ 0: не торговать. Kelly > 1: cap на 25% |
| **Threshold Rebalancing** | v0.2 | Перебалансировка при отклонении > 10% | Calendar Rebalancing | Фиксированный график не адаптируется к волатильности | Threshold < 5%: чрезмерная торговля (комиссии) |

---

### 4.17 Режимы рынка

**Источник:** Агент 20 — Regime Detection

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **HMM (Gaussian, 3–4 состояния)** | v0.3 | Bull / Bear / (High Vol Range) / (Low Vol Range) | GMM standalone | Нет временной зависимости. Bull/Bear могут чередоваться каждый бар | Локальные максимумы EM: multi-start (10+ запусков) |
| **ADX threshold (ADX > 25)** | v0.1 | Быстрый фильтр: тренд vs флэт | Aroon | Нечувствителен. Дублирует ADX | ADX запаздывает ~N/2 баров |
| **Hurst Exponent** | v0.3 | H > 0.5 = trending, H < 0.5 = mean-reverting | — | — | < 200 наблюдений: H нестабилен |

#### Конфликт: 3 vs 4 состояния

> Агент 6 (Статистические модели) рекомендует 3 состояния (BIC минимум на N=3).  
> Агент 20 (Regime Detection) рекомендует 4 состояния (разделение High/Low Vol Range).  
> **Резолюция:** Начать с 3 (Bull/Bear/Range), обновить до 4 при наличии ≥ 5000 баров.

---

### 4.18 Временные ряды

**Источник:** Агент 21 — Time Series Analysis

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **GARCH(1,1)** | v0.3 | Условная волатильность | ARIMA | Линейность, нестабильно на крипте. ACF лог-доходностей ≈ 0 с лага 1 | α+β → 1: IGARCH (volatility не mean-reverts) |
| **Hurst Exponent (R/S)** | v0.3 | Память рынка | DFA | R/S проще и стандартнее | Короткие ряды: нестабилен |
| **Cointegration (Johansen)** | v0.4 | Корзина коинтегрированных активов | Engle-Granger | Только пары. Johansen — 3+ актива | Нет stationarity → Johansen ненадёжен |
| **Granger Causality** | v0.4 | X «Granger-causes» Y если прошлое X улучшает прогноз Y | Impulse Response Functions | IRF — более сложный, менее интерпретируемый | Spurious causality при non-stationarity |

#### Отклонённые методы анализа временных рядов

| Метод | Причина |
|-------|---------|
| ARIMA | Линейность, нестабильно. ACF ≈ 0 с лага 1 |
| SARIMA | Суточная сезонность на крипте слабая |
| Prophet | Предполагает сезонность + тренд, крипта — regime-switching |
| TBATS | Чрезмерная сложность для крипты |
| VAR | Требует stationarity, мало данных |

---

### 4.19 Кросс-валидация

**Источник:** Агент 27 — Cross-Validation

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **Purged K-Fold с Embargo** | v0.1 | Основной метод валидации. Embargo = 2×holding_period | Standard K-Fold | Look-ahead bias (обучение на будущих данных) | K ≥ N: каждый фолд < 2 наблюдений |
| **Walk-Forward (Expanding)** | v0.1 | Имитация реальной торговли. Train растёт, test — фиксированный шаг | LOO (Leave-One-Out) | Слишком высокая дисперсия, не для финансовых рядов | T_test слишком велик: мало итераций |
| **Monte Carlo Permutation** | v0.2 | Проверка: стратегия лучше случайного? p-value для Sharpe | Bootstrap (Moving Block) | MC permutation проще и не требует предположений о структуре | M < 1000: p-value нестабилен |
| **Deflated Sharpe Ratio** | v0.2 | Коррекция Sharpe на множественное тестирование | PBO (Probability of Backtest Overfitting) | DSR проще, PBO требует более сложной реализации | N_strategies < 2: DSR сводится к обычному Sharpe |

---

### 4.20 Качество данных

**Источник:** Агент 22 — Data Quality

| Проблема | Severity | Обнаружение | MVP | Решение |
|----------|----------|-------------|-----|---------|
| Missing Data (gaps) | 🔴 Critical | Timestamp diff > expected interval | v0.1 | 1 свеча: forward fill; 2–5: linear interpolation; >60: mark incomplete |
| Outliers / Flash Crashes | 🔴 Critical | Z-score > 4.0 + rate-of-change > 20% | v0.1 | Winsorize на 1%/99% перцентилях |
| Wash Trading | 🟠 High | Volume/Trade count ratio аномалия | v0.2 | Фильтр: trades < 1ms apart = wash |
| OHLCV Violations | 🔴 Critical | min(O) ≤ min(C)? H ≥ max(O,C)? | v0.1 | Автоматическая коррекция или удаление |
| Survivorship Bias | 🟠 High | Historical listing/delisting audit | v0.2 | Включать delisted токены в бэктест |
| Duplicate Candles | 🟡 Medium | Dedup by (exchange, pair, timestamp) | v0.1 | Hash-based dedup |
| Timezone Issues | 🟡 Medium | UTC enforcement | v0.1 | Всё в UTC ms |

---

### 4.21 Фундаменталы (Calendar & Macro Gate)

> **Источник:** Ольга (Бизнес-аналитик), Бен (Трейдер)  
> **Философия:** Бот не может торговать в вакууме. В крипте есть заранее известные события, которые ломают любой теханализ. Если через час заседание ФРС США (FOMC) или разлок 10% токенов SOL — никакие линии Боллинджера не спасут. Роботу нужно выключаться.

#### Что мы добавляем в ядро

**Token Unlocks API Integration:**

```
Вход: API TokenUnlocks (tokenunlocks.app/api)
Логика: Если у актива (например, ARB, SUI) запланирован разлок 
        более 2% циркулирующего предложения в ближайшие 48 часов:
  → Бот снимает все лимитные ордера на покупку
  → Блокирует LONG-сигналы
  → Существующие позиции: trailing stop (не закрывать заранее)
```

**Спор о шортировании разлоков:**
- Джон предлагал шортить разлоки (давление продаж → цена падает)
- Бен возразил: «Маркет-мейкеры часто пампят цену ПЕРЕД разлоком, чтобы выгрузиться об шортистов. Торговать это слишком рискованно»
- **Решение:** Нейтральная позиция (HALT). Не пытаться «угадать» направление.

**Macro Events (FOMC / CPI):**

```
Логика: За 60 минут до оглашения ставки ФРС или публикации инфляции (CPI):
  → Бот переходит в режим SUSPENDED
  → Существующие позиции: жёсткие стопы (Trailing Stop подтягивается)
  → Новые сигналы: все блокируются
  → Торговля возобновляется через 30 минут после новости,
    когда GARCH-волатильность возвращается в норму
```

#### События, требующие HALT

| Событие | Влияние | Окно HALT | Источник |
|---------|---------|-----------|----------|
| **FOMC (решение по ставке)** | BTC двигается 3–8% за минуты после объявления | −1ч до +30мин | FRED API |
| **CPI (инфляция США)** | 2–5% движение, направление непредсказуемо | −1ч до +30мин | FRED API |
| **Token Unlock (> 2% предложения)** | Прямое давление продаж, −5–15% за неделю | −48ч до +24ч | TokenUnlocks API |
| **Крупный hack/exploit** | Flash crash, паника | Немедленно | CryptoPanic API |
| **Regulatory news** | Бан крипты в крупной юрисдикции → обвал | Немедленно | CryptoPanic API |
| **ETF approval/rejection** | BTC 5–15% за час | −1ч до +4ч | Новостные API |
| **Крупная ликвидация (> $100M)** | Каскадный эффект | Пока OI не стабилизируется | CoinGlass WS |

#### Логика фильтра

```
Calendar Event → HALT Window

HALT:
  - Все новые сигналы → BLOCK
  - Открытые позиции → trailing stop (не закрывать заранее, но не открывать новые)
  - MaxDD circuit breaker → усиленный (L1 = 8% вместо 12%)

RESUME:
  - По истечении HALT окна
  - ИЛИ когда volatility возвращается к нормальному уровню (ATR z-score < 2)
  - ИЛИ когда spread возвращается к нормальному (спред < 2× обычного)
  - ИЛИ минимальное количество стабильных баров ≥ 10
```

#### Источники данных

| Источник | Данные | Частота |
|----------|--------|---------|
| **FRED API** | FOMC даты, CPI release dates | Ежемесячно |
| **TokenUnlocks.app API** | Calendar unlock events | Ежедневно |
| **CoinGlass** | Large liquidation alerts | Real-time |
| **CryptoPanic API** | Breaking news, regulatory | Real-time |
| **Config YAML** | Ручные даты (известные события) | Вручную |

#### Config

```yaml
fundamental_filter:
  enabled: true
  
  halt_events:
    fomc:
      halt_before_hours: 1
      halt_after_minutes: 30
      source: "fred_api"
    
    cpi:
      halt_before_hours: 1
      halt_after_minutes: 30
      source: "fred_api"
    
    token_unlock:
      min_unlock_pct_circulating: 2.0    # 2%+ циркулирующего предложения
      halt_before_hours: 48
      halt_after_hours: 24
      source: "tokenunlocks_api"
    
    large_liquidation:
      threshold_usd: 100000000    # $100M+
      halt_minutes: 30
      source: "coinglass_ws"
  
  resume_conditions:
    atr_zscore_below: 2.0
    spread_normalized: true
    min_stable_bars: 10
```

---

### 4.22 Комбинация альфа-сигналов

**Источник:** Агент 25 — Alpha Combination

| Инструмент | MVP | Применение | Забракованная альтернатива | Причина отклонения | Edge case |
|-----------|-----|-----------|--------------------------|-------------------|-----------|
| **Regime-Conditional Weighted Combination** ⭐ ТОП-1 | v0.1 | Разные веса для разных режимов (Bull: trend=0.5, Bear: risk=0.4, Range: osc=0.4) | Mean-Variance Combination | Комбинация сигналов ≠ комбинация активов. Сигналы не имеют «доходности» | Нет данных о режиме: fallback к equal weight |
| **Meta-Labeling (López de Prado)** ⭐ ТОП-2 | v0.3 | ML-фильтр: «стоит ли исполнять этот сигнал?» Binary classifier на фичах | Stacking (ML ensemble) | Требует ML-инфраструктуры. Не для MVP | False positive rate > 30%: порог слишком низкий |
| **Veto Rules** ⭐ ТОП-3 (доп.) | v0.1 | Circuit breaker + hard stops. Никакая комбинация не override риска | Fuzzy Logic | Правила нужно вручную писать. Субъективность | Слишком много veto rules → стратегия не торгует |

#### Сигнальная архитектура комбинации

```
Режим рынка → определяет веса:
  Bull Trend:    trend=0.50, osc=0.15, volume=0.20, order_flow=0.15
  Bear Trend:    trend=0.35, osc=0.15, volume=0.15, risk=0.35
  High Vol Range: osc=0.40, mr=0.30, volume=0.20, risk=0.10
  Low Vol Range:  trend=0.20, vol_squeeze=0.50, volume=0.20, risk=0.10

Veto (override):
  - MaxDD > 15% → HALT
  - CVaR > 10% Capital → HALT
  - Flash crash detected (1-bar PnL < −8%) → HALT
  - Kelly ≤ 0 → не торговать
```

---

## 5. ML-слой: Meta-Labeling (фильтр сигналов)

> **Философия:** Не предсказывать цену напрямую. Базовый сигнал дают EMA + ADX / Supertrend; ML-модель решает — **разрешить сигнал или заблокировать**.

### 5.1 Почему XGBoost, а не LSTM

| Критерий | XGBoost | LSTM |
|----------|---------|------|
| **Тип данных** | Табличные фичи (идеально) | Последовательности |
| **Скорость inference** | <1ms на бар | 5–20ms на бар |
| **Устойчивость к шуму** | Высокая (bagging) | Низкая (переобучается на шум) |
| **Интерпретируемость** | SHAP values (топ-фичи) | Чёрный ящик |
| **Обучение** | Минуты | Часы |
| **Production deploy** | `xgboost` Rust bindings или ONNX | Требует `tch-rs` или Python bridge |
| **Практический опыт в финансах** | López de Prado (Advances in FML) — стандарт | Эксперименты, но нет consistent edge |

**Вердикт: XGBoost.** Для табличных фич он проще, быстрее и устойчивее к шуму.

### 5.2 Meta-Labeling архитектура

```
Базовый сигнал (EMA + ADX + Supertrend)
    ↓
Набор фичей (лаговые доходности, ATR z-score, CVD slope, ...)
    ↓
XGBoost classifier: P(сигнал прибыльный | фичи)
    ↓
Если P > threshold → EXECUTE
Если P ≤ threshold → BLOCK
```

**Ключевое:** модель не предсказывает направление. Она отвечает на вопрос «стоит ли исполнять этот конкретный сигнал от базовой стратегии?»

### 5.3 Ключевые фичи

| # | Фича | Формула | Зачем |
|---|------|---------|-------|
| 1 | **Лаговые доходности** | r(t−1), r(t−2), r(t−5), r(t−10), r(t−20) | Краткосрочная динамика, momentum/reversion |
| 2 | **ATR z-score** | (ATR − μ_ATR) / σ_ATR, окно 20 | Нормализованная волатильность: squeeze или expansion |
| 3 | **CVD slope** | ΔCVD / Δt за последние 5 баров | Ускорение/замедление order flow |
| 4 | **Funding z-score** | (FR − μ_FR) / σ_FR, окно 30 | Перекупленность/перепроданность деривативов |
| 5 | **Distance to VWAP** | (Price − VWAP) / VWAP | Насколько далеко цена от «справедливой» |
| 6 | **Order Book Imbalance** | OBI multi-level (K=10, γ=0.5) | Перекос покупатели/продавцы в стакане |
| 7 | **Micro-price vs Mid** | (Best_Ask×Q_bid + Best_Bid×Q_ask) / (Q_bid + Q_ask) − Mid | Смещение micro-price → направление краткосрочного движения |
| 8 | **Beta к BTC** | Cov(r_alt, r_BTC) / Var(r_BTC), окно 60 | Для альтов: насколько зависим от BTC. Высокий beta = сигнал BTC доминирует |

### 5.4 Обучение и валидация

```
Данные: 2 года 1H баров BTC/USDT (~17,500 наблюдений)
Метка: y = 1 если |PnL_сделки| > ATR за период холда, иначе y = 0
Train: Purged K-Fold (K=5) с embargo = 2 × holding_period
Метрика: AUC-ROC (target ≥ 0.60 для production)

Параметры XGBoost (дефолт):
  max_depth = 6
  n_estimators = 200
  learning_rate = 0.1
  subsample = 0.8
  colsample_bytree = 0.8
  scale_pos_weight = auto (балансировка классов)

Inference: <1ms на бар → не bottleneck
Deploy: ONNX export → Rust `ort` crate для inference
```

### 5.5 Пороги

| P(прибыльный) | Действие |
|---------------|----------|
| > 0.65 | EXECUTE — высокая уверенность |
| 0.50–0.65 | EXECUTE с уменьшенным size (×0.5) |
| < 0.50 | BLOCK — модель не уверена |

---

## 6. Фундаментальный риск-фильтр

> **Философия:** Бот должен уметь останавливаться перед событиями, которые ломают теханализ. Не «угадывать» движение — а **HALT**.

### 6.1 События, требующие HALT

| Событие | Влияние | Окно HALT |
|---------|---------|-----------|
| **FOMC (решение по ставке)** | BTC двигается 3–8% за минуты после объявления | −4ч до +2ч после |
| **CPI (инфляция США)** | 2–5% движение, направление непредсказуемо | −2ч до +1ч после |
| **Token Unlock** | Прямое давление продаж. Крупные разлоки → −5–15% за неделю | −12ч до +24ч после |
| **Крупный hack/exploit** | Flash crash, паника | Немедленно, пока не оценён ущерб |
| **Regulatory news** | Бан крипты в крупной юрисдикции → обвал | Немедленно |
| **ETF approval/rejection** | BTC 5–15% за час | −1ч до +4ч после |
| **Крупная ликвидация (> $100M)** | Каскадный эффект | Пока OI не стабилизируется |

### 6.2 Логика фильтра

```
Calendar Event → HALT Window

HALT:
  - Все новые сигналы → BLOCK
  - Открытые позиции → trailing stop (не закрывать заранее, но не открывать новые)
  - MaxDD circuit breaker → усиленный (L1 = 8% вместо 12%)

RESUME:
  - По истечении HALT окна
  - ИЛИ когда volatility возвращается к нормальному уровню (ATR z-score < 2)
  - ИЛИ когда spread возвращается к нормальному (спред < 2× обычного)
```

### 6.3 Источники данных

| Источник | Данные | Частота |
|----------|--------|---------|
| **FRED API** | FOMC даты, CPI release dates | Ежемесячно |
| **TokenUnlocks.app API** | Calendar unlock events | Ежедневно |
| **CoinGlass** | Large liquidation alerts | Real-time |
| **CryptoPanic API** | Breaking news, regulatory | Real-time |
| **Config YAML** | Ручные даты (известные события) | Вручную |

### 6.4 Config

```yaml
fundamental_filter:
  enabled: true
  
  halt_events:
    fomc:
      halt_before_hours: 4
      halt_after_hours: 2
      source: "fred_api"
    
    cpi:
      halt_before_hours: 2
      halt_after_hours: 1
      source: "fred_api"
    
    token_unlock:
      min_unlock_usd: 10000000    # $10M+ разлок → HALT
      halt_before_hours: 12
      halt_after_hours: 24
      source: "tokenunlocks_api"
    
    large_liquidation:
      threshold_usd: 100000000    # $100M+
      halt_minutes: 30
      source: "coinglass_ws"
  
  resume_conditions:
    atr_zscore_below: 2.0
    spread_normalized: true
    min_stable_bars: 10
```

---

## 7. Риск-менеджмент и сайзинг

> **Источник:** Агент 5 — Risk Management

### 5.1 ATR-based Stop Loss / Take Profit

```
LONG:
  SL = Entry − k_SL × ATR(14)    где k_SL = 2.0
  TP = Entry + k_TP × ATR(14)    где k_TP = 3.0
  R:R = k_TP / k_SL = 1.5:1

SHORT:
  SL = Entry + k_SL_short × ATR(14)  где k_SL_short = 1.5
  TP = Entry − k_TP × ATR(14)        где k_TP = 3.0
  R:R = k_TP / k_SL_short = 2.0:1
```

**Адаптивность к волатильности:** при высоком ATR → широкие стопы, при низком → узкие. Не зависит от абсолютного уровня цены.

### 5.2 Position Sizing через Half-Kelly

```
Full Kelly:
  Kelly = (W × R − L) / R
  где W = WinRate, L = 1−W, R = AvgWin/AvgLoss

Half-Kelly:
  f = Kelly × 0.5

Position Size:
  PositionSize = min(f, MaxPct) × Capital / SL_distance
  где MaxPct = 0.05 (5% капитала на сделку)
```

**Пример:**
```
W = 0.55, R = 1.75, Capital = $10,000, ATR = $1,200, Entry = $42,000
Kelly = (0.55×1.75 − 0.45) / 1.75 = 0.2929
Half-Kelly = 0.1464
SL_distance = 2.0 × 1,200 = $2,400
PositionSize = min(0.1464, 0.05) × 10,000 / 2,400 = 0.2083 BTC
MaxLoss = 0.2083 × 2,400 = $500 (5% от капитала)
```

### 5.3 VaR и CVaR (Historical)

```
VaR_α = −Percentile(PnL_window, α)     α = 0.05 (95% CI)
CVaR_α = Mean(худшие ⌈α×N⌉ наблюдений)

Применение:
  CVaR > 10% Capital → стоп-торговля
  CVaR > 5% Capital → сократить позицию на 50%
```

**Почему Historical, а не Parametric:**
- Крипта: kurtosis ~9 (vs 3 нормального). Parametric VaR недооценивает риск в 2–3 раза.
- Historical не требует предположений о распределении.

### 5.4 MaxDD Circuit Breaker

```
CurrentDD = (Peak − CurrentCapital) / Peak

Уровни:
  L1 (Pre-warning): DD ≥ 12% → PositionSize × 0.5
  L2 (Full Stop):   DD ≥ 15% → halt all trading

Восстановление:
  - Новый торговый день (00:00 UTC), ИЛИ
  - DD < 10%, ИЛИ
  - Timeout 4 часа после Full Stop

Flash Crash подмодуль:
  Если PnL за 1 свечу < −8% Capital → немедленный Full Stop
```

### 5.5 Полная цепочка риска

```
Сигнал → ATR-SL/TP → Half-Kelly sizing → MaxDD check → CVaR check → Исполнение
                                          ↓ HALT
                                    Circuit Breaker
```

---

## 8. Бэктестинг и валидация

> **Источник:** Агент 27 — Cross-Validation

### 6.1 Walk-Forward Analysis

```
Параметры:
  train_ratio = 0.8
  T_test = T × (1 − 0.8) / K, где K ≥ 5
  Embargo = 2 × holding_period

Expanding Window:
  |===== TRAIN =====|== TEST ==|
  |========= TRAIN =========|== TEST ==|
  |============= TRAIN ============|== TEST ==|

Метрика: средний OOS Sharpe по всем фолдам
```

### 6.2 Purged K-Fold с Embargo

```
K = 5 фолдов
Embargo = 2 × holding_period (баров между train и test)

Для каждого фолда:
  1. Определить test fold
  2. Удалить из train наблюдения в embargo-зоне
  3. Обучить на purged train, протестировать на test
  4. Собрать все OOS предсказания
```

### 6.3 Monte Carlo Permutation Test

```
H₀: стратегия не лучше случайного
M = 10,000 перестановок

Для каждой перестановки i:
  1. Перемешать метки (buy/sell) случайно
  2. Рассчитать Sharpe_permuted(i)

p-value = count(Sharpe_permuted(i) ≥ Sharpe_actual) / M

Если p-value < 0.05 → стратегия статистически значима
```

### 6.4 Anti-Overfitting Protocol

```
1. ВСЕГДА использовать Walk-Forward (никакого in-sample оптимизма)
2. Один набор параметров на все фолды (no cherry-picking)
3. Deflated Sharpe Ratio: скорректировать на количество протестированных стратегий
4. Minimum OOS период: 20% от общего dataset
5. Sensitivity analysis: ±20% от каждого параметра → Sharpe не должен падать > 50%
```

---

## 9. Конфликты между агентами и резолюции

### Конфликт 1: HMM — 3 vs 4 состояния

| Сторона | Позиция |
|---------|---------|
| **Агент 6** (Статистические модели) | 3 состояния (Bull/Bear/Range). BIC минимум при N=3. Достаточно для 5000 баров. |
| **Агент 20** (Regime Detection) | 4 состояния (Bull/Bear/High Vol Range/Low Vol Range). Критическое различие: стратегия полностью меняется между High и Low Vol Range. |

**Резолюция:** Начать с 3 состояний (MVP v0.3). Обновить до 4 при наличии ≥ 5000 баров и подтверждении BIC.

### Конфликт 2: MACD периоды для крипты

| Сторона | Позиция |
|---------|---------|
| **Агент 2** (Осцилляторы) | Оставить 12/26/9 как дефолт. Дать возможность переопределения через config. Walk-forward оптимизация покажет лучшие значения. |
| **Агент 1** (Тренд) | На 1H крипты (8760 баров/год vs 252 у акций) периоды слишком быстрые. Пропорциональный масштаб: 24/52/9. |

**Резолюция:** Дефолт 12/26/9 (стандарт индустрии, совместимость с TradingView/Bloomberg). Config-based override для 24/52/9. Walk-forward validation решит окончательно.

### Конфликт 3: ADX порог

| Сторона | Позиция |
|---------|---------|
| **Агент 1** (Тренд) | ADX > 25 = тренд. Стандарт Уайлдера. |
| **Агент 20** (Regime) | ADX > 25 + удержание ≥ 3 бара подряд. Без этого фильтра — ложные сигналы на всплесках. |

**Резолюция:** ADX > 25 + подтверждение 3 бара. Добавить ATR-фильтр волатильности для разделения High/Low Vol Range.

### Конфликт 4: Kelly fraction

| Сторона | Позиция |
|---------|---------|
| **Агент 5** (Риск) | Half-Kelly (f = 0.5). ~75% доходности при ~25% просадке. Максимум допустимого при fat tails. |
| **Агент 25** (Alpha Combination) | Quarter-Kelly более безопасен. Fat tails на крипте (excess kurtosis ~6–9) делают Half-Kelly агрессивным. |

**Резолюция:** Half-Kelly как дефолт. Quarter-Kelly если MaxDD > 10% за последние 30 дней. Динамическое переключение.

### Конфликт 5: Mean Reversion на цене

| Сторона | Позиция |
|---------|---------|
| **Агент 14** (Mean Reversion) | MR на цене BTC НЕ работает. ADF p > 0.90. Только MR на spreads и funding rate. |
| **Агент 2** (Осцилляторы) | RSI/StochRSI показывают «mean-reversion к 50», что полезно для тайминга. |

**Резолюция:** Оба правы в своей области. Агент 14 прав: нельзя торговать MR на цене BTC. Агент 2 прав: осцилляторы полезны как фильтры тайминга внутри тренда, но не как standalone MR стратегия. Осцилляторы — фильтры, не primary сигналы.

### Конфликт 6: Волатильность — ATR vs Historical σ

| Сторона | Позиция |
|---------|---------|
| **Агент 5** (Риск) | ATR для SL/TP: учитывает gaps через True Range. |
| **Агент 6** (Статистические модели) | σ для GARCH, VaR, Kelly: статистически обоснована. |

**Резолюция:** Оба используются в разных контекстах. ATR — для SL/TP и trailing stops (цена-ориентированные). σ — для VaR, Kelly, GARCH (статистические модели). Нет конфликта — разные применения.

---

## 10. MVP v0.1 Implementation Plan

> **Источник:** Агент 29 — Implementation Plan (05-implementation-plan.md)  
> **Примечание:** Файл 05-implementation-plan.md содержит план для не связанного проекта (PaperDAO). Ниже — адаптированный план для крипто-торгового бота на основе собранных данных всех агентов.

### Phase 1 — Foundation (Недели 1–3)

| # | Задача | Приоритет | Зависимости | Часы | Deliverables |
|---|--------|-----------|-------------|------|-------------|
| T-001 | Data Ingest: Binance WebSocket kline stream | P0 | — | 16h | `data_ingest.rs`, reconnect logic, ring buffer |
| T-002 | OHLCV Parser + Validation | P0 | T-001 | 8h | OHLCV struct, gap detection, OHLCV consistency check |
| T-003 | Indicator Engine: EMA (O(1) update) | P0 | T-002 | 8h | `ema.rs`, EMA(20), EMA(50), crossover signal |
| T-004 | Indicator Engine: ADX(14) + DI | P0 | T-002 | 12h | `adx.rs`, Wilder smoothing, DI+/DI- |
| T-005 | Indicator Engine: ATR(14) | P0 | T-002 | 4h | `atr.rs`, True Range, Wilder smoothing |
| T-006 | Indicator Engine: RSI(14) | P0 | T-002 | 6h | `rsi.rs`, Wilder smoothing, clamp edge cases |
| T-007 | Indicator Engine: OBV | P0 | T-002 | 4h | `obv.rs`, winsorize flash crash wicks |
| T-008 | Signal Generator: EMA crossover + ADX filter | P0 | T-003, T-004 | 8h | `signal_gen.rs`, LONG/SHORT/NEUTRAL output |
| T-009 | Risk Manager: ATR-SL/TP Calculator | P0 | T-005 | 6h | `risk_mgr.rs`, k_SL=2.0, k_TP=3.0 |
| T-010 | Risk Manager: Half-Kelly Position Sizer | P0 | T-009 | 8h | Kelly formula, MaxPct=0.05, fallback Fixed Fraction |
| T-011 | Risk Manager: MaxDD Circuit Breaker | P0 | — | 6h | L1=12%, L2=15%, flash crash detector |
| T-012 | Order Executor: Binance REST API (OCO) | P0 | — | 12h | `executor.rs`, OCO orders, error handling |
| T-013 | Order Executor: Slippage Model (Fixed 5bps) | P0 | T-012 | 4h | `slippage.rs`, execution price calculation |
| T-014 | Backtest Engine: Walk-Forward | P0 | T-003..T-013 | 16h | `backtest.rs`, expanding window, OOS metrics |
| T-015 | Performance Metrics: Sharpe, Sortino, MaxDD | P0 | T-014 | 8h | `metrics.rs`, 15 key metrics |
| T-016 | Config: YAML-based parameter management | P1 | — | 4h | `config.rs`, serde deserialization |
| **Итого** | | | | **130h** | |

**Gate to Phase 2:** Бот может: получать данные → рассчитывать EMA/ADX/ATR → генерировать сигнал → рассчитать SL/TP → определить размер позиции → исполнить ордер → провести бэктест.

### Phase 2 — Alpha (Недели 4–6)

| # | Задача | Приоритет | Зависимости | Часы |
|---|--------|-----------|-------------|------|
| T-017 | Stochastic RSI(14,3,3) | P1 | T-006 | 6h |
| T-018 | Fisher Transform(9) | P1 | T-002 | 6h |
| T-019 | CCI(20) | P1 | T-002 | 4h |
| T-020 | MACD(12,26,9) | P1 | T-003 | 6h |
| T-021 | VWAP (00:00 UTC reset) | P1 | T-002 | 8h |
| T-022 | MFI(14) | P1 | T-002 | 6h |
| T-023 | Bollinger Bands(20,2) | P1 | T-002 | 4h |
| T-024 | KAMA (Kaufman Adaptive) | P1 | T-002 | 8h |
| T-025 | Supertrend (ATR-based) | P1 | T-005 | 6h |
| T-026 | Historical VaR + CVaR | P1 | T-015 | 8h |
| T-027 | Regime-Conditional Signal Combination | P1 | T-008, T-004 | 12h |
| T-028 | Monte Carlo Permutation Test | P2 | T-014 | 8h |
| T-029 | Purged K-Fold Cross-Validation | P2 | T-014 | 8h |
| **Итого** | | | | **90h** |

### Phase 3 — Beta (Недели 7–10)

| # | Задача | Приоритет | Зависимости | Часы |
|---|--------|-----------|-------------|------|
| T-030 | HMM Regime Detector (3 states) | P1 | T-002 | 20h |
| T-031 | GARCH(1,1) Conditional Volatility | P2 | T-002 | 12h |
| T-032 | HP Filter (λ=6) | P2 | T-002 | 10h |
| T-033 | Wavelet Denoising | P2 | T-002 | 12h |
| T-034 | CVD (Cumulative Volume Delta) | P1 | T-002 | 8h |
| T-035 | Volume Profile | P1 | T-002 | 10h |
| T-036 | Funding Rate Z-score | P1 | — | 8h |
| T-037 | Open Interest Δ tracker | P1 | — | 6h |
| T-038 | Meta-Labeling (binary classifier) | P2 | T-027 | 16h |
| T-039 | Fear & Greed Index integration | P2 | — | 4h |
| T-040 | HRP Portfolio Manager | P2 | — | 16h |
| **Итого** | | | | **112h** |

### Phase 4 — Production (Недели 11–14)

| # | Задача | Приоритет | Зависимости | Часы |
|---|--------|-----------|-------------|------|
| T-041 | OBI (multi-level, K=10) | P1 | — | 10h |
| T-042 | Kyle's Lambda (rolling OLS) | P1 | — | 10h |
| T-043 | VPIN | P2 | — | 12h |
| T-044 | MVRV Z-Score (API integration) | P2 | — | 8h |
| T-045 | SOPR (API integration) | P2 | — | 8h |
| T-046 | Hilbert Transform | P2 | T-002 | 12h |
| T-047 | Johansen Test (cointegration) | P2 | — | 12h |
| T-048 | Square-Root Slippage Model | P1 | T-012 | 6h |
| T-049 | Prometheus + Grafana monitoring | P2 | — | 12h |
| T-050 | Integration testing suite | P1 | ALL | 20h |
| **Итого** | | | | **110h** |

---

## 11. Appendix: Magic Numbers Reference Table

### Индикаторы тренда

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| EMA Fast period | 20 | ~20 часов ≈ торговый день на 1H | Агент 1 |
| EMA Slow period | 50 | ~50 часов ≈ 2.5 дня | Агент 1 |
| α_fast (EMA) | 0.095238 | = 2/21 | Вычисление |
| α_slow (EMA) | 0.039216 | = 2/51 | Вычисление |
| ADX threshold | 25 | Порог «есть тренд» | Wilder, Агент 1 |
| ADX confirmation bars | 3 | Подтверждение тренда N баров | Агент 20 |
| KAMA period | 10 | Efficiency Ratio окно | Агент 1 |
| VWAP reset time | 00:00 UTC | Сброс сессии | Агент 3 |
| Supertrend multiplier | 3.0 | ATR multiplier для полос | Агент 1 |
| Ichimoku periods | 9, 26, 52 | Tenkan, Kijun, Senkou B | Агент 1 |

### Осцилляторы

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| RSI period | 14 | Стандарт Уайлдера | Агент 2 |
| RSI overbought | 70 | Порог перекупленности | Агент 2 |
| RSI oversold | 30 | Порог перепроданности | Агент 2 |
| StochRSI period | 14,3,3 | RSI period, K smoothing, D smoothing | Агент 2 |
| Fisher period | 9 | Период трансформации | Агент 2 |
| CCI period | 20 | Период CCI | Агент 2 |
| CCI overbought | 100 | Порог перекупленности | Агент 2 |
| CCI oversold | −100 | Порог перепроданности | Агент 2 |
| MACD fast/slow/signal | 12/26/9 | Стандарт Appel | Агент 2 |

### Объёмные индикаторы

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| MFI period | 14 | Период Money Flow Index | Агент 3 |
| MFI overbought | 80 | Порог перекупленности MFI | Агент 3 |
| MFI oversold | 20 | Порог перепроданности MFI | Агент 3 |
| VWAP bands σ | 1σ, 2σ | Отклонения VWAP | Агент 3 |
| RVOL period | 20 | SMA окно для Relative Volume | Агент 3 |

### Волатильность

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| ATR period | 14 | Период ATR (Wilder) | Агент 5 |
| Bollinger period | 20 | Период BB | Агент 3 |
| Bollinger multiplier | 2.0 | σ multiplier для BB | Агент 3 |
| GARCH α | 0.10 | ARCH coefficient | Агент 6 |
| GARCH β | 0.85 | GARCH coefficient | Агент 6 |
| GARCH ω | 0.05 | Constant term | Агент 6 |

### Риск-менеджмент

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| k_SL (long) | 2.0 | ATR multiplier для Stop Loss | Агент 5 |
| k_SL_short | 1.5 | ATR multiplier для SL (short) | Агент 5 |
| k_TP | 3.0 | ATR multiplier для Take Profit | Агент 5 |
| R:R long | 1.5:1 | Reward/Risk ratio | Вычисление |
| R:R short | 2.0:1 | Reward/Risk ratio | Вычисление |
| Kelly fraction | 0.5 | Half-Kelly | Агент 5 |
| MaxPct per trade | 0.05 (5%) | Макс. капитала на сделку | Агент 5 |
| MaxPct per asset | 0.30 (30%) | Макс. вес на актив | Агент 19 |
| MinPct per asset | 0.05 (5%) | Мин. вес на актив | Агент 19 |
| MaxDD L1 (warning) | 12% | Pre-warning уровень | Агент 5 |
| MaxDD L2 (halt) | 15% | Полная остановка | Агент 5 |
| Flash crash threshold | −8% за 1 свечу | Мгновенный halt | Агент 5 |
| VaR α | 0.05 | 95% доверительный интервал | Агент 5 |
| CVaR halt threshold | 10% Capital | Стоп-торговля | Агент 5 |
| CVaR reduce threshold | 5% Capital | Сократить позицию на 50% | Агент 5 |
| Min SL distance | max(2×ATR, 0.5%×Entry) | Защита от ATR → 0 | Агент 5 |
| Fixed Fraction (fallback) | 0.02 (2%) | При Kelly ≤ 0 или < 30 сделок | Агент 5 |

### Order Flow

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| OBI depth K | 10 уровней | Глубина книги | Агент 7 |
| OBI decay γ | 0.5 | Экспоненциальное затухание | Агент 7 |
| OBI bias threshold | ±0.3 | Значимый перекос | Агент 7 |
| OBI extreme threshold | ±0.7 | Экстремальный перекос | Агент 7 |
| OFI window | 1 секунда | Окно Order Flow Imbalance | Агент 7 |
| VPIN bucket size | 50 trades | Объём бакета для VPIN | Агент 7 |
| Kyle Lambda window | 200 наблюдений | Rolling OLS window | Агент 7 |

### Крипто-специфичные

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| Funding Rate cap | 0.75%/8h | Binance cap | Агент 16 |
| FR Z-score overbought | +2.0 | Экстремальная перекупленность | Агент 16 |
| FR Z-score oversold | −2.0 | Экстремальная перепроданность | Агент 16 |
| FR absolute warning | 0.05%/8h | Умеренная перекупленность | Агент 16 |
| MVRV sell zone | > 3.5 | Перегрев | Агент 17 |
| MVRV buy zone | < 1.0 | Capitulation | Агент 17 |
| MVRV StdDev window | 365 дней | Окно для Z-Score | Агент 17 |
| SOPR level | 1.0 | Support/resistance | Агент 17 |
| Basis check filter | Квартал экспирация | Фильтр аномалий basis | Агент 16 |
| Fear & Greed extreme fear | < 20 | Contrarian buy | Агент 23 |
| Fear & Greed extreme greed | > 80 | Contrarian sell | Агент 23 |

### Статистические модели

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| HMM states | 3 (initially) | Bull/Bear/Range | Агент 6 |
| HMM states (target) | 4 | Bull/Bear/HV Range/LV Range | Агент 20 |
| HP λ (1H) | 6 | Сглаживание тренда | Агент 13 |
| HP λ (4H) | 25 | Сглаживание тренда | Агент 13 |
| HP λ (1D) | 1600 | Ravn-Uhlig rule | Агент 13 |
| ADF significance | 0.05 | Порог стационарности | Агент 14 |
| KPSS significance | 0.05 | Порог стационарности | Агент 14 |
| MR Gate Rule | ADF < 0.05 AND KPSS > 0.05 | Строгий критерий MR | Агент 14 |
| Hurst threshold | 0.5 | H > 0.5 = trending | Агент 21 |

### Кросс-валидация

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| Train ratio | 0.8 | 80% train, 20% test | Агент 27 |
| Walk-Forward K | ≥ 5 | Минимальное число фолдов | Агент 27 |
| Embargo | 2 × holding_period | Защита от label leakage | Агент 27 |
| MC permutations M | 10,000 | Для permutation test | Агент 27 |
| Min OOS period | 20% от dataset | Минимальный out-of-sample | Агент 27 |

### Качество данных

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| Z-score outlier threshold | 4.0 | Обнаружение выбросов | Агент 22 |
| Rate-of-change outlier | 20% за 1 свечу | Flash crash detection | Агент 22 |
| Gap fill limit | 5 свечей | Макс. заполнение интерполяцией | Агент 22 |
| Wash trade filter | trades < 1ms apart | Обнаружение wash trading | Агент 22 |
| Volume spike threshold | 5× средней за 20 баров | Обнаружение аномалий объёма | Агент 22 |

### Портфель

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| Max assets | 5–7 | Макс. одновременных пар | Агент 19 |
| Rebalance threshold | 10% | Отклонение для перебалансировки | Агент 19 |
| Max rebalance interval | 7 дней | Максимальный интервал | Агент 19 |
| Correlation window | 60–90 дней | Rolling window для ковариации | Агент 19 |
| Kendall tau | Да | Устойчивость к fat tails | Агент 19 |

### Арбитраж

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| Triangular min profit | 0.05% | Минимальная нетто-прибыль | Агент 15 |
| Triangular max latency | 100 ms | Максимальная задержка | Агент 15 |
| Triangular min depth | $50,000 | Минимальная глубина стакана | Агент 15 |
| Triangular max slippage/leg | 0.02% | Макс. проскальзывание на ногу | Агент 15 |
| Fee taker (Binance VIP0) | 0.10% | Комиссия taker | Агент 15 |

### Execution

| Константа | Значение | Контекст | Источник |
|-----------|---------|---------|---------|
| Fixed slippage bps | 5.0 | 0.05% для backtest | Агент 10 |
| Sqrt slippage κ | 0.1 | Эмпирическая константа | Агент 10 |
| Sqrt slippage max Q/V | 0.1 | Ограничение impact ratio | Агент 10 |

---

> **КОНЕЦ ДОКУМЕНТА**  
>  
> Компиляция выполнена Агентом 31 (Master Compiler & QA).  
> Всего обработано: 30 файлов от агентов 1–30 + консилиум 4 улучшений.  
> Пропущенные файлы: нет (все агенты представлены).  
>  
> Дата: 17 апреля 2026