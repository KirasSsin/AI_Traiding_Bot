---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S57 kit-maintenance in progress (mega-run S57–S63)
sprint: 57
phase: 4-execution
branch: feature/sprint-57-kit-ground-truth
tag: v0.1.0-alpha.55  # последний shipped
---

## Текущий статус

**Mega-run S57–S63 (kit-maintenance, оператор ушёл — автономный прогон).** Фаза 0 (MERGE & VERIFY 8 аудитов) завершена: 15 CONFIRMED / 3 STALE / 6 WRONG. Артефакты: [[UNIFIED-BACKLOG-S57]], [[VERIFICATION-LEDGER]], [[OPERATOR-QUEUE]] (OQ-1 = ротация токена, ждёт оператора). Решения оператора: без остановок; модели = матрица §4.1; S63 = только рекомендации; git push один в конце прогона.

**S57 «Ground Truth & Basis»** — план [[plans/2026-07-02-sprint-57-kit-ground-truth]]. Задачи: T1 secret-out, T2 kit/ в репо, T3 hooks-selfcheck (fail-CLOSED), T4 kit-inventory.sh (count-drift), T5 link-scan lib.

**Важно для следующей сессии (если обрыв):** S56 (docs 128 страниц) НЕ закрыт — корпус на `chore/kit-integrate-headroom-ponytail` (+9 коммитов над main); мердж = S59 шаг 0. «Спринт 75» не существовал (проверено). Auth: `unset GITHUB_TOKEN GH_TOKEN` перед git remote ops (Keychain gho_).

**S55 shipped** (main `2c31c07`, tag alpha.55). Канонические счётчики: states=16, events=30, transitions=76, reason_codes=67. ADRs 72. Детали → [[sprints/sprint-55-full-audit-refactor]].

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S57)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | Фаза 0 mega-run = orient; SPRINT_STATE+git verified, chapter marked |
| 2 Brainstorm | skipped (approved backlog) | торговых вопросов нет; trader-expert не нужен |
| 3 Plan | done | plans/2026-07-02-sprint-57-kit-ground-truth.md |
| 4 Execute | done | T1–T5, per-task коммиты (5) |
| 5 Verify | done | grep=0, kit=30 files, selfcheck red/green, inventory idempotent, scanner red/green, unit 1650/0 |
| 6 Review | done | arch APPROVE (+drift-guard сделан); security REQUEST_CHANGES → BLOCKER (.bak с токеном) устранён, все фиксы re-verified |
| 7 Sync | done | hooks-selfcheck-hook.md + index + AUTO-блоки канонов |
| 8 Ship | done (local) | sprint-57 page + squash-merge + tag v0.1.0-alpha.57 (push в конце прогона) |
| 9 Close | done | → сразу S58 «Gates» |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
