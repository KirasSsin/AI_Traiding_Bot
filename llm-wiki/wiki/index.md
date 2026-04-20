# Index

Каталог всех страниц wiki. Обновляется на каждом ingest.

## Trading — Strategies

- [[trading/strategies/ema-crossover-adx-rsi]] — MVP v0.1: EMA(12)×EMA(26) classical + ADX(14) Wilder + RSI(14) Wilder + ATR(14) Wilder, Binance Spot BTC/USDT 1H, LONG+FLAT.

## Trading — Indicators

- [[trading/indicators/ema]] — Exponential Moving Average (classical α=2/(n+1)), использование в crossover.
- [[trading/indicators/adx]] — Average Directional Index (Wilder α=1/n) + `+DI`/`-DI`, фильтр тренда.
- [[trading/indicators/rsi]] — Relative Strength Index (Wilder), гейт перегрева.
- [[trading/indicators/atr]] — Average True Range (Wilder), вход/SL/TP/position sizing.

## Trading — Patterns

_(пусто — v0.2+)_

## Trading — Concepts

- [[trading/concepts/kelly-phases]] — 4-фазный Kelly sizing: fixed 1%/2% → Q-Kelly cap 3% → Half-Kelly cap 5%, с Wilson 95% CI.
- [[trading/concepts/circuit-breakers]] — L1=15% warn+half-size, L2=22% halt 24h, L3=30% full stop, flash=max(8%, 3·ATR).
- [[trading/concepts/slippage-model]] — Fixed 5 bps (<$10k) + sqrt κ·σ·√(Q/V) (>$50k или >0.1% ADV).
- [[trading/concepts/walk-forward-validation]] — train=2000, test=500, K=5, embargo=20 баров, OOS/IS≥0.7 gate.
- [[trading/concepts/deflated-sharpe-ratio]] — DSR по Bailey–López de Prado, коррекция Sharpe на skew/kurt/N configs.
- [[trading/concepts/monte-carlo-permutations]] — sign-flip N=2000 (primary) + block-bootstrap L=20-50 (secondary).
- [[trading/concepts/reason-codes]] — 28 enum-кодов (6 entry + 7 scale/exit + 8 rejects + 7 halts).
- [[trading/concepts/look-ahead-bias]] — 5 канонических форм, 6 invariants, CI gate detector, property tests.

## Project — Architecture

- [[project/architecture/overview]] — MVP v0.1 target: стек, roadmap, риски, acceptance.
- [[project/architecture/current-state]] — инвентаризация текущего кода (Bybit futures 1m, pandas .ewm(), in-memory).
- [[project/architecture/gap-analysis]] — 24 расхождения current vs MVP v0.1 с приоритетами P0/P1/P2.
- [[project/architecture/migration-plan]] — 10 спринтов, 3-4 месяца, local-first; Docker/deploy → v0.2.
- [[project/architecture/development-workflow]] — Superpowers pipeline (7 скиллов) маппится на 10 спринтов v0.1.

## Project — Plans

- [[project/plans/2026-04-20-sprint-1-foundation]] — implementation plan Sprint 1 (storage + pydantic v2 + cleanup).
- [[project/architecture/stack-v0.1]] — Python 3.12 + asyncio/uvloop + TA-Lib + pydantic v2 + structlog; Docker-compose sketch.
- [[project/architecture/bounded-contexts]] — 5 DDD контекстов: Market Data / Signal Gen / Risk / Execution / Analytics.
- [[project/architecture/domain-events]] — 20 domain events + event sourcing SQL + happy/error/reconnect paths.
- [[project/architecture/state-machine]] — 12-state Harel statechart, watchdogs, edge cases.
- [[project/architecture/storage]] — SQLite WAL (OLTP) + Parquet snappy (OLAP), полные схемы таблиц.
- [[project/architecture/execution-timing]] — signal on close(T) → fill at open(T+1), 6 invariants.
- [[project/architecture/edge-cases]] — 24 edge-кейса: детекция + реакция + reason code.
- [[project/architecture/risk-register]] — 22 риска (technical/market/operational/statistical) по ISO 31000.
- [[project/architecture/acceptance-criteria]] — S1-S6 + T1-T6 + поддерживающие метрики + gating flow.
- [[project/architecture/reason-codes-schema]] — JSON Schema Draft 2020-12 для audit-record + SHA-256 chain.

## Project — Components

- [[project/components/config]] — `Settings` (pydantic-settings v2): env/.env, Binance creds, trading_enabled/live_trading invariant, paths.
- [[project/components/logging]] — structlog JSON pipeline → stdout, обязательные ключи event/level/timestamp, contextvars.
- [[project/components/models]] — pydantic v2 domain models: Bar / Signal / Order / Fill с инвариантами (OHLC, look-ahead, executed_qty ≤ orig_qty).
- [[project/components/storage]] — SQLite WAL (OLTP, 8 таблиц + migrations runner) + Parquet snappy writer (OLAP).

## Project — Experiments

_(пусто — Stage 3+: бэктесты, walk-forward runs, A/B на paper-trade)_

## Project — Decisions

- [[project/decisions/0001-record-architecture-decisions]] — использовать ADR-формат для всех значимых решений.
- [[project/decisions/0002-python-only-for-mvp]] — только Python, без микросервисов, для v0.1.
- [[project/decisions/0003-sqlite-parquet-for-storage]] — SQLite (OLTP) + Parquet (OLAP), без Postgres.
- [[project/decisions/0004-binance-spot-as-initial-venue]] — Binance Spot как первая биржа v0.1.
- [[project/decisions/0005-1h-timeframe-mvp]] — 1H таймфрейм для MVP (баланс шум/частота).
- [[project/decisions/0006-pydantic-v2-for-domain-models]] — pydantic v2 вместо dataclass.
- [[project/decisions/0007-utc-timestamps-ns-precision]] — UTC ns-precision ISO-8601 везде.
- [[project/decisions/0008-event-loop-uvloop]] — uvloop как drop-in замена asyncio loop.
- [[project/decisions/0009-semver-keepachangelog]] — SemVer + Keep-a-Changelog для strategy_version.
- [[project/decisions/0010-sqrt-slippage-model]] — sqrt-формула для больших ордеров, Q² отвергнута.
- [[project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — Wilder для ADX/RSI/ATR, classical для EMA-crossover.
- [[project/decisions/0012-4-phase-kelly-sizing]] — 4 фазы Kelly (n<30, n<100, n<200, n≥200).
- [[project/decisions/0013-circuit-breakers-l1-l2-l3-flash]] — L1/L2/L3/flash hierarchy.
- [[project/decisions/0014-walk-forward-train2000-test500]] — train=2000 / test=500, K=5, embargo 1%.
- [[project/decisions/0015-sign-flip-mc-permutations-n2000]] — sign-flip MC N=2000 как primary test.

## Queries (saved answers)

_(пусто)_
