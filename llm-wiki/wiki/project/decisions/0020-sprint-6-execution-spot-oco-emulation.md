---
title: 0020. Sprint 6 — Bybit Spot V5 OCO emulation (reverses ADR 0019 sub-decision 1)
type: decision
tags: [adr, sprint-6, execution, oco, fsm, reconciler, bybit-spot]
created: 2026-04-23
updated: 2026-04-23
status: accepted
---

# 0020. Sprint 6 — Bybit Spot V5 OCO emulation

**Status:** accepted
**Date:** 2026-04-23
**Sprint:** S6
**Supersedes:** [[0019-sprint-5-execution-decisions]] sub-decision 1 (native `tpslMode=Full`)
**Amends:** [[0019-sprint-5-execution-decisions]] sub-decisions 2 (FSM extends 12→21), 3 (schema migration 0004), 4 (reason codes 31→39)
**Related:** [[../architecture/migration-plan]] §S6, [[../components/oco]], [[../components/reconciler]], [[../components/execution-state-machine]], [[../components/bybit-adapter]]

## Контекст

Перед стартом S6 эмпирически проверены 14 предположений (B1-B5 + G1-G14) на Bybit Demo
trading (`api-demo.bybit.com`, virtual money, mainnet matching engine). Три probe скрипта
(`scripts/spot_oco_probe.py`, `_v2.py`, `_v3.py`) с реальными WebSocket private streams
(execution + order + wallet) подтвердили или опровергли каждое.

**Главное опровержение:** ADR 0019 sub-decision 1 (native `tpslMode=Full` в одном
`place_order`) **не работает на Spot V5**. Воспроизведение в probe v1 (line 20):

```text
ErrCode 170130 "Data sent for paramter '' is not valid"
POST /v5/order/create category=spot orderType=Market takeProfit=... stopLoss=... tpslMode=Full
```

Поля `tpslMode/takeProfit/stopLoss/tpOrderType/slOrderType` валидны для linear/inverse,
но Spot Market их отклоняет. Это перечёркивает основу OCO архитектуры S5.

S6 предоставляет полную замену: 3-order emulated bracket с client-side sibling-cancel,
расширенным FSM (21 состояние), новой schema-миграцией, новыми reason codes.

## Sub-decisions

### Sub-decision 1 — OCO эмуляция через 3 раздельных ордера

**Decision:** заменить native `tpslMode=Full` тремя последовательными ордерами:

1. **Entry** — `place_order(category=spot, orderType=Market, marketUnit=baseCoin, qty=Q, orderLinkId=oco-{bid}-entry-{n})`
2. **TP leg** — после Filled события: `place_order(orderType=Limit, side=Sell, qty=oco_qty, price=tp_price, timeInForce=GTC, orderLinkId=oco-{bid}-tp-{n})`
3. **SL leg** — затем: `place_order(orderType=Market, orderFilter=StopOrder, side=Sell, qty=oco_qty, triggerPrice=sl_price, orderLinkId=oco-{bid}-sl-{n})`

`bid` = UUIDv4 bracket id (см. sub-decision 2). `n` = attempt number (sub-decision 9).

**Empirical evidence:**
- B2 = FALSE (probe v1: ErrCode 170130 на native tpslMode)
- B3 = TRUE (probe v1: оба leg видны в `get_open_orders` default)
- v3-A: Stop trigger sequence `[Untriggered, Triggered, Filled]` подтверждён — `Triggered` event существует на Spot

**Trade-off:** теряем native cancel-on-fill — реализуем client-side (sub-decision 3).
Rate limit нагрузка ×3 (но v0.1 single-symbol, ≤ 2 brackets/сутки → не критично).

### Sub-decision 2 — Bracket correlation ID + schema v2

**Decision:** каждый bracket получает UUIDv4 `bracket_id`, который пропагируется как prefix
во все три `orderLinkId` (`oco-{bracket_id}-{role}-{attempt}`). Schema-миграция
`migrations/0004_execution_state_v2.sql` (forward-only ALTER ADD COLUMN):

```sql
ALTER TABLE execution_state ADD COLUMN bracket_id TEXT;
ALTER TABLE execution_state ADD COLUMN oco_tp_order_id TEXT;
ALTER TABLE execution_state ADD COLUMN oco_sl_order_id TEXT;
ALTER TABLE execution_state ADD COLUMN expected_oco_qty TEXT;
ALTER TABLE execution_state ADD COLUMN arming_started_at TEXT;
ALTER TABLE execution_state ADD COLUMN last_attempt_num INTEGER NOT NULL DEFAULT 1;
-- oco_main_order_id оставляем nullable для backward compat; код пишет NULL.
```

`oco_main_order_id` сохраняется в схеме (backward-compat), но новый код пишет NULL и
читает только три новых поля. Coordinator._persist (sub-decision 8) переписывается под
lookup по `stopOrderType` (`""` = TP Limit, `"Stop"` = SL StopOrder), а не по индексу
списка.

### Sub-decision 3 — Client-side sibling cancel-on-Triggered (race-aware)

**Decision:** Coordinator слушает order stream; при `orderStatus=Triggered` для SL leg
отправляет `cancel_order` для TP leg. При `orderStatus=Filled` для TP leg отправляет
`cancel_order` для SL leg.

**Race window:** probe v3-A показал, что Triggered и Filled приходят в **одну и ту же
миллисекунду** (`11:45:24.953` для обоих). Cancel почти наверняка прибудет на биржу
после фактического fill — это нормально:

- Cancel orderId, который уже Filled → ErrCode 110001 ("order not exists or finished") —
  **классифицируется non-fatal** (`map_error → REJECT_ORDER_ALREADY_TERMINAL`,
  audit-mapping = info, не halt).
- Race-free логика: cancel-on-`Triggered` гарантирует попытку, не доставку до fill.

**Empirical evidence:** v3-A status sequence `[Untriggered, Triggered, Filled]` доказал
существование промежуточного `Triggered` события на Spot.

### Sub-decision 4 — IOC override на Spot Stop + residual flatten

**Decision:** Bybit V5 Spot Stop **молча перезаписывает submitted `timeInForce` на IOC**.
Probe v3-D: отправили `timeInForce=GTC`, все три события (Untriggered/Triggered/Filled)
показали `IOC`. Это поведение биржи, не SDK.

Следствие: при триггере SL спавнится IOC Market Sell. На flash crash с тонким стаканом
IOC может частично зафиллиться, оставив **residual position naked**. Defense:

- При `orderStatus=PartiallyFilled` для SL → новое FSM состояние `EXIT_SL_RESIDUAL`.
- Coordinator немедленно отправляет дополнительный `Market Sell` на
  `cumExecQty(prev) - cumExecQty(curr)` до полного flat.
- Reason code `EXIT_STOP_RESIDUAL_FLATTEN` для audit (sub-decision 7).

### Sub-decision 5 — Position truth = `walletBalance(coin=BTC)` + entry_price local-only

**Decision:** Spot **не имеет position-объекта** (`get_position(category=spot)` n/a).
Reconciler использует `get_wallet_balance(accountType=UNIFIED, coin=BTC)`, поле
`walletBalance` (НЕ `availableToWithdraw`/`availableBalance`/`equity`):

- `walletBalance` — total BTC включая held в open Sell orders (правильно для current position size)
- `availableToWithdraw` приходит как **пустая строка `""`** (probe v2 line 805) — Reconciler treats `""` as None
- `locked` — BTC reserved в open Sells (для free = walletBalance - locked, информативно)

**Precondition:** bot-owned wallet, no external BTC. Startup-check предупреждает если
`walletBalance > expected_position + dust_threshold (5e-7 BTC)`.

**entry_price split:** `walletBalance` НЕ содержит `avgPrice`. Coordinator._persist
получает `position_qty` от Reconciler, а `entry_price` — из локального SQLite (записан
при entry Filled событии). Cold-start без SQLite строки → `entry_price=None`,
accepted-stale, audit пишет "entry_price unknown after restart" один раз.

### Sub-decision 6 — Fee-aware OCO qty sizing (G5)

**Decision:** при entry с `feeCurrency=BTC` (Spot Buy: 0.1% taker, fee из base coin) реальный
БТЦ-баланс **меньше ordered qty на сумму fee**. Sell на ordered qty проваливается с
ErrCode 170131 "Insufficient balance".

**Формула:**
```python
oco_qty = step_floor(cumExecQty - cumExecFee) if feeCurrency == base_coin else step_floor(cumExecQty)
```

**Empirical evidence (probe v3-B, clean wallet):**
- Entry: ordered=0.000644, cumExecQty=0.000644, cumExecFee=0.000000644 BTC
- Wallet после entry: 0.00064387 (math: dust + qty - fee)
- Sell at exact cumExecQty (0.000644) → **ErrCode 170131** ✅
- Sell at step_floor(cumExecQty - cumExecFee) = 0.000643 → **rc=0** ✅

Adapter ждёт `cumExecQty` из order stream `Filled` события (НЕ из REST place response,
который возвращает 0). Sell-side fees приходят в USDT (`feeCurrency=USDT`), BTC qty не
изменяется → формула falls through к `step_floor(cumExecQty)`.

### Sub-decision 7 — Reason code enum delta (31 → 39 codes)

**Decision:** добавить 8 новых reason codes в `src/risk/reason_codes.py::ReasonCode`:

| Code | Trigger | FSM transition |
|------|---------|----------------|
| `HALT_BRACKET_INCOMPLETE` | TP placed, SL place failed → flatten | OCO_ARMING → EXIT_PENDING → HALTED |
| `HALT_OCO_ARM_TIMEOUT` | bracket build > 10s от ENTRY_FILLED | OCO_ARMING → HALTED |
| `HALT_OCO_SIBLING_STUCK` | sibling cancel retries exhausted | EXIT_SIBLING_CANCEL_FAILED → HALTED |
| `HALT_PARTIAL_FILL_BELOW_MIN` | post-partial qty * tp_price < $5 min notional | OCO_ARMING → EXIT_PENDING → HALTED |
| `HALT_FLATTEN_FAILED` | emergency Market Sell failed twice | EXIT_PENDING → HALTED (terminal) |
| `HALT_PHANTOM_SL` | post-place SL verification mismatch | OCO_ARMING → EXIT_PENDING → HALTED |
| `EXIT_STOP_RESIDUAL_FLATTEN` | IOC SL partial → forced flatten | EXIT_SL_RESIDUAL → FLAT |
| `REJECT_ORDER_ALREADY_TERMINAL` | cancel of already-Filled (110001) | non-state, audit-info |

**Total:** 31 + 8 = **39 codes**. Tests `tests/unit/test_reason_codes.py` дополняются
проверкой каждого нового (member, semantic, `_RISK_TO_AUDIT_MAPPING`).

### Sub-decision 8 — FSM v2 (12 → 21 состояний)

**Decision:** добавить 9 новых состояний к существующим 12:

| State | Meaning | Predecessor → Successor |
|-------|---------|-------------------------|
| `OCO_ARMING` | TP placed, SL pending OR SL placed, awaiting both Untriggered ack | LONG_OPEN → OCO_ARMED OR HALTED |
| `EXIT_SIBLING_CANCELLING` | sibling cancel in flight after one leg filled/triggered | OCO_ARMED → FLAT OR EXIT_SIBLING_CANCEL_FAILED |
| `EXIT_SIBLING_CANCEL_FAILED` | sibling cancel returned retryable error; periodic retry | EXIT_SIBLING_CANCELLING → FLAT OR HALTED |
| `EXIT_SL_RESIDUAL` | IOC SL partial fill, residual qty needs flatten | OCO_ARMED → FLAT OR HALTED |
| `HALT_BRACKET_INCOMPLETE` | terminal subset of HALTED (sub-decision 7) | OCO_ARMING → HALTED |
| `HALT_OCO_ARM_TIMEOUT` | terminal subset of HALTED | OCO_ARMING → HALTED |
| `HALT_OCO_SIBLING_STUCK` | terminal subset of HALTED | EXIT_SIBLING_CANCEL_FAILED → HALTED |
| `HALT_PARTIAL_FILL_BELOW_MIN` | terminal subset of HALTED | OCO_ARMING → HALTED |
| `HALT_FLATTEN_FAILED` | terminal subset of HALTED, manual-only | EXIT_PENDING → HALTED |

**Note:** HALT_* states выше — концептуальные subsets `HALTED` для FSM completeness.
В коде `ExecutionState` enum они представлены как `HALTED` плюс `halt_reason: ReasonCode`
(не множим enum). Транзиции и invariants — те же.

**Transition delta:** ~22 новых transitions добавляется в
`src/execution/state_machine.py::TRANSITIONS`. Полная таблица — в plan документе
[[../plans/2026-04-23-sprint-6-spot-oco-emulation]].

### Sub-decision 9 — Idempotent retry с deterministic orderLinkId

**Decision:** orderLinkId формируется детерминистически:
`oco-{bracket_id}-{role}-{attempt_num}`, где `role ∈ {entry, tp, sl, flatten}`,
`attempt_num` начинается с 1, инкрементируется на retry.

Adapter retries при network errors (timeout, 5xx, 429) **с тем же orderLinkId**.

**Recovery от repo crash между attempt и persist:**
- Перед placement attempt N (N≥2) Coordinator вызывает `get_open_orders(symbol)` AND
  `get_order_history(orderLinkId=oco-{bid}-{role}-*)` — детектирует артефакты прошлых attempts.
- Если найдено → adopt the prior orderId, persist, no new place. Это закрывает race
  "сеть OK, repo crash → бот думает 'надо retry' → дубликат на бирже".

`last_attempt_num` колонка в schema v2 хранит последний попытанный N для idempotency
guard. На 110001 ("orderLinkId already exists") → call `get_order` для извлечения orderId
и treat как success-of-idempotent-retry.

### Sub-decision 10 — Atomicity + flatten cascade

**Decision:** при failure SL placement (после успешного entry + TP) Coordinator:

1. Cancel TP (`cancel_order(orderId=tp_oid)`).
2. Emergency Market Sell на `step_floor(walletBalance - locked)`.
3. Если retCode != 0 → retry один раз с `qty -= step` (один tick меньше для dust race).
4. Если второй attempt fails → state = HALTED + `HALT_FLATTEN_FAILED`, ALERT operator
   (Telegram per Sprint 7 — пока stdout WARN), TP уже отменён, позиция naked, manual-only.

`OCO_ARMING` имеет TTL = 60 секунд (`arming_started_at` колонка).
Reconciler на startup/reconnect: если строка в OCO_ARMING + `now - arming_started_at >
60s` → state = HALTED + `HALT_OCO_ARM_TIMEOUT` (прежний G13 → теперь sub-decision 7).
Если `< 60s` + position + ровно один leg в open_orders → resume bracket build (place
missing leg). Если два leg → state = OCO_ARMED.

### Sub-decision 11 — Adapter API surface (banned + new)

**Decision:** `BybitMarketAdapter` API:

**Удалить (dead code, регрессия):**
- `place_market_order(take_profit=, stop_loss=, tpsl_mode=)` keyword args (ADR 0019
  sub-decision 1 dead path). Если параметры переданы → `ValueError("Spot does not
  support native tpslMode; use 3-order OCO")`.

**Banned payload поля для category=spot (raise ValueError):**
- `tpslMode`, `takeProfit`, `stopLoss`, `tpOrderType`, `slOrderType`, `triggerDirection`
  (probe доказал silent-ignore для Spot — лучше не отправлять)

**Новые методы:**
- `place_limit_order(symbol, side, qty, price, time_in_force, order_link_id) -> PlaceResult`
- `place_stop_market_order(symbol, side, qty, trigger_price, order_link_id) -> PlaceResult`
- `cancel_order(symbol, order_id, order_filter=None) -> CancelResult`
- `cancel_all_orders(symbol, order_filter=None) -> CancelResult`
- `get_order(symbol, order_id) -> OrderSnapshot`
- `get_wallet_balance(coin) -> WalletSnapshot`

**Banned `marketUnit` для v0.1:** `quoteCoin` запрещён на adapter уровне (raise
ValueError). Probe v2 показал, что quoteCoin entry возвращает cumExecQty с 16 десятичными
знаками ниже step boundary (`0.000645745377431715` vs step `0.000001`) — landmine
для последующего step-floor sizing. baseCoin only.

### Sub-decision 12 — Sprint 6 acceptance criteria

**Decision:** Sprint 6 считается готовым к merge только при:

1. Unit tests: новые FSM transitions (≥22), reason codes (≥8), formula G5, OCO_ARMING TTL,
   idempotency retry — все RED→GREEN.
2. Property tests: bracket lifecycle invariants (entry → OCO_ARMED → exit terminal в FLAT
   ИЛИ HALTED, никогда orphan state).
3. Integration test (Demo, opt-in `RUN_DEMO=1`): один happy-path сценарий entry → OCO
   armed → cancel both legs → flatten → FLAT.
4. **Pre-mainnet acceptance (выполнить отдельно перед mainnet deploy):**
   - Re-run probe v1 (B2 native tpslMode rejection) на api-testnet с testnet keys
   - Re-run probe v3-D (Stop GTC→IOC override) на testnet
   - Re-run probe v2 S2 (quoteCoin 16-dp cumExecQty) на testnet
   - **Если ANY of these behaves differently → BLOCK mainnet, revisit ADR**

### Sub-decision 13 — Open empirical gaps

**Decision:** ниже принимаются как осознанные риски с mitigation:

| Gap | Status | Mitigation |
|-----|--------|------------|
| G14 testnet env diff | accept Demo proxy | sub-decision 12 pre-mainnet checks |
| WS `wallet` topic shape | проверен (probe v3-C: 5 events, shape `data[0].coin[]`) | adopted в Sprint 7+ для event-driven reconcile; v0.1 = REST poll |
| v3-E phantom SL get_open_orders filter | pybit `orderId` filter не сработал в probe | adapter sanity-assertion (`sl_trigger < entry - tick`) + post-place GET по orderLinkId |
| Stop trigger event sequence на flash-crash thin book | not stress-tested | sub-decision 4 EXIT_SL_RESIDUAL обрабатывает |

## Последствия

### Положительные
- ADR 0019 sub-decision 1 dead path удалён → больше нет hidden regression vector.
- 14/14 предположений эмпирически проверены или явно accepted с mitigation.
- FSM v2 покрывает реальные failure modes (orphan TP, IOC residual, repo-crash idempotency,
  phantom SL).
- G5 формула эмпирически доказана на clean wallet (170131 reproduced + safe qty success).

### Отрицательные / Риски
- **Vendor lock-in deeper:** все 9 новых FSM состояний и flatten cascade специфичны для
  Bybit Spot V5. Миграция на другую биржу = переписывание FSM.
- **Code complexity ×2:** 12 → 21 states, 28 → 50+ transitions, 6 → 14 adapter methods.
  Sprint 6 plan = ~30 tasks вместо изначальных ~12.
- **Race на cancel-of-Filled (110001) будет частой** в production (probe v3-A: 0ms gap).
  Audit log будет шумнее — фильтр `REJECT_ORDER_ALREADY_TERMINAL` в monitoring.
- **Naked-position window** при HALT_FLATTEN_FAILED requires manual ops procedure.
  Документируется в [[../runbooks/halt-recovery]] (создаётся в S6 Stage E).

### Обновления wiki (Stage E plan)
- [[../components/oco]] — переписать full (3-order pattern, не tpslMode)
- [[../components/reconciler]] — wallet truth + entry_price split
- [[../components/execution-state-machine]] — FSM v2 table
- [[../components/bybit-adapter]] — new method list, banned fields
- [[../../trading/concepts/reason-codes]] — 39 codes total
- [[../runbooks/halt-recovery]] — NEW: manual flatten procedure
- [[../sprints/sprint-06-spot-oco-emulation]] — после merge

## Реестр эмпирических данных

Все probe outputs commit'нуты:
- `scripts/spot_oco_probe.py` + `scripts/spot_oco_probe_output.json` (B1-B5 + observations 1-8)
- `scripts/spot_oco_probe_v2.py` + `scripts/spot_oco_probe_v2_output.json` (G5/G7/G14 + S2/S5)
- `scripts/spot_oco_probe_v3.py` + `scripts/spot_oco_probe_v3_output.json` (v3-A/B/C/D/E)

Каждый JSON содержит полные REST responses + WS event captures с timestamps. Для аудита
будущих регрессий: при изменении API behavior на Bybit стороне — re-run probes, diff JSONs.

## Связанные документы

- Plan: [[../plans/2026-04-23-sprint-6-spot-oco-emulation]]
- Migration: [[../architecture/migration-plan]] §S6
- Reason codes: [[../../trading/concepts/reason-codes]]
- Sprint page (after merge): [[../sprints/sprint-06-spot-oco-emulation]]
- Touched components: [[../components/oco]] · [[../components/reconciler]] · [[../components/execution-state-machine]] · [[../components/bybit-adapter]]
- Reviews: trading-logic-reviewer (sonnet, 2 rounds, BLOCK→PROCEED-after-v3)
