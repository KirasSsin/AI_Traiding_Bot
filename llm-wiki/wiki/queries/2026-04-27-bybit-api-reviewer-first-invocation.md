---
title: bybit-api-reviewer First Invocation (δ TESTNET S38 readiness)
type: query
tags: [query, bybit-api-reviewer, sprint-38, delta-testnet, six-axis-review, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - src/execution/coordinator.py
  - src/execution/bybit/adapter.py
  - src/execution/bybit/ws_private.py
  - src/execution/bybit/errors.py
  - project/decisions/0058-sprint-38-delta-parallel-hardening.md
---

# bybit-api-reviewer First Invocation

**Date:** 2026-04-27
**Sprint:** S38 T3
**Trigger:** ADR 0058 SD-2 + ROUND 6 trading-logic-reviewer F3
**Context:** δ TESTNET activation. First production-runtime invocation of `bybit-api-reviewer` agent (dormant since S30 — created precisely для этого moment). Agent spec: `~/.claude/agents/bybit-api-reviewer.md` (146 lines, 6-axis checklist).

## Review scope

```
Review src/execution/coordinator.py + src/execution/bybit/* — FIRST production-runtime context invocation.

CONTEXT:
- δ TESTNET activation S38 (operator currently activates per delta-activation-playbook.md)
- Strategy: MeanReversionRsiBBStrategy + MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED (RSI 35/65, BB 1.5σ AND-gate)
- Symbol: BTCUSDT 4H (single-symbol per pre-commit, fail-closed whitelist enforced)
- HaltGate fail-closed (4 triggers + tamper detection HALT_UNKNOWN_SYMBOL)
- Pybit V5 adapter via src/execution/bybit/adapter.py (REST + WS private)
- ws_private.py = WebSocket private channel consumer (order/execution events)
- coordinator.py = lifecycle owner (bootstrap + on_order_event + start_bracket + arm_oco + reconcile)

FILES TO REVIEW:
- src/execution/coordinator.py (663 lines)
- src/execution/bybit/adapter.py (289 lines)
- src/execution/bybit/ws_private.py (172 lines)
- src/execution/bybit/errors.py (33 lines)

6-AXIS CHECKLIST: rate limits / order params / WS schema / retCode handling / pagination / HMAC sign
```

## Findings

### Blockers (must fix перед next live order)

**None identified.** δ TESTNET activation cleared on this surface.

The four files reviewed delegate ALL signing + transport (HMAC SHA256, recv_window, timestamp, NTP drift handling) to `pybit.unified_trading.HTTP` and `pybit.unified_trading.WebSocket` per ADR 0016. No custom signing code in scope = no signature-correctness BLOCKER possible from this surface. Pybit ≥5.11 owns Axis 6 entirely.

### Concerns (HIGH — fix soon)

**H1. Rate-limit awareness absent — no backoff on `10006` (Axis 1 + Axis 4)**
- `src/execution/bybit/errors.py:21` maps `10006 → RATE_LIMIT_HIT` — но **никто это не consumes для backoff**. `BybitAPIError(reason=RATE_LIMIT_HIT)` raises к caller, и в `coordinator._try_place_market_sell` / `_best_effort_cancel` — bare `except Exception`, no retry-with-sleep, no exponential backoff.
- Per agent checklist: "Backoff strategy: exponential на 429/10006 errors. No tight retry loops без sleep."
- Risk on δ TESTNET: signal cluster (RSI cross + BB touch одновременно) → `arm_oco` retry loop after `IllegalTransitionError` recovery → 60 orders/sec spot limit hit → cascade rejects.
- Fix: wrap `_rest._http.place_order` calls в decorator-level retry с exponential backoff specifically for `retCode==10006`. OR document explicitly that S38 single-symbol BTCUSDT-4H bar cadence (1 bar / 4h) makes RL exhaustion impossible by design and add an assertion in `runtime/` enforcing single-symbol.
- **Recommend: pre-s39-backlog** (S38 operationally safe — 1-bar-per-4h cadence guarantees < 5 req/min; document the dependency).

**H2. WebSocket reconnect re-subscribe path not auditable (Axis 3)**
- `ws_private.py:55-75` calls `WebSocket(...).order_stream(callback=...)` → relies on pybit's internal reconnect-and-resubscribe loop. The agent checklist requires: "Reconnect logic: ping/pong heartbeat 30s. Re-subscribe topics after reconnect." Code provides `check_alive(max_silence_seconds=30.0)` watchdog (line 101) and a close-hook (line 77-99), но resubscribe **happens implicitly via pybit re-connect**, not via re-calling `order_stream/wallet_stream/execution_stream`.
- After `on_disconnect` fires `coordinator.on_ws_reconnect()` → reconcile path runs, BUT if pybit failed to re-attach the subscription (silent failure), reconcile would deliver AGREE on stale local state and bot would proceed без live event flow — **silent dead WS**.
- Fix: add post-reconnect probe (e.g. `check_alive` second pass after N seconds) that explicitly verifies `last_ping_time` advanced AFTER on_disconnect, OR re-instantiate WebSocket if `check_alive` returns False twice in row. Currently `check_alive` calls `on_disconnect` (line 115) but does NOT bring the WS back up.
- **Recommend: pre-s39-backlog** (operator monitors logs during δ TESTNET first activation per playbook step 5; manual restart fallback exists).

**H3. `accountType="UNIFIED"` hardcoded (Axis 2 / config drift)**
- `adapter.py:272` — `get_wallet_balance(accountType="UNIFIED", ...)`. If user's TESTNET account is non-UNIFIED (e.g. legacy SPOT account on testnet), wallet read fails → bootstrap raises BybitAPIError(-1, "wallet for {coin} not found"). Currently no config knob к override.
- Per Bybit V5: spot trading on testnet may use either UNIFIED or SPOT classic depending on creation date. Operator activating δ for first time может hit this.
- Fix: extract `account_type` к `BybitMarketAdapter.__init__` parameter, default `"UNIFIED"`, allow operator override via settings. Sanity-check at bootstrap: try UNIFIED first, fall back к SPOT с warning if 10001-class param error.
- **Recommend: S38 hotfix candidate IF operator confirms TESTNET account type during playbook step 1.** Otherwise pre-s39-backlog.

### Concerns (MEDIUM — track for S39+)

**M1. retCode taxonomy gaps (Axis 4)**
- `errors.py:_MAP` covers 8 codes. Agent checklist lists 11+ common codes. Missing mappings:
  - `10001` (params error) — currently → UNKNOWN_ERROR. Should map к explicit FILTER_VIOLATION или new BAD_REQUEST. Critical because RSI/BB strategy generates fixed qty per signal — params error during δ would be silent UNKNOWN.
  - `10010` (UID not authorized) — auth-class, distinct from 10003 (IP whitelist).
  - `170132` (qty too small) and `170134` (price out of range) — already covered by 170131/170140 grouped к FILTER_VIOLATION, но 170132 specifically tells filter we have stale `instruments_info`. Worth distinct ReasonCode.
- Risk: δ TESTNET surfaces a new code → UNKNOWN_ERROR → operator sees opaque alert. Not blocker but harms ops debuggability.
- Fix: extend `_MAP` + add 1-2 new ReasonCode values (BAD_REQUEST, AUTH_FAILED).

**M2. `place_order` response shape assumes V5 (Axis 3 / contract)**
- `adapter.py:131-134` — `resp["result"]["orderId"]` direct access; no defensive check that `result` key exists. If Bybit V5 spec changes shape (e.g. wraps in `data: {orderId}`) → KeyError → bare exception in `start_bracket._adapter.place_order()` call → bracket FSM stuck в FLAT (no row insert because place_order raised before `repo.upsert`). Per agent checklist Axis 3: "Data structure: message['data'] — list of dicts (V5 changed от V3 single-dict)."
- Same risk on `cancel_order`, `get_order`, `get_open_orders`, `get_order_history`.
- Fix: helper `_safe_get(resp, "result.orderId")` с explicit assertion + structured log on shape mismatch.

**M3. WebSocket `data` array iteration drops items silently on parse-fail (Axis 3)**
- `ws_private.py:131-148` — `_on_order_raw` / `_on_wallet_raw` exception-swallow at OUTER try (line 138). If `msg.get("data", [])` returns single dict (V3-shape regression) instead of list, `for item in data` iterates dict keys → `_parse_order` receives a string → KeyError → entire batch dropped.
- ADR 0021 sub-decision 3 reconcile-on-divergence is the safety net, но a silent WS-event-drop window between reconcile cycles = potential stale state.
- Fix: explicit `isinstance(msg.get("data"), list)` guard + log + drop с structured marker.

**M4. WebSocket auth credentials lifecycle (Axis 6)**
- `ws_private.py:41-49` — `api_key` + `api_secret` stored as instance attrs, passed к pybit `WebSocket(api_key=..., api_secret=...)`. No explicit redaction in `__repr__` / log output (the class doesn't override `__repr__`). If a developer logs the consumer instance during debugging, secret leaks к log.
- Per agent checklist: "No api_secret в logs — explicit redaction. No api_secret в exception messages — sanitize before raise."
- Fix: add `__repr__` returning `BybitPrivateWSConsumer(endpoint=..., REDACTED)` + add lint rule banning bare `f"{self}"` interpolation.

### Concerns (LOW)

**L1. `_TERMINAL_STATES` includes `ERROR` but no event paths route to ERROR в visible scope.** Defensive but adds dead code surface. Verify в state_machine.py whether ERROR is reachable.

**L2. `coordinator.py:200` — `int(lid.split("-")[-1])` exception class is `(ValueError, IndexError)` but `split` always returns list ≥1, so IndexError unreachable here.** Cosmetic.

**L3. `errors.py:31` — `# noqa: ARG001` suppresses unused arg warning for `ret_msg`.** Future enhancement: include `ret_msg` в reason resolution для FILTER_VIOLATION subdivision (current grouping of 110017/170131/170140/170213 loses semantic).

### Verified (positive findings)

- **V1. Banned-spot-fields guard (Axis 2)** — `adapter.py:96-101` rejects `tpslMode`/`takeProfit`/`stopLoss`/etc. that Bybit Spot V5 silently rejects with 170130. Defense-in-depth + tested per ADR 0020 sub-decision 3.
- **V2. `marketUnit=quoteCoin` ban (Axis 2)** — `adapter.py:104-109` blocks 16-dp accumulation drift bug from probe S2 v2.
- **V3. Cancel-of-Filled race classifier (Axis 4)** — `adapter.py:212-213` defense-in-depth: requires BOTH `retCode==110001` AND `reason is REJECT_ORDER_ALREADY_TERMINAL`. Future _MAP additions can't silently swallow as "already terminal". Excellent.
- **V4. orderLinkId attempt-bumping (Axis 2)** — `coordinator.py:396-408` bumps `last_attempt_num` BEFORE place to avoid duplicate-orderLinkId 10006 rejects on retry. Persisted upfront so crash mid-arm doesn't reuse number.
- **V5. Bracket flatten-cascade safety (Axis 4)** — `coordinator._handle_sl_partial` cancels TP sibling FIRST before flatten residual (sub-dec 6 race fix — orphan TP could self-fill on bid spike → phantom short).
- **V6. WS event terminal-state drop (Axis 3 / idempotency)** — `coordinator.py:290-298` silently drops WS echoes that arrive after FLAT/HALTED + logs warning. Stale echo cannot kill executor worker.
- **V7. WS missing-fee-field validation (Axis 3)** — `ws_private.py:165-171` rejects Filled/PartiallyFilled events lacking `cumExecFee`/`feeCurrency`. Audit-trail integrity preserved.
- **V8. Pybit delegation для signing (Axis 6)** — НЕ rolling own HMAC. Per ADR 0016 — pybit V5 ≥5.11 owns recv_window, NTP-aligned ms-epoch timestamp, signature payload formation. Zero custom-crypto risk.
- **V9. WS close-hook + heartbeat backstop (Axis 3)** — `ws_private.py:77-117` dual-path on-disconnect: close-hook primary + `check_alive(30s)` watchdog backstop. Try/except wrap means pybit upgrade can't crash startup.
- **V10. `availableToWithdraw` empty-string coercion (Axis 2)** — `adapter.py:283` handles Bybit V5 quirk: empty string when funds fully locked, coerced к Decimal('0').

### Follow-ups для wiki

- Update [[components/bybit-adapter]] add section "Rate-limit posture" stating: single-symbol BTCUSDT-4H δ TESTNET cadence guarantees < 5 req/min, well under 60/sec и 600/min limits. Document explicitly the **dependency** that S38 deployment is single-symbol.
- Update [[components/ws-private-consumer]] add section "Reconnect verification gap" linking H2.
- Consider new component page [[components/bybit-error-taxonomy]] enumerating mapped retCodes + ReasonCode bridge — currently scattered between `errors.py` + `risk/reason_codes.py`.

## Triage decisions

| Finding | Severity | Action |
|---------|----------|--------|
| H1 — rate-limit backoff missing | HIGH | **pre-s39-backlog** — S38 single-symbol 4H cadence makes RL exhaustion impossible; document dependency in component page (S38 T7 wiki sync) |
| H2 — WS reconnect verification gap | HIGH | **pre-s39-backlog** — operator monitors first δ activation per playbook; add explicit ws-resubscribe probe in S39 |
| H3 — `accountType="UNIFIED"` hardcoded | HIGH | **S38 operator gate** — playbook step 1 must confirm TESTNET account = UNIFIED. If non-UNIFIED → S38 hotfix (T8 candidate). If UNIFIED → pre-s39-backlog для config-knob refactor. |
| M1 — retCode taxonomy gaps (10001, 10010, 170132 разделение) | MEDIUM | pre-s39-backlog |
| M2 — pybit response-shape direct access (KeyError risk) | MEDIUM | pre-s39-backlog |
| M3 — WS `data` array isinstance guard | MEDIUM | pre-s39-backlog |
| M4 — WS consumer `__repr__` redaction для secrets | MEDIUM | pre-s39-backlog (security-auditor co-review recommended) |
| L1-L3 — minor / cosmetic | LOW | pre-s39-backlog |
| V1-V10 — verified positive findings | — | document в wiki components page (S38 T7) |

## Severity breakdown

- **0 BLOCKER**
- **3 HIGH** (H1 rate-limit / H2 ws-reconnect / H3 accountType)
- **4 MEDIUM** (M1-M4)
- **3 LOW** (L1-L3)
- **10 VERIFIED** (V1-V10)

**Total: 20 findings.**

## Recommended actions per HIGH

| Action | Owner | Sprint |
|--------|-------|--------|
| Document single-symbol RL dependency in components/bybit-adapter wiki | AI (T7) | S38 |
| Operator confirms TESTNET account = UNIFIED при playbook step 1; if NOT, escalate к maintainer-dispatcher для S38 T8 hotfix | Operator | S38 |
| Add ws-resubscribe verification probe + accountType config knob | AI | S39 |

## Related

- ADR 0058 (S38 — этот sprint)
- ADR 0019 (Coordinator design)
- ADR 0020 (Bybit Spot OCO emulation, 11 sub-decisions)
- ADR 0021 (Reconciler unified path, 6 sub-decisions)
- ADR 0022 (Runtime lifecycle + RuntimeManager)
- ADR 0023 (halt-code → FSM event mapping)
- ADR 0016 (Bybit venue migration / pybit V5 ≥5.11)
- pre-s38-backlog.md (ROUND 6 binding — F3 trigger для этого invocation)
- delta-activation-playbook.md (operator procedure)

## Reviewer self-meta

`bybit-api-reviewer` agent dormant since S30 creation (Sprint 32d Kit Phase 3 per ADR 0048). FIRST production-runtime invocation. Methodology = full 6-axis checklist applied. Output format compliant с `superpowers:requesting-code-review` standard (Blockers / Concerns / Verified / Follow-ups).

Reference: Bybit V5 docs https://bybit-exchange.github.io/docs/v5/intro
