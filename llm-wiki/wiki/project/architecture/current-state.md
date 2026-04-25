---
title: Current State — post-S8c inventory + canonical counts
type: architecture
tags: [current-state, inventory, baseline, canonical-counts, sprint-8c]
created: 2026-04-19
updated: 2026-04-25
status: stable
sources:
  - src/
  - project/sprints/sprint-08c-wiki-backfill.md
  - project/decisions/0023-halt-code-fsm-event-mapping.md
---

# Current State (post-S9, 2026-04-25)

**TL;DR:** Live state v0.1 on tag `v0.1.0-alpha.9`. 11 sprints completed (S1-S7 + S8a + S8b + S8c + S9). S9 added: data quality detector (REST-vs-REST → HALT_DATA_QUALITY) + mypy --strict full enable + per-fill schema (trade_fills + WS execution topic) + DSR module (Bailey & López de Prado). Single-symbol Bybit Spot BTCUSDT 1H. EMA(12)×EMA(26) + ADX(14) + RSI(14) + ATR(14). LONG+FLAT only. signal on close(T) → fill at open(T+1) (look-ahead-free). 4-phase Kelly + Wilson 95% CI + L1/L2/L3/flash circuit breakers + manual override. 3-order Spot OCO emulation. 16-state Harel FSM. Live runtime: `python -m src run` (S8a STUB, production wiring pending). Demo Mainnet ready. Pre-production hardening continues.

**Pre-S1 historical state** archived в section "Pre-S1 Legacy" внизу.

## Canonical counts (live, MUST be kept current per dev-workflow.md PHASE 8 step 5a HARD-GATE)

| Metric | Value | Source of truth | Last update |
|--------|-------|-----------------|-------------|
| FSM states | **16** | `src/execution/state_machine.py` `ExecutionState` enum | S6 (ADR 0020) |
| FSM events | **30** | `src/execution/state_machine.py` `ExecutionEvent` enum | S8a (ADR 0022, +KILL_SWITCH_REQUESTED) |
| FSM transitions | **74** | `src/execution/state_machine.py` `TRANSITIONS` dict | S8b T7 (ADR 0023, +1 FLAT,RISK_HALT) |
| Reason codes | **45** | `src/risk/reason_codes.py` `ReasonCode` enum | S8a (ADR 0022 G5, +HALT_RUNTIME_CRASH/HALT_BAR_POLL_STALL/KILL_SWITCH_REQUESTED) |
| Component pages | **32** | `wiki/project/components/*.md` (incl. README.md cluster index) | S9 (data-quality + fill-history + dsr) + C7 batch (wiki-broken-link-hook) + S8c (kill-switch-cli + risk-override + trade-history + backtest-harness + adr-index-sync-hook) + post-S8c (components/README.md) |
| ADRs | **24** | `wiki/project/decisions/*.md` (0001-0024) | S9 (ADR 0024 — aggregate Q1+Q2+Q3) |
| Sprint pages | **11** | `wiki/project/sprints/sprint-*.md` (sprint-01..sprint-07 + sprint-08a + sprint-08b + sprint-08c + sprint-09) | S9 (sprint-09-data-quality-types-analytics) + C7 batch (sprint-08c-wiki-backfill) |

**Verify counts live (CI-safe):**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected output: `states=16, events=30, transitions=74, reason_codes=45`

## Структура `src/` (post-S8b)

| Module | Files | LoC | Wiki page | Sprint origin |
|--------|-------|-----|-----------|---------------|
| `__main__.py` | entry | 117 | [[../components/kill-switch-cli]] | S8a (ADR 0022 G6) |
| `analytics/` | __init__ stub | <50 | — | (S8c+ scope) |
| `backtest/` | replay_engine, vector_backtest, reporter, indicators, data_collector, replay | ~700 | [[../components/backtest-harness]] | S2 |
| `core/` | models | <50 | (legacy stub) | pre-S1 (mostly removed) |
| `data/` | __init__ stub | <50 | — | pre-S1 (replaced by marketdata/) |
| `execution/` | coordinator (628), state_machine (170), state_repo (148), reconciler (278), bracket (oco-builder, ADR 0020 sub-decision 2, 101 LoC), models, bybit/{adapter, ws_private, rest} | ~1500 | [[../components/coordinator]], [[../components/execution-state-machine]], [[../components/reconciler]], [[../components/oco]], [[../components/bybit-adapter]], [[../components/ws-private-consumer]] | S5/S6/S7/S8a/S8b |
| `marketdata/` | bar_builder, clock, filters, gaps, models, pipeline, storage | ~600 | [[../components/bar-builder]], [[../components/storage]] | S2 |
| `platform/` | config, db, logging | ~350 | [[../components/config]], [[../components/logging]] | S1 |
| `risk/` | manager (315), kelly (128), reason_codes, override (147), trade_history (118), circuit_breakers, equity_tracker, sizing, resume_cb, models | ~1100 | [[../components/risk-manager]], [[../components/kelly]], [[../components/sizing]], [[../components/circuit-breakers]], [[../components/risk-override]], [[../components/trade-history]] | S4/S7 |
| `runtime/` | manager (231), bar_source (~150) | ~380 | [[../components/runtime-manager]], [[../components/bar-poller]] | S8a |
| `signalgen/` | strategy (181), indicators (113), models | ~340 | [[../components/strategy]], [[../components/indicators]], [[../components/models]] | S3 |

**Total:** ~4693 LoC (`wc -l src/*/*.py` excluding `__pycache__`).

## Стек реально используется (post-S8b)

| Layer | Tech | Sprint introduced |
|-------|------|-------------------|
| Language | Python 3.12 (StrEnum, PEP 604) | S1 (ADR 0002) |
| Models | pydantic v2 | S1 (ADR 0006) |
| Storage | SQLite WAL (state) + Parquet snappy (OHLCV) | S1 (ADR 0003) |
| Exchange | Bybit V5 Spot (pybit>=5.11) | S2 (ADR 0016 supersedes 0004 Binance) |
| TA library | TA-Lib (Wilder EMA + classical EMA crossover) | S3 (ADR 0011) |
| Statistics | scipy>=1.12, numpy>=1.26 | S4 |
| Logging | structlog | S1 (ADR 0008) |
| Tests | pytest + property-based + integration (opt-in `RUN_DEMO=1`) | S1+ |
| Lint/Type | ruff + mypy --strict | S1 |
| Concurrency | sync + threading.RLock (Coordinator) + threading.Lock (Reconciler) | S8a (ADR 0022 sub-decision 1) |

**NOT used (rejected/deferred):**
- gRPC (`src/gateway/` skeleton удалён в S2)
- HMM regime detection (`src/strategy/hmm_regime.py` legacy — удалён в S2)
- XGBPredictor / `src/ml/` (deferred → v0.2)
- asyncio/uvloop (deferred → S9+)
- TimescaleDB / DuckDB (rejected по ADR 0003)

## Карта спринтов

| Sprint | ADR | Tag | Date | Theme |
|--------|-----|-----|------|-------|
| S1 | 0001-0015 (foundational) | v0.1.0-alpha.1 | 2026-04-20 | DDD skeleton + platform + models + storage |
| S2 | 0016 | v0.1.0-alpha.2 | 2026-04-21 | Bybit venue migration + MarketData + adapter |
| S3 | 0017 | v0.1.0-alpha.3 | 2026-04-22 | EMA/ADX/RSI/ATR strategy port (Wilder + classical) |
| S4 | 0018 | (skipped, → alpha.6) | 2026-04-23 | Risk module (Kelly + Wilson + L1-L3+flash + override) |
| S5 | 0019 | (skipped, → alpha.6) | 2026-04-23 | Execution layer (OCO + 12-state FSM + Reconciler) |
| S6 | 0020 | v0.1.0-alpha.6 | 2026-04-23 | 3-order Spot OCO emulation (FSM 12→16, +8 events) |
| S7 | 0021 | v0.1.0-alpha.7 | 2026-04-24 | Resilience (bootstrap + 4-valued reconcile + γ halt persistence) |
| S8a | 0022 | v0.1.0-alpha.8a | 2026-04-24 | Live Runtime (RuntimeManager + bar poller + KILL_SWITCH + threading) |
| S8b | 0023 | v0.1.0-alpha.8b | 2026-04-24 | S8a carry-over fixes + ADR 0023 halt-code mapping invariant |

**Tag drift note (S4+S5):** `v0.1.0-alpha.4` + `v0.1.0-alpha.5` never created — S4+S5+S6 consolidated в одну ship-волну под `v0.1.0-alpha.6`. См. `wiki/project/sprints/README.md` Tag exceptions section + `wiki/project/pre-s8c-backlog.md` Bucket A5.

## Test/quality state (live)

- pytest unit: 604 passed / 24 skipped / 3 pre-existing test_config env-pollution failures (carry-over → S8c)
- pytest property: 8/8
- pytest integration: opt-in `RUN_DEMO=1` (Demo Mainnet)
- mypy --strict src/: 44 errors (pre-existing tech debt, не S8b regression)
- ruff: clean on S8 src + tests; legacy `src/core/`, `src/backtest/*` excluded в pyproject.toml pending retirement

---

## Pre-S1 Legacy (archived, для исторического контекста)

> Этот раздел описывает codebase ДО Sprint 1 (2026-04-19 baseline). Зафиксирован для исторической трассируемости; **не отражает текущее состояние**. Большая часть legacy modules удалена в S2-S5 (см. `git log --oneline -- src/controller.py main.py`).

**Pre-S1 TL;DR (2026-04-19):** Existing code = Phase 1 MVP на Bybit (perpetual futures, linear, 1m bars, EMA+RSI+ATR). НЕ Binance Spot 1H. Math stack (Hurst, Kelly, CVaR, HMM) заложен, но XGBPredictor + HMM не задействованы в live signal. Нет TA-Lib, pydantic, SQLite/Parquet, DDD-структурирования.

**Pre-S1 src/ structure (REMOVED/REPLACED):**

| Pre-S1 module | Status post-S8b |
|---------------|------------------|
| `src/core/{models, math_engine}.py` | math_engine удалён в S4; models ужал stub |
| `src/data/consumer.py` | удалён в S2, заменён `src/marketdata/` + pybit |
| `src/strategy/{strategy, hmm_regime, order_flow}.py` | удалены в S3, заменены `src/signalgen/` |
| `src/risk/risk_manager.py` | удалён в S4, заменён `src/risk/manager.py` |
| `src/execution/executor.py` | удалён в S5, заменён `src/execution/coordinator.py` + adapter |
| `src/gateway/` (gRPC stubs) | удалены в S2 |
| `src/backtest/vector_backtest.py` | сохранён, расширен `src/backtest/replay_engine.py` (S2) |
| `src/ml/models.py` | удалён → deferred v0.2 |
| `src/controller.py` | удалён в S8a (broken since S2) |
| `main.py` (top-level) | удалён в S8a |

**Pre-S1 stack notes:**

- pybit (V5) — kept, upgraded in S2
- `pandas==2.x`, `numpy==1.x` — без pinning. **Сейчас:** pinned `>=` floor in pyproject.toml.
- structlog — добавлен в S1.
- pydantic — добавлен в S1.
- `python-dotenv` — kept.
- `xgboost`, `hmmlearn`, `joblib` — deferred / removed.
- TA-Lib — добавлен в S3.
- Нет DDD bounded contexts — добавлены в S1.

**Pre-S1 не было:**
- DDD bounded contexts
- Pydantic schemas
- SQLite WAL persist
- Parquet OHLCV storage
- ADR repository
- Test suite (unit/property/integration)
- Domain reviewer agents
- llm-wiki/

## Sources

- `src/` (live tree)
- `project/sprints/sprint-08b-carryover.md` (latest sprint)
- `project/decisions/0023-halt-code-fsm-event-mapping.md` (latest ADR)
- `Docs/current_bot/README_RU.md` + `IMPLEMENTATION_NOTES.md` (pre-S1 baseline reference)
