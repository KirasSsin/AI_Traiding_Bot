---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S51 D6 done (supertrend_runner parity test).
sprint: 51
phase: 3-planning
branch: main
tag: v0.1.0-alpha.50
---

## Текущий статус

**S50 SHIPPED** — squash-merge `81d4bc7` (PR #61), tag `v0.1.0-alpha.50`. Supertrend hypothesis #10 WFA_FAIL (honest), reusable infra landed, BLOCKER look-ahead fixed. Детали → `sprints/sprint-50-supertrend.md`.

**S51 = debt-closing sprint** (operator decision: «все долги»). 6 carry-overs (3 S49 + 3 S50). Bugfix-сприн — kit lite (баги известны, brainstorm не нужен; trader-expert только для D5 pool-scoping policy если judgment нужен).

## S51 scope — 6 debts

| # | Debt | Source | Severity | Fix |
|---|------|--------|----------|-----|
| D1 | 110072 dup-order retCode | S49 (bybit re-review) | HIGH (pre-mainnet) | **DONE** — 110072→REJECT_DUPLICATE_ORDER (bybit-local enum, canonical 65 unchanged). Flatten paths (_handle_sl_partial residual + _try_place_market_sell emergency) catch BybitAPIError, pin retCode==110072 → success (idempotency complete, no spurious HALT). Mirrors 110001 pattern. RED→GREEN; genuine-error guard still HALTs. |
| D2 | parquet manifest/partition | S49 (data-integrity) | MEDIUM | SHA-256 manifest + document flat-filename layout. OR honest "deferred" ADR note if scope-heavy. |
| D3 | block_bootstrap edge-null | S49 (quant) | LOW | **DONE** `109462a` — docstring warning + gate-promotion guard test (AST-parse research_wfa assert sign_flip gate, not block_bootstrap). |
| D4 | atr_breakout windowed-ATR | S50 (trading-logic) | HIGH (shipped LOCKED) | live/backtest parity check: did ADR 0064 WFA use streaming on_bar OR vectorized? If divergent → ADR note + (maybe) incremental-ATR fix mirroring S50 Supertrend. |
| D5 | cross_trial pool contamination | S50 (quant+trader) | MEDIUM | ADR-decision: per-strategy-class pool scoping (mixing S44 ATR + S50 Supertrend over-penalizes DSR). trader-expert verdict. |
| D6 | supertrend_runner _backtest_single numerical test | S50 (test-engineer) | LOW (gated) | **DONE** `02e775a` — 5 parity tests (GBM×3 seeds, zero-flip, MTM close), all GREEN. _backtest_single PnL matches streaming reference within 1e-9. No src bugs found. |

## Phase tracking (S51)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | post-S50 ship |
| 2 Brainstorm | skipped | bugfix sprint, debts known (D5 may need trader-expert mini-verdict) |
| 3 Plan | in_progress | writing-plans for 6 debts |
| 4-9 | pending | — |

## Следующее действие

**S51 PHASE 4** — D1 (110072 dup-order) DONE, D3+D6 DONE. Осталось: D4 (atr_breakout parity, highest priority shipped code), D2 (parquet manifest), D5 (cross_trial pool scoping, trader-expert verdict).

## S52+ ROADMAP

- NEW strategy hypothesis #11 (operator-driven). ADX-filter Supertrend reconsidered (pure FAILED). OR fresh strategy class.
- Permanently deferred: 12mo MAINNET ADR / live trade feed widget / M4 __repr__ redaction.

---

## История спринтов (где искать)

**SPRINT_STATE — only current sprint.** History distributed:
- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint (primary lookup "что было в SN")
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history table + canonical counts
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
