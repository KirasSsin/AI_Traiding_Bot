---
title: Sprint 25 — Dashboard UI (FastAPI + vanilla JS, demo-only backtest comparison)
type: sprint
tags: [sprint-25, dashboard, fastapi, presentation-context, demo-only, backtest-comparison, s4-system-criterion-partial]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0039-sprint-25-dashboard.md
  - project/pre-s25-backlog.md
---

# Sprint 25 — Dashboard UI

## Overview

User-driven feature sprint. Per directive 2026-04-26: dashboard для visual strategy comparison + display backtest results UI. Demo-only (TESTNET=true), no live trading control в S25 scope.

Joint trader+architecture brainstorm:
- **Trader-expert CONFIRM** spec (TIER 1 verdict-critical metrics + TIER 2 trade stats + 4 mandatory warnings + comparison table). HARD requirement: Sortino anomaly guard (CC4) — if Sortino>50 AND n_trades<100 → display N/A
- **Architecture-reviewer APPROVE_WITH_CONDITIONS:** FastAPI + vanilla JS + auto-open browser + localhost-only. Conditions: process isolation, optional dependency group, read-only SQLite via mode=ro, src/dashboard/ isolated Presentation context

## Plan / ADR links

- [[../decisions/0039-sprint-25-dashboard]] — Sprint 25 ADR
- [[../pre-s25-backlog]] — joint trader+architecture verdicts trail

## Deliverables

| Task | Status | Description |
|------|--------|-------------|
| T0 | ✅ DONE | Backfill 2023-01-01 → 2026-04-26 (BTC 5M/15M/60/240/1D + ETH 15M/60/240 + SOL 15M/60/240) |
| T1 | ✅ DONE | ADR 0039 (joint verdict + 11 CCs) |
| T2 | ✅ DONE | pyproject.toml `[dashboard]` optional dep group (fastapi + uvicorn + jinja2) |
| T3 | ✅ DONE | src/dashboard/app.py (FastAPI app + 7 endpoints) |
| T4 | ✅ DONE | src/dashboard/backtest_runner.py (wraps WFA + caching + 4 risk warnings + Sortino anomaly guard) |
| T5 | ✅ DONE | src/dashboard/templates/index.html (single-file UI) |
| T6 | ✅ DONE | src/dashboard/static/dashboard.js (vanilla JS frontend) |
| T7 | ✅ DONE | src/dashboard/static/dashboard.css (warning colors + verdict styling) |
| T8 | ✅ DONE | scripts/dashboard.sh (launcher) |
| T9 | ✅ DONE | tests/unit/test_dashboard_app.py (8 smoke tests) |
| T10 | ✅ This commit | sprint-25 page + wiki sync |
| T11 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.25) |

## FSM growth

NONE. S25 = Presentation context. Counts unchanged: **16/30/74/45**.

## Reason codes growth

NONE.

## Tests / quality

- pytest unit: **740 passed**, 24 skipped (+8 dashboard tests)
- mypy --strict src/: clean (75 source files, +3 dashboard modules)
- Q7-S12 zero-migration: trivially preserved

## Code structure (NEW: src/dashboard/)

```
src/dashboard/
├── __init__.py             # Module docstring
├── app.py                  # FastAPI factory + 7 endpoints + main()
├── backtest_runner.py      # WFA wrapper + caching + warnings + Sortino guard
├── templates/
│   └── index.html          # Single-file UI (Jinja2 template)
└── static/
    ├── dashboard.js        # Vanilla JS frontend (no framework)
    └── dashboard.css       # Styling (warning colors, verdict, table)

scripts/
└── dashboard.sh            # Launcher (uvicorn + auto-open browser)
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Static HTML dashboard |
| GET | `/api/strategies` | Strategy presets (3: EMA crossover S13 / Mean-rev S15 / Mean-rev S17 relaxed) |
| GET | `/api/intervals` | Supported timeframes (5M/15M/60/240/1D) |
| GET | `/api/data/availability` | Per-symbol+interval data availability scan |
| POST | `/api/backtest` | Run WFA → return results JSON (cached к data/runs/<run_id>.json) |
| GET | `/api/runs` | List previous cached runs (newest first) |
| GET | `/api/runs/{run_id}` | Fetch specific run |

## Strategy presets

| ID | Label | Type | Indicators |
|----|-------|------|-----------|
| `ema_crossover_s13` | EMA crossover (S13 baseline) | ema_crossover | EMA 12/26 + RSI 14 (overbought 68) + ATR 14 |
| `mean_reversion_s15` | Mean-reversion (RSI 30/70 + BB 2.0σ) — S15 original | mean_reversion | RSI 14 (oversold 30 / overbought 70) + BB(20, 2.0σ) + ATR 14 |
| `mean_reversion_s17_relaxed` | Mean-reversion (RSI 35/65 + BB 1.5σ) — S17 relaxed | mean_reversion | RSI 14 (oversold 35 / overbought 65) + BB(20, 1.5σ) + ATR 14 |

## Metrics displayed (per trader spec)

**TIER 1 (verdict-critical):** T1 Sharpe (red >3 overfit warn) / T2 Sortino (N/A guard) / T3 MaxDD / T4 win+RR / T5 trades+t_stat (n<100 red) / T6 OOS-IS / DSR / MC p / per-fold sharpes table.

**TIER 2 (trade-level stats):** Total Return % / Total Commissions / Profitable+Losing trade counts / Avg Win+Loss USDT / Profit Factor.

**4 risk warnings:**
1. Overfit Sharpe (T1>3.0)
2. Regime concentration (max fold > 5 OR > 2× median positive)
3. MC noise (p > 0.10)
4. DSR penalty (≤ 0)

Plus: Sortino anomaly guard (display N/A if >50 AND n<100), low_sample warn (n<100).

## Backfill summary (T0)

| Symbol | Interval | Bars | Range |
|--------|----------|------|-------|
| BTCUSDT | 5M | 349,117 | 2023-01-01 → 2026-04-26 |
| BTCUSDT | 15M | 116,372 | 2023-01-01 → 2026-04-26 |
| BTCUSDT | 1H | 29,093 | 2023-01-01 → 2026-04-26 |
| BTCUSDT | 4H | 7,273 | 2023-01-01 → 2026-04-26 |
| BTCUSDT | 1D | 1,212 | 2023-01-01 → 2026-04-26 |
| ETHUSDT | 15M | 116,372 | 2023-01-01 → 2026-04-26 |
| ETHUSDT | 1H | 29,093 | 2023-01-01 → 2026-04-26 |
| ETHUSDT | 4H | 7,273 | 2023-01-01 → 2026-04-26 |
| SOLUSDT | 15M | 116,372 | 2023-01-01 → 2026-04-26 |
| SOLUSDT | 1H | 29,093 | 2023-01-01 → 2026-04-26 |
| SOLUSDT | 4H | 7,273 | 2023-01-01 → 2026-04-26 |

**30M (30) + 2H (120) skipped:** Bar.interval Literal не supports их (pydantic ValidationError). Future Bar model extension would unlock.

## Code changes summary

### NEW

- `src/dashboard/__init__.py` — module docstring + ADR 0039 reference
- `src/dashboard/app.py` (108 lines) — FastAPI factory + 7 endpoints + main() launcher
- `src/dashboard/backtest_runner.py` (300+ lines) — WFA wrapper + caching + warnings + Sortino guard + STRATEGY_PRESETS + INTERVAL_LABELS
- `src/dashboard/templates/index.html` (60 lines)
- `src/dashboard/static/dashboard.js` (200+ lines) — vanilla JS, no framework
- `src/dashboard/static/dashboard.css` (~100 lines)
- `scripts/dashboard.sh` (executable launcher)
- `tests/unit/test_dashboard_app.py` (8 tests)

### Modified

- `pyproject.toml` — added `[project.optional-dependencies] dashboard` group
- `src/marketdata/bybit/rest.py:68-77` — extended intervals dict (5/15/30/60/120/240/D — 30+120 work для backfill but skipped в dashboard scope)
- `src/__main__.py`:
  - `_derive_heal_max_age_seconds` interval_seconds_map extended 5/15/30/60/120/240/D
  - `_default_wfa_config()` NEW (extracted к standalone function для dashboard override)
  - `_run_wfa_single_symbol` accepts `strategy_config: dict | None = None` parameter
  - Other map sites extended (interval_label_map ×2, bars_per_year_map, choices ×2)

## Wiki updates

- 1 NEW ADR (0039 — accepted)
- 1 NEW sprint page (this — sprint-25-dashboard)
- 1 NEW backlog (pre-s25-backlog.md)
- Modified: current-state.md (TL;DR + S25 row + counts ADR 38→39, sprint pages 25→26), index.md (sprint-25 + ADR 0039), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.25)

## Usage

```bash
# 1. Install dashboard deps (one-time)
.venv/bin/pip install -e ".[dashboard]"

# 2. Launch dashboard
./scripts/dashboard.sh
# → uvicorn starts on http://127.0.0.1:8000/
# → browser auto-opens

# 3. UI workflow
# - Select strategy / symbol / interval / date range
# - Click "Запустить backtest"
# - Wait ~30-60s
# - View metrics table + warnings + per-fold sharpes
# - "История запусков" — re-display cached previous runs
```

## Cross-cutting concerns (binding per ADR 0039)

- CC1 Process isolation BINDING (uvicorn separate OS process от bot runtime)
- CC2 Optional dependency group (core CLI works без dashboard deps)
- CC3 Localhost-only bind (127.0.0.1, no auth, no CORS)
- CC4 Read-only data access (Parquet pure read, SQLite via mode=ro pattern)
- CC5 Sortino anomaly guard HARD (>50 AND n<100 → N/A display)
- CC6 NO live trading в S25 scope (только historical backtest)
- CC7 NO Mainnet support в S25 (TESTNET=true enforced)
- CC8 No spec amendment (acceptance-criteria.md preserved)
- CC9 Backtest concurrency: 1 at a time (threading.Lock)
- CC10 Result caching disk-based (data/runs/<run_id>.json)
- CC11 Tag semantics: alpha.25 = dashboard sprint (UI capability, NOT MVP DONE)

## Open issues для future sprints

**S26+ candidates:**
- Live bot start/stop control via UI (currently `_cmd_run` separate CLI)
- Mainnet pilot UI (per S1-S6 system criteria roadmap, requires MVP DONE first)
- Real-time WebSocket updates (FSM state, current balance, recent fills)
- Equity curve chart visualization (matplotlib/plotly OR pure SVG)
- 30M + 2H backfill support (extend Bar.interval Literal)
- Multi-run comparison view (side-by-side multi-strategy)
- Strategy parameter customization (currently presets-only)

**S24 ESC-1 still open:** pause vs multi-symbol revival decision deferred (independent от S25).

All previous carry-overs preserved (16+ items).

## Key decisions (S25 ADR 0039)

- **Joint convergence:** trader CONFIRM metrics spec + architecture APPROVE_WITH_CONDITIONS
- **NEW Presentation context:** src/dashboard/ isolated, no execution/risk imports
- **Optional dep group:** dashboard not loadable без install — core CLI lean
- **Sortino anomaly guard CC4 HARD:** prevents misleading 4446/7309 artifact display
- **NO live trading в S25:** scope limited к backtest comparison, future S26+ для live UI
- **Strategy presets-only:** S25 MVP — 3 hardcoded presets. Future = parameter customization

## Related

- [[../decisions/0039-sprint-25-dashboard]] — S25 ADR
- [[../pre-s25-backlog]] — joint verdicts trail
- [[../decisions/0026-sprint-11-operator-readiness]] — S11 `_cmd_monitor` pattern (read-only SQLite reused)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, dashboard displays)
