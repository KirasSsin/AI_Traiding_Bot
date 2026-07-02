---
title: "Sprint 68 — Boot-слой: стоимость и правда"
type: sprint
sprint: 68
created: 2026-07-02
updated: 2026-07-02
status: shipped
tags: [sprint-68, kit-maintenance, boot, token-economy]
---

# Sprint 68 — Boot-слой

**Тема:** токен-кровотечение + мёртвые ритуалы + канон-дрейф (deep-research S68 «Boot-слой», 9 HIGH). Полный kit-цикл. src/ денежного ядра заморожен.

## Deliverables (10 задач)

| # | Задача | Находки | Итог |
|---|---|---|---|
| T4 | touch-ритуал → S59 content-check | D1-02/SKW-02/MEM-06 | 8 поверхностей (finding 6 + 2 свежих ошибки этой сессии + полное mtime-описание component page). Мёртвый `touch` → `ADR NNNN` текст-check. |
| T5 | kit-inventory AUTO-блок расширен | SKW-01/D7-04 | +ADR/sprint/component/model-tier счётчики (де-дрейф kit-overview+tooling-inventory); phase table +ponytail/ponytail-audit/docs-update; tooling-inventory §1 dispatch-source pointer |
| T6 | global CLAUDE.md → проект-scope | MEM-07/D7-03/D2-09 | global §9 banned-list (проект-пути) → в llm-wiki/CLAUDE.md; kit-team-agents fable→ADR 0077 pointer |
| T7 | ancestor-scan WARN | D7-02 хвост | hooks-selfcheck WARN на walk-up CLAUDE.md (защита рецидива Desktop boot-tax). Смоук: plant→WARN(19B)→remove→clean |
| T9 | error-taxonomy миф + классы | D5-05 и др. | «151× parse-fail» → ~2 реальных (149 = region-block HTML, класс 10); класс 11 no-read-back |
| T10 | **phase-dispatch канон** | директива оператора | [[../architecture/phase-dispatch-ru]] — фаза→агент→модель+effort (ADR 0077); «работа ТОЛЬКО по спринтам» усилено |
| T1 | launchd-краш-луп | LOG9-01 | C2 `com.kit.auto-resume.plist` unload+removed (TCC-краш-луп; S67 desktop-путь заменил). security-auditor review |
| T2 | caveman-дубли + warp off | D8-01/D8-04 | ручные caveman-хуки из settings.json (плагин их сам даёт — двойной баннер) + warp=false. Гейты выжили |
| T3 | claude-mem пороги | D5-03/MEM-01 | OBSERVATIONS 50→5, SESSION_COUNT 10→3 (меньше инжекта/сессию) |
| T8 | AI_Traiding_Tool дерево | LOG9-03 | 1 lesson merged→канон, галлюцинированное дерево удалено |

## Pre-done (эта сессия, до S68-ветки — на main)
ADR 0077 tiered пины + скилл kit-conventions + CLAUDE.md компрессия (105→52KB) + Desktop 43.8KB удалён + 18 тел агентов валидированы. См. plan «Pre-done».

## Live-изменения вне git (backups для отката)
- `~/.claude/settings.json` → `.bak-s68-fe1a24b` (caveman-дубли сняты, warp off)
- `~/.claude-mem/settings.json` → `.bak-s68-fe1a24b` (пороги 5/3)
- `~/Library/LaunchAgents/com.kit.auto-resume.plist` → `~/com.kit.auto-resume.plist.removed-s68-fe1a24b` (unloaded)

## Verify (Phase 5)
- все живые + kit хуки `bash -n` OK; hooks-selfcheck runs (docs/manifest WARN pre-existing, вне S68)
- 18 агентов целы, зеркало `diff -rq` = 0; settings.json valid JSON; caveman single-fire (плагин)

## Review (Phase 6)
security-auditor на батч-Б (removal-diff: settings/launchd/claude-mem/delete) — verdict в [[../reviews/review-s68]].

## Экономия
~20k токенов/сессию (Desktop boot-tax 13.3k + caveman-дубль + claude-mem 6.3k→меньше). Мёртвый touch-ритуал (гарантированный блок пуша каждый ADR-спринт) устранён. launchd-краш-луп остановлен.

## Related
[[../plans/2026-07-02-sprint-68-boot-layer]] · [[../kit-deep-research-2026-07-02]] · [[../decisions/0077-model-pin-tiered-v3]] · [[../architecture/phase-dispatch-ru]]
