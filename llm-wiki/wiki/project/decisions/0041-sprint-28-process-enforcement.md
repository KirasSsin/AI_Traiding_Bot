---
title: 0041. Sprint 28 — Process enforcement (sprint-flow-check hook + Russian process docs)
type: decision
date: 2026-04-26
sprint: 28
tags: [adr, sprint-28, process, enforcement, hook, kit-flow, ru, sprint-flow-check]
sources:
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/architecture/development-workflow.md
  - project/decisions/0017-review-agent-harness.md
  - project/plans/2026-04-26-sprint-28-process-enforcement.md
status: accepted
---

# 0041. Sprint 28 — Process enforcement

**Status:** accepted
**Date:** 2026-04-26

## Контекст

Operator complaint после S27 ship:

> "Последний спринт выглядит flow так что наш кит сломан. Я ожидаю чтобы это
> было как раньше с использованием каждой фазы. При завершении каждой задачи
> обновляется SPRINT_STATE. В S27 не подключались скиллы планирования, todo,
> superpowers:brainstorming и все наши наработки в ките."
>
> "Заметил что не обновляется папка llm-wiki/wiki/project/plans"
>
> "Твоя задача сделать наш flow таким, чтобы он всегда исполнялся если работа
> касается спринтов."

### Verified drift (S16-S27)

```bash
$ ls llm-wiki/wiki/project/plans/ | tail
2026-04-25-sprint-12-live-demo-validation.md
2026-04-25-sprint-13-backfill-wfa.md
2026-04-25-sprint-8c-wiki-backfill.md
2026-04-25-sprint-9-quality-types-analytics.md
2026-04-26-sprint-15-mean-reversion-multi-symbol.md
```

Last plan = S15. Then 12 sprints (S16, S17, S18, S19, S20, S21, S22, S23, S25, S26, S27) = no plan files. Drift accumulated under load — kit invocation = polite reminder, not enforcement.

S27 specifically violated:
- Direct `Agent` dispatch instead of `superpowers:brainstorming` или `brainstorm-init` skill
- No plan file (PHASE 3 skipped)
- `superpowers:writing-plans` skipped
- `superpowers:subagent-driven-development` skipped (controller-driven)
- SPRINT_STATE updated only at end (not per-task)
- TodoWrite ad-hoc, not phase tracker

## Варианты

### Option A — Polite reminder в CLAUDE.md (status quo, drift continues)
- **Pros:** Zero infrastructure
- **Cons:** Already failing — 12 sprints drifted

### Option B — Mechanical enforcement via hooks
- **Pros:** Cannot bypass под нагрузкой. Aligns с existing pattern (adr-agent-sync, adr-index-sync, wiki-broken-link).
- **Cons:** Requires hook infrastructure + settings.json registration

### Option C — Project-level skills auto-trigger каждый message
- **Pros:** Conceptually elegant
- **Cons:** Still bypassable. Skill auto-trigger = description match — not deterministic enforcement.

## Решение

**Option B** — mechanical enforcement via hook (`sprint-flow-check.sh`) + Russian process docs (single source of truth для operator).

### Components

1. **Hook `~/.claude/hooks/sprint-flow-check.sh`** (NEW) — pre-push enforcement
   - Pattern: blocks push на `feature/sprint-NN-*` branch без plan file matching `^[0-9]{4}-[0-9]{2}-[0-9]{2}-sprint-NN-.+\.md$` в `llm-wiki/wiki/project/plans/`
   - Tested: positive (plan exists → exit 0), negative (no plan → exit 2 + helpful error)
   - Registered в `~/.claude/settings.json` PreToolUse Bash matcher

2. **Russian process docs**:
   - `wiki/project/architecture/sprint-flow-ru.md` — обязательный 9-фаз процесс с per-phase HARD-GATEs + anti-patterns + per-task SPRINT_STATE protocol
   - `wiki/project/architecture/tooling-inventory-ru.md` — full catalog (6 agents + 5 project skills + 13 superpowers + 21 agent-skills + 7 claude-mem + 5 caveman + 6 MCP servers + 5 hooks) с decision matrix

3. **CLAUDE.md updates**:
   - `CLAUDE.md` (repo root): "⚠️ BEFORE ANY SPRINT WORK — kit flow обязателен (BINDING)" section с phase table + HARD-GATEs + anti-patterns + links к Russian docs
   - `llm-wiki/CLAUDE.md`: references к Russian docs + hook description

4. **SPRINT_STATE template** (applied inline в S28 itself):
   - Per-phase tracking table (Phase 1-9 status / artifact / updated)
   - Per-task progress subtable under Phase 4
   - Per-task SPRINT_STATE update protocol (BINDING — не batch в конце)

## Последствия

### Code / config changes

- `~/.claude/hooks/sprint-flow-check.sh` NEW (out-of-repo, content embedded ниже для reproducibility)
- `~/.claude/settings.json` MODIFIED — registered sprint-flow-check.sh к PreToolUse Bash matcher
- `CLAUDE.md` (repo root) — binding section добавлена
- `llm-wiki/CLAUDE.md` — Russian docs links

### Wiki changes

- `wiki/project/architecture/sprint-flow-ru.md` NEW (~12 KB)
- `wiki/project/architecture/tooling-inventory-ru.md` NEW (~14 KB)
- `wiki/project/decisions/0041-sprint-28-process-enforcement.md` NEW (этот ADR)
- `wiki/project/sprints/sprint-28-process-enforcement.md` NEW
- `wiki/project/plans/2026-04-26-sprint-28-process-enforcement.md` NEW (first plan file since S15 — closes drift)
- `wiki/project/SPRINT_STATE.md` MODIFIED — phase tracking template applied
- `wiki/index.md` — entries для new docs + sprint-28 + ADR 0041
- `wiki/project/architecture/current-state.md` — sprint history row +S28
- `wiki/log.md` — sprint-end entry

### Hook script content (для reproducibility)

```bash
#!/usr/bin/env bash
# sprint-flow-check.sh — see ~/.claude/hooks/sprint-flow-check.sh для full source
set -u

payload="$(cat || true)"
[ -z "$payload" ] && exit 0

command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""), end="")
except: pass
' 2>/dev/null || true)"

case "$command_str" in
    *"sprint-flow-check.sh"*) exit 0 ;;
    *"git push"*) ;;
    *) exit 0 ;;
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -z "$repo_root" ] && exit 0
[ ! -d "$repo_root/llm-wiki/wiki/project/plans" ] && exit 0

current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
[ -z "$current_branch" ] && exit 0

[[ ! "$current_branch" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]] && exit 0
sprint_num="${BASH_REMATCH[1]}"

plan_files="$(ls "$repo_root/llm-wiki/wiki/project/plans" 2>/dev/null \
    | grep -E "^[0-9]{4}-[0-9]{2}-[0-9]{2}-sprint-${sprint_num}-.+\.md$" || true)"

if [ -z "$plan_files" ]; then
    cat >&2 <<EOF
🚫  Sprint flow check FAILED
Branch: $current_branch (sprint $sprint_num)
Required: plan file <YYYY-MM-DD>-sprint-${sprint_num}-<slug>.md
Required action: invoke superpowers:writing-plans skill
EOF
    exit 2
fi
exit 0
```

### Per-task SPRINT_STATE update protocol (Phase 4 BINDING)

После КАЖДОЙ task complete:
1. Edit `llm-wiki/wiki/project/SPRINT_STATE.md`:
   - Update Phase 4 task table row (status / commit SHA)
   - Update "Текущий статус" если milestone
   - Update "Следующее действие"
   - Update `updated:` frontmatter
2. (Optional) commit: `docs(sprint): SPRINT_STATE update phase=4 task=Tx done`

### Backward compatibility

- Existing hooks (`adr-agent-sync`, `adr-index-sync`, `wiki-broken-link`) preserved — no conflicts
- S15 plan file (last existing) preserved — backward reference
- S16-S27 sprints без plan files — historical drift, не retroactively fixable

### Carry-overs к S29+

- Per-task SPRINT_STATE protocol depends on operator/controller discipline (hook не enforces in-flight commits)
- Optional future: pre-commit hook checking SPRINT_STATE updated within last hour
- Optional future: project-level skill `/sprint-start` automates branch + SPRINT_STATE template + plan file scaffolding

## Ссылки

- `wiki/project/architecture/sprint-flow-ru.md` — обязательный процесс
- `wiki/project/architecture/tooling-inventory-ru.md` — tooling catalog
- `wiki/project/architecture/development-workflow.md` — English MASTER SOP (more detail, complementary)
- `wiki/project/decisions/0017-review-agent-harness.md` — review agents matrix (parent policy)
- `wiki/project/plans/2026-04-26-sprint-28-process-enforcement.md` — S28 plan
- [[../sprints/sprint-28-process-enforcement]] — спринт delivery record
- ADR 0017 amendment 2026-04-25 (review-agent harness) — pattern source для hook approach
