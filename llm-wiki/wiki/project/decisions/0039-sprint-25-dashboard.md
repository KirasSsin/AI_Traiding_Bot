---
title: 0039. Sprint 25 — Dashboard UI (FastAPI + vanilla JS, demo-only backtest comparison)
type: decision
date: 2026-04-26
sprint: 25
tags: [adr, sprint-25, dashboard, fastapi, presentation-context, demo-only, no-mainnet, s4-system-criterion-partial]
sources:
  - project/pre-s25-backlog.md
  - project/decisions/0038-sprint-23-honest-close-v05.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0039. Sprint 25 — Dashboard UI

**Status:** accepted
**Date:** 2026-04-26

## Context

S23 closed v0.5 honest. S24 brainstorm: trader+architecture both REVISE → (E) project pause OR (b) multi-symbol revival (operator decision). User chose к build dashboard FIRST (S25), defer S24 ESC-1 decision.

User directive 2026-04-26 verbatim:
1. "Скачиваем для каждого интервала исторические данные за период с 2023.01.01 по [2026.04.26]"
2. "Делаем в UI возможность запуска каждой стратегии + возможность теста на исторических данных"
3. "Если на исторических данных, то торговли в реальном времени не происходит"
4. "Я просто хочу увидеть основные показатели доходности RSI, комиссия, кол-во сделок (прибыльных + неприбыльных) и прочее"

Joint trader+architecture brainstorm verdicts:
- **Trader CONFIRM (3 questions):** TIER 1 metrics (T1-T6 + DSR + MC + per-fold), TIER 2 (commissions + win/loss + holding time + equity curve), 4 mandatory warnings (overfit Sharpe>3, regime concentration, MC noise, DSR penalty), comparison table schema. **CC4 HARD: Sortino anomaly guard** (display N/A if Sortino>50 AND n_trades<100 — prevents misleading 4446/7309 numbers).
- **Architecture APPROVE_WITH_CONDITIONS:** FastAPI + vanilla JS + auto-open browser + localhost-only confirmed. Conditions: process isolation, optional dependency group, read-only SQLite via `mode=ro`, `src/dashboard/` isolated Presentation context (no execution/risk imports).

## Decision

### S25 scope: Dashboard UI for backtest comparison (demo-only)

**NEW bounded context: Presentation (Dashboard).** Module: `src/dashboard/`. Read-only к existing data sources (Parquet OHLCV + SQLite WAL state). NO execution/risk imports (architectural isolation).

**Tech stack (per architecture verdict):**
- FastAPI (pydantic v2 native fit, project ecosystem)
- Vanilla JS + HTML (single-file frontend, no build step)
- Static files served via FastAPI
- `webbrowser.open()` для auto-launch

**Optional dependencies (architecture-mandated):**
```toml
[project.optional-dependencies]
dashboard = ["fastapi>=0.115", "uvicorn>=0.32", "jinja2>=3.1"]
```

Install: `pip install -e ".[dashboard]"`. Backtest pipeline (`_cmd_wfa`, `_run_wfa_single_symbol`) does NOT depend on dashboard deps.

### S25 features (per trader spec)

**Backend endpoints (FastAPI):**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Static HTML dashboard |
| GET | `/api/strategies` | List available strategies (presets) |
| GET | `/api/intervals` | List supported timeframes (5/15/30/60/120/240/D) |
| GET | `/api/symbols` | List backfilled symbols (BTC/ETH/SOL) |
| GET | `/api/data/availability` | Per-symbol+interval data range available |
| POST | `/api/backtest` | Run WFA on (strategy, symbol, interval, dates) → return results JSON |
| GET | `/api/runs` | List previous backtest runs (cached on disk) |
| GET | `/api/runs/{run_id}` | Fetch specific run results |

**Strategy presets (configurable for dashboard launch):**
1. EMA crossover (S13 params): EMA 12/26 + ADX 14 + RSI 14 + ATR 14
2. Mean-reversion S15 (RSI 30/70 + BB(20, 2.0σ) AND-gated)
3. Mean-reversion S17 relaxed (RSI 35/65 + BB(20, 1.5σ) AND-gated)

**TIER 1 metrics displayed (verdict-critical per trader spec):**
- VERDICT (PASS/FAIL) + failed_criteria (which T-criteria failed)
- T1 Sharpe OOS (red if >3.0 overfit warning)
- T2 Sortino OOS (CC4 HARD: N/A if >50 AND n_trades<100)
- T3 MaxDD %
- T4 win_rate / avg_RR (paired display)
- T5 t_stat + n_trades (red if <100, prominent — T5 = structural ceiling)
- T6 OOS/IS Sharpe ratio mean
- DSR + MC p_value
- Per-fold sharpe table (5 folds + failed_folds highlight)

**TIER 2 metrics displayed (per trader + user request):**
- Total Return % (with Sharpe + MaxDD context, label "raw — not risk-adjusted")
- Total Commissions USDT (user explicit)
- Profitable trades count + Losing trades count (user explicit)
- Avg Win USDT + Avg Loss USDT
- Avg Holding Time hours
- Profit Factor
- Equity curve chart (cumulative pnl over time)
- Run config parameters (RSI thresholds, BB sigma, etc.)

**4 Mandatory risk warnings (trader spec):**
1. **Overfit signal:** trigger T1>3.0 → "Sharpe >3 на этом sample size = data artifact, не tradeable edge"
2. **Regime concentration:** trigger max(fold_sharpe) > 5 OR > 2× median non-negative folds → "Fold #N драйвит aggregate (Sharpe X.X vs aggregate Y.Y) — strategy regime-specific"
3. **Statistical noise:** trigger MC p > 0.10 → "MC permutation p=X — returns indistinguishable от random"
4. **Multi-testing penalty:** trigger DSR ≤ 0 → "DSR ≤ 0 — claimed edge не credible after multi-testing adjustment"

**Strategy comparison table (TIER 3 — included для multi-run UX):**
Columns ordered by decision-relevance: Strategy / Symbol / TF / VERDICT / Failed why / T1 Sharpe / T5 trades / T5 t-stat / T6 OOS-IS / DSR / MC p / Max fold Sharpe / MaxDD / Net return%. Color-coded cells against thresholds.

### S25 deliverables

| Task | Description |
|------|-------------|
| T0 | Backfill missing intervals 2023-01-01 → 2026-04-26 (BTC 5M/30M/2H/4H/1D + ETH 15M/4H + SOL 15M/4H) |
| T1 | ADR 0039 (this document) |
| T2 | Optional dep group `[project.optional-dependencies] dashboard` в pyproject.toml |
| T3 | `src/dashboard/__init__.py` + `app.py` (FastAPI app + endpoints) |
| T4 | `src/dashboard/backtest_runner.py` (wraps `_run_wfa_single_symbol` с caching) |
| T5 | `src/dashboard/templates/index.html` (single-file UI с vanilla JS) |
| T6 | `src/dashboard/static/dashboard.js` (form handling + API calls + render results) |
| T7 | `src/dashboard/static/dashboard.css` (минимальные styles + warning colors) |
| T8 | `scripts/dashboard.sh` (launcher: starts uvicorn + opens browser) |
| T9 | `tests/unit/test_dashboard_app.py` (basic endpoint smoke tests) |
| T10 | sprint-25 page + wiki sync |
| T11 | PHASE 8 ship (PR + tag v0.1.0-alpha.25) |

### Cross-cutting concerns (binding per architecture verdict)

- **CC1 Process isolation BINDING:** uvicorn runs as separate OS process from `_cmd_run` (live bot). Dashboard NEVER co-located с bot runtime. Reading SQLite WAL via `mode=ro` URI prevents lock contention.
- **CC2 Optional dependency group:** `pip install -e .` без `[dashboard]` extras = dashboard NOT loadable, но WFA pipeline works. Architectural isolation.
- **CC3 Localhost-only bind:** `127.0.0.1:8000` (NOT `0.0.0.0`). No CORS, no auth needed. Single-user dev tool.
- **CC4 Read-only data access:** Parquet files = pure read. SQLite via `mode=ro` URI per S11 `_cmd_monitor` pattern (S11 ADR 0026 reference).
- **CC5 Sortino anomaly guard HARD (trader CC4):** if Sortino>50 AND n_trades<100 → display "N/A — insufficient losing trade count для reliable downside deviation estimate". Prevents misleading 4446/7309 artifact numbers.
- **CC6 NO live trading через dashboard в S25:** только historical backtest mode. Live bot start/stop control = future S26+ scope (currently `_cmd_run` separate CLI invocation).
- **CC7 NO Mainnet support в S25:** demo-only. `TESTNET=true` enforced. ADR 0016 venue policy unchanged.
- **CC8 No spec amendment:** acceptance-criteria.md preserved. S25 = pure presentation layer + S4 system criterion partial (Dashboard p95 latency не measured BEYOND functional UI).
- **CC9 Backtest concurrency: 1 at a time** (per architecture). FastAPI thread pool + simple lock в `backtest_runner.py`. Queue future deferred (YAGNI).
- **CC10 Result caching:** WFA results saved к `data/runs/<run_id>.json` (run_id = hash of strategy+symbol+interval+dates). Reuse cached если same params re-requested. Disk-based, no DB schema change.
- **CC11 Tag semantics:** `v0.1.0-alpha.25` = dashboard sprint marker (UI capability, not MVP DONE).

## Consequences

**Plus:**
- User-friendly UI для strategy comparison (vs CLI JSON parsing)
- Dashboard = first step toward S4 acceptance criterion (Dashboard p95<2s)
- Reuses 100% existing WFA infrastructure (no new measurement code)
- Optional dep keeps core lean (CLI users не нужны FastAPI)
- Cached runs = quick re-display без re-execution
- Foundation для future S26+ live bot control + Mainnet pilot UI

**Minus:**
- New bounded context (Presentation) adds module count
- Frontend = vanilla JS (no framework) — UX limitations vs React/Vue
- 1 backtest at-a-time = potential UX bottleneck если user impatient (counter: backtests are 30-60s each)
- Optional dep = installation step required (`pip install -e ".[dashboard]"`)
- HTML/CSS/JS = новый surface для maintenance
- S25 не addresses S24 ESC-1 (pause vs multi-symbol) — that decision still pending

**v0.6+ carry-overs (anticipated):**

If dashboard reveals new strategy hypothesis worth testing → operator decides между:
- v0.6-A hybrid ML XGBoost
- v0.6-B HMM regime-switch
- v0.6-C multi-symbol revival (requires lift BTC-only constraint)
- v0.6-D different strategy class
- v0.6-E pause
- v0.6-F MVP T5 floor amendment

S25 dashboard does NOT preempt S24 ESC-1 — operator decides at any future point.

## Related

- [[../pre-s25-backlog]] — PHASE 2 joint verdicts (trader metrics spec + architecture scope verdict)
- [[0038-sprint-23-honest-close-v05]] — v0.5 honest close (predecessor)
- [[0026-sprint-11-operator-readiness]] — S11 `_cmd_monitor` pattern (read-only SQLite via `mode=ro` reused в dashboard)
- [[../architecture/acceptance-criteria]] — T1-T6 + DSR + MC (dashboard displays per trader spec)

## Amendments

- (none yet)
