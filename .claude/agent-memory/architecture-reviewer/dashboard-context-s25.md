---
name: Dashboard Presentation context — S25
description: Architectural decisions for S25 dashboard scope — DDD placement, process isolation, concurrency, data isolation, dependency grouping
type: project
---

## Dashboard = new Presentation bounded context (src/dashboard/)

**Decision (S25 APPROVE_WITH_CONDITIONS):** Dashboard is a new DDD Presentation bounded context, NOT an extension of Platform.

**DDD boundary (hard):** src/dashboard/ imports ONLY:
- src/backtest/ (read-only WFA calls)
- src/platform/config (Settings for paths)
- NEVER: src/execution/, src/risk/, src/signalgen/, src/marketdata/

Historical-only scope enforces boundary naturally in S25.

## Process isolation invariant (CRITICAL)

Bot (sync+threading, WS thread + tick thread) and dashboard (uvicorn asyncio event loop) MUST run in separate OS processes. Never co-locate in same process. uvicorn is internally asyncio — mixing with bot's sync+threading model = undefined behavior.

**Why:** ADR 0022 sub-decision 1 defers asyncio to S9+. Bot is sync+threading canonical. uvicorn cannot share the bot process without violating this.

**How to apply:** Enforce in ADR 0039. Launcher script (scripts/dashboard.sh) launches `python -m src.dashboard` as standalone. Prohibit any dashboard import in src/__main__.py bot commands.

## FastAPI + uvicorn (optional dependency group)

Add to pyproject.toml as [project.optional-dependencies] dashboard = ["fastapi>=0.111", "uvicorn[standard]>=0.29"].
Do NOT add to main dependencies — live bot has no web server need. Keeps deployment footprint minimal.

## Background thread + polling for long-running backtest endpoint

Pattern: POST /api/backtest → start WFA in background thread → return run_id immediately → GET /api/backtest/{run_id}/status polls.

Concurrency: threading.Lock(blocking=False) on POST. Returns HTTP 409 if backtest already running. No queue needed for single-user localhost tool.

Result cache: data/runs/<run_id>.json using atomic write pattern (os.open + os.replace, mirror S8b T4).

## SQLite read-only connection

If dashboard reads trade_history or execution_state: use mode=ro URI exactly as _cmd_monitor does.
Pattern: `f"file:{settings.db_path}?mode=ro"` + `sqlite3.connect(uri=True)`.
NEVER call init_db() from dashboard process.

## plotly mypy override

pyproject.toml already has plotly.* in mypy overrides (line 67). If Chart.js (CDN) chosen for frontend, plotly is NOT imported server-side. Verify and remove override if unused.

## Sortino anomaly guard (trader CC4 hard requirement)

Display t2_sortino_oos as "insufficient sample" warning when n_losers < 5 rather than raw NaN.
Frontend concern, not backend computation change. strategy_metrics.py already returns NaN correctly.
