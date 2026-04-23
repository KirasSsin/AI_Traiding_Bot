# Консолидированная архитектура алготрейдингового бота BTC/USDT 1H v0.1

## 1. Executive Summary

**Scope v0.1** — MVP бот для BTC/USDT на 1H таймфрейме Binance spot на стеке **Python-only** (asyncio + uvloop, pandas, NumPy, TA-Lib, pydantic v2) c хранением в **SQLite + Parquet**. Стратегия — EMA-crossover (classical) + ADX (Wilder) + RSI (Wilder) с фиксированными процентными размерами в первой фазе. Rust, QuestDB и Grafana отложены до v0.2/v0.3 как реакция на измеренные проблемы, а не как априорные требования. Документ разрешает 10 рассогласований между тремя предыдущими отчётами в пользу эмпирически и математически обоснованных решений.

**Главные изменения vs предыдущей версии документов:** (1) Модель slippage переведена на square-root `κ·σ·√(Q/V)` с fixed 5 bps как защитного placeholder для orders <$10k (квадратичная Q²-модель отвергнута как эмпирически и теоретически неверная); (2) параметры валидации пересчитаны под 1H-горизонт — `train_bars=2000`, `test_bars=500`, `K=5`, `MC=2000`, `OOS/IS≥0.7`; (3) Kelly разбит на 4 фазы с фиксированными процентами до n=30, дальше ступенчатое масштабирование; (4) Circuit breakers согласованы с backtest MaxDD — L1=15%, L2=22%, L3=30%, flash=max(8%, 3·ATR); (5) ADX/RSI/ATR используют **Wilder EMA (α=1/n)**, crossover-EMA — **classical (α=2/(n+1))**; (6) явный DDD с 5 bounded contexts и 20 domain events.

**Главные риски v0.1:** статистический (overfitting — 5 лет данных BTC 1H позволяет безопасно протестировать не более ~45 конфигураций по MinBTL-границе Bailey–López de Prado 2014); рыночный (режимный сдвиг — BTC после 2017 демонстрирует затухание простых MA-правил по Hudson & Urquhart 2021, OOS-Sharpe у них отрицателен); операционный (неверный API-ключ, неожиданный rate-limit-ban HTTP 418). Риск Rust-оверинжиниринга снят: нагрузка 8760 бар/год и <1% CPU не оправдывает Rust хот-путь.

## 2. Таблица разрешённых рассогласований

| # | Вопрос | Было | Стало | Обоснование | Источник |
|---|---|---|---|---|---|
| 1 | Slippage-модель | Fixed 5 bps / sqrt κ=0.1 / квадратичная Q² | **Fixed 5 bps для MVP orders <$10k; sqrt `κ·σ·√(Q/V)` κ=0.1 для orders >$50k или >0.1% ADV** | Q² опровергнута: Almgren–Thum–Hauptmann–Li (2005) дают β≈0.6 для акций, Donier–Bonart (2015) подтверждают β≈0.5 на 1M+ BTC-метазаказов; Gatheral (2010) показывает, что permanent impact обязан быть линейным/вогнутым по no-arbitrage | Almgren & Chriss (2000) *J. Risk* 3(2):5–39, §1.3–1.5 pp.8–11; Almgren et al. (2005) *Risk* 18(7):58–62, §3.2 pp.16–17; Donier & Bonart (2015) *MML* 1(2):1550008; Kissell (2013) Ch.5 |
| 2 | MC permutations | 10,000 vs 1,000 | **N=2,000** для рутинного α=0.05; эскалировать до 10,000 при DSR/Bonferroni-коррекции | SE(p̂)=√(p(1−p)/N); при N=2000, p=0.05 → SE≈0.005 (10% относительной ошибки у границы решения); N=1000 даёт 14%, N=10,000 — 4% (overkill без multiple-testing) | López de Prado (2018) *AFML* Ch.11–12, §12.4 CPCV; Bailey, Borwein, López de Prado, Zhu (2017) *J. Comput. Finance* 20(4):39–70 |
| 2a | MC method | не специфицировано | **sign-flip** первичный; block-bootstrap (блок 20–50 баров) вторичный | Sign-flip сохраняет тайминг/размер сделок, тестирует H₀="направление без edge" — точно то, что нужно для EMA-crossover | AFML Ch.12 |
| 3 | Walk-Forward train_bars | 252 (калька forex — 10.5 дней на 1H!) | **train=2000 баров (~12 недель), test=500 (~3 недели)** | Окно должно содержать ≥30–100 сделок для статзначимости; EMA-cross+ADX на 1H генерирует 2–5 сделок/неделю → 2000 баров ≈ 24–60 сделок в окне | AFML Ch.12 §12.2; Pardo (2008) Ch. Walk-Forward Analysis |
| 4 | K-Fold splits | K=3 (catastrophically few) | **K=5 standard для v0.1, K=10 для v0.2+ через PKCV** | K=3 даёт высокую variance оценок; K=10 — рекомендация López de Prado для финансовых рядов с purging+embargo h≈0.01·T | AFML Ch.7 §7.4 pp.103–111 |
| 5 | OOS/IS Sharpe | ≥0.5 (стратегия может деградировать вдвое) | **≥0.7** | 0.5 означает 50% деградацию edge — недопустимо; институциональная практика — 0.7–0.8 как порог "не overfit" | Halls-Moore (2015) Ch.16.1; Bailey–López de Prado (2014) DSR *JPM* 40(5):94–107 |
| 6 | Kelly | Half-Kelly с n=0 | **4 фазы**: n<30→1%; n<100→2%; n<200→Q-Kelly cap 3%; n≥200→Half-Kelly cap 5% | Wilson 95% CI при n=30, p̂=0.55 = [0.37, 0.71] — CI на f\* straddles zero, нельзя отвергнуть "no edge"; при n=200, p̂=0.55 CI=[0.481, 0.616] — edge статзначим на 90% уровне | Kelly (1956) *BSTJ* 35:917–926; Thorp (2006); MacLean–Thorp–Ziemba (2011); Halls-Moore (2015) Ch.13.2; Agresti–Coull (1998) *Am. Stat.* 52:119–126 |
| 7 | Circuit breakers | L1=12%, L2=15% (противоречит MaxDD=25%) | **L1=15% warn+half-size, L2=22% halt 24h, L3=30% full stop; flash=max(8%, 3·ATR)** | Не противоречие: L1<MaxDD — буфер раннего предупреждения, аналогично NYSE L1=7% при исторической DJIA-MaxDD 22% в 1987. 3·ATR target hit rate ≈0.1–0.5% баров; 8% floor страхует от volatility compression | NYSE Rule 7.12; Harris (2003) Ch.28; Kirilenko–Kyle–Samadi–Tuzun (2017) *JF* 72(3):967–998; Magdon-Ismail–Atiya (2004) *JAP* 41(1):147–161 |
| 8 | Tech stack | Rust+Python с 0 / Rust MVP / Python-only | **v0.1: Python-only; v0.2: +PyO3 Rust для L2-парсера (опционально); v0.3: QuestDB+Grafana** | 1 бар/час = 8760 bars/год, Python+uvloop даёт 3 порядка headroom (105K req/s 1KiB); Rust нужен для sub-10μs tick-to-trade, не для 1H-бота | Knuth (1974) *Computing Surveys* 6(4):261–301 "premature optimization"; MagicStack uvloop benchmarks; markrbest.github.io HFT-and-Rust |
| 9 | СУБД | QuestDB+SQLite с 0 | **v0.1: SQLite (OLTP:trades/config/state) + Parquet (OLAP:OHLCV); v0.3: QuestDB только при L2-snapshots >10K msg/s** | OHLCV 1H = 8760 rows/год = <100KB Parquet; QuestDB (4–11M rows/s) на 27 порядков избыточен; Kleppmann разделяет OLTP (B-tree SQLite) и OLAP (columnar Parquet) | Kleppmann (2017) *DDIA* Ch.3 pp.72–101: §"B-Trees" pp.79–83, §"OLTP vs OLAP" pp.90–93, §"Column-Oriented Storage" pp.95–101 |
| 10 | EMA смешение | Wilder vs classical спутаны | **ADX/+DI/−DI/ATR/RSI → Wilder α=1/n; EMA-crossover → Classical α=2/(n+1)**; для n=14: α_classical=0.1333, α_Wilder=0.0714; Wilder(n) ≈ Classical(2n−1) | Wilder (1978) — оригинальные формулировки; TA-Lib поведение: `EMA()` классический, `ADX/RSI/ATR` — Wilder | Wilder (1978) *New Concepts* Ch.3,4,6; Kaufman (2013) *TS&M* Ch.7,9; TA-Lib SF bug #87 |

## 3. Технологический стек по версиям

**v0.1 (MVP, 2–3 месяца работы одного разработчика):** Python 3.12, asyncio + uvloop, `websockets` или `aiohttp` для Binance WS, `python-binance` или `ccxt` для REST, pandas 2.x + NumPy, TA-Lib (C-bindings), pydantic v2 для domain-моделей, structlog для JSON-логов. Хранение: SQLite (WAL-mode) для `orders`, `fills`, `positions`, `runs`, `config`, `audit_index`; Parquet (snappy-compression, row-group по timestamp) для `ohlcv_1h_btcusdt`. Деплой: Docker-compose на один VPS (2 vCPU, 4 GB RAM достаточно). Мониторинг: Sentry (free tier 5K events/мес), healthchecks.io dead-man's switch.

**v0.2 (через 3–6 месяцев, после 200+ реальных сделок):** добавить DuckDB поверх Parquet-озера для ad-hoc исследовательских SQL-запросов (zero-install embedded engine). Опционально — Rust-модуль через PyO3/maturin **только если** добавляется L2-orderbook стратегия: Rust обрабатывает `@depth@100ms` updates, отдаёт в Python агрегированный order-book-imbalance feature. Оркестрация остаётся в Python. Добавить property-based тесты через `hypothesis`, look-ahead-детектор в CI.

**v0.3 (через 6–12 месяцев, после подтверждения edge и необходимости масштабирования):** QuestDB **только при** реальной потребности >10K msg/s устойчивой ингестии (multi-symbol tick archive, полный L2-snapshot store). Grafana + Prometheus exporter для: equity curve, rolling Sharpe, drawdown, per-trade PnL, WS disconnect counter, order reject rate, X-MBX-USED-WEIGHT headroom. Добавить GitOps-деплой через watchtower или ArgoCD. Rotation secrets через Doppler или SOPS+age.

**Обоснование против Qwen (Rust с нуля) и ChatGPT (Rust MVP):** Binance для одного символа @kline_1h пушит ~1 msg/s; bot-hot-path выполняется 8760 раз/год; измеренный CPU load на современном laptop <1%. uvloop benchmarks показывают 105K req/s на 1 KiB на одном ядре, то есть 5 порядков запаса. Knuth 1974 §1: "premature optimization is the root of all evil". Rust обоснован только для sub-10μs tick-to-trade в market-making (markrbest.github.io/hft-and-rust), что не наш случай.

## 4. Параметры валидации (исправленные)

| Параметр | Было | Стало | Почему |
|---|---|---|---|
| train_bars | 252 (форекс-калька) | **2000** (~12 недель на 1H) | 24–60 сделок в окне для EMA-cross+ADX при 2–5 trades/week |
| test_bars | не специфицировано | **500** (~3 недели) | Train/test 4:1, стандарт Pardo 70/20–80/20 |
| K-fold | 3 | **5 (v0.1), 10 (v0.2+ с PKCV)** | K=3 имеет высокую variance; AFML Ch.7 рекомендует 10 с purging+embargo h=0.01·T |
| MC permutations | 10,000 или 1,000 | **2,000** для α=0.05; 10,000 при multiple-testing correction | SE(p̂)=0.005 у границы решения достаточно для go/no-go |
| MC method | не указано | **sign-flip primary, block-bootstrap (блок 20–50 баров) secondary** | Sign-flip тестирует H₀ "направление без edge" — прямая проверка EMA-signal value |
| OOS/IS Sharpe | ≥0.5 | **≥0.7** | 0.5 допускает 50% деградацию edge — неприемлемо |
| min_trades по фазам | не разделено | **30 → 100 → 200 → ∞** | Wilson CI анализ — см. §5 |
| Embargo period | не специфицировано | **h = 0.01·T ≈ 20 баров** после каждой test-fold на 1H | AFML §7.4.2 |
| Deflated Sharpe Ratio | не применяется | **Обязательно** при тестировании N>1 конфигураций; variance-of-trials + Gumbel expected-max | Bailey–López de Prado (2014) *JPM* 40(5):94–107; AFML §14.7.3 p.204 |
| Minimum Backtest Length | не проверяется | **MinBTL < 2·ln(N) / E[max_N]² лет**; 5 лет BTC-данных ⇒ max ~45 независимых конфигураций при target Sharpe=1 | Bailey et al. (2014) *Notices AMS* |

**Альтернативы для walk-forward:**

| Подход | Преимущества | Недостатки | Вердикт |
|---|---|---|---|
| Простой Walk-Forward | Интуитивный, легко имплементируется | Path-dependent; тратит данные; одна историческая траектория | v0.1 baseline |
| Purged K-Fold CV | Использует все данные; корректно для labels | Один test-path | v0.2 upgrade |
| Combinatorial Purged CV (CPCV) | Распределение Sharpe по C(N,k) путям; золотой стандарт AFML | Вычислительно дорог | v0.3 при формальном reporting |

**Рекомендация v0.1: Walk-Forward + sign-flip MC permutation + DSR.** v0.2: PKCV с embargo. v0.3: CPCV.

## 5. Kelly phases

| Фаза | n (число сделок) | Размер позиции | 95% Wilson CI на p при p̂=0.55 | Обоснование |
|---|---|---|---|---|
| **1** | n < 30 | **Fixed 1%** | [0.374, 0.711] — CI на f\* straddles zero | Классическая CLT-граница n=30; невозможно отвергнуть "no edge"; ruin-risk при Kelly катастрофичен |
| **2** | 30 ≤ n < 100 | **Fixed 2%** | при n=100: [0.453, 0.643] | Направление edge становится правдоподобным, но не статзначимо; MacLean–Thorp–Ziemba (2011) показывают "short-term Kelly very risky" |
| **3** | 100 ≤ n < 200 | **Quarter-Kelly, cap 3%** | при n=200: [0.481, 0.616], значим на 90% | SE(p̂) вдвое меньше Phase 1; quarter-Kelly защищает от mis-estimation |
| **4** | n ≥ 200 | **Half-Kelly, cap 5%** | при n=500: [0.507, 0.592], значим на 95% | Соответствует явной рекомендации Halls-Moore §13.2: "many traders use half-Kelly"; cap страхует от fat-tails (BTC Student-t d.f.≈4) |

Формула f* binary: `f* = (p·b − q)/b`; SE(f*) ≈ (1+1/b)·√[p(1−p)/n]. Rebalance — ежедневно на trailing 3–6 мес. окне (Halls-Moore). Source: Kelly (1956) *BSTJ* 35:917–926; Thorp (2006) Handbook ch.54; MacLean–Thorp–Ziemba (2011) *Kelly Capital Growth*; Halls-Moore (2015) Ch.13 §13.2.

## 6. Circuit Breaker levels

| Уровень | Порог DD | Действие | Обоснование |
|---|---|---|---|
| **L1** | 15% equity drawdown | **Warn + reduce size ×0.5** (de-lever) | Ниже backtest MaxDD=25% — ранний Bayesian trigger. Magdon-Ismail–Atiya (2004): P(MDD>25%) имеет значимую массу при ожидаемом MaxDD=25%; снижение размера на 15% сохраняет вероятностную массу ниже 25% |
| **L2** | 22% equity drawdown | **Halt 24h, manual resume required** | Приближается к ожидаемому MaxDD; гипотеза "edge intact" требует явной проверки — аналог NYSE L2 (13%) 15-min halt |
| **L3** | 30% equity drawdown | **Full stop, manual restart** | 30% > backtest MaxDD ⇒ гипотеза отвергнута; аналог NYSE L3 (20%) end-of-day halt. Kirilenko et al. (2017): в Flash Crash автоматика должна уступать человеку, когда события выходят за модельное распределение |
| **Flash** | max(8%, 3·ATR) одного бара | **Immediate halt, cancel-all, flatten** | 3·ATR адаптируется к режиму (target hit rate 0.1–0.5% баров); 8% absolute floor ≈ NYSE L1, страхует от volatility compression когда ATR коллапсирует |

Source: NYSE Rule 7.12 (7/13/20%); Harris (2003) *Trading and Exchanges* Ch.28 "Bubbles, Crashes, and Circuit Breakers"; Kirilenko–Kyle–Samadi–Tuzun (2017) *JF* 72(3):967–998; Magdon-Ismail–Atiya (2004) "Maximum Drawdown" *Risk Magazine*; Harvey et al. (2020) "Drawdowns" *JPM* 46(8):34–50.

**Защита от ложных триггеров:** (a) drawdown считается от 24h high-water mark equity, не от session-start; (b) flash-detection использует close-to-close на текущем баре, не intrabar — чтобы не триггериться на wicks; (c) manual-resume после L2/L3 требует reconciliation `/api/v3/account` + `/myTrades` + checklist (§RUNBOOK).

## 7. State Machine (12 состояний)

**Состояния:** `IDLE`, `ANALYZE`, `SIGNAL`, `RISK_CHK`, `EXECUTE` (композитный: `SUBMITTING → WORKING → PARTIAL_FILL | FILLED | CANCELLING`), `MONITOR`, `HALT`, `RECONNECT`, `STALE_DATA`, `CLOCK_DRIFT`, `RATE_LIMITED`, плюс неявный `TERMINATED`.

**Паттерны:** Harel statecharts (EXECUTE — hierarchical); orthogonal parallel regions для watchdogs (STALE_DATA, CLOCK_DRIFT, RATE_LIMITED, RECONNECT могут firing из любого состояния); Hohpe & Woolf "Enterprise Integration Patterns" — Idempotent Receiver на `clientOrderId`, Dead Letter Channel на ошибочные события, Correlation Identifier (`newClientOrderId`).

**Ключевые переходы (сокращённо):**

```
IDLE --NewBar--> ANALYZE --IndicatorsReady--> SIGNAL --SignalEmitted--> RISK_CHK
RISK_CHK --RiskApproved--> EXECUTE.SUBMITTING --OrderAck--> EXECUTE.WORKING
EXECUTE.WORKING --FILLED--> MONITOR --OCOTriggered--> IDLE
EXECUTE.WORKING --PARTIAL--> EXECUTE.PARTIAL_FILL
EXECUTE.PARTIAL_FILL --FillTimeout--> EXECUTE.CANCELLING
EXECUTE.* --ErrCode(-1021)--> CLOCK_DRIFT
EXECUTE.* --HTTP429/-1003--> RATE_LIMITED
EXECUTE.* --ErrCode(-2010,-1013,-2018)--> IDLE (reject, no retry)
ANY --WSDisconnect--> RECONNECT --StateReconciled--> previous_state
ANY --NoBarFor(2·Δ)--> STALE_DATA --BarResumed--> IDLE
ANY --CircuitBreaker--> HALT --OperatorResume--> IDLE
```

**Критические edge-cases:**

1. **Reconnect с открытой позицией** — на WS resume: `GET /api/v3/openOrders?symbol=BTCUSDT` + `GET /api/v3/account` + `GET /api/v3/myTrades` от последнего известного `tradeId`. Если exchange-position ≠ local-position — **HALT, manual review** (никогда не реконсилировать автоматически при расхождении qty).

2. **STALE_DATA** — threshold `2·Δ = 7200s` tolerance на Binance maintenance; `4·Δ → HALT`. После resume — требовать 3 consecutive валидных бара (или перезапустить warm-up индикаторов если >N баров потеряно).

3. **CLOCK_DRIFT** — Binance `-1021` срабатывает при `timestamp > serverTime + 1000ms`. Держать `|drift|<250ms` через chrony с ≥3 stratum-1 peers; offset обновлять через `GET /api/v3/time` каждые 60s; при `drift>1s` — стоп подписанных запросов, resync, после 3 неудач — HALT.

4. **RATE_LIMITED** — token bucket per rate-limit-bucket (`REQUEST_WEIGHT@1m`, `ORDERS@10s`, `ORDERS@1d`); читать live limits из `/api/v3/exchangeInfo.rateLimits` при старте (не хардкодить 1200 — может быть 6000); на HTTP 429 honor `Retry-After` + jitter; на HTTP 418 — **HALT, ждать expiry бана (до 3 дней)**.

5. **PARTIAL_FILL на OCO-leg** — per Binance docs, любой terminal state (включая `PARTIALLY_FILLED`) на одной leg автоматически отменяет sibling. Бот должен детектить `listStatus`-event и **немедленно выпустить новый защитный ордер** на residual qty.

## 8. Domain Events (20 событий)

| # | Event | Producer | Consumers | Ключевой payload |
|---|---|---|---|---|
| 1 | `NewBar` | MarketData | SignalGen, Analytics | symbol, interval, openTime, closeTime, OHLCV, tradeCount |
| 2 | `SignalGenerated` | SignalGen | Risk, Analytics | signalId, barCloseTime, side, confidence, features dict |
| 3 | `RiskApproved` | Risk | Execution, Analytics | signalId, orderIntentId, qty, stopPrice, tpPrice |
| 4 | `RiskRejected` | Risk | Analytics | signalId, reason (enum) |
| 5 | `OrderPlaced` | Execution | Analytics, Monitor | clientOrderId, exchOrderId, symbol, side, type, qty, price, ts |
| 6 | `OrderFilled` | Execution | Position, Analytics | clientOrderId, fills[{qty,price,fee}], avgPrice |
| 7 | `PartialFill` | Execution | Execution-self, Analytics | clientOrderId, executedQty, cumQuoteQty, remainingQty |
| 8 | `OrderCancelled` | Execution | Analytics | clientOrderId, reason, executedQty |
| 9 | `PositionOpened` | Execution | Risk, Analytics | positionId, symbol, side, qty, avgEntryPrice |
| 10 | `PositionClosed` | Execution | Analytics | positionId, exitQty, avgExitPrice, realizedPnl |
| 11 | `DrawdownWarning` | Risk | Ops | equity, peakEquity, ddPct |
| 12 | `CircuitBreakerTriggered` | Risk | Execution(HALT), Ops | reason, ddPct, level |
| 13 | `WebSocketReconnect` | Infra | All | streamName, lastEventId, downtimeMs |
| 14 | `StaleDataDetected` | MarketData | Signal(HALT), Ops | lastBarCloseTime, ageMs |
| 15 | `ClockDriftDetected` | Infra | Execution(HALT), Ops | localMs, serverMs, driftMs |
| 16 | `RateLimitHit` | Gateway | Execution, Ops | endpoint, usedWeight, limit, retryAfterMs |
| 17 | `ConfigReloaded` | Ops | All | configHash, diff |
| 18 | `HeartbeatMissed` | Infra | Ops, Risk | since, missedCount |
| 19 | `OCOTriggered` | Execution | Position, Analytics | listClientOrderId, triggeredLeg (TP\|SL), qty, price |
| 20 | `FilterViolation` | Gateway | Risk, Ops | filter (LOT_SIZE\|PRICE_FILTER\|NOTIONAL), requested, allowed |

**Happy-path sequence:** `NewBar → SignalGenerated → RiskApproved → OrderPlaced → OrderFilled → PositionOpened → [MONITOR] → OCOTriggered → PositionClosed`.

**Error path (rate-limit retry):** `OrderPlaced → HTTP429 → RateLimitHit → [exponential backoff 2ⁿ·base+jitter, cap 60s, max 5 retries] → OrderPlaced(retry) | → CircuitBreakerTriggered(HALT)`.

**Event Sourcing:** persist append-only event log (SQLite table `events` с PK `(aggregateId, version)`) для всех aggregate-changing events; rebuild Order/Position агрегатов через replay; snapshot каждые N=100 events для bounded replay. Market data хранить отдельно (Parquet), ссылаться через `barCloseTime`. Outbox pattern: записывать event в локальный лог **до** ack Binance-response.

Source: Brandolini *Introducing EventStorming*; Evans (2003) *DDD* Ch.14 "Maintaining Model Integrity"; Vernon (2013) *IDDD* Ch.3, Ch.13.

## 9. Edge Case Catalog (20+)

| # | Edge case | Обнаружение | Действие |
|---|---|---|---|
| 1 | Missing bar (gap) | Δt между barами > period | Синтетический NaN-бар с `data_quality=GAP`, **без forward-fill OHLC**; skip signal generation |
| 2 | Consecutive missing >3 bars | Счётчик GAP-bars | `HALT_DATA_QUALITY`; требовать 3 valid bars после resume |
| 3 | volume=0 bar | `v==0` | Accept (возможно на illiquid pair), volume-filter корректно отвергнет |
| 4 | Duplicate timestamp | Same `openTime` дважды | Deduplicate, keep last (check `isClosed` flag) |
| 5 | Negative volume / price≤0 / OHLC inconsistent | Sanity check | Reject как corruption, re-fetch через REST, persistent → HALT |
| 6 | Stale bar (>1.5·Δ old) | `now − last_bar > 1.5·period` | Halt decisioning, listening continue |
| 7 | Out-of-order bar | `ts_new < ts_prev` | Reject, log, WS/REST sync check |
| 8 | WS dropout | No msg for 30s / heartbeat miss | Exponential backoff reconnect; dual WS optional (v0.2) |
| 9 | Clock drift >1s | chrony offset monitor | CLOCK_DRIFT → resync → retry; 3x fail → HALT |
| 10 | Rate limit 429 | `X-MBX-USED-WEIGHT >90%` или HTTP 429 | Token bucket throttle, honor `Retry-After` |
| 11 | IP ban HTTP 418 | status 418 | HALT, ждать expiry (до 3 дней), alert |
| 12 | Partial fill entry timeout | >T_fill=60s в PARTIAL_FILL | Cancel residual, adopt executed qty (check min filters) |
| 13 | Partial fill OCO leg | listStatus `PARTIALLY_FILLED` на leg | Немедленно re-issue защитный ордер на residual qty |
| 14 | Duplicate signal на том же баре | Signal registry по `bar_ref.closeTime` | Reject `REJECT_DUPLICATE_SIGNAL` |
| 15 | Insufficient balance -2010 | Pre-trade balance check | Reduce size до max feasible или reject |
| 16 | Filter violation -1013 (LOT/PRICE/NOTIONAL) | Pre-submit local filter validator | Round qty до `stepSize`, price до `tickSize`, ensure `qty·price ≥ minNotional`; если всё равно невозможно → reject |
| 17 | HTTP 5xx / -1006 / -1007 (status unknown) | Network/timeout error | **Не ретраить с новым clientOrderId**; query `GET /api/v3/order?origClientOrderId=X`; адоптить state |
| 18 | Server crash mid-fill | systemd restart с WAL SQLite | Reconcile при boot: `/openOrders` + `/account` + `/myTrades` from last tradeId |
| 19 | Config drift prod/test | Config hash on boot | CI-diff на PR, immutable config в prod, 4-eyes deploy |
| 20 | Wrong API key (prod/testnet) | Startup self-test: place+cancel $0.01 order на известном endpoint | Kill-switch при mismatch |
| 21 | Flash crash >10% в 1H | `|Δprice| > max(8%, 3·ATR)` на close | Immediate HALT, cancel-all, flatten |
| 22 | Listen-key expiry (60min) | Timer + WS-error | Refresh каждые 30min через PUT `/api/v3/userDataStream` |
| 23 | Exchange maintenance | Binance status RSS + `503` codes | Flatten positions pre-maintenance, no entries в последний час |
| 24 | USDT depeg (|1−price|>1%) | Stablecoin monitor | Flatten USDT exposure, alert |

## 10. Acceptance Criteria

**System-level (6 — infrastructure works):**

| # | Критерий | Порог | Метод измерения |
|---|---|---|---|
| S1 | Uptime | ≥99.5% rolling 30d (excluding documented Binance downtime) | Heartbeat 1/s, Prometheus |
| S2 | WS reconnect time | p99 < 5s from disconnect to first new tick | WS client timestamps, histogram |
| S3 | P&L reconciliation | ≥99.99% (local vs `/account` + `/myTrades`) | Nightly diff; fail if >1 bp for >1 day |
| S4 | Dashboard update latency | p95 < 2s from fill event to UI | Grafana histogram |
| S5 | Config hot-reload | Non-critical params 0s downtime; critical require restart | SIGHUP reload, chaos test |
| S6 | Zero API key leaks | 0 secrets в git/logs/images | `gitleaks`, `trufflehog` в CI, IP whitelist + no-withdrawal permission |

**Strategy-level (6 — strategy works, OOS only):**

| # | Критерий | Порог | Обоснование |
|---|---|---|---|
| T1 | Sharpe OOS (annualized net) | ≥1.0 | Реалистичный target; >2.0 suspicious; >3.0 almost certainly overfit (Hudson–Urquhart 2021) |
| T2 | Sortino OOS | ≥1.5 | Trend-following с positive skew должен показывать Sortino > Sharpe |
| T3 | MaxDD | <25% | Trend-following на BTC historically 15–30%; <10% suspicious |
| T4 | Win rate | ≥45% при RR≥1.5 OR ≥35% при RR≥2.0 | Trend-following typically 35–50%; >65% suspicious |
| T5 | Math expectation per-trade | >0 с t-stat >2.0 | Guards против random-noise edge; требует n≥100 OOS trades |
| T6 | OOS/IS Sharpe ratio | ≥0.7 | Primary overfit-detector; degradation >30% red flag |

Supporting (не gating): Deflated Sharpe Ratio >0; PBO <0.5; Calmar >0.5.

Source: Halls-Moore (2015) Performance Measurement chapter; AFML Ch.14; Bailey–López de Prado (2014); Hudson & Urquhart (2021) *Annals of OR* 297:191–220.

## 11. ADR Template (Michael Nygard, 2011)

```markdown
# NNNN. <Title: the decision, not the problem>

Date: YYYY-MM-DD

## Status
Proposed | Accepted | Deprecated | Superseded by [NNNN](./NNNN-....md)

## Context
What is the issue that we're seeing that motivates this decision?
Describe forces at play: technological, market, operational, statistical.

## Decision
What is the change we're proposing? Active voice: "We will ..."

## Consequences
Positive, negative, and neutral consequences.

## Alternatives considered
Alt 1: ... (rejected because ...)
Alt 2: ... (rejected because ...)

## References
[Author, Year, Chapter, Page]
```

**Initial ADR list для v0.1:**
- 0001 — Record architecture decisions (meta)
- 0002 — Python-only for MVP (rejects Rust+Python)
- 0003 — SQLite + Parquet for storage (rejects QuestDB for v0.1)
- 0004 — Binance Spot as initial venue
- 0005 — 1H timeframe MVP
- 0006 — Pydantic v2 for domain models
- 0007 — UTC timestamps everywhere, ns precision
- 0008 — Event loop uvloop
- 0009 — SemVer 2.0.0 + Keep a Changelog 1.1.0
- 0010 — Square-root slippage model (rejects quadratic Q²)
- 0011 — Wilder EMA for ADX/RSI/ATR; Classical EMA for crossover
- 0012 — 4-phase Kelly sizing
- 0013 — Circuit breakers L1=15%/L2=22%/L3=30%/flash=max(8%,3·ATR)
- 0014 — Walk-Forward with train=2000/test=500 bars for 1H
- 0015 — Sign-flip MC permutations N=2000 primary

Source: Nygard (2011) "Documenting Architecture Decisions", cognitect.com/blog/2011/11/15.

## 12. Data Dictionary с DDD Bounded Contexts

**Bounded Contexts (5):**

1. **Market Data Context** — ingestion, normalization, gap detection, persistence of OHLCV and L2.
2. **Signal Generation Context** — indicators computation, strategy logic, signal emission.
3. **Risk Management Context** — position sizing (Kelly phases), drawdown monitoring, circuit breakers, filter pre-validation.
4. **Order Execution Context** — order placement, OCO management, fill handling, reconciliation.
5. **Analytics Context** — P&L reporting, performance metrics, audit trail, DSR/PBO computations.

**Relationships:** Market Data → Signal Gen (Customer/Supplier, published language = `NewBar`); Signal Gen → Risk (Customer/Supplier); Risk ↔ Execution (Partner); Execution ↔ Binance (Anti-Corruption Layer — translates REST/WS to domain events); Analytics (Conformist — consumes events only).

**Ubiquitous Language (24 терминa):**

| Термин | Context | Определение |
|---|---|---|
| Bar (OHLCV) | Market Data | Completed candle for interval Δ closed at `closeTime`; value object, immutable; invariant `low ≤ min(o,c) ≤ max(o,c) ≤ high` |
| Closed Bar | Market Data | Bar с `closeTime < now`; только closed bars питают Signal Gen (look-ahead-protection invariant) |
| Signal | Signal Gen | Value object `{side ∈ {LONG, FLAT}, confidence ∈ [0,1], bar_ref}`; ссылается на конкретный Closed Bar |
| Indicator | Signal Gen | Pure function over Bars → scalar/vector; immutable state, deterministic |
| Risk Approval | Risk | Authorization event с qty + price bounds + sl/tp |
| Order | Execution | Aggregate root; lifecycle `NEW → (PARTIALLY_FILLED →)? FILLED\|CANCELED\|EXPIRED\|REJECTED`; `clientOrderId` unique + immutable; `executedQty ≤ origQty` monotonic |
| OCO (One-Cancels-the-Other) | Execution | Bracket из двух contingent orders; terminal state одного cancels другой automatically on Binance |
| Working order | Execution | Active leg currently on the book (Binance terminology) |
| Pending order | Execution | Leg held off-book до trigger (OTO/OTOCO terminology) |
| Fill / Execution Report | Execution | WS `executionReport` с partial или full match |
| Partial Fill | Execution | `0 < executedQty < origQty` |
| Position | Execution | Aggregate root; `qty ≥ 0` (spot); один active entry Order + максимум один OCO bracket |
| Round-trip / Trade | Analytics | Entry + exit closed cycle; immutable once closed |
| Drawdown | Risk | Peak-to-trough decline of equity curve от high-water mark |
| Circuit breaker | Risk | Automatic HALT при DD ≥ threshold (см. §6) |
| Equity | Analytics | Cash + mark-to-market value открытых позиций |
| Slippage | Analytics | `(fill_price − decision_price) / decision_price` в bps |
| Tick size / Step size / Min notional | Execution | Binance filters (`PRICE_FILTER`, `LOT_SIZE`, `NOTIONAL.minNotional`) |
| Weight | Execution | Cost of REST endpoint against `REQUEST_WEIGHT` bucket |
| Recv window | Execution | Server-side tolerance (`recvWindow`, default 5s, max 60s) |
| Listen key | Execution | User-data-stream auth key (expires 60min, refresh каждые 30min) |
| Client Order ID | Execution | `newClientOrderId` idempotency token; pattern `"{strategy}-{bar_close_epoch}-{uuid4_short}"` |
| Reconciliation | Execution | Diff между local Order/Position аггрегатами и exchange state |
| Heartbeat | Infra | 30s WS ping (Binance sends every 20s, pong required within 1min) |

**Aggregates и invariants:** см. разделы 8 и 2.

Source: Evans (2003) *Domain-Driven Design*; Vernon (2013) *Implementing DDD*; Brandolini *Introducing EventStorming*.

## 13. Risk Register (22 риска в 4 категориях)

**Технические (6):** WS dropout (**H**igh prob / $50–500), rate-limit (M/$0–2000), server crash (L/$500–5000), clock drift (L/rejection), DB corruption (L/$1K–10K), stale data (M/$100–2000). Митигация: dual WS (v0.2), token bucket rate-limiter, systemd watchdog `Restart=always`, chrony ≥3 stratum-1, SQLite WAL + nightly offsite dump, data-quality pipeline pre-indicator.

**Рыночные (5):** flash crash (L/$1.5K–7.5K), exchange maintenance (H/$0–5K depending на holding), regime change (H/$2K–8K gradual), liquidity shock (L/$200–2K slippage), symbol delisting + USDT depeg (L/total-position). Митигация: circuit breakers (§6), calendar-aware flatten pre-maintenance, monthly walk-forward re-optimization, volume-adaptive sizing (`limit ≤ k·rolling_median_volume`), USDC fallback plan.

**Операционные (5):** wrong API key prod/testnet (**M/catastrophic**), insufficient balance (M/$50–500), wrong pair in config (**L/catastrophic**), config drift (M/$500–5K), unpatched OS (**M/catastrophic — key exfiltration**). Митигация: startup self-test с $0.01 place+cancel на known endpoint; pre-trade balance check с 10% cash floor; config-as-code с CI validation + symbol whitelist; hashes diff per env; minimal Docker image + CVE scanner (Trivy) daily + WireGuard VPN + hardware 2FA + Binance IP whitelist + withdrawal whitelist.

**Статистические (5):** overfitting (H/$1K–10K gradual bleed), look-ahead bias (M/silent), data snooping (H/inflated edge→oversize Kelly), survivorship bias (L для BTC-only), regime change invalidating backtest (H/$2K–15K). Митигация: DSR (Bailey–López de Prado 2014), OOS/IS ≥0.7 gate, CPCV (v0.2+), parameter count ≤ log₂(n_trades), pre-registration of hypothesis; future-bar poison test в CI, `shift(1)` enforcement + property tests; Bonferroni/Holm correction; BTC-only (survivorship non-issue); KS test / CUSUM на live-vs-backtest distribution, revert к Phase 1 при p<0.01.

Framework: ISO 31000:2018 (process identify→analyse→evaluate→treat→monitor) + NIST SP 800-30 Rev. 1 (Risk = Likelihood × Impact с H/M/L scoring).

## 14. Reason Codes Schema (JSON)

**JSON Schema Draft 2020-12** — полная запись в audit-log после каждой сделки/отказа/halt. Ключевые поля (сокращённо, полная версия в DATA_SCHEMA.md):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://algo.local/schemas/trade_audit.v1.json",
  "required": ["schema_version","trade_id","timestamp","symbol",
               "signal_inputs","risk_decision","execution","reason_code"],
  "properties": {
    "schema_version": "1.0.0",
    "trade_id": "uuid",
    "parent_trade_id": "uuid|null",
    "timestamp": "ISO-8601 UTC ns",
    "symbol": "BTCUSDT",
    "venue": "BINANCE_SPOT",
    "strategy_id": "string",
    "strategy_version": "semver",
    "git_commit": "hex7-40",
    "config_hash": "sha256",
    "bar_closed": "bool (invariant: true for all live decisions)",
    "clock_drift_ms": "number",
    "signal_inputs": {
      "bar_timestamp": "ISO-8601",
      "bar_ohlcv": {...},
      "ema_fast": "number", "ema_slow": "number",
      "ema_fast_period": "int", "ema_slow_period": "int",
      "adx_14": "0..100", "plus_di_14": "0..100", "minus_di_14": "0..100",
      "rsi_14": "0..100", "atr_14": "number", "volume_sma_20": "number",
      "data_quality": "OK|STALE|GAP_FILLED|SUSPECT",
      "signal_reason": "EMA_CROSS_UP_WITH_ADX_CONFIRM | ... | NO_SIGNAL"
    },
    "risk_decision": {
      "account_equity": "number", "available_balance": "number",
      "kelly_phase": "0..5", "position_fraction": "0..1",
      "position_size_quote": "number", "position_size_base": "number",
      "sl_price": "number", "tp_price": "number",
      "sl_distance_atr": "number", "tp_distance_atr": "number",
      "rr_ratio": "number", "max_risk_quote": "number",
      "portfolio_exposure": "0..1", "drawdown_pct": "0..1"
    },
    "execution": {
      "order_id_local": "string", "order_id_exchange": "string|null",
      "client_order_id": "string", "order_type": "MARKET|LIMIT|STOP_MARKET|STOP_LIMIT|TAKE_PROFIT",
      "side": "BUY|SELL", "time_in_force": "GTC|IOC|FOK|POST_ONLY",
      "intended_price": "number", "fill_price": "number|null",
      "fill_qty": "number", "slippage_bps": "number|null",
      "fee_quote": "number", "fee_asset": "string", "fee_is_maker": "bool",
      "time_submit_ms": "int", "time_ack_ms": "int",
      "time_fill_ms": "int", "time_to_fill_ms": "int", "retry_count": "int"
    },
    "reason_code": "enum (see below)",
    "notes": "string, max 2048",
    "prev_record_hash": "sha256 — tamper chain",
    "record_hash": "sha256 of this record"
  }
}
```

**Reason code enum (28 кодов):** `ENTRY_LONG_TREND_FOLLOWING`, `ENTRY_SHORT_TREND_FOLLOWING`, `ENTRY_LONG_PULLBACK`, `ENTRY_SHORT_PULLBACK`, `SCALE_IN_LONG`, `SCALE_IN_SHORT`, `SCALE_OUT_PARTIAL`, `EXIT_SL_HIT`, `EXIT_TP_HIT`, `EXIT_TRAILING_STOP`, `EXIT_SIGNAL_FLIP`, `EXIT_TIME_STOP`, `EXIT_CIRCUIT_BREAKER`, `EXIT_MANUAL_OVERRIDE`, `REJECT_RISK_EXCEEDED`, `REJECT_INSUFFICIENT_BALANCE`, `REJECT_STALE_DATA`, `REJECT_RATE_LIMITED`, `REJECT_CLOCK_DRIFT`, `REJECT_MIN_NOTIONAL`, `REJECT_FILTER_PRICE`, `REJECT_DUPLICATE_SIGNAL`, `HALT_DRAWDOWN_L1`, `HALT_DRAWDOWN_L2`, `HALT_FLASH_CRASH`, `HALT_DATA_QUALITY`, `HALT_EXCHANGE_OUTAGE`, `HALT_KILL_SWITCH`.

**Storage:** JSONL append-only daily-rotated (`audit-YYYY-MM-DD.jsonl.gz`), `record_hash = SHA-256(prev_record_hash || canonical_json(record))` — tamper-evident chain. Secondary SQLite index `audit.db` (WAL mode) с `(trade_id, timestamp, symbol, reason_code, file_offset)` для O(log n) lookups — rebuildable from JSONL, never source of truth. Cold storage: daily gzip в S3/Glacier с ObjectLock WORM.

**Retention:** 7 years hot + cold (consistent с MiFID II RTS 24, SEC 17a-4, CFTC 1.31, хотя для retail crypto формальной обязанности нет). Аудит-запись ~1 KB, хранение бесконечно бесплатно.

## 15. CI/CD Pipeline

**Pre-commit hooks (local):**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks: [{id: ruff, args: [--fix]}, {id: ruff-format}]
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks: [{id: mypy, args: [--strict, --ignore-missing-imports]}]
  - repo: https://github.com/Yelp/detect-secrets
    hooks: [{id: detect-secrets, args: ['--baseline', '.secrets.baseline']}]
  - repo: local
    hooks:
      - id: pytest-fast
        entry: pytest -q -m "not integration and not slow" --maxfail=1
```

**GitHub Actions on-PR (.github/workflows/ci.yml):** 6 jobs — `lint-and-type` (ruff + mypy strict), `unit-tests` (pytest с coverage ≥80%), `property-tests` (hypothesis), `lookahead-check` (custom `scripts.lookahead_detector --strict` — future-bar poison test), `backtest-regression` (fixture на known-good dataset, assert identical PnL and trade list), `integration-testnet` (Binance testnet с secrets).

**On-tag release (.github/workflows/release.yml):** Docker build+push в GHCR с metadata-action semver tags, cache GHA layers; SSH deploy на VPS через appleboy/ssh-action — `docker compose pull && docker compose up -d --remove-orphans && docker image prune -f`.

**Secrets:** GitHub Secrets для CI; `.env` file `chmod 600` на VPS для docker-compose; Binance production keys с IP whitelist + trading-only permission (no withdrawal) + quarterly rotation. Alternative: SOPS+age для gitops-style.

**Release tagging:** SemVer 2.0.0 signed GPG tags `vMAJOR.MINOR.PATCH`. Pragmatic semantics для trading bot: **MAJOR** = breaking change к strategy behaviour / risk model / persisted schema; **MINOR** = новая strategy или exchange backward-compatible; **PATCH** = bug fixes, dep bumps, refactors. CHANGELOG.md по Keep a Changelog 1.1.0.

**Rollback:** immutable image per release `ghcr.io/user/bot:v0.2.3`, compose pins tag через env var `BOT_VERSION`; rollback = `env edit + docker compose up -d` за <30s. Kill-switch env var `TRADING_ENABLED=false` → read-only mode (cancel open orders, no new entries).

**Observability (v0.3):** Sentry (free 5K events/мес); `prometheus_client` `/metrics`; Grafana dashboards — equity, DD, per-trade PnL, WS disconnects, order rejects, rate-limit headroom; structlog JSON → journalctl или Loki; healthchecks.io dead-man's switch (ping каждые 70min → SMS alert).

## 16. Execution timing convention

**Канонический стандарт:** `Signal on close of bar T → order placed at open of bar T+1`. Это единственный вариант, который (a) не содержит look-ahead bias by construction; (b) соответствует real-world execution latency (1–5s между close и next-open на 1H — pренебрежимо); (c) согласован с vectorized research pipeline `signal.shift(1) × returns[t+1]`.

**Отвергнутые альтернативы:**
| Вариант | Почему отвергнут |
|---|---|
| (b) Intra-bar signal + immediate market order | **Текстбуковый look-ahead bias** — использует ещё не закрытый close (Halls-Moore §3.2, Harris) |
| (c) Signal on close + immediate market order | Размывает границу decision/execution, плохо бэктестится из OHLCV; underestimate adverse selection |
| (d) Signal on close + limit at `close ± k·ATR` | Вносит fill-probability uncertainty; допустимо **только как v0.2 refinement** после (a) baseline |

**Backtest implementation:**
```python
# signal computed at close of T, fill at open of T+1 with slippage
signal[t] = strategy(bars[0..t])        # use only closed bars
entry_px[t+1] = open[t+1] * (1 + slip_bps/1e4 * sign(signal[t]))
pnl[t+1]      = signal[t] * (close[t+1] - entry_px[t+1]) / entry_px[t+1] \
              - fee_bps/1e4 * 2
# Invariant: .shift(1) enforced; property test asserts signal_ts < fill_ts
```

**Production implementation:** на WS `kline` event с `k.x == true` (terminal bar message; **не** on every intra-bar tick): (1) run strategy → Signal; (2) within ~1s submit MARKET order **или** LIMIT IOC at `close ± tolerance` (tolerance ≈ 1 tick или small ATR fraction) для capping slippage; (3) после entry-fill event — place OCO bracket (TP + SL) как separate call.

**Hard look-ahead-protection invariants** (enforced по ACL + property tests):
1. Indicator computed только на `Bar` с `closeTime < now`.
2. `Signal` value object carries `bar_ref.closeTime`; Execution context отказывает в orders с `bar_ref.closeTime > previous_closed_bar.closeTime`.
3. Backtest: signals shift ≥1 bar before fill simulation.
4. Property test asserts `signal_ts < fill_ts` для каждой сделки в audit log.
5. Integration test: feed live WS stream в backtester event-order; result equals vectorized backtest within slippage tolerance.
6. Freqtrade-style `lookahead-analysis` regression test в CI — re-run с signals computed up to each t isolated, compare to full backtest.

Source: Chan (2013) *Algorithmic Trading* Ch.2; Pardo (2008) Ch.4–5; Halls-Moore (2015) §3.2; Freqtrade lookahead-analysis docs.

## Conclusion

Документ снимает все 10 выявленных рассогласований с опорой на первичные источники. **Главный сдвиг в эпистемологии** — от "best-practice заклинаний" к количественно обоснованным решениям: Wilson CI объясняет, почему Kelly-фазы именно n=30/100/200; Monte Carlo SE формула даёт N=2000, а не магическую 10,000; Bayesian drawdown-анализ превращает "L1=15% при MaxDD=25%" из противоречия в корректный risk buffer; no-arbitrage теорема Gatheral исключает квадратичную Q²-модель slippage.

**Принцип доминирующий над всеми решениями** — **right-sizing complexity to actual workload**. 1 бар/час = 8760 событий/год. Python+uvloop даёт 3 порядка headroom; SQLite+Parquet — 7 порядков. Добавлять Rust, QuestDB, Kafka, Kubernetes до того, как профилировка покажет проблему — это Qwen/ChatGPT-подход, который Knuth в 1974 назвал "root of all evil". Архитектурная дисциплина v0.1 — каждое усложнение требует ADR с измеренным обоснованием, а не априорного убеждения "enterprise надо делать правильно".

**Новое понимание для принятия решений:** результат Hudson & Urquhart (2021) о **негативной OOS-производительности простых MA-правил на BTC после 2017** меняет ожидания: target Sharpe ≥1.0 OOS — это аспирация, не нормальный baseline. Это должно прямо влиять на решение о масштабировании — требовать **≥200 реальных сделок** (Phase 4 Kelly) и DSR > 0 перед committing >2× initial capital. При средней частоте 2–5 trades/week это 12+ месяцев live trading прежде чем можно говорить о серьёзном масштабировании — и этот timeline обязательно должен быть зашит в product roadmap, иначе Kelly-фазы превратятся в формальность.

**Следующие шаги:** (1) создать 15 стартовых ADR согласно шаблону §11; (2) имплементировать `scripts/lookahead_detector.py` как CI gate; (3) написать `tests/property/test_no_future_reference.py` через hypothesis; (4) откалибровать `κ` slippage-модели после 200 реальных fills; (5) запустить PKCV-валидацию на 5 годах BTC 1H с ≤45 конфигурациями (MinBTL bound) и применить DSR к выбранной. v0.2/v0.3 milestones определяются измеренной потребностью, не календарём.