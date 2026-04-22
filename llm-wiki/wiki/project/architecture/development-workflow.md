---
title: Development Workflow — Superpowers pipeline для проекта
type: architecture
tags: [workflow, superpowers, methodology, tdd, v0.1]
created: 2026-04-20
updated: 2026-04-20
status: stable
sources: [obra/superpowers README, llm-wiki/CLAUDE.md, migration-plan.md]
---

# Development Workflow

**TL;DR:** Проект использует **Superpowers** — методологию из 7 скиллов, автоматически триггерящихся на соответствующих фазах (brainstorm → worktree → plan → subagent exec / TDD / review → finish). Каждый спринт v0.1 проходит полный цикл; wiki (`llm-wiki/`) держит артефакты всех фаз.

## Superpowers pipeline (7 шагов)

| # | Skill | Активируется | Output |
|---|-------|-------------|--------|
| 1 | `brainstorming` | любой новый scope (feature, спринт, subsystem) | `design-spec` (у нас — страницы в `wiki/project/architecture/`) |
| 2 | `using-git-worktrees` | после approve spec | изолированный worktree на новой ветке + clean baseline |
| 3 | `writing-plans` | approved spec в руках | implementation plan в `wiki/project/plans/YYYY-MM-DD-<slug>.md` |
| 4a | `subagent-driven-development` | approved plan | fresh subagent на task → two-stage review (spec compliance → code quality) |
| 4b | `executing-plans` | approved plan (альтернатива) | batch execution inline + human checkpoints |
| 5 | `test-driven-development` | во время implementation | RED → GREEN → REFACTOR, коммит на зелёном |
| 6 | `requesting-code-review` | между tasks / перед merge | issues по severity (critical блокирует) |
| 7 | `finishing-a-development-branch` | tasks завершены | merge / PR / keep / discard + cleanup worktree |

Дополнительно при отладке: `systematic-debugging` (4-phase root cause), `verification-before-completion`.

## Маппинг на стадии нашего v0.1

| Stage | Наша активность | Superpowers skill |
|-------|-----------------|-------------------|
| **Stage 1 — Docs ingest** | чтение MVP-спеки, создание wiki (41 страница: architecture + ADRs + strategies + indicators + concepts) | не применялся (чистый wiki-ingest) |
| **Stage 2 — Migration plan** | `wiki/project/architecture/migration-plan.md` через обсуждение scope/детализации | ✅ `brainstorming` |
| **Stage 3 — Sprint-by-sprint** | цикл per-sprint (см. ниже) | ✅ все 7 скиллов |

## Sprint lifecycle (применяется к каждому из 10 спринтов)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. brainstorming                                            │
│    (опционально; если scope спринта из migration-plan       │
│     ясен — пропускаем, идём сразу к writing-plans)          │
│                                                             │
│ 2. using-git-worktrees                                      │
│    - уже внутри worktree elastic-noyce-046edb               │
│    - per-sprint: sub-branch sprint/S<N>-<slug>              │
│                                                             │
│ 3. writing-plans                                            │
│    → wiki/project/plans/YYYY-MM-DD-sprint-<N>-<slug>.md     │
│                                                             │
│ 4. subagent-driven-development (рекомендовано)              │
│    или executing-plans (inline, когда контекст короткий)    │
│                                                             │
│ 5. test-driven-development (enforced в каждом task)         │
│    - failing test → run → impl → pass → commit              │
│                                                             │
│ 6. requesting-code-review (после каждых 3-5 tasks)          │
│    - critical blocks / major / minor / suggestion           │
│                                                             │
│ 7. finishing-a-development-branch                           │
│    - merge sprint branch → main                             │
│    - tag v0.1.0-alpha.<N>                                   │
│    - wiki update: components/ + log.md                      │
└─────────────────────────────────────────────────────────────┘
```

## Артефакты на фазу

| Skill | Артефакт | Куда сохраняется |
|-------|----------|------------------|
| `brainstorming` | design spec | `wiki/project/architecture/<topic>.md` |
| `writing-plans` | implementation plan | `wiki/project/plans/YYYY-MM-DD-<slug>.md` |
| `subagent-driven-development` | per-task commits + review notes | git history + `wiki/log.md` |
| `test-driven-development` | failing-then-passing test sequences | `tests/unit/`, `tests/integration/`, `tests/property/` |
| `requesting-code-review` | review report | `wiki/queries/YYYY-MM-DD-review-<slug>.md` (опционально) |
| `finishing-a-development-branch` | tag + changelog entry | `CHANGELOG.md` + git tag |

## Связь с глобальным CLAUDE.md

Пользовательский `~/.claude/CLAUDE.md` требует:
- **Plan Mode сначала** → покрывается `brainstorming` + `writing-plans`.
- **TDD** → `test-driven-development`.
- **YAGNI / KISS / DRY** → enforced в `brainstorming` (design-review) и `writing-plans` (scope-check).
- **Минимальные изменения** → `subagent-driven-development` two-stage review ловит scope creep.
- **Conventional commits** → коммиты в каждом TDD-цикле следуют формату `feat:/fix:/docs:/refactor:/test:/chore:`.

Superpowers — **надстройка** над глобальными правилами, не конфликт.

## Связь с wiki-maintainer workflow (CLAUDE.md llm-wiki)

Наш `llm-wiki/CLAUDE.md` описывает **отдельный** workflow: ingest / query / lint — это **wiki maintenance**, не разработка кода. Superpowers skills активируются при **code work** (sprint execution). Оба workflow сосуществуют:

- **Code-work спринт** (Superpowers) → генерирует событие → **wiki-ingest** документирует в `wiki/project/components/` и дописывает в `wiki/log.md`.
- **Wiki lint** (llm-wiki schema) может выявить расхождение между wiki и актуальным кодом → триггерит **новый brainstorming** (Superpowers) для resolution.

## Когда пропускаем скиллы

- `brainstorming` — пропускается, когда scope уже утверждён в `migration-plan.md` и не изменился (спринты S1-S10 имеют готовые AC).
- `using-git-worktrees` — уже в worktree; для спринтов — sub-branch достаточно.
- `requesting-code-review` — **не** пропускаем, но на мелких patch'ах делаем light-review inline.
- `finishing-a-development-branch` — применяется **только** в конце sprint/release, не на каждом коммите.

## Red flags (когда skill НЕ соблюдается)

Из `superpowers:using-superpowers`:

| Мысль | Реальность |
|-------|-----------|
| "Это простой спринт, skill излишен" | Skill-check быстрый; запуск гарантирует дисциплину. |
| "Сначала посмотрю код, потом подумаю о плане" | `writing-plans` требует design first. Исследование — часть `brainstorming`. |
| "Напишу код, потом тест" | **Нарушение `test-driven-development`.** Код без теста удаляется. |
| "Чуть-чуть расширю scope задачи" | `requesting-code-review` поймает; лучше явный `brainstorming` на новый scope. |

## Sources

- [obra/superpowers](https://github.com/obra/superpowers) — репозиторий + README (установка через `/plugin install superpowers@claude-plugins-official`).
- `skills/writing-skills/SKILL.md` — гайд по расширению.
- Наш `llm-wiki/CLAUDE.md` — wiki-maintainer schema (параллельный workflow).

## Related

- [[migration-plan]] — 10 спринтов, где применяется этот workflow.
- [[overview]] — target v0.1.
- [[../plans/2026-04-20-sprint-1-foundation]] — первый пример plan-артефакта.
- `~/.claude/CLAUDE.md` (private) — глобальные правила пользователя (TDD, Plan-Mode, YAGNI).
