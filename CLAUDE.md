# CLAUDE.md — AI Trading Bot v0.1 (repo root)

Этот файл — bootstrap anchor. Claude Code авто-грузит его при старте сессии в этом репозитории.

## ⚠️ BEFORE ANY SPRINT WORK — kit flow обязателен (BINDING per ADR 0041 + ADR 0042)

Любая работа касающаяся sprint = MUST follow 9 phases. NO shortcuts. NO "очевидно skip". 26 skills integrated (13 superpowers + 5 project + 8 agent-skills).

| Phase | Primary skill(s) | Optional/sub-skills | HARD-GATE |
|-------|------------------|---------------------|-----------|
| 1 Orient | `sprint-orient` (project) | — | Chapter marked + SPRINT_STATE read |
| 2 Brainstorm | `brainstorm-init` (project) → `trader-expert` | `superpowers:brainstorming` (non-trading scope) | `pre-s{N}-backlog.md` |
| 3 Plan | `superpowers:writing-plans` | `agent-skills:planning-and-task-breakdown` (DEPTH ref) | **Hook `sprint-flow-check.sh` блокирует push без plan file** |
| 4 Execute | `superpowers:subagent-driven-development` (code) OR `superpowers:executing-plans` (docs) + `superpowers:test-driven-development` | `superpowers:systematic-debugging` (bug sub-flow), `superpowers:dispatching-parallel-agents` (parallel reviewers), `agent-skills:context-engineering` (briefs > 200 слов) | Per-task TDD + per-task SPRINT_STATE update |
| 5 Verify | `superpowers:verification-before-completion` | pytest + mypy + canonical counts | All GREEN per checklist + 🔒 **Hook `phase-advance.sh` (S30+) блокирует merge если Phase 5 status != "done"/"skipped"** |
| 6 Review | Domain reviewer (L5: trading-logic / quant-stats / data-integrity / architecture / python) + `superpowers:requesting-code-review` (brief format) + `superpowers:receiving-code-review` (feedback processing) | **`security-auditor` (money/API/override) + `test-engineer` (new modules / coverage gaps) + `doc-reviewer` (post wiki-update)** 🆕 (S30) + `superpowers:dispatching-parallel-agents`, `agent-skills:code-review-and-quality`, `agent-skills:security-and-hardening` | Blockers addressed |
| 7 Sync | `wiki-update` (project) | — | Block 1↔Block 2 sync |
| 8 Ship | `sprint-finish` (project) → `superpowers:finishing-a-development-branch` | `agent-skills:git-workflow-and-versioning`, `agent-skills:shipping-and-launch` | tag v0.1.0-alpha.N |
| 9 Close | SPRINT_STATE between-sprints + log session-end | — | — |

**Cross-phase optional skills:**
- `superpowers:using-git-worktrees` — sandbox/parallel sprint experiments (rare)
- `superpowers:writing-skills` — создание new project skill (`.claude/skills/`)
- `superpowers:using-superpowers` — meta auto-loaded session start

**Per-task SPRINT_STATE update протокол (PHASE 4) — BINDING:**
После КАЖДОЙ task complete (НЕ только в конце спринта):
1. Edit `llm-wiki/wiki/project/SPRINT_STATE.md` Phase 4 task table
2. Update "Текущий статус" + "Следующее действие"
3. Update `updated:` frontmatter
4. Optional: commit `docs(sprint): SPRINT_STATE update phase=4 task=Tx done`

**Полный процесс на русском:** [`llm-wiki/wiki/project/architecture/sprint-flow-ru.md`](llm-wiki/wiki/project/architecture/sprint-flow-ru.md)
**Каталог tooling (9 agents + 26 skills × phases mapped + cascade):** [`llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`](llm-wiki/wiki/project/architecture/tooling-inventory-ru.md)

### LLMWiki ↔ Claude-mem cascade rule (BINDING per ADR 0043 — token economy)

При любом lookup (decision / pattern / API / past learning) — следуй cascade order:

```
STEP 1: wiki/<page>.md    (curated, structured)   ← CHECK FIRST
   ↓ not found
STEP 2: mem-search        (past sessions semantic)
   ↓ not found
STEP 3: Grep raw          (current code state)
   ↓ needed
STEP 4: Read raw + offset (full content)
```

Полный rationale + examples: [`tooling-inventory-ru.md` Section 13](llm-wiki/wiki/project/architecture/tooling-inventory-ru.md).

**Anti-pattern:** ❌ Skip wiki check → mem-search OR Read raw напрямую (loses curation, increases tokens).

### Анти-patterns (НЕ делать)
- ❌ Прямой `Agent` dispatch вместо `brainstorm-init` / `writing-plans` / `subagent-driven-development` skills
- ❌ Code на feature/sprint-* branch без plan file в `wiki/project/plans/` — hook БЛОКИРУЕТ push
- ❌ SPRINT_STATE update только в конце спринта (Phase 4 protocol требует per-task)
- ❌ Batch commit "all of S{N}" в одном commit
- ❌ Skip фазу потому что "очевидно" / "тривиально"
- ❌ Bug ad-hoc fix без `superpowers:systematic-debugging` (skip → recurrence risk)
- ❌ Sequential reviewers где `superpowers:dispatching-parallel-agents` подходит (2-3× slower)
- ❌ Verify через "looks ok" вместо `superpowers:verification-before-completion` checklist
- ❌ Reviewer brief ad-hoc без `superpowers:requesting-code-review` skill format
- ❌ Reviewer feedback ad-hoc без `superpowers:receiving-code-review` categorization
- ❌ Создать new project skill без `superpowers:writing-skills` methodology
- ❌ 🆕 Money/API/override/Mainnet code change без `security-auditor` agent invocation
- ❌ 🆕 New module ship без `test-engineer` coverage analysis
- ❌ 🆕 Skip wiki check (cascade STEP 1) → jump straight к mem-search OR Read raw
- ❌ 🆕 Merge sprint без Phase 5 status="done" в SPRINT_STATE (`phase-advance.sh` блокирует)
- ❌ 🆕 (S31) Kitchen-sink session — long context с irrelevant accumulation. Use `/clear` between unrelated tasks
- ❌ 🆕 (S31) Side question в main thread — pollutes context. Use `/btw` instead
- ❌ 🆕 (S31) Correcting same issue 3+ times — context cluttered с failed approaches. Use `/clear` + better prompt
- ❌ 🆕 (S31) CLAUDE.md > 250 lines per file — bloated файл = ignored rules per best practices

### Token-saver commands (per Anthropic best practices)

| Command | Use case |
|---------|----------|
| `/btw <question>` | Side question — answer dismissed, не enters history |
| `/rewind` (Esc+Esc) | Restore previous state — experimental approach failed |
| `/clear` | Reset context — switching unrelated tasks |
| `/compact <instructions>` | Controlled summarization — approaching limit |
| `claude --continue` | Resume последнюю session |
| `claude --resume` | Choose из recent sessions |
| `claude -p "<prompt>"` | Non-interactive (CI/CD, batch operations) |
| `--allowedTools` | Scoped permissions для batch ops |

Detail: [[llm-wiki/wiki/project/architecture/tooling-inventory-ru.md#18-token-saver-commands-binding--best-practices]]

## ПЕРВОЕ ДЕЙСТВИЕ КАЖДОЙ СЕССИИ (обязательно, до всего остального)

```
1. Read: llm-wiki/wiki/project/SPRINT_STATE.md
   → sprint N, phase X, completed tasks, next_action
2. Read: llm-wiki/CLAUDE.md
   → wiki workflow + 5-layer skills hierarchy + token economy + trigger cascade
3. git branch --show-current && git log --oneline -3
4. mcp__ccd_session__mark_chapter "Sprint N — session resume"
```

**Если `SPRINT_STATE.md` говорит `phase = 4-execution` и есть `in_progress` task:**
```
git status → pytest tests/unit -x -q → продолжай с next_action
```

## ПОСЛЕДНЕЕ ДЕЙСТВИЕ КАЖДОЙ СЕССИИ (перед закрытием)

```
1. Edit llm-wiki/wiki/project/SPRINT_STATE.md:
   → phase, in_progress, next_action, updated date
2. Append llm-wiki/wiki/log.md session-end entry
3. mcp__ccd_session__mark_chapter "Sprint N — session end"
4. git commit -m "docs(sprint): update SPRINT_STATE phase/progress"
```

## Ключевые файлы (navigation anchors)

| Файл | Роль |
|------|------|
| `llm-wiki/wiki/project/SPRINT_STATE.md` | Living sprint state (≤2KB) — FIRST READ |
| **`llm-wiki/wiki/project/architecture/kit-overview-ru.md`** | **Single source of truth gateway (S31) — 1-page TL;DR всех kit settings** |
| `llm-wiki/CLAUDE.md` | Wiki maintainer rules + 5-layer skills hierarchy + trigger cascade |
| `llm-wiki/wiki/project/architecture/development-workflow.md` | MASTER SOP — 9-phase sprint lifecycle |
| `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` | Russian обязательный 9-фаз процесс с per-phase HARD-GATEs (S28 BINDING) |
| `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` | Catalog: 9 reviewer agents + 26 skills + 6 MCP + 6 hooks + cascade rule + 19 sections |
| `llm-wiki/wiki/index.md` | Wiki catalog (all pages) |
| `llm-wiki/wiki/log.md` | Chronological sprint journal |
| `llm-wiki/wiki/project/decisions/` | ADRs (0001-0023) |
| `llm-wiki/wiki/project/components/` | Component docs (wiki-first reads before raw ADR) |
| `llm-wiki/wiki/project/sprints/sprint-NN-<slug>.md` | **Canonical sprint summary** — "что было сделано в спринте N". HARD-GATE creation per dev-workflow.md PHASE 8 step 5. Read для понимания исторического контекста. |
| `llm-wiki/wiki/project/pre-s{N}-backlog.md` | Pre-sprint backlog — gaps + bugs to discharge before brainstorm S{N}. Создаётся когда post-sprint audit находит actionable items. Закрывается → удаляется. |
| `llm-wiki/wiki/project/mental-map.md` | "Where to look for X" decision tree — first-hit для open-ended queries. Заменяет blind grep. |
| `llm-wiki/wiki/project/components/README.md` | 27 components grouped в 9 domain clusters. Reverse lookup ("I'm reading X — what's related?"). |
| `.claude/skills/<name>/SKILL.md` | **Project-level workflow skills** (5 total: sprint-orient, sprint-finish, wiki-update, brainstorm-init, hook-test). Auto-trigger по description match — заменяют hardcoded inline workflow logic. См. `llm-wiki/wiki/index.md` "Workflow Skills" section. |
| `~/.claude/agents/<name>.md` | **L5 reviewer agents** (6: trading-logic, quant-stats, data-integrity, python, trader-expert, architecture-reviewer) — user-level, outside repo. ADR 0017 review-agent harness. |

## Project constraints (short form)

- **Python**: 3.12 (pyproject.toml). Venv: `.venv/` at repo root.
- **Test cmd**: `pytest -x -q` (unit), `pytest -m integration` (opt-in), `pytest -m property`.
- **Branch**: feature/<sprint-N-slug>. PR to main. Conventional commits.
- **Current state**: Sprint 8c COMPLETE (tag `v0.1.0-alpha.8c`). Between sprints. Next = S9 brainstorm.

## Workflow skills (project-level, `.claude/skills/`)

**5 skills заменяют hardcoded inline workflow logic:**

| Skill | Trigger | Replaces |
|-------|---------|----------|
| `sprint-orient` | Session start, `/clear`, "где мы", "ориентируйся" | PHASE 1 inline orient sequence |
| `sprint-finish` | "ship", "финишируем", subagent-driven completion | PHASE 8 HARD-GATE checklist |
| `wiki-update` | After src/ change, "sync docs" | PHASE 8 step 5a inline canonical counts sync |
| `brainstorm-init` | "брейнштурм", scope questions surface | PHASE 2 step 3a-3f binding protocol |
| `hook-test` (explicit only) | `/hook-test` invocation | Manual env -i sandbox commands |

**ВАЖНО:** skills auto-trigger по description match. Inline workflow logic в этом CLAUDE.md и в `dev-workflow.md` теперь references к SKILL.md, НЕ дублируется. Полная procedure — в `.claude/skills/<name>/SKILL.md` per progressive disclosure.

**PHASE 2 binding protocol полностью реализован в `brainstorm-init` skill** (structured questionnaire → trader-expert ROUND 1 → iterative justify ROUND 2 на REVISE-disagreement → CONFIRM_REVISE/CHANGED BINDING → backlog persistence + user escalation).

**PHASE 8 HARD-GATE checklist полностью в `sprint-finish` skill** (sprint-NN.md mandatory, canonical counts sync, orphan-audit grep includes tests/, index.md ADR sync).

**Anti-pattern:** дублировать workflow steps inline в этом файле OR в dev-workflow.md — skills are single source of truth.

## Python venv discipline (MANDATORY for all Bash invocations)

System macOS Python = **3.9** → `ImportError: cannot import name 'StrEnum' from 'enum'` on any `src.execution.state_machine` import. Bare `python` does not exist on PATH (exit 127). Project uses `StrEnum`, PEP 604 unions, modern `pydantic-settings` — needs **3.12**.

**Rule for controller AND every subagent brief:**
- ALWAYS prefix Python invocations with venv:
  - `source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate && python -c "..."`
  - OR direct path: `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/python -c "..."`
- Same for tools: `.venv/bin/pytest`, `.venv/bin/mypy`, `.venv/bin/ruff`.
- NEVER bare `python` / `python3` — fails or returns wrong-Python results.
- When dispatching subagent that may run Python — explicitly include venv path in brief.

## Language rules (BINDING — пересмотрено 2026-05-09)

| Канал | Язык | Rationale |
|-------|------|-----------|
| **Чат с operator** (responses, questions, sprint reports) | **Русский** | User-facing |
| **ADR** в `llm-wiki/wiki/project/decisions/*.md` | **Русский** | User reads directly |
| **Wiki pages** в `llm-wiki/wiki/` (components, sprints, architecture, strategies) | **Русский** | User-facing knowledge base |
| **Sprint summaries / brainstorm verdicts / plan files** | **Русский** | User reviews |
| **Subagent inter-communication** (briefs to agents, agent prompts/responses) | **English** | Productivity boost — agents trained на English; внутренний канал |
| **Code / identifiers / file paths** | **English** | Tooling convention |
| **Code comments в `src/`** | **English** | Production standard |
| **Code comments в `research/`** | **Russian OK** | Research toy paradigm |
| **Commit messages** | **English** | Conventional Commits standard |
| **Error messages в коде** | **English** | Logging standard |

Технические термины (file paths, code blocks, error strings, command names, library names) — оставлять как есть (без перевода) внутри русского текста.

## Kit cycle MANDATORY (BINDING per ADR 0041 — пересмотрено 2026-05-09)

ВСЕГДА следовать 9-фазовому kit cycle (PHASE 1-9 per `dev-workflow.md`), КРОМЕ:
- Operator explicitly says "**autoresearch**" / "**запусти autoresearch**" / "**autoresearch N итераций**"
- В этом случае — **bypass kit**, follow `research/program.md` autoresearch toy rules
- После autoresearch завершения — **return к kit cycle** для production integration (если PASS found)

**Anti-patterns:**
- ❌ Skip kit потому что "очевидно" / "тривиально" / "быстро"
- ❌ Code на feature/sprint-* branch без plan file (hook `sprint-flow-check.sh` БЛОКИРУЕТ push)
- ❌ Merge sprint без Phase 5 status="done" (hook `phase-advance.sh` БЛОКИРУЕТ)

## Minimum behavior

- Read before edit. TDD strict (RED→GREEN→COMMIT).
- YAGNI, DRY, KISS. No "улучшения" сверх scope.
- Token economy: wiki-first (components/ before raw ADR), mem-search first (`mcp__plugin_claude-mem_mcp-search__smart_search`), parallel reviewers, model dispatch (sonnet default, opus for judgment-heavy, haiku for mechanical).

## Skills hierarchy (5 layers — detail в `llm-wiki/CLAUDE.md`)

```
L5: Domain reviewers     (trading-logic / quant-stats / data-integrity / python-reviewer / trader-expert / architecture-reviewer)
L4: Agent Skills + Caveman (depth checklists, compression)
L3: Superpowers          (brainstorm → plan → subagent-driven → TDD → finishing)
L2: llm-wiki             (source of truth — read THIS BEFORE raw files)
L1: claude-mem + ccd_session (session bookends + chapter marks)
```

## Read tool guard (большие файлы)

Hard-limit ~25k токенов = ~90KB. Если файл > 50KB — `Read` с `offset`+`limit` или `Grep`-first. Полный список banned-from-full-read файлов → `~/.claude/CLAUDE.md` секция 9.

## Anti-waste tool patterns (BINDING — CRITICAL)

| Pattern | Rule | Cost on miss |
|---------|------|--------------|
| **Edit-after-Read** | Read × N batch THEN Edit × N batch (never skip STEP 1) | 3× per unread file |
| **Path verification** | `AI_Traiding_Bot` exact spelling. Verify via `pwd` если doubt. Don't-retry on Read miss (max 1 retry). | hallucination compounds |
| **MEMORY.md tolerance** | `.claude/agent-memory/<agent>/MEMORY.md` (**project-local**, NOT `~/.claude/agent-memory/`) may NOT exist (created on first WRITE). | wasted Read |
| **Hook bash quirk** | `bash -n <script>` after editing `~/.claude/hooks/*.sh`. Triple-backtick inside heredoc fails. | push fails → debug cycle |

Полные правила: `~/.claude/CLAUDE.md` sections 9b + 9c, `llm-wiki/CLAUDE.md` "Anti-waste tool patterns".

---

**Полная методология** → `llm-wiki/CLAUDE.md` + `llm-wiki/wiki/project/architecture/development-workflow.md`.
