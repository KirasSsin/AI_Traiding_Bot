---
title: Unified Backlog — kit mega-run S57–S63 (слияние 8 аудитов)
type: backlog
updated: 2026-07-02
sources: CLAUDE, GLM, MINIMAX, MIMO, QWEN, GEMINI, CHATGPT, DEEPSEEK (вес одинаковый)
verification: см. VERIFICATION-LEDGER.md — в работу идут только CONFIRMED
---

# UNIFIED-BACKLOG-S57 — дедуплицированный бэклог кита

Решения оператора (2026-07-02): прогон без остановок; модели = матрица §4.1; S63 = только фиксация рекомендаций (без установки); git push один в конце.

## CONFIRMED → в спринты

| ID | Название | Источники | Sev | Компонент | Фикс | Спринт |
|---|---|---|---|---|---|---|
| KIT-001 | GITHUB_TOKEN плейнтекстом в settings.json | [CLAUDE P0-SECRET][GLM K-12][QWEN P-06][GEMINI DE-001] | BLOCKER | `~/.claude/settings.json` | Убрать из файла; Keychain/env; security-auditor зона +settings.json; ротация → OPERATOR | S57 |
| KIT-002 | Гейты обходятся именем ветки (fail-OPEN на chore/*) | [CLAUDE P0-BRANCH][GLM K-01][MINIMAX 2.1.6][QWEN] | BLOCKER | sprint-flow-check.sh:69, phase-advance.sh:68 | Условие от SPRINT_STATE.phase ∈ {2..8}, не от ветки; red/green hook-test | S58 |
| KIT-003 | Нет механического гейта Фазы 6 (ревью денег) | [CLAUDE P0-REVIEW][GLM K-06] | BLOCKER | hooks/ | review-gate.sh на `gh pr merge`: денежные пути → требовать review-sNN.md (Blockers=0) + `\| 6 Review \| done \|` | S58 |
| KIT-004 | docs/ на main ПУСТ; S56-корпус (155 файлов) не смержен; авто-sync отсутствует | все 8 + новая находка | BLOCKER | docs/, chore-ветка | (а) домержить chore→main как закрытие S56; (б) Docs-Sync Gate: staleness+link хуки, manifest, скилл docs-update | S59 |
| KIT-005 | Кит не под git (не переносим, дрейфует) | [CLAUDE P0-KITVCS] | HIGH | ~/.claude/* | kit/ в репо (agents/skills/hooks/settings.example.json без секретов) + install.sh; settings.json → .gitignore | S57 |
| KIT-006 | Count-drift инвентарей (11→15 агентов, 5→8 скиллов, «7»→6+2+1 хуков, 13→14 superpowers) | [CLAUDE P1-INVENTORY][GLM K-07][QWEN P-01/02][MINIMAX][CHATGPT][DEEPSEEK] | HIGH | kit-overview-ru.md:216, tooling-inventory-ru.md | kit-inventory.sh → AUTO-блоки в канонах и docs/10-… | S57 |
| KIT-007 | Синтаксис хуков не сторожится (fail-OPEN дыра) | [CLAUDE P1-BASHN] | HIGH | SessionStart | hooks-selfcheck.sh (bash -n все хуки, fail-CLOSED) + WARN про несжатые промпты (P2-COMPRESS) | S57 |
| KIT-008 | SPRINT_STATE монолит; contextExceededCount=7; инцидент 86КБ | [GLM Блок4][MINIMAX Н.4][QWEN P-03][CHATGPT][DEEPSEEK][GEMINI] | HIGH | SPRINT_STATE.md | v2: state/CURRENT.md ≤2КБ + BACKLOG.md ≤4КБ + .backup/ + integrity-hook + last_task_sha + git-коммит на запись; PRE-PLAN гейт architecture-reviewer | S60 |
| KIT-009 | adr-agent-sync обходится `touch` (mtime) | [GLM K-03] | HIGH | adr-agent-sync-check.sh:96-140 | Проверка содержимого: ADR-номер grep'ом в теле агента/changelog | S58 |
| KIT-010 | Нет доказательства «скилл выстрелил» | [CLAUDE P1-MANIFEST][MIMO][DEEPSEEK] | HIGH | sprint-finish | Skill-firing manifest по артефактам фаз + kit-validation-checklist.md [MINIMAX финал] | S61 |
| KIT-011 | Каскад/banned-full-read не принуждается | [CLAUDE P1-CASCADE] | MEDIUM | PreToolUse | Хук: Read/cat banned-файла без offset/limit → БЛОК | S61 |
| KIT-012 | AUTOCOMPACT=50 / MAX_THINKING=10000 без ADR и замеров | [CLAUDE P1-TUNING][QWEN][MINIMAX 2.1.8] | MEDIUM | settings.json env | ADR + скрипт замера токенов/спринт; A/B фоном | S61 |
| KIT-013 | Per-task обновление state не детектится | [GLM Блок4][DEEPSEEK 4][MINIMAX 2.1.15] | MEDIUM | PreToolUse git commit | WARN-хук: src/** в коммите без state → предупреждение (блок позже по данным) | S58 |
| KIT-014 | Модельная политика: нет pin-policy, матрица §4.1 не применена | [GLM K-05][QWEN P-05][CLAUDE P2-PINPOLICY] + директива §4 | HIGH | ~/.claude/agents/* | ADR pin-policy v2; trader-expert+architecture-reviewer → claude-fable-5; смоук-таблица; факт про CLAUDE_CODE_SUBAGENT_MODEL в docs | S62 |
| KIT-015 | Нет агентов kit-auditor / merge-analyst / release-manager | директива §4.3 | MEDIUM | ~/.claude/agents/ | Создать 3 агента (claude-fable-5, effort max, memory project) + регистрация через kit-inventory | S62 |
| KIT-016 | Битые wiki-ссылки в docs-корпусе | [CLAUDE §4.1→P2-DOCLINKS][QWEN P-L01][MINIMAX] | MEDIUM | docs/ (chore) | docs_broken_link_scan.py (формат `page`, `page\|alias`, пути) → починить всё найденное | S59 |
| KIT-017 | Self-Consistency debugging (≥2 гипотезы до правки) | [GEMINI] (решение: без формул) | LOW | CLAUDE.md | Абзац в правила дебага (systematic-debugging — плагин, не правим) | S61 |
| KIT-018 | context-budget-warn: добавить «сначала сериализуй state → потом /compact» | [GEMINI Context-Pressure→решение конфликтов] | LOW | context-budget-warn.sh | Строка в красное предупреждение; пороги оставить, замерить | S61 |
| KIT-019 | S56 не закрыт (Phase 9 отсутствует, ветки висят) | новая находка (git) | HIGH | chore-ветка, SPRINT_STATE | Мердж chore→main (docs-контент; денежный код не тронут) + log.md запись + удалить obsolete ветку sprint-56 | S59 (шаг 0) |
| KIT-020 | consolidate-memory триггер не принуждается | [GLM K-08][MINIMAX 2.1.x] | MEDIUM | Phase 9 | Проверка в manifest (S61): sprint%5==0 → требовать лог consolidate | S61 |
| KIT-021 | agent-memory NONE: doc-reviewer, trader-expert | инвентарь | LOW | .claude/agent-memory/ | Проверить при смоуках S62; не ошибка если агент не писал | S62 |

## DEFER (ADR-черновики, без реализации в прогоне)
| ID | Что | Источники | Причина |
|---|---|---|---|
| KIT-D01 | БД/LangGraph для state | [QWEN][GEMINI] | Кит file-first (токен-экономия+git-история). Черновик ADR «когда пересмотреть» в S60 |
| KIT-D02 | GitHub Actions docs-CI | [GEMINI DE-004/005] | PreToolUse-механика доказана в бою; CI — черновик ADR в S59 |
| KIT-D03 | Партиции памяти (Bridges 2-4) | [CLAUDE P2-MEMPART] | Долгосрок; после S60 |
| KIT-D04 | using-git-worktrees для autoresearch | [CLAUDE 2.1-a] | Отдельный спринт |
| KIT-D05 | Формульный Context Pressure Gate | [GEMINI] | Решение: ужесточить существующий хук (KIT-018) |
| KIT-D06 | wiki Block1↔Block2 механический валидатор | [GLM K-09] | Черновик в S61 |

## WRONG / STALE / N-A (уроки о качестве источников — в работу НЕ идут)
| Заявление | Источник | Вердикт |
|---|---|---|
| SPRINT_STATE 6242>6144 сейчас | [GLM K-02] | STALE (5380) |
| Канонические счётчики устарели | подтекст нескольких | WRONG (16/30/76/67 совпадают) |
| claude-mem грузит 50 наблюдений | [GLM K-10] | STALE (17 obs, 94% savings) |
| PostToolUse нестабильность у нас | [QWEN P-07] | N-A (не используем) |
| «Токсичность» параллельных агентов | [QWEN P-08] | OPINION (изоляция — дизайн) |
| OTTL/автоскейлинг/CI-права | [GEMINI DE-005..007] | N-A (нет таких подсистем) |
| «Был спринт 75» | оператор | WRONG (max alpha.55 везде; S56 docs не закрыт; следующий = S57) |

## S63-research (фиксация, БЕЗ установки — решение оператора)
Кандидаты на верификацию: serena (LSP), context-mode, git-mcp, usage-monitor/claude-code-costs, context7, atomic-commits, no-leak hook, sequential-thinking, security-sweep, code-graph/Graphify, AutoMem. Выход: отчёт с вердиктами живости/совместимости/экономии → оператор решает.
