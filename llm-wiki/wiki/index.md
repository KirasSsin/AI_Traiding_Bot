---
title: Wiki Index — каталог всех страниц
type: summary
tags: [index, navigation, catalog]
created: 2026-04-19
updated: 2026-04-25
status: stable
---

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
- [[trading/concepts/reason-codes]] — 42 enum-кодов (6 entry + 11 scale/exit + 9 rejects + 16 halts); S7 +3 (HALT_BOOTSTRAP_AMBIGUOUS / HALT_EXIT_RECONCILE_DIVERGENCE / EXIT_RECONCILE_DETECTED).
- [[trading/concepts/look-ahead-bias]] — 5 канонических форм, 6 invariants, CI gate detector, property tests.

## Project — Architecture

- [[project/architecture/overview]] — MVP v0.1 target: стек, roadmap, риски, acceptance.
- [[project/architecture/current-state]] — инвентаризация текущего кода (Bybit futures 1m, pandas .ewm(), in-memory).
- [[project/architecture/gap-analysis]] — 24 расхождения current vs MVP v0.1 с приоритетами P0/P1/P2.
- [[project/architecture/migration-plan]] — 10 спринтов, 3-4 месяца, local-first; Docker/deploy → v0.2.
- [[project/architecture/development-workflow]] — Superpowers pipeline (7 скиллов) маппится на 10 спринтов v0.1.

## Project — Sprints

- [[project/sprints/README|sprints/ README]] — назначение директории + шаблон sprint-page.
- [[project/sprints/sprint-01-foundation]] — S1 (2026-04-20): DDD skeleton + platform + models + storage; tag `v0.1.0-alpha.1`.
- [[project/sprints/sprint-02-bybit-venue-migration]] — S2 (2026-04-21 → 22): Bybit venue migration + MarketData ingest + BybitMarketAdapter; tag `v0.1.0-alpha.2`, PR #1.
- [[project/sprints/sprint-03-strategy-port]] — S3 (2026-04-22): EMA crossover + ADX/RSI/ATR через TA-Lib, on_bar контракт, FLAT/LONG FSM; tag `v0.1.0-alpha.3`.
- [[project/sprints/sprint-04-risk]] — S4 (2026-04-23): RiskManager (4-phase Kelly + Wilson 95% CI + L1/L2/L3/flash CB + override + 50-bar integration); tag skipped — merged into v0.1.0-alpha.6.
- [[project/sprints/sprint-05-execution]] — S5 (2026-04-23): OCO native tpslMode + 12-state FSM + Reconciler (reconcile-as-truth) + 2 reason codes (29→31); tag skipped — merged into v0.1.0-alpha.6.
- [[project/sprints/sprint-06-spot-oco-emulation]] — S6 (2026-04-23): 3-order Spot OCO emulation; FSM 12→16 states / 55 transitions; reason codes 31→39; tag v0.1.0-alpha.6 (consolidates S4+S5+S6).
- [[project/sprints/sprint-07-resilience]] — S7 (2026-04-24): bootstrap reconcile + WS-reconnect wiring + 4-valued verdicts + γ halt persistence + ws_private consumer; FSM 16/29/59 (dedup); reason codes 39→42; tag v0.1.0-alpha.7.
- [[project/sprints/sprint-08a-live-runtime]] — S8a (2026-04-24): RuntimeManager (bootstrap → tick loop → shutdown) + REST bar poller + KILL_SWITCH sentinel-file CLI + threading lock policy; FSM +11 KILL_SWITCH_REQUESTED transitions (59→70); reason codes 42→45; tag v0.1.0-alpha.8a.
- [[project/sprints/sprint-08b-carryover]] — S8b (2026-04-24): S8a carry-over fixes (request_halt FSM dispatch + BarSource validator + atomic kill write + main() typed dispatch) + ADR 0023 halt-code mapping invariant + property test; FSM 70→74 (T1 +3 RISK_HALT, T7 +1 FLAT,RISK_HALT); tag v0.1.0-alpha.8b.
- [[project/sprints/sprint-08c-wiki-backfill]] — S8c (2026-04-25): wiki backfill + tooling debt + S8a/S8b carry-overs. 12 tasks, 4 new component pages (backtest-harness, kill-switch-cli, risk-override, trade-history) + 3 file deletions (oco.py + 2 tests per ADR 0019/1 supersession) + trace map mandatory + adr-index-sync hook. PHASE 2 binding protocol caught DELETE bracket.py catastrophic regression. Tag v0.1.0-alpha.8c.
- [[project/sprints/sprint-09-data-quality-types-analytics]] — S9 (2026-04-25): data quality detector (REST-vs-REST → HALT_DATA_QUALITY) + mypy --strict full enable (override removal + 18 fixes) + per-fill schema (trade_fills + WS execution topic) + DSR module (Bailey & López de Prado, Pearson kurtosis). 12 TDD tasks, +32 tests (589→621 unit). FSM/counts unchanged. Tag v0.1.0-alpha.9.
- [[project/sprints/sprint-10-wfa-dsr-mc]] — S10 (2026-04-25): WFA orchestrator (WindowSplitter + WalkForwardRunner + acceptance gate per ADR 0014) + DSR sigma_sr extension (closes S9 NYI) + MC sign-flip + block bootstrap (ADR 0015) + 3-Sharpe routing + vector_backtest annualization fix. 11 TDD tasks, +26 tests (630→656 unit + 1 integration). FSM/counts unchanged. Tag v0.1.0-alpha.10.
- [[project/sprints/sprint-11-operator-readiness]] — S11 (2026-04-25): Pre-flight gap closure (test_risk_flow.py + `_cmd_run`/`_cmd_reconcile_only`/`_cmd_wfa`/`_cmd_monitor` CLI subcommands closing S8a T20 STUB) + operator-readiness (halt-recovery priority matrix integration + log-grep-templates runbook + pre-flight checklist). 10 TDD tasks, +10 tests (656→666 unit). FSM/counts unchanged. Tag v0.1.0-alpha.11.

## Project — Plans

- [[project/plans/2026-04-20-sprint-1-foundation]] — implementation plan Sprint 1 (storage + pydantic v2 + cleanup).
- [[project/plans/2026-04-21-sprint-2-bybit-venue-migration]] — implementation plan Sprint 2 (pybit migration + MarketData + Execution ACL).
- [[project/plans/2026-04-22-sprint-3-strategy-port]] — implementation plan Sprint 3 (TA-Lib indicators + EmaCrossoverAdxRsiStrategy + look-ahead property test).
- [[project/plans/2026-04-23-sprint-4-risk]] — implementation plan Sprint 4 (Risk module — split into tasks-1-8 / 9-13 / 14-17).
- [[project/plans/2026-04-23-sprint-5-execution]] — implementation plan Sprint 5 (OCO + 12-state FSM + Reconciler + testnet integration).
- [[project/plans/2026-04-23-sprint-6-spot-oco-emulation]] — implementation plan Sprint 6 (3-order Spot OCO emulation + bracket builder + reconcile-as-truth refactor).
- [[project/plans/2026-04-24-sprint-7-resilience]] — implementation plan Sprint 7 (bootstrap reconcile + 4-valued verdicts + γ halt persistence + ws_private close-hook).
- [[project/plans/2026-04-24-sprint-8a-live-runtime]] — implementation plan Sprint 8a (RuntimeManager + REST bar poller + KILL_SWITCH + threading lock policy + entry-point).
- [[project/plans/2026-04-24-sprint-8b-carryover]] — implementation plan Sprint 8b (S8a carry-over fixes + ADR 0023 halt-code mapping invariant).
- [[project/plans/2026-04-25-sprint-8c-wiki-backfill]] — implementation plan Sprint 8c (wiki backfill + tooling debt + S8a/S8b carry-overs).

## Project — Runbooks

- [[project/runbooks/halt-recovery]] — operator manual для 19 halt codes (5 class groups, 2 severity tiers — CRITICAL full diagnosis vs RECOVERABLE abbreviated) + S11 priority matrix (P0/P1/P2 escalation chain integrated INTO single source of truth per Q3 REVISE). Per Bucket F1 (S8c PR-γ) trader-expert ROUND 1+2 binding verdicts. Covers: Drawdown (4), Operational (4), OCO/bracket (6), Bootstrap/reconcile (3), Runtime (2).
- [[project/runbooks/log-grep-templates]] — operator log filtering recipes (structlog jq filters + halt_log SQL queries). S11 A scope T6.
- [[project/runbooks/pre-flight]] — operator pre-flight checklist (5 critical gates + 4 recommendations + post-start monitoring + halt response). Mandatory before `python -m src run` on Mainnet/demo. S11 A scope T8.

## Project — Workflow Skills (`.claude/skills/`)

Project-level skills заменяют hardcoded inline workflow logic (per Anthropic progressive disclosure pattern). Auto-trigger по description match, не нужен manual invoke.

- **`.claude/skills/sprint-orient/SKILL.md`** — PHASE 1 orient sequence (SPRINT_STATE + git verify + log tail + canonical counts + chapter mark). Auto-trigger: session start, `/clear`, "где мы", "ориентируйся".
- **`.claude/skills/sprint-finish/SKILL.md`** — PHASE 8 finishing HARD-GATE checklist (sprint-NN.md mandatory + canonical counts sync + orphan-audit grep tests/ + index.md ADR sync). Auto-trigger: "ship", "финишируем", subagent-driven completion.
- **`.claude/skills/wiki-update/SKILL.md`** — code → docs sync after src/ change (dependency graph walk + Block 1↔Block 2 + canonical counts verify). Auto-trigger: после src/ edit.
- **`.claude/skills/brainstorm-init/SKILL.md`** — PHASE 2 binding protocol (structured questionnaire → trader-expert ROUND 1 → iterative justify ROUND 2 на REVISE-disagreement → CONFIRM_REVISE/CHANGED BINDING). Auto-trigger: scope/architecture questions, "брейнштурм".
- **`.claude/skills/hook-test/SKILL.md`** (`disable-model-invocation: true`) — sandboxed PreToolUse hook test через env -i isolation. Explicit `/hook-test` invocation only.
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

- [[project/components/config]] — `Settings` (pydantic-settings v2): env/.env, Bybit creds, trading_enabled/live_trading invariant, paths.
- [[project/components/logging]] — structlog JSON pipeline → stdout, обязательные ключи event/level/timestamp, contextvars.
- [[project/components/models]] — pydantic v2 domain models: Bar / Signal / Order / Fill с инвариантами (OHLC, look-ahead, executed_qty ≤ orig_qty).
- [[project/components/storage]] — SQLite WAL (OLTP, 8 таблиц + migrations runner) + Parquet snappy writer (OLAP).
- [[project/components/backtest-harness]] — backtest pipeline: replay engine + vector backtest + reporter + indicators + data collector. S2-era reference, S9+ DSR/MC/WFA deferred.
- [[project/components/bybit-rest]] — BybitRESTClient (pybit V5 HTTP wrapper): server_time, instruments_info, paginated klines.
- [[project/components/bybit-ws]] — BybitWSConsumer: pybit WebSocket callback → asyncio iteration мост.
- [[project/components/bar-builder]] — venue-agnostic aggregator: confirm-gate + dedup + out-of-order + gap synthesis.
- [[project/components/bybit-adapter]] — MARKET spot execution: filter-validate + place_order + retCode→ReasonCode.
- [[project/components/indicators]] — TA-Lib wrappers: EMA classical/wilder + ADX/±DI/RSI/ATR Wilder.
- [[project/components/strategy]] — EmaCrossoverAdxRsiStrategy: on_bar(Bar) → Signal | None, FLAT/LONG FSM.
- [[project/components/kelly]] — 4-phase Kelly + Wilson 95% CI; pure functions, KellyCaps from Settings.
- [[project/components/kill-switch-cli]] — operator-facing CLI: kill (sentinel-file atomic write) + run + backfill + reconcile-only. ADR 0022 sub-decisions 5+9 + ADR 0023 dispatch invariant.
- [[project/components/circuit-breakers]] — L1/L2/L3/Flash detector (stateless); CircuitBreakerConfig from Settings.
- [[project/components/sizing]] — `compute_qty(equity, fraction, atr, price, k)` ATR-based pure function.
- [[project/components/risk-manager]] — orchestrator: assess(signal, mark_price) → RiskAssessment с look-ahead invariant.
- [[project/components/risk-override]] — manual CB resume gate (HMAC-SHA256 signed JSON file + config_hash anti-replay + atomic write 0o600). ADR 0018.
- [[project/components/trade-history]] — per-trade audit log (TradeRecord + TradeHistoryRepository + UNIQUE INDEX uq_trade_history_entry_signal + AwareDatetime). Kelly trade-count source (ADR 0012). ADR 0018.
- [[project/components/adr-agent-sync-hook]] — PreToolUse hook на git push: блокирует пуш при drift'е ADR vs agent prompts.
- [[project/components/adr-index-sync-hook]] — PreToolUse git push hook: блокирует пуш если новый ADR не упомянут в `wiki/index.md`. Mirror of adr-agent-sync-check (Bucket C6).
- [[project/components/wiki-broken-link-hook]] — PreToolUse git push hook: блокирует пуш если changed wiki files содержат broken `[[link]]` refs (Bucket C7, pre-S9).
- [[project/components/data-quality]] — REST-vs-REST consecutive bar deviation detector → HALT_DATA_QUALITY (S9 Q1). 0.5% threshold, per-bar cadence, no WS kline subscription needed.
- [[project/components/fill-history]] — per-fill audit log (FillRecord + FillHistoryRepository + FK trade_history + WS execution topic source) (S9 Q3 B1).
- [[project/components/dsr]] — Bailey & López de Prado Deflated Sharpe Ratio module (Pearson kurtosis). S9 Q3 B2 + S10 sigma_sr extension (Bailey eq. 12, n_trials > 1 supported).
- [[project/components/walk-forward]] — WFA orchestrator (WindowSplitter + WalkForwardRunner + acceptance gate). Rolling K=5 per ADR 0014 (S10).
- [[project/components/mc-permutations]] — sign-flip primary + block bootstrap secondary. N=2000 per ADR 0015 (S10).
- [[project/components/wfa-reporter]] — 3-Sharpe series routing + DSR aggregate informational. Fixed sqrt(8760) annualization (S10).
- [[project/components/oco]] — 3-order Spot OCO emulation: bracket builder + orderLinkId scheme + G5 fee-aware qty + S7 entry_order_id capture для HEAL.
- [[project/components/reconciler]] — 4-valued verdict (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED) + heal_max_age_seconds=3600.
- [[project/components/execution-state-machine]] — 16-state FSM + 29 events + 59 transitions + γ halt persistence (S7).
- [[project/components/ws-private-consumer]] — Bybit V5 private WS (order + wallet) с pybit close-hook + check_alive watchdog (S7 ADR 0021 sub-decision 6).
- [[project/components/runtime-manager]] — RuntimeManager: process lifecycle owner (bootstrap → loop → shutdown). S8a.
- [[project/components/bar-poller]] — BarSource: REST kline poller с dedup + stall counter. S8a.
- [[project/runbooks/halt-recovery]] — see Runbooks section above (19 halt codes, 5 class groups, 2 severity tiers — CRITICAL/RECOVERABLE).

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
- [[project/decisions/0016-bybit-spot-supersedes-binance]] — Bybit Spot supersedes 0004; pybit>=5.11; V5 Unified endpoint map.
- [[project/decisions/0017-review-agent-harness]] — 3 доменных ревьюера (trading-logic / quant-stats / data-integrity) + python-reviewer; non-overlapping scope, MUST-BE-USED триггеры.
- [[project/decisions/0018-sprint-4-risk-decisions]] — Sprint 4 sub-decisions: R:R 2:1, REJECT_INVALID_SIGNAL/ZERO_QTY не распаковываются, Wilson lower bound для phases 3/4, L0 explicit naming, reason-codes count fix (28→29).
- [[project/decisions/0019-sprint-5-execution-decisions]] — Sprint 5: native Bybit `tpslMode` for OCO (sub-decision 1 SUPERSEDED by 0020), 12-state FSM, reconcile-as-truth, +2 reason codes (29→31), testnet happy-path scope.
- [[project/decisions/0020-sprint-6-execution-spot-oco-emulation]] — Sprint 6: 3-order Spot OCO emulation (reverses 0019/1), bracket_id schema v2, FSM 12→21, reason codes 31→39, fee-aware sizing (G5), client-side sibling cancel-on-Triggered, IOC override + EXIT_SL_RESIDUAL — backed by 14/14 empirical probes on Bybit Demo.
- [[project/decisions/0021-sprint-7-resilience]] — Sprint 7: 9 sub-decisions (bootstrap reconcile + 4-valued reconciler + WS-reconnect wiring + heal_max_age=3600s + γ halt persistence + halt_log audit + ws_private close-hook); FSM 16/29/59; reason codes 39→42; B1 narrow scope (passive consumer).
- [[project/decisions/0022-sprint-8a-live-runtime]] — Sprint 8a: 14 sub-decisions (RuntimeManager lifecycle + REST bar poller + KILL_SWITCH sentinel-file CLI + threading lock policy на Coordinator/Reconciler + entry-point `python -m src` + orphan removal); FSM +11 KILL_SWITCH_REQUESTED transitions; reason codes 42→45.
- [[project/decisions/0023-halt-code-fsm-event-mapping]] — Sprint 8b ADR. Halt-class ReasonCode dispatch invariant in Coordinator.request_halt + 3-layer enforcement (ADR + reviewer prompt + property test).
- [[project/decisions/0024-sprint-9-data-quality-types-analytics]] — Sprint 9 aggregate ADR: Data quality detector (REST-vs-REST + HALT_DATA_QUALITY) + mypy strict full enable (override removal + 18 fixes) + per-fill schema (trade_fills table + WS execution topic) + DSR module (Bailey & López de Prado, Pearson kurtosis).
- [[project/decisions/0025-sprint-10-wfa-dsr-mc]] — Sprint 10 aggregate ADR: WFA orchestrator (rolling K=5 per ADR 0014) + DSR sigma_sr extension (closes S9 NYI, Bailey eq. 12) + MC sign-flip + block bootstrap (ADR 0015) + 3-Sharpe series routing + vector_backtest annualization fix.
- [[project/decisions/0026-sprint-11-operator-readiness]] — Sprint 11 aggregate ADR: Pre-flight gap closure (test_risk_flow.py + _cmd_run + _cmd_reconcile_only + _cmd_wfa CLI, closes S8a T20 STUB) + operator-readiness (halt priority matrix integration + log-grep-templates + _cmd_monitor read-only + pre-flight checklist).

## Queries (saved answers)

_(пусто)_
