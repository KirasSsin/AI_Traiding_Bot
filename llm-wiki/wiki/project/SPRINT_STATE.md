---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S64 LLM-Wiki Audit & Doc-Flow — ship
sprint: 64
phase: 8-ship
branch: feature/sprint-64-llm-wiki-doc-flow
tag: v0.1.0-alpha.63  # последний shipped (S63)
last_task_sha: 7d5f5e5  # HEAD последней задачи — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~S57~~…~~S63~~ → **S64 LLM-Wiki Audit & Doc-Flow** → S65 Error-Harvest → S66 Plugins(≤2) → отчёт+push. Директивы (BINDING, оператор 2026-07-02): (1) doc-first — техдоки llm-wiki RU → код → пользовательские docs/ RU, гейт docs/=WARN; (2) все вызываемые агенты = kit fable-5 через Workflow (основной луп opus 4.8 дорогой — минимизировать); (3) session-restore от техдоков llm-wiki; (4) минимум токенов.

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

## Phase tracking (S64)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked; директивы оператора в память |
| 2 Brainstorm | skipped (validated plan) | оператор провалидировал: 2 спринта, docs/=WARN |
| 3 Plan | in_progress | plans/2026-07-02-sprint-64-llm-wiki-doc-flow.md + audit-workflow |
| 4 Execute | done | T1 аудит+синк, T2 doc-first (CLAUDE.md+sprint-flow-ru+orient+manifest 3b), T3 docs/ WARN, T4 orient 4b, T5 idea-verdict, T6 docs/-страница |
| 5 Verify | done | bash -n + WARN red-check + selfcheck + drift clean + счётчики 18/14 |
| 6 Review | done | arch APPROVE_WITH_CONDITIONS (2 HIGH закрыты) + kit-auditor + doc-reviewer-depth (все fable-5), review-s64 Blockers=0 |
| 7 Sync | done | current-state синк + sprint-64 + review + index + docs-sync-gate/docs-update → WARN |
| 8 Ship | in_progress | manifest + squash + tag v0.1.0-alpha.64 |
| 9 Close | pending | → S65 Error-Harvest |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
