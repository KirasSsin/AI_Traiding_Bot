---
title: kit-team agents — kit-auditor / merge-analyst / release-manager (S63)
type: component
tags: [kit, agent, fable-5, advisory]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/agents/kit-auditor.md, kit/agents/merge-analyst.md, kit/agents/release-manager.md, kit/PINNED_VERSIONS.md]
status: stable
---

# kit-team агенты (S63)

**TL;DR:** три read-only advisory-агента на fable-5, дополняющие механические гейты (не заменяющие их). Спроектированы через Workflow (architecture-reviewer ×4).

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

## Пины (ADR [[../decisions/0075-model-pin-policy-v2]])
Все 3 + arch/trader/security/doc-linker/doc-reviewer-depth = `claude-fable-5` (judgment-heavy, причина в `kit/PINNED_VERSIONS.md`). frontend-developer opus-4-7(stale)→`opus`. Явный пин ≠ алиас.

## Ограничение развёртывания
Свежесозданные агенты dispatchable как subagent_type ТОЛЬКО после reload реестра (session start грузит registry). → OPERATOR-QUEUE OQ-5.

## Related
[[../decisions/0075-model-pin-policy-v2]] · [[manifest-telemetry]] · [[../reviews/review-s63]] · [[state-integrity-hook]]
