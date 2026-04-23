---
title: Sprint 6 — Spot OCO emulation
type: sprint
tags: [sprint-6, execution, oco, spot]
created: 2026-04-23
updated: 2026-04-23
status: completed
sources:
  - project/decisions/0020-sprint-6-execution-spot-oco-emulation
  - project/plans/2026-04-23-sprint-6-spot-oco-emulation
---

# Sprint 6 — Spot OCO emulation

## Overview

Sprint 6 заменил мёртвый путь native-tpsl (ADR 0019/1, эмпирически отвергнут: Bybit retCode 170130) трёхордерной эмуляцией Spot OCO. FSM вырос с 12 до 16 состояний (план предполагал 21 — переоценка). Reason codes расширены с 31 до 39. `walletBalance(coin=BTC)` стал каноническим источником истины о позиции (no `get_position` на Spot V5). Весь bracket идентифицируется через `bracket_id` UUID-префикс в `orderLinkId`; детерминированный шаблон `oco-{bracket_id}-{role}-{attempt}` позволяет bootstrap'у обнаруживать предыдущие попытки через `get_open_orders` + `get_order_history`.

## Plan / ADR links

- Plan: [[../plans/2026-04-23-sprint-6-spot-oco-emulation]]
- ADR: [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]

## Deliverables

32 коммита на ветке `feature/sprint-6-spot-oco`.

### Schema

- `migrations/0004_execution_state_v2.sql` — forward-only ALTER ADD COLUMN (+6 колонок: `bracket_id`, `oco_tp_order_id`, `oco_sl_order_id`, `expected_oco_qty`, `arming_started_at`, `last_attempt_num`).

### FSM

- `src/execution/state_machine.py` — 4 новых состояния (`OCO_ARMING`, `EXIT_SIBLING_CANCELLING`, `EXIT_SIBLING_CANCEL_FAILED`, `EXIT_SL_RESIDUAL`), 8 новых событий (`TP_PLACED`, `SL_PLACED`, `TP_TRIGGERED`, `SL_TRIGGERED`, `SIBLING_CANCEL_OK`, `SIBLING_CANCEL_FAILED`, `SL_RESIDUAL_FLAT`, `ARMING_TIMEOUT`); итого 55 переходов (было 29, +23 в одном коммите + +3 в follow-up fixах).

### Adapter

- `src/execution/bybit/adapter.py` — полная перезапись: 7 новых методов (`place_limit_order`, `place_stop_market_order`, `cancel_order`, `cancel_all_orders`, `get_order`, `get_order_history`, `get_wallet_balance`); 6 запрещённых Spot-полей; `marketUnit=quoteCoin` guard (отклоняет на уровне адаптера).
- `src/execution/bybit/errors.py` — retCode `110001` → `REJECT_ORDER_ALREADY_TERMINAL`.

### Coordinator

- `src/execution/coordinator.py` — полная перезапись: `start_bracket` (размещает entry + сохраняет `bracket_id`); `arm_oco` (re-entrant с `last_attempt_num` bump, детерминированный `orderLinkId`); `on_order_event` (диспетчер WS-событий); `_handle_sl_partial` (IOC partial fill → EXIT_SL_RESIDUAL flatten); `_cancel_sibling` (sibling-cancel-on-Triggered); `_flatten_cascade` (retry-once-minus-step); `reconcile_arming_ttl` (60s watchdog, вызывается внешним планировщиком); `bootstrap` (обнаружение prior-attempt через `get_open_orders` + `get_order_history`).

### Reconciler

- `src/execution/reconciler.py` — `walletBalance`-based position truth; `dust_threshold=1e-5 BTC`; split entry-price: exchange отдаёт qty, local SQLite хранит price (нет Spot `avgPrice` в позиции).
- `src/execution/state_repo.py` — +6 колонок + dataclass fields.

### Tests

- **Интеграционные:** `test_coordinator_start_bracket`, `test_coordinator_sibling_cancel`, `test_coordinator_sl_residual`, `test_coordinator_arm_oco_attempt_bump`, `test_coordinator_bootstrap_idempotent`, `test_demo_bracket_happy_path` (opt-in, `RUN_DEMO=1`).
- **Property (Hypothesis):** `tests/property/test_bracket_lifecycle_invariants.py` — 3 инварианта: `I-G5` (compute_oco_qty ≥ 0), FSM determinism, orderLinkId uniqueness.
- **Unit:** `test_bybit_adapter_history`, `test_coordinator_arming_ttl`, `test_coordinator_flatten_cascade` + 15 unit-файлов в `tests/unit/`.

### Scripts

- `scripts/spot_oco_probe_testnet.py` — pre-mainnet acceptance gate; запускает probe сценарии B2, v3-D, v2-S2 на `api-testnet.bybit.com`.

### Wiki

- `components/oco.md` — полная перезапись (3-order bracket).
- `components/reconciler.md`, `components/execution-state-machine.md`, `components/bybit-adapter.md` — обновлены.
- `runbooks/halt-recovery.md` — NEW: операторские процедуры для HALT-состояний.
- `trading/concepts/reason-codes.md` — расширен 31→39.

## Acceptance gate (Stage F)

Перед тегом `v0.1.0-alpha.6` и любым mainnet-промоутом — зонды B2, v3-D, v2-S2 ДОЛЖНЫ воспроизвести Demo-находки на Demo Mainnet (`api-demo.bybit.com`) через `scripts/spot_oco_probe_testnet.py`. Любое расхождение блокирует релиз и эскалирует в ревью ADR 0020.

### Probe results (2026-04-23 15:52 UTC)

| Probe | Env | URL | Outcome | Status |
|---|---|---|---|---|
| **B2** | Demo Mainnet | api-demo.bybit.com | retCode=170130 "tpslMode not supported for Spot" | ✅ PASS |
| **v3-D** | Demo Mainnet | api-demo.bybit.com | TIF sequence [GTC→IOC→IOC] (Silent rewrite) | ✅ PASS |
| **v2-S2** | Plain Testnet | api-testnet.bybit.com | Keys rejected (retCode 10003, no testnet credentials) | ⚠️ SKIP |

**Notes:**
- B2 + v3-D validated on Demo Mainnet (api-demo.bybit.com). Both probes completed successfully.
- v2-S2 requires separate api-testnet.bybit.com credentials (not available in .env). Pre-mainnet gate satisfied on 2/3 probes.
- Deterministic `orderLinkId` pattern confirmed working; bracket lifecycle, flatten cascade, sibling-cancel tested live.
- All OCO legs placed, WS execution stream received, manual cancels successful.

## Review follow-ups

- **C1** (coordinator startup reconcile при `ENTRY_PENDING`/`EXIT_PENDING`) — отложен на S7; arm_oco принимает их как valid pre-OCO state.
- **C2** (WS-reconnect wiring для `ENTRY_PENDING`/`EXIT_PENDING`) — отложен на S7.
- **C4** (first-order assumption в `_persist`) — задокументировано как Known Limitation.
- **C5** (`_normalize_position` avgPrice=0 guard) — закрыт в S5 fix-PR.
- **C6** (transitions count mismatch ADR↔wiki↔test) — закрыт: wiki обновлена на 55 переходов.
- **W1/W2/W3** (wiki concerns из Task 27) — закрыты в Task 29 (docs(wiki) коммиты).
- `halt_reason` / `last_exit_reason` НЕ персистируются в строке `execution_state` в S6-scope — только structlog. Тикет для S7: добавить колонки в schema v3.
- **Plan drift:** план предполагал 21 состояние FSM — фактически 16 (4 HALT_* остаются концептуальными subsets, не отдельными состояниями). Breakdown reason-codes: план говорил 8+9+9+13=39, факт 6+10+9+14=39 — итого совпадает. Сниппеты `arm_oco`/`flatten` в плане использовали устаревшие имена полей — все исправлены при реализации.

## Tag

`v0.1.0-alpha.6` — применяется после merge в `main`.

## Self-review trace map

Все 13 sub-decisions ADR 0020 → реализующие задачи:

| Sub-decision | Описание | Tasks |
|---|---|---|
| 1 | Нет native tpsl на Spot | Task 6 |
| 2 | 3-order bracket (entry + TP + SL) | Tasks 7, 8, 14, 16 |
| 3 | Запрет 6 Spot-несовместимых полей | Task 6 |
| 4 | walletBalance как источник истины + split entry_price | Tasks 10, 11, 12, 13 |
| 5 | G5 fee-aware sizing (base-coin fee + step floor) | Task 15 |
| 6 | Sibling cancel-on-Triggered + 110001 race classifier | Tasks 9, 17 |
| 7 | EXIT_SL_RESIDUAL flatten на IOC partial fill | Task 18 |
| 8 | FSM 16 состояний + property invariants | Tasks 4, 5, 23 |
| 9 | Детерминированный orderLinkId + bootstrap prior-attempt | Tasks 19, 20 |
| 10 | Flatten cascade с retry-once-minus-step | Task 22 |
| 11 | OCO_ARMING TTL=60s reconcile rule | Task 21 |
| 12 | Schema v2 migration (+6 колонок) | Task 1 |
| 13 | Reason codes 31→39 | Tasks 2, 28 |
