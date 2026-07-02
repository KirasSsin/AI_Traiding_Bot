---
title: kit-team agents — kit-auditor / merge-analyst / release-manager (S63)
type: component
tags: [kit, agent, advisory]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/agents/kit-auditor.md, kit/agents/merge-analyst.md, kit/agents/release-manager.md, kit/PINNED_VERSIONS.md]
status: stable
---

# kit-team агенты (S63)

**TL;DR:** три read-only advisory-агента (модели по [[../decisions/0077-model-pin-tiered-v3]]: kit-auditor/merge-analyst/release-manager = sonnet-5 medium), дополняющие механические гейты (не заменяющие их). Спроектированы через Workflow.

## Агенты

| Агент | Роль | Дополняет | Триггер |
|---|---|---|---|
| `kit-auditor` | аудит целостности кита (8 измерений: drift, секреты-tripwire, orphans, битые ссылки, count-drift, bash -n обоих деревьев, heredoc-python, **pin-registry**) | hooks-selfcheck (только синтаксис), kit-inventory (только счётчики) | периодически / «прогони аудит кита» |
| `merge-analyst` | pre-merge риск-профиль диффа (контуры, предсказание гейтов, gaps) | review-gate (механика) | перед PR/branch-merge kit-спринта |
| `release-manager` | ship-чеклист (sprint-page, changelog, тег-последовательность, manifest, budget) — предлагает, НЕ выполняет | sprint-finish (выполняет) | «ship»/«финишируем»/tag |

## Ключевые границы (S63 review conditions)
- **«Read-only» = дисциплина промпта, НЕ sandbox.** Bash физически может писать; harness инжектит Write для памяти независимо от `tools:`. Ограничение: Write ТОЛЬКО под `.claude/agent-memory/<name>/`. Не гарантия уровня песочницы.
- **Хук главнее отчёта.** Расхождение вывода агента и exit-code хука → прав хук (агент может галлюцинировать «чисто»). Агенты advisory — не блокируют push/merge.
- **kit-auditor secret-scan = tripwire only** (HIGH-1 фикс): presence + ТОЛЬКО префикс-evidence, никогда полный секрет в stdout; эскалирует security-auditor как владельцу.

## Пины ([[../decisions/0077-model-pin-tiered-v3]] tiered v3, суперседит 0076/0075)
Модель+effort каждого агента — источник истины `kit/PINNED_VERSIONS.md` (5 opus-4.8 / 11 sonnet-5 / 2 haiku-4.5 по фазе×роли). Эти 3 advisory = sonnet-5 medium. effort в frontmatter (baseline) + Workflow-dispatch-override для эскалаций. Fable-5 нигде как пин.

## Ограничение развёртывания
Свежесозданные агенты dispatchable как subagent_type ТОЛЬКО после reload реестра (session start грузит registry). → OPERATOR-QUEUE OQ-5.

## Related
[[../decisions/0077-model-pin-tiered-v3]] · `kit/PINNED_VERSIONS.md` · [[manifest-telemetry]] · [[../reviews/review-s63]] · [[state-integrity-hook]]
