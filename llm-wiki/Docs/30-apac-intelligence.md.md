
# Агент 30: APAC / Chinese Market Intelligence

**Дата:** 2026-04-17  
**Назначение:** Alpha из азиатского крипто-рынка, которой нет в западных источниках.  
**Исходники:** APAC Intelligence.md, Research Indicators.md, модули 07/16, веб-исследование.

---

## Содержание

1. [Ключевые инсайты: что нового](#ключевые-инсайты)
2. [Метрики, отсутствующие в каталоге 779 формул](#новые-метрики)
3. [Binance vs OKX vs Bybit: ликвидность в азиатские часы](#биржи--ликвидность-utc8)
4. [Как китайские кванты работают со стаканом](#l2l3-практики-китайских-квантов)
5. [Funding Rate стратегии на OKX](#funding-rate-okx)
6. [MEV / Front-running в Азии](#mev-в-азии)
7. [Сезонность: CNY, Golden Week, 11.11](#сезонность)
8. [Практическое применение для бота](#применение-для-бота)

---

## Ключевые инсайты

### Инсайт 1: Cross-Exchange Funding Divergence — недооценённый alpha-источник

**Что обнаружено:** В APAC Intelligence документе описана метрика «средневзвешенный funding» (加权资金费率), которая усредняет funding rate по объёму торгов на всех биржах. Расхождение funding между биржами >0.02% за 8 часов = арбитражная возможность. Экстремальные значения усреднённого funding (>0.05% за 8ч) предшествуют коррекции в 70% случаев.

**Обоснование:** Наши модули (16-crypto-specific.md) уже содержат Funding Rate как метрику, но только в рамках **одной биржи**. Ни один из 779 инструментов не реализует кросс-биржевой funding spread. Это реальный gap.

**Практическое применение:**
```
Funding_Spread = FR_OKX - FR_Binance

| Funding_Spread | Интерпретация |
|----------------|---------------|
| > +0.02% за 8ч | OKX платит больше → арбитраж: short OKX perp, long Binance perp |
| < -0.02% за 8ч | Binance платит больше → обратный арбитраж |
| > +0.05% за 8ч | Экстремум → высокая вероятность mean-reversion funding |
```
Для бота: добавить в модуль 15 (Arbitrage) как отдельную стратегию `CrossExchangeFundingArb`.

---

### Инсайт 2: «Коэффициент потока» — реконструкция скрытого потока

**Что обнаружено:** Метрика «资金流向系数» (Zījīn liúxiàng xìshù) — аналог CVD, но с учётом iceberg orders и TWAP/VWAP-алгоритмов. Классический CVD учитывает только market orders, но крупные игроки часто используют лимитные ордера и алгоритмические стратегии.

**Обоснование:** В нашем каталоге CVD (модуль 07) считается только по aggressive orders. Iceberg Detection (модуль 07) есть, но он не интегрирован с CVD в единый «настоящий поток». Китайские фонды соединяют эти два инструмента.

**Практическое применение:**
```
True_Flow = CVD + Iceberg_Adjustment

где:
  Iceberg_Adjustment = Estimated_Hidden_Volume × Direction
  Direction определяется по: если после исполнения на уровне через <3сек 
  появляется ордер того же объёма → hidden buyer/seller

True_Flow_Divergence = True_Flow расходится с ценой → сильный разворотный сигнал
```
Для бота: комбинация CVD (модуль 04) + Iceberg Detection (модуль 07) в единый `TrueFlow` индикатор.

---

### Инсайт 3: «Индекс манипуляции» — фильтр ложных сигналов

**Что обнаружено:** Метрика «操盘指数» (Cāopán zhǐshù) из китайских WeChat-каналов. Формула включает 4 компонента:
1. Соотношение объёма крупных сделок (>100K USDT) к общему объёму
2. Коэффициент асимметрии ордербука (bid-ask imbalance)
3. Частоту отмены крупных лимитных ордеров (спуфинг-индикатор)
4. Волатильность в нестандартные часы (02:00–06:00 UTC = «тихие часы» Азии)

**Обоснование:** Ни один из 779 инструментов не оценивает вероятность манипуляции как отдельную метрику. Мы имеем OBI, CVD, spoofing detection по отдельности, но не комбинированный «manipulation index».

**Практическое применение:**
```
Manipulation_Index = 0.3 × Big_Trade_Ratio + 0.25 × Book_Asymmetry 
                   + 0.25 × Cancel_Frequency + 0.2 × Off_Hours_Vol

где:
  Big_Trade_Ratio = Volume(>100K USDT) / Total_Volume
  Book_Asymmetry = |Bid_Vol - Ask_Vol| / (Bid_Vol + Ask_Vol)  [на 5 уровнях]
  Cancel_Frequency = Cancelled_Orders(>50K) / Total_Orders     [за 15 мин]
  Off_Hours_Vol = σ(returns) в 02:00-06:00 UTC / σ(returns) весь день

MI > 70 → высокая вероятность манипуляции → не торговать / уменьшить позицию
MI < 30 → «чистый» рынок → стандартная торговля
```
Для бота: добавить как **фильтр** в модуль 1 (Signal Engine). Все сигналы с MI > 70 отбрасываются.

---

### Инсайт 4: «Маржа маркетмейкера» — мониторинг монополии

**Что обнаружено:** 庄家利润率 (Zhuāngjiā lìrùn lǜ) — отношение заработанного спреда к объёму. Если > 0.02% за сессию → монопольное положение маркетмейкера и потенциальная манипуляция.

**Обоснование:** У нас есть Kyle's Lambda (стоимость потребления ликвидности), но нет обратной метрики — «сколько зарабатывает маркетмейкер». Это дополнение к модулю 07.

**Практическое применение:**
```
MM_Margin = Effective_Spread / Total_Volume

где:
  Effective_Spread = Σ (Execution_Price - Mid_Price_at_Order) по всем сделкам

MM_Margin > 0.02% → MM_extracting_alpha → осторожность с market orders
MM_Margin < 0.005% → конкурентный рынок → нормальное исполнение
```

---

### Инсайт 5: Время жизни ордера — классификация участников

**Что обнаружено:** 订单存活时间 (Dìngdān cúnhuó shíjiān) — среднее время между выставлением лимитного ордера и его исполнением/отменой.

**Обоснование:** Не существует в каталоге. Это дополнение к Lee-Ready Algorithm (модуль 07) — помогает классифицировать участника как HFT vs institutional.

**Практическое применение:**
```
Order_Life = Mean(Time_to_Fill_or_Cancel) по всем лимитным ордерам

< 5 сек → HFT-участник → его действия краткосрочны
5-60 сек → активный трейдер
> 300 сек → институциональный → его уровни = «настоящие» support/resistance

Применение: уровни с Order_Life > 300 сек → приоритетные S/R для бота
```

---

## Новые метрики

### Что НЕТ в каталоге 779 формул

| # | Метрика | Источник | Категория | Модуль для интеграции |
|---|---------|----------|-----------|----------------------|
| 1 | **Cross-Exchange Funding Spread** | APAC Intel (加权资金费率) | Арбитраж | 15 (Arbitrage) |
| 2 | **True Flow (CVD + Iceberg)** | APAC Intel (资金流向系数) | Order Flow | 07 (Order Flow) |
| 3 | **Manipulation Index** | APAC Intel (操盘指数) | Фильтр | 01 (Signal Engine) |
| 4 | **MM Margin (Market Maker Profit)** | APAC Intel (庄家利润率) | Микроструктура | 07 (Order Flow) |
| 5 | **Order Lifetime** | APAC Intel (订单存活时间) | Классификация | 07 (Order Flow) |
| 6 | **Inter-Exchange Capital Flow** | APAC Intel (交易所资金流系数) | On-chain + CEX | 17 (On-chain) |
| 7 | **Enhanced Liquidation Heatmap** | APAC Intel (清算热力图) | Деривативы | 16 (Crypto-Specific) |
| 8 | **VPIN + CVD Composite** | APAC Intel (связка) | Order Flow | 07 (Order Flow) |

**Рекомендация по приоритету для внедрения:**
- **MVP 0.2:** Cross-Exchange Funding Spread, Manipulation Index (как фильтр)
- **MVP 0.3:** True Flow, Order Lifetime
- **MVP 0.4:** MM Margin, Inter-Exchange Capital Flow, Enhanced Liquidation Heatmap

---

## Биржи & Ликвидность (UTC+8)

### Binance vs OKX vs Bybit: профили ликвидности

| Параметр | Binance | OKX | Bybit |
|----------|---------|-----|-------|
| **Доминирующая аудитория** | Retail ЮВ-Азия (VN, PH, ID) | Институционалы Гонконг/Япония | Retail + институционалы Сингапур |
| **Серверы** | Токио + Сингапур | Гонконг | Сингапур |
| **Деривативы (рейтинг 2025)** | #1 | #2 | #3 |
| **Пик ликвидности UTC+8** | 14:00–17:00 (Shanghai power hours) | 10:00–16:00 (HK институционалы) | 10:00–18:00 |
| **Самые ликвидные пары** | BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, DOGE/USDT | BTC/USDT, ETH/USDT, BTC/USD (settlement), SOL/USDT | BTC/USDT, ETH/USDT, SOL/USDT, PEPE/USDT |
| **Спред BTC/USDT** | 0.01–0.02% | 0.01–0.03% | 0.02–0.04% |
| **Фиатные шлюзы** | Ограничены в КНР | Ограничены в КНР | Ограничены в КНР |

### Пары с наибольшей ликвидностью в азиатские часы (08:00–17:00 CST)

**Tier 1 (спред < 0.02%, глубина > $5M на ±2%):**
- BTC/USDT (Binance ≈ OKX > Bybit)
- ETH/USDT (Binance > OKX > Bybit)

**Tier 2 (спред 0.02–0.05%, глубина $1–5M на ±2%):**
- SOL/USDT (Binance > Bybit > OKX)
- XRP/USDT (Binance > OKX)
- DOGE/USDT (Binance доминирует — корейский retail через Binance)
- BNB/USDT (Binance, эксклюзивно)

**Tier 3 (спред 0.05–0.15%, релевантно для swing):**
- PEPE/USDT, WIF/USDT (Bybit доминирует — мем-коины)
- ARB/USDT, OP/USDT (OKX > Binance — L2 narrative)
- SUI/USDT, APT/USDT (Binance — Asian L1 narrative)

### Латентность и инфраструктура для арбитража

```
Оптимальное размещение серверов:
- AWS Tokyo (ap-northeast-1) → Binance: <5ms
- AWS Hong Kong (ap-east-1) → OKX: <5ms  
- AWS Singapore (ap-southeast-1) → Bybit: <5ms
- AWS Direct Connect между регионами: <15ms межбиржевой

Для бота: если не colo, приемлемая латентность <50ms
  → покрывает 70-85% кросс-биржевых возможностей
  → ловит только расхождения >0.15%
```

---

## L2/L3 практики китайских квантов

### Многоуровневый CVD (Multi-Instrument CVD)

Шанхайские HFT-фонды (Wintermute Asia, Amber Group, Nibbio Capital) строят **отдельные CVD** для каждого инструмента и сравнивают:

```
CVD_Spot_Binance vs CVD_Perp_OKX vs CVD_Options_Aevo

Если CVD_Spot > 0, а CVD_Perp < 0 → расхождение funding → закроется за 2-4ч
```

**Для бота:** Реализовать `MultiInstrumentCVD` — не один CVD, а вектор CVD по spot/perp/options каждой биржи.

### Footprint на нестандартных барах

Азиатские маркетмейкеры анализируют footprint **не на временных свечах**, а на:
- Тиковых барах (100 контрактов для BTC perp)
- Объёмных барах (фиксированный объём)
- Range bars (фиксированное ценовое движение)

Это даёт разрешение 1–5 секунд вместо 1 минуты на стандартных свечах.

**Для бота:** добавить в конфиг поддержку `bar_type: tick|volume|range` кроме `timeframe`.

### VPIN + CVD связка (не в каталоге)

```
Если VPIN растёт И CVD расходится с ценой:
  → маркетмейкеры сужают спред или уходят с рынка
  → ликвидность падает → любой импульс усилится
  → СИГНАЛ: уменьшить позицию или выйти

VPIN > 0.4 + CVD_divergence = режим "toxic flow"
  → спреды расширяются до 0.15-0.3%
  → не торговать market orders
```

---

## Funding Rate стратегии на OKX

### Почему OKX особенный для китайских трейдеров

1. **Контракты в USD (coin-margined):** OKX предлагает BTC/USD perpetual с расчётом в BTC. Китайские институционалы предпочитают это для cash-and-carry без USDT-риска.
2. **Funding каждые 4 часа** (не 8 как Binance) на некоторых парах → более частые выплаты, но и более частые смены направления.
3. **Block trading desk:** OKX имеет OTC-блок для крупных funding arb (> $10M), что недоступно на Binance.

### Специфичные OKX паттерны

```
Паттерн 1: OKX funding > Binance funding на >0.03% за 8ч
  → китайские фонды short OKX perp + long Binance spot
  → за 2-4 часа spread сокращается
  → доходность: 0.02-0.04% за цикл

Паттерн 2: OKX coin-margined funding vs USDT-margined funding
  → расхождение создаётся разным спросом на leverage
  → coin-margined обычно > USDT-margined в bull market
  → arb: short coin-margined + long USDT-margined

Паттерн 3: End-of-quarter funding spike
  → последняя неделя квартала → институционалы roll позиции
  → funding spike на 2-3 дня → временный arb
```

### Пороги для бота

```
Вход в funding arb:
  FR_annualized >= 15% (FR_8h >= 0.034%)
  Spread между биржами >= 0.02%
  Ликвидность на обеих ногах >= $1M на ±1%

Выход:
  FR_annualized < 8% (FR_8h < 0.018%)
  ИЛИ 3 последовательных периода с отрицательным FR
  ИЛИ margin usage > 70% (риск ликвидации)
```

---

## MEV в Азии

### География MEV

Азиатские валидаторы и searchers доминируют в MEV на:
- **BNB Chain:** большинство валидаторов расположены в Азии. BNB Chain briefly overtook Solana в memecoin trading volume в начале 2025 → MEV activity surged.
- **Solana:** Jito block engine привлёк азиатских searchers. Попытка создать memepool на Solana привела к атакам с расходами 300K+ SOL.
- **Ethereum L2s (Arbitrum, Base):** азиатские боты активны в sandwich attacks на мемкоинах.

### Типы MEV, распространённые в Азии

| Тип | Платформа | Применение для бота (CEX) |
|-----|-----------|--------------------------|
| **Sandwich attacks** | DEX (Uniswap, PancakeSwap) | Мониторинг: если бот торгует через DEX-агрегаторы → детекция sandwich |
| **Arbitrage bots** | Все DEX + CEX | Кросс-DEX-CEX arb: купить на DEX дешевле, продать на CEX дороже |
| **Liquidation MEV** | Aave, Compound | Мониторинг ликвидаций on-chain → предсказание каскадов на CEX |
| **Frontrunning** | BNB Chain, Solana | Для CEX-бота: мониторинг on-chain крупных свопов → торговля опережающая |

### Применение для CEX-бота

```
Мониторинг on-chain MEV как leading indicator:
1. Рост MEV-extracted value на BNB Chain/Solana
   → повышенная активность informed traders
   → уменьшить позицию на связанных CEX-парах

2. Крупные sandwich profits (> $50K за 1 час)
   → волатильность incoming
   → подготовить ликвидационные уровни

3. Cross-chain arb volume spike
   → capital rotation между chains
   → мониторить exchange net flows
```

**Источники данных:**
- **EigenPhi** (eigenphi.io) — MEV-аналитика на Ethereum
- **BSCScan/BNB Chain Explorer** — MEV-транзакции на BNB Chain
- **Jito Labs** — Solana MEV-данные
- **Flashbots Protect** — прозрачность MEV на Ethereum

---

## Сезонность

### Chinese New Year (春节)

**2026 дата:** 17 февраля (вторник)

| Параметр | Влияние | Детали |
|----------|---------|--------|
| **Объём** | -30-40% за 7-10 дней до, -50-60% во время | Thin market effect |
| **Волатильность** | +30-50% на единицу объёма | Неожиданные движения 3-5% без причин |
| **Ликвидации** | Реже, но каждая больше влияет | Thin liquidity amplifies |
| **Recovery** | 3-5 дней после праздника | Post-holiday surge |
| **Тренд 2021-2026** | Эффект ослабевает | Институционализация BTC (ETF) снижает региональный эффект |

**Стратегия бота:**
```yaml
chinese_new_year:
  reduce_leverage_before_days: 7
  max_leverage_during: 5x          # вместо обычных 10-20x
  widen_stop_loss_pct: 15-20%
  avoid_new_positions: [-2, +2]    # дня до/после
  consider_straddle: true          # опционный straddle на повышенной волатильности
```

**Важное наблюдение 2026:** Эффект CNY ослабевает с 2021 года. BTC теперь управляется ETF flows и макро-факторами. Но для альткоинов (особенно с азиатской аудиторией: BNB, OKB, BGB) эффект остаётся значимым.

---

### Golden Week (黄金周, 1-7 октября)

| Параметр | Влияние |
|----------|---------|
| **Объём** | -20-30% (мягче CNY) |
| **Особенности** | Совпадает с публикацией экономических данных Китая (PMI, GDP) |
| **Гонконг** | HKEX закрыт → снижение институционального потока |
| **Корреляция** | Иногда совпадает с корейским Chuseok → двойной эффект |

---

### 11.11 (Singles' Day, 11 ноября)

**Прямого влияния на крипту минимально**, но есть косвенные эффекты:
- Ритейлеры в Китае переводят USDT в юани для покупок → selling pressure на стейблкоинах
- Alibaba/Tencent квартальные отчёты → влияние на tech sentiment → корреляция с крипто

---

### Другие азиатские сезонные факторы

| Праздник | Страна | Период | Влияние |
|----------|--------|--------|---------|
| **Chuseok** | Корея | Сен/Окт | -10-15% объём (Upbit, Bithumb) |
| **Obon** | Япония | Август | Снижение институциональной активности |
| **Diwali** | Индия | Окт/Нояб | Рост retail interest в крипту |
| **FY-end Япония** | Март | Март | Продажи для фиксации прибыли/убытков |
| **FY-end Китай** | Декабрь | Декабрь | Переток капитала |

### Временные паттерны азиатской сессии (UTC)

```
00:00-02:00 UTC (08:00-10:00 CST, Токио открытие):
  Активность: ~60% от пика
  Японские экономические данные → движения

02:00-06:00 UTC (10:00-14:00 CST, "тихие часы"):
  Активность: 30-40% от пика
  ⚠️ Наиболее опасный период: thin liquidity + манипуляции маркетмейкеров
  Минимальная волатильность, но резкие движения наиболее вероятны

06:00-09:00 UTC (14:00-17:00 CST, "power hours"):
  Активность: 80-100% от пика
  Шанхайская фондовая биржа закрывается в 07:00 UTC → переток в крипто

09:00-12:00 UTC (переход Азия-Европа):
  Высокая волатильность, расширение спредов
  Типичное время "утренних" ликвидаций
```

---

## Применение для бота

### Приоритетные интеграции

| # | Что добавить | Модуль | Версия | Сложность |
|---|-------------|--------|--------|-----------|
| 1 | **Cross-Exchange Funding Spread** | 15 (Arbitrage) | 0.2 | Низкая (API funding rates) |
| 2 | **Manipulation Index (фильтр)** | 01 (Signal) | 0.2 | Средняя (нужны tick data) |
| 3 | **True Flow (CVD + Iceberg)** | 07 (Order Flow) | 0.3 | Средняя |
| 4 | **Order Lifetime** | 07 (Order Flow) | 0.3 | Средняя (L2 event stream) |
| 5 | **Seasonal Calendar** | 01 (Signal) | 0.2 | Низкая (календарь) |
| 6 | **VPIN + CVD Composite** | 07 (Order Flow) | 0.3 | Высокая (tick data) |
| 7 | **MM Margin** | 07 (Order Flow) | 0.4 | Высокая |
| 8 | **Multi-Instrument CVD** | 04 (Volume) | 0.4 | Средняя |

### Seasonal Calendar для config.yaml

```yaml
seasonal:
  chinese_new_year:
    date: "lunar_calendar"  # вычисляется динамически
    volume_drop_pct: 40
    volatility_increase_pct: 40
    reduce_leverage_days_before: 7
    max_leverage: 5
    avoid_new_positions_days: [−2, +2]
  
  golden_week:
    dates: ["10-01", "10-07"]
    volume_drop_pct: 25
    watch_macro_data: true  # PMI, GDP публикации
  
  chuseok:
    date: "lunar_calendar"
    volume_drop_pct: 12
    affected_exchanges: ["upbit", "bithumb"]
  
  quiet_hours_asia:
    start_utc: "02:00"
    end_utc: "06:00"
    manipulation_risk: "high"
    max_position_reduction: 0.5  # сократить позицию вдвое
```

### Manipulation Index для config.yaml

```yaml
manipulation_index:
  enabled: true
  components:
    big_trade_threshold_usdt: 100000
    book_depth_levels: 5
    cancel_window_minutes: 15
    off_hours_start_utc: "02:00"
    off_hours_end_utc: "06:00"
  
  thresholds:
    high_risk: 70       # блокировать все сигналы
    medium_risk: 50     # уменьшить размер позиции на 50%
    low_risk: 30        # нормальная торговля
```

### Cross-Exchange Funding Spread для config.yaml

```yaml
funding_arb:
  enabled: true
  exchanges: ["binance", "okx", "bybit"]
  
  entry:
    min_annualized_rate: 15        # %
    min_cross_exchange_spread: 0.02 # % за 8h
    min_liquidity_usd: 1000000     # на ±1%
  
  exit:
    min_annualized_rate: 8         # ниже → выход
    consecutive_negative_periods: 3
    max_margin_usage: 0.70         # 70% → выход
  
  risk:
    max_leverage: 3                # для arb консервативно
    margin_buffer: 0.50            # 50% запас по марже
```

---

## Итоговая оценка: что реально даёт alpha

| Источник alpha | Размер edge | Доступность | Уже в каталоге? |
|----------------|-------------|-------------|----------------|
| Cross-Exchange Funding Spread | +2-5% годовых | API funding rates | ❌ НЕТ |
| Manipulation Index как фильтр | +5-10% точности сигналов | Tick data | ❌ НЕТ |
| True Flow (CVD + Iceberg) | +3-8% к CVD точности | L2 data | ❌ НЕТ (CVD есть, но без iceberg) |
| Сезонность (CNY calendar) | +1-3% на альткоинах | Календарь | ❌ НЕТ |
| VPIN + CVD Composite | +5-15% к risk management | Tick data | ❌ НЕТ (VPIN и CVD по отдельности есть) |
| Order Lifetime | +2-5% к S/R определению | L2 event stream | ❌ НЕТ |
| MM Margin | +3-7% к выбору времени исполнения | Tick data | ❌ НЕТ |
| Quiet Hours фильтр | +3-8% (avoid manipulation) | Календарь + vol | ❌ НЕТ |

**Вывод:** Все 8 метрик — genuine alpha, отсутствующие в текущем каталоге. Наиболее просты для внедрения (низкая сложность, высокий impact): **Cross-Exchange Funding Spread**, **Manipulation Index**, **Seasonal Calendar**, **Quiet Hours фильтр**.

---

## Источники

- APAC Intelligence.md — первичный анализ азиатской микроструктуры
- Binance WU Blockchain Report (январь 2026) — деривативы рейтинг
- OKX Research — liquidity, leverage, liquidation dynamics
- Unocoin Research — CNY seasonal effects weakening
- BlockTempo (華語) — MEV landscape on BNB Chain/Solana
- Собственный анализ: Research Indicators.md (779 формул) → gap analysis