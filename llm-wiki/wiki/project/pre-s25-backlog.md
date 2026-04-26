---
title: Pre-S25 backlog — Dashboard UI joint trader+architecture verdicts
type: backlog
tags: [sprint-25, brainstorm, phase-2, verdicts, trader-expert, architecture-reviewer, dashboard]
created: 2026-04-26
updated: 2026-04-26
status: complete
sources:
  - project/decisions/0039-sprint-25-dashboard.md
---

# Pre-S25 backlog — Dashboard UI brainstorm

## Context

User directive 2026-04-26: "В UI возможность запуска каждой стратегии + возможность теста на исторических данных. Только historical backtest mode (no live trading в S25). Trader-expert spec на metrics: «доходность RSI, комиссия, кол-во сделок (прибыльных + неприбыльных) и прочее»".

Joint dispatch: trader-expert (metrics spec) + architecture-reviewer (FastAPI scope).

## ROUND 1 verdicts (complete)

| Agent | Verdict |
|-------|---------|
| Trader-expert | **CONFIRM** TIER 1 + TIER 2 metrics + 4 mandatory warnings + comparison table. **CC4 HARD: Sortino anomaly guard.** |
| Architecture-reviewer | **APPROVE_WITH_CONDITIONS** FastAPI + vanilla JS + auto-open browser + localhost-only. Conditions: process isolation, optional dep group, read-only SQLite mode=ro, src/dashboard/ isolated Presentation context. |

## Trader spec summary

**TIER 1 (verdict-critical):** VERDICT (PASS/FAIL) / failed_criteria / T1 Sharpe (red >3 overfit) / T2 Sortino (CC4 N/A guard) / T3 MaxDD / T4 win/RR / T5 trades + t_stat (n<100 red) / T6 OOS-IS / DSR / MC p / per-fold sharpes table.

**TIER 2 (trade stats):** Total Return % / Total Commissions USDT / Profitable+Losing trade counts / Avg Win+Loss USDT / Profit Factor.

**TIER 3 (deferred):** symbol/timeframe side-by-side comparison / RSI distribution histogram / cumulative trade log с timestamps.

**4 risk warnings (mandatory):**
1. Overfit Sharpe (T1 > 3.0) — Hudson & Urquhart 2021
2. Regime concentration (max fold > 5 OR > 2× median positive)
3. Statistical noise (MC p > 0.10)
4. Multi-testing penalty (DSR ≤ 0)

**CC4 HARD requirement:** Sortino anomaly guard — if Sortino > 50 AND n_trades < 100 → display "N/A — insufficient losing trade count для reliable downside deviation estimate". Prevents misleading 4446/7309 artifact display (S17/S22 historical examples).

## Architecture verdict summary

**Pattern APPROVED:** FastAPI (pydantic v2 native fit) + vanilla JS (no framework, single-file frontend) + `webbrowser.open()` auto-launch + localhost-only bind (127.0.0.1:8000).

**Conditions BINDING:**
- Process isolation: uvicorn separate OS process от bot runtime
- Optional dependency group `[project.optional-dependencies] dashboard = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "jinja2>=3.1"]`
- Read-only SQLite via `mode=ro` URI (per S11 `_cmd_monitor` pattern)
- `src/dashboard/` isolated Presentation context (no execution/risk imports)
- Backtest concurrency: 1 at a time (threading.Lock)
- Result caching: disk-based `data/runs/<run_id>.json` (run_id = hash strategy+symbol+interval+dates)

**Sprint scope estimate:** 8-10 tasks realistic.

## USER FINAL DECISION (autonomous mode)

S25 = Dashboard sprint. All trader spec + architecture conditions applied per ADR 0039.

S25 deliverables: T0 backfill missing intervals + T1-T11 dashboard implementation + ship.

## Related

- [[decisions/0039-sprint-25-dashboard]] — Sprint 25 ADR
- [[sprints/sprint-25-dashboard]] — Sprint 25 page
