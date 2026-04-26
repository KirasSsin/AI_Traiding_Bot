---
name: S12 brainstorm Round 1 verdicts
description: Binding verdicts for S12 PHASE 2 brainstorm Q1-Q7 — 2026-04-25 (live demo validation, FillRecorder, data path, endpoint fix)
type: project
---

**Date:** 2026-04-25. Sprint S12 brainstorm round 1.

Q1 (demo vs mainnet): CONFIRM — Bybit demo trading correct. ADR 0016 MVP gating. v0.1 never executed a live order. Demo = structural validation, not trading edge confirmation.

Q2 (48h duration): CONFIRM — pre-confirmed from S11 Q4. 48 bars adequate for structural validation. Zero trades expected and acceptable for S12 scope.

Q3 (success criteria framework): CONFIRM multi-criteria gate (zero P0 halts + reconcile divergence=0 + drawdown ≤5% + operator sign-off). CRITICAL ADDITION: must add explicit zero-trade outcome clause ("if 0 fills: structural criteria only, trading criteria waived"). Without this clause, sign-off is ambiguous.

Q4 (_load_ohlcv data path): REVISE — Parquet via data_collector correct in destination but NOT a drop-in. data_collector.load_market_data(config: Dict) takes config dict, NOT (symbol, start, end) args. A thin shim translating CLI args → config dict is required in _load_ohlcv. Also: operator must pre-fetch Parquet before running wfa (FileNotFoundError otherwise). Pre-flight Gate 5 must document this prerequisite.

Q5 (FillRecorder wiring): REVISE — FillHistoryRepository is NOT a drop-in replacement for _NoopFillRecorder. Interface mismatch confirmed by source:
- _FillRecorderProto requires on_fill_event(evt: dict) -> None (ws_private.py:22-24)
- FillHistoryRepository exposes insert_fill(record: FillRecord) -> int (fill_history.py:39-42)
A FillRecorderAdapter class is required: on_fill_event(evt) → parse WS execution event → build FillRecord → call insert_fill(). Additional complexity: parent_trade_id must be derived from coordinator state (not in WS event). Reviewers: trading-logic + data-integrity mandatory.

Q6 (C1 endpoint fix): CONFIRM P0 priority but REVISE scope. Current "demo.bybit.com" is CORRECT for S12 demo trading via substring logic in ws_private.py:66-67 ("testnet" in "demo.bybit.com"=False, "demo" in "demo.bybit.com"=True → demo=True, testnet=False). The SPRINT_STATE carry-over note "fix to contain testnet substring" would BREAK S12 demo connectivity. The real fix needed is a 3-way endpoint enum (DEMO/TESTNET/MAINNET) for future testnet use — but NOT a P0 blocker for S12 itself. SPRINT_STATE carry-over C1 note must be corrected to avoid regression.

Q7 (halt criteria + rollback): CONFIRM P0-wake + alpha.11 rollback + RC tags. Critical hidden risk: if S12 adds DB migrations, rollback to alpha.11 code may fail on S12 schema. Plan must either (a) add no migrations OR (b) document downgrade SQL. Secondary: P1 HALT_EXCHANGE_OUTAGE during OCO_ARMED state after >1H becomes de-facto CRITICAL per halt-recovery.md — operator briefing must include this escalation path.

**Cross-cutting:**
- Q4+Q5: ordered dependency (WFA validates fitness BEFORE live run, FillRecorder operates DURING). No overlap but ordering matters.
- Q5+Q3: FillRecorder untested if 0 trades. Must be noted as conditional in success criteria.
- Q6: current 2-value settings.testnet bool cannot represent 3 routing modes. ADR 0027 consequences should note this as future breaking change if actual testnet needed.
