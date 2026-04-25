---
title: Sprint 12 — Live demo validation 24-72h + production wiring
type: sprint
tags: [sprint-12, live-demo, fill-recorder, parquet-shim, operator-runbooks, bybit-demo]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-12-live-demo-validation
  - project/decisions/0027-sprint-12-live-demo-validation
  - project/pre-s12-backlog
---

# Sprint 12 — Live demo validation 24-72h + production wiring

## Overview

S12 closes two production-wiring carry-overs from S11 and delivers the operator infrastructure needed for the first live demo validation cycle on Bybit Demo. `FillRecorderAdapter` replaces the 8-month-old `_NoopFillRecorder` stub in `_cmd_run` (S11 T2 deferral closed), and `_load_ohlcv` gains a Parquet shim that wires `data_collector.load_market_data` into the WFA CLI subcommand (closing the Gate 5 empty-DataFrame stub from S11). Two operator runbooks (`live-demo-validation.md` + `halt-response-protocol.md`) document the 48h validation procedure and P0 rollback protocol. Tag `v0.1.0-alpha.12`.

S12 operates in orchestration + adapter mode: no FSM growth, no new migrations. The Q7 zero-migration constraint (enforced as a hard plan-level commitment) preserves `v0.1.0-alpha.11` binary rollback compatibility throughout the S12 schema window. A critical endpoint-routing correction (Q6) was applied to SPRINT_STATE pre-PHASE 3: the S11 carry-over note "fix endpoint к testnet substring" was factually WRONG — current `"demo.bybit.com"` routing is correct for S12 demo intent, verified by trader-expert source-citing evidence.

## Plan / ADR links

- ADR (NEW): [[../decisions/0027-sprint-12-live-demo-validation]]
- Brainstorm trail: [[../pre-s12-backlog]]
- Predecessor: [[sprint-11-operator-readiness]]

## Deliverables

6 tasks, all TDD.

- **T1** (`044dad8`): `FillRecorderAdapter` — `src/risk/fill_recorder_adapter.py`. Implements `_FillRecorderProto`. 2-layer pattern: always-on structlog audit + best-effort DB insert via `execution_state.find_by_order_id → trade_history.find_trade_id_by_signal → FillHistoryRepository.insert_fill`. Race-condition safe (skip+warn). 7 unit tests. Closes S11 `_NoopFillRecorder` stub (S8a T20, S11 T2 deferral).
- **T2** (`5d94c1a`): `_load_ohlcv` Parquet shim — `src/__main__.py`. Translates CLI args `(symbol, start, end)` → `data_collector.load_market_data(config_dict)`. Improved error message on missing Parquet. Updated `pre-flight.md` Gate 5 documentation. 2 unit tests. Closes S11 `_cmd_wfa` empty-DataFrame stub.
- **T3** (`8f4dd1e`): Pre-flight Gate 5 `_cmd_wfa` integration + `HALT_BOOTSTRAP_AMBIGUOUS` + `OCO_ARMED` conditional P1 escalation to CRITICAL documented in `halt-recovery.md`. Pre-flight Gate 5 updated for Parquet prerequisite.
- **T4** (`51dc3c4`): `wiki/project/runbooks/live-demo-validation.md` — operator playbook for first 48h Bybit Demo validation cycle. HARD-GATE pre-conditions (all 5 pre-flight gates pass) + multi-criteria success gate with MANDATORY zero-trade clause (Q3 CONFIRM).
- **T5** (`bd172e1`): `wiki/project/runbooks/halt-response-protocol.md` — P0 wake decision tree + `v0.1.0-alpha.11` rollback procedure (Q7: zero-migration enables clean binary rollback) + RC tag iteration protocol.
- **T6** (this commit): ADR 0027 status `proposed → accepted` + this sprint page + `fill-recorder-adapter` component page + `index.md` + `current-state.md` + `mental-map.md` counts sync.

## FSM growth — NONE

S12 = orchestration layer + adapters + documentation. FSM/counts unchanged:

| Metric | Value |
|--------|-------|
| FSM states | 16 |
| FSM events | 30 |
| FSM transitions | 74 |
| Reason codes | 45 |

## Reason codes growth — NONE

## Tests

- pytest unit: **689 passed** (baseline 680 pre-S12 + 7 T1 `test_fill_recorder_adapter.py` + 2 T2 `_load_ohlcv` tests)
- mypy --strict src/: clean (67 source files — +1 `fill_recorder_adapter.py`)
- ruff: clean on touched files
- migrations diff vs main: **empty** (Q7 zero-migration constraint verified)

## Wiki updates

- 2 NEW runbook pages: `live-demo-validation.md` + `halt-response-protocol.md`
- 1 NEW component page: `fill-recorder-adapter.md` (per T1 trading-logic-reviewer follow-up)
- 1 NEW ADR: `0027-sprint-12-live-demo-validation.md`
- 1 NEW sprint page: this file
- Modified: `halt-recovery.md` (P1 `HALT_EXCHANGE_OUTAGE` + `OCO_ARMED` conditional escalation), `pre-flight.md` (Gate 5 Parquet prerequisite), `index.md`, `mental-map.md`, `current-state.md`

## Open issues для S13+

- **F (live demo Mainnet validation actual run)** — operator-driven post-merge; S12 ships infrastructure, not the run itself.
- **FillRecorderAdapter Layer 2 schema gap** — `execution_state` table has no `entry_signal_id` column (migrations 0003+0004+0005); lookup chain breaks at `bracket_id↔trade_id` gap → Layer 2 always-skips during S12. Fix: add `entry_signal_id` to `execution_state` migration + wire `Coordinator.start_bracket` to persist `signal_id`. Q7 zero-migration constraint deferred this to S13.
- **3-way endpoint enum (DEMO/TESTNET/MAINNET) refactor** — Q6 REVISE-DISAGREE-FACTUAL: current routing correct for S12, full enum к S13+.
- **DSR per-fold DataFrame→TradeRecord conversion** — informational, deferred from S10.
- **DSR threshold calibration** — S15+, needs ≥30 trades.
- **`halt_log` INSERT order swap в `_set_halt`** — pre-existing, data-integrity reviewer T1 follow-up.
- **`find_by_order_id` ORDER BY explicit** — T1 reviewer follow-up, future-safe for multi-symbol.

## Key decisions

| Decision | Verdict |
|----------|---------|
| Q1: exchange for demo validation | CONFIRM: Bybit Demo trading endpoint |
| Q2: validation duration | CONFIRM: 48h |
| Q3: success gate definition | CONFIRM: multi-criteria + MANDATORY zero-trade clause |
| Q4: `_load_ohlcv` production data integration | REVISE-additive: Parquet shim via `data_collector` (config-dict API mismatch) |
| Q5: FillRecorderAdapter class | REVISE-additive: new class required (`FillHistoryRepository` not drop-in for `_FillRecorderProto`) |
| Q6: endpoint string change for S12 | REVISE-DISAGREE-FACTUAL: NO change — current `"demo.bybit.com"` routing CORRECT; S11 carry-over note WAS WRONG |
| Q7: halt response + rollback protocol | CONFIRM: P0-wake + `alpha.11` rollback + RC tag iteration + zero-migration constraint |
| C4: zero-migration hard constraint | Hard plan-level commitment; `trade_fills` table reused from S9 schema |
| 2-layer adapter pattern | Audit always fires (structlog); DB insert best-effort only when lookup chain resolves fully |

## Related

- [[../decisions/0027-sprint-12-live-demo-validation]] — aggregate ADR + Q-verdicts trail
- [[sprint-11-operator-readiness]] — predecessor sprint (operator infrastructure consumed by S12)
- [[../runbooks/live-demo-validation]] — 48h validation playbook (T4)
- [[../runbooks/halt-response-protocol]] — P0 rollback procedure (T5)
- [[../runbooks/halt-recovery]] — priority matrix + S12 P1→CRITICAL escalation update
- [[../runbooks/pre-flight]] — Gate 5 Parquet prerequisite updated (T2)
- [[../components/fill-recorder-adapter]] — component page (T6 follow-up from T1 reviewer)
