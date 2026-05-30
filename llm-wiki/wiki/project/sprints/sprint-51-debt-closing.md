---
title: "Sprint 51 — Debt Closing (6 carry-overs: 3 S49 + 3 S50)"
type: sprint
tags: [sprint-51, debt-closing, bugfix, bybit-110072, parquet-manifest, block-bootstrap, atr-parity, dsr-pool-scoping, supertrend-parity]
created: 2026-05-30
updated: 2026-05-30
status: completed
sources:
  - llm-wiki/wiki/project/plans/2026-05-29-sprint-51-debt-closing.md
  - llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md
---

# Sprint 51 — Debt Closing

## Обзор

Bugfix-спринт: закрыты 6 carry-over долгов (3 из S49 tech-audit + 3 из S50 Supertrend). Operator decision «все долги». Kit lite (баги известны, brainstorm не нужен; trader-expert ROUND 1 только для D5 pool-scoping policy). Тег `v0.1.0-alpha.51`.

**Baseline (post-S50):** pytest 1414 / mypy 0 / reason_codes 65.
**Post-S51:** pytest **1449** / mypy 0/91 / reason_codes **65 UNCHANGED** (D1 добавил код в bybit-local enum `src/execution/bybit/errors.py`, не в canonical `src/risk/reason_codes.py`).

## Долги закрыты

| # | Debt | Источник | Решение | Commit |
|---|------|----------|---------|--------|
| **D1** | Bybit retCode 110072 (OrderLinkedID duplicate) → UNKNOWN_ERROR → spurious HALT | S49 bybit | 110072 → `REJECT_DUPLICATE_ORDER` (bybit-local enum 9→10). Flatten paths double-pin `ret_code==110072 AND reason is REJECT_DUPLICATE_ORDER` → success (idempotency complete). Mirrors 110001. | `24248be` |
| **D2** | parquet manifest отсутствует | S49 data | SHA-256 sidecar atomic temp+os.replace + `verify_parquet()`. Hive partitioning deferred YAGNI. | `6309e9b` |
| **D3** | `block_bootstrap_p_value` не edge-null | S49 quant | Docstring WARNING + AST-parse guard test (research_wfa imports sign_flip NOT block_bootstrap). Math untouched. | `109462a` |
| **D4** | atr_breakout windowed-ATR re-seed (SHIPPED LOCKED) | S50 trading | ADR 0064 WFA = full-history vectorized; live = windowed deque re-seed. MATERIAL (BTCUSDT 4H: stop ATR max 38.7% rel, 16 signal flips). Fix: инкрементальный `_WilderATR`, [-2] indexing сохранён, parity 1e-9. | `00763c5` |
| **D5** | DSR cross-trial pool contamination | S50 quant+trader | trader verdict (e) two-level: sigma_SR per-class (eq.13), N_trials global (eq.12). +strategy_class field, INSUFFICIENT_CLASS_HISTORY fallback, 4 runners wired, 9 entries backfilled. ADR 0056 Поправка 3. | `ac79531` |
| **D6** | supertrend_runner `_backtest_single` PnL unverified | S50 test | 5 parity tests (GBM×3 + zero-flip + MTM-close). PnL matches 1e-9. No bugs (S50 fix confirmed). | `02e775a` |

## PHASE 6 review (6 reviewers)

| Reviewer | Scope | Verdict |
|----------|-------|---------|
| bybit-api | D1 | APPROVE (110072 V5-confirmed, money-safe) |
| python | all | APPROVE (mypy 0, no new ruff) |
| test-engineer | all | APPROVE (RED-on-regression, no assert-nothing) |
| data-integrity | D2+D5 | APPROVE (D5 checksum −238.701726 byte-preserved) |
| trading-logic | D4 | APPROVE (signal-change justified — old=bug) |
| quant-stats | D3+D5 | APPROVE_WITH_CONCERNS → addressed (`fac2b15` doc-fix) |

**quant HIGH (addressed):** docstring/ADR overstated «N_trials stays global». `INSUFFICIENT_CLASS_HISTORY` fallback **forfeits N** (drops to 1) при <3 within-class — единственный Bailey-coherent выбор (eq.12 N-term не существует без admissible sigma_SR), bounded by 3 independent gates. Doc исправлен: «fresh class never resets» holds ТОЛЬКО для CLASS_SCOPED.

## Open issues для S52

- **atr_breakout ATR-index offset** (D4 follow-up, HIGH) — отдельный defect: live оценивает breakout на бар позже vs research kernel → live 9 entries vs research 28 (BTCUSDT 4H). Безопасно (консервативно, не look-ahead) но shipped edge ≠ WFA-validated. Own ADR + WFA re-run ДО live-капитала. Документировано ADR 0064.
- **D5 forfeit-N policy** (operator escalation) — accept forfeit-N as-is ИЛИ conservative pooled-sigma proxy. Human decision.
- **free-form reason strings** (atr_breakout, pre-existing) — verify ENTRY_LONG_ATR_BREAKOUT etc. в canonical enum.

## Key decisions

- D5 two-level scoping (verdict e): sigma per-class fixes S50 contamination, N global preserves 6-honest-close anti-snooping.
- D4 SHIPPED LOCKED signal-change justified: old windowed-ATR = implementation bug, не param change.
- D2 YAGNI: minimal sidecar over full Hive manifest.

## Related
- [[../plans/2026-05-29-sprint-51-debt-closing]]
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] (Поправка 3)
- [[../decisions/0064-sprint-44-wfa-retrofit]] (D4 + follow-up)
- [[sprint-50-supertrend]]
- [[sprint-49-tech-review-audit]]
