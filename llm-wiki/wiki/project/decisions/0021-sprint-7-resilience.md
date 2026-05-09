---
title: "0021. Sprint 7 — Resilience: bootstrap reconcile, WS-reconnect wiring, halt persistence"
type: decision
status: accepted
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0020-sprint-6-execution-spot-oco-emulation.md
  - wiki/project/components/oco.md
  - wiki/project/components/reconciler.md
  - wiki/project/components/execution-state-machine.md
tags: [execution, resilience, fsm, reconcile, ws-reconnect, halt, persistence, bybit-spot]
---

# 0021. Sprint 7 — Resilience: bootstrap reconcile, WS-reconnect wiring, halt persistence

**Status:** accepted
**Date:** 2026-04-24
**Supersedes:** — (extends [[0020-sprint-6-execution-spot-oco-emulation]])

## Контекст

S6 (ADR 0020) реализовал 3-order Spot OCO emulation: 16-state FSM, `Coordinator.start_bracket/arm_oco/on_order_event/flatten`, Reconciler R4 walletBalance truth, schema v2, 39 reason codes. Закрыт Phase F (Demo Mainnet probes B2+v3-D). Остались нерешёнными три interconnected gap'а, задокументированные в S6 review follow-ups:

1. **C1 — Coordinator startup reconcile**. `Coordinator.bootstrap()` существует (`coordinator.py:62-92`), но делает только `_extract_max_attempt` из `get_open_orders + get_order_history` (sub-decision 9 из ADR 0020). Не вызывает `self._reconciler.reconcile()` и не resolve'ит hung `ENTRY_PENDING` / `EXIT_PENDING`. После crash с position на бирже процесс стартует с locally-persisted `ENTRY_PENDING`, но не знает что entry фактически Filled → torbadge FSM.

2. **C2 — WS-reconnect wiring для ENTRY_PENDING / EXIT_PENDING**. FSM уже имеет `WS_RECONNECT` transitions из `OCO_ARMING`, `EXIT_SIBLING_CANCELLING`, `EXIT_SL_RESIDUAL` (state_machine.py:121-124), но `ENTRY_PENDING + WS_RECONNECT` и `EXIT_PENDING + WS_RECONNECT` — **отсутствуют**. Если WS падает в окне между `start_bracket` и `arm_oco` (ENTRY_PENDING) или между `flatten` и FLAT (EXIT_PENDING), FSM зависает в PENDING навсегда. Также отсутствует сам **trading WS consumer** — `marketdata/bybit/ws.py` подписывается только на `kline_stream`, `coordinator.on_order_event(evt)` никто не вызывает live.

3. **halt_reason / last_exit_reason persistence**. Зафиксированы только в `Reconciler.ReconcileVerdict.halt_reason: str | None` (in-memory, `reconciler.py:41`). Coordinator.py:302 явно: `"ExecutionStateRow has no halt_reason/last_exit_reason field."` Post-mortem любого HALT требует `grep structlog` — не SQL-query'я. Runbook `halt-recovery.md` полагается на ручное выставление halt_reason через logging, без audit trail на frequency / timeline.

S7 закрывает все три gap'а одним спринтом, с пре-мейннет acceptance gate (ADR 0020 sub-decision 12 probes на api-testnet) в конце.

**Сopeplement по scope:** trading-logic-reviewer (opus, design-phase review на brainstorm answers) флагнул 7 hidden invariants — в частности несовместимость текущих `RECONCILE_OK → OCO_ARMED` transition и бинарного `Reconciler.ReconcileResult.verdict` с HEAL-narrow posture. Каждый invariant либо резолвится одним из sub-decisions ниже, либо документируется в runbook как known limitation.

## Цели и не-цели

**Goals (S7 scope):**

- G1 — Bootstrap вызывает reconciler для всех persistable states; HEAL-narrow для unambiguous crash-in-window cases, HALT иначе.
- G2 — WS private stream consumer (`order` + `wallet` topics) wired в `Coordinator.on_order_event` + Reconciler.R4.
- G3 — `ENTRY_PENDING + WS_RECONNECT` и `EXIT_PENDING + WS_RECONNECT` transitions в FSM.
- G4 — Две новые reconcile verdicts: `HEAL_ENTRY_FILLED` и `RECONCILE_EXITED`, плюс соответствующие FSM events.
- G5 — Persistence halt_reason / last_exit_reason через миграцию `0005_*.sql` (4 column + 1 table).
- G6 — Acceptance gate Phase G: re-run B2, v3-D, v2-S2 на api-testnet.bybit.com с отдельными testnet keys.

**Non-goals (откладываем → S8+):**

- **Live trade driver loop** — binding Strategy → Risk → Coordinator для всех ~28 нон-WS_RECONNECT FSM events (ENTRY_PLACED/ENTRY_FILLED/OCO_PLACED/TP_HIT/SL_HIT/RISK_HALT etc. end-to-end от signal до order submission). Это **отдельная архитектурная подсистема** (async event loop, backpressure, graceful shutdown, retry semantics) → S8. S7 оставляет **пассивный WS consumer** (`BybitPrivateWSConsumer` — routes events в existing `coordinator.on_order_event` метод S6), но НЕ создаёт signal→order driver. Bot НЕ запускается end-to-end после S7; S7 закрывает FSM holes safely, S8 строит driver на чистой FSM. **Вариант B1** выбран — одна подсистема per спринт.
- Per-fill `execution` topic подписка (granular fees / VWAP) — `order` topic даёт aggregated cumExecFee, достаточно для v0.1.
- Multi-bracket concurrency (вторая позиция параллельно). Текущий FSM single-symbol single-bracket.
- Analytics post-mortem engine поверх halt_log. Table создаётся, отчёты — v0.2.
- Kill-switch external signal (SIGTERM → KILL_SWITCH). Present FSM handles KILL_SWITCH event, но внешний trigger — отдельный модуль.

## Суб-решения

### 1. Bootstrap делегирует reconcile для всех persisted states

**Что меняется:** `Coordinator.bootstrap()` теперь:

```
def bootstrap(self) -> None:
    row = self._repo.get(self._symbol)
    if row is None:
        return  # cold start, ничего resolve'ить
    # Startup-only step: recover last_attempt_num (ADR 0020 sub-decision 9)
    self._recover_attempt_num(row)
    # Reuse same reconcile path as WS-reconnect (sub-decision 4 below)
    self.on_ws_reconnect()
```

`_recover_attempt_num` — приватный хелпер, инкапсулирует текущее `_extract_max_attempt` поведение.

**Почему:** bootstrap = "WS first-connect at process start" семантически. Композиция минимизирует drift между двумя path'ами. Тесты `test_on_ws_reconnect_*` покрывают и bootstrap.

**Sequencing invariant:** `await coordinator.bootstrap()` ОБЯЗАН завершиться ДО запуска WS consumer'а ИЛИ signal worker'а. Нарушение → race: новый signal может вызвать `start_bracket` между reconcile-fetch и reconcile-action. Enforced в entry-point (`src/entrypoint.py` когда он появится) + документируется в docstring.

### 2. FSM: новые events и transitions

**Новые events (`ExecutionEvent`):**
- `RECONCILE_ENTRY_FILLED` — reconciler classified "entry order Filled + position matches expected + no orphan OCO"
- `RECONCILE_EXITED` — reconciler classified "position == 0 on exchange, no open orders" (exit completed during disconnect)

**Новые transitions:**

| From state | Event | To state | Reason |
|---|---|---|---|
| ENTRY_PENDING | WS_RECONNECT | RECONCILING | C2 gap fill |
| EXIT_PENDING | WS_RECONNECT | RECONCILING | C2 gap fill |
| RECONCILING | RECONCILE_ENTRY_FILLED | LONG_OPEN | HEAL-narrow path (затем арм_oco вызывается coordinator'ом из LONG_OPEN) |
| RECONCILING | RECONCILE_EXITED | FLAT | Clean fill-during-disconnect, нет logic error |

**Почему не используем existing `RECONCILE_OK → OCO_ARMED`:** этот transition полагался на pre-S7 assumption что reconcile вызывается только из OCO_ARMED-adjacent states. ENTRY_PENDING→OCO_ARMED бypass'ит LONG_OPEN и арм_oco не вызывается → OCO_ARMED без legs на бирже (logic error, flagged reviewer'ом invariant #1).

### 3. Reconciler: 4-valued verdict + expected_state hint

**Что меняется:** `ReconcileResult` (reconciler.py):

```python
@dataclass(frozen=True)
class ReconcileResult:
    verdict: Literal["AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED"]
    exch_qty: Decimal
    entry_price: Decimal | None
    halt_reason: str | None
    heal_context: dict | None  # populated на HEAL_ENTRY_FILLED: avgPrice, cumExecFee
```

`Reconciler.reconcile(local: LocalState, expected_state: ExecutionState | None = None)` — опциональный параметр `expected_state` позволяет caller сказать "я ожидаю ENTRY_PENDING"; reconciler тогда возвращает HEAL-ready verdict вместо слепого DIVERGENCE.

**Classification algorithm (по-шагово):**
```
1. Fetch exch_qty = walletBalance(base_coin) (WS cache или REST fallback)
2. Fetch open_orders = get_open_orders(symbol)
3. Fetch entry order status = get_order(entry_order_id)  # из row

if expected_state == ENTRY_PENDING:
    if entry_order.status == Filled and exch_qty >= expected_entry_qty - dust and len(open_orders) == 0:
        staleness = now_utc - row.updated_at
        if staleness.total_seconds() > settings.heal_max_age_seconds:  # default 3600
            return HALT("HALT_BOOTSTRAP_STALE")
        return HEAL_ENTRY_FILLED(exch_qty=..., entry_price=entry_order.avgPrice, heal_context=...)
    if entry_order.status in (Cancelled, Rejected) and exch_qty < dust:
        return EXITED  # revert to FLAT
    # Any other combination = ambiguous
    return HALT("HALT_BOOTSTRAP_AMBIGUOUS")

if expected_state == EXIT_PENDING:
    if exch_qty < dust and len(open_orders) == 0:
        return EXITED
    return HALT("HALT_EXIT_RECONCILE_DIVERGENCE")

# Other states (OCO_ARMING, EXIT_SIBLING_CANCELLING, EXIT_SL_RESIDUAL) use binary AGREE/DIVERGENCE
if exch_qty == local.position_qty:
    return AGREE
return HALT("HALT_RECONCILE_DIVERGENCE")
```

**HEAL precondition детализация:** ВСЕ три условия должны выполняться одновременно:
- `entry_order.status == "Filled"`
- `exch_qty >= expected_entry_qty - dust_threshold` (см. ADR 0020, dust = 1e-5 BTC)
- `len(open_orders_for_bracket) == 0` (никаких orphan TP/SL на бирже)

Если ТОЛЬКО entry Filled + position matches, но есть open orders — это значит crash в OCO_ARMING с partial arm, и тогда это **not narrow HEAL**, это handled existing `OCO_ARMING + WS_RECONNECT → RECONCILING` path (уже в FSM) с binary DIVERGENCE-или-AGREE verdict → HALT если anything off.

### 4. HEAL staleness threshold = 3600s (1 bar period)

**Decision:** `settings.heal_max_age_seconds = 3600` (default, configurable). Если `now - row.updated_at > heal_max_age_seconds` при expected_state=ENTRY_PENDING с HEAL precondition satisfied → HALT вместо HEAL.

**Почему не 60s (ARMING TTL parity):** ARMING TTL — про успех RPC, не про market freshness. Crash внутри 60s окна не repeat цена движения. Правильный reference = duration одного bar'а стратегии (v0.1 = 1H = 3600s). Crash < 1 bar → entry при том же ATR/SL/TP levels, которые были signal-time. Crash > 1 bar → структурные market changes, SL/TP могут быть absurd → manual review безопаснее.

**Почему не 30s:** слишком агрессивно. Нормальный restart занимает 10-20s (импорты, pybit handshake, DB open). 30s false-HALT'ит на каждом втором legitimate restart.

**Config:** `src/platform/config.py::Settings.heal_max_age_seconds: int = 3600`.

### 5. halt_reason persistence — γ (column + log)

**Schema (миграция 0005_halt_persistence.sql):**

```sql
-- ALTER existing table
ALTER TABLE execution_state ADD COLUMN halt_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_exit_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_reconcile_at TEXT;
ALTER TABLE execution_state ADD COLUMN bootstrap_at TEXT;

-- New audit table (append-only)
CREATE TABLE halt_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    ts          TEXT    NOT NULL,
    reason      TEXT    NOT NULL,
    context_json TEXT   NOT NULL
);
CREATE INDEX halt_log_symbol_ts ON halt_log(symbol, ts);
```

**Helper (`ExecutionStateRepo._set_halt(reason, context)`)** — идемпотентный:

```
def _set_halt(self, *, reason: str, context: dict) -> None:
    with self._conn:  # atomic
        row = self.get(symbol)
        is_first = row.halt_reason is None
        if is_first:
            self._conn.execute(
                "UPDATE execution_state SET halt_reason=?, ... WHERE symbol=?",
                (reason, symbol),
            )
        # Log always appends (audit trail даже secondary halts)
        self._conn.execute(
            "INSERT INTO halt_log (symbol, ts, reason, context_json) VALUES (?,?,?,?)",
            (symbol, now_iso(), reason, json.dumps(context)),
        )
```

**Idempotency rule:** если `halt_reason is not None` (уже halted) — секундарный halt event **не перезаписывает** column (primary reason wins), но **всегда append в log**. Это даёт chronological trail всех halt attempts (e.g., RISK_HALT fire через 100ms после BRACKET_TIMEOUT), сохраняя "root cause" в column.

**`context_json` required fields:**
- `state_at_halt` — FSM state immediately before transition to HALTED
- `position_qty` — local row.position_qty в момент halt
- `oco_tp_id`, `oco_sl_id` — чтобы runbook знал какие orderLinkId cancel'ить manually
- `expected_qty` — `expected_oco_qty` (dust/sizing debugging)
- `last_event` — ExecutionEvent.name что triggered transition в HALTED
- `last_attempt_num` — для runbook reconstruction orderLinkId pattern `oco-{bracket_id}-{role}-{N}`
- `arming_started_at` — для HALT_OCO_ARM_TIMEOUT post-mortem (clock drift vs real timeout)

### 6. WS private stream consumer: order + wallet topics

**Новый компонент:** `src/execution/bybit/ws_private.py::BybitPrivateWSConsumer`.

**Topics:** `order` + `wallet` (V5 private WS endpoint, testnet `wss://stream-testnet.bybit.com/v5/private`, demo `wss://stream-demo.bybit.com/v5/private`, mainnet `wss://stream.bybit.com/v5/private`).

**Routing:**
- `order` topic events → parse → dict with `orderLinkId`, `orderStatus`, `cumExecQty`, `cumExecFee`, `feeCurrency`, `avgPrice` → `coordinator.on_order_event(evt)`.
- `wallet` topic events → update `Reconciler._wallet_cache[coin] = walletBalance` → `reconciler.reconcile()` reads cache first, REST fallback при cache miss.

**Parser acceptance criterion:** WS parser ОБЯЗАН извлекать `cumExecFee` и `feeCurrency` для каждого Filled/PartiallyFilled события. Если field отсутствует (schema drift от Bybit) → структуролог ERROR + drop event (НЕ forward `coordinator.on_order_event` с None fees, это потеряет fee на PnL).

**Reconnect handling:**
- `BybitPrivateWSConsumer.on_disconnect` callback → `loop.call_soon_threadsafe(queue.put_nowait, {"type": "disconnect"})` → main async loop routes к `coordinator.on_ws_reconnect()` на следующем reconnect.
- pybit `WebSocket` сам делает auto-reconnect; мы только detect'им что он случился через heartbeat gap ИЛИ через явный disconnect callback.

**Paranoia try/except:** consumer loop обёрнут в `try/except Exception as e: structlog.error(...); trigger_reconnect()`. Acceptance criterion task spec'а: **consumer loop не propagate any exception в entry-point**.

### 7. Startup sequencing invariant

**Rule:**
```
1. Process start
2. coordinator.bootstrap() — SYNCHRONOUS или awaited, blocks entry-point
3. bootstrap() calls on_ws_reconnect() internally → reconcile + FSM transitions
4. bootstrap() returns
5. Start WS consumer (private stream)
6. Start signal worker / kline consumer
```

Нарушение порядка → race: new signal → start_bracket → write ENTRY_PENDING → bootstrap reads row → sees new entry + no position on exchange → classifies как DIVERGENCE → HALT legitimate fresh order.

**Enforcement:** entry-point (`src/entrypoint.py` когда будет) будет иметь явное:
```python
await coordinator.bootstrap()
ws_consumer_task = asyncio.create_task(ws_consumer.run())
signal_worker_task = asyncio.create_task(signal_worker.run())
```

Если порядок нарушен (старт workers до bootstrap complete) → runtime assert `assert coordinator._bootstrap_done, "bootstrap must complete first"` в `start_bracket` и `on_order_event`.

### 8. Acceptance gate — Phase G (Demo Mainnet)

**Scope:** re-run B2, v3-D, v2-S2 probes per pre-merge acceptance gate. Smoke test критических Bybit findings:

- B2: `place_order(category=spot, tpslMode=Full) → retCode=170130` (native OCO impossible)
- v3-D: Stop order `timeInForce=GTC` → echo shows `IOC` (silent override)
- v2-S2: `marketUnit=quoteCoin` → cumExecQty с 16 decimal places (banned at adapter)

**Scripts:** `scripts/spot_oco_probe_testnet.py` (S6). Manual run с keys в env.

**Revised target — Demo Mainnet (2026-04-24 decision):**

Initial scope требовал `api-testnet.bybit.com` с отдельной testnet credential pair. **Re-scoped:** v0.1 ops target = Demo Mainnet (`api-demo.bybit.com`), не testnet. Demo Mainnet uses real Bybit production matching engine (только money fake) — это релевантнее для v0.1 чем testnet (отдельный движок с разными API quirks).

**Phase G evidence (executed 2026-04-24 by operator):**

| Probe | Endpoint | Result |
|---|---|---|
| B2 | api-demo.bybit.com | ✅ `InvalidRequestError ErrCode=170130` on `tpslMode=Full` (`spot_oco_probe_output.json` B2_native_tpsl_attempt) |
| v3-D | api-demo.bybit.com | ✅ TIF sequence `[IOC, IOC, IOC]` after submit `GTC` (silent override; `spot_oco_probe_v3_output.json` v3AD_tif_sequence) |
| v2-S2 | api-demo.bybit.com (S6 evidence) | ✅ Drift confirmed in S6 `spot_oco_probe_v2_output.json`; testnet attempt 2026-04-24 returned 401/10003 (separate keys not provisioned). **Adapter unconditionally pins `marketUnit=baseCoin`** (см. `bybit-adapter.md` §Banned Spot fields), exchange-side property already validated on Demo. |

**Блокирующий статус (closed):**
- S7 PR merge → **разблокирован** 2026-04-24 после Demo Mainnet evidence.
- Tag `v0.1.0-alpha.7` valid for **Demo Mainnet ops only**. Mainnet promotion (v0.2+) requires fresh acceptance gate включая testnet или mainnet smoke с small size.
- Mainnet config change (env = MAINNET) → enforced via `settings.require_mainnet_gate_passed: bool = True` startup validator (will FAIL until v0.2 gate passes).

**Divergence handling:** если future probe возвращает retCode отличный от Demo findings → STOP merge, escalate новый ADR, revisit ADR 0020 sub-decision 12.

### 9. Schema migration 0005 — единый файл

**Всё в одной forward-only миграции:** `migrations/0005_halt_persistence.sql`.

```sql
-- Migration 0005: halt persistence + reconcile timestamps + audit log
-- ADR 0021 sub-decisions 5, 7 (bootstrap_at для distinguishing cold start vs WS reconnect)

ALTER TABLE execution_state ADD COLUMN halt_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_exit_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_reconcile_at TEXT;
ALTER TABLE execution_state ADD COLUMN bootstrap_at TEXT;

CREATE TABLE halt_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    ts          TEXT    NOT NULL,
    reason      TEXT    NOT NULL,
    context_json TEXT   NOT NULL
);
CREATE INDEX halt_log_symbol_ts ON halt_log(symbol, ts);
```

`ExecutionStateRow` dataclass → +4 поля: `halt_reason: str | None`, `last_exit_reason: str | None`, `last_reconcile_at: str | None`, `bootstrap_at: str | None`.

**Backward compat:** существующие queries (`get`, `upsert`) делают `SELECT *` — новые columns просто возвращаются None для pre-S7 rows.

**Не добавляем в migration 0005:**
- `last_signal_at`, `last_bar_at` — computable из signal worker logs, не нужны в hot table.
- `bracket_start_at` — уже `arming_started_at` существует для OCO_ARMING; entry start = `updated_at` на `ENTRY_PLACED` transition.

## Коды причин (delta)

**Нет новых кодов.** S7 использует existing S6 set (39 codes):
- HALT_BOOTSTRAP_AMBIGUOUS (already в enum) — ambiguous classification на bootstrap/reconcile.
- HALT_RECONCILE_DIVERGENCE (already) — position qty mismatch.
- EXIT_TP_FILLED / EXIT_SL_TRIGGERED / EXIT_SL_PARTIAL_RESIDUAL (already) — clean exit paths.

**Potential новый (reviewed, rejected):** `HALT_BOOTSTRAP_STALE` (crash > heal_max_age_seconds). Решение: reuse `HALT_BOOTSTRAP_AMBIGUOUS` с `context_json.sub_reason = "stale_age"`. Один новый enum = один новый test, ADR, doc — overhead не оправдан.

## Последствия

**Что меняется в code:**
- `src/execution/state_machine.py` — +2 events, +4 transitions.
- `src/execution/coordinator.py` — `bootstrap()` expanded, `on_ws_reconnect()` NEW, `_set_halt()` callsites at все HALTED transitions.
- `src/execution/reconciler.py` — `ReconcileResult` 4-valued, `reconcile(local, expected_state=None)`, `_wallet_cache` для WS-fed R4.
- `src/execution/state_repo.py` — 4 new dataclass fields + `_set_halt()` helper.
- `src/execution/bybit/ws_private.py` — NEW module (order + wallet topics).
- `src/platform/config.py` — `heal_max_age_seconds: int = 3600`, `require_mainnet_gate_passed: bool = True`.
- `migrations/0005_halt_persistence.sql` — NEW.

**Тесты:**
- `tests/unit/test_state_machine_s7.py` — new events/transitions.
- `tests/unit/test_reconciler_verdicts.py` — 4-valued matrix.
- `tests/unit/test_coordinator_bootstrap_reconcile.py` — HEAL vs HALT branches.
- `tests/unit/test_coordinator_on_ws_reconnect.py` — ENTRY_PENDING / EXIT_PENDING / OCO_ARMING paths.
- `tests/unit/test_halt_persistence.py` — _set_halt idempotency + log append.
- `tests/unit/test_ws_private_consumer.py` — parser accepts cumExecFee, dispatch routing, reconnect callback.
- `tests/property/test_bootstrap_ws_reconnect_idempotent.py` — Hypothesis: повторные reconnect'ы не ломают FSM.
- `tests/integration/test_bootstrap_demo.py` (opt-in RUN_DEMO=1) — реальный crash-restart cycle на Demo.

**Wiki updates:**
- `components/execution-state-machine.md` — "Known limitations" update (S6 defer → S7 closed), new transitions table.
- `components/reconciler.md` — 4-valued verdict, expected_state hint, wallet_cache.
- `components/oco.md` — mention bootstrap reconcile в happy/crash paths.
- `components/bybit-adapter.md` — cross-ref к ws_private consumer.
- NEW: `components/ws-private-consumer.md` — separate page для trading WS.
- NEW: `runbooks/halt-recovery.md` обновить "Why HALTED?" section с SQL queries к halt_log.

**ADR cross-ref:** 0020 (S6 OCO) supersessed in narrow sense только для sub-decision 9 bootstrap scope; core S6 decisions unchanged.

**Breaking changes:** none. Pre-S7 DB rows получают NULL в новых columns (no-op). ReconcileResult signature change — internal, не public API.

## Рассмотренные альтернативы

**Alt-1: HALT-always посture** (reject HEAL entirely). Safer, runbook-driven. Reject: каждый normal restart → HALT → manual unhalt — operationally unsustainable для даже v0.1 low-frequency trading.

**Alt-2: separate path for bootstrap и on_ws_reconnect** (no composition). Reject: drift risk. Два места где описывается HEAL vs HALT classification — инvariant violations через 2-3 спринта.

**Alt-3: per-fill `execution` topic WS subscription** включить в S7. Reject: YAGNI для v0.1 — Market entry = atomic single fill on Spot; IOC SL partials уже получают cumExecQty через `order` topic; fee granularity v0.2 concern (Analytics).

**Alt-4: halt_log только в structlog (без SQL table)**. Reject: невозможно SQL-query'ть "halt frequency last 24h" — для halt-recovery runbook это первый вопрос post-mortem'а.

**Alt-5: split S7 на S7 (C1+C2) + S7.5 (halt persistence + gate)**. Reject: взаимосвязанные изменения. halt_reason persist нужен на момент когда bootstrap классифицирует DIVERGENCE → HALT (sub-decision 5 вызывается изнутри sub-decision 1 flow). Разделение → double schema migration cost.

## Открытые вопросы → отложено на S8+

- External kill-switch signal (SIGTERM, lint process, risk-dashboard override) → emit KILL_SWITCH event. S8 when manager.py orchestration exists.
- `execution` topic subscription + per-fill Analytics table — S8 (Analytics sprint).
- Multi-symbol / multi-bracket concurrency — FSM currently single-symbol. S9+.
- HALT_BOOTSTRAP_STALE как отдельный enum code (decision: no, reuse HALT_BOOTSTRAP_AMBIGUOUS).

## Чеклист верификации (перед merge)

- [ ] Все 4 new FSM transitions имеют unit tests (positive + illegal).
- [ ] `Reconciler.reconcile` matrix test покрывает 4 verdicts × 3 expected_state hints.
- [ ] `Coordinator.bootstrap` тест: cold start (row=None), warm HEAL, warm HALT, warm AGREE.
- [ ] `Coordinator.on_ws_reconnect` тест: ENTRY_PENDING, EXIT_PENDING, OCO_ARMING, EXIT_SIBLING_CANCELLING, EXIT_SL_RESIDUAL.
- [ ] `_set_halt` idempotency test: secondary halt не перезаписывает column, log получает обе записи.
- [ ] WS parser test: cumExecFee присутствует → forward; отсутствует → drop + ERROR log (not crash).
- [ ] Startup sequencing assert fires если workers стартуют до bootstrap complete.
- [ ] Property test Hypothesis: 10k reconnect sequences не ломают FSM.
- [x] Phase G Demo Mainnet probe run 2026-04-24: B2 (170130), v3-D (TIF=IOC), v2-S2 (S6 Demo evidence + adapter pin baseCoin). Testnet re-verification deferred to v0.2 mainnet promotion gate.
- [ ] Wiki pages updated (3 existing + 1 new + runbook).
- [ ] `~/.claude/agents/trading-logic-reviewer.md` synced (если новые invariants → mention в prompt).

---

**Approved:** pending user review.
**Implementation plan:** [[../plans/2026-04-24-sprint-7-resilience]].
**Sprint page:** [[../sprints/sprint-07-resilience]] — delivery record (33+ commits, 16/29/59 FSM, reason codes 39→42).

**Затронутые компоненты:**
- [[../components/reconciler]] — 4-valued verdict (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED)
- [[../components/coordinator]] — bootstrap + WS_RECONNECT path + halt persistence (γ primary-wins)
- [[../components/execution-state-machine]] — transitions 59→74 (S7 reconcile/timeout events)
- [[../components/ws-private-consumer]] — close-hook + check_alive heartbeat watchdog
