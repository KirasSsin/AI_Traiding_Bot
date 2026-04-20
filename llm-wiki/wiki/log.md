# Log

Хронологический append-only журнал wiki. Формат записи:

```
## [YYYY-MM-DD] <ingest|query|lint> | <короткое описание>
- ...
```

Парсится простыми unix-инструментами: `grep "^## \[" log.md | tail -5`.

---

## [2026-04-19] init | Wiki скелет создан
- Added: CLAUDE.md, README.md, wiki/index.md, wiki/log.md
- Структура каталогов: raw/{trading,project,assets}, wiki/{trading,project}, queries/
- Notes: пустая wiki готова к первому ingest.

## [2026-04-19] ingest | MVP v0.1 спецификация (Docs/MVP + Docs/MVP + ALL PROJECT)
- Sources: Docs/MVP/{MVP-DESCRIPTION,FINAL-CONSOLIDATED,Architecture-Analysis,Deep-Research-Report}.md, Docs/MVP + ALL PROJECT/{MVP,Full Project}.md.
- Added (architecture, 11): overview, bounded-contexts, state-machine, domain-events, stack-v0.1, storage, execution-timing, edge-cases, acceptance-criteria, risk-register, reason-codes-schema.
- Added (decisions, 15): ADR 0001…0015 (ADR-формат, python-only, sqlite+parquet, binance-spot, 1h, pydantic v2, utc-ns, uvloop, semver, sqrt-slippage, wilder-vs-classical, 4-phase-kelly, CB-L1/L2/L3/flash, walk-forward-2000/500, sign-flip-MC-N=2000).
- Added (strategies, 1): ema-crossover-adx-rsi.
- Added (indicators, 4): ema, adx, rsi, atr.
- Added (concepts, 8): kelly-phases, circuit-breakers, slippage-model, walk-forward-validation, deflated-sharpe-ratio, monte-carlo-permutations, reason-codes, look-ahead-bias.
- Notes: v0.1 таргет оформлен полностью. Все страницы на русском, кросс-линки [[...]] прописаны. Выявлено 22 риска и 24 edge-кейса — требуют детекторов в коде.

## [2026-04-19] ingest | Инвентаризация текущего кода (src/, Docs/current_bot/)
- Sources: src/{core,data,strategy,risk,execution,gateway,backtest,ml}/, controller.py, main.py; Docs/current_bot/{README_RU,IMPLEMENTATION_NOTES,Specification-*}.md.
- Added: wiki/project/architecture/current-state.md.
- Notes: существующий код — Phase 1 MVP на Bybit linear (perpetual futures, 1m, EMA+RSI+ATR через pandas .ewm(), in-memory storage, 4 math-теста). НЕ соответствует MVP v0.1 target (Binance Spot, 1H, TA-Lib, pydantic v2, SQLite+Parquet, DDD).

## [2026-04-19] lint | Gap-analysis current vs MVP v0.1
- Added: wiki/project/architecture/gap-analysis.md.
- Findings: 24 расхождения. P0 (9): venue Bybit→Binance, timeframe 1m→1H, symbol side no-SHORT, TA-Lib + ADX + Wilder, SQLite+Parquet storage, OCO bracket + partial-fill, circuit breakers L1/L2/L3/flash, reconciliation при reconnect, cleanup src/ml/ + src/gateway/. P1 (9): pydantic v2, DDD контексты, 20 domain events, 12-state machine, Kelly 4 фазы, walk-forward+MC+DSR, look-ahead protection, audit log, edge-case detectors. P2 (4): uvloop, CI/CD, structlog+Sentry, Grafana.
- Предложено 10 спринтов общей длительностью 3-4 месяца (детали — Stage 2 migration-plan.md).
- Contradictions: старая Specification-Trading-Bot.md покрывает L2/ML/HMM — явно вне scope v0.1 (см. ADR 0002).
- Orphans: нет (все страницы залинкованы из index.md + cross-refs).

## [2026-04-19] lint | Index обновлён, Stage 1 завершён
- Updated: wiki/index.md — каталог 41 страницы (13 architecture + 15 decisions + 1 strategy + 4 indicators + 8 concepts).
- Notes: Stage 1 (Documentation Ingest + Inventory) завершён. Следующий шаг — Stage 2: migration-plan.md с детальной разбивкой по спринтам и переходом к Stage 3 (реализация P0 спринтов по TDD).

## [2026-04-20] ingest | Superpowers methodology integration
- Added: wiki/project/architecture/development-workflow.md — маппинг Superpowers 7-step pipeline на 10 спринтов v0.1.
- Updated: llm-wiki/CLAUDE.md — секция "Связь с Superpowers" (параллельный workflow к wiki-maintenance).
- Updated: llm-wiki/README.md — упоминание методологии + ссылка на workflow.
- Updated: wiki/index.md.
- Source: obra/superpowers README (установка `/plugin install superpowers@claude-plugins-official`).
- Notes: зафиксирован принцип сосуществования — wiki-maintainer workflow (ingest/query/lint) + Superpowers (code-work). Code-commit триггерит wiki-ingest; wiki-lint может триггерить brainstorming.

## [2026-04-20] plan | Sprint 1 — Foundation implementation plan
- Added: wiki/project/plans/2026-04-20-sprint-1-foundation.md.
- Updated: wiki/index.md (новая секция "Project — Plans").
- Scope: 12 tasks с TDD: legacy branch, pyproject/ruff/mypy, DDD skeleton, Settings, structlog, Bar/Signal/Order/Fill (pydantic v2), SQLite WAL + migrations, Parquet writer, legacy cleanup, Makefile, wiki-sync.
- Source of truth: wiki/project/architecture/{migration-plan,storage,stack-v0.1}.md + ADR 0003, 0006, 0007.
- Notes: План готов к исполнению. Два варианта: subagent-driven-development (рекомендуемый) или executing-plans inline.

## [2026-04-20] ingest | Migration plan (Stage 2)
- Added: wiki/project/architecture/migration-plan.md.
- Updated: wiki/index.md.
- Scope: 10 спринтов компактного формата (goal, scope, AC, deps, artifacts), before/after src/ структура, mapping старых путей → DDD контексты, legacy freeze plan, local ops playbook, 8 migration-specific risks, rollback strategy.
- Key decision: **local-first MVP** (macOS/Linux laptop), Docker/GHA/VPS/Prometheus — явно помечены v0.2 Deploy release.
- Dependencies graph: S1 → {S2, S3, S6} → S4 → S5 → S7 → S8 → S9 → S10.
- Self-review: исправлен inconsistency в dependency graph (S2→S4 удалён, т.к. S4 deps = S1+S3 per sprint text).
- Notes: Stage 2 завершён. Готово к Stage 3 — старт Sprint 1 (Foundation) по TDD при одобрении пользователя.

## [2026-04-20] ingest | Sprint 1 — Foundation completed
- Added (code): src/platform/{config,logging,db}.py, src/marketdata/{models,storage}.py, src/signalgen/models.py, src/execution/models.py, migrations/001_initial.sql, Makefile, conftest.py, tests/conftest.py, 6 unit-test модулей (20 tests).
- Added (wiki): wiki/project/components/{config,logging,models,storage}.md.
- Removed: src/ml/, src/gateway/, src/strategy/{hmm_regime,order_flow,strategy}.py, src/data/consumer.py, src/execution/executor.py, src/controller.py, main.py, test_execution.py, tests/test_math.py, protos/, pybit-master/, test_grpc_latency.py (Bybit chain + legacy).
- Preserved: branch `legacy/phase1-bybit` содержит полный старый код.
- Updated: wiki/index.md (Project — Components — 4 записи).
- Tag: `v0.1.0-alpha.1` на HEAD (commit a0f57f8).
- Verification: `make check` green — ruff clean, mypy --strict clean (22 files), pytest 20/20 passed.
- Python runtime: установлен 3.12.13 через Homebrew, worktree-local `.venv/`, editable install `pip install -e ".[dev]"`.
- Commits (TDD, 12): Tasks 1–12 в ветке текущей работы. Legacy (ml/backtest/risk_manager) — под ruff/mypy ignore до соответствующих спринтов S3-S5.
- Notes: Stage 3 Sprint 1 закрыт. Следующий — Sprint 2 (MarketData ingest: Binance REST backfill + WS live) по migration-plan §S2.
