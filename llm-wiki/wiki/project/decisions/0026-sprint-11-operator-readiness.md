---
title: 0026. Sprint 11 — Operator-readiness + pre-flight gap closure
type: decision
date: 2026-04-25
sprint: 11
tags: [adr, sprint-11, operator-readiness, cli, monitoring, di-wiring, halt-priority]
sources:
  - project/pre-s11-backlog.md
  - project/decisions/0016-binance-spot-testnet-mvp.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
status: accepted
---

# 0026. Sprint 11 — Operator-readiness + pre-flight gap closure

**Status:** accepted
**Date:** 2026-04-25

## Context

Sprint 11 closes pre-flight gaps blocking live execution + ships operator infrastructure:
- `_cmd_run` STUB since S8a T20 deferral — bot не runnable end-to-end через `python -m src run`
- `_cmd_reconcile_only` STUB since same source
- WFA shipped S10 но не exposed как CLI subcommand
- test_risk_flow.py failing с OverrideStore signature drift since S4 era
- halt-recovery.md (S8c PR-γ) covers 19 codes но без priority/escalation index
- No operator-friendly state snapshot tool

PHASE 2 brainstorming verdicts (`pre-s11-backlog.md`):
- Q1 CONFIRM: A-first (operator-readiness), F (Live demo Mainnet) deferred к S12
- Q2 CONFIRM: bundle pre-flight gaps в S11 P0
- Q3 REVISE: integrate halt priority matrix INTO halt-recovery.md (NOT separate dashboard)
- Q4 CONFIRM: F params validated for S12 (Bybit demo + 48h + $1000 virtual)
- Q5 CONFIRM: defer DSR threshold calibration к S15+ (need 30+ trades)
- Q6 CONFIRM: 1-test fix + audit для other S4-era drift
- Q7 CONFIRM + addition: architecture-reviewer MANDATORY для _cmd_run

## Decision

### P0 pre-flight (Q2)

Bundle 4 tasks BEFORE A scope deliverables:
- T1 (`afb5760`): test_risk_flow.py — restore `OverrideStore(path, hmac_key=settings.risk_override_hmac_key)` signature + add fixture hmac_key
- T2 (`ead6dca` + `d7b196f`): `_cmd_run` DI wiring — Settings → REST client → BybitFilters → market adapter → DB → state repo → reconciler → coordinator → bar source → strategy → risk manager → WS consumer → RuntimeManager.run(). FillRecorder = `_NoopFillRecorder` stub (production wiring deferred S12+).
- T3 (`bb8cba9` + `e4df4cd`): `_cmd_reconcile_only` wiring — subset of T2 DI graph (Coordinator + Reconciler only).
- T4 (`6e1fff2`): `_cmd_wfa` subcommand — wires WindowSplitter + WalkForwardRunner + sign_flip_p_value + evaluate_acceptance_gate + format_wfa_report. Exit 0 = pass, 2 = fail, 1 = error.

architecture-reviewer T2 verdict: SOUND. 3 concerns identified (1 fixed inline, 2 deferred к S12).

### A scope — Operator-readiness (Q3 REVISE)

Per Q3 trader REVISE accepted: integrate priority matrix INTO `halt-recovery.md` (NOT separate file — single source of truth).

- T5 (`0b57062`): Extended `halt-recovery.md`:
  - NEW "Priority matrix" section (P0/P1/P2 tiers)
  - Extended Quick Reference Table с "On-call escalation" column (19 codes mapped)
- T6 (`26f7b68`): NEW `wiki/project/runbooks/log-grep-templates.md` — structlog jq filters + halt_log SQL queries
- T7 (`281896e`): `_cmd_monitor` CLI — read-only state snapshot. STRICTLY read-only per C2 (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`). Test enforces no DB mtime change.
- T8 (`92c37b9`): NEW `wiki/project/runbooks/pre-flight.md` — operator checklist (5 critical gates + 4 recommendations + post-start monitoring + halt response).

### Cross-cutting concerns (binding)

- **C1:** `_cmd_run` DI wiring real risk. architecture-reviewer mandatory. Pre-plan DI feasibility read-pass verified constructors aligned (no mini-ADR needed). T2 architecture verdict: SOUND.
- **C2:** `_cmd_monitor` strictly read-only. Implementation uses SQLite `?mode=ro` URI. T7 test enforces no DB mtime change.
- **C3:** WFA CLI bundled с P0 (T4) но не blocked A scope parallel.

## Consequences

**Plus:**
- Bot runnable end-to-end через `python -m src run` (closes 8-month-old S8a T20 STUB)
- Operator infrastructure ready для S12 F live demo Mainnet validation
- Single source of truth для halt priority (no dashboard drift)
- Pre-flight checklist enforces config gate validation before live start
- WFA accessible как CLI subcommand для on-demand baseline

**Minus:**
- FillRecorder stub в `_cmd_run` (production wiring deferred S12+) — fills logged but не persisted
- `_load_ohlcv` stub в `_cmd_wfa` (S12 F integrates real data path)
- Per-fold DSR в reporter still NaN (DataFrame→TradeRecord conversion deferred)
- DSR threshold gate calibration deferred к S15+ (need empirical data)
- **S12 carry-overs from architecture-reviewer T2 concerns:**
  - **C1 (T2 review):** `endpoint = "demo.bybit.com" if testnet else "stream.bybit.com"` — pybit derives `testnet`/`demo` flags from substring match. Current string sets `demo=True, testnet=False` (correct для S11 demo trading intent но semantically wrong для Bybit testnet). Fix to use string containing "testnet" substring (e.g., `"stream-testnet.bybit.com"`) when actual testnet validation needed.
  - **C3 (T2 review):** `init_db` opens own internal connection separate from `connect()` returned conn. WAL mode safe but worth code comment.

## Related

- [[../pre-s11-backlog]] — PHASE 2 verdicts trail
- [[0016-binance-spot-testnet-mvp]] — testnet MVP gating + Phase G mention
- [[0022-sprint-8a-live-runtime]] — RuntimeManager origin + T20 STUB deferral closed by T2
- [[0025-sprint-10-wfa-dsr-mc]] — WFA components consumed by T4 _cmd_wfa
- [[../runbooks/halt-recovery]] — extended с priority matrix (T5)
- [[../runbooks/log-grep-templates]] — NEW (T6)
- [[../runbooks/pre-flight]] — NEW (T8)
- [[../plans/2026-04-25-sprint-11-operator-readiness]] — implementation plan + trace map

## Amendments

- (none yet)
