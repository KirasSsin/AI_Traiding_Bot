---
title: 0019. Sprint 5 — Execution advanced (OCO / FSM / Reconciler) decisions
type: decision
tags: [adr, sprint-5, execution, oco, fsm, reconciler]
created: 2026-04-23
updated: 2026-04-23
status: accepted
---

# 0019. Sprint 5 — Execution advanced decisions

**Status:** accepted (sub-decision 1 superseded by [[0020-sprint-6-execution-spot-oco-emulation]])
**Date:** 2026-04-23
**Sprint:** S5
**Supersedes:** —
**Superseded-in-part-by:** [[0020-sprint-6-execution-spot-oco-emulation]] (sub-decision 1 native `tpslMode=Full` empirically rejected for Spot V5; sub-decisions 2/3/4 amended — FSM 12→21 states, schema v2, reason codes 31→39)
**Amends:** [[0018-sprint-4-risk-decisions]] (extends reason-code enum)
**Related:** [[../architecture/migration-plan]] §S5

## Context

Sprint 5 реализует продвинутый execution layer поверх минимального S2 Bybit-adapter'а:
OCO bracket (SL+TP), partial-fill handling, post-reconnect reconciliation, 12-state machine.
Перед TDD-планом нужно зафиксировать архитектурные решения, влияющие на > 1 модуль.

## Sub-decisions

### Sub-decision 1 — Native Bybit `tpslMode` для OCO (НЕ эмулируем)

> **⚠️ SUPERSEDED by [[0020-sprint-6-execution-spot-oco-emulation]] sub-decision 1.**
> Empirical probe v1 (`scripts/spot_oco_probe.py` line 20) confirmed that Bybit Spot V5
> Market `place_order` rejects `tpslMode/takeProfit/stopLoss/tpOrderType/slOrderType`
> with ErrCode 170130 ("Data sent for paramter '' is not valid"). These fields are
> valid only for linear/inverse contracts, not Spot. ADR 0020 replaces this with a
> 3-order emulated bracket (Entry Market → Limit Sell @ TP → Stop Market Sell @ SL)
> + client-side sibling cancel-on-Triggered.

**Decision (rejected):** используем нативный Bybit Spot V5 `tpslMode=Full` с `takeProfit` и `stopLoss`
полями в одном `place_order` запросе. Не эмулируем OCO через два отдельных
conditional ордера + cancel-on-fill wiring.

**Rationale:**
- Bybit на стороне биржи гарантирует cancel-on-fill (одна нога заполнилась → вторая отменена).
- Меньше edge cases (race между partial-fill и cancel).
- Меньше rate-limit нагрузки (1 запрос вместо 3).
- v0.1 — single symbol (BTC/USDT), нативный tpslMode достаточен.

**Trade-off:** теряем независимый контроль над SL/TP modify (если захотим
trailing stop в v0.2 — придётся перейти на эмуляцию). Это явно вне scope v0.1.

**Code refs:**
- `src/execution/oco.py::build_oco_order` — конструирует `place_order` payload с
  `takeProfit = entry + 3.0·ATR`, `stopLoss = entry - 1.5·ATR` (k из `Settings`).
- `src/execution/bybit/adapter.py::place_order` — расширяется поддержкой
  `tpslMode`, `takeProfit`, `stopLoss`, `tpOrderType`, `slOrderType`.

### Sub-decision 2 — 12-state FSM (Harel-style)

**Decision:** формальный набор состояний execution layer:

| # | State | Описание |
|---|---|---|
| 1 | `INIT` | старт процесса, до загрузки state |
| 2 | `FLAT` | нет открытых позиций, нет pending ордеров |
| 3 | `ENTRY_PENDING` | entry ордер отправлен, ждём fill |
| 4 | `LONG_OPEN` | позиция открыта, OCO ещё не выставлен |
| 5 | `OCO_ARMED` | позиция открыта + OCO активен (нормальный режим) |
| 6 | `PARTIAL_FILL` | OCO partial fill, осталось < full qty |
| 7 | `EXIT_PENDING` | exit ордер (TP/SL/flip) отправлен, ждём confirm |
| 8 | `RECONCILING` | post-reconnect: сравниваем local ↔ exchange |
| 9 | `HALTED` | risk halt (CB L1/L2/L3/flash) — не торгуем, держим позицию |
| 10 | `COOLDOWN` | post-halt пауза перед re-entry (per Settings) |
| 11 | `ERROR` | unrecoverable error, ждём manual intervention |
| 12 | `KILLED` | kill-switch активирован, всё остановлено |

**Переходы (28 каноничных):** см. `src/execution/state_machine.py::TRANSITIONS`
(table-driven). Запрещённые переходы → `IllegalTransitionError` + ERROR state.

**Rationale:** Harel-style explicit states + table-driven transitions =
property-test покрытие (все edge cases) + детерминированный recovery после
restart. Альтернатива (implicit FSM через if/else) не прошла S4 review-стандарт.

**Code refs:**
- `src/execution/state_machine.py` — `ExecutionState(StrEnum)`, `TRANSITIONS: dict[(State,Event), State]`, `apply(event) -> State`.
- `tests/unit/test_execution_fsm.py` — table-driven тест (28+ legal + N illegal).

### Sub-decision 3 — SQLite `execution_state` + reconcile-as-truth (warm start)

**Decision:** persistence FSM-state в SQLite таблицу `execution_state` (PK = `symbol`),
ОДНОВРЕМЕННО reconcile при каждом WS reconnect и startup. SQLite = warm-start
кеш (избегаем full reconcile на каждом restart), reconcile = source of truth
(если расходится — exchange wins, SQLite перезаписывается).

**Schema:**
```sql
CREATE TABLE execution_state (
    symbol TEXT PRIMARY KEY,
    state TEXT NOT NULL,         -- ExecutionState enum value
    position_qty TEXT NOT NULL,  -- Decimal as TEXT
    entry_price TEXT,            -- Decimal as TEXT, nullable for FLAT
    oco_main_order_id TEXT,      -- bracket main leg id, nullable
    updated_at TEXT NOT NULL     -- ISO-8601 UTC
);
```

**Rationale:**
- Warm start: восстановление за O(1) read, не O(N) replay event log.
- Safety net: если reconcile failed (exchange API down) — есть последний known state.
- Divergence handling: при mismatch → `HALT_RECONCILE_DIVERGENCE`, оператор разбирается.

**Trade-off vs event sourcing (S6):** дублирование с будущим event log. Решение:
S5 ставит SQLite-таблицу, S6 добавит event log параллельно, в S7+ возможно
заменим execution_state на projection из events. Не сейчас.

**Code refs:**
- `migrations/0003_execution_state.sql`
- `src/execution/state_repo.py::ExecutionStateRepo`
- `src/execution/reconciler.py::Reconciler.reconcile() -> ReconcileResult`.

### Sub-decision 4 — Новые reason codes (extends ADR 0018)

**Decision:** добавить в `src/risk/reason_codes.py::ReasonCode` enum:

- `HALT_RECONCILE_DIVERGENCE` — local FSM state разошёлся с exchange после reconcile.
- `EXIT_OCO_PARTIAL_TIMEOUT` — OCO partial fill висит > N сек, force-close оставшегося qty.

**Total enum:** 29 + 2 = **31 codes**. (Pre-S5 actual count was 29: 4 entry + 3 scale + 7 exit + 8 reject + 7 halt — earlier ADRs referenced 28 but actual enum had `SCALE_OUT_PARTIAL` already shipped in S4.)

**Rationale:** существующий `HALT_EXCHANGE_OUTAGE` семантически про связь, не про
divergence (биржа ответила, но факты разные). `EXIT_OCO_PARTIAL_TIMEOUT` отдельно
от `EXIT_TP_HIT`/`EXIT_SL_HIT` для audit (понимаем причину закрытия).

**Tests:** `tests/unit/test_reason_codes.py` дополняется проверкой обоих новых
кодов (включены в enum, нет коллизий, есть в `_RISK_TO_AUDIT_MAPPING` если
применимо).

**Doc:** [[../../trading/concepts/reason-codes]] обновляется в Stage E плана —
секция "Halt codes" + "Exit codes" + "Total: 30".

### Sub-decision 5 — Testnet integration scope: happy path в S5

**Decision:** integration-тест на Bybit testnet в S5 покрывает ОДИН сценарий:
**entry MARKET → OCO armed → SL hit → FLAT + audit log**.

Отложено в S5.5 (или S6, по плану):
- partial-fill сценарий (требует контролируемой liquidity ситуации)
- WS reconnect divergence сценарий (требует injected disconnect)

**Rationale:** testnet flaky (Bybit testnet периодически имеет downtime/lag).
Один сценарий = один интеграционный тест = одна точка обслуживания. Расширенные
сценарии живут в isolated test suite + опциональны в CI.

**Marker:** тест помечен `@pytest.mark.integration` + `@pytest.mark.testnet`,
default skip без `RUN_TESTNET=1` env (см. `tests/conftest.py`).

## Consequences

### Positive
- Явный контракт FSM → property-test покрывает все edge cases.
- Native OCO снимает race-condition риски.
- Reconcile-as-truth защищает от silent state drift после reconnect.
- Reason-code enum остаётся source of truth для audit (30 codes).

### Negative / Risks
- Нативный tpslMode = vendor lock на Bybit для bracket логики (миграция на другую
  биржу потребует переписывания `oco.py`). Принято: v0.1 = Bybit-only.
- `execution_state` таблица — потенциальное дублирование с S6 event log. План
  миграции (S7+) фиксируется в [[../architecture/migration-plan]].
- Testnet integration test может flaky'нуться — mitigated через retry-decorator
  + opt-in marker.

## Related

- Plan: [[../plans/2026-04-23-sprint-5-execution]]
- Migration: [[../architecture/migration-plan]] §S5
- Reason codes: [[../../trading/concepts/reason-codes]]
- Sprint page (after merge): [[../sprints/sprint-05-execution]]
- Touched components: [[../components/oco]] · [[../components/reconciler]] · [[../components/execution-state-machine]] · [[../components/bybit-adapter]] (extension)
