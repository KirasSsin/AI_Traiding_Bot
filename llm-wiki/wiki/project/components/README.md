---
title: Components — индекс доменных кластеров
type: navigation
tags: [navigation, components, clusters, llm-friendly]
created: 2026-04-25
updated: 2026-05-09
status: stable
sources:
  - project/mental-map.md
  - index.md
---

# Components — индекс доменных кластеров

> **Для LLM-агентов:** этот файл = тематический reverse lookup ("я читаю X — что связано?"). Дополняет плоский алфавитный список `index.md`. Используй, когда читаешь один компонент и нужен связанный контекст.

**TL;DR:** 31 страница компонентов, сгруппированных по 10 доменным кластерам (Market Data + Signal + Risk + Execution + Resilience + Runtime + Infrastructure + Backtest + Tooling + Analytics). Каждый кластер имеет anchor (основной компонент) + поддерживающие компоненты. Кросс-кластерные связи — в секции "Bridge components".

## Кластер 1 — Приём рыночных данных (Market Data ingest)

**Тема:** OHLCV pipeline (REST seed + WS live + bar building + storage). Начало: S2 (ADR 0016).

| Компонент | Роль |
|-----------|------|
| **[[bybit-rest]]** | pybit V5 HTTP wrapper — server_time, instruments_info, paginated klines |
| [[bybit-ws]] | pybit WebSocket callback → asyncio iteration мост (S2 legacy, replaced by ws-private-consumer for execution) |
| [[bar-builder]] | venue-agnostic aggregator — confirm-gate + dedup + out-of-order + gap synthesis |
| [[bar-poller]] | REST kline 5s cadence + stall detection (S8a) |
| [[data-quality]] | REST-vs-REST consecutive bar deviation detector → HALT_DATA_QUALITY (S9 Q1) |

**Мост к:** Storage (writes Parquet) → Strategy (consumer)

## Кластер 2 — Генерация сигналов (Signal generation)

**Тема:** Strategy + indicators (look-ahead-free, signal on close(T) → fill open(T+1)). Начало: S3 (ADR 0011, 0017).

| Компонент | Роль |
|-----------|------|
| **[[strategy]]** | EmaCrossoverAdxRsiStrategy — `on_bar(Bar) → Signal \| None`, FLAT/LONG FSM |
| [[indicators]] | TA-Lib wrappers — EMA classical/Wilder + ADX/±DI/RSI/ATR Wilder |
| [[models]] | pydantic v2 domain models — Bar/Signal/Order/Fill с look-ahead invariants |

**Мост к:** Risk (Signal → assess) → Execution (start_bracket)

## Кластер 3 — Risk + sizing

**Тема:** 4-phase Kelly + Wilson 95% CI + L1/L2/L3/flash CB + manual override. Начало: S4 (ADR 0012, 0013, 0018).

| Компонент | Роль |
|-----------|------|
| **[[risk-manager]]** | orchestrator — `assess(signal, mark_price) → RiskAssessment` с look-ahead invariant |
| [[kelly]] | 4-phase Kelly + Wilson 95% CI; pure functions, KellyCaps from Settings |
| [[circuit-breakers]] | L1/L2/L3/Flash detector (stateless); CircuitBreakerConfig from Settings |
| [[sizing]] | `compute_qty(equity, fraction, atr, price, k)` ATR-based pure function |
| [[risk-override]] | Manual CB resume gate — HMAC-SHA256 signed JSON + config_hash anti-replay + atomic write 0o600 |
| [[trade-history]] | Per-trade audit log — TradeRecord + TradeHistoryRepository + UNIQUE INDEX entry_signal_id (Kelly trade-count source) |
| [[fill-history]] | Per-fill audit log — FillRecord + FillHistoryRepository (FK trade_history) + WS execution topic source (S9 Q3 B1) |

**Мост к:** Execution (approved Signal → Coordinator.start_bracket)

## Кластер 4 — Исполнение + OCO (Execution + OCO)

**Тема:** 3-order Spot OCO emulation + 16-state Harel FSM + bracket lifecycle. Начало: S5/S6 (ADR 0019, 0020).

| Компонент | Роль |
|-----------|------|
| **[[coordinator]]** | Central orchestrator — FSM dispatch (`_transition`) + bracket lifecycle (`start_bracket`/`arm_oco`/`flatten`) + halt mechanics (`request_halt`) + reconcile delegation. 8 RLock-protected methods. |
| [[execution-state-machine]] | 16 states / 30 events / 74 transitions table-driven `TRANSITIONS` + `IllegalTransitionError` |
| [[oco]] | 3-order bracket (Entry Market + TP Limit + SL StopMarket IOC) + builder (`compute_oco_qty`, `make_order_link_id`) |
| [[bybit-adapter]] | MARKET/Limit/StopMarket spot execution + 6 methods + filter-validate + retCode→ReasonCode + banned-field guard |

**Мост к:** Resilience (Reconciler ↔ Coordinator), Runtime (RuntimeManager owns Coordinator lifecycle)

## Кластер 5 — Устойчивость (Resilience, S7)

**Тема:** Bootstrap reconcile + 4-valued verdicts + γ halt persistence + WS reconnect. Начало: S7 (ADR 0021).

| Компонент | Роль |
|-----------|------|
| **[[reconciler]]** | 4-valued verdict producer (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED). walletBalance-as-truth для Spot. |
| [[ws-private-consumer]] | pybit WebSocket close-hook + check_alive watchdog. Routes order/wallet events → Coordinator/Reconciler. |

**Мост к:** Execution (Reconciler called from Coordinator.bootstrap + on_ws_reconnect), Runtime (WS consumer started by RuntimeManager)

## Кластер 6 — Runtime (S8a) — живой процесс

**Тема:** Владелец жизненного цикла процесса (bootstrap → tick loop → graceful shutdown). Начало: S8a (ADR 0022).

| Компонент | Роль |
|-----------|------|
| **[[runtime-manager]]** | Owns process lifecycle. Tick pipeline: `_maybe_kill_switch` → `_check_alive_inline` → `_poll_bar_and_strategy` → `_poll_or_arm_oco`. |
| [[bar-poller]] | REST kline 5s cadence + stall detection (cross-listed с Кластером 1) |
| [[kill-switch-cli]] | Operator-facing CLI (`python -m src run/backfill/reconcile-only/kill`) + sentinel-file atomic write semantics |

**Мост к:** Execution (RuntimeManager → Coordinator), Resilience (RuntimeManager → WS consumer)

## Кластер 7 — Инфраструктура (Infrastructure)

**Тема:** Cross-cutting platform — config, logging, storage. Начало: S1.

| Компонент | Роль |
|-----------|------|
| **[[config]]** | Settings (pydantic-settings v2) — env/.env, Bybit creds, trading_enabled/live_trading invariant, paths |
| [[logging]] | structlog JSON pipeline → stdout, обязательные ключи event/level/timestamp, contextvars |
| [[storage]] | SQLite WAL (OLTP, 8 tables + migrations runner) + Parquet snappy writer (OLAP) |

**Мост к:** ALL clusters (everything uses Settings + structlog + storage)

## Кластер 8 — Backtest + WFA (S2-era + S10 production WFA)

**Тема:** Backtest pipeline — replay engine + vector backtest + reporter + WFA orchestrator + MC permutations. **S10 возродил S2 backtest engine + расширил production WFA layer per ADR 0025.**

| Компонент | Роль |
|-----------|------|
| **[[backtest-harness]]** | Одна страница охватывает 6 src/backtest файлов (replay_engine + vector_backtest + reporter + indicators + data_collector + replay-stub) |
| [[walk-forward]] | WindowSplitter + WalkForwardRunner + acceptance gate (S10 Q1+Q4, ADR 0014+0025) |
| [[mc-permutations]] | sign-flip primary + block bootstrap secondary (S10 Q3, ADR 0015) |
| [[wfa-reporter]] | 3-Sharpe series routing + DSR aggregate informational (S10 Q4+Q6+Q7) |

## Кластер 9 — Tooling / хуки

**Тема:** PreToolUse `git push` хуки для обеспечения инвариантов wiki. Начало: S7 (adr-agent-sync) + S8c T11 (adr-index-sync) + Bucket C7 pre-S9 (wiki-broken-link).

| Компонент | Роль |
|-----------|------|
| [[adr-agent-sync-hook]] | Блокирует push если ADR изменён, но `~/.claude/agents/*.md` mtime не обновлён (per ADR 0017) |
| [[adr-index-sync-hook]] | Блокирует push если новый ADR не прописан в `wiki/index.md` |
| [[wiki-broken-link-hook]] | Блокирует push если изменённые wiki-файлы содержат broken `[[link]]` refs (Bucket C7) |

## Кластер 10 — Аналитика (Analytics, S9+ foundation)

**Тема:** Статистические post-process модули. Начало: S9 Q3 B2.

| Компонент | Роль |
|-----------|------|
| **[[dsr]]** | Bailey & López de Prado Deflated Sharpe Ratio — pure-function on TradeRecord array. Pearson kurtosis. **S10: sigma_sr extension closes S9 NYI (n_trials > 1, Bailey eq. 12).** |

**Мост к:** Risk (consumes trade_history TradeRecord), [[walk-forward]] + [[wfa-reporter]] (S10 aggregate DSR consumer)

## Bridge components (мультикластерные)

Эти компоненты охватывают несколько кластеров — учитывать при кросс-кластерных изменениях:

| Компонент | Кластеры | Почему |
|-----------|----------|--------|
| **coordinator** | Execution + Resilience + Runtime | FSM owner + reconcile delegate + halt API consumed by RuntimeManager |
| **reconciler** | Resilience + Execution | 4-valued verdict producer; called from Coordinator |
| **bar-poller** | Market Data + Runtime | REST kline source + RuntimeManager tick consumer |
| **bybit-rest** | Market Data + Execution | HTTP V5 client shared для kline seeding (C1) и order execution через BybitAdapter (C4) |
| **storage** | Infrastructure + ALL clusters | SQLite WAL (execution_state, halt_log, trade_history) + Parquet (OHLCV); zero-copy read path для backtest |
| **risk-override** | Risk + Runtime | HMAC-signed file + atomic write 0o600. Operator interface consumed by RuntimeManager.tick (RiskManager.assess() reads override на каждый call). Pattern shared с kill-switch S8b T4. |
| **execution-state-machine** | Execution + Resilience | TRANSITIONS table includes RECONCILE_*+ HEAL_ENTRY_FILLED events from Resilience |
| **kill-switch-cli** | Runtime + Tooling | Operator entry-point (sentinel-file pattern identical к hooks); RuntimeManager polls sentinel each tick |
| **models** | Signal + Execution | pydantic Bar/Signal/Order/Fill — defined в C2, consumed by C4 (Order/Fill in execution path) |

## Операторские runbooks

Runbooks — не компоненты, а процедуры реагирования на инциденты. Перечислены здесь для обнаруживаемости.

| Runbook | Что покрывает |
|---------|--------------|
| [[../runbooks/halt-recovery]] | 19 halt-кодов (5 групп, 2 уровня severity). CRITICAL = полная диагностика (SQL + REST cross-check + recovery). RECOVERABLE = сокращённая (симптомы + действия + эскалация). Первый источник для production-инцидентов. |

**Кластер halt recovery:** `halt-recovery.md` охватывает Кластер 3 (Risk/circuit-breakers), Кластер 4 (Execution/OCO/coordinator), Кластер 5 (Resilience/reconciler), Кластер 6 (Runtime/RuntimeManager). Ни один кластер не является единственным владельцем — использовать runbook напрямую.

## Предупреждения о когезии кластеров (анти-паттерны)

- **Не спрашивать Coordinator о Strategy logic.** Coordinator orchestrates FSM/bracket; Strategy живёт в Кластере 2 (signal computation).
- **Не grep'ать "halt" в Strategy cluster.** Halt mechanics = Кластер 4 (Coordinator) + Кластер 3 (risk-override). Strategy не halts — RiskManager отклоняет сигналы при halt.
- **Не читать backtest cluster для вопросов live runtime.** Backtest = S2-era reference, не active dev pipeline.
- **Не искать определения моделей Order/Fill в Кластере 4.** Domain models живут в Кластере 2 (`models.md` — pydantic Bar/Signal/Order/Fill). Кластер 4 импортирует их.
- **Не искать "REST" только в Кластере 1.** `bybit-rest` — Bridge (C1 Market Data + C4 Execution). BybitAdapter в C4 оборачивает его для ордеров.

## Правило поддержки

**Обновлять эту страницу когда:**
- Создана новая страница компонента → назначить кластер (или создать новый кластер при новом домене)
- Scope компонента расширяется на несколько кластеров → добавить в "Bridge components"
- Кластер имеет > 6 компонентов → рассмотреть разделение

## Связанное

- [[../mental-map|mental-map.md]] — query → canonical-path lookup (прямое направление)
- [[../../index|index.md]] — плоский алфавитный каталог
- [[../architecture/current-state|current-state.md]] — канонические счётчики + история спринтов
- [[../architecture/bounded-contexts|bounded-contexts.md]] — DDD bounded contexts (5 contexts: MarketData/SignalGen/Risk/Execution/Analytics)
