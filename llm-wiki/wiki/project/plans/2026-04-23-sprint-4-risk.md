---
title: Sprint 4 — Risk & Circuit Breakers (4-phase Kelly + L1/L2/L3/flash)
type: plan
tags: [plan, sprint-4, risk, kelly, circuit-breakers, tdd]
created: 2026-04-23
updated: 2026-04-23
status: ready-to-execute
parts:
  - 2026-04-23-sprint-4-risk-tasks-1-8.md
  - 2026-04-23-sprint-4-risk-tasks-9-13.md
  - 2026-04-23-sprint-4-risk-tasks-14-17.md
sources:
  - project/architecture/migration-plan.md §S4
  - project/decisions/0012-4-phase-kelly-sizing.md
  - project/decisions/0013-circuit-breakers-l1-l2-l3-flash.md
  - trading/concepts/kelly-phases.md
  - trading/concepts/circuit-breakers.md
---

# Sprint 4 — Risk & Circuit Breakers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** реализовать 4-фазный Kelly position sizing + L1/L2/L3/flash circuit breakers + drawdown monitoring; полностью заменить legacy `src/risk/risk_manager.py`.

**Architecture:** S4-owned persistence (новая миграция `002_risk.sql` с `trade_history` + `equity_snapshots`; реюз существующей `state` таблицы по trio risk-ключей). Caller-driven equity API: `update_equity(realized, unrealized, ts)` + `assess(signal, mark_price)` + `on_bar_close(bar)`. Output — frozen pydantic `RiskAssessment` value object. Manual L2/L3 resume — CLI `python -m src.risk.resume_cb` с config_hash binding.

**Tech Stack:** Python 3.12, pydantic v2, SQLite (через `src/platform/db.py`), scipy.stats для Wilson 95% CI, pytest 8 + hypothesis 6.

---

## Locked design (do NOT re-debate)

**Q1 Persistence:** S4-owned tables in `migrations/002_risk.sql` + reuse `state` table (already in 001_initial.sql).

**Q2 Equity API:**
```python
class RiskManager:
    def update_equity(self, *, realized: Decimal, unrealized: Decimal, ts: datetime) -> None: ...
    def assess(self, signal: Signal, *, mark_price: Decimal) -> RiskAssessment: ...
    def on_bar_close(self, bar: Bar) -> None: ...
```
Synchronous snapshot on every `update_equity()`.

**Q3 Manual resume:** CLI `python -m src.risk.resume_cb --level {L2,L3,FLASH} --reason "..." [--expires-in 1h]` writes `state/cb_override.json` with `{level, reason, config_hash, created_at, expires_at}`. Default expires_at = +1h. Consumed override → rename `.consumed.json`.

**Q4 Output:**
```python
class RiskAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    signal_id: UUID
    approved: bool
    qty: Decimal | None
    sl_price: Decimal | None      # mark_price - 1.5*ATR
    tp_price: Decimal | None      # mark_price + 3.0*ATR
    kelly_phase: Literal[1, 2, 3, 4]
    kelly_fraction: Decimal
    halt_state: HaltState         # L0|L1|L2|L3|FLASH
    reason_code: ReasonCode
    assessed_at: datetime
```
Sizing — pure function `compute_qty(equity, fraction, atr, price, k=Decimal("1.5")) -> Decimal` in `src/risk/sizing.py`.

**Q5 Schema (`migrations/002_risk.sql`):**
```sql
CREATE TABLE trade_history (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_signal_id TEXT NOT NULL,
    entry_ts TEXT NOT NULL,
    exit_ts TEXT NOT NULL,
    qty TEXT NOT NULL,
    entry_price TEXT NOT NULL,
    exit_price TEXT NOT NULL,
    pnl_quote TEXT NOT NULL,
    pnl_pct TEXT NOT NULL,
    fees_paid TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    kelly_phase INTEGER NOT NULL CHECK(kelly_phase IN (1,2,3,4)),
    recorded_at TEXT NOT NULL
);
CREATE INDEX idx_trade_history_exit_ts     ON trade_history(exit_ts);
CREATE INDEX idx_trade_history_symbol_exit ON trade_history(symbol, exit_ts);

CREATE TABLE equity_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    realized_equity TEXT NOT NULL,
    unrealized_pnl TEXT NOT NULL,
    total_equity TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('BAR_CLOSE','POSITION_CLOSE','MANUAL'))
);
CREATE INDEX idx_equity_ts ON equity_snapshots(ts);
```

State keys (in existing `state` table):
- `risk:cb:current_level` → JSON `{level, triggered_at, peak_equity, dd_pct}`
- `risk:kelly:phase` → JSON `{phase, trade_count, updated_at}`
- `risk:kelly:params` → JSON `{p_hat, b, computed_at}`

---

## Decisions & deviations

**D1 — ReasonCode mapping:** The 28-enum from `wiki/trading/concepts/reason-codes.md` does NOT include `APPROVED`, `RISK_REJECT_HALT_L1`, etc. per the naming requested in the task prompt. The actual enum names that map to risk context are: `REJECT_RISK_EXCEEDED`, `HALT_DRAWDOWN_L1`, `HALT_DRAWDOWN_L2`, `HALT_DRAWDOWN_L3`, `HALT_FLASH_CRASH`. The prompt-requested names (`RISK_REJECT_HALT_L1` etc.) are **non-existent** in the 28-enum. Flagged as Follow-up: see §Follow-ups. Implementation uses canonical 28-enum names only.

**D2 — `APPROVED` code:** No `APPROVED` reason code exists in the 28-enum. Approved assessments use `ENTRY_LONG_TREND_FOLLOWING` (or relevant entry code) passed through from the signal, not a separate risk code. `RiskAssessment.reason_code` on approval carries the entry code; on rejection carries the reject/halt code.

**D3 — `scipy.stats` dependency:** Added to `pyproject.toml` for Wilson CI computation. Alternative: inline formula (z=1.96 fixed). Plan uses inline formula with `z = Decimal("1.96")` cast to float only for the sqrt computation, result cast back to Decimal. No scipy required — eliminates dependency.

**D4 — `Bar` type for `on_bar_close`:** Uses `src.marketdata.models.Bar` (from S2). If S2 not merged, use a minimal `Bar` protocol with `close: Decimal`, `high: Decimal`, `low: Decimal`, `ts: datetime`, `atr_14: Decimal`.

---

## Scope

### In scope (AC from migration-plan §S4)

- `migrations/002_risk.sql` — `trade_history` + `equity_snapshots` tables.
- 4-phase Kelly: `KellyCalculator` with `phase_from_trade_count`, Wilson 95% CI, `kelly_fraction`, `phase_adjusted_fraction`.
- Position sizing: `compute_qty(equity, fraction, atr, price, k) -> Decimal`.
- Circuit breaker detector: L1/L2/L3 drawdown thresholds + flash detector.
- `EquityTracker` with 24h HWM rolling query.
- `TradeHistoryRepository` + `TradeRecord` pydantic model.
- `StateRepo` — JSON kv adapter for `state` table.
- `OverrideStore` — write/read/consume `cb_override.json` with config_hash binding.
- `RiskManager` orchestrator: `update_equity`, `assess`, `on_bar_close`.
- CLI `python -m src.risk.resume_cb`.
- Integration test: 50-bar synthetic flow, phase transitions, CB triggers, override resume.
- Wiki component pages: kelly, circuit-breakers, sizing, risk-manager.
- Sprint delivery record + wiki index/log updates.
- **Legacy removal:** `git rm src/risk/risk_manager.py`.

### Out of scope (explicit)

- OCO bracket placement (S5).
- Event bus integration (S6).
- Reconciliation / state-machine (S5).
- Regime shift KS-test downgrade (S7).
- Backtest harness (S7).

### Prerequisites

- Python 3.12 venv активен.
- `make check` green на `origin/main` (Sprint 3 tag).
- `src/signalgen/models.py` — `Signal` с `atr_14: Decimal` (S3 artifact).
- `src/platform/db.py` — `connect()` + `init_db()` (S1 artifact).
- `migrations/001_initial.sql` — `state` table exists.

---

## File Structure

### Created

```
migrations/
└── 002_risk.sql

src/risk/
├── __init__.py          # re-exports RiskManager, RiskAssessment, HaltState
├── reason_codes.py      # ReasonCode StrEnum (28 canonical codes)
├── models.py            # HaltState StrEnum, RiskAssessment frozen pydantic
├── sizing.py            # compute_qty() pure function
├── kelly.py             # KellyCalculator
├── trade_history.py     # TradeHistoryRepository + TradeRecord
├── equity_tracker.py    # EquityTracker (HWM, snapshots)
├── circuit_breakers.py  # CircuitBreakerDetector (pure functions)
├── override.py          # OverrideStore (cb_override.json)
├── state_repo.py        # StateRepo (JSON kv for state table)
├── manager.py           # RiskManager orchestrator
└── resume_cb.py         # CLI entry point

tests/unit/
├── test_risk_migration.py
├── test_risk_settings.py
├── test_reason_codes.py
├── test_risk_models.py
├── test_sizing.py
├── test_kelly.py
├── test_trade_history.py
├── test_equity_tracker.py
├── test_circuit_breakers.py
├── test_override.py
├── test_state_repo.py
└── test_risk_manager.py

tests/integration/
└── test_risk_flow.py

llm-wiki/wiki/project/components/
├── kelly.md
├── circuit-breakers.md
├── sizing.md
└── risk-manager.md

llm-wiki/wiki/project/sprints/
└── sprint-04-risk.md
```

### Modified

- `src/platform/config.py` — добавить risk settings + `config_hash()`.
- `src/risk/__init__.py` — обновить re-exports, удалить legacy imports.
- `pyproject.toml` — убедиться что `scipy` в dependencies (если нужен — см. D3, скорее всего не нужен).
- `llm-wiki/wiki/index.md` — добавить новые component pages + sprint + plan.
- `llm-wiki/wiki/log.md` — append entry.

### Removed

- `src/risk/risk_manager.py` — legacy, полностью заменяется `src/risk/manager.py`.

---

## Task Index

- [Task 1: Migration `002_risk.sql` + idempotency test](2026-04-23-sprint-4-risk-tasks-1-8.md#task-1-migration-002_risksql--idempotency-test)
- [Task 2: Settings additions + `config_hash()`](2026-04-23-sprint-4-risk-tasks-1-8.md#task-2-settings-additions--config_hash)
- [Task 3: `src/risk/reason_codes.py` — ReasonCode StrEnum](2026-04-23-sprint-4-risk-tasks-1-8.md#task-3-srcriskreason_codespy--reasoncode-strenum)
- [Task 4: `src/risk/models.py` — `HaltState` + `RiskAssessment`](2026-04-23-sprint-4-risk-tasks-1-8.md#task-4-srcriskmodelspy--haltstate--riskassessment)
- [Task 5: `src/risk/sizing.py` — `compute_qty()` pure function](2026-04-23-sprint-4-risk-tasks-1-8.md#task-5-srcrisksiingpy--compute_qty-pure-function)
- [Task 6: `src/risk/kelly.py` — `KellyCalculator`](2026-04-23-sprint-4-risk-tasks-1-8.md#task-6-srcriskkellypy--kellycalculator)
- [Task 7: `src/risk/trade_history.py` — `TradeHistoryRepository`](2026-04-23-sprint-4-risk-tasks-1-8.md#task-7-srcrisktrade_historypy--tradehistoryrepository)
- [Task 8: `src/risk/equity_tracker.py` — `EquityTracker`](2026-04-23-sprint-4-risk-tasks-1-8.md#task-8-srcriskequity_trackerpy--equitytracker)
- [Task 9: `src/risk/circuit_breakers.py` — `CircuitBreakerDetector`](2026-04-23-sprint-4-risk-tasks-9-13.md#task-9-srcriskcircuit_breakerspy--circuitbreakerdetector)
- [Task 10: `src/risk/override.py` — `OverrideStore`](2026-04-23-sprint-4-risk-tasks-9-13.md#task-10-srcriskoverridepy--overridestore)
- [Task 11: `src/risk/state_repo.py` — JSON kv adapter](2026-04-23-sprint-4-risk-tasks-9-13.md#task-11-srcriskstate_repopy--json-kv-adapter-for-state-table)
- [Task 12: `src/risk/manager.py` — `RiskManager` orchestrator](2026-04-23-sprint-4-risk-tasks-9-13.md#task-12-srcriskmanagerpy--riskmanager-orchestrator)
- [Task 13: `src/risk/resume_cb.py` + CLI](2026-04-23-sprint-4-risk-tasks-9-13.md#task-13-srcriskresume_cbpy--srcriskmainpy--cli)
- [Task 14: Legacy cleanup — remove `src/risk/risk_manager.py`](2026-04-23-sprint-4-risk-tasks-14-17.md#task-14-legacy-cleanup--remove-srcriskrisk_managerpy)
- [Task 15: Integration test — `tests/integration/test_risk_flow.py`](2026-04-23-sprint-4-risk-tasks-14-17.md#task-15-integration-test--testsintegrationtest_risk_flowpy)
- [Task 16: Wiki component pages](2026-04-23-sprint-4-risk-tasks-14-17.md#task-16-wiki-component-pages)
- [Task 17: Sprint delivery record + wiki updates](2026-04-23-sprint-4-risk-tasks-14-17.md#task-17-sprint-delivery-record--wiki-updates)

---

## Critical requirements

- **TDD strict:** RED → GREEN → VERIFY → COMMIT every task. No implementation before failing test.
- **Decimal everywhere** for money; float only inside Wilson CI sqrt computation (cast back to Decimal).
- **Reason codes from existing 28-enum only.** New codes → Follow-up requiring ADR amendment. Do NOT add silently.
- **Look-ahead safety:** `assess()` only uses data with `ts ≤ signal.generated_at`. Enforced via SQL `WHERE ts <= ?`.
- **Determinism:** inject `clock: Callable[[], datetime]` — no `datetime.now()` in domain logic anywhere.
- **Test isolation:** `tmp_path` fixture per test, fresh SQLite per test.
- **Atomic state updates:** Kelly phase + equity snapshot + CB level in single `with conn:` block via `StateRepo.update_many()`.
- **scipy NOT required** — Wilson CI is inline formula, no extra dependency.

---

## Self-review checklist

- [ ] Every §S4 AC mapped to ≥1 task
- [ ] Legacy `src/risk/risk_manager.py` removed (Task 14)
- [ ] Kelly transitions n=29→30, 99→100, 199→200 covered (Task 6 + Task 15)
- [ ] CB L1/L2/L3/flash all covered (Task 9 + Task 15)
- [ ] Override flow tested end-to-end (Task 10 + Task 15)
- [ ] Wiki component pages updated (Task 16)
- [ ] No `datetime.now()` in domain logic — `clock` injected (Tasks 12, 13)
- [ ] All Edit chunks succeeded; final file ≥1500 lines
- [ ] ReasonCode: only canonical 28 used; non-canonical names flagged as Follow-up
- [ ] Property tests for sizing (hypothesis, 200 examples)
- [ ] `config_hash()` deterministic + changes with value (Task 2)
- [ ] `init_db()` idempotency verified (Task 1)
- [ ] Integration test covers 50 bars, 5 trades, phase transition, CB trigger, override (Task 15)

---

## Follow-ups (require ADR amendment)

**FA-1 — ReasonCode namespace for risk rejections:**
The task prompt requested codes `APPROVED`, `RISK_REJECT_HALT_L1`, `RISK_REJECT_HALT_L2`, `RISK_REJECT_HALT_L3`, `RISK_REJECT_HALT_FLASH`, `RISK_REJECT_INVALID_SIGNAL`, `RISK_REJECT_ZERO_QTY`. None of these exist in the canonical 28-enum (`wiki/trading/concepts/reason-codes.md`). Current mapping:
- `RISK_REJECT_HALT_L1` → `HALT_DRAWDOWN_L1` (existing)
- `RISK_REJECT_HALT_L2` → `HALT_DRAWDOWN_L2` (existing)
- `RISK_REJECT_HALT_L3` → `HALT_DRAWDOWN_L3` (existing)
- `RISK_REJECT_HALT_FLASH` → `HALT_FLASH_CRASH` (existing)
- `APPROVED` → no code; entry uses `ENTRY_LONG_TREND_FOLLOWING`
- `RISK_REJECT_INVALID_SIGNAL` → no canonical match; closest: `REJECT_STALE_DATA` or `REJECT_FILTER_PRICE`
- `RISK_REJECT_ZERO_QTY` → `REJECT_RISK_EXCEEDED` (existing, covers zero qty case)

**Action required:** If the RISK_REJECT_* namespace is intentional design, open ADR to amend the 28-enum. Until then, implementation uses existing canonical codes only.

**FA-2 — Regime shift downgrade:**
KS-test (p<0.01) → revert Phase 1 logic deferred to S7. `KellyCalculator` has no regime detection — by design.

**FA-3 — Event Bus integration:**
`RiskManager.on_bar_close()` and `update_equity()` are synchronous. Async event-driven integration deferred to S6.
