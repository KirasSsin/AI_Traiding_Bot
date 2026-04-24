---
title: Components — domain cluster index
type: navigation
tags: [navigation, components, clusters, llm-friendly]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - project/mental-map.md
  - index.md
---

# Components — domain cluster index

> **For LLM agents:** этот файл = topic-grouped reverse lookup ("I'm reading X — what's related?"). Complementary к flat `index.md` alphabetic list. Use если читаешь one component и need related context.

**TL;DR:** 27 component pages grouped по 9 domain clusters (Market Data + Signal + Risk + Execution + Resilience + Runtime + Infrastructure + Backtest + Tooling). Each cluster has anchor (primary component) + supporting components. Cross-cluster relationships в "Bridge components" section.

## Cluster 1 — Market Data ingest

**Theme:** OHLCV pipeline (REST seed + WS live + bar building + storage). Sprint origin: S2 (ADR 0016).

| Component | Role |
|-----------|------|
| **[[bybit-rest]]** | pybit V5 HTTP wrapper — server_time, instruments_info, paginated klines |
| [[bybit-ws]] | pybit WebSocket callback → asyncio iteration мост (S2 legacy, replaced by ws-private-consumer for execution) |
| [[bar-builder]] | venue-agnostic aggregator — confirm-gate + dedup + out-of-order + gap synthesis |
| [[bar-poller]] | REST kline 5s cadence + stall detection (S8a) |

**Bridge to:** Storage (writes Parquet) → Strategy (consumer)

## Cluster 2 — Signal generation

**Theme:** Strategy + indicators (look-ahead-free, signal on close(T) → fill open(T+1)). Sprint origin: S3 (ADR 0011, 0017).

| Component | Role |
|-----------|------|
| **[[strategy]]** | EmaCrossoverAdxRsiStrategy — `on_bar(Bar) → Signal \| None`, FLAT/LONG FSM |
| [[indicators]] | TA-Lib wrappers — EMA classical/Wilder + ADX/±DI/RSI/ATR Wilder |
| [[models]] | pydantic v2 domain models — Bar/Signal/Order/Fill с look-ahead invariants |

**Bridge to:** Risk (Signal → assess) → Execution (start_bracket)

## Cluster 3 — Risk + sizing

**Theme:** 4-phase Kelly + Wilson 95% CI + L1/L2/L3/flash CB + manual override. Sprint origin: S4 (ADR 0012, 0013, 0018).

| Component | Role |
|-----------|------|
| **[[risk-manager]]** | orchestrator — `assess(signal, mark_price) → RiskAssessment` с look-ahead invariant |
| [[kelly]] | 4-phase Kelly + Wilson 95% CI; pure functions, KellyCaps from Settings |
| [[circuit-breakers]] | L1/L2/L3/Flash detector (stateless); CircuitBreakerConfig from Settings |
| [[sizing]] | `compute_qty(equity, fraction, atr, price, k)` ATR-based pure function |
| [[risk-override]] | Manual CB resume gate — HMAC-SHA256 signed JSON + config_hash anti-replay + atomic write 0o600 |
| [[trade-history]] | Per-trade audit log — TradeRecord + TradeHistoryRepository + UNIQUE INDEX entry_signal_id (Kelly trade-count source) |

**Bridge to:** Execution (approved Signal → Coordinator.start_bracket)

## Cluster 4 — Execution + OCO

**Theme:** 3-order Spot OCO emulation + 16-state Harel FSM + bracket lifecycle. Sprint origin: S5/S6 (ADR 0019, 0020).

| Component | Role |
|-----------|------|
| **[[coordinator]]** | Central orchestrator — FSM dispatch (`_transition`) + bracket lifecycle (`start_bracket`/`arm_oco`/`flatten`) + halt mechanics (`request_halt`) + reconcile delegation. 8 RLock-protected methods. |
| [[execution-state-machine]] | 16 states / 30 events / 74 transitions table-driven `TRANSITIONS` + `IllegalTransitionError` |
| [[oco]] | 3-order bracket (Entry Market + TP Limit + SL StopMarket IOC) + builder (`compute_oco_qty`, `make_order_link_id`) |
| [[bybit-adapter]] | MARKET/Limit/StopMarket spot execution + 6 methods + filter-validate + retCode→ReasonCode + banned-field guard |

**Bridge to:** Resilience (Reconciler ↔ Coordinator), Runtime (RuntimeManager owns Coordinator lifecycle)

## Cluster 5 — Resilience (S7)

**Theme:** Bootstrap reconcile + 4-valued verdicts + γ halt persistence + WS reconnect. Sprint origin: S7 (ADR 0021).

| Component | Role |
|-----------|------|
| **[[reconciler]]** | 4-valued verdict producer (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED). walletBalance-as-truth для Spot. |
| [[ws-private-consumer]] | pybit WebSocket close-hook + check_alive watchdog. Routes order/wallet events → Coordinator/Reconciler. |

**Bridge to:** Execution (Reconciler called from Coordinator.bootstrap + on_ws_reconnect), Runtime (WS consumer started by RuntimeManager)

## Cluster 6 — Runtime (S8a) — live process

**Theme:** Process lifecycle owner (bootstrap → tick loop → graceful shutdown). Sprint origin: S8a (ADR 0022).

| Component | Role |
|-----------|------|
| **[[runtime-manager]]** | Owns process lifecycle. Tick pipeline: `_maybe_kill_switch` → `_check_alive_inline` → `_poll_bar_and_strategy` → `_poll_or_arm_oco`. |
| [[bar-poller]] | REST kline 5s cadence + stall detection (cross-listed with Cluster 1) |
| [[kill-switch-cli]] | Operator-facing CLI (`python -m src run/backfill/reconcile-only/kill`) + sentinel-file atomic write semantics |

**Bridge to:** Execution (RuntimeManager → Coordinator), Resilience (RuntimeManager → WS consumer)

## Cluster 7 — Infrastructure

**Theme:** Cross-cutting platform — config, logging, storage. Sprint origin: S1.

| Component | Role |
|-----------|------|
| **[[config]]** | Settings (pydantic-settings v2) — env/.env, Bybit creds, trading_enabled/live_trading invariant, paths |
| [[logging]] | structlog JSON pipeline → stdout, обязательные ключи event/level/timestamp, contextvars |
| [[storage]] | SQLite WAL (OLTP, 8 tables + migrations runner) + Parquet snappy writer (OLAP) |

**Bridge to:** ALL clusters (everyone uses Settings + structlog + storage)

## Cluster 8 — Backtest + analytics (S2-era reference)

**Theme:** Backtest pipeline — replay engine + vector backtest + reporter. **Status: not actively developed S3-S8b. DSR/MC/WFA deferred к S9+.**

| Component | Role |
|-----------|------|
| **[[backtest-harness]]** | Single page covering 6 src/backtest files (replay_engine + vector_backtest + reporter + indicators + data_collector + replay-stub) |

## Cluster 9 — Tooling / hooks

**Theme:** PreToolUse `git push` hooks enforcing wiki invariants. Sprint origin: S7 (adr-agent-sync) + S8c T11 (adr-index-sync).

| Component | Role |
|-----------|------|
| [[adr-agent-sync-hook]] | Block push если ADR changed но `~/.claude/agents/*.md` mtime not advanced (per ADR 0017) |
| [[adr-index-sync-hook]] | Block push если new ADR не referenced в `wiki/index.md` |

## Bridge components (multi-cluster owners)

These components span clusters — keep aware of cross-cluster impacts:

| Component | Clusters bridged | Why |
|-----------|------------------|-----|
| **coordinator** | Execution + Resilience + Runtime | FSM owner + reconcile delegate + halt API consumed by RuntimeManager |
| **reconciler** | Resilience + Execution | 4-valued verdict producer; called from Coordinator |
| **bar-poller** | Market Data + Runtime | REST kline source + RuntimeManager tick consumer |
| **bybit-rest** | Market Data + Execution | HTTP V5 client shared для kline seeding (C1) и order execution через BybitAdapter (C4) |
| **storage** | Infrastructure + ALL clusters | SQLite WAL (execution_state, halt_log, trade_history) + Parquet (OHLCV); zero-copy read path для backtest |
| **risk-override** | Risk + Runtime | HMAC-signed file + atomic write 0o600. Operator interface consumed by RuntimeManager.tick (RiskManager.assess() reads override на каждый call). Pattern shared с kill-switch S8b T4. |
| **execution-state-machine** | Execution + Resilience | TRANSITIONS table includes RECONCILE_*+ HEAL_ENTRY_FILLED events from Resilience |
| **kill-switch-cli** | Runtime + Tooling | Operator entry-point (sentinel-file pattern identical к hooks); RuntimeManager polls sentinel each tick |
| **models** | Signal + Execution | pydantic Bar/Signal/Order/Fill — defined в C2, consumed by C4 (Order/Fill in execution path) |

## Cluster cohesion warnings (anti-patterns)

- **Don't ask Coordinator about Strategy logic.** Coordinator orchestrates FSM/bracket; Strategy lives в Cluster 2 (signal computation).
- **Don't grep "halt" в Strategy cluster.** Halt mechanics = Cluster 4 (Coordinator) + Cluster 3 (risk-override). Strategy doesn't halt — RiskManager rejects signals при halt.
- **Don't read backtest cluster для live runtime questions.** Backtest = S2-era reference, не active dev pipeline.
- **Don't look for Order/Fill model definitions в Cluster 4.** Domain models live в Cluster 2 (`models.md` — pydantic Bar/Signal/Order/Fill). Cluster 4 imports them.
- **Don't search "REST" exclusively в Cluster 1.** `bybit-rest` is Bridge (C1 Market Data + C4 Execution). BybitAdapter в C4 wraps it for orders.

## Maintenance rule

**Update этой странице when:**
- New component page created → assign к cluster (or create new cluster если новый домен)
- Component scope expands cross-cluster → add к "Bridge components"
- Cluster gets > 6 components → consider splitting

## Related

- [[../mental-map|mental-map.md]] — query → canonical-path lookup (forward direction)
- [[../../index|index.md]] — flat alphabetic catalog
- [[../architecture/current-state|current-state.md]] — canonical counts + sprint history
- [[../architecture/bounded-contexts|bounded-contexts.md]] — DDD bounded contexts (5 contexts: MarketData/SignalGen/Risk/Execution/Analytics)
