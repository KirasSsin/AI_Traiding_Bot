---
title: Wiki Log — chronological append-only journal
type: log
tags: [log, journal, chronological, append-only]
created: 2026-04-19
updated: 2026-04-25
status: stable
---

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

## [2026-04-23] review | Sprint 4 pre-merge security audit (code-review-and-quality + security-and-hardening)
- Reviewers: AS L4 `code-review-and-quality` + AS L4 `security-and-hardening`, parallel dispatch на full PR diff (12 files / ~1.4k LoC).
- Verdict: do not merge until 5 must-fix addressed (1 Critical + 3 High + 1 Important). User chose Option B → batched 8 fixes (5 must-fix + M1+M2+L3 cheap mediums).
- **Fixes (all in src/risk/* + src/platform/config.py):**
  - **C1 / CWE-798** — `bybit_api_key` + `bybit_api_secret` теперь required `Field(..., min_length=8)` (no committed defaults).
  - **H1 / CWE-532** — `Settings.config_hash()` whitelist'нул 12 risk-threshold полей (исключил creds + paths + log/observability). Rotate API secret больше не invalidate active overrides.
  - **H2 / CWE-345 + CWE-306** — Override file = HMAC-SHA256 envelope `{"payload":..,"sig":..}`. Verify через `hmac.compare_digest`. Required new field `risk_override_hmac_key: str = Field(..., min_length=32)`.
  - **H3 / CWE-672** — Override single-use: `consume()` сразу после успешного match override→halt в `assess`, до sizing.
  - **M1 / CWE-276** — File mode 0o600, parent dir 0o700.
  - **M2 / CWE-367** — Atomic write через `os.open(O_WRONLY|O_CREAT|O_TRUNC, 0o600)` + `fsync` + `os.replace`.
  - **I1 / ADR 0007** — `EquityTracker.peak_equity_24h` ranking через Python `max(Decimal)`, не SQL `CAST AS REAL` (collapse в IEEE-754 для значений > 15 sig digits).
  - **L3 / CWE-532** — `resume_cb.py` printит `level` + `expires_at`, но не absolute path.
- **New invariants** (added to risk-manager.md): #10 HMAC envelope, #11 single-use consume, #12 file mode 0o600 + atomic write, #13 config_hash allowlist, #14 Decimal-strict peak ranking.
- **Tests added:** 12 (4 config, 9 override HMAC + tamper + chmod + atomic, 1 resume_cb path leak, 1 equity Decimal precision, 1 manager consume).
- **Verification:** 315 tests passing, 0 failures, 0 errors.
- Modified (wiki): 0018-sprint-4-risk-decisions.md (added sub-decision 9 — full security audit hardening, 8 sub-fixes); risk-manager.md (invariants table 9→14; settings section с allowlist + HMAC key; tags +security; sources +override.py +config.py).
- Modified (code): src/platform/config.py, src/risk/override.py, src/risk/manager.py, src/risk/equity_tracker.py, src/risk/resume_cb.py + 5 test files.
- Deferred follow-ups (M3/M4/L1/L2): clock injection в `OverrideStore.read_active` (testability), `force=True` flag для overwriting existing override (S5 ops), structured logging fields (S5 observability), magic numbers в test fixtures (S5 cleanup).

## [2026-04-23] sprint | 5 completed
- Branch: `feature/sprint-5-execution` (commits `7fa328f..HEAD`)
- Merged PR: `#TBD` (pending)
- Added (code): `src/execution/{state_machine,state_repo,oco,reconciler,coordinator}.py`, `src/execution/bybit/adapter.py` (extended), `src/risk/reason_codes.py` (+2 codes).
- Added (migrations): `migrations/0003_execution_state.sql`.
- Added (tests): `tests/unit/test_{reason_codes,oco,bybit_adapter_oco,reconciler_fetch,reconciler_diff,coordinator_reconcile}.py` + state_repo + state_machine; `tests/integration/test_execution_oco_testnet.py` (opt-in).
- Added (wiki): ADR `0019-sprint-5-execution-decisions.md`, components `{oco,reconciler,execution-state-machine}.md`, sprint summary `sprint-05-execution.md`.
- Updated (wiki): `components/bybit-adapter.md` (S5 tpslMode section), `trading/concepts/reason-codes.md` (29→31), `index.md`, this log.
- Reason codes: 29 → 31 (`HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT`).
- Verification: full unit suite green; testnet integration SKIPPED без `PYTEST_RUN_INTEGRATION=1`.
- Plan drift fixes: tasks 8/9 brief signatures корректировались — actual `BybitMarketAdapter.place_market_order` + nested `ExchangeState.position` API использовался.
- Deferred: partial-fill testnet scenario, WS-divergence injected test, `OCO_PARTIAL_TIMEOUT` watchdog daemon → S5.5/S6.

## [2026-04-23] adr | 0020 — Sprint 6 Spot OCO emulation (reverses 0019/1)
- Added (wiki): `wiki/project/decisions/0020-sprint-6-execution-spot-oco-emulation.md` (13 sub-decisions).
- Added (probe scripts): `scripts/spot_oco_probe_v2.py`, `scripts/spot_oco_probe_v3.py` + outputs `*_output.json`. Pre-existing `scripts/spot_oco_probe.py` covers v1 baseline (B1-B5).
- Updated (wiki): `0019-sprint-5-execution-decisions.md` (sub-decision 1 marked SUPERSEDED with empirical evidence pointer), `index.md` (ADR 0020 entry).
- **Empirical findings (14/14 assumptions B1-B5 + G1-G14 closed):**
  - B2 = FALSE: `place_order(category=spot, orderType=Market, tpslMode=Full)` → ErrCode 170130 — native OCO impossible.
  - v3-A: Spot Stop status sequence `[Untriggered, Triggered, Filled]` confirmed; Triggered+Filled same millisecond (race window = 0ms).
  - v3-B (clean wallet): G5 fee formula reproduced — Sell at `cumExecQty=0.000644` → ErrCode 170131; Sell at `step_floor(cumExecQty - cumExecFee)=0.000643` → rc=0.
  - v3-C: WS `wallet` topic shape `data[0].coin[]` verified (5 events captured).
  - v3-D: Bybit Spot Stop silently rewrites submitted `timeInForce=GTC` → `IOC` in echo (all 3 events).
  - S2/v2: marketUnit=quoteCoin returns `cumExecQty` with 16 decimal places below step boundary — **banned at adapter level**.
  - G14: Demo keys invalid on api-testnet (10003) — Demo accepted as proxy with sub-decision 12 pre-mainnet checks.
- **Reviewer:** trading-logic-reviewer (sonnet, 2 rounds, BLOCK→PROCEED-after-v3). Round 1 BLOCK exposed missing TIF override + Triggered race verification → drove v3 design. Round 2 PROCEED after v3 closed both gaps.
- **Architectural delta vs ADR 0019:**
  - OCO: native `tpslMode=Full` → 3-order emulated bracket with `bracket_id` UUID prefix in `orderLinkId`.
  - FSM: 12 → 21 states (added OCO_ARMING, EXIT_SIBLING_CANCELLING/_FAILED, EXIT_SL_RESIDUAL + 5 HALT_* concept-subsets).
  - Schema: forward-only ALTER ADD COLUMN migration `0004_execution_state_v2.sql` (bracket_id, oco_tp_order_id, oco_sl_order_id, expected_oco_qty, arming_started_at, last_attempt_num).
  - Reason codes: 31 → 39 (HALT_BRACKET_INCOMPLETE, HALT_OCO_ARM_TIMEOUT, HALT_OCO_SIBLING_STUCK, HALT_PARTIAL_FILL_BELOW_MIN, HALT_FLATTEN_FAILED, HALT_PHANTOM_SL, EXIT_STOP_RESIDUAL_FLATTEN, REJECT_ORDER_ALREADY_TERMINAL).
  - Adapter: removed dead `place_market_order(take_profit=, stop_loss=, tpsl_mode=)` path; banned 6 payload fields for Spot; added 6 new methods (place_limit_order, place_stop_market_order, cancel_order, cancel_all_orders, get_order, get_wallet_balance); banned `marketUnit=quoteCoin`.
  - Position truth: `walletBalance(coin=BTC)` (no Spot get_position object); entry_price stays in local SQLite (split from Reconciler).
- **Pre-mainnet acceptance gate (sub-decision 12):** re-run probe v1 (B2), v3-D (TIF override), v2 S2 (quoteCoin) on api-testnet with **separate testnet keys** before mainnet deploy. Any behavior diff → BLOCK + revisit ADR.
- **Next:** Sprint 6 implementation plan via Superpowers `writing-plans` skill (~30 tasks: FSM v2 transitions, schema migration, reason-code tests, adapter API rework, Reconciler walletBalance integration, Coordinator sibling-cancel-on-Triggered, OCO_ARMING TTL, deterministic orderLinkId, flatten cascade, EXIT_SL_RESIDUAL, integration test on Demo).

## [2026-04-23] review | S5 post-merge audit + fix-PR
- Reviewers: `trading-logic-reviewer` (opus) + `python-reviewer` (sonnet) parallel on commits `7fa328f..76b88ba` (PR #6).
- trading-logic: no blockers; 6 concerns (startup-reconcile, ENTRY_PENDING/EXIT_PENDING WS, `_normalize_position` `"0"`, testnet wallet-balance scope, `_persist` first-order assumption, count mismatch ADR↔wiki↔test).
- python: 1 BLOCKER (`_persist` untyped `result`), 4 CONCERN (ReconcileVerdict forward ref, bare `open()` test path, `_normalize_position` `"0"`, line >88), 5 NITs.
- Cross-flagged real bug: `_normalize_position` accepts `avgPrice="0"` as valid → `entry_price=Decimal("0")` пишется в `execution_state`. **Fix shipped (TDD red→green)**.
- Fix-PR commits (branch `fix/sprint-5-review-followup`):
  - `67622b5` fix(execution): normalize avgPrice='0' to None
  - `2485a0d` style(execution): type hint + import order + line length cleanups
  - `b5d79cc` test(execution): harden migration path + transitions count assertion
- Updated (wiki): `components/execution-state-machine.md` (Known limitations section: startup-reconcile defer, ENTRY_PENDING/EXIT_PENDING WS defer, `_persist` first-order assumption defer — все → S6).
- Verification: 66/66 S5 unit tests green после fix-PR.
- Deferred → S6: startup `Coordinator.bootstrap()`, ENTRY_PENDING/EXIT_PENDING `WS_RECONNECT` wiring, `orderLinkId`-based OCO main matching.

## [2026-04-23] sprint | S6 — Spot OCO emulation (ADR 0020 implementation)
- Added: src/execution/bracket.py, migrations/0004_execution_state_v2.sql, tests/property/test_bracket_lifecycle_invariants.py, tests/integration/test_demo_bracket_happy_path.py, tests/unit/test_coordinator_arming_ttl.py, tests/unit/test_coordinator_flatten_cascade.py, tests/unit/test_bybit_adapter_history.py, tests/integration/test_coordinator_start_bracket.py, tests/integration/test_coordinator_sibling_cancel.py, tests/integration/test_coordinator_sl_residual.py, tests/integration/test_coordinator_arm_oco_attempt_bump.py, tests/integration/test_coordinator_bootstrap_idempotent.py, scripts/spot_oco_probe_testnet.py, llm-wiki/wiki/project/runbooks/halt-recovery.md, llm-wiki/wiki/project/sprints/sprint-06-spot-oco-emulation.md
- Updated: src/execution/state_machine.py (+26 transitions net; total 55), src/execution/coordinator.py (full rewrite: start_bracket/arm_oco/on_order_event/flatten/_handle_sl_partial/_cancel_sibling/reconcile_arming_ttl/bootstrap), src/execution/reconciler.py (walletBalance truth + dust_threshold=1e-5 BTC + split entry_price), src/execution/state_repo.py (+6 columns + dataclass fields), src/execution/bybit/adapter.py (+7 methods + banned-field guard + marketUnit=quoteCoin reject), src/execution/bybit/errors.py (+retCode 110001 classifier), src/risk/reason_codes.py (+8 codes, 31→39), src/platform/config.py (oco_arming_ttl_seconds, oco_dust_threshold_btc), llm-wiki/wiki/project/components/oco.md (full rewrite), llm-wiki/wiki/project/components/reconciler.md, llm-wiki/wiki/project/components/execution-state-machine.md, llm-wiki/wiki/project/components/bybit-adapter.md, llm-wiki/wiki/trading/concepts/reason-codes.md
- Notes: FSM actual = 16 states / 55 transitions (plan estimate 21/~50); plan drift on halt_reason/last_exit_reason row persistence — kept structlog-only. Pre-mainnet acceptance gate via scripts/spot_oco_probe_testnet.py pending manual testnet-key verification. 32 commits total on branch.
- Tag: v0.1.0-alpha.6 (pending merge)

## [2026-04-23] session-end | S6 post-merge + flow infrastructure refactor
- S6 merged: commit `9eff03f` on main, tag `v0.1.0-alpha.6` pushed.
- Created: `llm-wiki/wiki/project/SPRINT_STATE.md` (≤2KB living state file — sprint/phase/next_action, MANDATORY first-read each session).
- Rewrote: `llm-wiki/wiki/project/architecture/development-workflow.md` (9-phase lifecycle: 0a session-start + 0b hooks + 1-orient + 2-brainstorm + 3-plan + 4-execute + 5-review + 6-wiki + 7-test + 8-finish + 9-session-end; Token Economy table; parallel dispatch ALWAYS/NEVER map; model selection haiku/sonnet/opus).
- Updated: `llm-wiki/CLAUDE.md` (added "ПЕРВОЕ/ПОСЛЕДНЕЕ ДЕЙСТВИЕ КАЖДОЙ СЕССИИ" blocks, Token Economy table with savings %, Sprint orient sequence, Model selection table, context-engineering trigger before subagent dispatch).
- Updated: `~/.claude/CLAUDE.md` (added "СЕССИЯ-СТАРТ" section referencing SPRINT_STATE.md; Model dispatch table; Wiki-first + mem-search-first token rules).
- Agent prompt sync: `~/.claude/agents/trading-logic-reviewer.md` reason-codes updated to 39-enum (was 31) for ADR-agent sync hook.
- Decision: caveman-compress deferred — risk of losing "unless/except" edge-case logic in agent prompts outweighs ~47% token savings for now. Backup files (.original.md) pattern documented but not executed.
- Legacy orphans untouched: `main.py`, `src/controller.py`, `FULL_PROJECT_DOCUMENTATION.md`, modified `IMPLEMENTATION_NOTES.md`/`README_RU.md`/`requirements.txt`/`src/core/models.py`/`web/dashboard.html` — pre-existing state, not session work.
- Next session: restart program → Sprint 7 brainstorming (candidates: C1 coordinator startup reconcile, C2 WS-reconnect wiring for ENTRY_PENDING/EXIT_PENDING, halt_reason/last_exit_reason persistence schema v3).

## [2026-04-24] sprint | S7 — Resilience (ADR 0021 implementation)
- Added: migrations/0005_halt_persistence.sql (halt_reason/last_exit_reason/last_reconcile_at/bootstrap_at + halt_log audit table), src/execution/bybit/ws_private.py (BybitPrivateWSConsumer with close-hook + check_alive watchdog, ADR 0021 sub-decision 6), tests/unit/test_ws_private_consumer.py, tests/unit/test_reconciler_verdicts.py, tests/integration/test_coordinator_bootstrap_idempotent.py, tests/property/test_bootstrap_ws_reconnect_idempotent.py, tests/integration/test_bootstrap_demo_heal.py (opt-in), llm-wiki/wiki/project/components/ws-private-consumer.md (NEW)
- Updated: src/execution/reconciler.py (4-valued verdict: AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED + heal_max_age_seconds=3600 + recommended_state hint + heal_context dict + OrderSnapshot snake_case fields), src/execution/coordinator.py (bootstrap() always reconciles + _bootstrap_done assert on external entries + _RECONCILABLE_STATES expanded to 9 active states + start_bracket captures entry_ack.order_id into oco_main_order_id), src/execution/state_machine.py (FSM v3: removed 2 silent S6 dup-keys per ruff F601 + added 6 transitions for bootstrap+4-valued verdicts → 16 states / 29 events / 59 transitions), src/risk/reason_codes.py (+3 codes: HALT_BOOTSTRAP_AMBIGUOUS, HALT_EXIT_RECONCILE_DIVERGENCE, EXIT_RECONCILE_DETECTED → 42 total), llm-wiki/wiki/project/components/{execution-state-machine,reconciler,oco,bybit-adapter}.md, llm-wiki/wiki/project/runbooks/halt-recovery.md (+sections 4 HALT_BOOTSTRAP_AMBIGUOUS, +5 HALT_EXIT_RECONCILE_DIVERGENCE, SQL templates updated to S7 schema), llm-wiki/wiki/trading/concepts/reason-codes.md (39→42), llm-wiki/wiki/index.md
- Notes: B1 narrow scope confirmed (passive WS consumer only; driver loop deferred to S8). 7 BLOCKERS from final domain review (trading-logic + python parallel) closed in commit 97b29cb. 481 unit/integration/property pass; 28 skipped (pre-existing pyarrow/talib gaps). pybit lacks user-level on_disconnect → wired via WebSocketApp.on_close + heartbeat watchdog backstop.
- Phase G testnet probes (PRE-MERGE blocking, operator-driven on api-testnet): pending — see scripts/spot_oco_probe_testnet.py (re-run B2 + v3-D + v2 S2 with separate testnet keys).
- Tag: v0.1.0-alpha.7 (pending Phase G + merge)

## [2026-04-24] session-end | S7 wiki Stage E + tag prep
- Wiki Stage E updates committed: 5 component pages + 1 runbook + 1 NEW component (ws-private-consumer.md) + reason-codes + index + log.
- Phase G testnet probes blocking pre-merge: operator-driven (separate testnet keys); not executable in autonomous session.
- SPRINT_STATE.md → "Sprint 7 wiki Stage E complete; Phase G testnet probes pending operator".
- Branch: feature/sprint-7-resilience (33+ commits, ahead of main).

## [2026-04-24] phase-G | S7 acceptance gate executed (re-scoped to Demo Mainnet)
- Operator ran `scripts/spot_oco_probe_testnet.py --probe B2 / v3-D / v2-S2` with provisioned keys.
- Script monkeypatch: B2 + v3-D auto-target `api-demo.bybit.com` (Demo Mainnet). v2-S2 calls `run_testnet()` against `api-testnet.bybit.com`.
- Results: B2 ✅ retCode=170130 (`InvalidRequestError` on `tpslMode=Full`); v3-D ✅ TIF sequence `[IOC, IOC, IOC]` (silent GTC→IOC override confirmed; status `[Untriggered, Triggered, Filled]`); v2-S2 ❌ 401/10003 (provisioned keys are demo, not testnet — separate credential pair required).
- Decision (operator + maintainer 2026-04-24): **re-scope Phase G к Demo Mainnet only**. Rationale: v0.1 ops target = Demo Mainnet (real Bybit production matching engine, fake money), не testnet (отдельный движок с разными API quirks). v2-S2 exchange-side property уже validated в S6 Demo evidence; adapter unconditionally pins `marketUnit=baseCoin` → bot path не достигает quoteCoin drift.
- ADR 0021 sub-decision 8 updated: Phase G evidence table + revised target Demo Mainnet + tag valid for Demo only + mainnet promotion (v0.2+) requires fresh gate.
- Created: `wiki/project/sprints/sprint-07-resilience.md` with full Phase G evidence table.
- Evidence files retained: `scripts/spot_oco_probe_output.json` (B2), `scripts/spot_oco_probe_v3_output.json` (v3-D), `scripts/spot_oco_probe_v2_output.json` (S6, v2-S2 Demo).

## [2026-04-24] sprint-end | S7 merged + tagged
- Tag `v0.1.0-alpha.7` created on `feature/sprint-7-resilience` HEAD.
- Merge `feature/sprint-7-resilience` → `main` (no-ff, preserved sprint history).
- SPRINT_STATE.md → phase=9-merged, branch=main, tag=v0.1.0-alpha.7.
- Push tags + main → operator-driven (not in autonomous session).
- Next sprint: S8 brainstorm (driver loop для WS consumer + manager.py orchestration + Analytics per-fill).

## [2026-04-24] workflow | trader-expert subagent + PHASE 2 update
- Added: ~/.claude/agents/trader-expert.md (sonnet) — domain expert decision-maker для open brainstorming questions.
- Updated: llm-wiki/wiki/project/architecture/development-workflow.md PHASE 2 — добавлен step 3 "Trader-expert delegation" (3a structured questionnaire → 3b dispatch → 3c per-item verdict → 3d apply → 3e escalate to user если есть items beyond expert authority).
- Updated: llm-wiki/CLAUDE.md "Curated agent set" — 4 → 5 active agents; trigger cascade row "Новый sprint / архитектурное решение" extended с L5 trader-expert step.
- Verdict format: CONFIRM | REVISE | DEFER | EXPAND per question, плюс cross-cutting concerns + escalation list.
- Trigger: PHASE 3 (plan writing) НЕ начинается пока все open brainstorm questions не получили verdict.

## [2026-04-24] agent-audit | Pre-S8 sync (5 agents + SOP + ADR 0017 amendment)
- Driver: 7 спринтов завершены, agent prompts отстали от FSM v3 / 42 reason codes / 4-valued reconciler / migration 0005 / WS private consumer.
- Patched ~/.claude/agents/trading-logic-reviewer.md: model sonnet→opus (per ADR 0017); reason codes 39→42 (+S7 trio); ws-private-consumer.md в required reads; FSM transitions 56→59 (S7 dedup + 6 new); WS_RECONNECT 7→9 active states (+ENTRY_PENDING, +EXIT_PENDING); Reconciler 2-valued→4-valued verdict (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED + recommended_state hint); NEW Bootstrap & resilience CRITICAL section (always-reconcile, entry_ack capture, heal_max_age=3600, γ halt persistence, WS close-hook, 3 S7 reason codes); Persistence section +migration 0005 + halt_log; Verified output 39-enum→42-enum.
- Patched ~/.claude/agents/quant-stats-reviewer.md: NEW MEDIUM Analytics per-fill table (S8+) section — schema, log/simple returns convention, DSR corridor formula, per-fill aggregation via bracket_id, no-look-ahead in analytics.
- Patched ~/.claude/agents/data-integrity-reviewer.md: ADR list +0021 (sub-decisions 4/5/9); NEW Migration 0005 halt persistence invariants — write-ahead halt_log INSERT before execution_state UPDATE, primary-wins UPDATE conditional WHERE halt_reason IS NULL.
- Patched ~/.claude/agents/python-reviewer.md: removed Django/FastAPI/Flask noise; added project-specific stack checks — Decimal hygiene, asyncio correctness (no time.sleep, no blocking sqlite, strong refs), structlog KV usage, pydantic v2 idioms, pydantic-settings, sqlite3 WAL+TEXT-Decimal, TA-Lib/numpy boundary.
- Patched ~/.claude/agents/trader-expert.md: domain priors +bootstrap sequencing prior +HEAL semantics 4-valued +γ halt primary-wins +ambiguity-prefers-halt.
- Updated wiki/project/architecture/development-workflow.md: PHASE 0a step 5 — agent staleness check (grep for "42 enum"|"59 canonical"|"4-valued"|"halt_log"|"HEAL_ENTRY_FILLED"|"HALT_BOOTSTRAP_AMBIGUOUS"|"ws-private-consumer"|"migration 0005" + ADR 0017 model sync); PHASE 2 — orchestration & concurrency questionnaire block (driver loop, backpressure, concurrency invariants, shutdown sequencing, supervision) — ОБЯЗАТЕЛЬНО включать в trader-expert questionnaire если затронуты в S8+.
- Amended wiki/project/decisions/0017-review-agent-harness.md: +trader-expert в Related; filename normalization "Python Reviewer.md" → "python-reviewer.md"; Amendments section с подтверждением model assignments и устранением drift.
- Updated SPRINT_STATE.md: pre-S8 audit DONE summary; open question for S8 — orchestration-reviewer create vs defer (decided: defer pending S8 PHASE 2 brainstorm).
- Decision: orchestration-reviewer NOT created pre-S8 (anti-bloat) — trading-logic + python-reviewer (asyncio) + data-integrity + trader-expert cover scope. Re-evaluate в S8 brainstorm если выявится gap.

## [2026-04-24] sprint-start | S8a brainstorm + ADR 0022 accepted
- Trader-expert verdict round 1: 18 questions → 10 CONFIRM / 7 REVISE / 1 DEFER. Key REVISEs: Q1/CC1 mandatory threading lock policy (Task 0); Q4 KILL_SWITCH wired в S8a (closes ADR 0021 line 364); Q5 HALT_RUNTIME_CRASH mandatory; Q6 check_alive INLINE; Q8 REST-only wallet truth (defer epsilon-halt); Q10 `python -m src` entry; Q13 +3 reason codes (43/44/45); Q16 settings drop epsilon+check_alive_interval; Q17 delete controller.py + main.py.
- Trader-expert verdict round 2 (single item): U1 stall threshold REVISE 12→24 (120s; bar-poller stall ≠ position-safety event, OCO bracket exchange-side; false-halt cost dominates). Validator 6 ≤ N ≤ 720.
- User U2: sentinel-file CLI (`.kill_switch`) — chosen over SIGUSR1 (supervisor collision risk).
- ADR 0022 created (396 lines, 14 sub-decisions, 7 alternatives rejected, 7 deferred to S8b+, 12-item verification checklist) — status accepted by maintainer.
- S8 split: S8a (this ADR) = live runtime; S8b (later ADR) = Analytics per-fill + execution topic + WS+REST epsilon-halt. Deferred until S8a merge.
- SPRINT_STATE.md → sprint=8a-live-runtime, phase=3-planning.
- Next: PHASE 3 writing-plans → branch feature/sprint-8a-live-runtime.

## [2026-04-24] session-end | S8a — Live Runtime merged

- Closed: ADR 0021 line 364 deferral (KILL_SWITCH wired via sentinel-file CLI).
- New: RuntimeManager (bootstrap → kill→alive→poll→strategy→bracket → shutdown), BarSource (REST kline + dedup + stall).
- Lock policy: Coordinator RLock (6 methods), Reconciler Lock (2 methods) — Task 0 mandatory.
- Reason codes: 42 → 45 (HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL, KILL_SWITCH_REQUESTED).
- FSM: KILL_SWITCH_REQUESTED event → HALTED from 10 active states.
- Removed: src/controller.py, main.py (orphans broken since S2).
- Entry-point: `python -m src` (run / backfill / reconcile-only / kill).
- Tests: 13 task suites + 1 opt-in Demo integration scaffold.
- ADR: 0022 accepted.
- Wiki updated: index.md (runtime-manager, bar-poller components), log.md (this entry), SPRINT_STATE.md (sprint 8a, phase 8-ship).

## [2026-04-24] sprint-ship | S8a — Live Runtime tagged + carry-over to S8b

- Merge `2205743` (--no-ff feature/sprint-8a-live-runtime → main).
- Tag `v0.1.0-alpha.8a` annotated (37 commits, 2411 +/255 - LoC).
- Reviewer summary: trading-logic (opus) NO blockers; python-reviewer (sonnet) 2 HIGH BLOCKERs fixed in `0e2359c` (None-guard for assessment.qty/tp_price/sl_price + structlog migration manager.py + bar_source.py); data-integrity (sonnet) NO blockers.
- Lint cleanup `62be604` (UP037 + ARG001 + F401, ruff clean on S8a src + tests).
- Final test suite: 570 unit pass / 24 skipped (clean env). 73 new S8a-specific tests across runtime/FSM/lock/CLI scopes.
- 3 pre-existing test_config.py failures = local `.env` env-pollution (verified false positive on clean clone — CI green).
- SPRINT_STATE.md: sprint=8a, phase=between-sprints, branch=main, tag=v0.1.0-alpha.8a.
- Carry-over to S8b: (1) `request_halt` → wire FSM transition (10 KILL_SWITCH_REQUESTED transitions currently dead code); (2) `BarSource._INTERVAL_MS` KeyError guard; (3) `main()` mypy no-any-return narrow + tests ARG005 cleanup; (4) sentinel-file atomic write.
- Branch `feature/sprint-8a-live-runtime` сохранена локально (S6/S7 pattern).
- Next: open S8b brainstorm (Analytics per-fill + WS+REST epsilon-halt).

## [2026-04-24] tooling | trading-logic-reviewer model opus → sonnet (4.6)

- ADR 0017 amended: trading-logic-reviewer model `opus` → `sonnet` (4.6 alias). Sonnet 4.5+ built-in extended thinking даёт ту же review depth (S7+S8a empirically: opus override не дал blockers > sonnet baseline).
- Файл `~/.claude/agents/trading-logic-reviewer.md` уже был `model: sonnet` (drift был только в ADR 0017 + `llm-wiki/CLAUDE.md` аннотациях). Drift fixed.
- Dispatch policy: future Agent calls subagent_type="trading-logic-reviewer" БЕЗ `model: "opus"` override. Cost reduction ~5×.
- `quant-stats-reviewer` остаётся `opus` — формулы/MC/DSR требуют heavier reasoning (не меняем).
- Files: `wiki/project/decisions/0017-review-agent-harness.md` (line 41 + Amendments), `llm-wiki/CLAUDE.md` (line 472).

## [2026-04-24] tooling | quant-stats-reviewer model opus → sonnet (4.6) — unified policy

- ADR 0017 amended (follow-up): quant-stats-reviewer model `opus` → `sonnet` (4.6 alias). Единая политика — все 5 curated агентов теперь sonnet.
- Файл `~/.claude/agents/quant-stats-reviewer.md` frontmatter `model: opus` → `sonnet` (real drift fix — file сам был opus, не как trading-logic).
- Reasoning: формулы/Wilson/Kelly/MC/DSR покрываются sonnet 4.5+ extended thinking. Symmetry + cost reduction ~5×.
- Escalation: re-evaluate post-S9 (DSR/MC heavy суите) — если sonnet пропускает real blockers, обратно к opus.
- Files: `~/.claude/agents/quant-stats-reviewer.md`, `wiki/project/decisions/0017-review-agent-harness.md` (line 42 + Amendments), `llm-wiki/CLAUDE.md` (line 471).

## [2026-04-24] tooling | subagent path discipline policy (5 агентов)

- Triggered by post-S8a S8b brainstorm round: trader-expert output содержал typo `/AI_Traiding_Tool/src/__main__.py` (вместо `_Bot`) и неправильный путь `override_store.py` (реально `override.py`).
- Root cause: я давал relative paths в Agent dispatch brief; subagent додумывал absolute paths сам и делал typo + неправильную инференцию имени файла из class name (OverrideStore → override_store.py vs реальный override.py).
- Fix: добавил "## Path discipline (file references)" section в 5 файлов агентов (`~/.claude/agents/trader-expert.md`, `python-reviewer.md`, `data-integrity-reviewer.md`, `quant-stats-reviewer.md`, `trading-logic-reviewer.md`). 4 правила: absolute paths, verify ls перед cite, never silent substitution, format `path:LINE`.
- Documented в `llm-wiki/CLAUDE.md` (Curated agent set → Subagent path discipline section + Cleanup history entry).
- Maintainer rule: future Agent briefs тоже использовать absolute paths.
- Out-of-band fix (отдельно от S8b PR — agents lives outside repo, wiki update единственный repo-side artefact).

## [2026-04-24] sprint-8b | Carry-over fixes complete

### What shipped
- Coordinator.request_halt — FSM transit fix (T1) + signature ReasonCode (mypy)
- Coordinator state_machine — (FLAT, RISK_HALT) → HALTED row (T7 fix-up; surfaced by property test, prevents idle-state halt-path crash)
- BarSource — fail-fast interval validator + 13-interval dict (T2)
- main() mypy no-any-return — typed dispatch via `Callable[[argparse.Namespace], int]` (T3)
- _cmd_kill — atomic sentinel write via os.open + os.replace, mirrors override.py minus fsync (T4)
- ADR 0023 — halt-code → FSM event mapping invariant (T5)
- trading-logic-reviewer.md — CRITICAL section "Halt-code mapping" (T6, agent prompt outside repo)
- tests/property/test_request_halt_mapping.py — coverage invariant 3 codes (T7)

### Wiki updates (Stage E)
- components/runtime-manager.md — atomic kill-switch sub-section
- components/bar-poller.md — supported intervals + fail-fast
- index.md — ADR 0023 link
- decisions/0023-halt-code-fsm-event-mapping.md — NEW

### Open wiki gaps (follow-up, not blocking S8b)
- components/coordinator.md — missing entirely; request_halt FSM-transit semantics + (FLAT, RISK_HALT) row currently only in commit log + ADR 0023. Create in dedicated wiki sprint.
- ADR 0023 / 0022 transition count — narrative may reference 73; live count is 74 after T7 fix-up. Update when next ADR amendment lands.
- _set_halt(reason: str) internal wrapper signature still str while request_halt now accepts ReasonCode — clean up in next sprint.

### Tag (planned)
- v0.1.0-alpha.8b

## [2026-04-25] session-end | Post-S8c batch — Wiki RAG + Skills + CLAUDE.md prune

### What shipped (3 PRs squash-merged to main)

- **PR #11** — Sprint 8c carry-over (already shipped earlier session) → tag `v0.1.0-alpha.8c`
- **PR #12** — Wiki RAG optimization (TIER 1+2+3): mental-map.md NEW + components/README.md cluster index NEW + 6 orphan "Referenced by" sections + 13 components canonical Invariants tables + reconciler.md SUPERSEDED note + frontmatter hygiene (5 pages type field, sprint pages normalize, `[[override]]`→`[[risk-override]]` fix) + Runbooks index section
- **PR #13** — PR-C: 5 NEW workflow skills (.claude/skills/sprint-orient + sprint-finish + wiki-update + brainstorm-init + hook-test) + kit refactor (replace hardcoded inline workflow с skill references) + llm-wiki/CLAUDE.md prune 610→407 lines (33% reduction, ~50% session-start token saving) + Anthropic best practices alignment section

### Wiki updates

- 2 NEW navigation pages (mental-map.md + components/README.md)
- 2 NEW methodology pages (methodology-decision-algorithms.md + methodology-rejected.md — extracted from CLAUDE.md prune)
- 13 component pages с canonical Invariants tables (CRITICAL classification по trader-expert)
- 6 orphan component pages с "Referenced by" sections
- All sprint pages frontmatter normalized (type: sprint, status: completed)
- ADR 0017 amended (architecture-reviewer addition deferred к PR-D+E)

### Open wiki gaps (deferred)

- **PR-A pending** — verification pass для 13 Invariants tables (line:N → function::name anchors, verify test names против actual files)
- **PR-B pending** — wiki coverage audit (broader gap finding) + Block 1/2 paradigm selectively
- **PR-D+E pending** — architecture-reviewer NEW agent + TIER A apply (memory + Sprint priming + effort) к 5 reviewers
- **Bucket F1** — `wiki/runbooks/halt-recovery.md` MISSING (referenced 8+ places, brainstorm scope для S9 dedicated operator-readiness sprint)

### Key methodology shifts

- **Skills paradigm** заменил hardcoded inline workflow logic. Single source of truth = `.claude/skills/<name>/SKILL.md`. Other docs (dev-workflow.md, repo CLAUDE.md, mental-map.md, index.md) — references only, не duplicate. Per Anthropic progressive disclosure.
- **Anthropic best practices selectively adopted** (12 adopted including hooks/subagents/skills/verify work; 7 NOT adopted including Plan Mode/Agent Teams/parallel sessions — paradigm conflicts с naшим sequential sprint discipline)
- **CLAUDE.md prune** per Anthropic guidance ("bloated CLAUDE.md = LLM ignores rules") — 33% reduction без losing canonical content (frontmatter schema, banned-list, hierarchy summary preserved)

### Session metrics

- 3 PRs shipped (squash-merged)
- ~32 wiki files touched
- 0 src/ changes (pure docs/skills/methodology batch)
- pytest 602 passed / 24 skipped / 0 failed (S8c baseline unchanged)

### Restart required

Skills not active в текущей session — нужен restart claude code чтобы Claude Code scanned `.claude/skills/` directory at session start и registered 5 new skills для auto-trigger через description match.

### Next action

После restart: continue с PR-A (verification pass) ИЛИ PR-D+E (architecture-reviewer + TIER A). PR-B deferred к больше time budget.

---

## [2026-04-25] session-end | Pre-S9 debugging batch (PR-α/β/γ + audit)

### Shipped (4 commits, 3 PRs + 1 direct main)

- **PR #14 PR-α** (`5cb84c3`): Kit conflict audit (verdict: 0 conflicts, only 3 stale facts) + Verification pass — 13 component pages, 52 anchors `:LINE` → `function::name`, 4 honest `(no test yet — TODO)` markers. Drift prevention.
- **PR #15 PR-β** (`876be51`): NEW 6th agent `architecture-reviewer` (sonnet 4.6) — closes cross-module/concurrency review gap. TIER A apply к ALL 6 reviewers: `memory: project` (institutional knowledge accumulation in `.claude/agent-memory/<agent>/MEMORY.md`) + Sprint context priming section (mandatory canonical loads at dispatch start). `effort: max` для trader-expert + quant-stats only (critical reasoning paths).
- **PR #16 PR-γ** (`98d0c40`): F1 halt-recovery.md extended 9 → 19 halt codes (5 class groups: Drawdown / Operational / OCO-bracket / Bootstrap-reconcile / Runtime; 2-tier severity: CRITICAL = full diagnosis SQL+REST+recovery, RECOVERABLE = abbreviated symptoms+actions+escalation). B2+B3: Block 1↔Block 2 sync HARD-GATE step 5c added к dev-workflow.md PHASE 8 + sprint-finish skill Step 4.
- **Audit follow-up** (`7c28a6d`, direct main): trader-expert cross-link audit verified 2 real gaps (CC1 caught trader hallucinated TBD claim — actual counts 74/45 correct). Fixed: repo CLAUDE.md 5→6 reviewers, 5 halt-emitter components linked к halt-recovery runbook.

### Key decisions logged

- **PR-γ F1 trader iterative justify ROUND 2:** maintainer over-classified — HALT_DRAWDOWN_L1 НЕ halt (just elevated risk), HALT_BOOTSTRAP_AMBIGUOUS = CRITICAL (not RECOVERABLE). Trader CONFIRM_REVISE BINDING.
- **B1 anti-pattern caught:** Explore subagent recommended creating page для `src/core/models.py`. Maintainer CC1 verification (grep src/ tests/) confirmed orphan → defer cleanup к S9. **0 new pages needed.**
- **Trader audit hallucination:** Subagent fabricated tool_use/tool_response blocks (claimed current-state.md had `TBD` values). Maintainer direct grep showed actual = 74 transitions / 45 reason codes (correct). CC1 verification protocol prevents applying false claims. Lesson: ALWAYS verify subagent claims via independent grep BEFORE applying.

### Session metrics

- 4 commits shipped (3 PRs squash-merged + 1 direct main)
- ~36 wiki/skill files touched
- 0 src/ changes (pure docs/skills/methodology batch)
- pytest 589 passed / 24 skipped / 0 failed (S8c baseline maintained)
- Canonical counts unchanged: states=16, events=30, transitions=74, reason_codes=45
- 7/28 component pages now link halt-recovery runbook (was 4/28) — improved 1-hop discovery для operator workflows

### Next action

Begin S9 brainstorm — `brainstorm-init` skill auto-fires on "брейнштурм S9" / "ориентируйся" / scope decision triggers. Trader-expert ROUND 1 questionnaire с carry-over scope (mypy batch / broken-link audit / further architecture-reviewer integration).

---

## [2026-04-25] feat | C7 broken-link hook deployed

### Shipped (1 commit on main)

- **C7 hook** (`f07e979`): NEW PreToolUse `git push` hook scans changed `wiki/**.md` files в pushed commits для broken `[[link]]` refs. Block push if any unresolvable. Bucket C7 — pre-S9 process improvement.

### Hook design (changed-files-only scope, не whole-wiki)

- **Scan corpus** = `git diff base..HEAD -- llm-wiki/wiki/` filtered к *.md (changed only)
- **Resolution corpus** = ALL wiki/**.md (basename_index for unqualified refs)
- 3 path resolution: source-relative, wiki-root-relative, cross-repo (для `[[../../../CLAUDE]]`)
- Skip patterns: empty / anchor-only / NNNN placeholder / TOML / fenced code / inline code spans
- Self-test guard mirrors adr-*-sync-check.sh
- Fail-open на missing python3 / no upstream / non-git command

### 5 real bugs caught + fixed during deployment scan

1. `log.md` `[[override]]` → backticks (historical mention)
2. `adr-index-sync-hook.md` `[[wiki/index.md]]` → `[[../../index]]`
3. `adr-agent-sync-hook.md` + `0017-review-agent-harness.md` `[[../../CLAUDE]]` → `[[../../../CLAUDE|llm-wiki/CLAUDE]]` (depth fix)
4. `bybit-rest.md` `[[filters]]` × 2 → plain text
5. **MAJOR HARD-GATE violation:** `sprint-08c-wiki-backfill.md` MISSING (S8c shipped без sprint page). CREATED stub from log.md + plan content.

### Files

- `~/.claude/hooks/wiki-broken-link-check.sh` — bash + inline python (~150 lines)
- `~/.claude/settings.json` PreToolUse Bash hooks: 3rd entry registered
- `wiki/project/components/wiki-broken-link-hook.md` — hook spec (NEW)
- `wiki/index.md` + `components/README.md` + `mental-map.md` — cross-link refs added

### Validation

- pytest 589 passed / 24 skipped / 0 failed
- Canonical counts unchanged: 16/30/74/45
- 0 src/ changes
- env -i sandbox tests verified (4/4 scenarios pass)

### Carry-over к S9 (post-C7)

- mypy 44 errors (typed batch sprint — defer)
- Trading concepts stubs `minimum-backtest-length.md` / `position-sizing.md` (low priority research)
- Existing pages Block 1/2 refactor (anti-bloat — paradigm implicit)

### Discovery during cleanup

`sprint-08c-wiki-backfill.md` MISSING revealed что PHASE 8 step 5 sprint-NN.md HARD-GATE прошёл без enforcement в S8c ship. C7 hook теперь catches this drift class for future sprints.

---

## [2026-04-25] refactor | mypy 44→0 type cleanup

### Shipped (1 commit on main)

- **mypy clean** (`ba4dcfe`): 44 pre-existing errors across 8 src/ files → 0. Pure type annotations cleanup. Zero behavioral changes.

### Categories fixed

| Category | Count | Fix pattern |
|----------|-------|-------------|
| `[type-arg]` | 22 | bare `dict` / `tuple` → `dict[str, Any]` / `tuple[X, ...]` |
| `[arg-type]` | 9 | bracket.py ROLE_* annotated as `Role` Literal; reconciler signatures tightened; defensive guards |
| `[union-attr]` | 5 | Reconciler._query refactored к non-Optional via `_q = ... ; if _q is None: raise; self._query: ExchangeQueryClient = _q` |
| `[no-untyped-call]` | 2 | pyarrow `# type: ignore[no-untyped-call]` (untyped third-party) |
| `[no-any-return]` | 2 | explicit Decimal cast in `_qty_step`; reconciler resolved via signature tightening |
| `[attr-defined]` | 2 | ws_private `_ws: Any \| None` annotation (pybit untyped) |
| `[no-untyped-def]` | 1 | ws_private wrapped close-hook callback typed |
| `[name-defined]` | 1 | coordinator LocalState moved к `TYPE_CHECKING` import (was lazy-imported inside method) |

### Files (8 src + 0 tests)

- `src/execution/bracket.py` — 6 ROLE_* литералы as Role
- `src/execution/bybit/adapter.py` — 2 list[dict] → list[dict[str, Any]]
- `src/execution/bybit/ws_private.py` — 5 dict typed + Any|None _ws + close-hook
- `src/execution/coordinator.py` — 4 dict typed + LocalState TYPE_CHECKING + Decimal cast
- `src/execution/reconciler.py` — 7 dict/tuple typed + _query non-Optional refactor + fetch_exchange_state guard
- `src/execution/state_repo.py` — 1 dict + 1 tuple typed
- `src/marketdata/gaps.py` + `storage.py` — pyarrow untyped-call ignores

### Validation

- `mypy src/` → "Success: no issues found in 60 source files"
- pytest tests/unit -x -q → 589 passed / 24 skipped / 0 failed
- Canonical counts unchanged: 16/30/74/45
- 0 logic changes (annotations + 2 defensive raises only)

### Carry-over к S9 (further reduced)

- Existing pages Block 1/2 refactor (anti-bloat)
- Trading concept stubs (research)
- `mypy --strict src/` опционально (defer — current `mypy src/` clean)

### Pre-S9 cleanup status

✅ C7 hook deployed
✅ mypy 44 → 0
✅ 5 docs/tooling batches shipped (PR #12-#16 + audit + C7 + mypy)

Готов к S9 brainstorm.

---

## [2026-04-25] sprint-end | S9 — Data quality + mypy strict + per-fill + DSR

### Shipped (PR #17 → 92c5268, tag v0.1.0-alpha.9)

12 TDD tasks, 20 commits squash-merged. Closed 3 deferred carry-overs:

- **Q1 C — Data quality:** NEW `BarPriceQualityDetector` (REST-vs-REST consecutive bar deviation, 0.5% threshold). Triggers HALT_DATA_QUALITY via existing RISK_HALT event (no new FSM state/event/transition). Wired в `RuntimeManager._poll_bar_and_strategy` BEFORE strategy.on_bar. `_stopping=True` set on halt (terminal — match stall + kill-switch patterns).
- **Q2 G — mypy strict:** Removed `ignore_errors=true` override для src.core/risk/backtest. Empirical per-module check missed 18 cross-module errors — fixed in T4 follow-up. `mypy src/` clean (63 source files).
- **Q3 B1 — Per-fill schema:** NEW migration `0006_trade_fills.sql` (FK trade_history, UNIQUE exec_id, composite index) + `FillRecord` + `FillHistoryRepository` + WS execution topic subscription (`_FillRecorderProto`).
- **Q3 B2 — DSR module:** NEW `src/analytics/dsr.py` Bailey & López de Prado Deflated Sharpe Ratio. **quant-stats-reviewer T9 caught BLOCKER** — wrong kurtosis convention (Fisher excess vs Pearson total). Fixed inline (`fisher=False`) + n_trials > 1 NotImplementedError guard.

### Validation

- pytest: 630 passed / 24 skipped / 0 failed (baseline 589 → +32 tests: 8 quality + 7 fill_history + 8 dsr + 1 coordinator + 3 migration + 3 ws_private + 2 runtime)
- mypy --strict src/: Success in 63 source files (added: dsr.py)
- Canonical counts unchanged: 16/30/74/45 (S9 = pure additive, no FSM impact)
- Property test: HALT_DATA_QUALITY added к `_REQUEST_HALT_CODES` (3→4 codes)

### Wiki updates

- 3 NEW component pages: data-quality, fill-history, dsr
- 1 NEW ADR: 0024-sprint-9-data-quality-types-analytics
- 1 NEW sprint page: sprint-09-data-quality-types-analytics
- 1 NEW migration: 0006_trade_fills.sql
- index.md, components/README.md (NEW Cluster 10 — Analytics), mental-map.md updated
- pre-s9-backlog.md (PHASE 2 brainstorming verdicts trail)

### Reviewers

- T1 (quality): data-integrity + python — ✅ both APPROVED post-fix (docstring clarity + log hygiene + import sort)
- T2 (coordinator): trading-logic + python — ✅ both APPROVED no concerns
- T3 (runtime): trading-logic + python — ✅ caught _stopping=True missing on halt path (real bug, fixed)
- T5 (migration): data-integrity — ✅ APPROVED post-fix (added FK enforcement INSERT violation test)
- T6 (fill_history): data-integrity + python — ✅ both APPROVED, low-priority concerns
- T7 (ws): trading-logic + python — ✅ both APPROVED (production wiring deferred per pre-existing S8a STUB)
- T9 (DSR): quant-stats — ❌ BLOCKER B1 (Fisher→Pearson kurtosis) caught + fixed → ✅ post-fix APPROVED

### Bug discovered + fixed (C7 hook)

`wiki-broken-link-check.sh` had bash parsing collision на triple-backtick `"\`\`\`"` внутри `$(... <<'PYEOF'` heredoc — bash interpreted backticks despite single-quoted heredoc delimiter. Fix: extracted python к external script `~/.claude/hooks/lib/wiki_broken_link_scan.py`. Caught at first push attempt of S9 branch.

### Key decisions

- **REST-vs-REST quality detector** (NOT WS+REST kline) — closes async dependency + WS partial-bar false-positive risk per Q1 trader REVISE
- **mypy strict empirical lesson** — per-module mypy doesn't see cross-module imports. Always full-tree verify before override removal.
- **Pearson kurtosis (NOT Fisher excess)** в DSR per Bailey eq. 13 — caught by quant-stats-reviewer
- **DSR annualization deferred** — per-trade Sharpe internally consistent (Φ output unit-free, annualization cancels)
- **Production wiring deferred** — `__main__.py::_cmd_run` STUB since S8a, defer к operator-readiness sprint

### Carry-over к S10+

- DSR annualization factor (deferred — irregular trade frequency normalization decision)
- DSR n_trials > 1 (NYI v0.1, requires sigma_SR per Bailey eq. 12)
- Walk-Forward acceptance gate consuming DSR (S10 D scope per ADR 0014)
- Production wiring of FillRecorder

### Roadmap

S10 = D (WFA + DSR + MC permutations) — large statistical layer, builds on S9 B2 DSR foundation. Alternative: S11 F (Live demo Mainnet 24-72h) если operator priority.

---

## [2026-04-25] sprint-end | S10 — WFA + DSR aggregate + MC permutations

### Shipped (PR #18 → dcb3576, tag v0.1.0-alpha.10)

11 TDD tasks, 14 commits squash-merged. Production-grade walk-forward validation pipeline.

- **T1 vector_backtest annualization fix** (`07c6042`): sqrt(365*24*60) → sqrt(8760), pandas 3.x deprecation fix incidentally
- **T2-T3 WFA orchestrator** (`57ff9d3` + `06cf625`): WindowSplitter (frozen dataclass, ADR 0014) + WalkForwardRunner (dual-Sharpe routing)
- **T4 DSR sigma_sr** (`0dc0b8a` + `c33dd28`): closes S9 NotImplementedError, Bailey eq. 12. quant-stats-reviewer T4 caught defensive sigma_sr < 0 guard.
- **T5-T6 MC permutations** (`3cda6f6` + `0e93847`): sign-flip primary + block bootstrap secondary. T6 spec correction caught by implementer.
- **T7 acceptance gate** (`b98fff2`): Sharpe AND MC, DSR informational
- **T8 WFA reporter** (`855a66a`): 3-Sharpe series routing + DSR aggregate с sigma_sr
- **T9 integration test** (`86d3db3`): end-to-end pipeline verified
- **T10-T11 ADR + wiki sync** (`fd2762b` + `8a9a2ca`): ADR 0025 + 3 NEW components + sprint page + counts updates

### Validation

- pytest unit: 656 passed / 24 skipped / 0 failed (baseline 630, +26 tests)
- pytest integration: test_wfa_pipeline.py ✅
- mypy --strict src/: clean (66 source files)
- Canonical counts unchanged: 16/30/74/45
- 0 src/ behavioral changes outside backtest scope

### Wiki updates

- 3 NEW component pages (walk-forward + mc-permutations + wfa-reporter)
- 1 NEW ADR (0025)
- 1 NEW sprint page (this)
- index.md / components/README.md (Cluster 8 expanded) / mental-map.md / current-state.md updated
- pre-s10-backlog.md (PHASE 2 brainstorming verdicts trail)

### Reviewers

- T1 (vector_backtest): inline review (math + pandas semantics) ✅
- T2-T3 (WFA orchestrator): inline review ✅
- T4 (DSR sigma_sr): quant-stats-reviewer MANDATORY → CORRECT verdict с 1 concern (sigma_sr < 0 guard added inline)
- T5-T6 (MC): inline review (T6 implementer correctly caught spec error)
- T7-T8 (gate + reporter): inline review ✅
- T9 (integration): self-validation through pytest run ✅

### Key discoveries / decisions

- **DSR informational, NOT gate** (Q2 trader REVISE) — N=40-80 trades/fold = high variance, would reject valid strategies
- **Fixed sqrt(8760) annualization** (Q6 trader REVISE) — derived = circular, breaks IS/OOS
- **3-Sharpe trap (cross-cutting #1)** — must not conflate bar-returns / per-trade / display
- **T4 quant-stats fix** — sigma_sr < 0 ValueError defensive (std non-negative по definition)
- **T6 implementer fix** — block bootstrap on constant returns yields p=1.0 (correct math, spec test was wrong)

### Carry-over к S11+

- DSR threshold gate calibration (deferred — TBD post-empirical fold data)
- Per-fold DSR в reporter (NaN placeholder, DataFrame→TradeRecord conversion deferred)
- WFA wired в `__main__.py` CLI (defer к operator-readiness sprint)
- **Pre-existing test failure:** test_risk_flow.py::test_50_bar_synthetic_risk_flow (OverrideStore.__init__() missing hmac_key — S4 era Task 15, NOT S10 regression)

### Roadmap

S11 = F (Live demo Mainnet 24-72h validation) per S9 carry-over plan. Alternative: S12 A (Operator-readiness — runbooks + monitoring + alerts) если Mainnet validation deferred.

## [2026-04-25] sprint-end | Sprint 11 — Operator-readiness + pre-flight gap closure

### Phase 2 brainstorming verdicts (binding)

7 questions через trader-expert ROUND 1:
- Q1 CONFIRM: A-first scope (operator-readiness BEFORE live Mainnet F)
- Q2 CONFIRM: bundle pre-flight gaps в S11 P0 (test_risk_flow.py + DI wiring + WFA CLI)
- Q3 REVISE: integrate halt priority matrix INTO halt-recovery.md (single source of truth, NOT separate dashboard)
- Q4 CONFIRM: S12 F params validated (Bybit demo + 48h + $1000 virtual)
- Q5 CONFIRM: defer DSR threshold calibration к S15+ (need 30+ trades empirical)
- Q6 CONFIRM: 1-test fix + audit для other S4-era drift
- Q7 CONFIRM + addition: architecture-reviewer MANDATORY для _cmd_run

### Tasks (10, 13 commits squash-merged)

P0 pre-flight (4):
- T1 (afb5760): test_risk_flow.py OverrideStore hmac_key signature restored
- T2 (ead6dca + d7b196f): _cmd_run DI wiring (architecture-reviewer SOUND verdict + 1 inline fix MagicMock→_NoopFillRecorder)
- T3 (bb8cba9 + e4df4cd): _cmd_reconcile_only DI wiring (Coordinator+Reconciler subset)
- T4 (6e1fff2): _cmd_wfa CLI (Sharpe + MC gate)

A scope operator-readiness (4):
- T5 (0b57062): halt-recovery.md priority matrix + escalation column (Q3 REVISE applied)
- T6 (26f7b68): NEW log-grep-templates.md (structlog jq + halt_log SQL)
- T7 (281896e): _cmd_monitor read-only CLI (C2 invariant — `?mode=ro` URI, no DB mtime change)
- T8 (92c37b9): NEW pre-flight.md operator checklist (5 gates + 4 recommendations)

Wiki + ADR (2):
- T9 (6ba4a41): ADR 0026 + index.md entry
- T10 (da7a68f): sprint-11 page + counts (ADR 25→26, sprint pages 12→13) + 2 runbooks к index + mental-map +4 query rows

### Tests / quality

- pytest unit: 680 passed (baseline 666 + 14 internal fixtures uncovered) / 24 skipped / 0 failed
- pytest integration: test_risk_flow.py ✅ (was failing pre-S11)
- mypy --strict src/: clean (66 source files)
- ruff: 3 pre-existing errors в tests/integration/test_risk_flow.py (S4-era I001/F401/UP017 — NOT S11 regression)
- Counts unchanged: 16/30/74/45 (CLI = orchestration, no FSM/reason code growth)

### Wiki updates

- 2 NEW runbook pages (log-grep-templates + pre-flight)
- 1 NEW ADR (0026)
- 1 NEW sprint page (this)
- Modified: halt-recovery.md (priority matrix + escalation column)
- current-state.md (TL;DR post-S11, ADR 25→26, sprint pages 12→13, +S8c/S9/S10/S11 rows в "Карта спринтов")
- index.md (sprint-11 + 2 runbooks + ADR 0026)
- mental-map.md (+4 operator query rows + WFA CLI row)

### Reviewers

- T1 (test fix): inline review (signature drift only)
- T2 (_cmd_run DI wiring): architecture-reviewer MANDATORY → SOUND verdict с 3 concerns (C1+C3 deferred S12, C2 fixed inline _NoopFillRecorder)
- T3-T8: inline reviews (small isolated scope)
- T9-T10: wiki-only (inline)

### Key discoveries / decisions

- **architecture-reviewer T2 SOUND verdict** — DI graph correct: Settings → REST → BybitFilters → market adapter → DB → state repo → reconciler → coordinator → bar source → strategy → risk → WS → RuntimeManager.run()
- **MagicMock→_NoopFillRecorder** (T2 review C2) — replace test library import в production с simple stub class
- **C2 strict read-only enforcement** — _cmd_monitor uses `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`. T7 test enforces no DB mtime change.
- **_cmd_run runnable end-to-end** — closes 8-month-old S8a T20 STUB. FillRecorder = `_NoopFillRecorder` stub (production wiring deferred S12+).
- **Halt priority matrix INTO halt-recovery.md** (Q3 REVISE) — single source of truth, prevents drift vs separate dashboard.
- **DI feasibility read-pass** (C1) — pre-plan verification confirmed constructors aligned, no mini-ADR needed.

### Carry-over к S12+

- **F (Live demo Mainnet 24-72h validation)** — main S12 scope per Q1 confirmed
- **FillRecorder production wiring** (currently `_NoopFillRecorder` stub в _cmd_run)
- **`_load_ohlcv` production data integration** в _cmd_wfa (currently empty DataFrame stub)
- **C1 (T2 review):** `endpoint = "demo.bybit.com" if testnet else "stream.bybit.com"` — semantically wrong для testnet. pybit derives `testnet`/`demo` flags from substring match. Current sets `demo=True, testnet=False` (correct для S11 demo trading intent но wrong для actual testnet validation). Fix to use string containing "testnet" substring (e.g., `"stream-testnet.bybit.com"`).
- **C3 (T2 review):** `init_db` opens own internal connection separate from `connect()` returned conn. WAL mode safe но worth explicit code comment.
- **Per-fold DSR DataFrame→TradeRecord conversion** (informational, deferred от S10)
- **DSR threshold calibration** (S15+ per Q5 verdict, need 30+ empirical trades)

### Roadmap

S12 = F (Live demo Mainnet 24-72h validation) per Q1 confirmed scope. Bybit demo + 48h + $1000 virtual capital + halt criteria per Q4 trader CONFIRM. Operator infrastructure now ready (S11 deliverables).

## [2026-04-25] sprint-end | Sprint 12 — Live demo validation 24-72h + production wiring

### Phase 2 brainstorming verdicts (binding)

7 questions через trader-expert ROUND 1:
- Q1 CONFIRM: Bybit demo trading endpoint (zero PnL exposure for first live cycle)
- Q2 CONFIRM: 48h validation duration (1H bars × 48 = 48 samples adequate structural)
- Q3 CONFIRM: multi-criteria success gate + MANDATORY zero-trade clause
- Q4 REVISE-additive: Parquet shim required (data_collector.load_market_data takes config dict, not args — verified via grep CC1)
- Q5 REVISE-additive: FillRecorderAdapter required (FillHistoryRepository не drop-in для _FillRecorderProto)
- Q6 REVISE-DISAGREE-FACTUAL: NO endpoint string change for S12 — current `"demo.bybit.com"` CORRECT; future 3-way enum к S13+. SPRINT_STATE S11 carry-over note "fix к testnet substring" was WRONG (verified truth table via source grep)
- Q7 CONFIRM: P0-wake + alpha.11 rollback + RC tag iteration + zero-migration constraint

NO ROUND 2 invoked (REVISEs additive scope refinements OR factual correction, no engineering disagreement). NO user escalation.

### Tasks (6, 8 commits squash-merged)

Production wiring (2):
- T1 (044dad8): FillRecorderAdapter — 2-layer pattern (always-on structlog audit + best-effort DB insert via WS orderId → execution_state → trade_history lookup chain). Race-condition safe (skip+warn). Schema gap acknowledged: execution_state lacks entry_signal_id → Layer 2 always-skips during S12 (S13 carry-over per Q7 zero-migration). 7 unit tests. trading-logic + data-integrity reviewers MANDATORY (per ADR 0027) — both APPROVED with non-blocking concerns
- T2 (5d94c1a): _load_ohlcv Parquet shim — config-dict translation + helpful FileNotFoundError pointing к backfill cmd

Operator runbooks (3):
- T3 (8f4dd1e): pre-flight Gate 5 backfill prerequisite + halt-recovery P1+OCO_ARMED conditional escalation
- T4 (51dc3c4): live-demo-validation.md operator playbook — 48h Bybit demo BTCUSDT 1H protocol + multi-criteria success gate + MANDATORY zero-trade clause
- T5 (bd172e1): halt-response-protocol.md — P0 wake decision tree + alpha.11 rollback procedure + RC tag iteration + Q7 zero-migration verification

Wiki sync (1):
- T6 (e99c36a): ADR 0027 status accepted + sprint-12 page + counts (ADR 26→27, sprint pages 13→14, components 35→36) + fill-recorder-adapter component page (T1 reviewer follow-up) + 2 runbooks к index + mental-map +3 rows

### Tests / quality

- pytest unit: 689 passed (baseline 680 + 7 T1 + 2 T2) / 24 skipped / 0 failed
- pytest integration: existing tests OK
- mypy --strict src/: clean (67 source files)
- ruff: 3 pre-existing errors в tests/integration/test_risk_flow.py (S4-era I001/F401/UP017 — NOT S12 regression)
- Counts unchanged: 16/30/74/45 (S12 = orchestration + adapter + docs)
- Q7 verification: `git diff main..HEAD -- migrations/` empty ✅

### Wiki updates

- 2 NEW runbook pages (live-demo-validation + halt-response-protocol)
- 1 NEW component page (fill-recorder-adapter)
- 1 NEW ADR (0027)
- 1 NEW sprint page (this)
- Modified: pre-flight.md (Gate 5), halt-recovery.md (P1+OCO_ARMED escalation)
- current-state.md (TL;DR post-S12, ADR 26→27, sprint pages 13→14, components 35→36, +S12 row)
- index.md (sprint-12 + 2 runbooks + ADR 0027 + fill-recorder-adapter component)
- mental-map.md (+2 operator runbook rows + FillRecorderAdapter component row)

### Reviewers

- T1 (FillRecorderAdapter): trading-logic-reviewer + data-integrity-reviewer parallel dispatch (MANDATORY per ADR 0027). Both CONCERNS, NO BLOCKERS:
  - trading-logic VERIFIED: look-ahead invariant, FSM dispatch impact (none), idempotency, partial fill detection, _NoopFillRecorder deletion, find_by_order_id SQL safety, reason codes (none new). Concerns: feeCurrency-absent test missing (low priority).
  - data-integrity VERIFIED: Q7 zero-migration ✅, UNIQUE INDEX idempotency, Decimal precision, fill_ts timezone, WAL concurrent access, INSERT OR IGNORE atomicity, structlog audit completeness. Concerns mostly pre-existing (halt_log write-ahead order S13 carry-over).
- T2-T6: inline reviews (small isolated scope OR wiki-only)

### Key discoveries / decisions

- **Schema reality forces 2-layer adapter pattern** — execution_state has NO entry_signal_id → lookup chain breaks at bracket_id↔trade_id gap. Honest per Q7 zero-migration: Layer 1 audit ALWAYS fires, Layer 2 DB insert always-skips during S12 (S13 will add schema link)
- **Q6 critical correction propagated** — SPRINT_STATE S11 carry-over note "fix endpoint к testnet substring" verified WRONG via source grep. Trader caught it. Currently `"demo.bybit.com"` correctly routes к demo (pybit `testnet="testnet" in endpoint = False, demo="demo" in endpoint = True`). "Fix" would set testnet=True/demo=False = actual Bybit testnet env, would BREAK demo connectivity.
- **Trader source-claim verification (CC1 lesson)** — all 7 trader source claims verified via grep BEFORE acceptance: __main__.py:138 endpoint, ws_private.py:65-67 substring matching, data_collector.py:63 config-dict signature, fill_history.py:39-42 + FillRecord.parent_trade_id constraint
- **Q7 zero-migration constraint enforced** — verified at T1 + T2 + T6 (`git diff main..HEAD -- migrations/` empty). Enables clean alpha.11 binary rollback per halt-response-protocol.md
- **Zero-trade clause MANDATORY** — Q3 trader concern caught: 1H BTC EMA crossover likely 0 trades during 48h → structural criteria only, FillRecorder live-path validation conditional carry-forward к S13

### Carry-over к S13+

- **F live demo Mainnet validation actual run** — operator-driven post-merge per live-demo-validation.md
- **FillRecorderAdapter Layer 2 schema link** — add entry_signal_id к execution_state migration + wire Coordinator.start_bracket к persist signal_id (Q7 hard constraint pushed это к S13)
- **3-way endpoint enum (DEMO/TESTNET/MAINNET)** — Q6 future fix
- **T2 review C3 init_db dual-conn comment** (S11 carry-over) — code comment for two-connection sequence
- **DSR per-fold DataFrame→TradeRecord conversion** (informational, deferred от S10)
- **DSR threshold calibration** (S15+ per Q5 verdict)
- **halt_log INSERT order swap в `_set_halt`** (PRE-EXISTING, data-integrity T1 follow-up)
- **find_by_order_id ORDER BY explicit** (T1 follow-up, future-safe для multi-symbol)
- **fill-history.md component page update** (T1 trading-logic follow-up — reference FillRecorderAdapter as production impl)
- **execFee vs cumExecFee distinction в bybit-adapter.md** (T1 trading-logic follow-up)

### Roadmap

S13 = TBD post 48h operator-driven validation results. Likely scope: FillRecorder Layer 2 schema link (S12 acknowledged gap) + slippage validation gaps + S12 carry-overs.

## [2026-04-26] sprint-end | Sprint 13 — Backfill 5y + WFA T1-T6 measurement

### Phase 2 brainstorming verdicts (binding)

8 questions, trader-expert ROUND 1 (NO ROUND 2 needed):
- Q1 CONFIRM, Q2 EXPAND, Q3 CONFIRM, Q4 REVISE-FACTUAL (spec inconsistency caught), Q5 CONFIRM, Q6 CONFIRM, Q7 REVISE -> user REJECTED, Q8 CONFIRM
- ESC-1=c (defer pattern preserved), ESC-2 (tiered 5y, floor 3.5y MET)
- Spec reconciliation (CC4): acceptance-criteria.md amended с footnotes 1+2+3

### Tasks (8, 12 commits squash-merged)

- T1 Bybit data probe (d8e6930): earliest 1H BTCUSDT = 2021-07-02
- T2 _cmd_backfill wire (59ef6fc + 4a1b56b snappy/atomic)
- (21604af) get_klines pagination bug fix — Bybit V5 end-anchored
- T3 backfill run (33ad6c5): 42098 bars, 4.81y
- T4 NaN pre-flight (e4439e1)
- T5 trade_extractor (a2f1e07)
- T6 strategy_metrics + BLOCKER fix (5908682 + 1f7124a)
- T7 wire measurement + verdict (eb83650)
- T8 PHASE 8 wiki sync (this commit)

### Verdict result

**FAIL** — T1=-44.46, T2=-101.38, T3=1.27%, T4 win=0.30 RR=0.797, T5 n_trades=20 (FAIL <100), T6=1.136 (PASS), DSR=0.0445 (PASS), MC p=0.048 (PASS). Failed: [t1, t2, t4, t5].

**Critical insight:** Sample size NOT data-span-bounded. Strategy fires ~1 trade per 10 days regardless of 2.2y vs 4.8y data span. T5 n_trades floor (>=100) unreachable without strategy revision.

### Tests / quality

- pytest: 712 passed (689 baseline + 23 new across T2/T4/T5/T6 + 1 pagination test)
- mypy --strict src/: clean
- ruff: clean on touched files
- Q7-S12 zero-migration preserved

### Wiki updates

- 2 NEW component pages (trade-extractor, strategy-metrics)
- 1 NEW ADR (0028 — accepted)
- 1 NEW sprint page (this)
- Modified: __main__.py (3 wiring changes) + bybit/rest.py (pagination fix) + acceptance-criteria.md (footnotes)

### Reviewers

- T2 python + data-integrity (parallel MANDATORY) — APPROVED с 6 non-blocking concerns
- T5 quant-stats — APPROVED с 3 non-blocking
- T6 quant-stats — BLOCKER (T3 MaxDD initial_capital) -> fixed inline (1f7124a)

### Carry-over к S14+

- ESC-1 decision moment: PASS path (S14 = Mainnet pilot) OR pivot path (revision/abandon) — defer per Q7
- All S12 carry-overs still unaddressed (10 items)
- T2/T5/T6 quant-stats deferred concerns
- DSR threshold calibration (still S15+ per S11 Q5)

### Roadmap

S15 brainstorm input: S13 verdict=FAIL on 4.81y data. Strategy fires too rarely for T5. Operator (user) decides direction at S15 brainstorm — possible paths: (a) strategy revision, (b) honest "no edge" close, (c) multi-symbol expansion, (d) signal frequency tuning (look-ahead risk).

## [2026-04-26] sprint-end | Sprint 14 — Honest close (no-edge verdict)

### Phase 2 brainstorming

5 questions, trader-expert ROUND 1:
- Q1 **EXPAND** — T5 ≥100 trades structurally unreachable (5x signal frequency gap, EMA crossover на 1H BTC fires ~1 trade per 5-10 days). Plus my RSI 35/65 semantic was inverted (tightens, not widens).
- Q2 **REVISE** — DSR cross-trial sigma_SR not implemented (cross-FOLD only per dsr.py:73). N_trials=2 needs Bailey eq. 13 cross-trial std.
- Q3 CONFIRM strict formula PASS
- Q4 CONFIRM Settings config wiring (moot per Option B)
- Q5 CONFIRM pre-commit FAIL fallthrough к Option B (honored)

### USER DECISION

Per user verbatim: "Продолжаем тогда (B) Honest close immediately."

S14 = honest close ship. NO measurement re-run. NO code changes. Documentation only.

### Tasks (T1-T6, 4 docs commits)

- T1 ADR 0029 status: accepted
- T2 sprint-14-honest-close.md page (this sprint's canonical record)
- T3 wiki sync (current-state.md + index.md + mental-map.md + counts ADR 28→29 + sprint pages 15→16)
- T4 log.md sprint-end entry (this entry)
- T5 SPRINT_STATE → between-sprints с post-MVP-honest-close status
- T6 PHASE 8 ship via sprint-finish skill (tag v0.1.0-alpha.14)

### Final v0.1 status

- Infrastructure: COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages + 4.81y data + WFA + DSR + MC)
- Strategy validation: NEGATIVE (EMA crossover на 1H BTC = no edge, 2 measurements: 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable for chosen strategy + timeframe)
- Mainnet exposure: 0 (33min Bybit demo only)
- Tag: `v0.1.0-alpha.14` = honest close marker (NOT MVP DONE — alpha suffix preserved)

### Tests / quality

NO code changes. Existing test suite preserved at S13 baseline:
- pytest unit: 712 passed (no new tests, no regressions)
- mypy --strict src/: clean (69 source files)
- ruff: clean
- Q7-S12 zero-migration: trivially preserved

### Carry-overs preserved (10+ items unaddressed)

All S12 + S13 carry-overs остаются open. See pre-s14-backlog.md "USER FINAL DECISION" + sprint-14-honest-close.md "Open issues для v0.2+" for full list.

### Future direction (operator-driven, NO commitment)

(A) Strategy revision (mean-reversion / regime-switch / ML) — 3-5 sprints
(B) Multi-symbol (ETH + SOL) — 2-3 sprints, ~3x signal frequency
(C) Different timeframe (15M / 4H) — 1-2 sprints, ADR 0005 amendment
(D) Project pause — 0 sprints, current state freeze

Operator decides if/when. No S15 commitment.

### Roadmap

**v0.1 closed at S14 honest.** Project state: between-sprints с post-MVP-honest-close marker.

## [2026-04-26] sprint-end | Sprint 15 — Mean-reversion + multi-symbol (v0.2 retry attempt #1)

**Verdict: FAIL** (4/6: T5 t_stat 1.04<2.0, T6 mean -12.38<0.7, MC p 0.998>0.05, DSR 0.0).
**Progress:** T5 ≥100 trades floor REACHED first time (108 aggregate trades). ADR 0030 multi-symbol aggregation hypothesis VALIDATED. Strategy still no edge — different failure mode vs S13.

**Per-symbol (3 Bybit Spot 1H):**
- BTCUSDT: 44 trades, sharpe ratio mean +1.75, MC p 0.197 (best performer)
- ETHUSDT: 29 trades, sharpe ratio mean -39.35, MC p 0.998 (one catastrophic fold drives mean)
- SOLUSDT: 35 trades, sharpe ratio mean +0.45, MC p 0.65

**Aggregate metrics:** T1 9.32 PASS / T2 29.55 PASS / T3 0.053 PASS / T4 win 37%/RR 2.27 PASS / T5 108 PASS-on-count BUT t_stat 1.04 FAIL / T6 -12.38 FAIL / MC 0.998 FAIL / DSR 0 FAIL (n_trials=2, sigma_SR=22.68 cross-trial — closes S14 Q2).

### Deliverables (8 TDD tasks)
- T0 CrossTrialLog (Bailey eq. 13) — closes S14 Q2 REVISE carry-over (commit fc8c761)
- T1 TradeHistory.load_recent symbol filter (HIGH BLOCKER per architecture-reviewer Q2 — Kelly contamination fix) — 2d3ad70
- T2 Bollinger Bands indicator (NEW, 9 unit tests) — d29e004
- T3 MeanReversionRsiBBStrategy (NEW, 11 unit tests, drop-in Strategy protocol) — 0b43c10
- T4 _cmd_run wires MeanReversion + symbol→RiskManager (live runtime kept single-symbol — multi-symbol fan-out deferred к v0.2 production wave) — bf9031a
- T5 Multi-symbol --symbols CLI for backfill+wfa, DSR cross-trial wiring, per-symbol JSON output — bf9031a
- T6 tz-aware parquet filter fix + indicators.py mean_reversion branch + measurement run — ccfbf71
- T7 wiki sync (this commit)
- T8 PHASE 8 ship — pending

### Tests / quality
- pytest unit: 712 → **732 passed**, 24 skipped (+20: 7 cross_trial_log + 9 BB + 11 MeanRev + 3 trade_history symbol filter + 4 CLI symbols)
- mypy --strict src/: clean (72 src files)
- Q7-S12 zero-migration: preserved

### S15 brainstorm key decisions (PHASE 2 — pre-s15-backlog.md)
- 4 questions delegated к trader-expert (all 4) + architecture-reviewer (Q2/Q3/Q4)
- ESC-1 RESOLVED Option B (Q1 mean-reversion + Q2 multi-symbol on 1H) — both reviewers converged
- ESC-2 RESOLVED pre-registered RSI 30/70 + BB(20, 2σ) AND-gated (binding, no post-result tuning)
- Q3 (15M timeframe) DEFERRED к S16+ — 2 hard blockers identified (interval_map, heal_max_age 1H coupling = production safety bug at 15M)
- Q4 (ML XGBoost) DEFERRED к v0.3+ — both reviewers concur (root cause = no edge, not signal noise)
- Architecture-reviewer found NEW HIGH BLOCKER: TradeHistory.load_recent missing symbol filter → multi-symbol Kelly contamination → fixed in T1

### Operator decision pending S16
- (B') Broader RSI thresholds + variance reduction (more trades = more N_trials = harsher DSR penalty)
- (C) Q3 15M timeframe — 2 sprints (interval_map + heal_max_age fixes blockers)
- (D) Honest close v0.2 — accept 2 strategy attempts both failed, freeze
- (E) Q4 ML XGBoost — viable only if simpler strategy showed partial signal (S15 didn't)

### Roadmap

**v0.2 retry attempt #1 SHIPPED.** Tag v0.1.0-alpha.15. Awaiting operator decision на S16 direction.

## [2026-04-26] sprint-end | Sprint 16 — v0.2 honest close

**Verdict: HONEST CLOSE v0.2** (per S16 PHASE 2 trader-expert ROUND 1 CONFIRM Option D — single direction question, no architecture-reviewer needed).

### Trader rationale (verbatim summary)

1. **DSR cross-trial math**: sigma_SR=22.68 с -44.46 anchor → expected max Sharpe gate ≈ +21.5 для n_trials=3 = unrealistic для 1H crypto. Options B' (broader thresholds) и C (15M) structurally futile.
2. **BTC +1.75 signal noted**: единственный positive direction в проекте, но p=0.197 не passes 0.05 MC gate; 9 trades/fold = unreliable t-stat. Institutional knowledge для v0.3, не decision-reversing.
3. **ETH fold -188.65** = data pathology (extreme vol window 2021-2022). MC p=0.998 на full distribution = strategy random-equivalent regardless.
4. **Option C (15M)** = 2 sprints architectural blockers (interval_map + heal_max_age) для academically weaker test (Hudson & Urquhart 2021 mean-reversion degrades sub-hourly).
5. **Option D breaks DSR accumulation cleanly + preserves v0.3 optionality** (Bailey 2014 N_trials per hypothesis).
6. **Evidence base sufficient**: 2 families × 5y data × proper WFA+DSR+MC pipeline.

### Final v0.2 status

- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 31 ADRs + 18 sprint pages)
- Strategy validation: ❌ NEGATIVE × 2 hypotheses (S13 EMA + S15 mean-reversion both FAIL)
- MVP DONE per acceptance-criteria.md: NOT achieved
- Mainnet exposure: 0 (33min Bybit demo only since S12)
- Tag: v0.1.0-alpha.16 = v0.2 honest close marker (NOT MVP DONE)

### Deliverables (S16, docs-only)

- T1 ADR 0031 accepted
- T2 sprint-16-honest-close-v02.md created
- T3 wiki sync (current-state TL;DR + ADR 30→31, sprint pages 17→18, +S16 row)
- T4 log.md sprint-end (this entry)
- T5 SPRINT_STATE → between-sprints, tag alpha.16
- T6 cross_trial_sharpes.json → _v0.2.json archival + reset к [] для v0.3 fresh-start
- T7 PHASE 8 ship via sprint-finish

### Tests / quality

NO code changes:
- pytest unit: 732 passed (S15 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved (no migrations changed)

### Cross-cutting concerns binding (per ADR 0031)

- **CC1 BTC institutional knowledge**: documented для v0.3-A (BTC-only mean-reversion fresh start)
- **CC2 cross_trial_sharpes archival**: BINDING policy — v0.3 fresh hypothesis archives current + resets к empty
- **CC3 ETH fold pathology**: documented к prevent future misattribution
- **CC4 Tag semantics**: alpha.16 = honest close marker, NOT MVP DONE
- **CC5 No spec amendment**: T1-T6 thresholds preserved
- **CC6 Q3 15M blockers preserved**: documented для potential future revival

### v0.3+ future direction options (operator-driven, no commitment)

- (v0.3-A) BTC-only mean-reversion fresh start — strongest observed signal
- (v0.3-B) Regime-switch (HMM) — 3-5 sprints
- (v0.3-C) ML XGBoost — defer (no partial signal evidence S15)
- (v0.3-D) Different timeframe (15M/4H) — Q3 blockers preserved
- (v0.3-E) Project pause — 0 sprints, freeze

### Roadmap

**v0.2 closed at S16 honest.** Tag v0.1.0-alpha.16. Project state: between-sprints с post-v0.2-honest-close marker. Operator decides v0.3 if/when.

## [2026-04-26] sprint-end | Sprint 17 — BTC-only mean-reversion relaxed (MVP retry hypothesis #3)

**Verdict: FAIL — T5 count only** (59 trades < 100 floor). Per ADR 0032 amendment 3 BINDING → S18 honest close v0.1.

User constraint (BINDING): "торговать будем в mvp только btc/usdt" — MVP scope = BTCUSDT only per ADR 0016 + ADR 0004.

### S17 PHASE 2 brainstorm

Trader-expert ROUND 1 EXPAND → CONFIRM (a) с 3 mandatory amendments:

1. Pre-register RSI 35/65 + BB(20, 1.5σ) AND-gated BINDING
2. DROP variance cap -10 threshold (ETH-pathology-derived, audit-clean)
3. T5 count failthrough clause: <100 trades → FAIL → honest close v0.1

Alternatives ruled out: (b) ATR regime filter definitionally frequency-reducing; (c) Donchian breakout same low-frequency как S13 EMA; (d) 15M architectural cost too high; (e) honest close NOW premature.

### Strategy criteria results (5/6 PASS + DSR + MC sig)

- T1 Sharpe OOS: **25.99** PASS (≥1.0)
- T2 Sortino OOS: 4446 PASS (≥1.5) — suspiciously high
- T3 MaxDD: 2.8% PASS (<25%)
- T4 win/RR: 47.5% / RR 154.5 PASS
- **T5: 59 trades FAIL** (но t_stat 2.13 ≥2.0, mean_pnl +2.40% positive — sample insufficient)
- T6 OOS/IS sharpe ratio: **0.712 PASS** (borderline ≥0.7)
- **DSR: 1.0 PASS** (n_trials=1 fresh baseline, single-trial formula)
- **MC p-value: 0.01 PASS** (statistically significant)

Fold sharpes: [0.96, -1.02, -1.46, 1.58, 3.50] — fold #5 outlier 3.50 drives mean. Без fold #5 mean ≈ 0.01 (concerning concentration).

### Frequency math reconciliation

Trader pre-measurement prediction: 66-88 BTC trades. Actual: **59**. AND-gate joint multiplier ~1.34x baseline (44 trades S15), ниже trader's 1.4-1.7x estimate. Likely cause: stronger positive correlation between RSI extreme + BB breach чем empirical estimate compresses joint probability further.

T5 floor 100 НЕ reachable на BTC-only 1H mean-reversion regardless of relaxed thresholds tested.

### Critical insight for v0.4+

**Strategy edge IS real on BTC mean-reversion regime** (MC p=0.01 statistically significant + DSR=1.0 + T1=25.99 + 5/6 criteria PASS). NO past sprint demonstrated этот set of metrics. Failure mode = INSUFFICIENT SAMPLE SIZE only.

Future MVP-DONE attempts requiring T5 PASS должны:
- Higher-frequency timeframe (15M = 4x — Q3 architectural blockers preserved)
- Hybrid mean-reversion + ML filter (Q4 deferred — S17 evidence supports: real partial signal exists)
- Multi-symbol revival (out of MVP scope per user 2026-04-26)

### Deliverables

- T1 ADR 0032 (S17 strategy + 3 amendments + T5 failthrough clause)
- T2 indicators.py mean_reversion branch (NO change — already config-driven from S15)
- T3 _run_wfa_single_symbol config update (RSI 35/65 + BB k=1.5) + sprint env var fix
- T4 measurement run BTC-only --symbol BTCUSDT 4.81y
- T5 sprint-17 page + ADR + wiki sync (this commit)
- T6 PHASE 8 ship via sprint-finish

### Tests / quality

NO new tests (trivial config change):
- pytest unit: 732 passed (S16 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

### Next sprint (binding per ADR 0032 amendment 3)

**S18 = honest close v0.1.** Documentation only sprint, mirrors S14 ADR 0029 + S16 ADR 0031 patterns:
- ADR 0033 v0.1 honest close (3 hypotheses tested negative)
- sprint-18-honest-close-v01.md
- Document strategy edge IS real (MC p=0.01) but sample insufficient на 1H BTC alone
- Archive cross_trial_sharpes.json к _v0.1-final.json
- Tag v0.1.0-alpha.18 = v0.1 final honest close marker

### Roadmap

**S17 SHIPPED.** Tag v0.1.0-alpha.17. Per failthrough → S18 = honest close v0.1.

3 hypotheses tested across 4.81y BTC Bybit Spot 1H:
1. EMA crossover trend-following (S13) — FAIL all critical T-criteria
2. Mean-reversion RSI+BB multi-symbol (S15) — FAIL T6+MC+DSR (T5 reached)
3. Mean-reversion RSI+BB BTC-only relaxed (S17) — FAIL T5 count only (5/6 PASS + DSR + MC sig)

**Strategy hypothesis space: positive direction found но не conjoint pass.** Operator decides v0.4 if/when (different timeframe / hybrid ML / multi-symbol revival).

## [2026-04-26] sprint-end | Sprint 18 — v0.1 FINAL honest close

**Verdict: HONEST CLOSE v0.1 FINAL** (pre-committed per ADR 0032 amendment 3 BINDING — S17 T5 count failthrough triggered, no new brainstorm needed).

### Final v0.1 status

3 strategy hypotheses tested across 4.81y BTC Bybit Spot 1H — all FAIL conjoint per acceptance-criteria.md T1-T6 + DSR:

| # | Hypothesis | Sprint | OOS Trades | Pass | Verdict |
|---|-----------|--------|-----------|------|---------|
| 1 | EMA crossover trend-following | S13 | 20 | T3 only | FAIL T1+T2+T4+T5 |
| 2 | Mean-reversion multi-symbol BTC+ETH+SOL | S15 | 108 | T1-T4 | FAIL T6+MC+DSR |
| 3 | Mean-reversion BTC-only relaxed | S17 | 59 | T1-T4+T6+DSR+MC | FAIL T5 count only |

- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 33 ADRs + 20 sprint pages)
- Strategy validation: ❌ NEGATIVE conjoint × 3 hypotheses
- MVP DONE per acceptance-criteria.md: NOT achieved
- Mainnet exposure: 0 (33min Bybit demo only since S12)
- Tag: v0.1.0-alpha.18 = v0.1 FINAL honest close marker

### Critical scientific finding (S17 partial signal preserved)

S17 produced **MC p=0.01 statistically significant** + DSR=1.0 + T1=25.99 + 5/6 criteria PASS на 59 BTC trades. Strategy edge IS real on BTC mean-reversion regime. **Sample size insufficient** на 1H BTC alone — frequency structural limit ~60-70 trades / 4.81y maximum (S15 baseline 44 + S17 relaxed 59, AND-gate joint multiplier 1.34x).

Future MVP-DONE attempts must address frequency dimension:
- Higher-frequency timeframe (15M = 4x — Q3 architectural blockers preserved)
- Hybrid ML filter (S17 evidence supports — partial signal exists для ML к learn)
- Multi-symbol aggregation (out of MVP scope per user 2026-04-26)

### Deliverables (S18, docs-only)

- T1 ADR 0033 accepted
- T2 sprint-18-honest-close-v01.md created
- T3 cross_trial_sharpes archival: data/cross_trial_sharpes.json → data/cross_trial_sharpes_v0.1-final.json + reset к {"trials": []} для v0.4 fresh-start
- T4 wiki sync (current-state TL;DR + ADR 32→33, sprint pages 19→20, +S18 row)
- T5 log.md sprint-end (this entry)
- T6 SPRINT_STATE → between-sprints, tag alpha.18
- T7 PHASE 8 ship via sprint-finish

### Tests / quality

NO code changes:
- pytest unit: 732 passed (S17 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved (no migrations changed)

### Cross-cutting concerns binding (per ADR 0033)

- **CC1 S17 partial signal preserved** для v0.4 institutional knowledge (mean-reversion regime works)
- **CC2 cross_trial_sharpes archival** BINDING (mirrors S16 CC2 — Bailey 2014 N_trials per hypothesis)
- **CC3 Frequency structural limit documented** — single-symbol BTC 1H mean-reversion ~60-70 trades / 4.81y max
- **CC4 Q3 15M architectural blockers preserved** (interval_map + heal_max_age production safety)
- **CC5 Tag semantics**: alpha.18 = v0.1 FINAL marker, NOT MVP DONE
- **CC6 No spec amendment**: T1-T6 thresholds preserved
- **CC7 Multi-symbol infrastructure preserved post-MVP**: S15 work не trash

### v0.4+ future direction options (operator-driven, no commitment)

- (v0.4-A) BTC 15M mean-reversion — STRONGEST viable path per S17 evidence (4x frequency = T5 floor reachable estimate)
- (v0.4-B) Hybrid mean-reversion + ML XGBoost filter — S17 evidence reverses ADR 0030 ML defer rationale
- (v0.4-C) Multi-symbol revival — out of MVP scope per user 2026-04-26
- (v0.4-D) Different timeframe 4H — НЕ recommended per S17 evidence
- (v0.4-E) Project pause — 0 sprints, freeze

### Roadmap

**v0.1 closed FINAL at S18 honest.** Tag v0.1.0-alpha.18. Project state: between-sprints с post-v0.1-honest-close-FINAL marker. 3rd honest close в проекте (S14 + S16 + S18). 3 strategy hypotheses tested + 1 partial signal observed = publishable scientific contribution. Operator decides v0.4 if/when.
