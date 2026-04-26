---
title: Current State — post-S31 inventory + canonical counts (Kit infrastructure complete, S32 Kit Phase 0 in progress)
type: architecture
tags: [current-state, inventory, baseline, canonical-counts, sprint-31, kit-revision-best-practices, kit-infrastructure-complete, sprint-32-pending, t5-100-structurally-unreachable, regime-independent-edge, esc-1-2-3-pending]
created: 2026-04-19
updated: 2026-04-27
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

# Current State (post-S31, 2026-04-27) — Kit infrastructure complete (S32 Kit Phase 0 in progress)

**TL;DR (post-S31):** Live state on tag `v0.1.0-alpha.31`. **Kit infrastructure layer COMPLETE post-S31:** 9 reviewer agents (L5) + 6 active hooks (mechanical enforcement) + 26 skills mapped к 9-phase flow + 4 plugins curated + 6 MCP servers + 5-step cascade rule + 20/20 best practices coverage. CLAUDE.md split preserved across 3 files (repo + llm-wiki + ~/.claude), pruned -25% tokens (954→756 lines, 61→46KB) per S31. **Kit-overview-ru.md** = single source of truth gateway. **Tooling-inventory-ru.md** Sections 14-19 (Permission modes / Plugin curation / CLI tools / Status line / Token-saver / Non-interactive). **S32 Kit Phase 0 in progress** (this sprint): P0 staleness fixes + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory. **Strategy/trading work BLOCKED** awaiting operator decision on ESC-1 (multi-symbol authorization), ESC-2 ("in profit" semantics), ESC-3 (4H operational implications). Pre-S32 КУ analysis showed kit Phase 0 = 57% avg КУ за 45 мин → highest ROI. Phase 1 (CI/SQLite MCP/freshness hook/dashboard-reviewer) deferred к S33.

**Previous TL;DR (post-S25 Dashboard, preserved для context):** Live state on tag `v0.1.0-alpha.25`. **S25 Dashboard sprint** shipped HTML+JS UI для backtest comparison через FastAPI на localhost. NEW Presentation context (`src/dashboard/`). 3 strategy presets, 5 timeframes (5M/15M/60/240/1D), 3 symbols (BTC/ETH/SOL). Backfill 2023-01-01 → 2026-04-26. Trader spec applied: TIER 1 + TIER 2 metrics + 4 mandatory warnings + Sortino anomaly guard. Architecture pattern: localhost-only FastAPI + vanilla JS + auto-open browser + optional dep group. NO live trading через dashboard. NO Mainnet support (TESTNET=true enforced). **MVP status unchanged:** strategy validation NEGATIVE (5 hypotheses tested, all FAIL conjoint per S23 honest close). Dashboard позволяет user visualize previous + future backtest runs via UI.

**Previous TL;DR (v0.5 honest close, preserved для context):** v0.5 closed honest at S23 — 5 strategy hypotheses tested across 4.81y BTC, all FAIL conjoint. CC1 T5 100 structurally unreachable BINDING (3 timeframes empirical). CC3 Strategy edge regime-INDEPENDENT (S17+S22 both 5/6+DSR+MC PASS). 5-th honest close в проекте (S14+S16+S18+S21+S23). **v0.5 closed honest:** 5 strategy hypotheses tested across 4.81y Bybit Spot BTCUSDT — all FAIL conjoint per acceptance-criteria.md. S13 EMA crossover 1H / S15 mean-reversion multi-symbol 1H / S17 mean-reversion BTC 1H relaxed (59 trades, 5/6+DSR+MC PASS) / S20 mean-reversion BTC 15M (73 trades, T1=-45.57 Hudson&Urquhart validated) / S22 mean-reversion BTC 4H (62 trades, **5/6+DSR+MC PASS regime-independent**). **CRITICAL INSIGHT BINDING:** T5 floor 100 STRUCTURALLY UNREACHABLE на BTC-only mean-reversion (3 timeframes ~60-73 trades all). T5 only reachable via multi-symbol (out of MVP) OR strategy class change. **`data/cross_trial_sharpes.json` archived к `_v0.5-final.json`, reset к `[]` для v0.6** (4-th archival, mirrors S16/S18/S21). **5-th honest close в проекте (S14+S16+S18+S21+S23).** Strategy edge regime-INDEPENDENT (S17+S22 both PASS): combined ~120 trades available для v0.6-A small-sample ML training. **v0.6+ options:** A hybrid ML / B HMM regime-switch / C multi-symbol revival post-MVP / D different strategy class / E pause / F MVP T5 floor amendment (operator decides spec amendment justified per empirical evidence).

**Pre-S1 historical state** archived в section "Pre-S1 Legacy" внизу.

## Canonical counts (live, MUST be kept current per dev-workflow.md PHASE 8 step 5a HARD-GATE)

| Metric | Value | Source of truth | Last update |
|--------|-------|-----------------|-------------|
| FSM states | **16** | `src/execution/state_machine.py` `ExecutionState` enum | S6 (ADR 0020) |
| FSM events | **30** | `src/execution/state_machine.py` `ExecutionEvent` enum | S8a (ADR 0022, +KILL_SWITCH_REQUESTED) |
| FSM transitions | **74** | `src/execution/state_machine.py` `TRANSITIONS` dict | S8b T7 (ADR 0023, +1 FLAT,RISK_HALT) |
| Reason codes | **45** | `src/risk/reason_codes.py` `ReasonCode` enum | S8a (ADR 0022 G5, +HALT_RUNTIME_CRASH/HALT_BAR_POLL_STALL/KILL_SWITCH_REQUESTED) |
| Component pages | **40** | `wiki/project/components/*.md` (incl. README.md cluster index) | S32b +2 components (dashboard-reviewer-agent + sprint-state-freshness-hook) |
| ADRs | **46** | `wiki/project/decisions/*.md` (0001-0046) | S32b (ADR 0046 — Kit Phase 1) |
| Sprint pages | **33** | `wiki/project/sprints/sprint-*.md` (sprint-01..sprint-32 + sprint-08a/b/c + sprint-32b, minus S24+S26) | S32b (sprint-32b-kit-phase-1-improvements) |
| Reviewer agents | **10** | `~/.claude/agents/` (out-of-repo) | S32b +1 (dashboard-reviewer sonnet) |
| Active push hooks | **7** | `~/.claude/hooks/` (PreToolUse Bash) | S32b +sprint-state-freshness-check.sh |
| MCP servers | **7** | settings.json + .mcp.json | S32b +sqlite-trading (.mcp.json project-level) |
| CI gates | **YES** | `.github/workflows/ci.yml` (push к main + PR) | S32b NEW — pytest + mypy + ruff + canonical counts |
| Pre-commit gates | **YES** | `.pre-commit-config.yaml` (ruff + mypy + yamllint) | S32b upgraded from S1-era basic config |
| Skills × Phase mapped | **32** | sprint-flow-ru.md Skills × Phase integration map | S32 +5 AS (idea-refine/spec/source/code-simpl/docs-adrs) +1 anthropic (consolidate-memory) |
| **Kit settings (RU)** | **3 files** | kit-overview-ru.md (S31) / sprint-flow-ru.md (Phase 9 +consolidate-memory step S32) / tooling-inventory-ru.md (19 sections) | S31 single source of truth + S32 cascade STEP 2.5 |
| **CLAUDE.md total tokens** | **~14K (was 18.5K)** | repo + llm-wiki + ~/.claude (3 files, S28 split preserved) | S31 prune -25% per session (S32 no CLAUDE.md changes) |

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
| S26 | (no ADR) | v0.1.0-alpha.26 | 2026-04-26 | Dashboard UI redesign — Bloomberg-pro × refined CRT aesthetic + Documentation tab. NO architecture changes — pure UI/CSS/JS работа. JetBrains Mono + Fraunces typography. README.md added для launch instructions. |
| **S27** | **0040** | **v0.1.0-alpha.27** | **2026-04-26** | **Formula bug fixes sprint** — operator-driven audit per directive ("ревизия всех торговых метрик и формул"). Built `scripts/audit_formulas.py` (30-experiment sweep + 17 formulas inventoried + dashboard auto-refresh hook). Trader+logic-reviewer parallel brainstorm: trader EXPAND (formulas correct, structural failures), logic-reviewer PARTIAL FAIL 4 bugs. **5 bugs fixed TDD:** T1 HIGH replay_engine bars_per_year (corrupted 27/30 experiments) / T2 MEDIUM Sortino canonical Sortino & Price 1994 / T3 MEDIUM RSI/ATR warm-up gating / T4 INFO/CC5 trade_extractor preserve actual reason_code / T5 LOW MC seed=42 default. Sweep re-run preserved verdict counts (0/30 PASS — failures structural не bugs) but reason codes diverse (187 SL / 141 TP / 2 TIME_STOP) + ema_crossover SOL 4H pnl improved. ESC-1/2/3 для S28+ pending operator. Trader-expert backlog S28-S32. 762 passed pytest (+18 new). |
| **S28** | **0041** | **v0.1.0-alpha.28** | **2026-04-26** | **Process enforcement sprint** — operator-driven correction после S27 complaint ("кит сломан, не подключались скиллы планирования / brainstorming"). Verified 12-sprint drift (S16-S27 без plan files в `wiki/project/plans/`). **Mechanical enforcement:** `~/.claude/hooks/sprint-flow-check.sh` NEW pre-push hook блокирует push на feature/sprint-NN-* без plan file. **Russian process docs:** `sprint-flow-ru.md` (9 фаз с per-phase HARD-GATEs + anti-patterns) + `tooling-inventory-ru.md` (catalog 6 agents + 5 project skills + 13 superpowers + 21 agent-skills + 7 claude-mem + 5 caveman + 6 MCP + 5 hooks + decision matrix). **CLAUDE.md updates:** "BEFORE ANY SPRINT WORK" binding section. **SPRINT_STATE template:** per-phase tracking + Phase 4 task progress subtable applied inline. **Per-task SPRINT_STATE update protocol BINDING.** No code changes (process/wiki only). S28 itself executed по proper flow (PHASE 1-9 demonstrated — first sprint после S15 с plan file). |
| **S29** | **0042** | **v0.1.0-alpha.29** | **2026-04-26** | **Full Superpowers Skills Integration sprint** — operator-driven kit upgrade per directive ("их надо внедрить в наш flow разработки"). Pre-S29 only 6/13 superpowers skills использовались. **7 NEW skills integrated** в kit flow: systematic-debugging (Phase 4 sub-flow bug encountered) / verification-before-completion (Phase 5 extended checklist) / requesting-code-review (Phase 6 PRE format brief) / receiving-code-review (Phase 6 POST categorize feedback) / dispatching-parallel-agents (Phase 4+6 explicit parallel pattern) / using-git-worktrees (cross-phase OPTIONAL sandbox) / writing-skills (cross-phase OPTIONAL new project skill methodology). **Skills × Phase integration map** NEW section в tooling-inventory-ru.md — 26 skills mapped к kit flow (13 superpowers + 5 project + 8 agent-skills). 5 wiki files updated. NO code changes. 762 pytest preserved. |
| **S30** | **0043** | **v0.1.0-alpha.30** | **2026-04-26** | **Tier-2 Agents + phase-advance hook + LLMWiki↔Claude-mem cascade sprint** — operator-driven kit hardening. **3 NEW reviewer agents** (out-of-repo): security-auditor opus (OWASP + trading-specific HMAC/withdraw/kill-switch rules) / test-engineer sonnet (test pyramid + Hypothesis property tests + S27 lessons) / doc-reviewer haiku (frontmatter + links + Block 1↔2 sync). **NEW hook** phase-advance.sh — pre-merge Phase 5 verify enforcement (blocks `gh pr merge` если SPRINT_STATE Phase 5 != done/skipped). **LLMWiki ↔ Claude-mem cascade rule** documentation-first: 4-step (wiki→mem→grep→raw), saves tokens via curated wiki priority. NEW Section 13 в tooling-inventory-ru.md + Token economy section в sprint-flow-ru.md + cascade в repo+llm-wiki CLAUDE.md. Bridges 2-4 (corpus sync / chapter mark auto-link / frontmatter tags) deferred к S31+. NO code changes. 762 pytest preserved. 9 agents + 6 hooks active. |
| **S31** | **0044** | **v0.1.0-alpha.31** | **2026-04-26** | **Kit Revision per Best Practices + Single Tools-Overview File sprint** — operator-driven kit optimization per Anthropic Claude Code best practices. **NEW** `kit-overview-ru.md` — 1-page TL;DR single source of truth для всех kit settings (Quick decision matrix + 9 agents + 6 hooks + 5 skills + 50 plugin skills + 6 MCP + cascade rule + Top 10 commands + Top 5 anti-patterns + 9-phase lifecycle + 20 best practices applied + sprint history). **EXPANDED** tooling-inventory-ru.md Sections 14-19 NEW: Permission modes (default/auto/sandbox) / Plugin curation (4 plugins versions) / CLI tools explicit list / Status line / Token-saver commands / Non-interactive + fan-out patterns. **PRUNED** все 3 CLAUDE.md per best practices ("bloated CLAUDE.md = ignored rules"): total 954→756 lines (-21%), 61KB→46KB (-25%), ~18.5K→14K tokens per session (-25%). **20/20 best practices coverage** (was 8/20). 4 NEW anti-patterns (kitchen-sink / side question / 3+ corrections / CLAUDE.md bloat) + token-saver commands table в repo CLAUDE.md. NO code changes. 762 pytest preserved. |
| **S32b** | **0046** | **v0.1.0-alpha.32b** | **2026-04-27** | **Kit Improvement Phase 1 sub-sprint** — operator-driven kit Phase 1 sub-sprint per КУ analysis. Sub-sprint S32 series (mirror S8a/S8b/S8c pattern, operator directive "пусть все фазы будут в 32 спринте"). 6 changes: T1 dashboard-reviewer L5 agent (out-of-repo + wiki page) + T2 SPRINT_STATE freshness check hook (out-of-repo bash script + settings.json registered + wiki page; conservative regex flags actionable patterns `S<N> PHASE X ship\|pending\|in_progress\|next`, skips carry-over context `closes S14 Q2`) + T3 Pre-commit hooks upgraded `.pre-commit-config.yaml` (ruff v0.4.0 + mypy --strict local + yamllint для CI workflows; pre-commit installed via .git/hooks/pre-commit) + T4 GitHub Actions CI `.github/workflows/ci.yml` (10 steps: checkout / py3.12 cache / TA-Lib build cached / pip install dev / ruff lint+format / mypy --strict baseline guard / pytest unit baseline guard / canonical counts verify; triggers push к main + PR; baseline guards informational не strict — 3 pytest + 1 mypy pre-existing allowed) + T5 SQLite MCP server `.mcp.json` (sqlite-trading → data/bot.db; settings.json schema rejects mcpServers field — .mcp.json правильный location per Claude Code MCP security; uvx + mcp-server-sqlite verified pre-installed) + T6 ADR 0046 + sprint-32b page + index + canonical counts (45→46 ADRs / 32→33 sprint pages / 9→10 reviewer agents / 6→7 active push hooks / 6→7 MCP servers / 38→40 component pages). КУ avg 60.5% / ~3 hours = ~120 КУ/час (above forecast 10.5 — pre-commit pkg + uvx + mcp-server-sqlite уже available pre-installed). Phase 2 (memory corpus org / context budget hook / 5 more skill mappings / Fetch MCP) deferred к S32c. Test debt carry-over к S33+: 3 pytest failures (test_replay_long_only / test_replay_next_open) + 1 mypy error (__main__.py:636 bars_per_year_map redef). NO src/ code changes. 773 pytest preserved by construction. |
| **S32** | **0045** | **v0.1.0-alpha.32** | **2026-04-27** | **Kit Improvement Phase 0 sprint** — operator-driven kit optimization per КУ analysis (post-S31 review session). Documentation-only sprint (controller-driven, no src/ touched). 6 changes per ADR 0045: T1 SPRINT_STATE.md P0 fix (stale "Текущий статус"/"Последний спринт"/"Следующее действие" → S32 reality + correct counts 30→44 ADRs / 17→31 sprint pages) + T2 current-state.md P0 fix (post-S25→post-S31 + 604→762 + sources/tags/TL;DR + S25 TL;DR preserved as Previous) + T3 5 NEW skill mappings sprint-flow-ru.md (idea-refine Phase 2 PRE / spec-driven Phase 2/3 non-trading / source-driven Phase 4 Bybit-pydantic-pybit-FastAPI-TA-Lib / code-simplification Phase 6 OPT / documentation-and-adrs Phase 8) + T4 cascade smart-explore STEP 2.5 (sprint-flow + kit-overview mirror, 30-50% дешевле naked grep+read для structural lookups) + T5 Phase 9 consolidate-memory step (every 5 sprints OR >30 observations + HARD-GATE) + T6 ADR 0045 + sprint-32 page + index sync + canonical counts (44→45 ADRs / 31→32 sprint pages). Skills × Phase map 26→32 entries. КУ avg 60% за 45 мин (best ROI per phase, forecast 114 КУ/час). Phase 1 (CI / SQLite MCP / SPRINT_STATE freshness hook / dashboard-reviewer L5 agent) deferred к S33. NO code changes. 762 pytest preserved by construction. |

**Tag drift note (S4+S5):** `v0.1.0-alpha.4` + `v0.1.0-alpha.5` never created — S4+S5+S6 consolidated в одну ship-волну под `v0.1.0-alpha.6`. См. `wiki/project/sprints/README.md` Tag exceptions section + `wiki/project/pre-s8c-backlog.md` Bucket A5.

## Test/quality state (live, post-S31 baseline preserved через S32)

- pytest unit: **762 passed** (S27-S31 baseline; +18 vs S26 pre-formula-fixes)
- pytest property: 8/8
- pytest integration: opt-in `RUN_DEMO=1` (Demo Mainnet)
- mypy --strict src/: ≤ 44 errors (S8c baseline preserved через S31)
- ruff: clean on S8+ src + tests; legacy `src/core/`, `src/backtest/*` excluded в pyproject.toml pending retirement

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
