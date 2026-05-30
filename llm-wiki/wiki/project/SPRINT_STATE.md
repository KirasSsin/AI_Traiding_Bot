---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S51 D2 done (parquet SHA-256 sidecar manifest 6309e9b).
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
| D2 | parquet manifest/partition | S49 (data-integrity) | MEDIUM | **DONE** `6309e9b` — SHA-256 sidecar: кажый `append()` атомарно пишет `.sha256` (temp+os.replace). `verify_parquet(path)->bool` helper. 5 новых TDD тестов (RED→GREEN). Hive-партиционирование: YAGNI-deferral задокументирован в storage.md. |
| D3 | block_bootstrap edge-null | S49 (quant) | LOW | **DONE** `109462a` — docstring warning + gate-promotion guard test (AST-parse research_wfa assert sign_flip gate, not block_bootstrap). |
| D4 | atr_breakout windowed-ATR | S50 (trading-logic) | HIGH (shipped LOCKED) | **DONE** `00763c5` — ADR 0064 WFA использовал full-history vectorized ATR; live `on_bar` — windowed deque re-seed. MATERIAL (BTCUSDT 4H: stop ATR max 38.7% rel, 16 signal flips, 13 vs 9 entries). Fix: инкрементальный full-history ATR (`_WilderATR`, mirror S50 Supertrend), [-2] индексация и entry/exit семантика сохранены. Parity test 1e-9 GREEN, mypy 0. **NEW FOLLOW-UP flagged** (вне D4 scope): ATR-index offset — live оценивает breakout на бар позже (atr[-2]/close[-2] vs research data-through-i-1) → 9 vs 28 entries; нужно отдельное решение про streaming↔backtest signal-bar parity. См. ADR 0064 «Открытый follow-up». |
| D5 | cross_trial pool contamination | S50 (quant+trader) | MEDIUM | **DONE** — two-level scoping (trader verdict e): sigma_SR per-strategy-class (within-class stdev, eq.13), N_trials GLOBAL (eq.12, anti-snooping). +strategy_class field, INSUFFICIENT_CLASS_HISTORY fallback, 4 runners wired, ADR 0056 amend. +17 tests, mypy clean. |
| D6 | supertrend_runner _backtest_single numerical test | S50 (test-engineer) | LOW (gated) | **DONE** `02e775a` — 5 parity tests (GBM×3 seeds, zero-flip, MTM close), all GREEN. _backtest_single PnL matches streaming reference within 1e-9. No src bugs found. |

## Phase tracking (S51)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | post-S50 ship |
| 2 Brainstorm | skipped | bugfix sprint, debts known (D5 trader-expert verdict e only) |
| 3 Plan | done | writing-plans 6-debt plan `5a7c044` |
| 4 Execute | done | D1-D6 committed (24248be/6309e9b/109462a/00763c5/ac79531/02e775a) |
| 5 Verify | done | pytest 1449 / mypy 0/91 GREEN |
| 6 Review | done | 6 reviewers: bybit/python/test-eng/data-integrity/trading-logic APPROVE + quant APPROVE_WITH_CONCERNS → doc-fix `fac2b15` |
| 7 Sync | done | sprint-51 page + index + log + current-state + ADR 0056/0064 amend |
| 8 Ship | in_progress | tag v0.1.0-alpha.51 — PR + merge |
| 9 Close | pending | — |

## Следующее действие

**S51 ship:** PR → squash-merge → tag `v0.1.0-alpha.51`. Затем **S52 = Kronos ML strategy** (operator-scoped: foundation model K-line forecast, Mac M4 Pro MPS, validation→trader-expert brainstorm).

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
