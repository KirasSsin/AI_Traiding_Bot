---
title: Sprint 57 — Kit Ground Truth & Basis (kit-maintenance)
type: plan
sprint: 57
updated: 2026-07-02
branch: feature/sprint-57-kit-ground-truth
scope: кит-инфраструктура; src/ денежного ядра НЕ трогаем
source: UNIFIED-BACKLOG-S57.md (Фаза 0 mega-run)
---

# План S57 — «Ground Truth & Basis»

Тип: kit-maintenance. Фаза 2 SKIP (утверждённый бэклог, торговых вопросов нет).

## Trace map: KIT-NNN → задачи

| Задача | KIT | Что делаем | Proof-of-done |
|---|---|---|---|
| T1 | KIT-001 | Удалить GITHUB_TOKEN из `~/.claude/settings.json` (env-ключ целиком); security-auditor: добавить зону наблюдения `~/.claude/settings.json` + `kit/settings.example.json`; ротация токена → OPERATOR-QUEUE OQ-1 (уже записано) | `grep -c "ghp_\|gho_" ~/.claude/settings.json` → 0 |
| T2 | KIT-005 | Зазеркалить кит в репо: `kit/agents/` `kit/skills/` (симлинк-инвентарь не нужен — скопировать), `kit/hooks/`, `kit/settings.example.json` (без секретов), `kit/install.sh` (rsync в ~/.claude с бэкапом) | `git ls-files kit/ \| wc -l` > 0; install.sh idempotent dry-run OK |
| T3 | KIT-007 | `hooks-selfcheck.sh` dual-mode: `bash -n` всех `~/.claude/hooks/*.sh`; SessionStart = баннер, PreToolUse(Bash) на push = fail-CLOSED блок. P2-COMPRESS WARN отброшен (нет надёжного маркера «когда сжимался» — YAGNI, as-shipped delta) | Подключён в settings.json в ОБА массива (SessionStart + PreToolUse); red-тест: битый хук → баннер/exit 2 |
| T4 | KIT-006 | `kit-inventory.sh`: генерирует счётчики (агенты/скиллы/хуки/superpowers) в AUTO-блоки `kit-overview-ru.md` + `tooling-inventory-ru.md`; прогнать → закрыть count-drift | числа в доках == `ls`-числам; повторный прогон = no-op |
| T5 | KIT-016 prep | `~/.claude/hooks/lib/docs_broken_link_scan.py` — сканер wiki-ссылок (пути, alias, якоря) — фундамент для S59; прогон по docs/ main (6 файлов) как смоук | скрипт исполняется, выводит парсабельный список |

## Не в объёме
- Мердж chore-ветки (S59 шаг 0), гейты (S58), state v2 (S60).

## Фазы
1 Orient ✅ (Фаза 0 = orient) → 2 SKIP → 3 этот план → 4 Execute (T1–T5, TDD для скриптов через smoke red/green) → 5 Verify (bash -n, прогоны, grep-пруфы; pytest НЕ нужен — src не тронут, но прогоним unit smoke для чистоты) → 6 Review (architecture-reviewer + security-auditor: T1/T2) → 7 Sync (wiki: components-страница хука selfcheck + счётчики; docs позже S59) → 8 Ship (страница спринта; тег локально) → 9 Close.
