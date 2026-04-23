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

## [2026-04-21] ingest | Sprint 2 — Bybit venue migration + MarketData ingest
- Added (code): src/marketdata/bybit/{rest,ws}.py, src/marketdata/{clock,filters,bar_builder,gaps,pipeline}.py, src/execution/bybit/{adapter,errors}.py, 9 unit-test модулей + 1 integration smoke.
- Added (wiki): wiki/project/decisions/0016-bybit-spot-supersedes-binance.md, wiki/project/components/{bybit-rest,bybit-ws,bar-builder,bybit-adapter}.md.
- Modified (wiki): decisions/0004 (→superseded), architecture/{migration-plan,stack-v0.1,bounded-contexts,edge-cases,overview}.md, wiki/project/components/config.md.
- Modified (code): pyproject.toml (python-binance → pybit>=5.11 + mypy overrides), .env.example (BINANCE_* → BYBIT_*), src/platform/config.py (Settings rename + testnet-defaults per user directive), Makefile (test-integration target).
- Tag: v0.1.0-alpha.2 (commit TBD на HEAD Sprint 2).
- Verification: `make check` green — ruff/mypy --strict/pytest unit (~35 tests). Integration smoke env-gated.
- Notes: Stage 3 Sprint 2 закрыт. Готово к Sprint 3 (Strategy port — EMA/ADX/RSI/ATR через TA-Lib + on_bar → Signal).

## [2026-04-22] lint | Gap-audit wiki перед Sprint 3
- Выполнен thorough lint-проход по `wiki/` (55 файлов) против требований `acceptance-criteria.md` и `migration-plan.md §S3-S10`.
- Findings: 44 пробела — 1 contradiction (ADR 0004 frontmatter) + 18 missing concept pages + 13 missing component pages + 4 missing architecture pages + 1 formula gap (Sortino partial-moment) + 7 cross-link gaps + 0 orphans.
- P0 (блокирует S3): components/strategy.md, trading/concepts/sortino-ratio.md.
- P1 (S4-S6): backtesting-workflow, MinBTL, PBO, component suite (risk-manager, kelly, circuit-breakers, oco, reconciler, state-machine, event-bus, event-sourcing, clock, filters, gaps, pipeline), architecture/{backtester-spec, ci-cd-strategy}.
- P2 (S7-S10): CVaR/VaR/RoR/Calmar concepts, paper-trading, observability, dashboard spec, fat-tails/Hurst, stationarity tests.
- Policy: P0/P1 страницы создаются синхронно с кодом в последнем task соответствующего спринта (как S1/S2). Авансовое создание запрещено — противоречит YAGNI `llm-wiki/CLAUDE.md`.

## [2026-04-22] sprint-doc | Введена директория sprints/ для per-sprint delivery records
- Added: wiki/project/sprints/README.md (шаблон + правила использования).
- Added: wiki/project/sprints/sprint-01-foundation.md, sprint-02-bybit-venue-migration.md.
- Updated: wiki/index.md (новая секция "Project — Sprints").
- Назначение: continuity между сессиями LLM — новая сессия читает sprint-page и сразу понимает контекст (scope, deviations, follow-ups, impact). Отделено от `plans/` (pre-execution) и `log.md` (append-only chronological).
- Правило: следующий sprint-page создаётся в последнем task следующего спринта (аналогично wiki-ingest для компонентов).

## [2026-04-22] ingest | Sprint 3 — Strategy port completed
- Added (code): src/signalgen/{indicators,strategy}.py, tests/unit/test_{indicators,strategy}.py, tests/property/test_lookahead.py.
- Added (wiki): wiki/project/components/{indicators,strategy}.md, wiki/project/sprints/sprint-03-strategy-port.md, wiki/project/plans/2026-04-22-sprint-3-strategy-port.md.
- Modified (code): pyproject.toml (+TA-Lib>=0.4.28, mypy override `talib`, testpaths += "tests/property"), src/platform/config.py (8 strategy_* params), tests/unit/test_{config,deps}.py (+1 test each).
- Modified (wiki): index.md (Project — Components +2 entries; Project — Sprints +1 entry; Project — Plans +1 entry).
- Removed: src/strategy/ (пустая legacy от S1).
- Tag: v0.1.0-alpha.3 (HEAD на момент tag).
- Verification: `make check` green — ruff/mypy --strict/pytest 84/84 (83 unit + 1 property hypothesis с 30 examples). Inline-verified.
- Subagent execution: 14 dispatches (haiku × 7 mechanical, sonnet × 6 standard TDD, opus × 1 для critical LONG entry с numerical tuning).
- Decisions/deviations: (1) Wilder EMA — own implementation (TA-Lib не поддерживает); (2) crafted-bars fixture для LONG entry retuned — резкий rally (+1.5) толкал RSI > 70 раньше cross-up'а, изменено на gentler (+0.2 × 30); (3) duplicate/OOO guard добавлен в on_bar() как defense-in-depth.
- Notes: Stage 3 Sprint 3 закрыт. Готово к Sprint 4 (Risk — 4-phase Kelly + CB L1/L2/L3/flash) per migration-plan §S4.

## [2026-04-22] ingest | Review-agent harness (ADR 0017)
- Added (agents): ~/.claude/agents/trading-logic-reviewer.md (opus), ~/.claude/agents/quant-stats-reviewer.md (opus), ~/.claude/agents/data-integrity-reviewer.md (sonnet).
- Added (wiki): wiki/project/decisions/0017-review-agent-harness.md.
- Modified (wiki): index.md (Project — Decisions +1), llm-wiki/CLAUDE.md (новая секция "Связь с review-агентами").
- Existing: ~/.claude/agents/Python Reviewer.md (generic Python hygiene) сохранён.
- Rationale: generic superpowers review + python-reviewer не покрывают доменные риски (look-ahead, Wilder/classical EMA, Kelly phases, OHLCV invariants). Альтернатива из 14 "персон" отклонена — overlap 60-70%, конфликт выбора. Выбраны 3 консолидированных агента с non-overlapping scope и MUST-BE-USED триггерами в description.
- When invoke: матрица в ADR 0017 (по спринтам S3-S9). Доменные ревьюеры заменяют generic quality reviewer на соответствующих файлах.
- Notes: агенты обязаны читать конкретные wiki/ADR перед ревью — операционализация wiki как source of truth. Stale wiki выявляется через "Follow-ups for wiki" секцию отчёта.

## [2026-04-22] ingest | ADR ↔ Agent sync hook (автоматизация 0017)
- Added (infra): ~/.claude/hooks/adr-agent-sync-check.sh (+x), регистрация в ~/.claude/settings.json (hooks.PreToolUse → Bash).
- Added (wiki): wiki/project/components/adr-agent-sync-hook.md (полная спецификация + алгоритм + fail-open policy + acknowledge flow).
- Modified (wiki): wiki/project/decisions/0017-review-agent-harness.md (consequences: "Минус закрыт — автоматизировано"), llm-wiki/CLAUDE.md (добавлен параграф про автоматический sync-контроль), wiki/index.md (Project — Components +1).
- Механика: hook срабатывает на PreToolUse Bash, фильтрует `git push`, сверяет `git log base..HEAD -- wiki/project/decisions/` с max mtime `~/.claude/agents/*.md`. Drift → exit 2 + stderr → push заблокирован. Fail-open для всего нерелевантного.
- Acknowledge flow: `touch ~/.claude/agents/<any>.md` продвигает mtime — явный ack, если ADR не требует agent-update.
- Verification: non-push → exit 0 ✅; push в worktree без committed ADR → exit 0 ✅ (ожидаемо — ADR 0017 пока не закоммичен); fail-closed ветка проверится на первом реальном ADR-коммите при PR'е.
- Notes: YAGNI-граница пройдена — sync-чек назван в CLAUDE.md, но без автоматизации он обречён забываться. Drift в prompt'ах агентов = молчаливая потеря корректности ревью. Теперь блокирующий.

## [2026-04-23] ingest | Sprint 4 — Risk module delivered (Tasks 1-17)
- Sources: src/risk/* (manager.py, kelly.py, circuit_breakers.py, sizing.py, equity_tracker.py, trade_history.py, override.py, state_repo.py, resume_cb.py, models.py, reason_codes.py), migrations/{002_risk,003_trade_history_unique}.sql, tests/{unit,integration}/test_risk_*.
- Added (wiki/components, 4): kelly.md, circuit-breakers.md, sizing.md, risk-manager.md.
- Added (wiki/sprints, 1): sprint-04-risk.md.
- Added (wiki/decisions, 1): 0018-sprint-4-risk-decisions.md (5 sub-decisions: R:R 2:1, REJECT_INVALID_SIGNAL/ZERO_QTY не распакованы, Wilson lower bound для phases 3/4, L0 explicit naming, reason-codes count 28→29).
- Modified (wiki): index.md (+1 sprint, +1 plan, +4 components, +1 decision), trading/concepts/reason-codes.md (header 28→29, exits 7→8, halts 6→7, total 6+8+8+7=29 + S4 note).
- Implementation highlights: 4-phase Kelly с Wilson 95% CI lower bound для phases 3/4 (conservative edge); L1/L2/L3/Flash CB stateless detector + EquityTracker 24h rolling HWM; OverrideStore с config_hash anti-replay; RiskManager.assess enforces look-ahead invariant `assessed_at >= signal.generated_at`; 50-bar integration flow в test_risk_flow.py.
- Removed: src/risk/risk_manager.py (legacy stub), src/core/math_engine.py (mock Kelly).
- Verification: 308 tests passing (unit 12 файлов + integration 1), mypy + ruff clean.
- Decisions/deviations: см. ADR 0018. Wiki ↔ code count discrepancy (28 vs 29) обнаружено и исправлено в S4 — code был всегда корректен.

## [2026-04-23] ingest | Caveman plugin integrated (Layer 4b active)
- Installed: caveman@caveman v84cc3c14fa1e (local scope, AI_Traiding_Bot project) — 5 sub-skills (caveman, caveman-commit, caveman-review, caveman-help, compress) + 3 commands (/caveman, /caveman-commit, /caveman-review) + 3 hooks.
- Modified (wiki): llm-wiki/CLAUDE.md — Layer 4b расширен с 3 до 4 meta-skills + caveman-specific правило для subagent briefs ("DO NOT compress technical specs"); удалён из Defer registry; cleanup history дополнен install metadata.
- Activation: `/caveman lite|full|ultra` per session. Auto-skips code blocks, commits/PRs, security warnings, irreversible actions, multi-step procedures.
- Boundary: для subagent briefs со спеками (Kelly формулы, Wilder α=1/n, миграции SQL, look-ahead invariants) — пиши brief в нормальном режиме и помечай `DO NOT compress technical specs below`. Briefs > 200 слов проходят через L4b prompt-master, не caveman.

## [2026-04-23] review | Sprint 4 domain-reviewer fixes (quant-stats + trading-logic)
- Reviewers: quant-stats-reviewer (opus) + trading-logic-reviewer (opus), parallel dispatch на коммиты `01c6b3f` (CB Task 9) + `df4e4e5` (RiskManager Task 12).
- **Quant-stats — 2 must-fix, обоих закрыт:**
  1. `src/risk/kelly.py:120,122` — `Decimal(str(f * 0.25))` делал float×float multiply ДО Decimal cast (нарушает ADR 0007). Fix: `Decimal(str(f)) * Decimal("0.25")`, затем `.quantize(Decimal("1e-10"))` чтобы убрать унаследованный IEEE noise. Tests: `test_phase{3,4}_decimal_no_float_contamination`.
  2. `src/risk/manager.py:184-185` — SL/TP формулы LONG-only без explicit gate; `ENTRY_LONG_TREND_FOLLOWING` hardcoded. Fix: explicit `ValueError if signal.side != LONG` в начале `assess()` (per ADR 0018 sub-decision 1, v0.1 FSM = LONG+FLAT). Test: `test_assess_rejects_non_long_signal`.
- **Trading-logic — 1 BLOCKER, закрыт:**
  - `src/risk/manager.py::update_equity` — invariant #5 ("equity snapshot + state в одной транзакции") нарушен: `EquityTracker.record` коммитил INSERT, потом `StateRepository.update_many` открывал отдельную транзакцию. Fix: добавлены `record_no_commit` / `update_many_no_commit` методы; `update_equity` оборачивает оба в один `with self._conn:` блок. Test: `test_update_equity_atomic_rollback_on_state_failure` (monkeypatches inner write to raise, asserts equity rollback).
- **Trading-logic — 2 concerns, закрыты:**
  - `src/risk/manager.py:175` — qty quantize использовал default ROUND_HALF_EVEN. Bybit Spot BUY rounding rule = step-floor. Fix: `quantize(..., rounding=ROUND_DOWN)`. Test: `test_qty_quantize_rounds_down`.
  - `src/risk/manager.py:67-71` — `load_state` восстанавливал halt level, но не `_prev_close` → flash CB пропускал первый bar после restart. Fix: `on_bar_close` персистит `risk:cb:prev_close` в state; `load_state` восстанавливает. Tests: `test_on_bar_close_persists_prev_close`, `test_load_state_restores_prev_close`.
- Modified (wiki): risk-manager.md (decision pipeline 12→13 шагов с FSM gate + ROUND_DOWN; invariants table расширен с 6 до 9; state schema детализирована с prev_close ключом); 0018-sprint-4-risk-decisions.md (added sub-decisions 6, 7, 8 с code refs + tests).
- Verification: 315 tests passing (308 → +7 новых), mypy clean.
- Pending от trading-logic (HIGH-3 NOT addressed): `bar: object` loose typing в `on_bar_close` — defer до S5 (когда определится Bar контракт через MarketData ACL); `b = float(avg_win/avg_loss)` precision на cents — flag для S7 backtest review.
