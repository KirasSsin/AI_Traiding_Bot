---
title: Migration Plan — Current → MVP v0.1
type: architecture
tags: [migration, plan, v0.1, local-first]
created: 2026-04-20
updated: 2026-04-20
status: stable
sources: [wiki/project/architecture/gap-analysis.md, wiki/project/architecture/overview.md, wiki/project/architecture/acceptance-criteria.md]
---

# Migration Plan — Current → MVP v0.1

**TL;DR:** 10 спринтов (3-4 месяца) переводят Bybit linear 1m → Binance Spot 1H с DDD, SQLite+Parquet, Kelly 4 фазы, CB L1/L2/L3/flash. MVP **работает локально на ноутбуке**; Docker/SSH-deploy/cold-storage — в v0.2 Deploy release.

## Принципы

- **TDD.** Тесты до кода; DoD спринта включает green suite.
- **Minimal changes.** Не рефакторим то, что не меняем (CLAUDE.md).
- **Legacy изолируется.** Старый код переезжает в branch `legacy/phase1-bybit` (не удаляется), main становится v0.1.
- **Feature flags через env vars.** `TRADING_ENABLED`, `LIVE_TRADING`, `SENTRY_DSN`, `DATA_SOURCE` (REST_SEED / WS / REPLAY).
- **Wiki-first.** Каждый спринт заканчивается обновлением `wiki/project/components/<name>.md` + `wiki/log.md` + ADR если решение нетривиально.
- **Local-first.** MVP запускается на одном ноутбуке (macOS/Linux); Docker и VPS — v0.2+.

## График зависимостей

```
                S1 (Foundation)
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
  S2 (Venue)  S3 (Strat)  S6 (Events)       ← параллельно после S1
                 │          │
                 ▼          │
          S4 (Risk/CB)      │
                 │          │
      ┌──────────┘          │
      ▼                     │
  S5 (Exec) ◄── S2 ◄────────┘                ← S5 нуждается в S2, S4, S6
      │
      ▼
  S7 (Validation) ◄── S3, S4, S6             ← S7 замыкает backtest/MC/DSR
      │
      ▼
  S8 (Audit/Obs) ◄── S5, S6                  ← S8 пишет из events и execution
      │
      ▼
  S9 (Local dev ergonomics)
      │
      ▼
  S10 (Paper trade mainnet)
```

## До / После: структура `src/`

### До (текущее, 8 папок без явных границ)

```
src/
├── core/           models.py (dataclass), math_engine.py
├── data/           consumer.py (BybitDataConsumer)
├── strategy/       strategy.py, hmm_regime.py, order_flow.py
├── risk/           risk_manager.py
├── execution/      executor.py (BybitExecutor, market-only)
├── gateway/        market_data_pb2.py, ..._grpc.py (stubs, unused)
├── backtest/       vector_backtest.py
├── ml/             models.py (XGBPredictor, unused)
├── controller.py
└── main.py
```

### После (MVP v0.1, 5 DDD bounded contexts)

```
src/
├── marketdata/     # Market Data Context
│   ├── binance_consumer.py    (WS + REST fallback)
│   ├── bar_builder.py         (isClosed gate, UTC ns ts)
│   ├── storage.py             (Parquet writer + SQLite cursor)
│   └── models.py              (Bar, Tick — pydantic v2)
├── signalgen/      # Signal Generation Context
│   ├── indicators.py          (TA-Lib EMA/ADX/RSI/ATR wrappers)
│   ├── strategy.py            (EMA-cross + ADX + RSI gate)
│   └── models.py              (Signal — pydantic v2)
├── risk/           # Risk Management Context
│   ├── kelly.py               (4 phases)
│   ├── circuit_breakers.py    (L1/L2/L3/flash)
│   ├── sizing.py              (qty = f·equity/(1.5·ATR))
│   └── manager.py
├── execution/      # Order Execution Context (ACL для Binance)
│   ├── binance_adapter.py     (python-binance wrapper)
│   ├── oco.py                 (OCO bracket placement)
│   ├── reconciler.py          (post-reconnect)
│   ├── state_machine.py       (12-state)
│   └── models.py              (Order, Fill — pydantic v2)
├── analytics/      # Analytics Context (Conformist)
│   ├── audit.py               (JSONL + SHA chain + SQLite index)
│   ├── backtest.py            (walk-forward + MC + DSR)
│   └── lookahead_detector.py
├── platform/       # cross-cutting
│   ├── events.py              (20 domain events)
│   ├── event_bus.py           (async pub-sub, outbox)
│   ├── db.py                  (SQLite connection, migrations)
│   ├── logging.py             (structlog config)
│   └── config.py              (pydantic-settings)
├── app.py          # orchestrator (replaces controller.py)
└── main.py         # entry point: asyncio.run(app.run())
```

### Соответствие: старый путь → новый

| Current | → | v0.1 | Action |
|---------|---|------|--------|
| `src/core/models.py` | → | `src/*/models.py` (split per context) | Rewrite as pydantic v2. |
| `src/core/math_engine.py` (Kelly, CVaR) | → | `src/risk/kelly.py`, `src/risk/manager.py` | Port + add 4 phases. |
| `src/core/math_engine.py` (Hurst, ADF) | → | `legacy/` | Не используется в v0.1 (ADR 0002). |
| `src/data/consumer.py` | → | `src/marketdata/binance_consumer.py` | Rewrite pybit → python-binance. |
| `src/strategy/strategy.py` | → | `src/signalgen/strategy.py` | Rewrite: classical EMA + Wilder ADX/RSI/ATR via TA-Lib. |
| `src/strategy/hmm_regime.py` | → | `legacy/` | Out of scope v0.1. |
| `src/strategy/order_flow.py` | → | `legacy/` | Out of scope v0.1. |
| `src/risk/risk_manager.py` | → | `src/risk/manager.py` | Port + 4-phase Kelly + CB hierarchy. |
| `src/execution/executor.py` | → | `src/execution/binance_adapter.py` | Rewrite; add OCO, partial-fill. |
| `src/gateway/` | → | `legacy/` | gRPC микросервис — v0.3+. |
| `src/backtest/vector_backtest.py` | → | `src/analytics/backtest.py` | Extend: walk-forward + MC + DSR. |
| `src/ml/models.py` | → | `legacy/` | ML вне scope v0.1. |
| `src/controller.py` | → | `src/app.py` | Rewrite вокруг event bus + state machine. |
| `src/main.py` | → | `src/main.py` | Слим-entry point, логика в `app.py`. |
| `web/dashboard.html`, `web/data.json` | → | сохраняются as-is | Локальный UI для мониторинга. |
| `tests/test_math.py` | → | `tests/unit/test_math_engine.py` | Keep + extend. |

## План заморозки legacy

**Sprint 1, шаг 1:**
```bash
git checkout -b legacy/phase1-bybit
git push -u origin legacy/phase1-bybit
git checkout main
# работа продолжается в main без удаления — файлы deleted через git rm по ходу спринтов
```

**Удаление (через `git rm`) происходит поэтапно:**
- S1: удаление `src/ml/`, `src/gateway/`, `src/strategy/hmm_regime.py`, `src/strategy/order_flow.py`.
- S2: удаление `src/data/consumer.py` (Bybit), замена.
- S3: удаление `src/strategy/strategy.py`, замена.
- S5: удаление `src/execution/executor.py`, замена.

**Восстановление:** `git checkout legacy/phase1-bybit -- <path>`.

---

## Спринты

### S1 — Foundation (2 недели)

- **Goal:** заложить persistent layer, pydantic v2 модели, вычистить legacy.
- **Scope in:** SQLite schema + Parquet writer; pydantic v2 (Bar, Signal, Order, Fill); platform/ каркас (config, logging, db); legacy freeze + удаление ml/ gateway/ hmm/order_flow.
- **Scope out:** real data source (S2), indicators (S3).
- **AC:**
  - `make test` зелёный; `ruff` + `mypy --strict` без ошибок.
  - SQLite init через `alembic upgrade head` создаёт все таблицы (см. [[storage]]).
  - pydantic-модели валидируют OHLC (high≥max(open,close), volume≥0).
  - Branch `legacy/phase1-bybit` pushed, main очищен.
- **Dependencies:** none.
- **Artifacts:** `src/platform/`, `src/marketdata/storage.py`, `src/marketdata/models.py`, `src/signalgen/models.py`, `src/execution/models.py`, `tests/unit/*`, wiki/project/components/{storage, models, config}.md, `migrations/`.

### S2 — Venue migration (2 недели)

- **Goal:** Binance Spot data consumer + базовая MARKET execution (dry-run).
- **Scope in:** WS kline stream (1H), REST seed, gap detection, bar builder с `isClosed` gate, testnet exec MARKET, normalize qty через `exchangeInfo` filters (MIN_NOTIONAL, LOT_SIZE, PRICE_FILTER).
- **Scope out:** OCO / partial-fill (S5), reconciliation (S5).
- **AC:**
  - WS принимает 24h BTCUSDT 1H без потерь; gaps логируются и filled через REST.
  - Все bars с `confirm=true` персистятся в Parquet (Parquet-only per ADR 0003).
  - Тестнет MARKET BUY 0.001 BTCUSDT (≈$60 при spot ценах ~60k); retCode errors 10002/110007/170140 → `ReasonCode` через `BybitErrorMapper`.
  - Clock drift check через `/v5/market/time`; drift>1s → `ClockDriftError`.
- **Dependencies:** S1.
- **Artifacts:** `src/marketdata/bybit/{rest,ws}.py`, `src/marketdata/{clock,filters,bar_builder,gaps,pipeline}.py`, `src/execution/bybit/{adapter,errors}.py`, wiki/project/components/{bybit-rest, bybit-ws, bar-builder, bybit-adapter}.md. См. [[../decisions/0016-bybit-spot-supersedes-binance]].

### S3 — Strategy port (1 неделя)

- **Goal:** EMA(12)×EMA(26) classical + ADX(14) Wilder + RSI(14) Wilder + ATR(14) Wilder через TA-Lib; entry/exit rules.
- **Scope in:** indicators wrappers; strategy.on_bar(closed=True) → Signal; Signal carries `bar_ref.closeTime`; execution-timing invariants (см. [[execution-timing]]).
- **Scope out:** sizing (S4), SL/TP execution (S5).
- **AC:**
  - Unit tests: TA-Lib results совпадают с manual Wilder EMA на 200 fixture-bars (tolerance 1e-9).
  - Property test (hypothesis): signal_ts < fill_ts для любого сгенерированного bar-stream.
  - Golden-output test: на 6 месяцев исторических 1H-данных сигналы совпадают с baseline-implementation (внутренней).
- **Dependencies:** S1.
- **Artifacts:** `src/signalgen/indicators.py`, `src/signalgen/strategy.py`, `tests/unit/test_strategy.py`, `tests/property/test_lookahead.py`, wiki/project/components/{strategy, indicators}.md.

### S4 — Risk & Circuit Breakers (1.5 недели)

- **Goal:** 4-phase Kelly sizing + L1/L2/L3/flash CB + drawdown monitor.
- **Scope in:** Kelly по фазам (n<30, n<100, n<200, ≥200); CB детекторы; position sizing `qty = (f·equity)/(1.5·ATR)`; кумулятивный DD tracker (equity curve в SQLite).
- **Scope out:** OCO execution (S5).
- **AC:**
  - Unit tests: Kelly transitions при n=29→30, n=99→100, n=199→200.
  - Property test: sizing никогда не превышает cap фазы (1%/2%/3%/5%).
  - CB L1/L2/L3 триггерятся на fixture equity curves с DD 15.1%/22.1%/30.1%.
  - Flash CB: single-bar return ≤ -max(0.08, 3·ATR) → `HALT_FLASH_CRASH`.
  - Manual resume через `state/cb_override.json` file + signature check.
- **Dependencies:** S1, S3.
- **Artifacts:** `src/risk/{kelly,circuit_breakers,sizing,manager}.py`, `tests/unit/test_risk.py`, wiki/project/components/{risk-manager, kelly, circuit-breakers}.md.

### S5 — Execution advanced (2 недели)

- **Goal:** OCO bracket (SL+TP), partial-fill handling, post-reconnect reconciliation, 12-state machine.
- **Scope in:** OCO placement (SL=entry-1.5·ATR, TP=entry+3.0·ATR); partial-fill: продолжаем OCO на оставшийся qty; reconcile `/openOrders` + `/account` + `/myTrades` при WS reconnect; divergence → HALT; state machine (Harel) со всеми переходами.
- **Scope out:** trailing stop (v0.2).
- **AC:**
  - Integration test на testnet: entry MARKET → OCO placed → SL triggered → position closed → audit log записан.
  - Partial-fill test: 50% fill → OCO на оставшиеся 50% корректен; reason_code = `EXIT_TP_HIT` только на полный close.
  - Reconciliation test: kill process → exchange executes SL → restart → state reconstructed без divergence.
  - State machine: все 12 состояний + 28+ переходов покрыты table-driven тестом.
- **Dependencies:** S1, S2, S4.
- **Artifacts:** `src/execution/{oco,reconciler,state_machine}.py`, `tests/integration/test_execution.py`, wiki/project/components/{oco, reconciler, state-machine}.md, ADR по OCO failure mode (if needed).

### S6 — Event Sourcing (1.5 недели)

- **Goal:** 20 domain events, append-only event log в SQLite, outbox pattern для reliable publishing.
- **Scope in:** events pydantic-модели; `events` table (см. [[storage]]); outbox writer; snapshots каждые N=100 events на aggregate; event bus (asyncio pub-sub, in-process).
- **Scope out:** distributed messaging (Kafka/NATS) — v0.3+.
- **AC:**
  - Property test: `(aggregate_id, version)` — primary key, violation → error.
  - Replay test: drop state → replay events из SQLite → state идентичен.
  - Outbox test: crash между write-event и publish → на restart publish повторяется (at-least-once).
  - Все 20 events в [[domain-events]] эмитятся в соответствующих местах.
- **Dependencies:** S1 (может идти параллельно с S2-S5).
- **Artifacts:** `src/platform/{events,event_bus}.py`, `tests/unit/test_events.py`, `tests/integration/test_replay.py`, wiki/project/components/{event-bus, event-sourcing}.md.

### S7 — Validation & Safety (2 недели)

- **Goal:** walk-forward CV K=5 + sign-flip MC N=2000 + DSR + look-ahead CI gate.
- **Scope in:** walk-forward harness (train=2000, test=500, embargo=20); MC permutations; DSR calculation; `scripts/lookahead_detector.py --strict` (future-bar poison test); Freqtrade-style regression test; hypothesis property tests.
- **Scope out:** PKCV K=10 (v0.2).
- **AC:**
  - Walk-forward на 2y BTC 1H-данных: OOS/IS≥0.7 gate проходит или явно fail → стратегия доработке.
  - DSR>0 на baseline (см. [[acceptance-criteria]] S1-S6).
  - `scripts/lookahead_detector.py --strict` в pre-commit; изменение signal на poisoned future → exit code ≠ 0.
  - MinBTL check (López de Prado): кол-во tested configs ≤ MinBTL bound.
- **Dependencies:** S3, S4, S6.
- **Artifacts:** `src/analytics/{backtest,lookahead_detector}.py`, `scripts/lookahead_detector.py`, `tests/property/`, wiki/project/experiments/2026-XX-XX-baseline-walkforward.md.

### S8 — Audit & Observability (1.5 недели)

- **Goal:** JSONL audit log + SHA-256 chain + SQLite index; structlog; optional Sentry.
- **Scope in:** audit writer (canonical JSON, SHA chain); daily rotation + gzip; `audit_index` SQLite; structlog JSON output в `./logs/bot.log` (rotating); Sentry client (включается `SENTRY_DSN` env).
- **Scope out:** Prometheus/Grafana (v0.3); S3/Glacier cold storage (v0.2+).
- **AC:**
  - Chain verification script (см. [[reason-codes-schema]]) проходит на 10k synthetic records.
  - Audit record для каждой сделки: reason_code ∈ 28-enum, git_commit, config_hash, bar_closed=true.
  - structlog пишет в `./logs/bot.log.YYYY-MM-DD` (daily rotate, 7-day retention локально).
  - Sentry init через env; off по умолчанию; test: raise → capture (если включён).
- **Dependencies:** S5, S6.
- **Artifacts:** `src/analytics/audit.py`, `src/platform/logging.py`, `scripts/verify_audit_chain.py`, wiki/project/components/{audit, logging}.md.

### S9 — Local dev ergonomics (1 неделя)

- **Goal:** comfortable local dev loop + release candidate ready для S10 paper-trade.
- **Scope in:** pre-commit (ruff, mypy, pytest, lookahead_detector); Makefile (`test`, `backtest`, `run-paper`, `clean`); `.env.example`; SemVer tag v0.1.0-rc1; simple local healthcheck endpoint (`http://127.0.0.1:8080/health`).
- **Scope out:** Dockerfile, docker-compose, GitHub Actions, SSH deploy, Prometheus — всё это **v0.2 Deploy release**.
- **AC:**
  - `make test` зелёный на чистом clone.
  - `make backtest` запускает walk-forward на fixture-данных, producing HTML report.
  - `make run-paper` стартует бота с `LIVE_TRADING=false`, логи в stdout + файл.
  - pre-commit блокирует коммит на mypy/lint/lookahead fail.
  - `CHANGELOG.md` в Keep-a-Changelog формате; tag `v0.1.0-rc1`.
- **Dependencies:** S1-S8.
- **Artifacts:** `Makefile`, `.pre-commit-config.yaml`, `.env.example`, `CHANGELOG.md`, wiki/project/components/local-dev.md.

### S10 — Paper trade on mainnet (4+ недели)

- **Goal:** Kelly Phase 1 (fixed 1%) на mainnet с минимальным капиталом; сбор 30+ сделок для phase transition.
- **Scope in:** real API keys (read+trade, no withdraw); минимальный капитал ($100-500 USDT); 24/7 процесс через `systemd --user` (Linux) / `launchd` (macOS) / `screen` (fallback); daily `rsync` `./data/` → cloud folder; `caffeinate` (macOS) или `systemd-inhibit` (Linux) для sleep-prevention.
- **Scope out:** scaling capital > $500 USDT (v0.2); multi-symbol (v0.3).
- **AC:**
  - Бот работает 30+ дней continuously без manual intervention (restarts логируются).
  - 30+ completed trades (ENTRY + EXIT) в audit log; reconciliation divergence = 0.
  - Wilson 95% CI на realized win-rate; если нижняя граница > 50% и DSR>0 → переход к Kelly Phase 2.
  - Если DD reach L1 (15%) → investigate + possible strategy freeze.
- **Dependencies:** S9 + v0.1.0 tag.
- **Artifacts:** wiki/project/experiments/2026-XX-XX-paper-trade-phase1.md (live log), daily status reports в `wiki/queries/`.

---

## Вне scope (v0.2 Deploy release)

- **Dockerfile + docker-compose** (local stack: bot + SQLite volume + Grafana + Prometheus).
- **GitHub Actions CI/CD** (6 jobs: lint, mypy, test, backtest regression, lookahead CI gate, Docker build).
- **VPS deploy** (SSH, systemd unit, nginx reverse-proxy для `/health`).
- **Remote secrets management** (.env → HashiCorp Vault / AWS Secrets Manager).
- **Cold storage** (`./data/audit/*.gz` → S3 Glacier с Object Lock WORM).
- **Prometheus/Grafana observability** (metrics: orders/sec, fill-latency p99, equity curve).
- **Remote healthcheck** (healthchecks.io integration).
- **Multi-region failover** (active-standby на втором VPS).

## Вне scope (v0.3+)

- Multi-symbol (ETHUSDT, SOLUSDT).
- Multi-timeframe (15m / 4H confirmation).
- Order-flow features (OBI, Kyle's λ).
- ML (XGBoost, HMM regime-gate).
- gRPC microservices split.
- Multi-venue (OKX, Bybit back as alternative).

---

## Операционный плейбук (локальный)

**Requirements:** macOS 14+ или Linux (Ubuntu 22+); Python 3.12; TA-Lib native (`brew install ta-lib` / `apt-get install libta-lib0-dev`); ноутбук с постоянным питанием во время paper-trade.

**Startup:**
```bash
cd AI_Traiding_Bot
cp .env.example .env  # отредактировать: BINANCE_API_KEY, BINANCE_API_SECRET
source .venv/bin/activate
make run-paper   # foreground; для 24/7 — systemd --user или screen
# в отдельном окне:
tail -f logs/bot.log | jq .
```

**Мониторинг:**
- `sqlite3 ./data/bot.db "SELECT state, updated_at FROM state ORDER BY updated_at DESC LIMIT 1;"` — текущее состояние state machine.
- `sqlite3 ./data/bot.db "SELECT reason_code, count(*) FROM audit_index GROUP BY 1;"` — распределение reason codes.
- Локальный dashboard: `open web/dashboard.html` (читает `web/data.json`).

**Резервирование:** `crontab -e` → `0 3 * * * rsync -a ~/AI_Traiding_Bot/data/ ~/iCloud/bot_backup/` (или Dropbox folder).

**Kill (graceful):** `pkill -SIGTERM -f "python.*src.main"` → бот закрывает позиции? **Нет** — только gracefully останавливается с open positions; OCO остаются на бирже. Ручная проверка через Binance UI.

**Kill-switch (экстренный):** `touch ./state/KILL_SWITCH` → бот увидит файл в следующем tick и перейдёт в `HALT_KILL_SWITCH`.

---

## Риски самой миграции

| # | Риск | P | Impact | Mitigation |
|---|------|---|--------|------------|
| M1 | Bybit klines (1m) ≠ Binance klines (1H) по семантике timestamp / isClosed | High | High | S2 AC включает explicit isClosed gate test; fixture data reference-проверка. |
| M2 | Wilder vs Classical смена → backtest на v1 код не сравним | High | Med | S3 golden-output на baseline; S7 re-run walk-forward полностью. |
| M3 | Удаление src/ml/ src/gateway/ сломает импорты controller.py | Med | Low | S1 атомарный коммит: удаление + правка imports + зелёный CI. |
| M4 | pybit → python-binance: разные async models | Med | Med | S2 integration test на testnet до замены. |
| M5 | Ноутбук sleep во время S10 → WS-disconnect → missed bars | High | Med | `caffeinate` / `systemd-inhibit`; reconciliation при wake-up. |
| M6 | Домашний Wi-Fi flakiness → rate 429 | Med | Low | Retry with exp backoff; weight tracking (см. edge-cases). |
| M7 | Ноут помер во время live trade → OCO на бирже остались | Low | High | Принимаем для MVP; v0.2 Deploy → VPS. |
| M8 | Временные диапазоны данных для walk-forward (2y BTC 1H) недоступны free | Low | Med | Binance `/klines` free для исторических; fallback — Kaggle datasets. |

---

## Стратегия отката

- **Per-sprint:** main branch всегда green; failed sprint → `git revert <merge-commit>`, а не reset.
- **Per-feature:** env-flag (e.g. `TRADING_ENABLED=false`) отключает live-placement без code rollback.
- **Full rollback к Bybit:** `git checkout legacy/phase1-bybit` → работоспособный Phase 1 bot. Приемлемо если v0.1 не сойдётся за 3 месяца.
- **Data rollback:** `./data/` backup daily → restore из iCloud/Dropbox при corruption.

---

## Связанные

- [[gap-analysis]] — почему миграция нужна (24 расхождения).
- [[overview]] — target v0.1 архитектура.
- [[acceptance-criteria]] — S1-S6 + T1-T6 критерии, привязанные к нашим спринтам.
- [[storage]] — schema, которую строит S1.
- [[domain-events]] — 20 events для S6.
- [[state-machine]] — 12 состояний для S5.
- [[execution-timing]] — invariants, которые S3/S5 обязаны соблюдать.
- [[reason-codes-schema]] — audit-record схема для S8.
- [[risk-register]] — операционные риски v0.1 (не этой миграции).
- ADR [[../decisions/0002-python-only-for-mvp]], [[../decisions/0004-binance-spot-as-initial-venue]], [[../decisions/0005-1h-timeframe-mvp]] — фундамент плана.
