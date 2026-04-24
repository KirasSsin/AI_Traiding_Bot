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
