---
title: 0027. Sprint 12 — Live demo validation 24-72h + production wiring
type: decision
date: 2026-04-25
sprint: 12
tags: [adr, sprint-12, live-demo, mainnet-validation, fillrecorder, data-integration, endpoint-routing, bybit-demo]
sources:
  - project/pre-s12-backlog.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
  - project/decisions/0021-sprint-7-resilience.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0026-sprint-11-operator-readiness.md
  - project/runbooks/halt-recovery.md
  - project/runbooks/pre-flight.md
status: proposed
---

# 0027. Sprint 12 — Live demo validation 24-72h + production wiring

**Status:** proposed
**Date:** 2026-04-25

## Context

Sprint 12 closes deferred carry-overs от S11 + delivers first live demo validation cycle:
- `_NoopFillRecorder` stub в `_cmd_run` (closes S11 T2 deferral)
- `_load_ohlcv` empty df stub в `_cmd_wfa` (closes S11 NOTE для Gate 5)
- Live demo Bybit V5 endpoint validation (S11 Q1 trader CONFIRM, deferred от A scope)

S11 shipped operator infrastructure (halt-recovery priority matrix + log-grep-templates + pre-flight checklist + monitor CLI) — S12 exercises that infrastructure через 48h validation window.

PHASE 2 brainstorming verdicts (`pre-s12-backlog.md`):
- Q1 CONFIRM: Bybit demo trading endpoint
- Q2 CONFIRM: 48h validation duration
- Q3 CONFIRM: Multi-criteria success gate + zero-trade clause MANDATORY
- Q4 REVISE-additive: Parquet via `data_collector` shim required (config-dict API mismatch)
- Q5 REVISE-additive: `FillRecorderAdapter` class required (FillHistoryRepository не drop-in для `_FillRecorderProto`)
- Q6 REVISE-DISAGREE-FACTUAL: NO endpoint string change for S12 — current `"demo.bybit.com"` correct; future 3-way enum к S13+
- Q7 CONFIRM: P0-wake + alpha.11 rollback + RC tag iteration + zero-migration constraint

**Critical correction (Q6):** SPRINT_STATE S11 C1 carry-over note "fix endpoint к testnet substring" was WRONG. Trader source-cited evidence (`__main__.py:138` + `ws_private.py:65-67`) verified by maintainer via grep (CC1 lesson). Truth table: current routing CORRECT for S12 demo intent.

## Decision

### Production wiring (Q4 + Q5 REVISE-additive)

**T1: `FillRecorderAdapter` class** (closes S11 T2 `_NoopFillRecorder` stub)
- New class `src/risk/fill_recorder_adapter.py` implementing `_FillRecorderProto`
- Method `on_fill_event(evt: dict[str, Any]) -> None`:
  - Parse Bybit V5 WS execution event → `FillRecord`
  - Derive `parent_trade_id` via `trade_history` lookup (`exec_id` cross-ref) OR `coordinator.bracket_id` mapping
  - Call `FillHistoryRepository.insert_fill(record)`
- Wire в `_cmd_run` constructor — replace `_NoopFillRecorder` instance с `FillRecorderAdapter(conn=db_conn, trade_history=trade_history_repo)`
- **No new migration** (`trade_fills` table already exists per S9 Q3 B1)

**T2: `_load_ohlcv` Parquet shim** (closes S11 `_cmd_wfa` empty df stub)
- Modify `src/__main__.py::_load_ohlcv` к call `data_collector.load_market_data(config_dict)`:
  - Translate CLI args `(symbol, start, end)` → config dict `{"data": {"source": "parquet", "parquet_path": ..., "start_date": start, "end_date": end}}`
- Improve error message when Parquet missing: `"Parquet not found at <path>. Run 'python -m src backfill --symbol <X>' first."`
- Update `wiki/project/runbooks/pre-flight.md` Gate 5 — document pre-fetch prerequisite

### Validation params (Q1 + Q2 + Q3)

**T3: Live demo validation run script + plan**
- Endpoint: Bybit demo trading (`settings.testnet=True` → `endpoint="demo.bybit.com"` per existing routing)
- Duration: 48h (1H BTC/USDT bars × 48 = 48 bars)
- Symbol: BTCUSDT
- Virtual capital: $1000 (Bybit demo arbitrary)
- Pre-flight: ALL gates pass per `pre-flight.md` (config + DB migration + reconcile-only smoke + override + WFA optional)
- Operator monitoring: `_cmd_monitor` every 5min + `tail -f bot.log | jq '.level == "warning" or "error"'`

**T4: Multi-criteria success gate**
- ✅ **Zero P0 halts** (per S11 priority matrix `halt-recovery.md`)
- ✅ **Reconcile divergence count = 0** (ADR 0021 4-valued verdict — AGREE/HEAL acceptable, DIVERGENCE blocker)
- ✅ **Bootstrap clean** (no `HALT_BOOTSTRAP_AMBIGUOUS`)
- ✅ **WS uptime ≥ 47/48h** (barring P1 outages)
- **IF trades occur:** drawdown ≤ 5% + FillRecorder.insert_fill writes successful (idempotent on duplicate exec_id)
- **IF zero trades:** structural criteria only; FillRecorder live-path validation carried forward к S13
- **Operator sign-off** (qualitative "no surprises")

### Halt response + rollback (Q7)

**T5: Halt-response operational protocol**
- **Wake immediately on P0 halt** (CRITICAL severity — open position concealment risk)
- **Rollback target:** `v0.1.0-alpha.11` (revert merge commit, preserves operator infrastructure)
- **RC tag iteration:** `v0.1.0-alpha.12-rc.1`, `-rc.2`, ... до final `v0.1.0-alpha.12`
- **Zero new migrations constraint** (S12 plan-level commitment) — preserves alpha.11 binary rollback compatibility on S12 schema DB
- **Operator briefing addendum:** P1 `HALT_EXCHANGE_OUTAGE` + bot in `OCO_ARMED` state → escalate к CRITICAL per `halt-recovery.md` conditional escalation rule

### Cross-cutting concerns (binding)

- **C1 (Q4+Q5 ordering):** Q4 `_load_ohlcv` shim BEFORE Q5 FillRecorderAdapter; both BEFORE 48h validation window opens. Plan task order enforces.
- **C2 (Q5+Q3 conditional):** Zero signals likely on 1H BTC EMA crossover during 48h. FillRecorder live-path validation conditional. Q3 zero-trade clause mandatory.
- **C3 (Q6 corrected wiki):** SPRINT_STATE C1 carry-over note CORRECTED before PHASE 3 plan author reads. Endpoint routing UNCHANGED in S12.
- **C4 (Q7 schema constraint):** Zero new migrations in S12 (Q5 reuses S9 `trade_fills`). Hard constraint, NOT preference.

### Reviewer matrix

- **T1 (FillRecorderAdapter):** trading-logic-reviewer (fill event semantics + parent_trade_id race conditions) + data-integrity-reviewer (SQLite write + UNIQUE INDEX idempotency on exec_id)
- **T2 (Parquet shim):** python-reviewer (config dict translation correctness)
- **T3-T5 (validation run + protocol):** maintainer + operator (live execution oversight)

## Consequences

**Plus:**
- Bot validated end-to-end на Bybit demo (first live cycle since `_cmd_run` STUB closed S11)
- FillRecorder production wiring closes S11 T2 deferral — fill audit available для post-mortem
- `_cmd_wfa` actually usable (Gate 5 of pre-flight no longer broken)
- Operator infrastructure (S11) exercised against real failure modes
- Migration of S11 carry-over correction prevents future regression (Q6 endpoint string)

**Minus:**
- Demo synthetic fills NOT replicate Mainnet liquidity/slippage — slippage model validation deferred к S13+
- 48h × 1H bars = 48 samples — likely 0-3 trades, FillRecorder live-path validation likely incomplete (carry-forward к S13 conditional waiver)
- Operator burden (5min monitoring × 48h supervised window OR 2-person rotation)
- 3-way endpoint enum (full DEMO/TESTNET/MAINNET routing) deferred к S13+

**S13 carry-overs (anticipated):**
- 3-way endpoint enum routing refactor (Q6 future fix)
- FillRecorder live-path validation re-run (если S12 0 trades)
- Slippage model real-fill validation (Mainnet pilot)
- DSR threshold calibration (S15+ per S11 Q5 verdict — needs ≥30 trades)
- Per-fold DSR DataFrame→TradeRecord conversion (informational, deferred от S10)

## Related

- [[../pre-s12-backlog]] — PHASE 2 verdicts trail с trader source claims verified
- [[0026-sprint-11-operator-readiness]] — predecessor sprint (operator infrastructure consumed)
- [[0022-sprint-8a-live-runtime]] — RuntimeManager + threading lock policy
- [[0021-sprint-7-resilience]] — 4-valued reconciler + γ halt persistence
- [[0016-bybit-spot-supersedes-binance]] — Bybit V5 endpoint family + demo trading mode
- [[../runbooks/pre-flight]] — operator entry criteria (Gate 5 update post-T2)
- [[../runbooks/halt-recovery]] — priority matrix (P0 wake criteria)

## Amendments

- (none yet)
