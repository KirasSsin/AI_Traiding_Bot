---
title: "Phase dispatch matrix — кого/на чём звать в каждой фазе (канон)"
type: architecture
tags: [kit, dispatch, model, effort, sprint]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/PINNED_VERSIONS.md, kit/agents/, llm-wiki/wiki/project/decisions/0077-model-pin-tiered-v3.md]
status: stable
---

# Phase dispatch matrix (канон — следовать КАЖДЫЙ спринт)

**Работа идёт ТОЛЬКО по спринтам** (ADR 0041 BINDING). Каждый спринт = одни и те же 9 фаз, в каждой фазе — одни и те же агенты на одних и тех же моделях/глубине. Эта таблица = операционный источник истины «кого и на какой модели/effort звать в фазе N». Выведена из [[../decisions/0077-model-pin-tiered-v3]]; модель+effort каждого агента также в `kit/PINNED_VERSIONS.md`.

## Механика (важно)

- **Модель** = статичный пин в frontmatter агента (`model:`). Контроллер НЕ переопределяет.
- **Effort** = frontmatter-baseline (детерминизм даже при Agent-tool dispatch) + **Workflow-override** для эскалаций: `agent(prompt, {effort:'xhigh'})`. Agent tool effort НЕ принимает — эскалации только через Workflow.
- **Haiku** — БЕЗ effort-поля (400-ошибка на Sonnet 4.5/Haiku).
- **max** — НИКОГДА как пин/фазовое правило. Только ручная эскалация, когда `xhigh` уже упёрся на конкретной задаче.

## Таблица: фаза → агент → модель → effort

| Фаза | Агент / роль | Модель | Effort | Когда override |
|---|---|---|---|---|
| **1 Orient** | контроллер (sprint-orient) | — | — | агентов нет |
| **2 Brainstorm** | trader-expert ROUND 1 | opus-4.8 | high | — |
| **2 Brainstorm** | trader-expert ROUND 2 (adversarial re-research) | opus-4.8 | **xhigh** ⤴ | Workflow-override на REVISE-disagreement |
| **2 Brainstorm** | non-trading scope | — | — | `superpowers:brainstorming` (контроллер, без агента) |
| **3 Plan** | architecture-reviewer (pre-plan gate: миграция стека/фреймворка) | opus-4.8 | high | — |
| **4 Execute** | executor: механика (scaffolding/config/DDL/fixtures) | haiku-4.5 | — | — |
| **4 Execute** | executor: бизнес-логика (default) | sonnet-5 | high | — |
| **4 Execute** | executor: длинная multi-file TDD-задача | sonnet-5 | **xhigh** ⤴ | Workflow-override (долгий agentic-забег) |
| **4 Execute** | эскалация: blocked 2× ИЛИ security-critical код | opus-4.8 | **xhigh** ⤴ | смена модели + Workflow-override |
| **5 Verify** | kit-auditor (kit-maintenance спринт) | sonnet-5 | medium | обычный спринт = контроллер + pytest, агента нет |
| **6 Review** | trading-logic-reviewer | opus-4.8 | high | — |
| **6 Review** | quant-stats-reviewer | opus-4.8 | high | — |
| **6 Review** | security-auditor (рутина: money/API/kit-config diff) | opus-4.8 | high | — |
| **6 Review** | security-auditor (ПЕРВЫЙ проход НОВОЙ money-поверхности) | opus-4.8 | **xhigh** ⤴ | Workflow-override (охота на неизвестные векторы) |
| **6 Review** | data-integrity-reviewer / bybit-api-reviewer / test-engineer | sonnet-5 | high | — |
| **6 Review** | dashboard-reviewer | sonnet-5 | medium | — |
| **6 Review** | python-reviewer | haiku-4.5 | — | — |
| **7 Sync** | doc-writer | sonnet-5 | high | — |
| **7 Sync** | doc-reviewer-depth | sonnet-5 | medium | **high** ⤴ на страницах денежного ядра (risk/kelly/DSR) |
| **7 Sync** | doc-linker | sonnet-5 | medium | — |
| **7 Sync** | doc-reviewer | haiku-4.5 | — | — |
| **8 Ship** | merge-analyst | sonnet-5 | medium | — |
| **8 Ship** | release-manager | sonnet-5 | medium | — |
| **9 Close** | контроллер (SPRINT_STATE + log) | — | — | агентов нет |
| **любая** | checkpoint / Write-агент внутри Workflow-скрипта | любая | **low** | доки: low = subagents/служебное |

## Итог тиров
5 opus-4.8 (security-auditor, trading-logic, quant-stats, architecture, trader-expert) · 11 sonnet-5 (data-integrity, bybit-api, test-engineer, doc-writer, frontend-developer @ high; kit-auditor, dashboard, doc-reviewer-depth, doc-linker, merge-analyst, release-manager @ medium) · 2 haiku-4.5 (python-reviewer, doc-reviewer).

## Related
[[../decisions/0077-model-pin-tiered-v3]] · `kit/PINNED_VERSIONS.md` · [[sprint-flow-ru]] · [[kit-overview-ru]] · [[../components/kit-team-agents]]
