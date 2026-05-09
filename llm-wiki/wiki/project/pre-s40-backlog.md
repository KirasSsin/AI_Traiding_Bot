---
title: Pre-S40 Backlog — S39 PHASE 6 deferred items + post-Gate 2 carry-overs
type: backlog
tags: [pre-sprint, sprint-40, deferred, post-s39-review, ru]
created: 2026-05-09
updated: 2026-05-09
status: active
sources:
  - llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
  - llm-wiki/wiki/project/sprints/sprint-39-volume-breakout-tech-debt.md
---

# Pre-S40 Backlog

Items deferred из S39 PHASE 6 review + post-S38 carry-overs не закрытые в S39.

## Из S39 PHASE 6 review (deferred — non-blocking)

### MEDIUM (S40 candidates)

| ID | Источник | Описание |
|----|----------|----------|
| **R3 C3** | trading-logic | place_order retry на 170213 (duplicate orderLinkId) propagates как BybitAPIError(FILTER_VIOLATION) — verify coordinator handles как non-fatal idempotent success. Нужен coordinator-level test. |
| **R4** | bybit-api | BybitMarketAdapter missing `__repr__` redaction — добавить consistency с BybitPrivateWSConsumer |
| **R6 vacuous-pass** | test-engineer | T3-03/T3-05/T3-06 conditional assertions могут pass silently. Add sentinel assertions ИЛИ deterministic signal setup. |
| **R6 6 coverage gaps** | test-engineer | (1) Coordinator-layer rate-limit retry test (2) dead_ws_triggers_halt path (3) M1 retCode taxonomy 10001/10010/170132 (4) M2 malformed response KeyError vs BybitAPIError (5) atr_stop_mult config wiring test (6) (см sprint-38 Test gaps section) |

### LOW (housekeeping)

| ID | Описание |
|----|----------|
| R4 docstring | `_retry_with_backoff` docstring mentions `RATE_LIMIT_HIT` reason — но raises с retCode=10006. Fix docstring OR add RATE_LIMIT_HIT к ReasonCode enum |
| R6 pytest.ini | `property` mark unregistered — add к pytest.ini markers section |
| **G6** | donchian_runner N_TRIALS_LOCKED=5 → должно быть 8 post-S39 (R2 C3) |

## Из ADR-0059 deferred sections

| ID | Описание |
|----|----------|
| **G1** | Dual execution kernel unification (volume_breakout_runner + replay_engine) — будет first production strategy с clean integration path |
| **G2** | Dashboard schema discriminator wired в frontend (currently backend-only) |
| **G5** | N_trials runtime gap для Gate 2 DSR — design decision |

## Carry-overs из BACKLOG.md (S38 origin, не закрытые в S39)

| ID | Описание |
|----|----------|
| **M1** | retCode taxonomy gaps (10001 + 110001 + 170131 + 170132 + 170134) |
| **M2** | pybit response-shape direct access (defensive guards needed) |
| **12mo MAINNET ADR** | Draft trigger n=10 first non-NaN DSR |

## NOT в S40 scope (frozen, requires separate ADR)

- ATR filter augmentation (per Q9 EXPAND→Option A defer) — pre-registered hypothesis в отдельном sprint
- Multi-symbol live runtime fan-out (S15 deferred MVP scope)
- Capital allocation cross-symbol exposure caps
- ML XGBoost / HMM regime-switch (v0.7+)
- FillRecorderAdapter Layer 2 (entry_signal_id schema migration — S12 carry-over, no MAINNET priority)

## Recommendation для S40

**Priority order:**

1. **HIGH** — close test debt (R6 vacuous-pass + 6 coverage gaps) перед next strategy hypothesis testing
2. **MEDIUM** — M1+M2 bybit-api hardening + R4 BybitMarketAdapter __repr__ + R3 C3 coordinator test
3. **LOW** — G1 dual kernel unification (только если volume_breakout Gate 2 PASS — иначе deprecated)
4. **LOW** — G6 donchian_runner stale constant

**Triggers для S40 brainstorm:**

- IF Gate 2 PASS (N≥10 forward signals positive) → S40 = MAINNET-promotion ADR draft + dual-kernel unification
- IF Gate 2 FAIL → S40 = 10-th honest close ADR (per ADR-0059 fallback clause)
- IF Gate 2 ongoing → S40 = test debt cleanup + bybit-api M1/M2 + 6 coverage gaps (waiting for δ data)
