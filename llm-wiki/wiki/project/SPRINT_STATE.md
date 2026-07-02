---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-03  # S69 SHIPPED (alpha.69) → S70 OPEN (orient)
sprint: 70
phase: 1-orient
branch: main  # ветка feature/sprint-70-* создаётся в Phase 3 plan
tag: v0.1.0-alpha.69  # S69 shipped локально; push origin отложен (директива оператора)
last_task_sha: 22248bf  # S69 squash-ship на main
---

## Текущий статус

**S70 — OPEN (Phase 1 orient).** S69 «Гейты по-настоящему» SHIPPED (alpha.69, squash `22248bf` на main): 2 новых lib (`op_detect.py` quote-strip skeleton + `emit_context.py` WARN→model), 10 хуков на op-detect, git-common-dir split-brain защита, security-auditor APPROVE (2 BLOCKER separator+sh-c закрыты в Phase 6). Детали → [[sprints/sprint-69-gates]] + log.md.

**S70 scope (из carry):** tuning A/B probe (ADR 0074) — дешёвый A/B эксперимент параметров стратегии с held-out (anti-snooping). **NB: src/ money-core заморожен в mega-run** → уточнить в brainstorm, probe = research/harness, а не сырые src-правки денежного ядра, ИЛИ разморозка через отдельный ADR. Доп. carry-backlog: KIT-OD-2 (inline-alias op-detect), docs/ бэкфилл, D3-04 (WARN-сверка Scheduled Task).

**next_action:** S70 Phase 2 brainstorm (`brainstorm-init` → trader-expert: A/B probe scope + метрика + held-out) → Phase 3 plan (техстраница llm-wiki ДО кода; ветка `feature/sprint-70-*`) → execute.

**⚠️ PUSH-TO-GITHUB (pending, директива оператора «слей в github»):** main = 12 коммитов ahead origin (S58…S69 локальные ships), теги alpha.57…alpha.69 НЕ запушены. Выполнить: `unset GITHUB_TOKEN GH_TOKEN; git push origin main --follow-tags` (один раз). Если обрыв до push — это ПЕРВОЕ действие возобновления.

**Carry (src/ money-core заморожен):** BYBIT-08 (typed AmbiguousOrderOutcome), atr_breakout ATR-offset (ADR 0064), D5 forfeit-N, Track B Kronos. Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`. OQ: 1 (токен), 5.

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S70 — A/B tuning probe)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | S69 shipped alpha.69 (22248bf); chapter marked; S70 scope = ADR 0074 A/B probe |
| 2 Brainstorm | pending | brainstorm-init → trader-expert: probe scope + метрика + held-out (anti-snooping) |
| 3 Plan | pending | техстраница llm-wiki ДО кода; ветка feature/sprint-70-* |
| 4 Execute | pending | — |
| 5-9 | pending | — |

**S69 (SHIPPED alpha.69):** op-detect hardening (quote-strip skeleton) + WARN→model + git-common-dir split-brain. 2 BLOCKER separator/sh-c закрыты в Phase 6, security APPROVE. → [[sprints/sprint-69-gates]].
**S68 (SHIPPED alpha.68):** Boot-слой, 10 задач. → [[sprints/sprint-68-boot-layer]].

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
