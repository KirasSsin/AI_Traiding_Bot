---
title: Gap Analysis — current vs MVP v0.1
type: architecture
tags: [gap-analysis, migration, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [wiki/project/architecture/current-state.md, wiki/project/architecture/overview.md]
---

# Gap Analysis

**TL;DR:** 16 существенных расхождений между текущим кодом и MVP v0.1. Критичные: смена venue (Bybit → Binance Spot), таймфрейм (1m → 1H), добавление ADX, замена in-memory storage на SQLite+Parquet, DDD-реструктуризация, 12-state machine, 20 domain events, Kelly 4 фазы, circuit breakers L1/L2/L3/flash.

## Таблица расхождений

| # | Область | Current | MVP v0.1 | Действие | Приоритет |
|---|---------|---------|----------|----------|-----------|
| 1 | **Venue** | Bybit Linear (perpetual futures) | Binance Spot | Replace pybit → python-binance/ccxt; rewrite executor, data consumer | **P0 критично** |
| 2 | **Symbol side** | LONG + SHORT (futures) | LONG + FLAT (spot only, no shorts) | Remove SHORT logic from strategy | **P0 критично** |
| 3 | **Timeframe** | 1m (в `main.py`) | 1H | Change `interval="60"` + rebuild backtest на 1H-данных | **P0 критично** |
| 4 | **Strategy indicators** | EMA12/26 + RSI14 + ATR14 (через pandas) | EMA12/26 (classical) + ADX14 + RSI14 + ATR14 (Wilder) через **TA-Lib** | Add ADX + +DI/-DI; migrate to TA-Lib | **P0** |
| 5 | **Indicator semantics** | Pandas `.ewm()` (classical для всех) | Classical для EMA-crossover; **Wilder** для ADX/RSI/ATR (α=1/n) | Fix RSI/ATR smoothing algorithm | **P0** |
| 6 | **Data storage** | In-memory Python list (до 1000 Kline) | SQLite (OLTP) + Parquet (OLAP) | Implement persistent layer; bot survives restart | **P0** |
| 7 | **Domain models** | `@dataclass` (Kline, Signal, Order) | pydantic v2 | Rewrite models with validation + serialization | P1 |
| 8 | **Architecture** | 8 папок (data/strategy/risk/execution/gateway/backtest/ml/core) без явных границ | 5 DDD bounded contexts с published events | Restructure → marketdata/ + signalgen/ + risk/ + execution/ + analytics/ | P1 |
| 9 | **Event model** | Direct method calls (callback chain) | 20 domain events + append-only event log | Implement event sourcing в SQLite | P1 |
| 10 | **State machine** | Ad-hoc в controller | 12 формализованных состояний (Harel statecharts) | Implement StateMachine class + watchdogs | P1 |
| 11 | **Order types** | MARKET only | MARKET entry + OCO bracket (TP + SL) | Implement OCO placement + partial-fill handling | **P0** |
| 12 | **Risk — Kelly** | Fractional 0.5-Kelly при n≥10 | 4 фазы: 1% (n<30), 2% (n<100), Q-Kelly cap 3% (n<200), Half-Kelly cap 5% (n≥200) | Rewrite position sizing logic | P1 |
| 13 | **Risk — circuit breakers** | Kill-switch при daily DD >5% | L1=15% warn+half-size, L2=22% halt 24h, L3=30% full stop, flash=max(8%,3·ATR) | Implement CB hierarchy + manual resume | **P0** |
| 14 | **Event loop** | asyncio (default) | asyncio + **uvloop** | Drop-in replacement (1 line) | P2 |
| 15 | **Backtest** | VectorBacktester (KPIs only) | Walk-Forward K=5 + sign-flip MC N=2000 + DSR + PBO | Add CV harness + MC permutation + DSR | P1 |
| 16 | **Look-ahead protection** | Нет | 6 invariants + CI gate + property tests + integration test | Implement `scripts/lookahead_detector.py`, hypothesis tests | P1 |
| 17 | **Audit log** | Нет (только `web/data.json` UI state) | JSONL append-only + SHA-256 chain + SQLite index | Implement audit writer + reason_code enum | P1 |
| 18 | **Reconciliation** | Sync executions каждую минуту | Post-reconnect reconciliation: `/openOrders` + `/account` + `/myTrades`; HALT при divergence | Rewrite reconciliation logic | **P0** |
| 19 | **Error handling** | Basic | Full edge case catalog (24): clock drift, rate limit, HTTP 418, stale data, flash crash, ... | Implement detector + response для каждого | P1 |
| 20 | **Tests** | 4 math tests | Unit + property (hypothesis) + integration (testnet) + lookahead detector + backtest regression | Build test suite | P1 |
| 21 | **CI/CD** | Нет | ruff + mypy strict + pre-commit + GitHub Actions (6 jobs) + Docker GHCR + SSH deploy | Set up pipeline | P2 |
| 22 | **Observability** | `web/data.json` + dashboard.html | structlog JSON + Sentry + healthchecks.io + (v0.3) Prometheus/Grafana | Add structlog + Sentry client | P2 |
| 23 | **ML модули** | XGBPredictor, HMM (скелеты) | **Вне scope** v0.1 | Move `src/ml/`, `src/strategy/hmm_regime.py`, `src/strategy/order_flow.py` → `legacy/` branch | P0 cleanup |
| 24 | **gRPC gateway** | Stubs `src/gateway/` | **Вне scope** v0.1 (v0.3+) | Move → `legacy/` | P0 cleanup |

## Приоритизация

### **P0 (must-have для MVP, функциональные блокеры):**
1. Venue: Bybit → Binance Spot
2. Timeframe: 1m → 1H
3. Symbol side: remove SHORT
4. Strategy: add ADX (+DI/-DI) + Wilder smoothing через TA-Lib
5. Storage: SQLite + Parquet
6. Execution: OCO bracket + partial-fill
7. Circuit breakers L1/L2/L3/flash
8. Reconciliation при reconnect
9. Cleanup: убрать `src/ml/`, `src/gateway/`, `src/strategy/hmm_regime.py`, `src/strategy/order_flow.py`

### **P1 (важно для MVP quality):**
10. pydantic v2 domain models
11. 5 DDD bounded contexts
12. 20 domain events + event sourcing
13. 12-state state machine
14. Kelly 4 фазы
15. Walk-Forward + MC permutations + DSR
16. Look-ahead protection (CI gate + property tests)
17. Audit log (JSONL + SQLite index + reason codes)
18. Edge cases detectors (все 24)

### **P2 (nice-to-have, можно v0.2):**
19. uvloop (1-line swap)
20. CI/CD pipeline
21. structlog + Sentry
22. Grafana/Prometheus (v0.3)

## Реалистичная оценка объёма

Per MVP-спеке (§1): **2-3 месяца работы одного разработчика** для v0.1 с нуля. Наш случай **сложнее** (миграция + рефакторинг vs чистая инсталляция), но **имеет преимущества** (математика и часть infrastructure готовы).

Оценка по блокам:
- P0 (venue + data + execution + CB): 3-4 недели.
- P1 (DDD + events + state machine + validation + audit): 4-6 недель.
- P2 (CI/CD + observability): 1-2 недели.
- Тестирование + debug: **надбавка 50%**.

**Итого: 3-4 месяца** при фокусированной работе.

## Предлагаемые спринты (детали в [[migration-plan]] на Этапе 2)

1. **Sprint 1 — Foundation** (2 недели): storage layer (SQLite + Parquet), pydantic v2 models, cleanup legacy.
2. **Sprint 2 — Venue migration** (2 недели): Binance Spot data consumer (WS + REST), basic MARKET execution.
3. **Sprint 3 — Strategy port** (1 неделя): TA-Lib EMA+ADX+RSI+ATR, entry/exit rules, unit-tested.
4. **Sprint 4 — Risk & CB** (1.5 недели): Kelly 4 фазы, circuit breakers L1/L2/L3/flash, drawdown monitor.
5. **Sprint 5 — Execution advanced** (2 недели): OCO bracket, partial-fill, reconciliation, state machine.
6. **Sprint 6 — Event sourcing** (1.5 недели): 20 domain events, SQLite event log, outbox pattern.
7. **Sprint 7 — Validation & safety** (2 недели): walk-forward + MC + DSR, look-ahead detector, property tests.
8. **Sprint 8 — Audit & observability** (1.5 недели): JSONL + SHA chain + SQLite index, structlog, Sentry.
9. **Sprint 9 — CI/CD & deploy** (1 неделя): pre-commit, GitHub Actions, Docker, SSH deploy.
10. **Sprint 10 — Paper trade on mainnet** (4+ недели): Kelly Phase 1 (1% fixed), сбор 30+ сделок для phase transition.

## Related

- [[current-state]] — что есть сейчас.
- [[overview]] — target v0.1.
- `migration-plan.md` — детальный план (создаётся на Этапе 2).
