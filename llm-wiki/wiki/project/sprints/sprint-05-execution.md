---
title: Sprint 5 — Execution layer (OCO + FSM + Reconciler)
type: summary
tags: [sprint, sprint-5, execution, oco, fsm, reconciler]
created: 2026-04-23
updated: 2026-04-23
sources: [project/plans/2026-04-23-sprint-5-execution.md]
status: done
---

# Sprint 5 — Execution layer (OCO + FSM + Reconciler)

**Dates:** 2026-04-23
**Plan:** [[../plans/2026-04-23-sprint-5-execution]]
**Tag:** skipped — S5 merged into `v0.1.0-alpha.6` (consolidates S4+S5+S6 ship). Drift note: original plan tagged `v0.1.0-alpha.5 (pending PR merge)` 2026-04-23, но tag `alpha.5` never created. Reconciled 2026-04-25.
**Merge PR:** consolidated в S6 PR
**Commit range:** `7fa328f..HEAD`

## Goal

Реализовать advanced execution layer на Bybit Spot V5: native OCO bracket (`tpslMode=Full`), формальный 12-state FSM с table-driven transitions, post-reconnect reconciler с reconcile-as-truth, plus opt-in testnet happy-path test.

## Scope delivered

### Code

- `src/risk/reason_codes.py` — +2 codes (`HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT`); total 29 → 31.
- `src/execution/state_machine.py` — 12-state FSM, 29 transitions, `IllegalTransitionError`.
- `src/execution/state_repo.py` — `ExecutionStateRow` + `ExecutionStateRepo` (sqlite, Decimal-as-TEXT).
- `src/execution/oco.py` — `build_oco_order(OcoParams) -> OcoOrder`, ROUND_DOWN/UP snap.
- `src/execution/bybit/adapter.py` — расширен `place_market_order` с `take_profit`/`stop_loss`/`tpsl_mode` kwargs (sub-decision 1).
- `src/execution/reconciler.py` — `Reconciler.fetch_exchange_state` + `Reconciler.reconcile` (sub-decision 3).
- `src/execution/coordinator.py` — `handle_ws_reconnect` orchestration.

### Migrations

- `migrations/0003_execution_state.sql` — `execution_state` table (PK symbol).

### Tests

- Unit (8 файлов): `test_reason_codes.py`, `test_execution_fsm.py` (если был), `test_state_repo.py`, `test_oco.py`, `test_bybit_adapter_oco.py`, `test_reconciler_fetch.py`, `test_reconciler_diff.py`, `test_coordinator_reconcile.py`.
- Integration: `tests/integration/test_execution_oco_testnet.py` (opt-in via `PYTEST_RUN_INTEGRATION=1`).

### Wiki

- Added: `components/{oco,reconciler,execution-state-machine}.md`, `decisions/0019-sprint-5-execution-decisions.md`, this sprint page.
- Updated: `components/bybit-adapter.md` (Sprint 5 extension section), `trading/concepts/reason-codes.md` (29→31 + new codes), `index.md`, `log.md`.

## Decisions & deviations

- **Sub-decision 1:** Native Bybit `tpslMode=Full`, NOT emulated.
- **Sub-decision 2:** 12-state FSM table-driven (Harel-style), property-test-friendly.
- **Sub-decision 3:** SQLite warm-cache + reconcile-as-truth (exchange wins on divergence).
- **Sub-decision 4:** +2 reason codes (29 → 31 total).
- **Sub-decision 5:** Testnet scope = happy path only in S5 (partial-fill / WS-disconnect → S5.5 / S6).
- **Plan drift:** Plan tasks 8 / 9 содержали preliminary signatures (`BybitAdapter.place_order`, flat `position_qty` snapshot) — actual code использует `BybitMarketAdapter.place_market_order` + nested `ExchangeState.position`. Briefs subagent'ам корректировались на месте.

## Verification

- `pytest tests/unit/ -q`: ~340 passed (≥30+ новых S5 тестов; точные числа see commits 7fa328f..HEAD).
- Pre-existing 5-6 `numpy`/`pybit`/`talib`/`pyarrow` collection-errors не относятся к S5.
- Testnet integration: SKIPPED без `PYTEST_RUN_INTEGRATION=1` (как ожидается).

## Impact on downstream

- S6 (event sourcing): `execution_state` table станет projection из event log; параллельная схема — план переноса в S7+ (см. ADR 0019 trade-off раздел).
- S6: `OCO_PARTIAL_TIMEOUT` watchdog daemon (currently событие есть в FSM, watcher TBD).
- S5.5 / S6: integration tests на partial-fill + WS-divergence (отложены per sub-decision 5).

## Follow-ups carried forward

- [ ] Partial-fill scenario integration test — controlled liquidity required, S5.5 / S6.
- [ ] WS reconnect divergence integration test — injected disconnect, S5.5 / S6.
- [ ] `OCO_PARTIAL_TIMEOUT` watchdog daemon — S6.
- [ ] Trailing stop — v0.2 candidate (требует переход с native tpslMode на эмуляцию).
- [ ] HIGH-3 from S4 trading-logic review: `bar: object` loose typing в `on_bar_close` — теперь Bar контракт стабилизирован, но fix отложен в S5 (не делали в S5 scope).

## Related

- Plan: `[[../plans/2026-04-23-sprint-5-execution]]`
- ADR: `[[../decisions/0019-sprint-5-execution-decisions]]`
- Components: `[[../components/oco]]`, `[[../components/reconciler]]`, `[[../components/execution-state-machine]]`, `[[../components/bybit-adapter]]`
- Concepts: `[[../../trading/concepts/reason-codes]]`
- Sprint 4 (predecessor): `[[sprint-04-risk]]`
