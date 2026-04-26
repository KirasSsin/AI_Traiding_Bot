---
title: Current State — post-S25 inventory + canonical counts (Dashboard UI shipped, demo-only backtest comparison)
type: architecture
tags: [current-state, inventory, baseline, canonical-counts, sprint-23, honest-close-v05, no-edge-conjoint, mvp-incomplete, hypothesis-5-tested, t5-100-structurally-unreachable, regime-independent-edge, n-trials-archival]
created: 2026-04-19
updated: 2026-04-26
status: stable
sources:
  - src/
  - project/sprints/sprint-14-honest-close.md
  - project/decisions/0029-sprint-14-honest-close.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/decisions/0030-sprint-15-mean-reversion-multi-symbol.md
  - project/sprints/sprint-16-honest-close-v02.md
  - project/decisions/0031-sprint-16-honest-close-v02.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/sprints/sprint-18-honest-close-v01.md
  - project/decisions/0033-sprint-18-honest-close-v01.md
  - project/sprints/sprint-19-15m-architecture.md
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/sprints/sprint-20-15m-measurement.md
  - project/decisions/0035-sprint-20-15m-measurement.md
  - project/sprints/sprint-21-honest-close-v04.md
  - project/decisions/0036-sprint-21-honest-close-v04.md
  - project/sprints/sprint-22-4h-test.md
  - project/decisions/0037-sprint-22-4h-test.md
  - project/sprints/sprint-23-honest-close-v05.md
  - project/decisions/0038-sprint-23-honest-close-v05.md
  - project/sprints/sprint-25-dashboard.md
  - project/decisions/0039-sprint-25-dashboard.md
---

# Current State (post-S25, 2026-04-26) — Dashboard UI shipped (demo-only backtest comparison)

**TL;DR:** Live state on tag `v0.1.0-alpha.25`. **S25 Dashboard sprint** ships HTML+JS UI для backtest comparison через FastAPI на localhost. NEW Presentation context (`src/dashboard/`). 3 strategy presets, 5 timeframes (5M/15M/60/240/1D), 3 symbols (BTC/ETH/SOL). Backfill 2023-01-01 → 2026-04-26 для всех. Trader spec applied: TIER 1 + TIER 2 metrics + 4 mandatory warnings + Sortino anomaly guard. Architecture pattern: localhost-only FastAPI + vanilla JS + auto-open browser + optional dep group. NO live trading через dashboard в S25 (only historical backtest). NO Mainnet support (TESTNET=true enforced). 26 sprints completed. **MVP status unchanged:** strategy validation NEGATIVE (5 hypotheses tested, all FAIL conjoint per S23 honest close). S24 ESC-1 (pause vs multi-symbol scope expansion) STILL OPEN — independent от S25 dashboard. Dashboard позволяет user visualize previous + future backtest runs via UI.

**Previous TL;DR (v0.5 honest close, preserved для context):** v0.5 closed honest at S23 — 5 strategy hypotheses tested across 4.81y BTC, all FAIL conjoint. CC1 T5 100 structurally unreachable BINDING (3 timeframes empirical). CC3 Strategy edge regime-INDEPENDENT (S17+S22 both 5/6+DSR+MC PASS). 5-th honest close в проекте (S14+S16+S18+S21+S23). **v0.5 closed honest:** 5 strategy hypotheses tested across 4.81y Bybit Spot BTCUSDT — all FAIL conjoint per acceptance-criteria.md. S13 EMA crossover 1H / S15 mean-reversion multi-symbol 1H / S17 mean-reversion BTC 1H relaxed (59 trades, 5/6+DSR+MC PASS) / S20 mean-reversion BTC 15M (73 trades, T1=-45.57 Hudson&Urquhart validated) / S22 mean-reversion BTC 4H (62 trades, **5/6+DSR+MC PASS regime-independent**). **CRITICAL INSIGHT BINDING:** T5 floor 100 STRUCTURALLY UNREACHABLE на BTC-only mean-reversion (3 timeframes ~60-73 trades all). T5 only reachable via multi-symbol (out of MVP) OR strategy class change. **`data/cross_trial_sharpes.json` archived к `_v0.5-final.json`, reset к `[]` для v0.6** (4-th archival, mirrors S16/S18/S21). **5-th honest close в проекте (S14+S16+S18+S21+S23).** Strategy edge regime-INDEPENDENT (S17+S22 both PASS): combined ~120 trades available для v0.6-A small-sample ML training. **v0.6+ options:** A hybrid ML / B HMM regime-switch / C multi-symbol revival post-MVP / D different strategy class / E pause / F MVP T5 floor amendment (operator decides spec amendment justified per empirical evidence).

**Pre-S1 historical state** archived в section "Pre-S1 Legacy" внизу.

## Canonical counts (live, MUST be kept current per dev-workflow.md PHASE 8 step 5a HARD-GATE)

| Metric | Value | Source of truth | Last update |
|--------|-------|-----------------|-------------|
| FSM states | **16** | `src/execution/state_machine.py` `ExecutionState` enum | S6 (ADR 0020) |
| FSM events | **30** | `src/execution/state_machine.py` `ExecutionEvent` enum | S8a (ADR 0022, +KILL_SWITCH_REQUESTED) |
| FSM transitions | **74** | `src/execution/state_machine.py` `TRANSITIONS` dict | S8b T7 (ADR 0023, +1 FLAT,RISK_HALT) |
| Reason codes | **45** | `src/risk/reason_codes.py` `ReasonCode` enum | S8a (ADR 0022 G5, +HALT_RUNTIME_CRASH/HALT_BAR_POLL_STALL/KILL_SWITCH_REQUESTED) |
| Component pages | **38** | `wiki/project/components/*.md` (incl. README.md cluster index) | S13 — **S25 added zero components** (Presentation context separate, future dashboard.md component possible) |
| ADRs | **39** | `wiki/project/decisions/*.md` (0001-0039) | S25 (ADR 0039 — Dashboard UI) |
| Sprint pages | **26** | `wiki/project/sprints/sprint-*.md` (sprint-01..sprint-25 + sprint-08a/b/c, S24 = backlog-only no sprint) | S25 (sprint-25-dashboard) |

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
| S8c | (wiki backfill) | v0.1.0-alpha.8c | 2026-04-25 | Wiki backfill + tooling debt + S8a/S8b carry-overs (12 tasks, 4 new components, trace-map mandatory + adr-index-sync hook) |
| S9 | 0024 | v0.1.0-alpha.9 | 2026-04-25 | Data quality detector + mypy --strict full enable + per-fill schema + DSR module (Bailey & López de Prado) |
| S10 | 0025 | v0.1.0-alpha.10 | 2026-04-25 | WFA orchestrator (rolling K=5) + DSR sigma_sr extension + MC sign-flip + block bootstrap + 3-Sharpe routing + vector_backtest annualization fix |
| S11 | 0026 | v0.1.0-alpha.11 | 2026-04-25 | Operator-readiness + pre-flight gap closure (test_risk_flow.py + `_cmd_run`/`_cmd_reconcile_only`/`_cmd_wfa`/`_cmd_monitor` CLI + halt priority matrix + log-grep-templates + pre-flight checklist) |
| S12 | 0027 | v0.1.0-alpha.12 | 2026-04-25 | Live demo validation 24-72h + production wiring (FillRecorderAdapter closes `_NoopFillRecorder` stub + `_load_ohlcv` Parquet shim + live-demo-validation + halt-response-protocol runbooks) |
| S13 | 0028 | v0.1.0-alpha.13 | 2026-04-26 | Backfill 5y BTCUSDT 1H Bybit Spot (42098 bars, 4.81y) + WFA T1-T6 measurement + DSR(N=1) + MC. Verdict: FAIL (4/6 criteria — 20 OOS trades, sample too small). trade_extractor + strategy_metrics components. FSM/counts unchanged. |
| S14 | 0029 | v0.1.0-alpha.14 | 2026-04-26 | Honest close. Trader Q1 EXPAND: T5 unreachable (5x signal frequency gap). v0.1 = infrastructure complete, strategy validation negative. Future direction (operator-driven, no commitment): revision / multi-symbol / timeframe / pause. Documentation only. |
| S15 | 0030 | v0.1.0-alpha.15 | 2026-04-26 | v0.2 retry attempt #1 — FAIL but T5 reached. Mean-reversion (RSI<30 AND close<lower_BB(20, 2σ)) AND-gated × multi-symbol BTC+ETH+SOL на 1H Bybit Spot. T0 CrossTrialLog (closes S14 Q2). T1 load_recent symbol filter (Kelly contamination fix). T2 BB indicator + T3 MeanReversionRsiBBStrategy (NEW). T5 Multi-symbol --symbols CLI. T6 measurement: 108 trades aggregate (T5 PASSED), но T6 mean -12.38 / MC p 0.998 / DSR 0 — FAIL. Different failure mode vs S13 = honest negative. |
| S16 | 0031 | v0.1.0-alpha.16 | 2026-04-26 | v0.2 honest close. Trader CONFIRM Option D: 2 strategy families (S13 EMA crossover + S15 mean-reversion) both FAIL across 4.81y; DSR cross-trial sigma_SR=22.68 с -44.46 anchor → expected max Sharpe gate +21.5 для n_trials=3 = unrealistic. T6 archives `cross_trial_sharpes.json` к `_v0.2.json` + resets к `[]` для v0.3 fresh-start (Bailey 2014 N_trials per hypothesis). BTC +1.75 institutional knowledge preserved для v0.3-A. Documentation only. |
| S17 | 0032 | v0.1.0-alpha.17 | 2026-04-26 | MVP retry hypothesis #3 — FAIL T5 count only. BTC-only mean-reversion relaxed (RSI 35/65 + BB 1.5σ AND-gated) per trader EXPAND. User constraint MVP=BTC only. Pre-registered binding, NO variance cap, T5 failthrough clause. Result: 59 trades < 100 floor, но 5/6 PASS + DSR=1.0 + MC p=0.01 statistically significant. AND-gate multiplier 1.34x (predicted 1.4-1.7x). Strategy edge IS real on BTC mean-reversion regime but sample insufficient. Per ADR 0032 amendment 3 BINDING: → S18 honest close v0.1. |
| S18 | 0033 | v0.1.0-alpha.18 | 2026-04-26 | v0.1 FINAL honest close. Pre-committed per ADR 0032 amendment 3 (T5 failthrough triggered). 3 strategy hypotheses tested across 4.81y BTC Bybit Spot 1H — all FAIL conjoint. CC1 S17 partial signal evidence preserved (MC p=0.01 stat-sig institutional knowledge). T3 archives cross_trial_sharpes.json к _v0.1-final.json + resets к [] для v0.4 fresh-start (mirror S16 CC2). |
| S19 | 0034 | v0.1.0-alpha.19 | 2026-04-26 | v0.4-A architectural sprint (BTC 15M prep). Joint trader+architecture verdict — Option (A) с 7 combined amendments BINDING. 3 architectural Conditions APPLIED + 4 trader Amendments + 167,383 bars 15M backfill. CLI `--interval` arg. NO measurement (S20 = measurement). |
| S20 | 0035 | v0.1.0-alpha.20 | 2026-04-26 | BTC 15M WFA measurement verdict FAIL — T5 73<150 floor (T-Amendment 1 failthrough triggered) + T1/T2/T4/T6 critical fails. Fold #2 -185.21 catastrophic (regime concentration negative). Hudson & Urquhart 2021 empirically validated. S17 partial signal contradicted at 15M (regime-specific к 1H). → S21 honest close BINDING. |
| S21 | 0036 | v0.1.0-alpha.21 | 2026-04-26 | v0.4 honest close. Pre-committed per ADR 0034 amendment 3 (S20 T5 failthrough triggered). 4 strategy hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint. CC1 S17 partial signal evidence preserved. CC3 Hudson & Urquhart 2021 empirically validated. v0.5 options A/B/C/D deferred к operator. |
| S22 | 0037 | v0.1.0-alpha.22 | 2026-04-26 | v0.5-C BTC 4H test — verdict FAIL T5 count. Joint trader+architecture verdict per user directive — both converged Option (C). Frequency probe pre-validated (439 raw triggers). 5-map atomic extension applied. Result: 62 trades < 100 floor, BUT 5/6+DSR=0.996+MC p=0.018 stat-sig PASS (similar pattern к S17 1H). CRITICAL INSIGHT: T5 100 STRUCTURALLY UNREACHABLE на BTC-only mean-reversion. Per ADR 0037 BINDING → S23. |
| S23 | 0038 | v0.1.0-alpha.23 | 2026-04-26 | v0.5 honest close. 5 hypotheses tested across 4.81y BTC — all FAIL conjoint. CC1 T5 100 structurally unreachable BINDING. CC3 Strategy edge regime-INDEPENDENT (S17+S22). cross_trial_sharpes archived → fresh `[]` для v0.6. 5-th honest close. |
| S24 | (backlog-only) | (no tag) | 2026-04-26 | v0.6 brainstorm — joint trader+architecture verdict (E) PROJECT PAUSE. ESC-1 escalated к user (pause vs lift BTC-only constraint). Acceptance gate failure CONFIRMED в S17+S22 (sharpe_gate_passed=false независимо от T5). Option F (T5 floor amendment) cost underestimated. NO sprint created. Backlog committed к main. |
| **S25** | **0039** | **v0.1.0-alpha.25** | **2026-04-26** | **Dashboard UI sprint** — user-driven feature: web UI для backtest comparison через FastAPI + vanilla JS + auto-open browser. NEW Presentation context (`src/dashboard/`). 3 strategy presets, 5 timeframes (5M/15M/60/240/1D), 3 symbols (BTC/ETH/SOL). T0 backfill 2023-01-01 → 2026-04-26. Trader spec: TIER 1 + TIER 2 metrics + 4 mandatory warnings + Sortino anomaly guard. Architecture APPROVE_WITH_CONDITIONS. Demo-only (TESTNET=true). NO live trading через UI. 740 passed pytest (+8 dashboard tests). |

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
