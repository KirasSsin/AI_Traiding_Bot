---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-06-26  # S55 full-audit-refactor — PHASE 1-7 done, PHASE 8 ship pending (alpha.55)
sprint: 55
phase: 8-ship
branch: feature/sprint-55-full-audit-refactor
tag: v0.1.0-alpha.54
---

## Текущий статус

**S55 = full-project audit + refactor.** Workflow `w1hxvgkoa` (120 агентов, 9 измерений, 2× skeptic-verified) нашёл 43 подтверждённых дефекта на shipped main (tag alpha.54). Все исправлены через strict TDD + 2 раунда re-review (PHASE 6 + 6.2), которые вскрыли 7 follow-up'ов. Детали по каждому finding → [[sprints/sprint-55-full-audit-refactor]].

**Исправлено:** 2 BLOCKER (TL-01 live-runtime никогда не вооружал OCO + сбрасывал exit-сигналы → unbounded-loss; BYBIT-01 REST/WS в разных Bybit-окружениях → fill loop сломан) + 9 HIGH (TL-02, BYBIT-02/03, ARCH-02, QS-1 DSR de-annualization, DI-01/02, SEC-S55-01 path-traversal, DASH-01) + 15 MEDIUM (TL-03/04, ARCH-03, BYBIT-04/05, DI-03/04, DASH-02/03, QS-2 ADR 0071, TQ-01..06) + 17 LOW (ARCH-05, TL-06/07, QS-2-bars, DI-06/SEC-03/PY-5, SEC-04, PY-1..4, TQ-07/08, DASH-04/05, BYBIT-06) + bonus QS-3 (donchian DSR twin).

**PHASE 6/6.2 follow-up (re-review):** SEC-BYBIT01-INCOMPLETE (HIGH — `demo=` на всех 4 RESTClient sites + AST gate), ARCH-02-REG-01 (HIGH — bootstrap освобождает RLock через REST I/O), ARCH-03-REGRESSION (HIGH — integration `_FakeAdapter` props; integration не в default gate), TL-NEW-01 (MEDIUM — 2 новых FSM-перехода), DASH-03-GAP-01 (MEDIUM — Kronos atomic writes через `_cache_io.py`), QS-6 (MEDIUM — `__main__` 4H bars→2191), NEW-LOW-01 (DRY consolidation).

**Канонические счётчики:** states=16, events=30, **transitions=76** (74→76: TL-NEW-01 +2 `FLATTEN_FAILED→HALTED`), reason_codes=67. ADRs 71 (0071 _cmd_wfa DSR units). Sprint pages 59.

**Финальные gates:** unit pytest 1694 passed / 0 failed, integration 103 passed, mypy --strict 0/101, ruff src/ clean, frontend vitest 51/51 + tsc/lint/build clean. 70 commits, 106 files, +7189/-956.

**Готово к ship `v0.1.0-alpha.55`.**

## Carry (post-S55)

- **BYBIT-08** (MEDIUM, pre-existing) — `coordinator._try_place_market_sell` bare `except` классифицирует post-retCode==0 OrderAck-parse failure как NOT_SENT → flatten attempt-2 → double-sell. Правильный fix = adapter-level typed `AmbiguousOrderOutcome` через 3 `place_*` варианта (coordinator type-split сломал бы intended retry-with-qty-step). Нужен свой ADR/sprint.
- atr_breakout ATR-index offset (D4, HIGH) — own ADR+WFA до live. ADR 0064.
- D5 forfeit-N policy (operator escalation).
- Track B Kronos signal enrichment — DEFER до forward paper-trade.
- Forward paper-trade harness → единственная валидная Kronos-валидация.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json` вместо tmp_path (spawn'нут follow-up в B2 run).
- Permanently deferred: 12mo MAINNET ADR / live trade feed widget / M4 __repr__ redaction.

---

## Phase tracking (S55)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | operator: full-project audit + refactor via workflow, thinking + effort max |
| 2 Brainstorm | skipped (operator-specified scope) | — |
| 3 Plan | done | 2026-05-30-sprint-55-audit-refactor.md (batched B0..B4) |
| 4 Execute | done | 43 findings + QS-3, sequential TDD, per-fix commit |
| 5 Verify | done | unit 1694/0, integration 103, mypy 0/101, ruff clean, frontend 51/51 + build |
| 6 Review | done | 2 rounds (9 reviewers + adversarial verify); 7 follow-ups fixed, BYBIT-08 carried |
| 7 Sync | done | sprint-55 page + canonical counts 74→76 + current-state/index/log + ADR 0071 |
| 8 Ship | in_progress | tag v0.1.0-alpha.55 |
| 9 Close | pending | — |

---

## История спринтов (где искать)

- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history + canonical counts
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
