---
title: Pre-S12 backlog — brainstorm verdicts trail
type: backlog
tags: [sprint-12, brainstorm, phase-2, verdicts, trader-expert, live-demo, mainnet-validation]
created: 2026-04-25
updated: 2026-04-25
status: open
sources:
  - project/decisions/0016-bybit-spot-supersedes-binance.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0026-sprint-11-operator-readiness.md
  - project/sprints/sprint-11-operator-readiness.md
  - project/runbooks/pre-flight.md
---

# Pre-S12 backlog — PHASE 2 brainstorming trail

## S12 scope hypothesis (maintainer-locked, awaiting trader confirmation)

**S12 = F = Live demo validation 24-72h** per S11 Q1 trader CONFIRM (deferred from S11 A scope).

S12 deliverables hypothesis:
1. **Production wiring** — close `_NoopFillRecorder` stub (replace с `FillHistoryRepository` DB-backed), close `_load_ohlcv` empty df stub в `_cmd_wfa`
2. **C1 endpoint string fix** (S11 T2 review carry-over) — `"demo.bybit.com"` → semantically correct testnet substring routing
3. **C3 init_db dual-conn comment** (S11 T2 review carry-over) — code comment explaining 2-connection sequence
4. **Live demo run** — 24-72h Bybit demo BTCUSDT 1H validation per pre-flight.md gates
5. **Validation report** — fail modes traced + halts + reason code distribution
6. **Halt-recovery validation** — real halt invocation tests (P0 codes per S11 priority matrix)

## Carry-overs from S11 (informing scope)

- **F (Live demo Mainnet 24-72h validation)** — main S12 scope (per Q1 S11 trader CONFIRM)
- **FillRecorder production wiring** — currently `_NoopFillRecorder` stub в `_cmd_run`
- **`_load_ohlcv` production integration** в `_cmd_wfa` — currently empty df stub
- **T2 review C1 endpoint string fix** — `"demo.bybit.com"` semantically wrong для testnet (pybit substring match)
- **T2 review C3 init_db dual-conn comment** — `init_db` opens internal connection separate от `connect()` returned conn
- **Per-fold DSR DataFrame→TradeRecord conversion** (informational, deferred S10) — out of scope S12
- **DSR threshold calibration** (S15+ per Q5 verdict) — deferred, needs ≥30 empirical trades

## S12 PHASE 2 brainstorming questions (7 questions)

### Q1 — Demo trading vs live mainnet с small capital

**Question:** Use Bybit demo trading endpoint (virtual capital, no real PnL exposure) OR live mainnet с tight capital cap ($50-$100, real PnL but minimal blast radius)?

**Maintainer recommended option:** Bybit demo trading (S11 Q4 trader pre-confirmed)

**Alternatives considered:**
- (a) Bybit demo trading — virtual capital, zero real loss, full V5 endpoint behavior
- (b) Live mainnet $50 cap — real fills + slippage realism, but PnL exposure
- (c) Live mainnet $1000 cap — closer to production sizing, larger blast radius

**Reasoning for recommended:**
- ADR 0016 explicit: "testnet MVP gating" — live Mainnet после Phase G testnet probes pass
- pre-flight.md Gate 1: `live_trading=True requires testnet=False AND trading_enabled=True` — invariant safeguards real-money path
- Bybit demo == V5 endpoint family (matches production code path), NOT separate testnet code
- v0.1 not production-grade yet (no full E2E shake-down) → real PnL premature
- S11 Q4 already pre-validated: demo + 48h + $1000 virtual baseline

**Risk/concern:**
- Demo может NOT replicate real liquidity/slippage (synthetic order book) → false negatives на real-fill issues
- HIDDEN ASSUMPTION: pybit treats demo endpoint identically to mainnet for code coverage purposes
- If demo synthetic fills are too friendly → undetected slippage model bugs surface only on Mainnet

---

### Q2 — Validation duration (24h / 48h / 72h)

**Question:** Validation run duration: 24h (1 calendar day), 48h (2 days, captures weekend boundary), OR 72h (3 days, multiple regime transitions)?

**Maintainer recommended option:** 48h (S11 Q4 trader pre-confirmed)

**Alternatives considered:**
- (a) 24h — minimum coverage, may miss intraday regime shifts (~24 1H bars)
- (b) 48h — captures 2 trading sessions + weekend transition (~48 bars)
- (c) 72h — multi-day regime variance (~72 bars), more halt opportunities

**Reasoning for recommended:**
- 1H timeframe → 48h = 48 bars (sample size adequate для seeing on_bar/strategy behavior)
- 2-day window covers Asian + EU + US session boundaries
- Operator burden моderate (1 weekend, supervised)
- S11 Q4 trader pre-confirmed 48h baseline

**Risk/concern:**
- 48 bars = small statistical sample (likely 0-3 trades from EMA crossover strategy)
- Не enough trades for DSR/MC validation → defer DSR confidence к S15+
- Если validation = 0 trades (no signal during 48h) → inconclusive, may need re-run

---

### Q3 — Validation success criteria framework

**Question:** What constitutes "S12 validation PASSED"? (1) Zero halts? (2) Configurable halt threshold? (3) PnL bounded? (4) Reason code coverage?

**Maintainer recommended option:** Multi-criteria gate: zero P0 halts (CRITICAL per S11 priority matrix) + reconcile divergence count = 0 + drawdown ≤ 5% (если any trades) + manual operator sign-off

**Alternatives considered:**
- (a) Strict: zero halts of any class — too aggressive (P2 halts могут fire during normal operation)
- (b) **Multi-criteria recommended** — zero P0 + reconcile clean + drawdown bounded + operator review
- (c) Loose: only operator sign-off — too subjective, drift risk
- (d) Statistical: DSR threshold met — premature (S15+ deferred)

**Reasoning for recommended:**
- P0 priority codes (per S11 T5 priority matrix) = "incorrect manual recovery can create or conceal open position"
- Reconcile divergence = primary integrity check (ADR 0021 4-valued verdict)
- Drawdown bound aligns с L1 (15% warn) circuit breaker — much tighter for validation
- Operator sign-off captures qualitative "no surprises" — matches v0.1 manual-validation paradigm
- Multi-criteria avoids single-point-of-failure judgment

**Risk/concern:**
- Subjective "no surprises" hard to falsify → may rationalize away real issues
- Если 0 trades during 48h (likely scenario) → most criteria N/A, validation degenerates к "nothing crashed" test
- HIDDEN ASSUMPTION: P0/P1/P2 classification correct — relies on S11 T5 trader REVISE accepted

---

### Q4 — Data path integration (`_load_ohlcv` real source)

**Question:** Real data path для `_cmd_wfa` `_load_ohlcv`: (1) Parquet pre-fetch via existing `data_collector` (S2-era), (2) Live REST kline pagination, (3) New DB-backed historical store, OR (4) Defer integration к S13?

**Maintainer recommended option:** Reuse existing `data_collector` Parquet pre-fetch path (option 1)

**Alternatives considered:**
- (a) **Parquet via data_collector reuse** — existing S2 component, snappy compression, fast WFA iteration
- (b) Live REST kline pagination — every WFA invocation hits Bybit API (slow + rate-limit risk)
- (c) New DB-backed store — overengineering для v0.1, duplicates Parquet purpose
- (d) Defer к S13 — leaves `_cmd_wfa` stub-broken (exit 1 per S11 NOTE)

**Reasoning for recommended:**
- `data_collector.py` (S2 component) — battle-tested, used by replay engine
- Parquet snappy = persistent local cache, no network roundtrip
- WFA = analytical tool, не needs realtime
- pre-flight Gate 5 (`_cmd_wfa` recommended check) — currently fails с "empty df warning" → Parquet wire fixes operator UX
- Reuse > rebuild (DRY)

**Risk/concern:**
- Parquet must contain symbol+timeframe range matching CLI args — operator gap if missing
- HIDDEN ASSUMPTION: data_collector API still works post-S2 (may have signature drift)
- May need separate `python -m src backfill --start --end` invocation BEFORE wfa — operator workflow burden

---

### Q5 — FillRecorder production wiring strategy

**Question:** Replace `_NoopFillRecorder` stub в `_cmd_run`: (1) Direct `FillHistoryRepository` DB-backed instance в constructor, (2) Lazy-init pattern с config flag (`fill_persistence_enabled: bool`), (3) Composite (DB + JSONL audit log mirror)?

**Maintainer recommended option:** Direct `FillHistoryRepository` DB-backed instance (option 1)

**Alternatives considered:**
- (a) **Direct DB-backed FillHistoryRepository** — closes stub, leverages S9 Q3 B1 schema (`trade_fills` table + WS execution dispatch)
- (b) Lazy-init с config flag — overengineering (when would operator disable fill persistence?)
- (c) Composite DB+JSONL — premature redundancy, adds disk I/O complexity

**Reasoning for recommended:**
- `FillHistoryRepository` already exists (S9 Q3 B1 component, `src/risk/fill_history.py`)
- WS dispatch already wired (S9 Q3 B1 `_FillRecorderProto.on_fill_event`) — drop-in replacement для stub
- DB-backed = SHA-256 chain audit (S9 Q3 B1 component invariants)
- pre-flight.md Gate 4 implicitly requires fill audit для operator post-mortem
- Removes "deferred S12+" comment в `_cmd_run` (T2 implementation note)

**Risk/concern:**
- DB write latency on hot path (each fill → SQLite write) — могут degrade tick loop tail latency
- HIDDEN ASSUMPTION: FillHistoryRepository signature matches `_FillRecorderProto.on_fill_event(evt: dict)`
- WAL contention если `_cmd_monitor` running concurrently (mitigated S11 C2 `?mode=ro`)

---

### Q6 — C1 endpoint string fix priority + scope

**Question:** S11 T2 review C1 endpoint string fix (`"demo.bybit.com"` → testnet substring): (1) Bundle as S12 P0 (must-fix before validation), (2) Separate tooling commit (deferrable), (3) Scope-creep к WS endpoint refactor?

**Maintainer recommended option:** P0 (option 1) — must-fix before live demo validation

**Alternatives considered:**
- (a) **P0 bundle in S12** — semantically correct routing required before live data path exercises pybit
- (b) Separate tooling commit — leaves S12 demo running on questionable endpoint
- (c) Refactor scope-creep — change endpoint resolution к Settings-driven enum (Mainnet/Demo/Testnet) — overengineering

**Reasoning for recommended:**
- pybit substring match `"testnet"` vs `"demo"` определяет request routing (per S11 T2 review C1 docs)
- Currently `"demo.bybit.com"` sets `demo=True, testnet=False` — correct for S11 _intent_ (demo trading)
- НО WS endpoint в `BybitPrivateWSConsumer` (если exists similar) могут has own routing → check
- Validation runs against demo → endpoint routing correctness affects EVERY API call observed
- Fix scope: 1 file edit + test assertion (substring "testnet" present) — trivial

**Risk/concern:**
- HIDDEN ASSUMPTION: only WS endpoint affected — REST may be separate
- Если refactor required across REST+WS+adapter → scope creep
- Without fix: S12 validation could PASS на synthetic demo behavior, then FAIL silently on real Mainnet (option c risk realized)

---

### Q7 — Halt criteria + rollback plan during validation

**Question:** During 48h validation: (1) what halt fires → operator wakes immediately, (2) rollback target если showstopper found?

**Maintainer recommended option:** Wake immediately on any P0 halt (per S11 priority matrix) + rollback к v0.1.0-alpha.11 (revert merge commit, no data loss). Production wiring fixes ship as v0.1.0-alpha.12-rc.N tags.

**Alternatives considered:**
- (a) **P0-wake + rollback к alpha.11 + RC tag iteration** — clear severity threshold, atomic rollback
- (b) Wake on P0+P1 — more sensitive, but P1 = "RECOVERABLE" → unnecessary 3-AM wake
- (c) No halt-based wake (operator-initiated only) — too lax for first live validation
- (d) Rollback к alpha.10 (pre-S11) — loses operator infrastructure (halt-recovery, runbooks)

**Reasoning for recommended:**
- P0 = "incorrect recovery can create/conceal open position" → cannot ignore
- alpha.11 stable + has operator infrastructure (rollback target preserves S11 deliverables)
- RC tags (-rc.1, -rc.2 ...) communicate S12 work-in-progress vs final v0.1.0-alpha.12 ship
- Aligns с pre-flight.md "halt response" section + halt-recovery.md priority matrix

**Risk/concern:**
- Rollback assumes SQLite state survives revert (forward-only migrations + no destructive S12 schema changes)
- HIDDEN ASSUMPTION: S12 не add migrations (если adds → rollback breaks DB compatibility)
- HIDDEN ASSUMPTION: operator available 24/7 during validation window (may need 2-person rotation)

---

## ROUND 1 verdicts (TRADER-EXPERT, complete)

**Maintainer source-claim verification (CC1 lesson):** ALL trader claims grep-verified before acceptance:
- ✅ Q4 `data_collector.load_market_data(config: Dict[str, Any])` (config-dict API, NOT `(symbol,start,end)` args)
- ✅ Q4 `_load_ohlcv(*, symbol: str, start: str, end: str)` signature mismatch confirmed (`__main__.py:260`)
- ✅ Q5 `_FillRecorderProto.on_fill_event(self, evt: dict[str, Any]) -> None` (`ws_private.py:22-24`)
- ✅ Q5 `FillHistoryRepository.__init__(conn)` + `insert_fill(record: FillRecord) -> int` (no `on_fill_event` method)
- ✅ Q5 `FillRecord.parent_trade_id: int = Field(..., gt=0)` required + non-nullable
- ✅ Q6 `endpoint = "demo.bybit.com" if settings.testnet else "stream.bybit.com"` (`__main__.py:138`)
- ✅ Q6 `WebSocket(testnet="testnet" in self._endpoint, demo="demo" in self._endpoint, ...)` (`ws_private.py:65-67`)

**Q6 truth table verified:** `settings.testnet=True` → endpoint `"demo.bybit.com"` → pybit `testnet=False, demo=True` = correct demo trading routing. S11 carry-over "fix к contain testnet substring" was WRONG — would set `testnet=True, demo=False` (actual Bybit testnet env, not demo). Maintainer's S11 note is hereby CORRECTED.

| # | Question | ROUND 1 verdict | Type | Final accepted | Wiki/code follow-ups |
|---|----------|-----------------|------|----------------|----------------------|
| Q1 | Demo vs mainnet | **CONFIRM** | agree | Bybit demo trading (option a) | — |
| Q2 | Validation duration | **CONFIRM** | agree (с zero-trade clause) | 48h baseline (option b) | Q3 plan MUST include zero-trade clause |
| Q3 | Success criteria framework | **CONFIRM** | agree (с MANDATORY zero-trade clause) | Multi-criteria + zero-trade fallback | Plan MUST add: "If 0 fills: structural criteria only, FillRecorder validation carry-forward S13" |
| Q4 | `_load_ohlcv` data path | **REVISE-additive** | direction agree, scope expand | Parquet via shim + Gate 5 doc | Plan tasks: shim implementation + better error message + pre-flight Gate 5 update |
| Q5 | FillRecorder wiring | **REVISE-additive** | direction agree, scope expand | `FillRecorderAdapter` class wrapping FillHistoryRepository + parent_trade_id derivation | Plan tasks: adapter class + parent_trade_id derivation strategy + 2 reviewers (trading-logic + data-integrity) |
| Q6 | C1 endpoint fix scope | **REVISE-DISAGREE-FACTUAL** | maintainer wrong on action | NO endpoint change — current correct. 3-way enum deferred к S13+ | SPRINT_STATE C1 carry-over note CORRECTED. ROUND 2 N/A (factual correction, не engineering judgment dispute) |
| Q7 | Halt criteria + rollback | **CONFIRM** | agree (с 2 concerns added) | P0-wake + alpha.11 rollback + RC tags | Plan MUST commit "zero new migrations" OR provide downgrade SQL + operator briefing P1+OCO_ARMED escalation |

## Cross-cutting concerns (trader-flagged)

1. **Q4 + Q5 ordered dependency** — Q4 (WFA pre-run) before Q5 (live run). Both before 48h validation window opens. Independent code paths.
2. **Q5 + Q3 conditional на trade occurrence** — Zero signals likely on 1H BTC EMA crossover during 48h. FillRecorder live-path NOT exercised если 0 fills. Plan must surface conditional waiver.
3. **Q6 endpoint correction impacts SPRINT_STATE correctness** — Carry-over note must be corrected BEFORE PHASE 3 plan author reads it. Wiki/metadata hygiene blocker.
4. **Q7 schema migration constraint** — S12 must commit zero new migrations OR provide downgrade SQL для alpha.11 rollback compatibility. `trade_fills` table already exists (S9 migration), so Q5 adapter does NOT need new migration.

## Escalation list для user (product/regulatory/business)

**NONE.** All 7 questions технические, в engineering authority. No user-decision items.

(Trader explicit: "operator availability assumption (Q7) — deployment/operations preference, document в pre-flight.md, не escalate".)

## ROUND 2 status

**NOT INVOKED.** Three REVISE verdicts but NONE require iterative justify:
- Q4 + Q5 = additive scope refinement (direction agree, just needs shim/adapter — trader provided implementation guidance)
- Q6 = factual correction of misleading S11 carry-over (verifiable via source grep — maintainer accepts immediately, no engineering disagreement)

Per dev-workflow.md PHASE 2 step 5 letter spirit: ROUND 2 designed для "REVISE where chosen option != maintainer's recommendation" requiring deeper compare. Here trader provided source-cited evidence; maintainer verified directly. No engineering judgment to dispute.

## Maintainer follow-ups (post-verdict)

- ✅ Verify trader source claims via grep (CC1) — ALL VERIFIED
- ⏳ Correct SPRINT_STATE C1 carry-over note per Q6 trader REVISE
- ⏳ Draft ADR 0027 (status: proposed) с 7 verdicts + 4 cross-cutting concerns
- ⏳ Transition SPRINT_STATE phase=2-brainstorming → 3-planning

## Related

- [[decisions/0026-sprint-11-operator-readiness]] — predecessor ADR (S11 ship)
- [[decisions/0022-sprint-8a-live-runtime]] — RuntimeManager origin
- [[decisions/0016-bybit-spot-supersedes-binance]] — Bybit Spot venue + demo endpoint family
- [[runbooks/pre-flight]] — operator pre-flight gates (S12 entry criteria)
- [[runbooks/halt-recovery]] — priority matrix (P0/P1/P2 escalation chain)
- [[architecture/development-workflow]] — PHASE 2 binding protocol
