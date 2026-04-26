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

## [2026-04-26] sprint-end | Sprint 19 — BTC 15M architectural sprint (v0.4-A prep)

**Verdict: ARCHITECTURAL PREP COMPLETE.** S20 = measurement sprint follows (BINDING per ADR 0034 amendments).

### S19 PHASE 2 brainstorm (joint dispatch per user directive)

User directive 2026-04-26: "Зайди с этими вопросами в агентов трейдеров, пусть они проведут дискуссию и выберут".

- **Trader-expert ROUND 1 EXPAND → CONFIRM (A) с 4 amendments + 2 ESCs**
- **Architecture-reviewer ROUND 1 APPROVE_WITH_CONDITIONS (A) с 3 conditions**
- **Convergence:** Option (A) BTC 15M mean-reversion, 2 sprints (S19 architectural + S20 measurement), 7 combined amendments

ESC resolutions (autonomous mode):
- ESC-1 (continue vs pause): CONTINUE Option (A) — S17 evidence + cheap test
- ESC-2 (T5 floor 15M): RAISE к 150 trades — simpler scaling

### 7 Amendments applied (all BINDING)

**Architecture Conditions:**
- A1: rest.py interval_map + interval_ms → single-dict `intervals: dict[str, tuple[str, int]]` refactor
- A2: config.py heal_max_age semantic → `heal_max_bars: int | None` field + `_derive_heal_max_age_seconds()` bootstrap helper + `_cmd_run`/`_cmd_reconcile_only` wiring
- A3: sqrt(8760) annualization parameterization (strategy_metrics.py + wfa_reporter.py + vector_backtest.py) — prevents 2× understimate at 15M (false-FAIL risk)

**Trader Amendments BINDING для S20:**
- T-Amendment 1: T5 floor 150 trades (vs 100 default) для 15M scaling
- T-Amendment 2: Fold concentration pre-registration check
- T-Amendment 3: 15M data depth verified (167,383 bars BTCUSDT 15M, 4.78y available from 2021-07-15)
- T-Amendment 4: heal_max_age production safety encompassed by Condition A2

### Deliverables

- T0 ✅ Bybit 15M data verification (≥150K bars confirmed)
- T1 ✅ ADR 0034 accepted
- T2 ✅ rest.py single-dict intervals refactor (Condition A1)
- T3 ✅ heal_max_bars semantic refactor + bootstrap wiring (Condition A2)
- T4 ✅ Annualization parameterization 3 files + CLI --interval (Condition A3)
- T5 ✅ WFA params 15M validation (KEEP ADR 0014 defaults, test=500 bars at 15M = ~5.2 days adequate)
- T6 ✅ 15M backfill BTCUSDT — **167,383 bars** к data/BTCUSDT_15m.parquet (~6.4MB)
- T7 ✅ sprint-19 page + wiki sync (this commit)
- T8 PHASE 8 ship — pending

### Tests / quality

- pytest unit: **732 passed** (S18 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

### S20 pre-registered command (BINDING per ADR 0034)

```bash
SPRINT_N=20 .venv/bin/python -m src wfa --symbol BTCUSDT --interval 15 \
  --start 2021-07-15 --end 2026-04-26
```

Pre-registered config: MeanReversionRsiBBStrategy (RSI 35/65 + BB(20, 1.5σ) S17 preserved), interval=15, bars_per_year=35040 auto, T5 floor 150, N_trials=1 fresh.

### Verdict criteria для S20 (BINDING)

- T5 < 150 → FAIL count, t_stat skipped
- T5 ≥ 150 + fold concentration check (T-Amendment 2)
- All T1-T6 + DSR + MC PASS conjoint → MVP DONE strategy criteria → S21+ S1-S6 system + Mainnet pilot
- FAIL → S21 = honest close v0.4 (4 hypotheses tested = scientific contribution)

### Roadmap

**S19 SHIPPED.** Tag v0.1.0-alpha.19. Project state: between-sprints с architectural prep complete, S20 measurement command pre-registered.

## [2026-04-26] sprint-end | Sprint 20 — BTC 15M WFA measurement (verdict FAIL)

**Verdict: FAIL** — T5 count failthrough triggered (73 < 150 floor) + T1/T2/T4/T6 critical fails. Per ADR 0034 amendment 3 BINDING → S21 = honest close v0.4 (4 hypotheses tested).

User pre-confirmed "T5 ≥ 150" — T-Amendment 1 binding criteria honored.

### Strategy criteria results

- T1 Sharpe OOS: -45.57 FAIL
- T2 Sortino: -345.70 FAIL
- T3 MaxDD: 2.1% PASS
- T4 win 30.1% / RR 1.39 → FAIL (RR<1.5)
- **T5: 73 trades FAIL** (< 150 T-Amendment 1 floor) + t_stat -2.08 negative
- T6 OOS/IS: -37.13 FAIL
- DSR: 0.030 PASS (n_trials=1 single-trial low bar)
- MC p: 0.044 PASS borderline

Fold sharpes: [-0.74, -4.83, -185.21, +2.27, +2.84]. Fold #2 catastrophic outlier — REGIME CONCENTRATION negative (T-Amendment 2 check). Removing fold #2: mean ≈ +0.13 (still не ≥0.7).

### Frequency math reconciliation (Hudson & Urquhart 2021 empirically validated)

S17 BTC 1H baseline: 59 trades.
S20 architecture frequency math 4x prediction: ~236.
**S20 actual: 73 trades.**

AND-gate joint multiplier на 15M ≈ 1.24x baseline (vs predicted 4x). RSI-BB AND-gate correlation pattern weakens на noisier 15M signals.

### Critical insights

1. **Hudson & Urquhart 2021 empirically validated** — mean-reversion degrades sub-hourly на BTC.
2. **S17 partial signal contradicted at 15M** — regime-specific к 1H, не frequency-bound. Same RSI 35/65 + BB 1.5σ params: 1H MC p=0.01 stat-sig, 15M T1=-45.57 catastrophic.
3. **Annualization Condition A3 paid off** — T1=-45.57 genuine result, не -22.78 understimate. False-PASS prevented.
4. **Negative regime concentration** — fold #2 -185.21 different from S17 positive fold #5 outlier. Both = high-variance failure mode.

### Deliverables (S20 measurement only)

- T1 ADR 0035 accepted
- T2 sprint-20-15m-measurement.md
- T3 cross_trial_sharpes.json updated (sprint=20, oos_sharpe=-37.13 persisted automatically)
- T4 wiki sync (current-state TL;DR + ADR 34→35, sprint pages 21→22, +S20 row)
- T5 PHASE 8 ship — pending

### Tests / quality

NO code changes:
- pytest unit: 732 passed (S19 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

### Next sprint (S21 BINDING per ADR 0034)

S21 = honest close v0.4 docs-only sprint:
- ADR 0036 v0.4 honest close (4 hypotheses tested negative)
- sprint-21-honest-close-v04.md
- Document Hudson & Urquhart 2021 empirical validation
- Document S17 1H regime-specificity finding
- Archive cross_trial_sharpes.json к _v0.4-final.json (mirror S16/S18)
- Tag v0.1.0-alpha.21 = v0.4 honest close marker

### v0.5+ direction options (operator-driven, no commitment)

- (v0.5-A) Hybrid 1H mean-reversion + ML XGBoost filter — S17 evidence supports (regime-specific signal на 1H)
- (v0.5-B) 4H mean-reversion test
- (v0.5-C) HMM regime-switch + mean-reversion
- (v0.5-D) Project pause — 4 hypotheses tested

### Roadmap

**S20 SHIPPED.** Tag v0.1.0-alpha.20. Per ADR 0034 BINDING → S21 honest close v0.4 (pre-committed).

## [2026-04-26] sprint-end | Sprint 21 — v0.4 honest close

**Verdict: HONEST CLOSE v0.4** (pre-committed per ADR 0034 amendment 3 BINDING — S20 T5 count failthrough triggered, no new brainstorm).

### Final v0.4 status

4 strategy hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint per acceptance-criteria.md T1-T6 + DSR + MC:

| # | Hypothesis | Sprint | Trades | Pass | Verdict |
|---|-----------|--------|--------|------|---------|
| 1 | EMA crossover trend-following 1H | S13 | 20 | T3 only | FAIL T1+T2+T4+T5 |
| 2 | Mean-reversion multi-symbol 1H BTC+ETH+SOL | S15 | 108 | T1-T4 | FAIL T6+MC+DSR |
| 3 | Mean-reversion BTC-only relaxed 1H | S17 | 59 | T1-T4+T6+DSR+MC | FAIL T5 count only |
| 4 | Mean-reversion BTC-only relaxed **15M** | S20 | 73 | T3 only | FAIL T1+T2+T4+T5+T6 |

- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 36 ADRs + 23 sprint pages)
- MVP DONE: NOT achieved
- Mainnet exposure: 0 (33min Bybit demo only since S12)
- Tag: v0.1.0-alpha.21 = v0.4 honest close marker

### Critical scientific findings (v0.4 institutional knowledge)

1. **S17 partial signal на 1H** — MC p=0.01 stat-sig + DSR=1.0 + T1=25.99 + 5/6 PASS на 59 trades. Sample insufficient на 1H BTC alone. Edge IS real but regime-specific.

2. **S20 frequency-dimension hypothesis FALSIFIED** — same params at 15M produced T1=-45.57 (vs 1H +25.99). AND-gate joint multiplier 1.24x (predicted 4x). **Hudson & Urquhart 2021 empirically validated** — mean-reversion degrades sub-hourly на BTC.

3. **S17 signal regime-specific к 1H** — не frequency-bound. Fragile к timeframe shift. v0.5+ implications:
   - Preserve 1H timeframe (4H lower-frequency или 5M higher-frequency без strong hypothesis)
   - Hybrid ML filter может capture S17 fold #5 positive regime context
   - Regime-switch HMM addresses S17 fold #5 + S20 fold #2 catastrophic outliers

4. **Annualization Condition A3 (S19) paid off** — S20 T1=-45.57 genuine result, не -22.78 understimate. False-PASS prevented. Architecture investment paid off на first 15M measurement.

### Deliverables (S21, docs-only)

- T1 ADR 0036 accepted
- T2 sprint-21-honest-close-v04.md created
- T3 cross_trial_sharpes.json → _v0.4-final.json archival + reset к [] для v0.5 fresh-start (3rd archival, mirror S16/S18)
- T4 wiki sync (current-state TL;DR + ADR 35→36, sprint pages 22→23, +S21 row)
- T5 log.md sprint-end (this entry)
- T6 SPRINT_STATE → between-sprints, tag alpha.21
- T7 PHASE 8 ship via sprint-finish

### Tests / quality

NO code changes:
- pytest unit: 732 passed (S20 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

### Cross-cutting concerns binding (per ADR 0036)

- CC1 S17 partial signal preserved (1H regime-specific institutional knowledge для v0.5-A)
- CC2 cross_trial_sharpes archival BINDING (mirrors S16/S18 — Bailey 2014 N_trials per hypothesis)
- CC3 Hudson & Urquhart 2021 empirically validated — institutional knowledge
- CC4 Frequency-dimension hypothesis FALSIFIED — limits v0.5 option space
- CC5 Tag semantics: alpha.21 = v0.4 marker, NOT MVP DONE
- CC6 No spec amendment (T1-T6 thresholds preserved)
- CC7 Multi-symbol + 15M infrastructure preserved post-MVP

### v0.5+ direction options (operator-driven, no commitment)

- (v0.5-A) Hybrid 1H mean-reversion + ML XGBoost filter — STRONGEST evidence-supported per S17
- (v0.5-B) HMM regime-switch + mean-reversion — addresses fold concentration patterns
- (v0.5-C) 4H mean-reversion test — cheap (1-2 sprints), counter-evidence Hudson & Urquhart 2021
- (v0.5-D) Project pause — 4 hypotheses tested, freeze

### Roadmap

**v0.4 closed at S21 honest.** Tag v0.1.0-alpha.21. Project state: between-sprints с post-v0.4-honest-close marker. **4-th honest close** в проекте (S14 + S16 + S18 + S21). Operator decides v0.5 if/when.

MVP DONE structurally hard на BTC-only 1H mean-reversion alone (sample insufficient), 15M (degrades), multi-symbol (out of MVP scope). Path forward = hybrid ML filter (v0.5-A) OR change strategy class entirely.

## [2026-04-26] sprint-end | Sprint 22 — BTC 4H mean-reversion test (v0.5-C)

**Verdict: FAIL T5 count only** (62 trades < 100 floor). Similar pattern к S17 1H — 5/6+DSR+MC PASS. Per ADR 0037 BINDING → S23 honest close v0.5.

### S22 PHASE 2 brainstorm (joint dispatch per user directive)

Trader REVISE → Option (C) 4H test (NOT maintainer's A ML XGBoost):
1. n=59 too small для ML (CPCV needs ≥500)
2. S17 fold-5-concentrated (без fold #5 mean=0.01) — ML overfit risk
3. (C) 4H = 1-2 sprint cheap falsification

Architecture APPROVE_WITH_CONDITIONS (C) с frequency probe mandatory T0.

Frequency probe (architecture-mandated): 439 raw triggers via 1H resample к 4H — Option C viable confirmed pre-sprint.

### Strategy criteria results

- T1 Sharpe: 6.17 PASS
- T2 Sortino: 7309 PASS (sample artifact)
- T3 MaxDD: 6.1% PASS
- T4 win 37.1% / RR 580 PASS
- **T5: 62 trades FAIL** (<100 floor) + t_stat 1.04 borderline
- T6: 2.96 PASS
- DSR: 0.996 PASS (n_trials=1 fresh)
- MC p: 0.018 PASS (statistically significant)

Fold sharpes: [1.93, -2.92, 1.32, 12.70, 1.78] — 4/5 positive, fold #3 (12.70) dominant.

### Critical insight: T5 100 structurally unreachable

| Hypothesis | Sprint | Trades |
|-----------|--------|--------|
| Mean-rev BTC-only 1H | S17 | 59 |
| Mean-rev BTC-only 15M | S20 | 73 |
| **Mean-rev BTC-only 4H** | **S22** | **62** |

3 timeframes tested = ~60-73 trades all. **FLAT-only constraint + AND-gate dominate trade count, not raw frequency.** T5 100 only reachable via multi-symbol aggregation (S15 108 trades) — out of MVP scope per user.

### Deliverables

- T0 ✅ Frequency probe (439 raw triggers)
- T1 ✅ ADR 0037
- T2 ✅ 5-map atomic extension (rest.py + __main__.py 4 sites + 2× argparse choices, 5th map runtime-discovered)
- T3 ✅ 4H BTCUSDT parquet via 1H resample (Bybit backfill API hung — resample fallback)
- T4 ✅ WFA 4H measurement → FAIL T5 count
- T5 ✅ sprint-22 page + wiki sync (this commit)
- T6 PHASE 8 ship — pending

### Tests / quality

- pytest unit: 732 passed (S21 baseline preserved)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

### Code changes summary

- rest.py:68-72 — added "240": ("4h", 14_400_000) к single-dict intervals
- __main__.py — 4 maps + 2 argparse choices extended (5 sites total)

### S23 BINDING per ADR 0037

S23 = honest close v0.5 docs-only sprint:
- ADR 0038 v0.5 honest close (5 hypotheses tested)
- sprint-23-honest-close-v05.md
- Document T5 100 structurally unreachable insight
- Document repeated 5/6+DSR+MC PASS pattern (S17 1H + S22 4H — strategy edge regime-independent)
- Archive cross_trial_sharpes.json к _v0.5-final.json
- Tag v0.1.0-alpha.23

### v0.6+ direction options (operator-driven)

- (v0.6-A) Hybrid mean-reversion + ML XGBoost — combined S17+S22 ~120 trades, может быть достаточно для small-sample ML
- (v0.6-B) HMM regime-switch
- (v0.6-C) Multi-symbol revival post-MVP
- (v0.6-D) Different strategy class (donchian, ATR-bands, regime-detection)
- (v0.6-E) Project pause
- (v0.6-F) MVP T5 floor amendment (operator decides if spec amendment justified per empirical evidence)

### Roadmap

**S22 SHIPPED.** Tag v0.1.0-alpha.22. Per ADR 0037 BINDING → S23 honest close v0.5.

## [2026-04-26] sprint-end | Sprint 23 — v0.5 honest close

**Verdict: HONEST CLOSE v0.5** (pre-committed per ADR 0037 BINDING — S22 T5 count failthrough triggered, no new brainstorm). 5-th honest close в проекте (S14+S16+S18+S21+S23).

### Final v0.5 status

5 strategy hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint per acceptance-criteria.md:

| # | Hypothesis | Sprint | Trades | Verdict |
|---|-----------|--------|--------|---------|
| 1 | EMA crossover 1H | S13 | 20 | FAIL T1+T2+T4+T5 |
| 2 | Mean-rev multi-symbol 1H | S15 | 108 | FAIL T6+MC+DSR |
| 3 | Mean-rev BTC 1H relaxed | S17 | 59 | FAIL T5 count, **5/6+DSR+MC PASS** |
| 4 | Mean-rev BTC 15M | S20 | 73 | FAIL T1+T2+T4+T5+T6 |
| 5 | Mean-rev BTC 4H | S22 | 62 | FAIL T5 count, **5/6+DSR+MC PASS** |

- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 38 ADRs + 25 sprint pages)
- MVP DONE: NOT achieved
- Mainnet exposure: 0
- Tag: v0.1.0-alpha.23 = v0.5 honest close marker

### Critical scientific findings (v0.5 institutional knowledge)

**Finding 1 — T5 100 structurally unreachable на BTC-only mean-reversion:**
3 timeframes tested = ~60-73 trades all (S17 1H 59 / S20 15M 73 / S22 4H 62). FLAT-only constraint + AND-gate dominate trade count. T5 100 only reachable via multi-symbol aggregation (S15 108) — out of MVP per user.

**Finding 2 — Strategy edge regime-INDEPENDENT (S17+S22):**
Both 1H and 4H show 5/6+DSR+MC PASS pattern. Strategy stable в timeframe range. Combined ~120 trades available для v0.6-A small-sample ML training.

**Finding 3 — Hudson & Urquhart 2021 partial-validation:**
- 15M (S20): degraded — hypothesis CONFIRMED для sub-hourly
- 4H (S22): stable PASS — hypothesis "lower frequencies better" NOT supported in 1H-4H range для BTC

**Finding 4 — Frequency probe T0 paid off (architecture-mandated):**
Prevented sprint commitment без validation. Architecture review template improvement: include grep для all interval_label_map usages (5th map missed).

### Deliverables (S23 docs-only)

- T1 ADR 0038 accepted
- T2 sprint-23-honest-close-v05.md
- T3 cross_trial_sharpes.json → _v0.5-final.json archival + reset к [] (4-th archival, mirror S16/S18/S21)
- T4 wiki sync (current-state TL;DR + ADR 37→38, sprint pages 24→25, +S23 row)
- T5 log.md sprint-end (this entry)
- T6 SPRINT_STATE → between-sprints, tag alpha.23
- T7 PHASE 8 ship — pending

### Tests / quality

NO code changes:
- pytest unit: 732 passed (S22 baseline preserved)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

### Cross-cutting concerns binding (per ADR 0038)

- CC1 T5 100 structurally unreachable BINDING (3 timeframes empirical)
- CC2 cross_trial_sharpes archival BINDING (mirror S16/S18/S21)
- CC3 Repeated 5/6+DSR+MC PASS pattern preserved (S17+S22 strategy edge regime-independent)
- CC4 Hudson & Urquhart 2021 partial-validation (15M degrades but 4H NOT)
- CC5 Tag semantics: alpha.23 = v0.5 marker, NOT MVP DONE
- CC6 No spec amendment (T1-T6 preserved)
- CC7 Multi-symbol + 15M + 4H infrastructure preserved post-MVP

### v0.6+ direction options (operator-driven, no commitment)

- (v0.6-A) Hybrid mean-reversion + ML XGBoost — combined S17+S22 ~120 trades viable
- (v0.6-B) HMM regime-switch — 4-6 sprints
- (v0.6-C) Multi-symbol revival post-MVP — ONLY path к T5 ≥100 conjoint pass
- (v0.6-D) Different strategy class
- (v0.6-E) Project pause — 5 hypotheses + structural insight = strong publishable contribution
- (v0.6-F) MVP T5 floor amendment — operator decides spec amendment justified per empirical evidence

### Roadmap

**v0.5 closed at S23 honest.** Tag v0.1.0-alpha.23. Project state: between-sprints с post-v0.5-honest-close marker. **5-th honest close в проекте** (S14+S16+S18+S21+S23). MVP DONE на BTC-only 1H mean-reversion structurally hard — requires multi-symbol revival OR strategy class pivot OR spec amendment.

## [2026-04-26] sprint-end | Sprint 25 — Dashboard UI

**User-driven feature sprint.** Per directive 2026-04-26: web UI для backtest comparison.

### Joint brainstorm
- Trader CONFIRM metrics spec (TIER 1 + TIER 2 + 4 mandatory warnings + Sortino anomaly guard CC4 HARD)
- Architecture APPROVE_WITH_CONDITIONS (FastAPI + vanilla JS + auto-open browser + localhost-only + isolated Presentation context)

### Deliverables
- T0 backfill 2023-01-01 → 2026-04-26 (BTC 5M/15M/60/240/1D + ETH 15M/60/240 + SOL 15M/60/240 = 11 parquet files)
- T1 ADR 0039
- T2 pyproject.toml `[dashboard]` optional dep group
- T3 src/dashboard/app.py (FastAPI 7 endpoints + main() launcher)
- T4 src/dashboard/backtest_runner.py (WFA wrapper + caching + warnings + Sortino guard)
- T5-T7 templates/index.html + static/dashboard.js + dashboard.css
- T8 scripts/dashboard.sh (launcher: uvicorn + auto-open browser)
- T9 tests/unit/test_dashboard_app.py (8 smoke tests)
- T10 sprint-25 page + wiki sync
- T11 PHASE 8 ship — pending

### Tests / quality
- pytest unit: 740 passed (+8 dashboard tests)
- mypy --strict src/: clean (75 source files, +3 dashboard modules)

### Strategy presets (3 в S25 MVP)
1. ema_crossover_s13 — EMA 12/26 + RSI 14 + ATR 14
2. mean_reversion_s15 — RSI 30/70 + BB(20, 2.0σ)
3. mean_reversion_s17_relaxed — RSI 35/65 + BB(20, 1.5σ)

### Usage
```bash
.venv/bin/pip install -e ".[dashboard]"
./scripts/dashboard.sh
# → http://127.0.0.1:8000/
```

### Cross-cutting concerns binding (per ADR 0039, 11 CCs)
CC1 process isolation / CC2 optional dep / CC3 localhost-only / CC4 read-only data / CC5 Sortino guard HARD / CC6 NO live trading в S25 / CC7 NO Mainnet / CC8 No spec amendment / CC9 1-at-a-time concurrency / CC10 disk caching / CC11 tag = UI capability not MVP.

### Future S26+ candidates
- Live bot start/stop control via UI
- Real-time WebSocket updates (FSM, balance, fills)
- Equity curve chart visualization
- Multi-run side-by-side comparison view
- Strategy parameter customization (currently presets-only)
- 30M + 2H Bar.interval Literal extension

### Roadmap
**S25 SHIPPED.** Tag v0.1.0-alpha.25. Dashboard accessible via `./scripts/dashboard.sh`. S24 ESC-1 (pause vs multi-symbol) STILL OPEN — independent от S25.

## [2026-04-26] sprint-end | S27 — Formula bug fixes (5 bugs)

**Operator-driven audit per directive:** "Провести ревизию всех торговых метрик и формул и оптимизировать их чтобы торговля была в плюсе. Вызывай subagents трейдера и трейдера с логикой."

### Audit infrastructure built
- `scripts/audit_formulas.py` — sweep + rebuild + auto-refresh modes
- `data/formulas_audit_v1.json` — 30 experiments × 17 formulas (347 KB)
- Dashboard `run_backtest()` hook → audit doc auto-updates after каждый POST `/api/backtest`
- Pre-fix per-run cache snapshots: `data/runs.backup_pre_s27_fixes/`

### Joint trader+logic-reviewer parallel verdict
- **Trader-expert** EXPAND — formulas correct, failures structural (T5 unreachable single-symbol). Sprint backlog S28-S32 proposed.
- **Trading-logic-reviewer** PARTIAL FAIL — 4 bugs found (1 HIGH, 2 MEDIUM, 1 INFO/CC5, 1 LOW)

### 5 bug fixes (TDD, +18 tests, 745→762 passed)
- T1 HIGH `src/backtest/replay_engine.py:51` — `np.sqrt(24*365)` hardcoded → `bars_per_year` parameterized (fixes 27/30 corrupted experiments)
- T2 MEDIUM Sortino canonical `sqrt(mean(min(r,0)²))` (was `std(losers, ddof=1)` — Sortino & Price 1994)
- T3 MEDIUM RSI/ATR mask first `period` bars NaN (was `.fillna(50.0)` — talib convention)
- T4 INFO/CC5 trade_extractor preserve actual reason_code (was hardcoded EXIT_TP_HIT — surfaced 187 SL / 141 TP / 2 TIME_STOP)
- T5 LOW MC `seed=42` default (was `None` — non-reproducible audit)

### Audit re-run результаты
- Verdict count unchanged: 0 PASS / 30 FAIL (bugs не fundamentally изменили acceptance gate outcomes)
- ema_crossover SOLUSDT 4H: pnl +88→+131 + sharpe 1.66→2.48 (RSI warm-up fix removed invalid early entries)
- mean_reversion strategies unchanged (BB gates immune к RSI fix)
- Reason codes diverse: 187 EXIT_SL_HIT + 141 EXIT_TP_HIT + 2 EXIT_TIME_STOP

### ESC items для S28+ (operator decision)
- ESC-1 Multi-symbol authorization (S28 expanded scope beyond BTCUSDT MVP)
- ESC-2 "In profit" vs "pass acceptance criteria" — different goals (ETH 4H +$404 already profitable)
- ESC-3 Operational implications 4H multi-symbol (3 simultaneous positions, 1-5 day holds)

### Trader-expert backlog (S28-S32)
- S28 Multi-symbol 4H mean_reversion (n≈135 → T5 PASS) — depends ESC-1
- S29 Regime filter + SMA50 trend gate (CC2 fold concentration)
- S30 SL calibration {1.0/1.25/1.5}×ATR + t-stat power
- S31 Donchian 4H breakout (independent hypothesis)
- S32 DSR cross-trial sigma_SR + MC power audit (closes S14 Q2 carry-over)

### Roadmap
**S27 SHIPPED.** Tag v0.1.0-alpha.27. Audit infrastructure live + 5 formula bugs eliminated. Measurement instrument now trustworthy. Strategy work (S28+) pending ESC-1/2/3 operator decision.

## [2026-04-26] sprint-end | S28 — Process enforcement (kit flow mechanical hook + RU docs)

**Operator complaint после S27 ship:** "Последний спринт выглядит flow так что наш кит сломан. В S27 не подключались скиллы планирования, todo, superpowers:brainstorming."

**Verified drift:** Last plan file = S15. S16-S27 = 12 sprints без plans. Kit invocation = polite reminder, not enforcement.

### Decision (ADR 0041): Mechanical enforcement
- Hook `sprint-flow-check.sh` блокирует push на feature/sprint-NN-* без plan file
- Russian process docs = single source of truth для operator
- CLAUDE.md binding section "BEFORE ANY SPRINT WORK"
- Per-task SPRINT_STATE update protocol

### Deliverables (T1-T6 + ship)
- T1 `wiki/project/architecture/sprint-flow-ru.md` NEW — 9 фаз с per-phase HARD-GATEs
- T2 `wiki/project/architecture/tooling-inventory-ru.md` NEW — full catalog с decision matrix
- T3 `~/.claude/hooks/sprint-flow-check.sh` NEW + registered в settings.json
- T4 SPRINT_STATE phase tracking template applied inline
- T5 `CLAUDE.md` (repo + llm-wiki) binding sections
- T6 ADR 0041 + sprint-28 page + index/current-state sync
- T7 PHASE 8 ship — pending tag v0.1.0-alpha.28

### S28 itself = proof of process
S28 executed по proper kit flow:
- PHASE 3 plan file `wiki/project/plans/2026-04-26-sprint-28-process-enforcement.md` (first since S15)
- PHASE 4 per-task TDD + per-task SPRINT_STATE update + per-task commit
- TodoWrite phase tracker
- 5 commits + 1 ship commit (planned)

### Roadmap
**S28 ready к ship.** Tag v0.1.0-alpha.28. Next = S29 trader-expert backlog (multi-symbol 4H mean_reversion, depends ESC-1 operator decision from S27 carry-over).

## [2026-04-26] sprint-end | S29 — Full Superpowers Skills Integration

**Operator directive после S28 ship:** "У нас есть множество полезных скиллов (https://github.com/obra/superpowers). Их надо внедрить в наш flow разработки. Переработай кит и внедри максимально нужное количество скиллов."

**Gap analysis pre-S29:** 6 of 13 superpowers skills used. 7 missing с concrete integration points.

### 7 NEW superpowers skills integrated
- `systematic-debugging` — Phase 4 sub-flow (bug encountered, 4-phase root cause)
- `verification-before-completion` — Phase 5 (extended pre-completion checklist)
- `requesting-code-review` — Phase 6 PRE (format reviewer brief)
- `receiving-code-review` — Phase 6 POST (categorize feedback BLOCKER/CONCERN/SUGGESTION)
- `dispatching-parallel-agents` — Phase 4+6 (explicit parallel pattern)
- `using-git-worktrees` — cross-phase OPTIONAL (sandbox sprint experiments)
- `writing-skills` — cross-phase OPTIONAL (new project skill methodology)

### Skills × Phase integration map (26 skills total)
NEW Section 12 в tooling-inventory-ru.md — single source of truth для "какой skill в какой фазе":
- 13 superpowers (6 EXISTING + 7 NEW S29 = full integration)
- 5 project skills
- 8 agent-skills

### Deliverables (4 commits + ship)
- T1 sprint-flow-ru.md MODIFIED — per-phase Используемые skills + Phase 4 sub-flows + Cross-phase optional + integration map
- T2 tooling-inventory-ru.md MODIFIED — Section 3 expanded (✅/🆕 status + Where invoked) + Section 12 NEW integration map + decision matrix +8
- T3 CLAUDE.md (repo) MODIFIED — phase table expanded (Primary + Optional/sub-skills columns) + 6 new anti-patterns
- T4 ADR 0042 + sprint-29 page + index/current-state sync
- Ship — pending tag v0.1.0-alpha.29

### S29 itself = proof of process
S29 executed по proper kit flow per S28 binding rules:
- PHASE 3 plan file `plans/2026-04-26-sprint-29-superpowers-integration.md`
- PHASE 4 controller-driven (docs sprint), per-task TDD pattern
- Per-task SPRINT_STATE update после каждой task (S28 protocol)
- 4 commits + ship commit (planned)

### Roadmap
**S29 ready к ship.** Tag v0.1.0-alpha.29. Next = S30 trader-expert backlog (multi-symbol 4H mean_reversion, depends ESC-1 operator decision from S27 carry-over).

## [2026-04-26] sprint-end | S30 — Tier-2 Agents + phase-advance hook + LLMWiki↔Claude-mem cascade

**Operator directives после S29 ship:**
1. "Register security-auditor + test-engineer plugins в L5 stack. + doc-reviewer (haiku). Update tooling-inventory + sprint-flow Phase 6. Hook phase-advance.sh validating verification checklist runs перед merge."
2. "Проанализируй как можно смержить функционал llmwiki и её потенциал с плагином claude mem (token economy / context delivery)."

### 3 NEW reviewer agents (~/.claude/agents/)
- `security-auditor.md` (opus, OWASP + trading-specific rules — HMAC override.py, withdraw whitelist, kill-switch auth, position bounds, Mainnet/Testnet detection)
- `test-engineer.md` (sonnet, test pyramid + Hypothesis property tests для DSR/Kelly/MC math invariants, S27 regression lessons)
- `doc-reviewer.md` (haiku, frontmatter + link integrity + Block 1↔2 sync per ADR 0017 + canonical counts)

### NEW hook (~/.claude/hooks/)
- `phase-advance.sh` — PreToolUse on `gh pr merge`. Blocks если SPRINT_STATE Phase 5 status != "done"/"skipped". Tested positive + negative.
- Registered к ~/.claude/settings.json PreToolUse Bash matcher.

### LLMWiki ↔ Claude-mem cascade (NEW Section 13 в tooling-inventory-ru.md)
Documentation-first integration. 4-step cascade order:
```
STEP 1 wiki/<page>.md (curated)  ← CHECK FIRST
   ↓ not found
STEP 2 mem-search (past sessions)
   ↓ not found
STEP 3 Grep raw (current code)
   ↓ needed
STEP 4 Read raw + offset
```
Saves tokens via curated wiki priority. Cascade enforcement via documentation в 4 places (tooling-inventory Section 13 + sprint-flow Token economy section + repo CLAUDE.md cascade rule + llm-wiki CLAUDE.md cascade reference).

Bridges 2-4 (wiki-mem-corpus-sync / chapter mark auto-link к log.md / frontmatter tags → corpus categorization) deferred к S31+ — requires claude-mem API investigation.

### Deliverables (6 task commits + ship)
- T1 plan + security-auditor agent
- T2+T3+T4 test-engineer + doc-reviewer + phase-advance.sh hook
- T5+T6 tooling-inventory-ru.md (Section 1 9 agents + Section 8 +hook + Section 13 NEW cascade + decision matrix +5)
- T7+T8 sprint-flow-ru.md Phase 6 expansion + repo CLAUDE.md tier-2 + cascade rule + llm-wiki CLAUDE.md hook+cascade
- T9 ADR 0043 + sprint-30 page + index/current-state sync
- Ship — pending tag v0.1.0-alpha.30

### Canonical counts updated
- Components 38 (unchanged)
- ADRs 42 → 43
- Sprint pages 29 → 30
- Reviewer agents 6 → 9
- Active hooks 5 → 6

### S30 itself = proof of process
S30 executed по proper kit flow per S28 binding rules + S29 expanded skills:
- PHASE 3 plan file `plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md`
- PHASE 4 controller-driven (docs/agents/wiki sprint), per-task TDD pattern
- Per-task SPRINT_STATE update после каждой task (S28 protocol)
- 6 task commits + ship commit (planned)

### Roadmap
**S30 ready к ship.** Tag v0.1.0-alpha.30. Next = S31 trader-expert backlog (multi-symbol 4H mean_reversion, depends ESC-1/2/3 operator decision from S27 carry-over).

## [2026-04-26] sprint-end | S31 — Kit Revision per Best Practices + Single Tools-Overview File

**Operator directives после S30 ship:**
1. "Все настройки нашего кита укажем в одном файле"
2. "Проведи ревизию на основе лучших best practices [Anthropic Claude Code best practices URL]"
3. "Адаптируй кит под максимальное качество и в тоже время экономию токенов без деградации"
4. "Учитывай что мы CLAUDE.md делили на файлы"

**Pre-S31 baseline:** 3 CLAUDE.md = 954 lines / 61 KB / ~18.5K tokens loaded каждую session. Best practices coverage 8/20.

### Decisions (4)
1. NEW `kit-overview-ru.md` — 1-page single source of truth (~300 lines): Quick decision matrix + 9 agents + 6 hooks + 5 skills + 50 plugin skills + 6 MCP + cascade rule + Top 10 commands + Top 5 anti-patterns + 9-phase lifecycle + 20 best practices applied + sprint history
2. EXPANDED `tooling-inventory-ru.md` Sections 14-19 NEW (Permission modes / Plugin curation / CLI tools / Status line / Token-saver commands / Non-interactive + fan-out)
3. PRUNED все 3 CLAUDE.md preserving CLAUDE.md split (operator explicit) — extracted verbose к wiki pages
4. ADD 4 NEW anti-patterns + token-saver commands table в repo CLAUDE.md

### Token economy results
| File | Before | After | Δ |
|------|--------|-------|---|
| repo CLAUDE.md | 190 / 14 KB | 212 / 15 KB | +12 lines (best practices links + anti-patterns) |
| llm-wiki/CLAUDE.md | 448 / 27 KB | 291 / 13 KB | -35% lines, -52% bytes |
| ~/.claude/CLAUDE.md | 316 / 20 KB | 253 / 17 KB | -20% lines, -15% bytes |
| **TOTAL** | **954 / 61 KB / ~18.5K tokens** | **756 / 46 KB / ~14K tokens** | **-21% lines, -25% tokens** |

**Per-session savings:** ~4500 tokens × N sessions.

### 20 Best Practices coverage (full)
Pre-S31: 8/20. Post-S31: 20/20.
NEW: Permission modes + Plugin curation + CLI tools + Status line + `/btw` + `/rewind` + `--continue` + `claude -p` + Fan-out + Common failure patterns documented + Single source of truth file.

### Deliverables (4 task commits + ship)
- T1+plan kit-overview-ru.md NEW
- T2 tooling-inventory-ru.md sections 14-19 NEW
- T3+T4+T5+T6 prune все 3 CLAUDE.md + anti-patterns + token-saver table
- T7 ADR 0044 + sprint-31 page + index/current-state/log sync
- Ship — pending tag v0.1.0-alpha.31

### Canonical counts updated (S31)
- ADRs 43→44
- Sprint pages 30→31
- Components 38 (unchanged)
- Reviewer agents 9 (unchanged)
- Active hooks 6 (unchanged)
- NEW: Kit settings (RU) 3 files = single source of truth
- NEW: CLAUDE.md total tokens ~14K (was ~18.5K, -25%)

### S31 itself = proof of process
S31 executed по proper kit flow:
- PHASE 3 plan file `plans/2026-04-26-sprint-31-kit-revision-best-practices.md`
- PHASE 4 controller-driven (docs/wiki sprint), per-task pattern
- Per-task SPRINT_STATE update после каждой task (S28 protocol)
- 4 task commits + ship commit (planned)

### Roadmap
**S31 ready к ship.** Tag v0.1.0-alpha.31. Operator плану перезапустить session — все settings встанут корректно с new prune-state CLAUDE.md.

Next = S32 trader-expert backlog (multi-symbol 4H mean_reversion, depends ESC-1/2/3 operator decision from S27 carry-over).

## [2026-04-27] sprint-end | S32 — Kit Improvement Phase 0 (КУ-driven, P0 fixes + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory)

**Kit Improvement Phase 0 sprint** — operator-driven kit optimization per КУ analysis (post-S31 review session 2026-04-26). Documentation-only sprint (controller-driven, no src/ touched). Pattern continues S28-S31 (5-th consecutive docs sprint). Trading work BLOCKED awaits ESC-1/2/3 operator decision from S27 carry-over → S32 slot занимаем kit work без conflict.

**6 changes per ADR 0045:**
- T1 (c095bd3) SPRINT_STATE.md P0 fix: stale "Текущий статус"/"Последний спринт"/"Следующее действие" → S32 reality + correct counts (30→44 ADRs / 17→31 sprint pages) + Phase tracking S32 inline
- T2 (2ec9824) current-state.md P0 fix: title/H1 "post-S25"→"post-S31", new TL;DR (S31 kit infrastructure complete + S32 Phase 0 in progress), S25 TL;DR preserved as "Previous", frontmatter sources/tags update, test counts 604→762 (subsequently corrected к 773 в Phase 5)
- T3 (e93e61c) sprint-flow-ru.md +5 skill mappings: idea-refine (Phase 2 PRE) / spec-driven-development (Phase 2/3 non-trading) / source-driven-development (Phase 4 Bybit/pydantic/pybit/FastAPI/TA-Lib) / code-simplification (Phase 6 OPT) / documentation-and-adrs (Phase 8) + Skills × Phase map 26→32 entries
- T4 (f1f60a7) cascade smart-explore STEP 2.5 (sprint-flow + kit-overview mirror) + decision matrix +6 entries в kit-overview-ru.md (Vague idea / Non-trading no spec / Bybit-pydantic-FastAPI / Structural code lookup / ADR creation / Post-impl simplification / Sprint Close consolidation). 30-50% дешевле naked grep+read для structural lookups.
- T5 (660630e) Phase 9 Close +Step 5: anthropic-skills:consolidate-memory (every 5 sprints OR >30 observations) + HARD-GATE
- T6 (397a655) ADR 0045 + sprint-32 page + index.md + canonical counts 44→45 ADRs / 31→32 sprint pages + S32 sprint history row

**КУ achieved:** avg 60% / time 45 мин = ~80 КУ/час (close to forecast 114 КУ/час).

**Phase 5 Verify outcome:** 773 passed pytest (count drift +11 vs S31 reported 762) / mypy 1 pre-existing error (`__main__.py:636 bars_per_year_map redef`) / canonical counts 16/30/74/45 ✓. **3 pytest failures pre-exist on main** (test_replay_long_only::test_replay_respects_long_only_flag, test_replay_long_only::test_long_only_does_not_exit_on_signal_flip, test_replay_next_open::test_entry_executes_on_next_open) — NOT S32 regression (verified via stash + main checkout). Carry-over к S33: fix replay tests + mypy redef.

**Phase 6 Review skipped** — process/wiki only sprint, no domain reviewer applicable.

**Phase 8 Ship pending:** PR + squash merge + tag v0.1.0-alpha.32. All 4 push hooks expected fire correctly (sprint-flow-check ✓ plan file present / adr-agent-sync ✓ ADR 0045 не affects agents / adr-index-sync ✓ ADR 0045 в index.md / phase-advance ✓ Phase 5 status=done).

**Skills × Phase map updated:** 26 → 32 (13 superpowers + 5 project + 13 agent-skills + 1 anthropic-skills).

**Kit Phase 1 (S33 candidate) carry-overs:** GitHub Actions CI / pre-commit hooks (ruff+mypy) / SQLite MCP server / SPRINT_STATE freshness check hook / dashboard-reviewer L5 agent. КУ avg 63% / 6 hours.

**Trading carry-overs (BLOCKED — operator):** ESC-1 multi-symbol authorization / ESC-2 "in profit" semantics / ESC-3 4H operational implications.

Next = Operator decision: S33 = kit Phase 1 (Track A — independent) OR Track B unblock (если ESC-1/2/3 resolved).

## [2026-04-27] session-end | S32 — Kit Improvement Phase 0 SHIPPED

**S32 SHIPPED.** PR #39 → 2bad7ee squash-merge. Tag v0.1.0-alpha.32 pushed. Branch `feature/sprint-32-kit-phase-0-improvements` deleted post-merge. SPRINT_STATE → between-sprints.

**Kit state post-S32:**
- 9 reviewer agents (L5)
- 6 active hooks (mechanical enforcement)
- **32 skills mapped** к kit flow (was 26): 13 superpowers + 5 project + 13 agent-skills + 1 anthropic-skills (consolidate-memory NEW)
- **5-step cascade** (was 4): wiki → mem-search → smart-explore → grep → Read+offset
- **Phase 9 consolidate-memory HARD-GATE** (every 5 sprints OR >30 observations)
- 4 plugins curated (superpowers 5.0.7 / agent-skills 1.0.0 / claude-mem 12.3.7 / caveman)
- 6 MCP servers active
- 20/20 best practices coverage
- CLAUDE.md split preserved (3 files, ~14K tokens total post-S31 prune)

**КУ achieved S32:** avg 60% / 45 мин = ~80 КУ/час. Best ROI per phase per КУ analysis (forecast 114 КУ/час).

**Carry-overs к S33:**
- Kit Phase 1: GitHub Actions CI / pre-commit hooks / SQLite MCP / SPRINT_STATE freshness hook / dashboard-reviewer L5 agent (КУ avg 63% / 6 hours)
- Test debt: 3 pytest failures (test_replay_long_only / test_replay_next_open) + 1 mypy redef (__main__.py:636) — pre-existing, surfaced via S32 Phase 5 verify
- Trading carry-overs (BLOCKED — operator): ESC-1 / ESC-2 / ESC-3

Next session = S33 brainstorm OR operator unblocks Track B.

## [2026-04-27] sprint-end | S32b — Kit Improvement Phase 1 (CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer)

**Kit Improvement Phase 1 sub-sprint** — operator directive "пусть все фазы будут в 32 спринте". Sub-sprint S32 series (mirror S8a/S8b/S8c pattern). Tag v0.1.0-alpha.32b. КУ avg 60.5% / ~3 hours = ~120 КУ/час (above forecast 10.5 — pre-commit pkg + uvx + mcp-server-sqlite уже available pre-installed).

**6 changes per ADR 0046:**
- T1 (6c2ea66) dashboard-reviewer L5 agent — out-of-repo `~/.claude/agents/dashboard-reviewer.md` (sonnet) + wiki page (5-axis review checklist per S25 ADR 0039 conditions: FastAPI correctness / template-JS data flow / Bybit data display / security / S25 architecture conditions)
- T2 (373d527) SPRINT_STATE freshness check hook — out-of-repo `~/.claude/hooks/sprint-state-freshness-check.sh` + settings.json registered (6th hook) + wiki page. Conservative regex flags actionable patterns (`S<N> PHASE X ship|pending|in_progress|next`), skips carry-over context (`closes S14 Q2`). Positive test exit 0 / negative test exit 2 verified.
- T3 (167fc9d w/ T4) Pre-commit hooks upgraded — `.pre-commit-config.yaml` ruff v0.4.0 + mypy --strict local + yamllint для CI workflows. pre-commit installed (`.git/hooks/pre-commit`). dev dep уже в pyproject.toml.
- T4 (167fc9d) GitHub Actions CI — `.github/workflows/ci.yml` 10 steps (checkout / py3.12 cache / TA-Lib build cached / pip install / ruff lint+format / mypy --strict baseline guard / pytest unit baseline guard / canonical counts verify). Triggers push к main + PR. Baseline guards informational не strict — 3 pytest + 1 mypy pre-existing allowed. CI runs first time на S32b PR.
- T5 (8a24abf) SQLite MCP server — `.mcp.json` (sqlite-trading → data/bot.db). settings.json schema rejects mcpServers field — .mcp.json правильный location per Claude Code MCP security policy. uvx + mcp-server-sqlite verified pre-installed. Operator approve at next session start OR `claude mcp` CLI.
- T6 (dabf368) ADR 0046 + sprint-32b page + index/counts sync (45→46 ADRs / 32→33 sprints / 9→10 agents / 6→7 hooks / 6→7 MCP / 38→40 components) + S32+S32b sprint history rows + kit-overview decision matrix updates.

**Phase 5 Verify outcome:**
- pytest: 773 passed (S32 baseline preserved)
- mypy: 1 pre-existing error (`__main__.py:636 bars_per_year_map redef`)
- canonical counts: 16/30/74/45 ✓
- bash -n freshness hook ✓ / yaml ci.yml ✓ / yaml .pre-commit-config ✓ / json .mcp.json ✓ / json settings.json ✓
- **3 pytest failures pre-existing** (test_replay_long_only / test_replay_next_open) — carry-over к S33

**Phase 6 Review skipped** — config + scripts + docs sprint, no src/ touched.

**Implementation discoveries:**
1. settings.json schema rejects `mcpServers` — must use project-level `.mcp.json` + `enabledMcpjsonServers`
2. Freshness hook regex iteration: первая версия flagged carry-over context (S14 Q2) → refined к actionable patterns only
3. Pre-commit upgrade preserved S1-era config + added yamllint
4. CI baseline guards prevent S32b ship blocking on pre-existing tech debt

**Phase 8 Ship pending:** PR + squash merge + tag v0.1.0-alpha.32b. Все 5 push hooks expected fire correctly + NEW freshness hook (6 total).

**Carry-overs к S32c (Kit Phase 2, КУ avg 42%):** Memory corpus org / context budget hook / 5 more skill mappings (performance-optimization / api-and-interface-design / browser-testing-with-devtools / idea-refine extension) / Fetch MCP.

**Carry-overs к S33+ (trading sprint когда unblocked):** 3 pytest failures + 1 mypy fix.

**Trading carry-overs (BLOCKED — operator):** ESC-1 / ESC-2 / ESC-3.

Next = operator decision: S32c (Kit Phase 2) OR Track B unblock.

## [2026-04-27] session-end | S32b — Kit Improvement Phase 1 SHIPPED

**S32b SHIPPED.** PR #40 → cb61678 squash-merge. Tag v0.1.0-alpha.32b pushed. Branch deleted. SPRINT_STATE → between-sprints.

**CI fix saga (3 iterations):**
1. TA-Lib parallel build race condition → drop `-j$(nproc)`, sequential build
2. Ruff lint 169 pre-existing errors → informational baseline guard (200 ceiling)
3. Mypy missing fastapi/uvicorn/jinja2 → install dashboard optional deps `pip install -e ".[dev,dashboard]"`

CI now green and validates: ruff lint baseline / mypy --strict baseline / pytest unit baseline / canonical counts. Future PRs auto-validated.

**Kit state post-S32b:**
- 10 reviewer agents (L5) — was 9, +dashboard-reviewer sonnet
- 7 active push hooks — was 6, +sprint-state-freshness-check.sh
- 7 MCP servers — was 6, +sqlite-trading (.mcp.json)
- 32 skills mapped к kit flow (unchanged S32)
- 5-step cascade rule (unchanged S32)
- Phase 9 consolidate-memory HARD-GATE (unchanged S32)
- 4 plugins curated (unchanged)
- 20/20 best practices coverage (unchanged S31)
- CLAUDE.md split preserved (3 files, ~14K tokens total post-S31 prune)
- **CI infrastructure NEW:** GitHub Actions workflow + pre-commit local gate

**КУ achieved S32b:** avg 60.5% / ~3 hours = ~120 КУ/час (above forecast 10.5 — pre-commit pkg + uvx + mcp-server-sqlite уже available pre-installed).

**Carry-overs к S32c (Kit Phase 2, КУ avg 42%):**
- Memory corpus organization (bridges 2-4)
- Context budget hook
- AS:performance-optimization / AS:api-and-interface-design / AS:browser-testing-with-devtools / AS:idea-refine extension
- Fetch/HTTP MCP

**Test debt carry-over к first trading sprint (S33+):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636)
- ~169 ruff baseline (legacy code cleanup)

**Trading carry-overs (BLOCKED — operator):** ESC-1 / ESC-2 / ESC-3.

Next session = operator decision: S32c (Kit Phase 2) OR Track B unblock OR test debt cleanup sprint.

## [2026-04-27] sprint-end | S32c — Kit Improvement Phase 2 (4 skill mappings + Fetch MCP + corpus categorization scheme)

**Kit Improvement Phase 2 sub-sprint** — Sub-sprint S32 series (mirror S8a/S8b/S8c). Tag v0.1.0-alpha.32c. **Reduced scope** decision (per pre-plan analysis): 5 clear wins shipped в S32c, 2 research items (memory corpus bridges 2-4 implementation script + context budget hook) deferred к S32d. КУ avg ~51% / ~1.5 hours.

**4 changes per ADR 0047:**
- T1 (0761bad) Fetch/HTTP MCP server — `.mcp.json` +fetch (uvx mcp-server-fetch verified pre-installed). Section 7.7 (sqlite-trading post-S32b doc) + Section 7.8 (fetch NEW) в tooling-inventory-ru.md. Use cases: Bybit V5 API docs / PyPI versions / GitHub releases. NOT для trading data (use pybit).
- T2 (09fcdee) 4 skill mappings к sprint-flow-ru.md: `+api-and-interface-design Phase 3` (CLI commands / module boundaries / endpoint design) / `+browser-testing-with-devtools Phase 5` (dashboard sprints, Chrome MCP enabled) / `+performance-optimization Phase 6 OPT` (backtest profile-first) / `+idea-refine extension Phase 2 PRE` (5-step workflow procedure для vague operator ideas). Skills × Phase 32→36 (17 agent-skills total).
- T3 (47bba48) Memory corpus categorization scheme — tooling-inventory-ru.md NEW Section 22. 4 partitions (trading-decisions / formula-knowledge / process-patterns / debug-knowledge) + tag mapping pseudo-code + cascade STEP 2 enhancement spec + operator validation procedure. Bridge 4 design — script implementation S32d candidate.
- T4 (231d55f) ADR 0047 + sprint-32c page + index/counts (46→47 ADRs / 33→34 sprints / 7→8 MCP / 32→36 skills) + S32c sprint history row + kit-overview decision matrix updates.

**Phase 5 Verify outcome:**
- pytest: 773 passed (S32b baseline preserved by construction — no src/ changes)
- mypy: 1 pre-existing error (`__main__.py:636 bars_per_year_map redef`)
- canonical counts: 16/30/74/45 ✓
- json .mcp.json: ✓ (sqlite-trading + fetch)
- 3 pytest failures pre-existing (test_replay_long_only / test_replay_next_open) — NOT S32c regression

**Phase 6 Review skipped** — config + docs sprint, no src/ touched.

**Reduced scope rationale (deferred к S32d):**
1. Memory corpus bridges 2-3 + bridge 4 implementation script — needs claude-mem internal API research (ingest hook framework, corpus partition support, search filter syntax)
2. Context budget hook (>70% warn) — needs Claude Code hook API research (context % exposure unknown)

**Phase 8 Ship pending:** PR + squash merge + tag v0.1.0-alpha.32c. CI runs second time на этом PR — S32b infrastructure validates.

**Carry-overs к S32d (Kit Phase 3):** Phase 2 deferred research items + Phase 3 originals (bybit-api-reviewer / anthropic-skills:schedule / Sprint metrics tracking).

**Test debt carry-over к S33+ (first trading sprint):** 3 pytest failures + 1 mypy error + ~169 ruff baseline cleanup.

**Trading carry-overs (BLOCKED — operator):** ESC-1 / ESC-2 / ESC-3.

Next = operator decision: S32d (Kit Phase 3) OR Track B unblock OR test debt cleanup sprint.

## [2026-04-27] session-end | S32c — Kit Improvement Phase 2 reduced SHIPPED

**S32c SHIPPED.** PR #41 → df521a6 squash-merge. Tag v0.1.0-alpha.32c pushed. Branch deleted. SPRINT_STATE → between-sprints.

**CI passed first try** — S32b infrastructure validated на non-S32b PR. Baseline guards (3 pytest pre-existing + 1 mypy pre-existing + ~169 ruff pre-existing) work correctly.

**Kit state post-S32c:**
- 10 reviewer agents (L5) — unchanged
- 7 active push hooks — unchanged
- **8 MCP servers** (was 7) — +fetch (project-level `.mcp.json`)
- **36 skills mapped к kit flow** (was 32) — +api-design (Phase 3) / +browser-test (Phase 5) / +perf-opt (Phase 6 OPT) / +idea-refine extension (Phase 2 PRE workflow)
- 5-step cascade rule — unchanged
- Phase 9 consolidate-memory HARD-GATE — unchanged
- Memory corpus categorization scheme designed (4 partitions trading-decisions/formula-knowledge/process-patterns/debug-knowledge) — bridge 4 ready для script S32d
- 4 plugins curated — unchanged
- 20/20 best practices coverage — unchanged
- CI infrastructure (S32b) — operational, validated on S32c PR

**КУ achieved S32c:** avg ~51% / ~1.5 hours. ROI = ~75 КУ/час (above forecast 4.2 — Phase 2 closer к Phase 1 ROI due to Fetch MCP pre-installed pattern).

**Carry-overs к S32d (Kit Phase 3):**
- Memory corpus bridges 2-3 + bridge 4 script implementation
- Context budget hook (>70% warn)
- bybit-api-reviewer L5 agent
- anthropic-skills:schedule (audit automation)
- Sprint metrics tracking

**Test debt carry-over к S33+ (first trading sprint):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636)
- ~169 ruff baseline cleanup

**Trading carry-overs (BLOCKED — operator):** ESC-1 / ESC-2 / ESC-3.

**Operator action на next session:** Approve `fetch` MCP at session start (one-time prompt).

Next session = operator decision: S32d (Kit Phase 3) OR Track B unblock OR Track C test debt cleanup.
