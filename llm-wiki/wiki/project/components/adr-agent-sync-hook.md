---
title: ADR ↔ Agent prompt sync hook
type: component
tags: [infrastructure, hooks, review-agents, process, superpowers]
created: 2026-04-22
updated: 2026-07-02
sources: [kit/hooks/adr-agent-sync-check.sh]
status: stable
---

# ADR ↔ Agent prompt sync hook

**TL;DR:** Claude Code `PreToolUse` hook на Bash. Срабатывает перед `git push`. Если в пушимых коммитах изменялся любой `llm-wiki/wiki/project/decisions/NNNN-*.md`, **номер `NNNN` обязан встречаться в теле хотя бы одного `~/.claude/agents/*.md`** (S59 KIT-009: содержательная проверка; прежний mtime-механизм с `touch`-подтверждением упразднён — A2-анализ показал, что 58 из 75 исторических блоков были touch-ритуалом без обновления знаний). Иначе push блокируется. Операционализация ADR [[../decisions/0017-review-agent-harness]].

> ⚠️ Диаграмма/примеры ниже описывают историческую mtime-механику (S8c–S58) — сохранены как контекст; актуальная логика = grep номера ADR по телам агентов.

## Purpose

Review-агенты (`trading-logic-reviewer`, `quant-stats-reviewer`, `data-integrity-reviewer`, `python-reviewer`) хранят в своих prompt'ах привязки к конкретным ADR: Kelly phases (ADR 0012), Wilder vs classical (ADR 0011), WFA params (ADR 0014), slippage model (ADR 0010), circuit breakers (ADR 0013). Когда ADR меняется, prompt агента должен быть обновлён синхронно — иначе ревью будет опираться на устаревшие формулы и пропустит баг.

Ручной sync-чек был описан в `llm-wiki/CLAUDE.md` как "часть workflow `finishing-a-development-branch`". На практике такие чек-листы забываются. Hook делает проверку **обязательной** через блокировку push.

## Files

- Script: `~/.claude/hooks/adr-agent-sync-check.sh` — bash, +x.
- Registration: `~/.claude/settings.json`, `hooks.PreToolUse[].matcher="Bash"` →
  `command="$HOME/.claude/hooks/adr-agent-sync-check.sh"`.
- Agents directory (watched): `~/.claude/agents/`.
- ADR directory (watched): `llm-wiki/wiki/project/decisions/` (relative to repo root).

## Hook contract

Claude Code passes JSON on stdin:

```json
{ "tool_input": { "command": "git push origin feature/sprint-4" } }
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | allow the tool call |
| `2` | **block** the tool call; stderr shown to the user |
| other non-zero | fail open (Claude Code proceeds) |

## Algorithm

```dot
digraph hook_flow {
    "stdin: tool_input" [shape=box];
    "command contains 'git push'?" [shape=diamond];
    "allow" [shape=doublecircle];
    "repo has wiki/project/decisions/?" [shape=diamond];
    "determine base (upstream or origin/main)" [shape=box];
    "ADR files in base..HEAD range?" [shape=diamond];
    "latest ADR commit ts" [shape=box];
    "max mtime of ~/.claude/agents/*.md" [shape=box];
    "agent mtime >= ADR ts?" [shape=diamond];
    "BLOCK (exit 2)" [shape=doublecircle, style=filled, fillcolor=lightcoral];

    "stdin: tool_input" -> "command contains 'git push'?";
    "command contains 'git push'?" -> "allow" [label="no"];
    "command contains 'git push'?" -> "repo has wiki/project/decisions/?" [label="yes"];
    "repo has wiki/project/decisions/?" -> "allow" [label="no (other repo)"];
    "repo has wiki/project/decisions/?" -> "determine base (upstream or origin/main)" [label="yes"];
    "determine base (upstream or origin/main)" -> "ADR files in base..HEAD range?";
    "ADR files in base..HEAD range?" -> "allow" [label="no ADR changes"];
    "ADR files in base..HEAD range?" -> "latest ADR commit ts" [label="yes"];
    "latest ADR commit ts" -> "max mtime of ~/.claude/agents/*.md";
    "max mtime of ~/.claude/agents/*.md" -> "agent mtime >= ADR ts?";
    "agent mtime >= ADR ts?" -> "allow" [label="yes"];
    "agent mtime >= ADR ts?" -> "BLOCK (exit 2)" [label="no (drift)"];
}
```

## Fail-open policy

Hook **намеренно** fail-open в следующих случаях:
- `python3` отсутствует или payload malformed (редкое — macOS ships with python3).
- Команда не содержит `git push`.
- Текущая директория не git repo или не имеет `llm-wiki/wiki/project/decisions/` (значит, это не наш проект).
- Нет upstream и нет `origin/main` (первый клон без remote).
- `git log base..HEAD` не нашёл ADR-изменений.

Fail-**closed** (exit 2 + stderr + block) только когда:
- ADR-коммит есть в диапазоне пуша.
- `~/.claude/agents/` не существует или пуст → блок (exit 2).
- Номер изменённого ADR (`NNNN`) НЕ найден строкой `ADR NNNN` ни в одном теле агента.

Принцип: лучше пропустить edge case, чем сломать работу пользователя в неродственных репах.

## Механизм: content-check (S59 KIT-009, НЕ mtime)

**mtime-механизм отменён в S59.** `touch` больше НЕ обходит хук. Для каждого изменённого ADR (`NNNN` из имени файла) хук `grep`'ает анкерованный `ADR[[:space:]-]*NNNN` в телах `~/.claude/agents/*.md`. Обоснование (A2-анализ): 58 из 75 исторических блоков этого хука были touch-ритуалом без реального обновления знаний агента — чистый шум. Голое 4-значное число НЕ засчитывается (108 цифровых серий уже живут в телах — нужен осознанный маркер `ADR`).

## Acknowledge flow (если ADR не требует agent-update)

Впиши строку `ADR NNNN: <одна фраза сути>` в тело релевантного ревьюера (даже для чисто-организационного ADR — это осознанный ack, что агент «знает» про решение):

```
ADR 0077: tiered пины opus/sonnet/haiku + effort в frontmatter
```

Правило выбора агента: деньги→security-auditor, торг.логика→trading-logic-reviewer, математика→quant-stats-reviewer, данные→data-integrity-reviewer, архитектура→architecture-reviewer.

## Output example (блокировка)

```
🚫  ADR ↔ Agent prompt sync check FAILED (KIT-009 content-check, S59)

ADR в пуше, чей номер НЕ упомянут ни в одном агент-промпте:
    - 0017-review-agent-harness.md

Required action:
  Впиши "ADR 0017: <суть>" в тело релевантного ревьюера (НЕ touch).
  touch mtime закрыт в S59.

(Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md
 Policy:     ADR 0017 + S59 KIT-009)
```

## Caveats

- **Cross-platform:** скрипт использует `stat -f` (BSD/macOS) и `find -printf` (GNU/Linux) через `uname`-гейт. Windows не поддерживается (у пользователя macOS).
- **mtime ≠ семантический sync.** Пользователь может открыть агент в редакторе без изменений и сохранить — mtime обновится, hook пропустит. Но это сознательный trade-off: автоматически определить "реальный" sync невозможно без manifest'а, а manifest — over-engineering до первого инцидента.
- **Worktree scope.** Hook срабатывает при push из любого worktree проекта (все они видят `llm-wiki/wiki/project/decisions/`). Этого достаточно для v0.1.
- **Для второго репозитория.** Если понадобится расширить (например, агенты для второго проекта), добавить per-project `.claude/settings.json` с своим hook-скриптом. Текущая реализация глобальная через `~/.claude/settings.json`.
- **Hook self-test guard (added 2026-04-25):** PreToolUse matcher `"Bash"` triggers hook на ANY Bash invocation. Test commands (`echo '{"tool_input":{"command":"git push ..."}}' | bash hook.sh`) substring-matched `"git push"` через `case` pattern → false-positive blocks. Guard skips if `$command_str` references hook script paths (`adr-agent-sync-check.sh` ИЛИ `adr-index-sync-check.sh` ИЛИ `hooks/*sync-check*`). Real `git push` commands не reference hook scripts, so guard is safe. См. `~/.claude/hooks/adr-agent-sync-check.sh:42-49`.

## Verification

Manual tests (прошли 2026-04-22):
- `echo '{"tool_input":{"command":"ls"}}' | hook` → exit 0 (non-push ignored).
- `echo '{"tool_input":{"command":"git push"}}' | hook` в worktree без committed ADR → exit 0 (нет ADR в range).
- Fail-closed ветка проверяется при первом реальном ADR-коммите.

## Referenced by

- [[../architecture/development-workflow]] — PHASE 8 step 4 (ADR ↔ agent prompt sync invariant)
- [[../../../CLAUDE|llm-wiki/CLAUDE]] — "ADR ↔ agent prompts" sync section
- [[../decisions/0017-review-agent-harness]] — defining ADR (review-agent harness operationalized by this hook)
- [[adr-index-sync-hook]] — sister hook (parallel pattern, mirror of this)

## Related

- [[../sprints/sprint-28-process-enforcement]] — sprint where ADR↔agent sync hook was established
- [[../decisions/0041-sprint-28-process-enforcement]] — ADR for process enforcement (sprint-flow-check pattern)
- ADR: [[../decisions/0017-review-agent-harness]] — политика, агенты.
- Config: `~/.claude/settings.json` (PreToolUse hook registration).
- Agents: `~/.claude/agents/{trading-logic-reviewer,quant-stats-reviewer,data-integrity-reviewer,Python Reviewer}.md`.
- Workflow: [[../architecture/development-workflow]] — Superpowers review gate.
