---
title: Halt Recovery Runbook
type: runbook
tags: [operations, halt, recovery, sprint-6, sprint-7, sprint-8a, sprint-8b, sprint-8c]
created: 2026-04-23
updated: 2026-04-25
status: stable
sources:
  - project/decisions/0013-circuit-breakers-l1-l2-l3-flash
  - project/decisions/0020-sprint-6-execution-spot-oco-emulation
  - project/decisions/0021-sprint-7-resilience
  - project/decisions/0022-sprint-8a-live-runtime
  - project/decisions/0023-halt-code-fsm-event-mapping
  - project/components/circuit-breakers
  - project/components/coordinator
  - project/components/oco
  - project/components/reconciler
  - project/components/runtime-manager
  - project/components/risk-override
---

# Halt Recovery Runbook

Operator manual для production halt recovery в AI Trading Bot v0.1. 19 halt codes (per `src/risk/reason_codes.py`) classified по 5 class groups + 2 severity tiers.

## CRITICAL definition (locked criterion)

> **CRITICAL halt** = halt где incorrect manual recovery can create or conceal an open position.

Per trader-expert ROUND 2 BINDING verdict (S8c PR-γ F1 brainstorm). New halt code authors apply this criterion mechanically для severity tier assignment.

- **CRITICAL** = full diagnosis (SQL queries + REST cross-check + state inspection + recovery procedure + escalation).
- **RECOVERABLE** = abbreviated (symptoms + actions + escalation only).

> **Operator safety:** ALWAYS stop bot (`python -m src kill` ИЛИ `Ctrl+C` / `systemctl stop bot`) BEFORE any SQL change. Never run SQL reset на live bot.

---

## Priority matrix (S11 operator readiness)

Per S11 PHASE 2 Q3 (trader REVISE): integrate priority + escalation INTO this runbook (single source of truth, не separate dashboard).

| Priority | Trigger characteristics | Operator action |
|----------|-------------------------|-----------------|
| **P0 — wake now** | CRITICAL severity (any halt where incorrect manual recovery can create OR conceal an open position) | Page on-call immediately. SQL + REST cross-check before resume. |
| **P1 — next morning** | RECOVERABLE severity (halt с automated diagnostic + clear recovery path) | Email/Slack notification. Resume during business hours. |
| **P2 — log only** | Operational halt с auto-resume mechanism (e.g. KILL_SWITCH_REQUESTED user-initiated) | Log to operator audit. No paging. |

## Quick reference table

| Halt code | Class | Severity | On-call escalation | Anchor |
|-----------|-------|----------|--------------------|--------|
| HALT_DRAWDOWN_L1 | Drawdown | RECOVERABLE | P1 | [#halt_drawdown_l1](#halt_drawdown_l1) |
| HALT_DRAWDOWN_L2 | Drawdown | CRITICAL | P0 | [#halt_drawdown_l2](#halt_drawdown_l2) |
| HALT_DRAWDOWN_L3 | Drawdown | CRITICAL | P0 | [#halt_drawdown_l3](#halt_drawdown_l3) |
| HALT_FLASH_CRASH | Drawdown | CRITICAL | P0 | [#halt_flash_crash](#halt_flash_crash) |
| HALT_DATA_QUALITY | Operational | RECOVERABLE | P1 | [#halt_data_quality](#halt_data_quality) |
| HALT_EXCHANGE_OUTAGE | Operational | RECOVERABLE | P1 | [#halt_exchange_outage](#halt_exchange_outage) |
| HALT_KILL_SWITCH | Operational | CRITICAL | P2 | [#halt_kill_switch](#halt_kill_switch) |
| KILL_SWITCH_REQUESTED | Operational | CRITICAL | P2 | [#kill_switch_requested](#kill_switch_requested) |
| HALT_BRACKET_INCOMPLETE | OCO/bracket | CRITICAL | P0 | [#halt_bracket_incomplete](#halt_bracket_incomplete) |
| HALT_OCO_ARM_TIMEOUT | OCO/bracket | RECOVERABLE | P1 | [#halt_oco_arm_timeout](#halt_oco_arm_timeout) |
| HALT_OCO_SIBLING_STUCK | OCO/bracket | RECOVERABLE | P1 | [#halt_oco_sibling_stuck](#halt_oco_sibling_stuck) |
| HALT_PARTIAL_FILL_BELOW_MIN | OCO/bracket | RECOVERABLE | P1 | [#halt_partial_fill_below_min](#halt_partial_fill_below_min) |
| HALT_FLATTEN_FAILED | OCO/bracket | CRITICAL | P0 | [#halt_flatten_failed](#halt_flatten_failed) |
| HALT_PHANTOM_SL | OCO/bracket | CRITICAL | P0 | [#halt_phantom_sl](#halt_phantom_sl) |
| HALT_BOOTSTRAP_AMBIGUOUS | Bootstrap/reconcile | CRITICAL | P0 | [#halt_bootstrap_ambiguous](#halt_bootstrap_ambiguous) |
| HALT_RECONCILE_DIVERGENCE | Bootstrap/reconcile | CRITICAL | P0 | [#halt_reconcile_divergence](#halt_reconcile_divergence) |
| HALT_EXIT_RECONCILE_DIVERGENCE | Bootstrap/reconcile | CRITICAL | P0 | [#halt_exit_reconcile_divergence](#halt_exit_reconcile_divergence) |
| HALT_RUNTIME_CRASH | Runtime | CRITICAL | P0 | [#halt_runtime_crash](#halt_runtime_crash) |
| HALT_BAR_POLL_STALL | Runtime | RECOVERABLE | P1 | [#halt_bar_poll_stall](#halt_bar_poll_stall) |

---

## 1. Drawdown class (4 codes) {#drawdown-class}

### Group recovery pattern

Drawdown halts share Wilson 95% CI override workflow (per ADR 0018). Procedure:

1. Verify drawdown source (data error vs real loss):
   ```sql
   SELECT * FROM equity_snapshots ORDER BY ts DESC LIMIT 100;
   ```
2. If real loss → wait для cooldown OR issue HMAC-signed override (per [[../components/risk-override]])
3. If data error → fix source first, then reset

### HALT_DRAWDOWN_L1 {#halt_drawdown_l1}

[RECOVERABLE — auto-resolves on next bar evaluation]

**Note:** L1 is NOT a halt в strict sense — `src/risk/circuit_breakers.py` returns L1 state из `check_drawdown` для sizing reduction (50% next entry), NOT FSM halt transit. Reason code emitted as audit event но trading continues.

#### Symptoms

- Log event: `circuit_breaker.l1_triggered` — equity drawdown exceeded L1 threshold but below L2.
- Bot continues trading; next signal will use half-sized position.
- No `halt_reason` written to `execution_state`.

#### Actions

1. Monitor next few bars — auto-resolves when drawdown recedes below L1 threshold.
2. If concerned about underlying losses: inspect `equity_snapshots` table for drawdown trajectory.
3. No SQL intervention required unless another halt code fires simultaneously.

#### Escalation

If L1 events repeat for > 5 consecutive bars → review strategy signal quality; consider manual stop via `python -m src kill`.

---

### HALT_DRAWDOWN_L2 {#halt_drawdown_l2}

[CRITICAL — full diagnosis]

#### Trigger

Equity drawdown exceeded L2 threshold (per `CircuitBreakerConfig.l2_drawdown_pct`). `RiskManager.assess()` → `check_drawdown` returns L2 → `Coordinator.request_halt(HALT_DRAWDOWN_L2)` → FSM `FLAT + RISK_HALT → HALTED`.

Source: ADR 0013 sub-decision 2.

#### Symptoms

- Log event: `circuit_breaker.l2_halt` with `drawdown_pct` field.
- `execution_state.halt_reason = 'HALT_DRAWDOWN_L2'`, `execution_state.state = 'HALTED'`.
- `halt_log` entry with `context_json` containing drawdown snapshot.

#### Diagnosis steps

1. **Read halt trail:**
   ```sql
   SELECT ts, reason, context_json FROM halt_log
   WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 5;
   ```

2. **Check execution_state:**
   ```sql
   SELECT state, halt_reason, position_qty, entry_price, updated_at
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```
   Verify `position_qty` — if non-zero bot was in a position when halted.

3. **Check exchange-side:**
   - Bybit Web UI → Assets → BTC balance.
   - Open Orders — any active orders?
   - Compare against `position_qty` from DB.

4. **Verify drawdown is real, not data error:**
   ```sql
   SELECT * FROM equity_snapshots ORDER BY ts DESC LIMIT 20;
   ```
   Look for abnormal spikes that could indicate feed errors.

#### Recovery procedure

1. **Stop bot** (if still running): `python -m src kill` или `systemctl stop bot`.

2. **If position_qty > 0 AND exchange confirms open position:** close manually via Bybit Web UI Market Sell.

3. **Verify all open orders cancelled** via Bybit Web UI Open Orders tab.

4. **Assess root cause:** real drawdown vs data error.
   - Real drawdown → review strategy; consider config change before restart.
   - Data error → fix feed, then proceed.

5. **Reset halt state:**
   ```sql
   UPDATE execution_state
   SET state = 'FLAT',
       bracket_id = NULL,
       last_attempt_num = 0,
       arming_started_at = NULL,
       oco_main_order_id = NULL,
       oco_tp_order_id = NULL,
       oco_sl_order_id = NULL,
       halt_reason = NULL,
       last_exit_reason = NULL,
       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
   WHERE symbol = 'BTCUSDT';
   ```

6. **Resume:** `python -m src run`.

#### Escalation criteria

- If drawdown was > 2× L2 threshold → escalate to maintainer before restart.
- If data error suspected but cannot confirm → do NOT restart, investigate feed first.

---

### HALT_DRAWDOWN_L3 {#halt_drawdown_l3}

[CRITICAL — full diagnosis]

#### Trigger

Equity drawdown exceeded L3 threshold (hard stop, per ADR 0013 sub-decision 3). More severe than L2 — indicates significant capital loss. Same FSM path as L2 but different threshold and escalation posture.

#### Symptoms

- Log event: `circuit_breaker.l3_halt` with `drawdown_pct` field.
- `execution_state.halt_reason = 'HALT_DRAWDOWN_L3'`.

#### Diagnosis steps

Same as HALT_DRAWDOWN_L2 above. Additionally:

1. **Mandatory post-mortem** — L3 is a hard stop requiring full capital loss accounting.

2. **Equity trajectory:**
   ```sql
   SELECT ts, equity_usdt, drawdown_pct FROM equity_snapshots
   ORDER BY ts DESC LIMIT 50;
   ```

3. **All recent trades:**
   ```sql
   SELECT * FROM trade_history ORDER BY entry_ts DESC LIMIT 20;
   ```

#### Recovery procedure

Same as L2. Additional requirements:

1. **Do NOT restart without maintainer review** — L3 threshold indicates systemic issue.
2. Document in `wiki/log.md`: equity at halt, drawdown_pct, strategy context.
3. Consider disabling `trading_enabled` in config until root cause resolved.

#### Escalation criteria

- L3 always requires escalation to maintainer before restart.
- If repeated L3 halts across sessions → strategy review required.

---

### HALT_FLASH_CRASH {#halt_flash_crash}

[CRITICAL — full diagnosis]

#### Trigger

Price movement exceeded flash crash threshold in single bar (per `CircuitBreakerConfig.flash_crash_pct`). Bot halted to prevent trading during abnormal market conditions. Per ADR 0013 sub-decision 4.

FSM: `FLAT + RISK_HALT → HALTED`

#### Symptoms

- Log event: `circuit_breaker.flash_crash_halt` with `bar_change_pct` and `bar_ts` fields.
- `execution_state.halt_reason = 'HALT_FLASH_CRASH'`.
- If bot was in `OCO_ARMED` when flash crash detected: OCO orders still live on exchange.

#### Diagnosis steps

1. **Read halt context:**
   ```sql
   SELECT ts, reason, context_json FROM halt_log
   WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 5;
   ```
   `context_json` contains the bar that triggered flash crash detection.

2. **Check current position:**
   ```sql
   SELECT state, halt_reason, position_qty, oco_tp_order_id, oco_sl_order_id
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

3. **Critical: check exchange state.** If `state` was `OCO_ARMED` at halt:
   - Bybit Web UI → Open Orders — are SL/TP orders still live?
   - BTC balance — did either leg fill during crash?

4. **Market condition:** check Bybit status page / external sources — is this a real crash or feed error?

#### Recovery procedure

1. **Stop bot** if still running.

2. **If OCO bracket active during crash:**
   - Check order history — did SL fill? At what price?
   - If SL filled → BTC balance should be 0. SQL-reset to FLAT.
   - If SL did NOT fill → position still open. Evaluate: manual close OR wait for market stabilization.

3. **Verify clean state** (no open orders, BTC balance = 0 or matches expected).

4. **SQL-reset** (see [Common SQL templates](#common-sql-templates)).

5. **Wait for market stabilization** before restart — flash crash conditions may persist.

6. **Resume:** `python -m src run`.

#### Escalation criteria

- If SL did not fire during crash (position still open) → escalate to maintainer immediately.
- If crash was > 20% price move → do NOT restart same day without review.

---

## 2. Operational class (4 codes) {#operational-class}

### Group recovery pattern

Operational halts are typically external-cause (operator action, data feed, exchange issues). Exchange state is usually stable; primary concern is clean local state before restart.

---

### HALT_DATA_QUALITY {#halt_data_quality}

[RECOVERABLE — abbreviated]

#### Symptoms

- Log event: `bar_source.data_quality_halt` — bar validator rejected consecutive bars (NaN OHLC, zero volume, timestamp regression, OHLC invariant violation).
- `execution_state.halt_reason = 'HALT_DATA_QUALITY'`.
- No position risk — bot halts before signal evaluation.

#### Actions

1. Check recent bars from log: `grep "bar_source" var/log/bot.log | tail -30`
2. Verify Bybit kline endpoint responding correctly: `curl -s "https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=5&limit=3" | jq`
3. If transient feed hiccup: SQL-reset `halt_reason = NULL` (see template), restart.
4. If bars still malformed: do NOT restart — investigate data feed issue first.

#### Escalation

If feed errors persist > 15 minutes → check Bybit status page; file incident if exchange-side.

---

### HALT_EXCHANGE_OUTAGE {#halt_exchange_outage}

[RECOVERABLE — abbreviated]

#### Symptoms

- Log event: `bybit_rest.outage_detected` OR `bybit_ws.outage_detected` — consecutive REST/WS failures exceeding threshold.
- `execution_state.halt_reason = 'HALT_EXCHANGE_OUTAGE'`.
- If bot was in `OCO_ARMED`: OCO bracket orders remain live on exchange during outage.

#### Actions

1. Check Bybit status: https://status.bybit.com
2. If OCO was active during outage:
   - After exchange recovers: verify open orders via Web UI.
   - Check if any leg filled during outage window.
3. Clean up: cancel stale orders if appropriate, verify BTC balance.
4. SQL-reset halt_reason, restart.

#### Escalation

If outage lasted > 1 hour AND bot had open OCO bracket → treat as CRITICAL: verify exchange state meticulously before restart (check order history for fills during outage).

---

### HALT_KILL_SWITCH {#halt_kill_switch}

[CRITICAL — full diagnosis]

#### Trigger

`RuntimeManager._maybe_kill_switch()` detected sentinel file `.kill_switch` on filesystem (per ADR 0022 sub-decision 5). This code fires when kill_switch is detected WHILE bot has an open position or pending bracket — distinguishing it from `KILL_SWITCH_REQUESTED` (clean shutdown).

#### Symptoms

- Log event: `runtime.kill_switch_open_position` — kill switch detected with non-FLAT state.
- `execution_state.halt_reason = 'HALT_KILL_SWITCH'`.
- `position_qty` may be non-zero.

#### Diagnosis steps

1. **Why was kill switch triggered?** Check operator intent — who ran `python -m src kill`?

2. **Check position state:**
   ```sql
   SELECT state, halt_reason, position_qty, entry_price,
          oco_tp_order_id, oco_sl_order_id
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

3. **Exchange verification:**
   - Bybit Web UI → Open Orders (any active SL/TP?).
   - BTC balance (any open position?).

4. **Order history** — did any orders fill while bot was shutting down?

#### Recovery procedure

1. **Determine intent:** was kill switch triggered intentionally (end of day) or emergency?

2. **If position open:**
   - Decide: manual close NOW or let OCO protect overnight.
   - If manual close: Bybit Web UI → Market Sell full BTC balance, cancel all open orders.

3. **Remove sentinel file:**
   ```bash
   rm -f .kill_switch   # or $RUNTIME_KILL_SWITCH_PATH
   ```

4. **SQL-reset** (see [Common SQL templates](#common-sql-templates)).

5. **Resume only when position is confirmed clean** (BTC balance = 0, no open orders).

#### Escalation criteria

- If position was open AND manual close is not straightforward (partial fill state) → escalate to maintainer.
- Document reason for kill switch in `wiki/log.md`.

---

### KILL_SWITCH_REQUESTED {#kill_switch_requested}

[CRITICAL — full diagnosis]

#### Trigger

`RuntimeManager._maybe_kill_switch()` detected sentinel file while state was FLAT — clean operator-initiated shutdown. Per ADR 0022 sub-decision 5. Despite being "operator-initiated / normal", it is CRITICAL severity because confirming clean state is mandatory before restart.

#### Symptoms

- Log event: `runtime.kill_switch_flat_shutdown`.
- `execution_state.halt_reason = 'KILL_SWITCH_REQUESTED'` (or state = FLAT with halt_reason set).
- No open position expected.

#### Diagnosis steps

1. **Verify clean state:**
   ```sql
   SELECT state, halt_reason, position_qty, oco_tp_order_id, oco_sl_order_id
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```
   `position_qty` should be 0. `state` should be FLAT or HALTED.

2. **Bybit Web UI:** confirm no open orders, BTC balance = 0.

#### Recovery procedure

1. **Verify intent** — was shutdown expected?

2. **Remove sentinel file:**
   ```bash
   rm -f .kill_switch   # default location, check Settings.kill_switch_path
   ```

3. **Reset halt_reason:**
   ```sql
   UPDATE execution_state
   SET halt_reason = NULL,
       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
   WHERE symbol = 'BTCUSDT';
   ```

4. **Restart:** `python -m src run`. `RuntimeManager` auto-cleanup sentinel on startup.

#### Escalation criteria

- If `position_qty` > 0 at shutdown → treat as `HALT_KILL_SWITCH` (open position path). Escalate.

---

## 3. OCO/bracket class (6 codes) {#oco-bracket-class}

### Group recovery pattern

OCO/bracket halts all involve live exchange orders. Before ANY SQL reset:

1. **Always check exchange state first** — Bybit Open Orders + Order History + BTC balance.
2. **Cancel stale orders manually** via Bybit Web UI before SQL reset.
3. **Close position** if BTC balance > 0 and bot cannot close automatically.
4. **Then** SQL-reset execution_state.

The risk: performing SQL reset while an open order exists on exchange → bot restarts thinking FLAT but exchange has live SL/TP → orphaned bracket creates future position risk.

---

### HALT_BRACKET_INCOMPLETE {#halt_bracket_incomplete}

[CRITICAL — full diagnosis]

#### Trigger

Bracket builder (`src/execution/bracket.py`) or OCO arming sequence failed to place all required orders (TP + SL) atomically. Entry filled but TP and/or SL not placed successfully. Bot cannot leave this position unprotected. Per ADR 0020 sub-decision 8.

FSM: `ENTRY_FILLED + BRACKET_INCOMPLETE → HALTED`

#### Symptoms

- Log event: `coordinator.bracket_incomplete_halt` with `missing_legs` field listing which orders failed.
- `execution_state.halt_reason = 'HALT_BRACKET_INCOMPLETE'`.
- `position_qty > 0` (entry filled).
- One or both of `oco_tp_order_id`, `oco_sl_order_id` may be NULL.

#### Diagnosis steps

1. **Read halt trail:**
   ```sql
   SELECT ts, reason, context_json FROM halt_log
   WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 5;
   ```

2. **Full state snapshot:**
   ```sql
   SELECT state, halt_reason, position_qty, entry_price,
          oco_main_order_id, oco_tp_order_id, oco_sl_order_id,
          bracket_id, last_attempt_num
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

3. **Exchange verification:**
   - Bybit Web UI → BTC balance → confirm position_qty matches.
   - Open Orders → which legs placed? Note exact order IDs.
   - Order History → was entry fully filled? At what price?

4. **Determine which legs are missing:**
   - NULL `oco_tp_order_id` → TP not placed.
   - NULL `oco_sl_order_id` → SL not placed (most dangerous — unprotected position).

#### Recovery procedure

1. **Stop bot immediately** — unprotected position.

2. **If SL is missing** (highest risk):
   - Option A: Place SL manually via Bybit Web UI (Sell Limit at SL price from `entry_price - ATR * sl_atr_mult`).
   - Option B: Market Sell entire position immediately to eliminate risk.

3. **If only TP is missing** (position has SL protection):
   - Place TP manually via Bybit Web UI (Sell Limit at TP price).
   - OR leave SL-only bracket (position protected against downside).

4. **Cancel any partial orders** from incomplete arming attempt (check Bybit Open Orders).

5. **After position resolved** (either manual close or manual bracket placed):
   - SQL-reset (see [Common SQL templates](#common-sql-templates)).

6. **Resume:** `python -m src run`.

#### Escalation criteria

- Missing SL with open position → immediately escalate if cannot place manual SL.
- If arming API error repeats > 2 times → investigate Bybit API health before restart.

---

### HALT_OCO_ARM_TIMEOUT {#halt_oco_arm_timeout}

[RECOVERABLE — abbreviated]

#### Symptoms

- Log event: `coordinator.oco_arm_timeout` — arming sequence exceeded `arming_timeout_seconds` without receiving confirmation.
- `execution_state.halt_reason = 'HALT_OCO_ARM_TIMEOUT'`.
- `position_qty` may be non-zero (entry filled, OCO placement timed out).

#### Actions

1. Check exchange state: Bybit Web UI → Open Orders → BTC balance.
2. If entry filled AND no OCO orders placed → treat as HALT_BRACKET_INCOMPLETE (see above).
3. If entry filled AND OCO partially placed → cancel partial orders, close position, SQL-reset.
4. If entry NOT filled → SQL-reset halt_reason, no position risk, restart.

#### Escalation

If `position_qty > 0` and OCO arming failed → escalate if manual bracket placement is unclear.

---

### HALT_OCO_SIBLING_STUCK {#halt_oco_sibling_stuck}

[RECOVERABLE — abbreviated]

#### Trigger

SL or TP-ордер сработал (Filled). Координатор вызвал `cancel_order(sibling)`, но получил `retCode`, отличный от `110001` (ордер уже не существует). FSM перешёл в `EXIT_SIBLING_CANCEL_FAILED`, затем — в `HALTED`.

Переход FSM: `EXIT_SIBLING_CANCELLING → EXIT_SIBLING_CANCEL_FAILED → HALTED`

Источник: ADR 0020 sub-decision 6.

#### Symptoms

- Log event: `coordinator.sibling_cancel_failed` with `retCode` field.
- `execution_state.halt_reason = 'HALT_OCO_SIBLING_STUCK'`.

#### Actions

1. Проверить идентификаторы ордеров:
   ```sql
   SELECT oco_tp_order_id, oco_sl_order_id, bracket_id
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```
2. Bybit Web UI → «Order History» + «Open Orders»: определить, какой leg заполнен (Filled), а какой завис (Active / PartiallyFilled).
3. Зафиксировать `retCode` из лога: `grep SIBLING_CANCEL_FAILED var/log/bot.log | tail -10`
4. Отменить застрявший sibling-ордер через Bybit Web UI.
5. Если позиция по BTC ненулевая (частичное исполнение): закрыть остаток через Web UI Market Sell.
6. SQL-reset (see [Common SQL templates](#common-sql-templates)), restart.

#### Escalation

- `retCode 110013` (partial fill, cannot cancel) → escalate: manual partial-fill resolution needed.
- `retCode 170213` (exchange risk lock) → escalate: Bybit support may be required.

**Post-mortem:** Зафиксировать точный `retCode`. Наиболее частые причины: `110013` (partial fill), `170213` (exchange risk lock), сетевой таймаут cancel_order.

---

### HALT_PARTIAL_FILL_BELOW_MIN {#halt_partial_fill_below_min}

[RECOVERABLE — abbreviated]

#### Symptoms

- Log event: `coordinator.partial_fill_below_min` — entry order partially filled but remaining qty below minimum lot size; cannot place full OCO bracket for residual.
- `execution_state.halt_reason = 'HALT_PARTIAL_FILL_BELOW_MIN'`.
- Small residual BTC position on exchange.

#### Actions

1. Check exchange state:
   ```sql
   SELECT state, position_qty, oco_main_order_id FROM execution_state WHERE symbol = 'BTCUSDT';
   ```
2. Bybit Web UI → BTC balance → confirm small residual amount.
3. Sell residual via Bybit Web UI Market Sell (even if below min lot — check if Bybit allows full balance sell).
4. Cancel any partially-placed OCO orders.
5. SQL-reset, restart.

#### Escalation

If residual cannot be sold (below Bybit minimum for market sell) → contact Bybit support OR wait for fee offsetting mechanism. Document in `wiki/log.md`.

---

### HALT_FLATTEN_FAILED {#halt_flatten_failed}

[CRITICAL — full diagnosis]

#### Trigger

Координатор дважды пытался закрыть позицию (полный объём + retry с `qty_step`), оба раза получил ошибку от биржи. Бот встал в `HALTED` с ненулевым остатком базовой монеты.

Переход FSM: `(OCO_ARMED | EXIT_PENDING | EXIT_SL_RESIDUAL) + FLATTEN_FAILED → HALTED`

Источник: ADR 0020 sub-decision 10.

#### Symptoms

- Log event: `coordinator.flatten_failed` with exchange `retCode` and `retMsg`.
- `execution_state.halt_reason = 'HALT_FLATTEN_FAILED'`.
- `position_qty > 0` (position open, flatten rejected twice).

#### Diagnosis steps

1. Проверить состояние в БД:
   ```sql
   SELECT state, bracket_id, last_attempt_num,
          oco_tp_order_id, oco_sl_order_id, updated_at
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

2. Bybit Web UI → «Assets» → BTC balance + вкладка «Open Orders». Зафиксировать фактический остаток BTC.

3. Проверить структурированный лог:
   ```bash
   grep HALT_FLATTEN_FAILED var/log/bot.log | tail -20
   ```
   Обратить внимание на `retCode` и `retMsg` от биржи — указывает причину отказа (min-qty, stale filter, exchange reject).

#### Recovery procedure

1. **Отменить все открытые ордера** по символу через Bybit Web UI. Не доверять боту — отменять вручную.

2. **Закрыть позицию** через Bybit Web UI: Spot → Sell BTC → Market. Убедиться, что BTC balance = 0 (с учётом комиссии).

3. **SQL-reset** (see [Common SQL templates](#common-sql-templates)).

4. **Перезапустить бот.** Проверить: `state=FLAT` в БД, `walletBalance ≈ 0 BTC` на бирже, нет открытых ордеров.

5. **Post-mortem обязателен** — добавить запись в `wiki/log.md`.

#### Escalation criteria

- If manual close fails (exchange also rejects) → escalate to maintainer immediately — position stuck.
- Investigate exchange `retCode` before restart: min-qty / stale lot filter / network rejection.

**Post-mortem log entry fields:**

| Поле | Значение |
|------|----------|
| Timestamp | UTC дата и время HALT |
| Qty stuck | Количество BTC в позиции |
| Root cause hypothesis | reject биржи / min-qty / stale lot filter / сеть |
| Fix applied | Ссылка на PR или описание изменения |

---

### HALT_PHANTOM_SL {#halt_phantom_sl}

[CRITICAL — full diagnosis]

#### Trigger

Reconciler при вызове `get_open_orders` обнаружил активный SL-ордер на бирже, для которого нет соответствующего `bracket_id` в локальной `execution_state`. Признак того, что ордер был создан предыдущим процессом, который упал, не записав результат в БД.

Переход FSM: `RECONCILING + RECONCILE_DIVERGENCE → HALTED`

Источник: ADR 0020 sub-decision 4.

#### Symptoms

- Log event: `reconciler.phantom_sl_detected` with `order_link_id` field.
- `execution_state.halt_reason = 'HALT_PHANTOM_SL'`.

#### Diagnosis steps

1. Bybit Web UI → «Open Orders»: найти ордер с подозрительным `orderLinkId`. Формат link-id у бота: `oco-{bracket_id}-sl-{attempt}`.

2. Извлечь `bracket_id` из `orderLinkId` и проверить в БД:
   ```sql
   SELECT * FROM execution_state WHERE bracket_id = '{bracket_id}';
   ```
   Если строка не найдена — phantom от крашнувшегося процесса.

3. Проверить лог:
   ```bash
   grep PHANTOM_SL var/log/bot.log | tail -10
   grep RECONCILE_DIVERGENCE var/log/bot.log | tail -10
   ```

#### Recovery procedure

1. **Отменить phantom-ордер** через Bybit Web UI. Убедиться, что он не был частично исполнен (check Order History).

2. **Проверить баланс кошелька** — если phantom не был исполнен, BTC balance должен быть равен нулю. Если есть остаток — закрыть через Market Sell.

3. При необходимости — **SQL-reset** если `execution_state.state` отличается от FLAT (see [Common SQL templates](#common-sql-templates)).

4. **Перезапустить бот.** `Coordinator.bootstrap()` заново просмотрит историю ордеров и корректно восстановит контекст.

#### Escalation criteria

- If phantom order was partially filled → position exists. Escalate — unclear ownership.

**Post-mortem:** Phantom SL — индикатор того, что процесс упал между вызовом `create_order` и записью результата в БД. Проверить: retry-логику вокруг записи `oco_sl_order_id`, OOM/SIGKILL журналы (journalctl, dmesg).

---

## 4. Bootstrap/reconcile class (3 codes) {#bootstrap-reconcile-class}

### Group recovery pattern

Bootstrap/reconcile halts all involve a mismatch between local SQLite state and exchange. The reconciler is the authority detector — it never modifies state, only produces verdicts. The Coordinator acts on verdicts.

**Exchange wins (per ADR 0019 sub-decision 3):** when local ↔ exchange diverge, exchange is source of truth. Align local to exchange, not the reverse.

**Always read `halt_log.context_json`** — it contains a snapshot of both local and exchange state at halt time, which is the authoritative diagnostic record.

---

### HALT_BOOTSTRAP_AMBIGUOUS {#halt_bootstrap_ambiguous}

[CRITICAL — full diagnosis]

#### Trigger

`Coordinator.bootstrap()` на старте процесса вызвал `reconciler.reconcile()`, и вердикт был `DIVERGENCE` — local SQLite и exchange расходятся, и это не классический heal/exit-случай.

Переход FSM: `INIT → RECONCILING + RECONCILE_DIVERGENCE → HALTED`
`halt_reason = "HALT_BOOTSTRAP_AMBIGUOUS"` (записан в `execution_state.halt_reason` + `halt_log`)

Источник: ADR 0021 sub-decision 1.

#### Symptoms

- Log event: `coordinator.bootstrap_ambiguous`.
- Bot stops at startup — does not enter main loop.
- `execution_state.halt_reason = 'HALT_BOOTSTRAP_AMBIGUOUS'`.

#### Diagnosis steps

1. Прочитать halt-trail:
   ```sql
   SELECT ts, reason, context_json FROM halt_log
   WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 5;
   ```
   `context_json` содержит local-state snapshot + reconcile verdict.

2. Прочитать current state:
   ```sql
   SELECT state, halt_reason, position_qty, entry_price,
          oco_main_order_id, oco_tp_order_id, oco_sl_order_id,
          bootstrap_at, last_reconcile_at
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

3. Bybit Web UI → Open Orders + walletBalance(BTC). Сравнить с local snapshot.

#### Recovery procedure

1. **Решить, кто прав** — обычно exchange (per ADR 0019 reconcile-as-truth). Если local имеет несоответствующий `oco_main_order_id`, который exchange не знает — local stale.

2. **Привести exchange в чистое состояние:** отменить все открытые ордера через Web UI, при необходимости закрыть позицию Market Sell.

3. **SQL-reset** (see [Common SQL templates](#common-sql-templates), **включая `halt_reason=NULL`**).

4. **Перезапустить бот.** `bootstrap()` теперь увидит чистый exchange + чистый local → AGREE → FLAT.

#### Escalation criteria

- If cannot determine which is source of truth (both local and exchange show position) → escalate to maintainer.

**Post-mortem:** Зафиксировать в `wiki/log.md` какой именно diff вызвал ambiguous-вердикт. Если повторяется — обновить classifier в `src/execution/reconciler.py::_classify_*` и добавить regression тест.

---

### HALT_RECONCILE_DIVERGENCE {#halt_reconcile_divergence}

[CRITICAL — full diagnosis]

#### Trigger

Reconciler обнаружил расхождение между локальным `execution_state` и фактическим состоянием биржи во время running reconcile (not bootstrap). Divergence not auto-healable.

Source: ADR 0020 sub-decision 4, reconciler component.

#### Symptoms

- Log event: `reconciler.divergence_halt`.
- `execution_state.halt_reason = 'HALT_RECONCILE_DIVERGENCE'`.

#### Diagnosis steps

1. Read halt trail (contains reconcile verdict snapshot):
   ```sql
   SELECT ts, reason, context_json FROM halt_log
   WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 5;
   ```

2. Full state snapshot:
   ```sql
   SELECT symbol, state, halt_reason, position_qty, entry_price,
          oco_main_order_id, oco_tp_order_id, oco_sl_order_id,
          last_reconcile_at, updated_at
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

3. Bybit Web UI: compare local `position_qty` against BTC balance; compare order IDs against Open Orders.

4. Determine divergence type from `context_json`:
   - Extra order on exchange not in local → possible phantom (see HALT_PHANTOM_SL path).
   - Missing order on exchange that local expects → order may have been cancelled/filled externally.
   - Balance mismatch → fill occurred without local record.

#### Recovery procedure

1. **Stop bot** if still running.

2. **Exchange wins:** verify exchange state manually.
   - Close open positions via Web UI if any.
   - Cancel stale orders.

3. **SQL-reset** (see [Common SQL templates](#common-sql-templates)).

4. **Перезапустить бот.**

#### Escalation criteria

- If unable to match local vs exchange state → escalate before any SQL change.
- If divergence indicates external order modification (not by bot) → security concern, escalate.

> Full component documentation: [[../components/reconciler#divergence-handling]]

---

### HALT_EXIT_RECONCILE_DIVERGENCE {#halt_exit_reconcile_divergence}

[CRITICAL — full diagnosis]

#### Trigger

Бот был в `EXIT_PENDING`, WS отвалился, после reconnect reconciler увидел state mismatch (например, exit-ордер уже не в open_orders, но walletBalance не сошёлся с ожидаемым FLAT).

Переход FSM: `EXIT_PENDING + WS_RECONNECT → RECONCILING + RECONCILE_DIVERGENCE → HALTED`
`halt_reason = "HALT_EXIT_RECONCILE_DIVERGENCE"`

Источник: ADR 0021 sub-decision 3.

#### Symptoms

- Log event: `reconciler.exit_divergence_halt`.
- `execution_state.halt_reason = 'HALT_EXIT_RECONCILE_DIVERGENCE'`.
- Bot was in EXIT_PENDING at WS disconnect.

#### Diagnosis steps

1. Прочитать halt_log + execution_state (как выше).
2. Bybit Web UI → Order History для exit-ордера: filled / cancelled / partially?
3. walletBalance(BTC): остаток или ноль?

#### Recovery procedure

1. **If exit-ордер was filled AND BTC = 0:** state в SQLite stale. SQL-reset к FLAT **включая `halt_reason=NULL`** + optionally set `last_exit_reason='EXIT_RECONCILE_DETECTED'` для аудита.

2. **If exit-ордер was partially filled:** закрыть остаток вручную через Market Sell, затем SQL-reset.

3. **If exit-ордер still active (not filled):** cancel manually, then SQL-reset (position may still be open — check BTC balance).

4. Перезапустить бот.

#### Escalation criteria

- If WS disconnect duration exceeded `heal_max_age_seconds=3600` AND position unclear → escalate.

**Post-mortem:** EXIT divergence — индикатор того, что `EXIT_PENDING` order заполнился во время WS-разрыва, но автоматический heal-путь не сработал. Проверить: возраст filled события > `heal_max_age_seconds=3600`? Тогда DIVERGENCE — корректное поведение. Иначе — баг в classifier'е, требуется тест + фикс.

---

## 5. Runtime class (2 codes) {#runtime-class}

### Group recovery pattern

Runtime halts are process-level failures. Primary risk is unknown state at time of crash. Always verify exchange state before restart.

---

### HALT_RUNTIME_CRASH {#halt_runtime_crash}

[CRITICAL — full diagnosis]

#### Trigger

Unhandled exception в `RuntimeManager.run()` — top-level `except Exception` catch в `src/runtime/manager.py` (ADR 0022 sub-decision 6). Bot crashed mid-operation.

FSM: exception caught → `request_halt(HALT_RUNTIME_CRASH)` → state written if possible.

#### Symptoms

- Log event: `runtime.crash` with `exc_type` and `exc_msg` fields.
- `execution_state.halt_reason = 'HALT_RUNTIME_CRASH'`.
- State at crash time may be anything (FLAT, OCO_ARMED, EXIT_PENDING, etc.).

#### Diagnosis steps

1. **Find crash log:**
   ```bash
   grep "runtime.crash" var/log/bot.log | tail -20
   ```

2. **Read crash context from halt_log:**
   ```sql
   SELECT ts, reason, context_json
   FROM halt_log
   WHERE symbol = 'BTCUSDT' AND reason = 'HALT_RUNTIME_CRASH'
   ORDER BY ts DESC LIMIT 5;
   ```

3. **Full state at crash:**
   ```sql
   SELECT state, halt_reason, position_qty, entry_price,
          oco_tp_order_id, oco_sl_order_id, updated_at
   FROM execution_state WHERE symbol = 'BTCUSDT';
   ```

4. **Exchange state verification:**
   - Bybit Web UI → BTC balance (does it match `position_qty`?).
   - Open Orders → any active OCO orders?

5. **Identify crash cause** from exception in log. Reproduce in dev. Fix bug → new ADR amendment if invariant changed.

#### Recovery procedure

1. **Stop any lingering process** (check `ps aux | grep "src"`, kill if still running).

2. **Resolve open position if any:**
   - If `position_qty > 0` AND exchange confirms → decide: keep with manual SL OR market sell.
   - Cancel any stale OCO orders.

3. **SQL-reset** (see [Common SQL templates](#common-sql-templates)).

4. **Fix the bug before restart** — HALT_RUNTIME_CRASH indicates unhandled code path.

5. **Resume:** `python -m src run` (only after bug fix OR confirming crash was one-time event).

#### Escalation criteria

- If crash is reproducible (second crash same session) → do NOT restart. Escalate.
- If crash occurred during OCO arming (position partially created) → escalate immediately.

---

### HALT_BAR_POLL_STALL {#halt_bar_poll_stall}

[RECOVERABLE — abbreviated]

#### Trigger

`BarSource.consecutive_failures >= settings.runtime_bar_poll_stall_threshold` (default 24 × 5s = 120s) — ADR 0022 sub-decision 3.

Signal-pipeline halt (НЕ position-safety). OCO bracket exchange-side; existing positions защищены bracket orders.

#### Symptoms

- Log event: `bar_source.stall_halt` with `consecutive_failures` count.
- `execution_state.halt_reason = 'HALT_BAR_POLL_STALL'`.
- If bot was in `OCO_ARMED`: OCO bracket remains active on exchange during stall.

#### Actions

1. Check Bybit REST status:
   ```bash
   curl -s https://api.bybit.com/v5/market/time | jq
   ```

2. Review recent failure cluster:
   ```bash
   grep "bar_source.poll_failed" var/log/bot.log | tail -50
   ```

3. Failure cluster < 5 minutes → likely transient. SQL-reset `halt_reason`, restart.
4. Failure cluster > 30 minutes → investigate network / API key / check Bybit incident page.
5. After SQL-reset and restart: BarSource counter resets automatically on first successful poll.

#### Escalation

If stall persists after restart → network/API issue. Check API key validity, firewall rules, Bybit status.

---

## Common SQL templates {#common-sql-templates}

### Reset execution_state to FLAT (Sprint 7 schema)

> Sprint 7 migration `0005_halt_persistence.sql` добавила колонки `halt_reason`, `last_exit_reason`, `last_reconcile_at`, `bootstrap_at` + audit-таблицу `halt_log`.
> Миграции: `migrations/0003_execution_state.sql` + `0004_execution_state_v2.sql` + `0005_halt_persistence.sql`.

```sql
-- Reset execution_state to FLAT (Sprint 7 schema):
UPDATE execution_state
SET state = 'FLAT',
    bracket_id = NULL,
    last_attempt_num = 0,
    arming_started_at = NULL,
    oco_main_order_id = NULL,
    oco_tp_order_id = NULL,
    oco_sl_order_id = NULL,
    halt_reason = NULL,                    -- S7: reset on manual recovery
    last_exit_reason = NULL,               -- optional: preserve for audit-trail
    last_reconcile_at = NULL,
    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
WHERE symbol = 'BTCUSDT';
```

> **Не удалять `halt_log` записи.** Append-only audit. Чтение для post-mortem — обязательно.

### Diagnostic SELECT (full state snapshot)

```sql
SELECT symbol, state, halt_reason, last_exit_reason,
       position_qty, entry_price,
       bracket_id, last_attempt_num,
       oco_main_order_id, oco_tp_order_id, oco_sl_order_id,
       arming_started_at, last_reconcile_at, bootstrap_at, updated_at
FROM execution_state
WHERE symbol = 'BTCUSDT';
```

### Halt audit trail

```sql
SELECT ts, reason, context_json FROM halt_log
WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 20;
```

---

## Maintenance rule

If page exceeds 50KB threshold (per Read-tool guard): split into `halt-recovery.md` (index + class groups overview) + `halt-recovery-<class>.md` (per-class deep dive). Per `~/.claude/CLAUDE.md` Read tool guard policy.

When new halt code added to `src/risk/reason_codes.py`:
1. Add entry to Quick reference table (with anchor).
2. Apply CRITICAL criterion: "halt where incorrect manual recovery can create or conceal an open position?"
3. If CRITICAL → write full diagnosis section in appropriate class group.
4. If RECOVERABLE → write abbreviated section.
5. Update group recovery pattern if new code shares family pattern.
6. Update `wiki/index.md` Runbooks section description.

---

## Связанные материалы

- [[../decisions/0013-circuit-breakers-l1-l2-l3-flash]]
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]
- [[../decisions/0021-sprint-7-resilience]]
- [[../decisions/0022-sprint-8a-live-runtime]]
- [[../decisions/0023-halt-code-fsm-event-mapping]]
- [[../components/oco]]
- [[../components/reconciler]]
- [[../components/coordinator]]
- [[../components/circuit-breakers]]
- [[../components/runtime-manager]]
- [[../components/risk-override]]
- [[../components/execution-state-machine]]
- [[../components/ws-private-consumer]]
- [[../../trading/concepts/reason-codes]]
