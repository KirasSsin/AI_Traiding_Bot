---
title: Sprint 7 — Resilience
type: sprint
tags: [sprint-7, execution, resilience, halt-persistence, ws-reconnect, fsm-v3]
created: 2026-04-24
updated: 2026-04-24
status: completed
sources:
  - project/decisions/0021-sprint-7-resilience
  - project/plans/2026-04-24-sprint-7-resilience
---

# Sprint 7 — Resilience

## Overview

Sprint 7 закрывает три interconnected resilience gap'а из S6 follow-ups: C1 (cold-start reconcile classification), C2 (WS reconnect mid-bracket diff), γ (halt persistence across restart). FSM вырос с 16/29/55 (S6) до 16/29/59 (-2 silent dup-keys per ruff F601 + 6 reconcile/timeout transitions). Reconciler стал 4-valued (AGREE / DIVERGENCE / HEAL_ENTRY_FILLED / EXITED) с `expected_state` hint + `heal_context`. Heal staleness threshold = 3600s (1H bar period). γ halt persistence — primary-wins semantics (first non-null sticks до MANUAL_RESET) + halt_log append-only audit. B1 narrow scope: passive WS consumer, driver loop отнесён в S8.

## Plan / ADR links

- Plan: [[../plans/2026-04-24-sprint-7-resilience]]
- ADR: [[../decisions/0021-sprint-7-resilience]]

## Deliverables

33+ commits на ветке `feature/sprint-7-resilience`.

### Schema

- `migrations/0005_halt_persistence.sql` — forward-only ALTER ADD COLUMN (+4 колонки: `halt_reason`, `last_exit_reason`, `last_reconcile_at`, `bootstrap_at`); CREATE TABLE `halt_log` (audit append-only, indexed by symbol+ts).

### FSM v3

- `src/execution/state_machine.py` — 6 новых transitions (RECONCILE_ENTRY_FILLED, RECONCILE_EXITED, OCO_PARTIAL_TIMEOUT) + dedup 2 silent S6 dup-keys (ruff F601). Итого 16 states / 29 events / 59 transitions.

### Reconciler

- `src/execution/reconciler.py` — 4-valued verdict через `ReconcileResult v3` (verdict, expected_state hint, heal_context dict). `heal_max_age_seconds=3600` config. OrderSnapshot snake_case fields (order_status, avg_price, cum_exec_fee, fee_currency).

### Coordinator

- `src/execution/coordinator.py` — `bootstrap()` always reconciles (cold + warm). `_bootstrap_done` assert на `start_bracket` + `on_order_event` (sequencing guard). `_RECONCILABLE_STATES` frozenset (9 active states) для WS_RECONNECT coverage. `start_bracket` capture `entry_ack.order_id` для HEAL path addressability. γ halt persistence: write-ahead `halt_log` → `execution_state.halt_reason` (primary-wins).

### WS Private Consumer (B1 narrow scope)

- `src/execution/bybit/ws_private.py` — pybit `unified_trading.WebSocket` close-hook через inner `WebSocketApp.on_close` + `check_alive` heartbeat watchdog (backstop при pybit upgrade). Order parser: cumExecFee mandatory drop guard для Filled/PartiallyFilled. Wallet parser: multi-coin dispatch.

### Reason codes

39 → 42: +EXIT_RECONCILE_DETECTED (scale/exits), +HALT_BOOTSTRAP_AMBIGUOUS, +HALT_EXIT_RECONCILE_DIVERGENCE (halts).

### Tests

- **Unit:** 481 pass / 28 skipped (pre-existing pyarrow/talib/asyncio gaps unrelated).
- **Property:** `tests/property/test_bootstrap_ws_reconnect_idempotent.py` — N reconnects under FSM stay idempotent.
- **Integration (opt-in `RUN_DEMO=1`):** bootstrap HEAL path on Bybit Demo.

### Wiki Stage E

- Updated: `components/execution-state-machine.md` (16/29/59 + γ persistence), `components/reconciler.md` (4-valued verdict), `components/oco.md` (entry_order_id capture), `components/bybit-adapter.md` (links). NEW `components/ws-private-consumer.md`. `runbooks/halt-recovery.md` (+HALT_BOOTSTRAP_AMBIGUOUS, +HALT_EXIT_RECONCILE_DIVERGENCE sections; SQL templates updated to S7 schema). `trading/concepts/reason-codes.md` (39→42). `index.md` + `log.md`.

## Phase G — Acceptance gate (Demo Mainnet)

**Re-scoped 2026-04-24:** initial scope требовал `api-testnet.bybit.com` с отдельной testnet credential pair. Re-scoped к Demo Mainnet (`api-demo.bybit.com`) — v0.1 ops target = Demo Mainnet, не testnet. Demo Mainnet = real Bybit production matching engine (только money fake), релевантнее для v0.1 чем testnet (отдельный движок).

| Probe | Endpoint | Expected | Result | Evidence file |
|---|---|---|---|---|
| **B2** | api-demo.bybit.com | retCode=170130 on `tpslMode=Full` | ✅ `InvalidRequestError ErrCode: 170130` | `scripts/spot_oco_probe_output.json` (`B2_native_tpsl_attempt`) |
| **v3-D** | api-demo.bybit.com | TIF echo IOC after submit GTC | ✅ TIF sequence `[IOC, IOC, IOC]`; status `[Untriggered, Triggered, Filled]` | `scripts/spot_oco_probe_v3_output.json` (`v3AD_tif_sequence`) |
| **v2-S2** | api-demo.bybit.com (S6) | marketUnit=quoteCoin BTC drift > 8 decimals | ✅ S6 evidence persists; testnet attempt 2026-04-24 = 401/10003 (separate keys not provisioned). Adapter unconditionally pins `marketUnit=baseCoin` → exchange-side property не достигается из bot path. | `scripts/spot_oco_probe_v2_output.json` (S6) |

**Decision:** v0.1 ops target = Demo Mainnet → tag `v0.1.0-alpha.7` valid for Demo Mainnet only. Mainnet promotion (v0.2+) requires fresh acceptance gate (testnet или mainnet smoke с small size). `settings.require_mainnet_gate_passed: bool = True` startup validator FAILs until v0.2 gate passes.

## Tag

`v0.1.0-alpha.7` — feature/sprint-7-resilience → main, 2026-04-24.

## Notable decisions (highlights)

- B1 narrow scope (sub-decision 6): только passive WS consumer; driver loop отнесён в S8.
- pybit `on_disconnect` без user-level callback → close-hook через inner `WebSocketApp.on_close` + heartbeat watchdog (`check_alive`) backstop при pybit upgrade breaking change.
- 4-valued verdicts с `recommended_state` hint — coordinator делегирует FSM-выбор reconciler'у (separation of concerns).
- halt_reason primary-wins (first non-null sticks до MANUAL_RESET) + halt_log append-only audit.
- heal_max_age_seconds = 3600 (1H bar period) — heal только если fill свежее.
- Phase G Demo Mainnet vs testnet: re-scoped по принципу "v0.1 target = Demo, validate where you ship".

## Follow-ups → S8+

- Driver loop для WS consumer (B1 deferred).
- `execution` topic subscription + per-fill Analytics — S8 Analytics sprint.
- External kill-switch signal (SIGTERM, lint) → KILL_SWITCH event — S8 manager.py orchestration.
- Mainnet acceptance gate (testnet OR mainnet smoke с small size) — v0.2 prerequisite.
- Pre-existing test_risk_flow OverrideStore signature drift (unrelated to S7) — defer.
- pyarrow/talib/asyncio test gaps (28 skipped) — defer.

## Related

- [[../decisions/0021-sprint-7-resilience]]
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]
- [[../components/execution-state-machine]]
- [[../components/reconciler]]
- [[../components/ws-private-consumer]]
- [[../runbooks/halt-recovery]]
- [[sprint-06-spot-oco-emulation]]
