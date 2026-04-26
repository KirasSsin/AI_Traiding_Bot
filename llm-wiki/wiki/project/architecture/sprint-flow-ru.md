---
title: Sprint Flow — обязательный процесс kit'а (русская версия)
type: architecture
tags: [workflow, sprint-lifecycle, kit, hard-gates, enforcement, ru]
created: 2026-04-26
updated: 2026-04-26
status: stable
sources:
  - project/architecture/development-workflow.md (английский оригинал, более детальный)
  - project/decisions/0041-sprint-28-process-enforcement.md
  - project/decisions/0017-review-agent-harness.md
  - .claude/skills/sprint-orient/SKILL.md
  - .claude/skills/brainstorm-init/SKILL.md
  - .claude/skills/sprint-finish/SKILL.md
  - .claude/skills/wiki-update/SKILL.md
---

# Sprint Flow — обязательный процесс (RU)

> **Это binding процесс.** Любая работа над спринтом ОБЯЗАНА пройти ВСЕ 9 фаз.
>
> Hook `~/.claude/hooks/sprint-flow-check.sh` блокирует push на ветку
> `feature/sprint-NN-*` без plan file в `wiki/project/plans/`.
>
> Catalog tooling: [[tooling-inventory-ru]]

## Зачем мы это делаем

Последние 12 спринтов (S16-S27) показали drift: kit постепенно ослаблялся под
нагрузкой. Конкретно S27 нарушил:
- Прямой `Agent` dispatch вместо `superpowers:brainstorming` или `brainstorm-init` skill
- Нет plan file в `wiki/project/plans/` (последний — S15)
- `superpowers:writing-plans` пропущен
- `superpowers:subagent-driven-development` пропущен (controller-driven вместо)
- SPRINT_STATE updated только в конце спринта, не после каждой задачи

Root cause: kit invocation = polite reminder в CLAUDE.md, не enforcement.
Решение: hook + Russian docs + per-task SPRINT_STATE protocol = mechanical gate.

## Обзор фаз (9)

| Фаза | Название | Триггер | HARD-GATE | Артефакт |
|------|----------|---------|-----------|----------|
| 1 | Orient | Старт сессии / `/clear` | SPRINT_STATE прочитан + git verified | `mcp__ccd_session__mark_chapter` |
| 2 | Brainstorm | Open scope/design questions | Все Q processed через trader-expert ROUND 1 (+ROUND 2 на REVISE-disagreement) | `wiki/project/pre-s{N}-backlog.md` |
| 3 | Plan | Brainstorm verdicts locked | Plan file в `wiki/project/plans/` создан (HARD-GATE — hook блокирует push без него) | `wiki/project/plans/<date>-sprint-N-<slug>.md` |
| 4 | Execute | Plan committed | TDD per task + per-task commit + SPRINT_STATE update после КАЖДОЙ task | git commits |
| 5 | Verify | All tasks done | pytest GREEN + mypy clean + canonical counts current | test output |
| 6 | Review | Verify passed | Domain reviewer (L5) per touched area + (если требуется) parallel reviewers | review reports |
| 7 | Sync | Review passed | wiki update — components + ADR + sprint page + index + log | wiki diffs |
| 8 | Ship | Wiki synced | sprint-NN.md + counts + orphan-audit + index sync (per `sprint-finish` skill) | tag v0.1.0-alpha.N + PR merge |
| 9 | Close | Tag pushed | SPRINT_STATE → between-sprints + log session-end | SPRINT_STATE |

---

## Phase 1: Orient (старт сессии)

### Триггер
- Старт сессии в проекте
- После `/clear`
- "Где мы остановились" / "ориентируйся заново"
- Switch context между sprints

### Procedure
**Использовать skill:** `.claude/skills/sprint-orient/SKILL.md`

```
1. Read llm-wiki/wiki/project/SPRINT_STATE.md
   → sprint N, phase X, branch, tag, "Следующее действие"
2. git branch --show-current && git log --oneline -3
3. Verify branch matches SPRINT_STATE — flag mismatch если разные
4. Read llm-wiki/wiki/log.md (offset+limit, не full file)
   → recent decisions
5. Read canonical-counts table в current-state.md
6. mcp__ccd_session__mark_chapter "Sprint N — session resume"
```

### HARD-GATE
- ✅ SPRINT_STATE прочитан полностью
- ✅ git branch verified против SPRINT_STATE
- ✅ Chapter marked
- ❌ Не начинай code пока orient не завершён

### Output к user
8 bullets max:
- Sprint N, phase X, branch Y, tag Z
- Last commit
- Recent log events (top 3)
- Canonical counts
- Carry-overs если есть
- Next action

---

## Phase 2: Brainstorm (scope/design questions)

### Триггер
- Новый sprint начало с open scope/architecture questions
- Carry-over decisions от prior sprint требуют resolution
- User says "брейнштурм S<N>", "scope sprint", "design questions"
- Pre-S{N} backlog имеет Bucket B (user bugs) OR Bucket D (architectural decisions)

### Skip when
- Sprint = pure execution of approved ADR (no new decisions)
- Operator уже specified deliverables (как в S28 — process enforcement clear)

### Используемые skills

| Skill | Когда |
|-------|-------|
| **`agent-skills:idea-refine`** 🆕 (S32) | Phase 2 PRE — vague operator idea перед brainstorm-init. Структурированный divergent → convergent thinking. Применять когда scope = "что-то улучшить" без конкретики. |
| **`brainstorm-init`** (project) → `trader-expert` agent | Trading scope/strategy/parameter questions (PRIMARY для нашего домена) |
| **`superpowers:brainstorming`** | Non-trading scope (process design, infrastructure) — Socratic refinement через clarifying questions one-at-a-time |
| **`agent-skills:spec-driven-development`** 🆕 (S32) | Phase 2/3 — non-trading features без spec (dashboard / CLI / infrastructure). Создаёт spec с acceptance criteria ДО plan writing. Применять когда: новая UI feature, новая CLI команда, новый module без ADR. NOT для trading strategies (используй trader-expert). |

### Procedure (idea-refine PRE-step — S32c extension)

**Use когда:** operator vague idea без concrete deliverables (e.g., "что-то улучшить в кит'е", "оптимизация", "ускорить"). Skip если operator уже specified deliverables (S28-S32 pattern: explicit task list).

```
1. Operator vague idea → invoke `agent-skills:idea-refine` skill
2. Skill structures divergent thinking:
   - Generate 3-5 alternative refinements (broader scope variants)
   - Identify constraints + success criteria
3. Convergent thinking:
   - Compare alternatives через tradeoff matrix
   - Select 2-3 best для brainstorm-init questionnaire
4. Output: refined option list с tradeoffs documented
5. THEN → brainstorm-init skill (trader-expert ROUND 1 на refined options)

Anti-pattern: skip idea-refine на vague idea → trader-expert получает unfocused questionnaire → poor verdicts → wasted ROUND 2.
```

### Procedure (trader-expert path)
**Использовать skill:** `.claude/skills/brainstorm-init/SKILL.md`

```
1. Collect open questions (carry-overs + user input + prior sprint open issues)
2. Build structured questionnaire (5 fields per question):
   - Question (verbatim)
   - Maintainer recommended option
   - Alternatives considered (a/b/c)
   - Reasoning for recommended (wiki/ADR/code refs)
   - Risk/concern
3. Dispatch trader-expert ROUND 1 (через `Agent(subagent_type="trader-expert")`)
4. Process verdicts:
   - CONFIRM → option locked
   - REVISE (option == maintainer's) → option locked + trader rationale
   - REVISE (option != maintainer's) → MUST go to ROUND 2 iterative justify
   - DEFER → к S{N+1}+
   - EXPAND → re-brainstorm
5. ROUND 2 (на REVISE-disagreement):
   - Re-evaluate, side-by-side compare, fresh research
   - Returns CONFIRM_REVISE OR CHANGED — BINDING, no round 3
6. Document verdicts в `wiki/project/pre-s{N}-backlog.md`
7. User escalation (только trader's escalation list — product/regulatory/business)
```

### HARD-GATE
- ✅ Каждая question processed через trader-expert ROUND 1
- ✅ REVISE-disagreement → ROUND 2 invoked (НЕ принимать REVISE без round 2 если maintainer disagree)
- ✅ Verdicts persisted в pre-s{N}-backlog.md
- ❌ НЕ asking user scope/architecture question напрямую без trader-expert ROUND 1

### Anti-patterns
- ❌ Прямой Agent dispatch без brainstorm-init skill structure
- ❌ Skipping trader потому что "очевидно" (S8c Q1 caught DELETE bracket.py = catastrophe)
- ❌ Третий round trader (ROUND 2 BINDING)
- ❌ Использовать `superpowers:brainstorming` для trading scope (use `brainstorm-init` → `trader-expert` чтобы не пропустить domain knowledge)

---

## Phase 3: Plan (writing-plans)

### Используемые skills

| Skill | Когда |
|-------|-------|
| **`superpowers:writing-plans`** | PRIMARY — comprehensive implementation plan |
| **`agent-skills:planning-and-task-breakdown`** | DEPTH reference (не replacement) — checklist для task decomposition quality |
| **`agent-skills:api-and-interface-design`** 🆕 (S32c) | CLI commands / module boundaries / endpoint design — stable interface contracts ДО implementation. Use когда Phase 3 plan включает new public API surface (REST endpoint / CLI subcommand / module exports). |

### Триггер
- PHASE 2 verdicts locked
- Sprint scope зафиксирован
- ADR proposed status

### Procedure
**Использовать skill:** `superpowers:writing-plans`

```
1. Inherit context from PHASE 2 (ADR + backlog verdicts)
2. Map file structure (which files create/modify, responsibilities)
3. Decompose в bite-sized tasks (2-5 minutes per step)
4. Write plan в `wiki/project/plans/<YYYY-MM-DD>-sprint-N-<slug>.md`
5. Format:
   - Header (goal / architecture / tech stack)
   - Context (link to ADR + spec)
   - File Structure (decomposition decisions)
   - Task Breakdown (per-task с file paths + steps + commands + commit messages)
   - Self-Review Checklist
   - Execution mode (subagent-driven OR controller-driven)
6. Self-review: spec coverage / placeholder scan / type consistency
```

### HARD-GATE (mechanical — hook enforced)
- ✅ Plan file существует в `wiki/project/plans/<YYYY-MM-DD>-sprint-N-<slug>.md`
- ✅ Pattern: `^[0-9]{4}-[0-9]{2}-[0-9]{2}-sprint-N-.+\.md$`
- ❌ Hook `sprint-flow-check.sh` БЛОКИРУЕТ push на feature/sprint-* branch без plan file

### Anti-patterns
- ❌ "TBD", "TODO", "implement later" placeholders в plan
- ❌ "Add appropriate error handling" (vague — needs explicit list)
- ❌ "Similar to Task N" (repeat code — engineer может читать out of order)
- ❌ Steps без code blocks где нужен код

---

## Phase 4: Execute (TDD + per-task SPRINT_STATE)

### Триггер
- Plan committed к branch
- SPRINT_STATE phase=4-execution

### Используемые skills

| Skill | Когда |
|-------|-------|
| **`superpowers:subagent-driven-development`** | PRIMARY для code-heavy sprints — fresh subagent per task с two-stage review |
| **`superpowers:executing-plans`** | ALTERNATIVE — controller-driven (docs/wiki sprints, batch execution с checkpoints) |
| **`superpowers:test-driven-development`** | КАЖДАЯ task с code change — RED → GREEN → COMMIT |
| **`superpowers:systematic-debugging`** | Bug encountered during execution — 4-phase root cause (reproduce → localize → fix → guard) |
| **`superpowers:dispatching-parallel-agents`** | Parallel reviewer dispatch (multiple Agent calls в одном message) |
| **`superpowers:requesting-code-review`** | Format request к L5 reviewer (context + diff + specific concerns) |
| **`agent-skills:test-driven-development`** | DEPTH reference — anti-patterns, pyramid, DAMP |
| **`agent-skills:incremental-implementation`** | DEPTH reference — thin vertical slices |
| **`agent-skills:context-engineering`** | Subagent briefs > 200 слов — right context, right time |
| **`agent-skills:source-driven-development`** 🆕 (S32) | Bybit API / pydantic / pybit / FastAPI / TA-Lib tasks — verify против official docs ДО implementation. Prevents API misuse bugs (S8a/S8b regression vector). Применять при touching: `src/execution/bybit/`, dependency updates, new external API integration. |

#### Subagent-driven (preferred для code-heavy sprints)
```
1. Extract all tasks с full text (don't make subagent read plan)
2. Create TodoWrite с all tasks
3. Per task:
   a. Dispatch implementer subagent с full task text + scene-setting context
   b. Implementer asks questions → answer перед work begins
   c. Implementer implements TDD (RED → GREEN → COMMIT) → self-review
   d. Spec compliance reviewer subagent → verifies code matches spec
   e. Code quality reviewer subagent → approves
   f. Re-review loops если issues found
   g. TodoWrite mark complete
   h. **Update SPRINT_STATE Phase 4 task table**
4. After all tasks → final code-reviewer subagent
5. → Phase 5 Verify
```

#### Controller-driven (preferred для docs/wiki sprints)
```
1. TodoWrite с all tasks
2. Per task:
   a. TDD (если applies) — write failing test first
   b. Implement minimal change
   c. Verify (pytest / bash -n / etc)
   d. Commit
   e. **Update SPRINT_STATE Phase 4 task table** ← ОБЯЗАТЕЛЬНО after EACH task
   f. TodoWrite mark complete
```

### Per-task SPRINT_STATE update протокол (BINDING)

После КАЖДОЙ task complete (НЕ только в конце спринта):

```
1. Edit llm-wiki/wiki/project/SPRINT_STATE.md:
   - Update Phase 4 task table row (status / commit SHA)
   - Update "Текущий статус" section если milestone
   - Update "Следующее действие" — что дальше
   - Update updated: frontmatter
2. (Optional) git commit:
   git add llm-wiki/wiki/project/SPRINT_STATE.md
   git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=Tx done"
```

### HARD-GATE
- ✅ TDD strict если code (RED → GREEN → COMMIT)
- ✅ SPRINT_STATE updated после КАЖДОЙ task
- ✅ TodoWrite используется как phase tracker, не ad-hoc
- ✅ Per-task git commit (не batch commit в конце)
- ❌ Skip review loops если reviewer found issues

### Sub-flow: Bug encountered during Phase 4

Если bug found во время execution:

```
1. STOP current task
2. Invoke `superpowers:systematic-debugging` skill (4-phase):
   a. Reproduce — minimal failing test case
   b. Localize — narrow to specific function/line
   c. Fix — minimal change addressing root cause (не симптом)
   d. Guard — regression test added
3. Commit fix с reference к bug
4. Resume original task
```

Don't ad-hoc guess fixes. Don't add "defensive" code без understanding root cause.

### Sub-flow: Parallel reviewers / agents

**`superpowers:dispatching-parallel-agents`** — explicit pattern для concurrent work:

```python
# Single message, multiple Agent tool calls:
Agent(subagent_type="trading-logic-reviewer", prompt=...)
Agent(subagent_type="quant-stats-reviewer", prompt=...)
Agent(subagent_type="python-reviewer", prompt=...)
```

Применять когда reviewers/research independent. NOT для sequential work с dependencies.

### Anti-patterns
- ❌ Batch commit "all of S28" в одном commit
- ❌ SPRINT_STATE update только в конце спринта (drift risk)
- ❌ TodoWrite пропущен потому что "memory достаточно"
- ❌ Subagent dispatch с "read plan file для context" (controller предоставляет full text)
- ❌ Bug found → ad-hoc fix без `systematic-debugging` skill (skip → recurrence risk)
- ❌ Sequential reviewers где parallel possible (2-3× slower, no `dispatching-parallel-agents` use)

---

## Phase 5: Verify (pytest + mypy + counts)

### Триггер
- All Phase 4 tasks done
- TodoWrite all completed

### Используемые skills

| Skill | Когда |
|-------|-------|
| **`superpowers:verification-before-completion`** | PRIMARY — pre-completion checklist (tests / linter / runtime check / edge cases) |
| **`agent-skills:browser-testing-with-devtools`** 🆕 (S32c) | Phase 5 для dashboard sprints (S25/S26-class) — Chrome DevTools MCP runtime verification (DOM / console errors / network requests / visual output). Requires Chrome MCP enabled (✓ via Claude_in_Chrome MCP). |

### Procedure
```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
mypy --strict src/ 2>&1 | tail -3
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

`verification-before-completion` skill — extended checklist beyond pytest/mypy:
- Tests pass (всех типов: unit / integration / property где applies)
- Linter clean (ruff)
- Runtime smoke check (если applies — import module, run CLI command)
- Edge cases verified (empty input, boundary values, error paths)
- Documentation updated (если public API changed)

### HARD-GATE
- ✅ pytest 0 new failures (baseline preserved)
- ✅ mypy ≤ baseline (S8c baseline = 44 errors)
- ✅ Canonical counts текущие
- ✅ `verification-before-completion` checklist passed
- ✅ SPRINT_STATE Phase 5 status updated → "done" (или "skipped (reason)")
- ❌ STOP если pytest fails — fix перед Phase 6
- 🔒 **Hook `phase-advance.sh` (S30+) блокирует `gh pr merge` если Phase 5 status != "done"/"skipped"** — mechanical enforcement

---

## Phase 6: Review (L5 domain reviewers + superpowers review skills)

### Триггер
- Phase 5 verify passed
- Code changes touched specific layers

### Используемые skills

| Skill | Когда |
|-------|-------|
| **`superpowers:requesting-code-review`** | Format request к L5 reviewer — context + diff + specific concerns + file refs |
| **`superpowers:receiving-code-review`** | Process reviewer feedback systematically — categorize blockers/concerns/suggestions, address per category |
| **`superpowers:dispatching-parallel-agents`** | Multiple reviewers (trading-logic + quant-stats + python) — single message с multiple Agent calls |
| **`agent-skills:code-review-and-quality`** | DEPTH reference — five-axis review checklist |
| **`agent-skills:security-and-hardening`** | MUST для money / API key / override.py changes |
| **`agent-skills:code-simplification`** 🆕 (S32) | Phase 6 OPTIONAL — post-implementation cleanup сложных формул / accumulated complexity. Simplify without behavior change (regression test guards). Применять когда: file > 300 LoC после feature add, formula код после S27-class fixes, перед merge sprint touching `src/{backtest,signalgen,risk}/`. NOT для new code (используй incremental-implementation). |
| **`agent-skills:performance-optimization`** 🆕 (S32c) | Phase 6 OPTIONAL — backtest/replay sprints touching `src/backtest/`. Profile FIRST через cProfile/timeit перед optimize ("measure first, optimize only what matters"). Replay engine 5y backfill iteration speed. NOT для premature optimization. Применять когда: backtest run > 30 sec, WFA fold count blow up, vector_backtest memory > 1GB. |

### Procedure (per touched layer)

| Touched | Reviewer | Mandatory? |
|---------|----------|-----------|
| `src/signalgen/`, `src/execution/`, `src/backtest/`, `src/risk/` | trading-logic-reviewer | YES |
| `src/signalgen/indicators.py`, `src/risk/`, `src/backtest/`, `src/analytics/` (math) | quant-stats-reviewer | YES если формулы тронуты |
| `src/marketdata/`, `src/platform/storage/`, `migrations/` | data-integrity-reviewer | YES |
| Cross-module refactor / concurrency / DI / API stability | architecture-reviewer | YES |
| Любой `*.py` (generic safety net) | python-reviewer | YES (после domain) |
| **Money / API keys / override.py / HMAC / signing / withdraw / Mainnet** 🆕 (S30) | **security-auditor** (opus) | YES для money paths |
| **New module без tests / coverage gap / property test design** 🆕 (S30) | **test-engineer** (sonnet) | YES для new modules |
| **Wiki consistency check** 🆕 (S30) | **doc-reviewer** (haiku) | YES после wiki-update skill |
| Money / API keys / override / signing (additional checklist) | + `agent-skills:security-and-hardening` | YES (вместе с security-auditor) |

### Procedure (using superpowers review skills)

```
1. PRE-REVIEW (controller):
   - Use `superpowers:requesting-code-review` to format reviewer brief:
     * Context (sprint goal, ADR refs)
     * Diff (git diff or specific file refs)
     * Specific concerns (areas reviewer should focus)
     * Acceptance criteria
2. DISPATCH (parallel если multiple reviewers):
   - Use `superpowers:dispatching-parallel-agents` pattern:
     Single message с multiple Agent(subagent_type="<reviewer>") calls
3. POST-REVIEW (process feedback):
   - Use `superpowers:receiving-code-review` skill:
     * Categorize feedback: BLOCKER / CONCERN / SUGGESTION
     * Address blockers first (must fix перед merge)
     * Acknowledge concerns (decide fix-now vs defer)
     * Note suggestions (consider future)
4. RE-REVIEW если blockers fixed
```

**Параллельный dispatch:** explicit `superpowers:dispatching-parallel-agents` pattern — multiple Agent calls в одном message.

### HARD-GATE
- ✅ Domain reviewer per touched area invoked
- ✅ Reviewer brief formatted per `superpowers:requesting-code-review` (context + diff + concerns)
- ✅ Blockers addressed (per `superpowers:receiving-code-review` categorization)
- ✅ Concerns acknowledged (даже если не fix)
- ❌ Skip review если "тривиально" — нет такого правила

### Skip когда
- Pure docs change (нет src/ touch)
- < 50 LoC + tests pass — может только domain reviewer (no parallel)

---

## Phase 7: Sync (wiki update)

### Триггер
- Phase 6 review passed
- Code changes требуют wiki update

### Procedure
**Использовать skill:** `.claude/skills/wiki-update/SKILL.md`

```
1. Walk dependency graph (touched src/* → component pages)
2. Block 1↔Block 2 sync per touched component:
   - Block 1 (Code refs): sources frontmatter + Public API + Invariants Enforcement column
   - Block 2 (Description): narrative + settings keys + class names + invariant text
   - HARD-GATE: оба блока MUST sync в одном commit
3. Canonical counts sync если FSM/reason codes/components изменились
4. ADR amendment если нужно
```

### HARD-GATE
- ✅ Component pages updated если public API changed
- ✅ Canonical counts current в `current-state.md` + `execution-state-machine.md`
- ✅ Block 1 anchors point на existing functions (не renamed/removed)

---

## Phase 8: Ship (sprint-finish skill)

### Триггер
- Phase 7 sync done
- All HARD-GATEs passed

### Используемые skills

| Skill | Когда |
|-------|-------|
| **`sprint-finish`** (project) | PRIMARY — HARD-GATE checklist (sprint-NN.md + canonical counts + Block 1↔2 sync + orphan-audit + index sync) |
| **`superpowers:finishing-a-development-branch`** | Delegated by `sprint-finish` после HARD-GATEs — verify tests → 4 options (merge/PR/keep/discard) → execute → cleanup |
| **`agent-skills:git-workflow-and-versioning`** | DEPTH reference — atomic commits, clean history |
| **`agent-skills:shipping-and-launch`** | DEPTH reference — pre-launch checklist + monitoring + rollback plan |
| **`agent-skills:documentation-and-adrs`** 🆕 (S32) | Phase 8 — ADR creation per sprint. Explicit step для capturing architectural decision context (Status / Context / Options / Decision / Consequences). Применять каждый sprint create new ADR. Replaces ad-hoc ADR writing. |

### Procedure
**Использовать skill:** `.claude/skills/sprint-finish/SKILL.md` → `superpowers:finishing-a-development-branch`

```
1. Pre-validation (pytest + mypy)
2. HARD-GATE — sprint-NN.md page существует
3. HARD-GATE — canonical counts sync
4. HARD-GATE — Block 1↔Block 2 sync per touched component
5. HARD-GATE — orphan-audit grep includes tests/
6. HARD-GATE — new ADRs в index.md
7. SPRINT_STATE → 8-ship
8. git push
9. gh pr create
10. gh pr merge --squash --delete-branch
11. git tag v0.1.0-alpha.N + push
12. SPRINT_STATE → between-sprints
13. mark_chapter "Sprint N — ship complete"
```

### Hooks которые fire (ожидать)

| Hook | Trigger | Действие если block |
|------|---------|---------------------|
| `adr-agent-sync-check.sh` | git push если ADR changed | touch agent prompt mtime |
| `adr-index-sync-check.sh` | git push если new ADR | add ADR к index.md |
| `sprint-flow-check.sh` (S28+) | git push на feature/sprint-* | create plan file |

---

## Phase 9: Close (between-sprints)

### Procedure
```
1. SPRINT_STATE → phase=between-sprints, sprint=N+1 ready, tag updated
2. Append wiki/log.md session-end entry
3. mark_chapter "Sprint N — ship complete"
4. git commit -m "docs(sprint): SPRINT_STATE → between-sprints alpha.N"
5. (Каждые 5 спринтов OR при >30 observations в claude-mem) — invoke `anthropic-skills:consolidate-memory`:
   - Trigger check: sprint number divisible by 5 (S35, S40, S45, ...) OR
                    `mcp__plugin_claude-mem_mcp-search__list_corpora` показывает >30 observations
   - Procedure: reflective pass over claude-mem corpus → organize learnings в structured chunks по категориям
                (trading-decisions / formula-knowledge / process-patterns / debug-knowledge)
                → persist consolidated knowledge → reduce noise в future mem-search
   - Output: cleaner corpus, faster STEP 2 lookups, better cross-session knowledge retention
   - Anti-pattern: skip consolidation потому что "не пора" — if observations > 30, ALWAYS run
```

### HARD-GATE
- ✅ SPRINT_STATE phase=between-sprints
- ✅ log.md session-end entry appended
- ✅ Chapter marked
- ✅ Если N % 5 == 0 OR observations > 30: consolidate-memory invoked

---

## Token economy: LLMWiki ↔ Claude-mem cascade (BINDING per ADR 0043 + ADR 0045 S32 update)

При любом lookup (decision / pattern / API / past learning / code structure) — следуй cascade order:

```
STEP 1: wiki/<page>.md             (curated, structured, tagged)        ← CHECK FIRST
   ↓ not found
STEP 2: mem-search                 (past sessions semantic search)
   ↓ not found
STEP 2.5: claude-mem:smart-explore (token-optimized structural code nav)  ← NEW (S32 ADR 0045)
   ↓ needed
STEP 3: Grep raw                   (current code state — text matching)
   ↓ needed
STEP 4: Read raw + offset          (full content, controlled)
```

**STEP 2.5 rationale (NEW S32):** `claude-mem:smart-explore` = token-optimized structural code search. Применять когда нужна structural understanding (call graph, file relationships, "where is X used?") ПЕРЕД naked grep. Экономит 30-50% tokens vs grep+full-read sequence на code exploration tasks. Skip STEP 2.5 если уже знаешь exact file (jump к STEP 4 offset Read).

Полный rationale + examples + bridges deferred → [[tooling-inventory-ru#13-llmwiki--claude-mem-cascade-rule-s30-adr-0043]]

**Anti-patterns:**
- ❌ Skip wiki check (STEP 1), jump straight к mem-search OR Read raw — loses curation, increases tokens
- ❌ Naked Grep (STEP 3) для structural questions — use smart-explore (STEP 2.5) first
- ❌ Read raw без offset для banned-from-full-read files (см. `~/.claude/CLAUDE.md` section 9)

## Cross-phase optional skills

Не привязаны к конкретной фазе — invoked по необходимости в любой phase.

### `superpowers:using-git-worktrees`
- **Назначение:** Isolated worktree workspace для parallel sprint experiments OR sandbox audits.
- **Когда:** (1) Нужно re-run audit / experiment без disturb текущей branch (S27 audit re-run примером был — мог использоваться worktree), (2) parallel sprint (rare для single-developer workflow).
- **NOT default** — наш sequential workflow обычно работает на feature/sprint-N branch напрямую.

### `superpowers:writing-skills`
- **Назначение:** Methodology создания new project-level skill (`.claude/skills/<name>/SKILL.md`).
- **Когда:** Когда existing skill не подходит и нужно создать новый workflow template (S28 sprint-orient/sprint-finish/wiki-update/brainstorm-init были созданы ad-hoc — повторное создание should follow эту methodology).
- **Output:** `.claude/skills/<new-name>/SKILL.md` per progressive disclosure pattern (frontmatter + when to use + steps + anti-patterns).

### `superpowers:using-superpowers` (meta)
- **Назначение:** Auto-loaded session start — discovers и invokes other superpowers skills based on task type.
- **Когда:** Каждая session — meta-level dispatch.
- **NOT manually invoked** — runs automatically.

## Skills × Phase integration map

Полная карта какой skill в какой фазе invoked:

| Skill | Phase | Trigger | Status |
|-------|-------|---------|--------|
| `sprint-orient` (project) | 1 | Session start | EXISTING |
| `agent-skills:idea-refine` | 2 PRE | Vague operator idea before brainstorm-init | NEW (S32) |
| `brainstorm-init` (project) | 2 | Trading scope questions | EXISTING |
| `superpowers:brainstorming` | 2 | Non-trading scope questions | NEW (S29) |
| `agent-skills:spec-driven-development` | 2/3 | Non-trading features без spec (dashboard/CLI/infra) | NEW (S32) |
| `superpowers:writing-plans` | 3 | Plan creation | EXISTING |
| `agent-skills:planning-and-task-breakdown` | 3 | DEPTH ref | EXISTING |
| `superpowers:subagent-driven-development` | 4 | Code-heavy execute | EXISTING |
| `superpowers:executing-plans` | 4 | Docs-heavy execute | EXISTING |
| `superpowers:test-driven-development` | 4 | Каждая code task | EXISTING |
| `superpowers:systematic-debugging` | 4 sub-flow | Bug encountered | NEW (S29) |
| `superpowers:dispatching-parallel-agents` | 4 sub-flow + 6 | Parallel reviewer dispatch | NEW (S29) |
| `agent-skills:test-driven-development` | 4 | DEPTH ref | EXISTING |
| `agent-skills:context-engineering` | 4 | Subagent briefs > 200 слов | EXISTING |
| `agent-skills:incremental-implementation` | 4 | DEPTH ref | EXISTING |
| `agent-skills:source-driven-development` | 4 | Bybit/pydantic/pybit/FastAPI/TA-Lib tasks — verify against official docs | NEW (S32) |
| `agent-skills:api-and-interface-design` | 3 | CLI commands / module boundaries / endpoint design — stable contracts ДО impl | NEW (S32c) |
| `superpowers:verification-before-completion` | 5 | Pre-completion checklist | NEW (S29) |
| `agent-skills:browser-testing-with-devtools` | 5 | Dashboard sprints — Chrome DevTools MCP runtime verify | NEW (S32c) |
| `superpowers:requesting-code-review` | 6 | Format reviewer brief | NEW (S29) |
| `superpowers:receiving-code-review` | 6 | Process reviewer feedback | NEW (S29) |
| `agent-skills:code-review-and-quality` | 6 | DEPTH ref | EXISTING |
| `agent-skills:security-and-hardening` | 6 | Money/API/override changes | EXISTING |
| `agent-skills:code-simplification` | 6 OPT | Post-impl cleanup сложных формул | NEW (S32) |
| `agent-skills:performance-optimization` | 6 OPT | Backtest/replay sprints — profile-first, measure перед optimize | NEW (S32c) |
| `wiki-update` (project) | 7 | After src/ change | EXISTING |
| `sprint-finish` (project) | 8 | Sprint complete | EXISTING |
| `superpowers:finishing-a-development-branch` | 8 | Delegated by sprint-finish | EXISTING |
| `agent-skills:git-workflow-and-versioning` | 8 | DEPTH ref | EXISTING |
| `agent-skills:shipping-and-launch` | 8 | DEPTH ref | EXISTING |
| `agent-skills:documentation-and-adrs` | 8 | ADR creation per sprint | NEW (S32) |
| `anthropic-skills:consolidate-memory` | 9 | Каждые 5 спринтов OR >30 observations — corpus consolidation | NEW (S32) |
| `superpowers:using-git-worktrees` | cross-phase | Sandbox/parallel | NEW (S29) |
| `superpowers:writing-skills` | cross-phase | New project skill creation | NEW (S29) |
| `superpowers:using-superpowers` | meta | Session start auto | EXISTING |

**Total: 36 skills mapped к kit flow** (13 superpowers + 5 project + 17 agent-skills + 1 anthropic-skills). +4 в S32c: `api-and-interface-design` (Phase 3) / `browser-testing-with-devtools` (Phase 5) / `performance-optimization` (Phase 6 OPT) / `idea-refine` extension Phase 2 PRE workflow.

## Anti-patterns (НЕ делать в любой фазе)

- ❌ Skip фазу потому что "очевидно" / "тривиально"
- ❌ Прямой Agent dispatch вместо brainstorm-init / writing-plans / subagent-driven skills
- ❌ Code без plan file (PHASE 3 hook блокирует)
- ❌ SPRINT_STATE update только в конце спринта (PHASE 4 protocol требует per-task)
- ❌ Batch commit вместо per-task
- ❌ Push с feature/sprint-* без plan file (hook block)
- ❌ Push с new ADR без index.md entry (hook block)
- ❌ Push с ADR change без agent prompt touch (hook block)
- ❌ Tag без sprint-NN.md page
- ❌ Bug ad-hoc fix без `systematic-debugging` skill
- ❌ Sequential reviewer dispatch где `dispatching-parallel-agents` подходит
- ❌ Verify через "looks ok" вместо `verification-before-completion` checklist
- ❌ Reviewer brief ad-hoc без `requesting-code-review` skill format
- ❌ Reviewer feedback ad-hoc без `receiving-code-review` categorization
- ❌ Создать new project skill ad-hoc без `writing-skills` methodology

## Связанные документы

- [[development-workflow]] — английский оригинал (more detail)
- [[tooling-inventory-ru]] — agents/skills/plugins/MCP catalog (full)
- [[../decisions/0017-review-agent-harness]] — review agents matrix
- [[../decisions/0041-sprint-28-process-enforcement]] — process enforcement ADR
- [[../decisions/0042-sprint-29-superpowers-integration]] — superpowers integration ADR (этот спринт)

### Project skills
- `.claude/skills/sprint-orient/SKILL.md` — Phase 1
- `.claude/skills/brainstorm-init/SKILL.md` — Phase 2
- `.claude/skills/wiki-update/SKILL.md` — Phase 7
- `.claude/skills/sprint-finish/SKILL.md` — Phase 8

### Superpowers skills (13)
- `superpowers:brainstorming` — Phase 2 (non-trading)
- `superpowers:writing-plans` — Phase 3
- `superpowers:subagent-driven-development` — Phase 4 (code)
- `superpowers:executing-plans` — Phase 4 (docs)
- `superpowers:test-driven-development` — Phase 4
- `superpowers:systematic-debugging` — Phase 4 sub-flow
- `superpowers:dispatching-parallel-agents` — Phase 4+6
- `superpowers:verification-before-completion` — Phase 5
- `superpowers:requesting-code-review` — Phase 6
- `superpowers:receiving-code-review` — Phase 6
- `superpowers:finishing-a-development-branch` — Phase 8
- `superpowers:using-git-worktrees` — cross-phase
- `superpowers:writing-skills` — cross-phase
- `superpowers:using-superpowers` — meta auto-loaded
