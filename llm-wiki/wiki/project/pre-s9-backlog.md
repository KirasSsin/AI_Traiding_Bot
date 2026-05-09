---
title: Pre-S9 backlog — brainstorm verdicts trail
type: backlog
tags: [sprint-9, brainstorm, phase-2, verdicts, trader-expert]
created: 2026-04-25
updated: 2026-04-25
status: open
sources:
  - project/decisions/0021-sprint-7-resilience.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0023-halt-code-fsm-event-mapping.md
---

# Pre-S9 backlog — PHASE 2 brainstorming trail

## S9 scope (maintainer-locked)

C + G + B grouping:
- **C** — WS+REST price epsilon-halt detector → HALT_DATA_QUALITY (S effort)
- **G** — mypy --strict full enable (remove ignore_errors overrides) (S effort)
- **B** — Analytics: per-fill schema + DSR foundation (M effort, split B1+B2)

## S9 PHASE 2 brainstorming verdicts

### Q1 — C: WS+REST price epsilon-halt detector

**ROUND 1 verdict:** REVISE (trader-expert)

**Maintainer original recommendation:** REST kline last_close vs WS kline last_close, threshold=0.5%, per-bar, new module `src/marketdata/quality.py`, halt severity CRITICAL.

**Trader chosen option:** REST-vs-REST consecutive bar comparison — current closed bar (T) from `BarSource.poll()` against previously stored REST bar close (T-1, in-memory). Threshold 0.5% relative, per-bar cadence. No WS kline subscription required.

**Trader rationale:**
- Maintainer's WS+REST kline requires new WS topic subscription (currently only order+wallet active per `src/execution/bybit/ws_private.py`)
- Async `MarketDataPipeline` уже existing — wiring kline WS contradicts S8a ADR 0022 async deferral к S9+
- WS kline publishes partial bar updates throughout bar — comparison window не deterministic, false-positive risk
- REST-vs-REST consecutive bar deviation 0.5% on 1H BTCUSDT = ~$500 instantaneous move — catches stuck/corrupted feed без new infrastructure

**ROUND 2:** NOT triggered. Maintainer accepts trader REVISE (technically stronger — устраняет async dep + WS partial-bar false-positive).

**Final accepted decision:** REST-vs-REST consecutive bar comparison. Module: `src/marketdata/quality.py` (new). Threshold: 0.5% relative. Cadence: per-bar (after BarSource.poll() returns). Halt: emits `RISK_HALT` event с `halt_reason=HALT_DATA_QUALITY` (uses existing FSM event, no new state/event).

**Wiki/code follow-ups:**
- New `src/marketdata/quality.py` module (mypy strict from day 1, нет override)
- Update `wiki/project/components/bar-poller.md` с data-quality detector cross-link
- New `wiki/project/components/data-quality.md` component page
- Verify HALT_DATA_QUALITY → RISK_HALT routing в `src/execution/coordinator.py::request_halt`

---

### Q2 — G: mypy --strict full enable

**ROUND 1 verdict:** REVISE (trader-expert)

**Maintainer original recommendation:** Sequential per-module: src.risk → src.backtest → src.core.

**Trader chosen option:** Sequential per-module, ORDER INVERTED: src.core → src.risk → src.backtest (optionally deferred).

**Trader rationale:**
- src.core = legacy stub (~50 LoC per current-state.md). Smallest, fastest wedge. Validates pyproject override-removal workflow с zero risk.
- src.risk = ~1100 LoC, 10 files (Kelly/CB/sizing/manager/override). Money path. Most complex. Failed risk task blocks ALL downstream mypy work.
- Maintainer's order puts hardest first — wrong wedge selection per `agent-skills:incremental-implementation` (start small, validate pattern, scale up).
- src.backtest scheduled S10 revival (WFA/DSR/MC) — mypy clean before revival = forcing function для correctness.

**ROUND 2:** NOT triggered. Maintainer accepts (incremental-implementation pattern).

**Final accepted decision:** Order src.core (T1) → src.risk (T2) → src.backtest (T3 optional, defer if sprint slots tight).

**Wiki/code follow-ups:**
- Update `pyproject.toml` overrides per task (remove one module at a time)
- Update `wiki/project/components/backtest-harness.md` mypy strict enforcement note for S10 revival prep

---

### Q3 — B: Per-fill analytics schema + DSR foundation

**ROUND 1 verdict:** CONFIRM (trader-expert)

**Maintainer recommendation = trader chosen option:** SPLIT into B1 + B2.

**B1 — Per-fill schema:**
- NEW `trade_fills` table: fill_id, parent_trade_id (FK к trade_history.trade_id), fill_qty, fill_price, fill_fee, fill_ts, exec_id (Bybit's), is_partial
- WS `execution` topic subscription added к `src/execution/bybit/ws_private.py` (currently order+wallet only)
- Per-fill recording в new `src/risk/fill_history.py` repository (mirror of trade_history.py pattern)

**B2 — DSR foundation:**
- NEW `src/analytics/dsr.py` module (`src/analytics/__init__.py` empty stub since S4)
- Pure post-process на `TradeHistoryRepository` — `TradeRecord` already has pnl_pct + entry_ts + exit_ts (sufficient для log-return DSR)
- log returns default, simple returns via flag
- No look-ahead = uses only closed trades (exit_ts populated)
- Bailey & Lopez de Prado DSR formula

**Trader CONFIRM rationale:**
- DSR doesn't depend on per-fill data — works on per-trade returns
- Per-fill is 3-sprint deferred carry-over (ADR 0021 → 0022 → S9) — closes named debt
- Bybit Spot single-fill typical (Market entries), partial fills rare на IOC SL — `is_partial` flag correct
- DSR on N=0 trades = NaN/empty (not crash) — infrastructure ships now для first live trades in S11 F

**ROUND 2:** N/A (CONFIRM verdict).

**Final accepted decision:** Split B1 + B2 as specified. quant-stats-reviewer MANDATORY на B2 dispatch (DSR formula correctness + log/simple return + annualization factor для 1H bars + no-look-ahead invariant).

**Wiki/code follow-ups:**
- New migration: `migrations/0006_trade_fills.sql` (CREATE TABLE trade_fills + FK + indexes)
- New `src/risk/fill_history.py` (repository pattern)
- Extend `src/execution/bybit/ws_private.py` execution topic subscription
- New `src/analytics/dsr.py` (Bailey & Lopez de Prado formula)
- New `wiki/project/components/fill-history.md`
- New `wiki/project/components/dsr.md`
- Update `wiki/project/architecture/current-state.md` analytics row + canonical-counts (component pages 28→30)

---

## Cross-cutting concerns (apply across all 3 questions)

1. **Mypy strict + Q1/Q3 new modules:** `src/marketdata/quality.py` (Q1), `src/risk/fill_history.py` (Q3 B1), `src/analytics/dsr.py` (Q3 B2) — все NEW modules без `ignore_errors` overrides → must be fully type-annotated from day 1. No retrofitting needed.

2. **Q3 B2 reviewer mandate:** quant-stats-reviewer обязателен на B2 dispatch (formula correctness, look-ahead invariant, annualization factor для 1H sample frequency).

3. **HALT_DATA_QUALITY FSM wiring (Q1):** Uses existing `RISK_HALT` event — emitter pattern matches HALT_DRAWDOWN_L2/L3, HALT_FLASH_CRASH. NO new FSM state or event needed. Verify `coordinator.py::request_halt` already handles HALT_DATA_QUALITY → RISK_HALT mapping (per ADR 0023 invariant `_REQUEST_HALT_CODES` set).

4. **No new ADR needed для C alone** — HALT_DATA_QUALITY already в ReasonCode enum since S4, FSM event existing. Document detector design в `src/marketdata/quality.py` docstring + component page.

5. **NEW ADR 0024 для S9 G + B aggregate** — G removes overrides (process change), B adds 2 new components + WS topic + migration. Worth single ADR documenting decisions.

## Escalation items для user

None. All engineering/architecture scope.

## Transition

PHASE 2 complete. SPRINT_STATE → phase=3-planning. Next: PHASE 3 plan write (`superpowers:writing-plans` skill) → trace map + bite-sized tasks.

## Related

- [[decisions/0021-sprint-7-resilience]] — per-fill execution topic deferral source
- [[decisions/0022-sprint-8a-live-runtime]] — wallet WS+REST epsilon-halt rejection (ADR 0020 sub-decision 4)
- [[decisions/0023-halt-code-fsm-event-mapping]] — HALT_*+ RISK_HALT mapping invariant
- [[decisions/0024-sprint-9-data-quality-types-analytics]] — Sprint 9 ADR
- [[sprints/sprint-09-data-quality-types-analytics]] — Sprint 9 page
- [[architecture/development-workflow]] — PHASE 2 binding protocol
- [[../components/trade-history]] — B1 base repository pattern
- [[../components/bar-poller]] — Q1 detector data source
