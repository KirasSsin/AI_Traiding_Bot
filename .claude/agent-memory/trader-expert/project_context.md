---
name: Project context — AI Trading Bot v0.1
description: Key facts about the trading bot project — canonical counts, architecture decisions, sprint status
type: project
---

AI Trading Bot v0.1 — Bybit Spot BTCUSDT 1H. LONG+FLAT only. signal on close(T) -> fill at open(T+1).

**Canonical counts (post-S9, 2026-04-25):** 16 FSM states / 30 events / 74 transitions / 45 reason codes. Unchanged in S9 (HALT_DATA_QUALITY reused RISK_HALT path, no new states/transitions).

**Tag:** v0.1.0-alpha.9. Between sprints, ready for S10 (WFA + DSR + MC permutations).

**mypy state:** `mypy src/` → 0 errors (cleaned in debugging batch). BUT pyproject.toml has `ignore_errors = true` for src.core.*, src.backtest.*, src.risk.* — so `mypy --strict src/` would show additional errors in those modules.

**Key domain priors:**
- REST canonical for wallet (ADR 0020 sub-decision 4). WS+REST wallet epsilon-halt REJECTED in S8a Q8.
- Price (kline) epsilon-halt never addressed — open for S9.
- Per-fill execution topic + analytics table: deferred S7 -> S8 -> S8b -> S9 (3x deferral via ADR 0021, 0022).
- HALT_DATA_QUALITY pre-allocated in ReasonCode (position 71 in file, code index ~5 in Halts group).
- pipeline.py is ASYNC (uses async/await, WS consumer). bar_source.py (S8a) is SYNC REST polling. Two separate subsystems.
- src/analytics/__init__.py exists but is empty (1 line stub).

**Why:** Architecture foundation — use when assessing feasibility claims about existing modules.

**How to apply:** Before accepting any maintainer claim that "module X already does Y," verify by reading the source file.
