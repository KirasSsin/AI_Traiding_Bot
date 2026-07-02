---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S63 SHIPPED (alpha.63) — далее S64 Plugins & Best Practices (финал)
sprint: 63
phase: between-sprints
branch: main
tag: v0.1.0-alpha.63  # последний shipped (S63)
last_task_sha: 7d5f5e5  # squash S63 на main — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~Фаза0~~ → ~~S57~~ → ~~S58~~ → ~~S59~~ → ~~S60~~ → ~~S61~~ → ~~S62~~ → ~~S63 Fable-team~~ → **S64 Plugins(внедрить ≤2)** → отчёт+push. Директива: максимум fable-5 kit-агентов через Workflow; команда агентов в каждом спринте.

**S63 SHIPPED** (main `7d5f5e5`, tag alpha.63): 3 read-only advisory-агента на fable-5 (kit-auditor / merge-analyst / release-manager), спроектированы через Workflow; ADR 0075 pin-policy + `kit/PINNED_VERSIONS.md`; Matrix §4.1 (arch+trader→fable-5); frontend-developer opus-4-7→opus. Ревью arch+security APPROVE_WITH_CONDITIONS (pin-dimension, PINNED-misclass, secret-echo HIGHs закрыты). OQ-5 (агенты dispatchable после reload), OQ-6 (doc-writer тир). Детали → [[sprints/sprint-63-fable-team]].

**S64 «Plugins & Best Practices» (финал):** ресерч популярных Claude Code плагинов по звёздам GitHub, валидация совместимости, **внедрить ≤2** лучших (директива оператора v2: не только задокументировать) с метрикой токенов. Отчёт `plugins-research-s63.md` (OQ-2). Затем: kit-upgrade-report.md + ОДИН git push в origin (весь mega-run локально до сюда).

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

## Phase tracking (S63)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked; agent-пины инвентаризованы |
| 2 Brainstorm | skipped (approved backlog) | Matrix §4.1 + pin-policy + 3 новых агента |
| 3 Plan | done | plans/2026-07-02-sprint-63-fable-team.md |
| 4 Execute | done | T1 пины fable5, T2 ADR 0075+registry+frontend fix, T3-T5 3 агента (design workflow), T6 smoke, T7 inventory 18 |
| 5 Verify | done | frontmatter 3/3, kit-drift clean (18), audit-block bash -n, selfcheck |
| 6 Review | done | arch APPROVE_WITH_CONDITIONS (2 HIGH: pin-dimension+PINNED-misclass закрыты) + security (HIGH secret-echo закрыт), review-s63 Blockers=0 |
| 7 Sync | done | component + ADR 0075 + sprint-63 + index + kit-inventory AUTO |
| 8 Ship | done | manifest 7/7 + squash main 7d5f5e5 + tag v0.1.0-alpha.63 |
| 9 Close | done | SPRINT_STATE between-sprints + log; → S64 Plugins & Best Practices |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
