# Sprint 28 — Process Enforcement + Russian Tooling Docs

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Зафиксировать kit flow механически (hooks + Russian docs + slash command) чтобы любая работа на спринтом ВСЕГДА проходила через все фазы (brainstorm → plan → execute → ship), плюс полный каталог tooling (agents/skills/plugins/MCP) на русском.

**Architecture:**
- Russian process docs в `wiki/project/architecture/*-ru.md` — single source of truth для operator
- Hook `sprint-flow-check.sh` блокирует push на feature/sprint-* branch без plan file → enforcement
- Slash command `/sprint-start` / `/sprint-resume` → автоматически invoke right skill в right phase
- CLAUDE.md updates → links Russian docs + binding rules section "BEFORE any sprint work"

**Tech Stack:** Markdown (wiki), Bash (hook), Python (helpers если нужно), git (PR/tag).

---

## Context

S27 violated kit flow:
- Прямой Agent dispatch вместо `superpowers:brainstorming` или `brainstorm-init` skill
- Нет plan file в `wiki/project/plans/` (последний S15, drift 12 sprints)
- Нет `superpowers:writing-plans` invocation
- `superpowers:subagent-driven-development` пропущен (controller-driven вместо)
- SPRINT_STATE updated только в конце спринта, не после каждой задачи
- TodoWrite использовался ad-hoc, не как phase tracker

Последние 12 спринтов (S16-S27) показали drift: kit постепенно ослаблен. Operator complaint = wakeup call.

Root cause: kit invocation = polite reminder в CLAUDE.md, не enforcement. Когда controller под нагрузкой → сокращает phases.

Решение: sprint-flow-check hook блокирует push BEZ plan file. Hook = mechanical enforcement, не убирается даже под нагрузкой.

---

## File Structure

NEW files:
- `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` — полный sprint lifecycle (9 фаз) на русском с per-phase HARD-GATEs
- `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` — catalog: agents (6), skills (5 project + 50+ plugin), plugins, MCP servers — назначение + когда + как
- `~/.claude/hooks/sprint-flow-check.sh` — pre-push hook, блокирует если sprint branch без plan file
- `llm-wiki/wiki/project/plans/2026-04-26-sprint-28-process-enforcement.md` — этот plan file
- `llm-wiki/wiki/project/decisions/0041-sprint-28-process-enforcement.md` — ADR
- `llm-wiki/wiki/project/sprints/sprint-28-process-enforcement.md` — sprint page

MODIFY:
- `CLAUDE.md` (repo root) — добавить "BEFORE any sprint work" binding section + link к Russian docs
- `llm-wiki/CLAUDE.md` — link к Russian docs
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase tracking template + update protocol
- `llm-wiki/wiki/project/architecture/development-workflow.md` — add header "Русская версия: sprint-flow-ru.md"
- `llm-wiki/wiki/index.md` — entries для новых docs

---

## Task Breakdown

### Task 1: sprint-flow-ru.md (Russian sprint lifecycle)

**Files:**
- Create: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`

- [ ] **Step 1: Write skeleton с frontmatter + 9 phase sections**

```markdown
---
title: Sprint Flow — обязательный процесс kit'а (русская версия)
type: architecture
tags: [workflow, sprint-lifecycle, kit, hard-gates, ru]
created: 2026-04-26
updated: 2026-04-26
status: stable
sources:
  - project/architecture/development-workflow.md (English original)
  - project/decisions/0041-sprint-28-process-enforcement.md
---

# Sprint Flow — обязательный процесс (RU)

> **Это binding процесс.** Любая работа над спринтом обязана пройти ВСЕ фазы.
> Hook `sprint-flow-check.sh` блокирует push если plan file отсутствует.

## Обзор фаз

| Фаза | Название | Триггер | HARD-GATE | Артефакт |
|------|----------|---------|-----------|----------|
| 1 | Orient | Старт сессии / `/clear` | SPRINT_STATE прочитан + git verified | `mcp__ccd_session__mark_chapter` |
| 2 | Brainstorm | Open scope/design questions | Все Q processed через trader-expert ROUND 1 (+ROUND 2 если REVISE-disagreement) | `wiki/project/pre-s{N}-backlog.md` |
| 3 | Plan | Brainstorm verdicts locked | Plan file в `wiki/project/plans/` создан | `wiki/project/plans/<date>-sprint-N-<slug>.md` |
| 4 | Execute | Plan committed | TDD per task + per-task commit + SPRINT_STATE update | git commits |
| 5 | Verify | All tasks done | pytest GREEN + mypy clean + canonical counts current | test output |
| 6 | Review | Verify passed | Domain reviewer (L5) per touched area + (если требуется) parallel reviewers | review reports |
| 7 | Sync | Review passed | wiki update — components + ADR + sprint page + index + log | wiki diffs |
| 8 | Ship | Wiki synced | sprint-NN.md + counts + orphan-audit + index sync (per sprint-finish skill) | tag v0.1.0-alpha.N + PR merge |
| 9 | Close | Tag pushed | SPRINT_STATE → between-sprints + log session-end | SPRINT_STATE |

## Phase 1: Orient
[detail]

## Phase 2: Brainstorm
[detail]

...

## Anti-patterns (НЕ делать)

- ❌ Прямой Agent dispatch вместо brainstorm-init skill
- ❌ Code without plan file
- ❌ SPRINT_STATE update только в конце
- ❌ Skip review (PHASE 6) потому что "тривиальные изменения"
- ❌ Push с feature/sprint-* без `wiki/project/plans/<date>-sprint-N-*.md` — hook блокирует

## Per-task SPRINT_STATE update протокол

После КАЖДОЙ task complete:
1. Edit SPRINT_STATE.md `## Текущий статус` — отметить что сделано
2. Edit `## Следующее действие` — что дальше
3. Edit `updated:` frontmatter
4. Optional: `git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): SPRINT_STATE update phase=X task=Y"`
```

- [ ] **Step 2: Fill all 9 phase sections с детальной procedure + invoke commands + HARD-GATE checks**
- [ ] **Step 3: Add "Per-task SPRINT_STATE update" протокол**
- [ ] **Step 4: Add anti-patterns section**
- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/project/architecture/sprint-flow-ru.md
git commit -m "docs(s28-t1): sprint-flow-ru.md — Russian sprint lifecycle с HARD-GATEs"
```

### Task 2: tooling-inventory-ru.md (agents/skills/plugins/MCP catalog)

**Files:**
- Create: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`

- [ ] **Step 1: Inventory existing tools**

```bash
ls ~/.claude/agents/                           # 6 agents
ls .claude/skills/                              # 5 project skills
ls ~/.claude/plugins/cache/                     # plugins
ls .claude/skills/*/SKILL.md                    # skill descriptions
```

- [ ] **Step 2: Write catalog с structure**

```markdown
---
title: Tooling Inventory — агенты/скиллы/плагины/MCP (русская версия)
type: architecture
tags: [tooling, agents, skills, plugins, mcp, catalog, ru]
---

# Tooling Inventory (RU)

## 1. Domain Reviewer Agents (6)

### trader-expert
- **Назначение:** Решает PHASE 2 brainstorm questions (CONFIRM/REVISE/DEFER/EXPAND verdicts).
- **Когда:** Любая sprint scope question (стратегия / архитектура с trading semantics / metrics calibration).
- **Модель:** sonnet 4.6 (effort:max)
- **Не использовать для:** Чисто архитектурных решений (architecture-reviewer), формул (quant-stats), Python idioms (python-reviewer).

### trading-logic-reviewer
[similar]

### quant-stats-reviewer
[similar]

### data-integrity-reviewer
[similar]

### python-reviewer
[similar]

### architecture-reviewer
[similar]

## 2. Project Skills (5) — `.claude/skills/`

### sprint-orient
[similar table]

### sprint-finish
[similar]

### wiki-update
[similar]

### brainstorm-init
[similar]

### hook-test
[similar]

## 3. Plugin Skills (50+) — Superpowers + Agent-Skills + Caveman

### superpowers:brainstorming
[when + why]

### superpowers:writing-plans
[when + why]

...

## 4. MCP Servers

### claude-mem
- mem-search: поиск по прошлым sessions

### ccd_session
- mark_chapter: chapter marks для navigation
- spawn_task: out-of-scope task chip

### Computer-use
- Только для UI walkthrough (не trading work)

## 5. Когда что вызывать (decision matrix)

| Задача | Tool sequence |
|--------|---------------|
| Старт сессии | sprint-orient skill |
| Новый sprint scope | brainstorm-init → trader-expert (если scope questions) |
| Plan writing | superpowers:writing-plans |
| Execute plan | superpowers:subagent-driven-development OR executing-plans |
| Code change в src/risk/* | trading-logic-reviewer + quant-stats-reviewer |
| Cross-module refactor | architecture-reviewer |
| Sprint complete | sprint-finish skill → superpowers:finishing-a-development-branch |
| После src/ change | wiki-update skill |
```

- [ ] **Step 3: Fill каждый tool entry с примером invocation**
- [ ] **Step 4: Add decision matrix table**
- [ ] **Step 5: Commit**

```bash
git commit -m "docs(s28-t2): tooling-inventory-ru.md — agents/skills/plugins/MCP catalog"
```

### Task 3: sprint-flow-check.sh hook (mechanical enforcement)

**Files:**
- Create: `~/.claude/hooks/sprint-flow-check.sh`

- [ ] **Step 1: Write hook script**

```bash
#!/usr/bin/env bash
# sprint-flow-check.sh — pre-push enforcement
# Блокирует push если работаешь на feature/sprint-NN-* BUT plan file отсутствует.
# Plan file pattern: llm-wiki/wiki/project/plans/<date>-sprint-NN-*.md
#
# Per ADR 0041 (S28). Mechanical enforcement of kit flow.

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$REPO_ROOT" ] && exit 0  # not in repo, skip

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

# Match feature/sprint-NN-<slug> pattern
if [[ ! "$CURRENT_BRANCH" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]]; then
  exit 0  # not sprint branch, skip
fi

SPRINT_NUM="${BASH_REMATCH[1]}"
PLANS_DIR="$REPO_ROOT/llm-wiki/wiki/project/plans"

# Check plan file exists for this sprint
PLAN_FILES=$(ls "$PLANS_DIR" 2>/dev/null | grep -E "^[0-9]{4}-[0-9]{2}-[0-9]{2}-sprint-${SPRINT_NUM}-.+\.md$" || true)

if [ -z "$PLAN_FILES" ]; then
  cat <<EOF
🚫  Sprint flow check FAILED

Branch: $CURRENT_BRANCH (sprint $SPRINT_NUM)
Required: plan file matching pattern в $PLANS_DIR
  llm-wiki/wiki/project/plans/<YYYY-MM-DD>-sprint-${SPRINT_NUM}-<slug>.md

Found: NONE

Required action: invoke superpowers:writing-plans skill to produce plan file
THEN retry push.

Reason: Last 12 sprints (S16-S27) drifted — no plan files. Per ADR 0041
mechanical enforcement of PHASE 3 (Plan writing).

(Defined by: ~/.claude/hooks/sprint-flow-check.sh
 Policy:     wiki/project/decisions/0041-sprint-28-process-enforcement.md)
EOF
  exit 1
fi

echo "✅ Sprint flow check: plan file found ($PLAN_FILES)"
exit 0
```

- [ ] **Step 2: Make executable + bash syntax check**

```bash
chmod +x ~/.claude/hooks/sprint-flow-check.sh
bash -n ~/.claude/hooks/sprint-flow-check.sh
```

- [ ] **Step 3: Register в settings (PreToolUse on git push)**

Edit `~/.claude/settings.json` (или project `.claude/settings.json` если scope project-only). Add hook entry pointing к script.

- [ ] **Step 4: Test hook**

```bash
# On current branch (feature/sprint-28-process-enforcement)
# With plan file already created — should PASS
~/.claude/hooks/sprint-flow-check.sh
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(s28-t3): sprint-flow-check.sh hook — mechanical PHASE 3 enforcement"
```

### Task 4: SPRINT_STATE phase tracking template

**Files:**
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md`

- [ ] **Step 1: Add per-phase tracking section**

```markdown
## Phase tracking (S{N})

| Phase | Status | Artifact | Updated |
|-------|--------|----------|---------|
| 1 Orient | done | mark_chapter | YYYY-MM-DD HH:MM |
| 2 Brainstorm | done | pre-s{N}-backlog.md | YYYY-MM-DD HH:MM |
| 3 Plan | done | plans/<date>-sprint-{N}-<slug>.md | YYYY-MM-DD HH:MM |
| 4 Execute | in_progress | task X/Y commits | YYYY-MM-DD HH:MM |
| 5 Verify | pending | — | — |
| 6 Review | pending | — | — |
| 7 Sync | pending | — | — |
| 8 Ship | pending | — | — |
| 9 Close | pending | — | — |
```

- [ ] **Step 2: Add per-task subtable under Phase 4**

```markdown
### Phase 4 — task progress
| Task | Status | Commit | Tests |
|------|--------|--------|-------|
| T1 | done | abc1234 | +5 cases |
| T2 | in_progress | — | — |
```

- [ ] **Step 3: Commit**

### Task 5: CLAUDE.md updates (repo + llm-wiki) + binding section

**Files:**
- Modify: `CLAUDE.md` (repo root)
- Modify: `llm-wiki/CLAUDE.md`

- [ ] **Step 1: Add к repo CLAUDE.md "BEFORE any sprint work" binding section**

```markdown
## BEFORE any sprint work — kit flow обязателен (BINDING)

Любая работа касающаяся sprint = MUST follow 9 phases:

1. **Orient** — `sprint-orient` skill OR manual SPRINT_STATE read
2. **Brainstorm** — `brainstorm-init` skill (auto-routes через trader-expert если scope questions)
3. **Plan** — `superpowers:writing-plans` skill → produces `wiki/project/plans/<date>-sprint-N-<slug>.md` (HARD-GATE: hook `sprint-flow-check.sh` блокирует push без этого файла)
4. **Execute** — `superpowers:subagent-driven-development` skill OR controller-driven с TodoWrite per-task tracking
5. **Verify** — pytest + mypy + canonical counts
6. **Review** — domain reviewers (L5) per touched area
7. **Sync** — `wiki-update` skill
8. **Ship** — `sprint-finish` skill → `superpowers:finishing-a-development-branch`
9. **Close** — SPRINT_STATE between-sprints + log session-end

**После КАЖДОЙ task complete (Phase 4):** обнови `llm-wiki/wiki/project/SPRINT_STATE.md` (текущий статус + следующее действие + updated date) — это per-task discipline, не только sprint-end.

**Полный процесс на русском:** `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`
**Каталог tooling (агенты / скиллы / MCP):** `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`
```

- [ ] **Step 2: Update llm-wiki/CLAUDE.md links**
- [ ] **Step 3: Commit**

### Task 6: ADR 0041 + sprint-28 page + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0041-sprint-28-process-enforcement.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-28-process-enforcement.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md`
- Modify: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Write ADR 0041**

Standard format. Decision: mechanical enforcement via hook + Russian process docs as single source of truth для operator.

- [ ] **Step 2: Write sprint-28 page**

- [ ] **Step 3: Update index.md** — entries для new docs + sprint-28 + ADR 0041

- [ ] **Step 4: Update current-state.md** — sprint history row +S28, canonical counts (40 → 41 ADRs, 27 → 28 sprint pages)

- [ ] **Step 5: Append log.md** — sprint-end entry

- [ ] **Step 6: Commit**

### Task 7: PHASE 8 ship per sprint-finish skill

- [ ] **Step 1: Pre-validation**

```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
```

- [ ] **Step 2: Touch agent prompts (ADR sync hook compliance)**

- [ ] **Step 3: Push branch**

```bash
git push -u origin feature/sprint-28-process-enforcement
```

- [ ] **Step 4: gh pr create**

- [ ] **Step 5: gh pr merge --squash --delete-branch**

- [ ] **Step 6: Tag v0.1.0-alpha.28**

```bash
git tag -a v0.1.0-alpha.28 -m "Sprint 28 — Process enforcement + Russian tooling docs" <merge-sha>
git push origin v0.1.0-alpha.28
```

- [ ] **Step 7: SPRINT_STATE → between-sprints**

---

## Self-Review Checklist

- [ ] Каждая task имеет file paths
- [ ] HARD-GATE explicit per phase
- [ ] Hook script bash -n verified
- [ ] Russian docs structure скелет ясен
- [ ] CLAUDE.md binding section включает phase numbering
- [ ] No placeholders ("TBD", "TODO")

---

## Execution mode

**Subagent-Driven** — fresh subagent per task с two-stage review. Implementer subagent invokes TDD where applicable.

ИЛИ controller-driven если задачи в основном docs (не code) — сейчас в S28 это уместно, экономит overhead.

**Recommended:** controller-driven для T1+T2+T4+T5+T6 (docs/wiki only), subagent для T3 (hook script — code + bash test).
