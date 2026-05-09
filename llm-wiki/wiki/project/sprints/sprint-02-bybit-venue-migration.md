---
title: Sprint 2 — Миграция на Bybit + инжест MarketData
type: sprint
tags: [sprint, sprint-2, bybit, marketdata, ingest, venue-migration]
created: 2026-04-22
updated: 2026-04-22
sources: [project/plans/2026-04-21-sprint-2-bybit-venue-migration.md]
status: completed
---

# Sprint 2 — Миграция на Bybit + инжест MarketData

**Dates:** 2026-04-21 → 2026-04-22
**Plan:** [[../plans/2026-04-21-sprint-2-bybit-venue-migration]]
**Tag:** `v0.1.0-alpha.2`
**Merge PR:** #1
**Commit range:** `ca1b436..99c1e75` (18 коммитов)

## Цель

Сменить venue с Binance на Bybit Spot (ADR 0016) и реализовать MarketData ingest (REST backfill + WS live + BarBuilder + Parquet writer) плюс минимальный Execution ACL (MARKET order). Source: `migration-plan.md §S2`.

## Доставленная функциональность

### Код — MarketData
- `src/marketdata/bybit/rest.py` — `BybitRESTClient`: `get_server_time()`, `get_filters()`, `get_klines()` (paginated, max 1000/call, enforces `[start_ms, end_ms)`).
- `src/marketdata/bybit/ws.py` — `BybitWSConsumer`: мост pybit-callback → asyncio.Queue → `async for msg in stream()`, через `call_soon_threadsafe`.
- `src/marketdata/clock.py` — `ClockDriftMonitor`: сравнение `time.time_ns()` с Bybit server time, threshold для `CLOCK_DRIFT` детекции.
- `src/marketdata/filters.py` — `BybitFilters` (pydantic v2): `tickSize`, `minOrderQty`, `minOrderAmt`, `basePrecision`; методы `round_qty()`, `round_price()`, `validate_order(qty, price)`.
- `src/marketdata/bar_builder.py` — `BarBuilder`: venue-agnostic aggregator с 3 инвариантами (confirm-gate / dedup / out-of-order reject) + синтетический GAP bar (`data_quality=GAP`, OHLCV=0, no forward-fill per edge-case #1).
- `src/marketdata/gaps.py` — `find_gaps(parquet_dir, interval_ms) → list[(start, end)]`: сканирует Parquet-архив, находит пропуски для REST-backfill.
- `src/marketdata/pipeline.py` — `MarketDataPipeline`: orchestrator seed-gaps (REST) → WS stream → BarBuilder → Parquet writer.

### Код — Execution
- `src/execution/bybit/errors.py` — `ReasonCode` (StrEnum) + `_MAP: dict[int, ReasonCode]` + `map_error(ret_code, ret_msg) → ReasonCode`. Покрыты retCode: 10002, 10003, 10006, 10016, 110007, 110017, 170131, 170140, 170213.
- `src/execution/bybit/adapter.py` — `BybitMarketAdapter.place_market_order(client_order_id, side, qty, reference_price) → Order`: pre-trade validate через `BybitFilters` → `pybit.HTTP.place_order(category="spot", orderType="Market", ...)` → retCode mapping → `Order(status=NEW)` или `BybitAPIError(reason)`.

### Tests
- Unit: `test_bybit_rest.py` (6), `test_bybit_ws.py` (2), `test_clock.py` (3), `test_filters.py` (6), `test_bar_builder.py` (6), `test_gaps.py` (3), `test_pipeline.py` (2), `test_bybit_errors.py` (7), `test_bybit_adapter.py` (4), `test_deps.py` (2).
- Integration: `tests/integration/test_testnet_smoke.py` — env-gated (`PYTEST_RUN_INTEGRATION=1`), реальный MARKET BUY 0.001 BTCUSDT на testnet.

### Config
- `pyproject.toml`: `python-binance` → `pybit>=5.11`, mypy overrides для `pybit.*`, `testpaths = ["tests/unit"]`, markers `integration`.
- `.env.example`: `BINANCE_*` → `BYBIT_*` с testnet defaults.
- `Makefile`: добавлен target `test-integration`.

### Вики
- ADR: [[../decisions/0016-bybit-spot-supersedes-binance]] с V5 endpoint map + UTA account type.
- Components: [[../components/bybit-rest]], [[../components/bybit-ws]], [[../components/bar-builder]], [[../components/bybit-adapter]].
- Modified: ADR 0004 (status → superseded), `architecture/{migration-plan,stack-v0.1,bounded-contexts,edge-cases,overview}.md`, `components/config.md`.

## Решения и отклонения

- **New ADR 0016** — Bybit Spot supersedes Binance. **Rationale:** политические/регуляторные причины + unified V5 API (одна библиотека pybit покрывает spot + futures + options, что уменьшает долг v0.2).
- **`Settings` rename Binance→Bybit с testnet-defaults.** **Rationale:** user-directive — безопасное умолчание для тестов.
- **`BybitFilters.validate` → `validate_order`.** **Rationale:** pydantic v2 имеет classmethod `BaseModel.validate`, что создавало mypy --strict конфликт.
- **`BybitRESTClient.get_klines` enforces `[start_ms, end_ms)` exclusive end** через `if open_ms >= end_ms: continue` в row loop. **Rationale:** Bybit V5 `end` параметр **inclusive**, что нарушало docstring-контракт. Добавлен test `test_get_klines_excludes_end_ms_boundary` (RED→GREEN, commit `c058cfa`).
- **`BybitWSConsumer.start` использует `asyncio.get_running_loop()`**, не `get_event_loop()`. **Rationale:** последний deprecated в Python 3.12+.
- **`BarBuilder` имеет 2 варианта API:** `process(msg) → Bar | None` и `process_with_gap_fill(msg) → tuple[Bar|None, Bar|None]`. **Rationale:** call sites в `pipeline.py` нужен явный gap-bar для персистенции; single-stream consumers — только real bar.
- **`type: ignore[call-overload]`** в `BarBuilder` (не `[arg-type]` как в плане). **Rationale:** mypy фактически репортит `call-overload` для pydantic `Literal`-параметра.
- **`BybitMarketAdapter` использует `self._rest._http.place_order(...)`** (private-attribute coupling) — flagged reviewer, deferred to Sprint 2 follow-up.

## Проверка

- `make check`: **green** — ruff clean, mypy --strict clean, pytest 63/63 unit passed.
- Tests: 63 unit (20 из S1 + 43 новых) + 1 env-gated integration.
- Manual: integration smoke requires `PYTEST_RUN_INTEGRATION=1 + testnet API-keys`.
- PR #1 merged into `main` at 2026-04-22.

## Влияние на следующие спринты

- **S3 (Strategy port)** получает: `Bar` stream из `MarketDataPipeline`, готовые `OHLC` данные в Parquet для warm-up индикаторов, `Signal` модель из S1 — можно напрямую писать `on_bar(Bar) → Signal | None`.
- **S4 (Risk)** получает: `BybitFilters.validate_order()` для pre-trade checks, `ReasonCode` enum для FILTER_VIOLATION/RATE_LIMIT_HIT/INSUFFICIENT_BALANCE halt-reasons.
- **S5 (OCO/Reconciler)** получает: `BybitMarketAdapter` как baseline для LIMIT/OCO расширения + `BybitRESTClient` для query-order/cancel-order.
- **S7 (Backtest)** получает: Parquet-архив с ascending `close_time`, `data_quality=OK|GAP`, gap-detection для целостности серии.

## Перенесённые задачи

- [ ] **`BybitRESTClient.place_order(...)` passthrough** — adapter сейчас дёргает приватный `rest._http`. Вынести как public-метод. **Scope:** 1 test + 5 строк кода. **Target:** S3 или начало S4.
- [ ] **Residual Binance refs** в `architecture/migration-plan.md` (lines 90, 116, 341) и `edge-cases.md` (rows #22, #23). **Target:** при любом следующем wiki-ingest.
- [ ] **Final adversarial Sprint 2 code review** не прогнан (агент упёрся в квоту). Inline-проверка зелёная, но глубокого adversarial-прохода нет. **Target:** опциональный `code-reviewer` запуск перед S3.
- [ ] **ADR 0004 frontmatter** — status: superseded by 0016 не проставлен в YAML-хедере (только прозой). **Target:** cosmetic fix в любом ingest.

## Related

- Plan: [[../plans/2026-04-21-sprint-2-bybit-venue-migration]]
- ADR: [[../decisions/0016-bybit-spot-supersedes-binance]]
- Components: [[../components/bybit-rest]], [[../components/bybit-ws]], [[../components/bar-builder]], [[../components/bybit-adapter]]
- Architecture: [[../architecture/migration-plan]] §S2, [[../architecture/edge-cases]], [[../architecture/bounded-contexts]]
- Prior sprint: [[sprint-01-foundation]]
