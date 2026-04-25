---
title: Mental map — "where to look for X" decision tree
type: navigation
tags: [navigation, mental-map, rag, discovery, llm-friendly]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - project/SPRINT_STATE.md
  - project/architecture/current-state.md
  - index.md
---

# Mental map — where to look for X

> **For LLM agents:** этот файл = first-hit для open-ended queries ("how does X work / where is Y / who owns Z"). Скажет какой wiki path читать вместо blind grep'а. Updated whenever new component / ADR / sprint added.

**TL;DR:** decision tree mapping common queries → canonical wiki paths. Saves tokens on first-time orientation. Prefer this over `Glob "**/*.md"` + `Grep` blind sweeps.

## Quick lookup table

| Query / Topic | Canonical source(s) | Order to read |
|---------------|---------------------|---------------|
| Current sprint / phase / state | `project/SPRINT_STATE.md` | 1 |
| Live counts (FSM states/events/transitions, reason codes, components) | `project/architecture/current-state.md` (canonical-counts table) | 1 |
| Last N events chronologically | `wiki/log.md` (use `tail -100` — file 51KB банен) | 1 |
| Sprint summary "что было в спринте N" | `project/sprints/sprint-NN-<slug>.md` | 1 |
| Sprint plan (bite-sized tasks + trace map) | `project/plans/YYYY-MM-DD-sprint-N-<slug>.md` (S6/S7/S8a/S2 plans банены — use Grep/offset Read) | 2 |
| ADR (architecture decision) | `project/decisions/NNNN-<slug>.md` + `index.md` "## Project — Decisions" | 2 |
| Methodology / sprint workflow / PHASE definitions | `project/architecture/development-workflow.md` (master SOP, 9 phases) | 1 |
| Wiki maintainer rules + 5-layer skills hierarchy | `llm-wiki/CLAUDE.md` (root, not inside wiki/) | 1 |
| Repo conventions + Python venv discipline + brainstorming protocol | `CLAUDE.md` (repo root) | 1 |
| Pre-sprint backlog (gaps + bugs to discharge) | `wiki/project/pre-s{N}-backlog.md` (если exists) | 2 |

## Domain-specific lookup

### FSM / state machine

| Query | Path | Notes |
|-------|------|-------|
| Current FSM state count + growth history | `components/execution-state-machine.md` TL;DR | live counts via `.venv/bin/python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"` |
| FSM dispatch logic (who calls `_transition`) | `components/coordinator.md` "FSM dispatch invariant" + `_transition` source | |
| KILL_SWITCH_REQUESTED transitions invariant | `decisions/0023-halt-code-fsm-event-mapping.md` (invariant) + `decisions/0022-sprint-8a-live-runtime.md` (event introduction) | ADR 0023 primary source |
| (FLAT, RISK_HALT) → HALTED edge case | `sprints/sprint-08b-carryover.md` T7 + `decisions/0023` | property test caught regression |
| Harel statechart design | `architecture/state-machine.md` (high-level) | pre-S5 design doc, FSM grew since |

### Operator procedures / incident response

| Query | Path | Notes |
|-------|------|-------|
| Halt recovery (how to resume from any halt code) | `project/runbooks/halt-recovery.md` (19 halt codes, 5 class groups, 2 severity tiers) | First-hit для production incident response |
| CRITICAL vs RECOVERABLE halt classification | `project/runbooks/halt-recovery.md` "CRITICAL definition" callout | CRITICAL = "incorrect manual recovery can create or conceal an open position" |
| SQL reset template (execution_state to FLAT) | `project/runbooks/halt-recovery.md` "Common SQL templates" | S7 schema с halt_reason + halt_log |
| Halt priority matrix (P0/P1/P2 escalation chain) | `project/runbooks/halt-recovery.md` "Priority matrix" section + Quick Reference Table "On-call escalation" column | S11 T5 (Q3 REVISE — single source of truth, NOT separate dashboard) |
| Pre-flight operator checklist (before `python -m src run`) | `project/runbooks/pre-flight.md` (5 critical gates + 4 recommendations + post-start monitoring + halt response) | S11 T8 — mandatory before Mainnet/demo start |
| Log filtering recipes (structlog jq + halt_log SQL) | `project/runbooks/log-grep-templates.md` | S11 T6 — operator filter templates (errors-only / per-bracket / halt history / fill audit) |
| Live demo validation 48h playbook | `project/runbooks/live-demo-validation.md` | S12 T4 — entry gates + monitoring + multi-criteria success gate с MANDATORY zero-trade clause |
| P0 halt response + rollback procedure | `project/runbooks/halt-response-protocol.md` | S12 T5 — P0 wake decision tree + alpha.11 rollback (Q7 zero-migration safe) + RC tag iteration |
| Read-only state snapshot CLI (`python -m src monitor`) | `components/kill-switch-cli.md` "_cmd_monitor" + `src/__main__.py::_cmd_monitor` | S11 T7, C2 invariant: SQLite `?mode=ro` URI, no DB mtime change. Test enforces. |
| WFA CLI subcommand (`python -m src wfa`) | `components/walk-forward.md` + `src/__main__.py::_cmd_wfa` | S11 T4 — WFA orchestrator + MC + acceptance gate exposure. NOTE `_load_ohlcv` stub (S12 integrates real data) |

### Halt mechanics / circuit breakers

| Query | Path |
|-------|------|
| Halt mechanics (γ persistence, primary-wins) | `components/coordinator.md` "γ Halt persistence" + `decisions/0021-sprint-7-resilience.md` sub-decisions 5+9 |
| `request_halt(reason: ReasonCode)` API | `components/coordinator.md` "request_halt" |
| Halt codes exempt from HALTED→event guard (KILL_SWITCH_REQUESTED + HALT_RUNTIME_CRASH + HALT_BAR_POLL_STALL) | `components/coordinator.md` "Allow-list contract" + `decisions/0023` |
| `HALT_BAR_POLL_STALL` semantics + threshold (24 consecutive failures) | `components/bar-poller.md` "Stall detection" + `decisions/0022` G3 |
| `halt_log` audit table (γ persistence write-ahead) | `decisions/0021` sub-decision 5 + `migrations/0005_halt_persistence.sql` |
| Manual CB resume (HMAC-signed override) | `components/risk-override.md` |
| Kill-switch CLI (`python -m src kill`) | `components/kill-switch-cli.md` |
| L1/L2/L3/flash circuit breakers | `components/circuit-breakers.md` + `decisions/0013` + `trading/concepts/circuit-breakers.md` |

### Reconcile / bootstrap

| Query | Path |
|-------|------|
| 4-valued verdict (AGREE/HEAL_ENTRY_FILLED/EXITED/DIVERGENCE) | `components/reconciler.md` |
| Bootstrap sequencing invariant | `components/coordinator.md` "Bootstrap sequencing" + `decisions/0021` sub-decision 1 |
| WS reconnect path | `components/coordinator.md` `on_ws_reconnect` + `components/ws-private-consumer.md` |
| `heal_max_age=3600s` rationale | `decisions/0021` sub-decision 4 |

### Risk / Kelly / sizing

| Query | Path |
|-------|------|
| 4-phase Kelly + Wilson 95% CI | `components/kelly.md` + `decisions/0012` + `trading/concepts/kelly-phases.md` |
| Position sizing (`compute_qty`) | `components/sizing.md` |
| Trade history (audit log + Kelly trade-count source) | `components/trade-history.md` |
| RiskManager.assess() decision pipeline | `components/risk-manager.md` |
| Reason codes catalog (45 total) | `architecture/reason-codes-schema.md` (canonical list) + `src/risk/reason_codes.py` (live) + `trading/concepts/reason-codes.md` (narrative) |

### Execution / OCO / bracket

| Query | Path |
|-------|------|
| 3-order Spot OCO emulation (Entry Market + TP Limit + SL StopMarket IOC) | `components/oco.md` + `decisions/0020` |
| Bracket builder (`compute_oco_qty`, `make_order_link_id`) | `components/oco.md` "bracket.py — чистое API" section (covers `src/execution/bracket.py`) |
| Bybit V5 adapter (REST + 6 methods) | `components/bybit-adapter.md` + `components/bybit-rest.md` |
| Bybit Spot specifics (no native OCO, IOC override, banned fields) | `decisions/0020` sub-decisions + `components/bybit-adapter.md` |
| WS private consumer (order/wallet events) | `components/ws-private-consumer.md` |

### Runtime / live process

| Query | Path |
|-------|------|
| Process lifecycle (bootstrap → tick loop → shutdown) | `components/runtime-manager.md` |
| Tick pipeline ownership (RuntimeManager → bar_poller → bar_builder → strategy → risk → coordinator) | `components/runtime-manager.md` "Tick pipeline" section |
| Bar poller (REST kline 5s cadence + stall detection) | `components/bar-poller.md` |
| Threading lock policy (RLock 8 methods Coordinator + Lock 2 Reconciler) | `components/coordinator.md` "Threading lock policy" + `decisions/0022` Task 0 |
| Entry-point CLI (`python -m src run/backfill/reconcile-only/kill`) | `components/kill-switch-cli.md` |

### Storage / persistence

| Query | Path |
|-------|------|
| SQLite WAL + Parquet schema | `components/storage.md` + `architecture/storage.md` + `decisions/0003` |
| Migrations (forward-only) | `migrations/*.sql` (ls) + `architecture/storage.md` |
| Execution state row (FSM persisted) | `components/coordinator.md` "State persistence" + `migrations/0003_execution_state.sql` + `migrations/0004_execution_state_v2.sql` + `migrations/0005_halt_persistence.sql` |
| `execution_state` schema columns | same |
| `halt_log` audit table (S7 γ) | `decisions/0021` sub-decision 5 + migration 0005 |

### Strategy / signal generation

| Query | Path |
|-------|------|
| EMA crossover strategy (live S3+) | `components/strategy.md` + `trading/strategies/ema-crossover-adx-rsi.md` |
| Indicators (EMA classical, ADX/RSI/ATR Wilder via TA-Lib) | `components/indicators.md` + `trading/indicators/*.md` (4 files) + `decisions/0011` |
| Signal contract (close(T) → fill open(T+1)) | `architecture/execution-timing.md` + `trading/concepts/look-ahead-bias.md` |

### Backtest

| Query | Path |
|-------|------|
| Replay engine + vector backtest + reporter (6 src files) | `components/backtest-harness.md` |
| WFA (train=2000 / test=500 / K=5 / embargo=20) | `decisions/0014` + `trading/concepts/walk-forward-validation.md` |
| MC permutations (sign-flip N=2000) | `decisions/0015` + `trading/concepts/monte-carlo-permutations.md` |
| DSR (Deflated Sharpe Ratio) | `trading/concepts/deflated-sharpe-ratio.md` (concept; integration deferred к S9+) |

### Tooling / hooks / methodology

| Query | Path |
|-------|------|
| Trace map mandatory PHASE 3 | `architecture/development-workflow.md` PHASE 3 step 1a |
| ADR ↔ Agent prompt sync hook | `components/adr-agent-sync-hook.md` + `~/.claude/hooks/adr-agent-sync-check.sh` |
| ADR ↔ Index sync hook | `components/adr-index-sync-hook.md` + `~/.claude/hooks/adr-index-sync-check.sh` |
| Wiki broken-link sync hook | `components/wiki-broken-link-hook.md` + `~/.claude/hooks/wiki-broken-link-check.sh` (Bucket C7) |
| Bar price quality detector (HALT_DATA_QUALITY) | `components/data-quality.md` + `src/marketdata/quality.py` (S9 Q1, REST-vs-REST) |
| Per-fill audit + WS execution topic | `components/fill-history.md` + `src/risk/fill_history.py` (S9 Q3 B1) |
| FillRecorderAdapter (Bybit V5 WS exec → DB best-effort) | `components/fill-recorder-adapter.md` + `src/risk/fill_recorder_adapter.py` (S12 Q5) — 2-layer pattern (structlog audit + best-effort DB insert via execution_state→trade_history lookup chain). Race-condition safe (skip+warn). S13 carry-over: add `entry_signal_id` к `execution_state` schema. |
| DSR (Deflated Sharpe Ratio, Bailey & López de Prado) | `components/dsr.md` + `src/analytics/dsr.py` (S9 Q3 B2 + S10 sigma_sr extension) |
| Walk-forward analysis (rolling K-folds, OOS/IS Sharpe gate) | `components/walk-forward.md` + `src/backtest/walk_forward.py` (S10 Q1+Q4, ADR 0014+0025) |
| Monte Carlo permutations (sign-flip + block bootstrap) | `components/mc-permutations.md` + `src/backtest/mc_permutation.py` (S10 Q3, ADR 0015) |
| WFA reporter + 3-Sharpe routing | `components/wfa-reporter.md` + `src/backtest/wfa_reporter.py` (S10 Q4+Q6) |
| Orphan-audit grep (включая `tests/`) | `architecture/development-workflow.md` PHASE 8 step 5b |
| Canonical counts sync HARD-GATE | `architecture/development-workflow.md` PHASE 8 step 5a |
| PHASE 2 brainstorming binding protocol (trader-expert ROUND 1+2) | `architecture/development-workflow.md` PHASE 2 step 3 → `.claude/skills/brainstorm-init/SKILL.md` |

### Project-level skills (workflow templates)

| Query | Skill |
|-------|-------|
| "где мы остановились?" / sprint resumption / after `/clear` | `.claude/skills/sprint-orient/SKILL.md` (auto-trigger) |
| "ship sprint" / "финишируем" / PHASE 8 HARD-GATEs | `.claude/skills/sprint-finish/SKILL.md` (auto-trigger) |
| After src/ change → docs sync | `.claude/skills/wiki-update/SKILL.md` (auto-trigger) |
| "брейнштурм" / scope questions / PHASE 2 binding | `.claude/skills/brainstorm-init/SKILL.md` (auto-trigger) |
| Test PreToolUse hook script | `.claude/skills/hook-test/SKILL.md` (explicit `/hook-test` only) |

Skills replace hardcoded inline workflow logic per progressive disclosure. Не дублировать procedure в other docs.

## Disambiguation FAQ

| Confusion | Answer |
|-----------|--------|
| FSM dispatch — `coordinator.md` OR `state-machine.md`? | Both. **`state-machine.md`** = enum + transitions table (data). **`coordinator.md`** = caller logic (who fires events). Read state-machine for "what transitions exist", read coordinator for "who calls `_transition`". |
| Halt — где живёт? | Persistence layer = `coordinator._set_halt()` writes to `execution_state.halt_reason` + `halt_log` table. Logic dispatch = `coordinator.request_halt()` → FSM event (ADR 0023 invariant). Operator trigger = `kill-switch-cli` (sentinel-file) OR `risk-override` (HMAC-signed manual resume). |
| OCO — `oco.md` OR `bracket.py`? | `oco.md` documents BOTH `src/execution/oco.py` (level computation, ATR-based TP/SL) AND `src/execution/bracket.py` (order builder, fee-aware qty per ADR 0020 sub-decision 6). Single component page covers entire OCO emulation. |
| Reason codes — где canonical list? | `src/risk/reason_codes.py` = source of truth (live, currently 45 codes). `architecture/reason-codes-schema.md` = JSON Schema + audit-record format. `trading/concepts/reason-codes.md` = narrative explanation. Use src for "what codes exist", schema for "what fields", concept for "why". |
| Sprint вопросы — `sprints/` OR `plans/` OR `decisions/`? | **sprints/sprint-NN.md** = "что было сделано" (delivery record, live for completed sprints). **plans/YYYY-MM-DD.md** = "what to do" (bite-sized tasks, used during execution). **decisions/NNNN.md** = "why we chose X" (architectural rationale, immutable except amendments). Read sprints first для context. |
| Reconciler vs Coordinator — кто пишет SQLite? | **Reconciler** produces verdict only (no I/O). **Coordinator.on_ws_reconnect()** acts on verdict + calls `_repo.upsert(...)`. "Exchange wins" per ADR 0019 sub-decision 3 — local state aligned to exchange truth, write-path through Coordinator only. |
| `_bootstrap_done` flag — зачем нужен? | Guard predicate в Coordinator. Set by `bootstrap()` completion. Asserted в `start_bracket` + `on_order_event` BEFORE processing. Prevents WS echo events from старых orders processing до того как cold/warm reconcile завершён → split-brain prevention. См. `components/coordinator.md` "Bootstrap sequencing" + `decisions/0021` sub-decision 1. |

## Когда не ясно — fallback

1. `Read llm-wiki/wiki/index.md` (full catalog ≤ 14KB, fast scan)
2. `Read llm-wiki/wiki/project/SPRINT_STATE.md` (current state ≤ 2KB)
3. `Read llm-wiki/wiki/project/architecture/current-state.md` (canonical counts + sprint history)
4. `Grep "<keyword>" llm-wiki/wiki/` (full search)
5. Если ещё не ясно — спроси maintainer'а, не improvise

## Maintenance rule

**Update это file when:**
- New ADR landed → add to relevant domain section
- New component page created → add to "Domain-specific lookup"
- Two pages become confused (cross-domain query) → add к "Disambiguation FAQ"
- New canonical source emerges → update Quick lookup table

PHASE 8 step 5/5a HARD-GATE — should also include "if new domain section needed → update mental-map.md" (recommend adding к kit в next iteration).

## Related

- [[index|index.md]] — flat catalog (this is decision-tree, that's enumeration)
- [[components/README|components/ README]] — topic clusters (reverse-lookup: "I'm reading X, what's related?")
- [[architecture/current-state|current-state.md]] — canonical counts + sprint history
- [[architecture/development-workflow|dev-workflow.md]] — methodology master SOP
- [[SPRINT_STATE]] — live working memory
