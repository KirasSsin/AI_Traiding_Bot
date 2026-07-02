---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S62 SHIPPED (alpha.62) — далее S63 Fable-5 Team
sprint: 62
phase: between-sprints
branch: main
tag: v0.1.0-alpha.62  # последний shipped (S62)
last_task_sha: f5b8943  # squash S62 на main — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~Фаза0~~ → ~~S57~~ → ~~S58 Auto-Resume~~ → ~~S59 Gates~~ → ~~S60 Docs-Sync~~ → ~~S61 State v2~~ → ~~S62 Manifest~~ → **S63 Fable-team** → S64 Plugins(внедрить ≤2) → отчёт+push. Директива: максимум fable-5 kit-агентов через Workflow (основной луп opus 4.8 дороже); команда агентов участвует в каждом спринте.

**S62 SHIPPED** (main `f5b8943`, tag alpha.62): skill-firing manifest (P1-MANIFEST, догфуд 6/6 ✓) + cascade-WARN (P1-CASCADE) + tamper-evidence review-артефакта (T2, закрыл эфемерность S59/S61) + ADR 0074 tuning + KIT-022 fix. Security HIGH #1 (origin-strip auth-bypass money-гейта, живой с S59) закрыт. Остаток → [[kit-op-detect-hardening-backlog]] (KIT-OD-1 argv, KIT-OD-2 T2-binding). Детали → [[sprints/sprint-62-manifest-telemetry]].

**S63 «Fable-5 Team» (следующий):** Matrix §4.1 (trader-expert + architecture-reviewer → fable-5), ADR pin-policy v2 (когда пинить vs алиас + триггер ревью при смене платформенного дефолта), новые агенты kit-auditor/merge-analyst/release-manager, смоук-тесты агентов. Директива оператора: kit-агенты уже на fable-5 max (для доработки кита).

**S61 SHIPPED** (main `35ae188`, tag alpha.61): SPRINT_STATE v2 Вариант B — state-backup + state-integrity (fail-OPEN restore) + last_task_sha. Закалка по 6 раундам adversarial bypass-hunt (1 BLOCKER + 6 HIGH + 3 MEDIUM закрыты; 32 python + 38 bash regression). Остаток → [[kit-op-detect-hardening-backlog]] + S62 tamper-evidence. Детали → [[sprints/sprint-61-state-v2]].

**S62 «Manifest & Telemetry» (следующий):** skill-firing manifest в sprint-finish (P1-MANIFEST), kit-validation-checklist, cascade-хук (block full-read banned-файлов), budget-хук ревизия, tuning ADR (AUTOCOMPACT/MAX_THINKING). Carry: KIT-022 (malformed-frontmatter WARN), KIT-025 (heredoc→external .py), tamper-evidence review-артефактов (S59/S61 остаток).

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ денежного ядра заморожен (kit-maintenance only). SPRINT_STATE стейджить ОТДЕЛЬНО от commit (иначе state-backup не увидит staged).

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ денежного ядра заморожен (kit-maintenance only).

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S62)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked |
| 2 Brainstorm | skipped (approved backlog) | P1-MANIFEST/CASCADE/TUNING + tamper-evidence |
| 3 Plan | done | plans/2026-07-02-sprint-62-manifest-telemetry.md |
| 4 Execute | done | T1 manifest, T2 tamper, T3 cascade, T4 ADR 0074, T5 KIT-022 fix+KIT-025 audit, T6 wiring |
| 5 Verify | done | red/green (tamper/cascade/KIT-022/HIGH#1), 17 хуков bash -n, ruff, selfcheck, S61 regression intact |
| 6 Review | done | arch APPROVE_WITH_CONDITIONS (2 HIGH+MED закрыты) + security (HIGH #1 origin-strip закрыт, MED#2→backlog), review-s62 Blockers=0 |
| 7 Sync | done | component manifest-telemetry + ADR 0074 + sprint-62 + index |
| 8 Ship | done | manifest 6/6 ✓ + squash main f5b8943 + tag v0.1.0-alpha.62 |
| 9 Close | done | SPRINT_STATE between-sprints + log; → S63 Fable-5 Team |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
