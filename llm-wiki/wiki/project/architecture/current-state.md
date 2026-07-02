---
title: Current State — post-S55 inventory + canonical counts (full-project audit + refactor)
type: architecture
tags: [current-state, inventory, baseline, canonical-counts, sprint-55, audit, refactor, fsm-76, reason-codes-67, s55]
created: 2026-04-19
updated: 2026-06-26
status: stable
sources:
  - src/
  - project/sprints/sprint-25-dashboard.md
  - project/decisions/0039-sprint-25-dashboard.md
  - project/sprints/sprint-27-formula-bug-fixes.md
  - project/decisions/0040-sprint-27-formula-bug-fixes.md
  - project/sprints/sprint-28-process-enforcement.md
  - project/decisions/0041-sprint-28-process-enforcement.md
  - project/sprints/sprint-29-superpowers-integration.md
  - project/decisions/0042-sprint-29-superpowers-integration.md
  - project/sprints/sprint-30-tier-2-agents-mem-wiki-merge.md
  - project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md
  - project/sprints/sprint-31-kit-revision-best-practices.md
  - project/decisions/0044-sprint-31-kit-revision-best-practices.md
  - project/plans/2026-04-26-sprint-32-kit-phase-0-improvements.md
---

# Current State (post-S55, 2026-06-26) — full-project audit + refactor (ADR 0071)

> **Sprint-history таблица (S1–S55):** [[current-state-part-2]] — вынесена S53 T8 (файл превысил 50KB). Этот файл = index: canonical counts + src/ inventory + tech stack.

**TL;DR (post-S31):** Live state on tag `v0.1.0-alpha.31`. **Kit infrastructure layer COMPLETE post-S31:** 9 reviewer agents (L5) + 6 active hooks (mechanical enforcement) + 26 skills mapped к 9-phase flow + 4 plugins curated + 6 MCP servers + 5-step cascade rule + 20/20 best practices coverage. CLAUDE.md split preserved across 3 files (repo + llm-wiki + ~/.claude), pruned -25% tokens (954→756 lines, 61→46KB) per S31. **Kit-overview-ru.md** = single source of truth gateway. **Tooling-inventory-ru.md** Sections 14-19 (Permission modes / Plugin curation / CLI tools / Status line / Token-saver / Non-interactive). **S32 Kit Phase 0 in progress** (this sprint): P0 staleness fixes + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory. **Strategy/trading work BLOCKED** awaiting operator decision on ESC-1 (multi-symbol authorization), ESC-2 ("in profit" semantics), ESC-3 (4H operational implications). Pre-S32 КУ analysis showed kit Phase 0 = 57% avg КУ за 45 мин → highest ROI. Phase 1 (CI/SQLite MCP/freshness hook/dashboard-reviewer) deferred к S33.

**Previous TL;DR (post-S25 Dashboard, preserved для context):** Live state on tag `v0.1.0-alpha.25`. **S25 Dashboard sprint** shipped HTML+JS UI для backtest comparison через FastAPI на localhost. NEW Presentation context (`src/dashboard/`). 3 strategy presets, 5 timeframes (5M/15M/60/240/1D), 3 symbols (BTC/ETH/SOL). Backfill 2023-01-01 → 2026-04-26. Trader spec applied: TIER 1 + TIER 2 metrics + 4 mandatory warnings + Sortino anomaly guard. Architecture pattern: localhost-only FastAPI + vanilla JS + auto-open browser + optional dep group. NO live trading через dashboard. NO Mainnet support (TESTNET=true enforced). **MVP status unchanged:** strategy validation NEGATIVE (5 hypotheses tested, all FAIL conjoint per S23 honest close). Dashboard позволяет user visualize previous + future backtest runs via UI.

**Previous TL;DR (v0.5 honest close, preserved для context):** v0.5 closed honest at S23 — 5 strategy hypotheses tested across 4.81y BTC, all FAIL conjoint. CC1 T5 100 structurally unreachable BINDING (3 timeframes empirical). CC3 Strategy edge regime-INDEPENDENT (S17+S22 both 5/6+DSR+MC PASS). 5-th honest close в проекте (S14+S16+S18+S21+S23). **v0.5 closed honest:** 5 strategy hypotheses tested across 4.81y Bybit Spot BTCUSDT — all FAIL conjoint per acceptance-criteria.md. S13 EMA crossover 1H / S15 mean-reversion multi-symbol 1H / S17 mean-reversion BTC 1H relaxed (59 trades, 5/6+DSR+MC PASS) / S20 mean-reversion BTC 15M (73 trades, T1=-45.57 Hudson&Urquhart validated) / S22 mean-reversion BTC 4H (62 trades, **5/6+DSR+MC PASS regime-independent**). **CRITICAL INSIGHT BINDING:** T5 floor 100 STRUCTURALLY UNREACHABLE на BTC-only mean-reversion (3 timeframes ~60-73 trades all). T5 only reachable via multi-symbol (out of MVP) OR strategy class change. **`data/cross_trial_sharpes.json` archived к `_v0.5-final.json`, reset к `[]` для v0.6** (4-th archival, mirrors S16/S18/S21). **5-th honest close в проекте (S14+S16+S18+S21+S23).** Strategy edge regime-INDEPENDENT (S17+S22 both PASS): combined ~120 trades available для v0.6-A small-sample ML training. **v0.6+ options:** A hybrid ML / B HMM regime-switch / C multi-symbol revival post-MVP / D different strategy class / E pause / F MVP T5 floor amendment (operator decides spec amendment justified per empirical evidence).

**Pre-S1 historical state** archived в section "Pre-S1 Legacy" внизу.

## Canonical counts (live, MUST be kept current per dev-workflow.md PHASE 8 step 5a HARD-GATE)

> **Живые счётчики кита (агенты/хуки/скиллы) — авто:** [[kit-overview-ru]] AUTO-блок (`kit/kit-inventory.sh`, регенерируется). Эта таблица — ручной синк в Фазе 7 (S64 doc-first); при расхождении верь AUTO-блоку. FSM/reason-code money-счётчики — из живого кода (проба в sprint-finish).

| Метрика | Значение | Источник истины | Последнее обновление |
|---------|----------|-----------------|-------------|
| FSM states | **16** | `src/execution/state_machine.py` `ExecutionState` enum | S6 (ADR 0020) |
| FSM events | **30** | `src/execution/state_machine.py` `ExecutionEvent` enum | S8a (ADR 0022, +KILL_SWITCH_REQUESTED) |
| FSM transitions | **76** | `src/execution/state_machine.py` `TRANSITIONS` dict | S55 TL-NEW-01 (+2: (LONG_OPEN, FLATTEN_FAILED)→HALTED + (OCO_ARMING, FLATTEN_FAILED)→HALTED; ранее S8b T7 ADR 0023 = 74) |
| Reason codes | **67** | `src/risk/reason_codes.py` `ReasonCode` enum | S52 T4 (+2 ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS, reason_codes 65→67) |
| Component pages | **60** | `wiki/project/components/*.md` (excl. README.md cluster index) | S64 sync (S57-S63 kit-компоненты) |
| Architecture pages | **+2 NEW S32e** | `wiki/project/architecture/{kit-audit-2026-04-27,tooling-inventory-ru-part-2}.md` | unchanged S33 |
| ADRs | **76** | `wiki/project/decisions/*.md` (0001-0076) | 0076 uniform fable-5 (оператор 2026-07-02, суперседит 0075) |
| Sprint pages | **65** | `wiki/project/sprints/sprint-*.md` (…sprint-63-fable-team) | S64 sync (S57-S63) |
| Reviewer/kit agents | **18** | `~/.claude/agents/` = `kit/agents/` (S57 mirror) | S64 sync (S63 +3: kit-auditor/merge-analyst/release-manager) |
| Active push hooks | **14** | `~/.claude/hooks/` (PreToolUse Bash); sh-файлов 17 | S64 sync (S57-S63 gates+state+cascade) |
| UserPromptSubmit hooks | **2** | `~/.claude/settings.json` (caveman + context-budget) | S32d +context-budget-warn.sh |
| MCP servers | **8** | settings.json + .mcp.json | unchanged S32d |
| CI gates | **YES** | `.github/workflows/ci.yml` (push к main + PR) | S32b (validated 3rd PR S32d) |
| Pre-commit gates | **YES** | `.pre-commit-config.yaml` (ruff + mypy + yamllint) | S32b (no change) |
| Skills × Phase mapped | **36** | sprint-flow-ru.md Skills × Phase integration map | unchanged S32d |
| Sprint metrics tracking | **YES** | `wiki/project/sprint-metrics.md` | S32d NEW |
| **S32 series status** | **COMPLETE** | sprint-32 + sprint-32b + sprint-32c + sprint-32d | S32d FINAL |
| **Kit settings (RU)** | **3 files** | kit-overview-ru.md (S31) / sprint-flow-ru.md (Phase 9 +consolidate-memory step S32) / tooling-inventory-ru.md (19 sections) | S31 single source of truth + S32 cascade STEP 2.5 |
| **CLAUDE.md total tokens** | **~14K (was 18.5K)** | repo + llm-wiki + ~/.claude (3 files, S28 split preserved) | S31 prune -25% per session (S32 no CLAUDE.md changes) |

**Verify counts live (CI-safe):**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected output: `states=16, events=30, transitions=76, reason_codes=67` (transitions 74→76 в S55 TL-NEW-01: (LONG_OPEN|OCO_ARMING, FLATTEN_FAILED)→HALTED; reason_codes 65→67 в S52 T4: ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS)

## Структура `src/` (post-S8b)

| Модуль | Файлы | LoC | Wiki-страница | Спринт происхождения |
|--------|-------|-----|-------------|------------------|
| `__main__.py` | entry | 117 | [[../components/kill-switch-cli]] | S8a (ADR 0022 G6) |
| `analytics/` | __init__ stub | <50 | — | (S8c+ scope) |
| `backtest/` | replay_engine, vector_backtest, reporter, indicators, data_collector, replay | ~700 | [[../components/backtest-harness]] | S2 |
| `core/` | models | <50 | (legacy stub) | pre-S1 (mostly removed) |
| `data/` | __init__ stub | <50 | — | pre-S1 (replaced by marketdata/) |
| `execution/` | coordinator (628), state_machine (170), state_repo (148), reconciler (278), bracket (oco-builder, ADR 0020 sub-decision 2, 101 LoC), models, bybit/{adapter, ws_private, rest} | ~1500 | [[../components/coordinator]], [[../components/execution-state-machine]], [[../components/reconciler]], [[../components/oco]], [[../components/bybit-adapter]], [[../components/ws-private-consumer]] | S5/S6/S7/S8a/S8b |
| `marketdata/` | bar_builder, clock, filters, gaps, models, pipeline, storage | ~600 | [[../components/bar-builder]], [[../components/storage]] | S2 |
| `ml/` | kronos_adapter, prediction_cache | ~300 | [[../components/kronos-adapter]], [[../components/prediction-cache]] | S52 (ADR 0068, optional `[ml]` dep) |
| `platform/` | config, db, logging | ~350 | [[../components/config]], [[../components/logging]] | S1 |
| `risk/` | manager (315), kelly (128), reason_codes, override (147), trade_history (118), circuit_breakers, equity_tracker, sizing, resume_cb, models | ~1100 | [[../components/risk-manager]], [[../components/kelly]], [[../components/sizing]], [[../components/circuit-breakers]], [[../components/risk-override]], [[../components/trade-history]] | S4/S7 |
| `runtime/` | manager (231), bar_source (~150) | ~380 | [[../components/runtime-manager]], [[../components/bar-poller]] | S8a |
| `signalgen/` | strategy (181), indicators (113), models | ~340 | [[../components/strategy]], [[../components/indicators]], [[../components/models]] | S3 |

**Total:** ~4693 LoC (`wc -l src/*/*.py` excluding `__pycache__`).

## Стек реально используется (post-S8b)

| Слой | Технология | Введён в спринте |
|------|-----------|-----------------|
| Language | Python 3.12 (StrEnum, PEP 604) | S1 (ADR 0002) |
| Models | pydantic v2 | S1 (ADR 0006) |
| Storage | SQLite WAL (state) + Parquet snappy (OHLCV) | S1 (ADR 0003) |
| Exchange | Bybit V5 Spot (pybit>=5.11) | S2 (ADR 0016 supersedes 0004 Binance) |
| TA library | TA-Lib (Wilder EMA + classical EMA crossover) | S3 (ADR 0011) |
| Statistics | scipy>=1.12, numpy>=1.26 | S4 |
| ML (optional `[ml]`) | torch>=2.2, transformers, tokenizers, safetensors, einops, huggingface_hub | S52 (ADR 0068) |
| Logging | structlog | S1 (ADR 0008) |
| Tests | pytest + property-based + integration (opt-in `RUN_DEMO=1`; opt-in `RUN_ML=1` для ML integration) | S1+ / S52 |
| Lint/Type | ruff + mypy --strict | S1 |
| Concurrency | sync + threading.RLock (Coordinator) + threading.Lock (Reconciler) | S8a (ADR 0022 sub-decision 1) |

**НЕ используется (отклонено/отложено):**
- gRPC (`src/gateway/` skeleton удалён в S2)
- HMM regime detection (`src/strategy/hmm_regime.py` legacy — удалён в S2)
- XGBPredictor (отложено → v0.2). `src/ml/` — СОЗДАН в S52 (Kronos: KronosAdapter + PredictionCache, optional `[ml]` dep group, torch-isolated)
- asyncio/uvloop (отложено → S9+)
- TimescaleDB / DuckDB (отклонено по ADR 0003)

## Карта спринтов

> Таблица вынесена в [[current-state-part-2]] (S53 T8 split — файл превысил 50KB). Последний спринт: **S55** — full-project audit + refactor (ADR 0071).

Полная таблица (S1–S55) → [[current-state-part-2]].

## Состояние тестов/качества (живое, базовый уровень S31 сохранён через S32)

- pytest unit: **762 passed** (базовый уровень S27-S31; +18 vs S26 до исправления формул)
- pytest property: 8/8
- pytest integration: opt-in `RUN_DEMO=1` (Demo Mainnet)
- mypy --strict src/: ≤ 44 ошибок (базовый уровень S8c сохранён через S31)
- ruff: чистый на src + tests S8+; legacy `src/core/`, `src/backtest/*` исключены в pyproject.toml (pending retirement)

---

## Наследие до S1 (архив, для исторического контекста)

> Этот раздел описывает кодовую базу ДО Sprint 1 (базовый уровень 2026-04-19). Зафиксирован для исторической трассируемости; **не отражает текущее состояние**. Большинство legacy-модулей удалено в S2-S5 (см. `git log --oneline -- src/controller.py main.py`).

**Pre-S1 TL;DR (2026-04-19):** Existing code = Phase 1 MVP на Bybit (perpetual futures, linear, 1m bars, EMA+RSI+ATR). НЕ Binance Spot 1H. Math stack (Hurst, Kelly, CVaR, HMM) заложен, но XGBPredictor + HMM не задействованы в live signal. Нет TA-Lib, pydantic, SQLite/Parquet, DDD-структурирования.

**Pre-S1 src/ structure (REMOVED/REPLACED):**

| Модуль до S1 | Статус после S8b |
|-------------|-----------------|
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

**Примечания по стеку до S1:**

- pybit (V5) — сохранён, обновлён в S2
- `pandas==2.x`, `numpy==1.x` — без pinning. **Сейчас:** pinned `>=` floor в pyproject.toml.
- structlog — добавлен в S1.
- pydantic — добавлен в S1.
- `python-dotenv` — сохранён.
- `xgboost`, `hmmlearn`, `joblib` — отложено / удалено.
- TA-Lib — добавлен в S3.
- DDD bounded contexts отсутствовали — добавлены в S1.

**До S1 не было:**
- DDD bounded contexts
- Pydantic schemas
- SQLite WAL persist
- Parquet OHLCV storage
- Репозиторий ADR
- Test suite (unit/property/integration)
- Domain reviewer agents
- llm-wiki/

## Связанные

- [[../components/execution-state-machine]] — FSM TRANSITIONS table — canonical live count
- [[acceptance-criteria]] — T1-T6 gates (amended S34 LOCKED)

## Источники

- `src/` (живое дерево)
- `project/sprints/sprint-08b-carryover.md` (последний спринт)
- `project/decisions/0023-halt-code-fsm-event-mapping.md` (последний ADR)
- `Docs/current_bot/README_RU.md` + `IMPLEMENTATION_NOTES.md` (базовый уровень до S1)
