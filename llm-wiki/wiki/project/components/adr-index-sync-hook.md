---
title: ADR ↔ Index sync hook
type: component
tags: [infrastructure, hooks, process, wiki, superpowers]
created: 2026-04-25
updated: 2026-04-25
sources: []
status: stable
---

# ADR ↔ Index sync hook

**TL;DR:** Claude Code `PreToolUse` hook на Bash. Срабатывает перед `git push`. Если в пушимых коммитах добавлены новые ADR-файлы (`llm-wiki/wiki/project/decisions/NNNN-*.md`), каждый из них должен быть упомянут в `wiki/index.md`. Иначе push блокируется. Операционализация Bucket C6 — pre-S8c process improvement.

## Purpose

`wiki/index.md` — единый каталог знаний проекта, навигационная точка входа. Когда в проект добавляется новый ADR, строка `- [[project/decisions/NNNN-slug]]` в секции `## Project — Decisions` должна быть создана вместе с ADR в том же PR/коммите. Без этого ограничения ADR-файлы "теряются": они лежат в `decisions/`, но в index.md нет ссылки, и LLM-агент не находит их при wiki-первом чтении.

Ручной чек-лист ("не забудь добавить в index") нарушается под давлением sprint-deadline. Hook делает проверку **обязательной** через блокировку push.

## Files

- Script: `~/.claude/hooks/adr-index-sync-check.sh` — bash, +x.
- Registration: `~/.claude/settings.json`, `hooks.PreToolUse[matcher="Bash"].hooks[]` →
  `command="$HOME/.claude/hooks/adr-index-sync-check.sh"` (второй entry, после adr-agent-sync-check).
- Index file (watched target): `llm-wiki/wiki/index.md` (relative to repo root).
- ADR directory (watched source): `llm-wiki/wiki/project/decisions/` (relative to repo root).

## Hook contract

Claude Code передаёт JSON на stdin:

```json
{ "tool_input": { "command": "git push origin feature/sprint-8c-wiki-backfill" } }
```

Коды выхода:

| Code | Meaning |
|---|---|
| `0` | allow the tool call |
| `2` | **block** the tool call; stderr shown to the user |
| other non-zero | fail open (Claude Code proceeds) |

## Algorithm

```
stdin: tool_input
    ↓
command contains 'git push'?
    → no  → exit 0 (allow)
    → yes ↓
repo has llm-wiki/wiki/project/decisions/? AND wiki/index.md?
    → no  → exit 0 (allow — other repo)
    → yes ↓
determine base (upstream or origin/main merge-base)
    → no base → exit 0 (fail open)
    ↓
git diff --name-only --diff-filter=A base..HEAD -- decisions/
    → no new ADR files → exit 0 (allow — no new ADRs)
    → has new ADR files ↓
for each new file:
    extract NNNN prefix and NNNN-slug stem
    grep wiki/index.md for NNNN or stem
    → found → OK
    → not found → add to missing_list
missing_list empty?
    → yes → exit 0 + "✓ ADR ↔ Index sync OK"
    → no  → exit 2 + block message with missing_list
```

Проверка использует `--diff-filter=A` — только **добавленные** файлы. Изменения существующих ADR (amendments) не блокируются этим хуком (их coverage — adr-agent-sync-check).

## Fail-open policy

Hook намеренно fail-open в следующих случаях:
- `python3` отсутствует или payload malformed.
- Команда не содержит `git push`.
- Текущий рабочий каталог не git repo.
- `llm-wiki/wiki/project/decisions/` или `wiki/index.md` не существуют (значит, это не наш проект).
- Нет upstream и нет `origin/main` (первый клон без remote).
- `git diff` в диапазоне не нашёл новых ADR-файлов (пуш не добавляет ADR).

Fail-**closed** (exit 2 + stderr + block) только когда:
- Найден хотя бы один новый ADR-файл в диапазоне пуша.
- Его имя (NNNN-prefix или полный stem) не встречается в `wiki/index.md`.

Принцип: лучше пропустить edge case, чем сломать работу в неродственных репозиториях.

## Отличия от adr-agent-sync-check

| Аспект | adr-agent-sync-check | adr-index-sync-check |
|---|---|---|
| Триггер | ADR изменён (любой) | ADR добавлен (новый) |
| Проверяемый ресурс | `~/.claude/agents/*.md` mtime | `wiki/index.md` references |
| Метрика | timestamp comparison | grep presence check |
| Acknowledge flow | touch любого агента | добавить строку в index.md |
| Policy | ADR 0017 | Bucket C6 |

## Output example (блокировка)

```
🚫  ADR ↔ Index sync check FAILED

New ADR file(s) not referenced in wiki/index.md:
    - 0024-sprint-9-backtesting.md

Required action:
  Add entry to wiki/index.md "## Project — Decisions" section.
  Example:
      - [[project/decisions/NNNN-slug]] — One-line summary.

  Then retry push.

(Defined by: llm-wiki/wiki/project/components/adr-index-sync-hook.md
 Policy:     Bucket C6 — pre-S8c process improvement)
```

## Output example (успех)

```
✓ ADR ↔ Index sync OK
```

## Caveats

- **Scope: только новые ADR.** Хук не требует index-entry при amendments (изменение существующего ADR). Это сознательный trade-off: amendments к уже зарегистрированному ADR не меняют навигационного каталога.
- **Grep по NNNN-prefix.** Если в index.md есть строка `0024-sprint-9-...` хотя бы где-то (даже в комментарии), хук пропустит. Это позволяет гибко форматировать entry без жёсткого regexp ADR-URL.
- **Worktree scope.** Срабатывает при push из любого worktree проекта. Все worktrees видят общий `wiki/index.md`.
- **Cross-platform.** Скрипт не использует `stat` или `find -printf` (в отличие от adr-agent-sync-check). Чистый bash + python3 + git — работает на macOS и Linux.
- **Hook self-test guard (added 2026-04-25):** PreToolUse matcher `"Bash"` triggers hook на ANY Bash invocation. Test commands (`echo '{"tool_input":{"command":"git push ..."}}' | bash hook.sh`) substring-matched `"git push"` через `case` pattern → false-positive blocks. Guard skips if `$command_str` references hook script paths (`adr-agent-sync-check.sh` ИЛИ `adr-index-sync-check.sh` ИЛИ `hooks/*sync-check*`). Real `git push` commands не reference hook scripts, so guard is safe. См. `~/.claude/hooks/adr-index-sync-check.sh:39-46`.

## Verification

Проверка логики (2026-04-25):

```bash
# На test-hook-adr-index-sync ветке с 0099-test-hook.md добавленным:
git diff --name-only --diff-filter=A $(git merge-base HEAD origin/main)..HEAD -- llm-wiki/wiki/project/decisions
# → llm-wiki/wiki/project/decisions/0099-test-hook.md

grep -qE "(0099|0099-test-hook)" wiki/index.md && echo FOUND || echo MISSING
# → MISSING (будет заблокировано)
```

Python-симуляция выдала `VERDICT: BLOCK (exit 2)` для 0099 — логика корректна.

Реальный push тестировался через Claude Code Bash hook: adr-agent-sync-check срабатывал первым (он обрабатывает thr range ADR изменений, не только добавленных), новый hook встаёт вторым в очереди и проверит своё условие.

## Referenced by

- [[../architecture/development-workflow]] — PHASE 8 step 5b HARD-GATE (added в S8c)
- [[adr-agent-sync-hook]] — sister hook (mirror pattern, both block git push на ADR-related drift)
- [[../decisions/0017-review-agent-harness]] — agent harness ADR (S8c amendment added this hook к review process)
- [[../../index]] — file этой hook guards

## Related

- Mirror of: [[project/components/adr-agent-sync-hook]] — предшествующий hook (ADR ↔ agent prompts sync).
- Config: `~/.claude/settings.json` (PreToolUse hook registration, второй entry в Bash-matcher).
- Index: [[wiki/index.md]] — файл-цель, который проверяется.
- Bucket C6 — wiki/project/decisions/ audit (S8c backfill sprint).
- Workflow: [[project/architecture/development-workflow]] — sprint lifecycle, finishing phase.
