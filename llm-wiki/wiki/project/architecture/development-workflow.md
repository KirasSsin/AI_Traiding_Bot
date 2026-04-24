---
title: Development Workflow — Ultimatum SOP v3 (session-persistent)
type: architecture
tags: [workflow, superpowers, agent-skills, claude-mem, caveman, llmwiki, tdd, hooks, mcp, token-economy, sprint-state, session-continuity, v0.1]
created: 2026-04-20
updated: 2026-04-23
status: stable
sources:
  - llmwiki pattern (obra)
  - obra/superpowers README
  - addyosmani/agent-skills README
  - JuliusBrussee/caveman README
  - thedotmack/claude-mem README
  - llm-wiki/CLAUDE.md (Skills hierarchy & integration)
  - ~/.claude/CLAUDE.md (global rules)
  - project/decisions/0017-review-agent-harness.md
---

# Development Workflow — Ultimatum SOP v3

**TL;DR:** Session continuity через `SPRINT_STATE.md` (первое чтение каждой сессии). 5 инструментов (llmWiki + Caveman + Agent Skills + Superpowers + claude-mem) покрывают все фазы. Anti-bloat через model dispatch + trigger cascade. KPD = качество × скорость / токены.

---

## КРИТИЧЕСКОЕ ПРАВИЛО: Первое действие каждой сессии

```
ОБЯЗАТЕЛЬНО — до любого кода, до любых вопросов:

1. Read: llm-wiki/wiki/project/SPRINT_STATE.md
   → Понять: sprint N, phase X, completed tasks, next action

2. git branch --show-current && git log --oneline -3
   → Код state: на какой ветке, что последнее

3. git status (если видно незакоммиченное)
   → Есть ли orphaned changes

4. mcp__ccd_session__mark_chapter "Sprint N — session resume"
```

**SPRINT_STATE.md = рабочая память между сессиями.**  
Если там написано "Task 3 in-progress: implement FSM transitions" — начинай именно оттуда.  
Не перечитывай весь план. Не спрашивай "где мы?" у пользователя.

---

## Token economy — зачем этот flow

| Проблема | Без flow | С flow | Выигрыш |
|---|---|---|---|
| "Где мы?" после перерыва | Перечитываем весь план + ADR (~15KB) | SPRINT_STATE.md (≤2KB) + git log | 7× меньше токенов |
| Повторное чтение ADR | Raw ADR каждую сессию (~8KB) | wiki/components/ (2-3KB, compiled) | 4× меньше |
| Длинные ответы | Prose с вводными | Caveman active (65% сжатие) | 65% меньше output |
| Все задачи на opus | Дорого, медленно | haiku/sonnet/opus dispatch | 10-50× экономия |
| "Решали ли X?" | Перечитываем ADRs | mem-search за секунды | 10× быстрее |
| Ревьюеры последовательно | Ждём каждого | Параллельный dispatch | 2-3× быстрее |
| Пропуск quality gates | "Кажется правильным" | Agent Skills + L5 reviewers | 0 регрессий |

---

## Карта инструментов (что решает каждый)

```
claude-mem     → память между сессиями (автоматически: 7 хуков)
               → явно: mem-search "did we solve X?" Phase 1

llmWiki        → compiled knowledge (wiki-first, не raw ADR)
               → SPRINT_STATE.md = working memory между сессиями

Superpowers    → process orchestration (brainstorm→plan→code→review→ship)
               → subagent-driven = свежий контекст per task

Agent Skills   → depth checklists (TDD, security, context-engineering)
               → context-engineering skill для subagent briefs

Caveman        → output compression (65% savings)
               → caveman-compress для CLAUDE.md files (47% на старте)

Domain reviewers → trading-domain correctness (ADR 0017)
                → L5: parallel dispatch, не sequential
```

---

## Sprint lifecycle — 9 фаз

### PHASE 0a — Session start (РУЧНОЙ, первые 2 минуты)

```
ДЕЙСТВИЯ:
1. Read llm-wiki/wiki/project/SPRINT_STATE.md
   → sprint, phase, next action, key decisions

2. git branch --show-current && git log --oneline -3
   → где находимся в git

3. Если SPRINT_STATE.phase = "4-execution" и есть in-progress task:
   a. git status → незакоммиченные изменения?
   b. pytest tests/unit -x --tb=short -q → тесты проходят?
   c. Начинай с "Следующее действие" из SPRINT_STATE.md

4. mcp__ccd_session__mark_chapter "Sprint N — resume phase X"

5. Agent staleness check (ОБЯЗАТЕЛЬНО при phase = "between-sprints" ИЛИ перед началом нового sprint):
   a. grep -E "42 enum|59 canonical|4-valued|halt_log|HEAL_ENTRY_FILLED|HALT_BOOTSTRAP_AMBIGUOUS|ws-private-consumer|migration 0005" \
        ~/.claude/agents/trading-logic-reviewer.md \
        ~/.claude/agents/data-integrity-reviewer.md \
        ~/.claude/agents/quant-stats-reviewer.md \
        ~/.claude/agents/trader-expert.md
      → если совпадений < N expected (см. SPRINT_STATE для current N) → агенты устарели
   b. Если устарели: dispatch trader-expert с questionnaire "что изменилось с last sprint" ИЛИ
      maintainer патчит вручную перед PHASE 2.
   c. Sync-check ADR 0017 model assignments vs frontmatter `model:` в каждом agent файле.

SKIP: шаг 2-3 только если SPRINT_STATE.phase = "between-sprints"
SKIP: шаг 5 только если phase = "4-execution" continue (уже проверяли в начале sprint)
```

### PHASE 0b — Session start (АВТОМАТИЧЕСКИ, хуки)

```
[AUTO] claude-mem SessionStart:
  → inject 50 релевантных observations (SQLite FTS5 + Chroma)
  → semantic session summary

[AUTO] CLAUDE.md загрузка:
  → ~/.claude/CLAUDE.md (global rules + model dispatch + token economy)
  → llm-wiki/CLAUDE.md (project schema + skills hierarchy + sprint orient)

[AUTO] Agent Skills meta:
  → using-agent-skills flowchart

[AUTO] Caveman:
  → CAVEMAN MODE ACTIVE (full)
```

**Что делать если SPRINT_STATE.md устарел (нет файла / phase = "between-sprints" но помним что начали):**
```
git log --oneline -10          → найти последний sprint commit
cat llm-wiki/wiki/log.md | tail -20  → последние wiki events
mem-search "sprint N in-progress"    → контекст из claude-mem
```

---

### PHASE 1 — Sprint orient (если новый спринт или неясно где мы)

```
Только если SPRINT_STATE.phase = "between-sprints" или неопределённо.
Если already in-progress → пропустить, перейти к Phase 4.

1. mem-search "sprint N" / "ADR NNNN" / "known issue X"
   Tool: mcp__plugin_claude-mem_mcp-search__smart_search
   → prior decisions, patterns, unresolved concerns

2. Read wiki/log.md (последние 10 entries)

3. Read wiki/index.md (top 50 lines)

4. mcp__ccd_session__mark_chapter "Sprint N — orient"
```

---

### PHASE 2 — Brainstorming + ADR

```
TRIGGER: новый scope (НЕ approved ADR)
SKIP: executing approved ADR → Phase 3

1. Skill("brainstorming") [Superpowers L3]
2. Escalate: Skill("process-interviewer") если < 3 раунда + impact > 1 sprint [L4b]

3. Trader-expert delegation (ОБЯЗАТЕЛЬНО если есть unresolved scope/architecture
   questions после brainstorming round'а — НЕ пропускать в PHASE 3 пока не пройдено):

   3a. Maintainer собирает structured questionnaire — markdown list, по каждому
       open question:
         - Question text (verbatim, точная формулировка проблемы)
         - Recommended option (рекомендация maintainer'а: какой выбрать)
         - Alternatives considered (2-3 альтернативы которые рассмотрели)
         - Reasoning (почему recommended option, ссылки на wiki/ADR/код)
         - Risk/concern (что может сломаться, если решение неверное)

   3b. Dispatch Agent(subagent_type="trader-expert", model=sonnet) с brief:
         - Sprint N context (из SPRINT_STATE + log tail)
         - Полный questionnaire из шага 3a
         - Constraints: ссылки на active ADR, схему, FSM состояние

   3c. Trader-expert возвращает per-question verdict (CONFIRM/REVISE/DEFER/EXPAND)
       + cross-cutting concerns + escalation list для user'а.

   3c.1 Iterative justify loop (ОБЯЗАТЕЛЬНО для каждого REVISE где выбранная trader'ом
        опция != maintainer's recommended option):

         (i)  Maintainer dispatch'ит ROUND 2 questionnaire ТОМУ ЖЕ trader-expert'у:
                - Verbatim text of disputed question.
                - Round 1 maintainer recommendation + reasoning.
                - Round 1 trader REVISE verdict (chosen option + rationale).
                - Brief: "Re-evaluate. Why did you choose <X> over maintainer's <Y>?
                  Perform deeper analysis: side-by-side compare <Y> vs <X>, fresh
                  research (re-read related wiki/ADR/code), then return final
                  verdict per Iterative justification protocol in your prompt."

         (ii) Trader-expert ROUND 2 response (per Iterative justification protocol
              in trader-expert.md) returns ONE of:
                - **CONFIRM_REVISE** — same answer, deeper rationale, explicit list
                  of risks in maintainer's option that justified rejecting it.
                  → ACCEPT trader's option. Lock for ADR.
                - **CHANGED** — new analysis showed maintainer's option was right
                  OR a third option emerged. MUST include compare table
                  (option Y vs option X vs option Z if any), fresh research findings.
                  → ACCEPT trader's NEW final verdict. Lock for ADR.

         (iii) Maintainer logs BOTH rounds in ADR section "Decision rationale":
                 - Round 1 verdict (REVISE, option X)
                 - Round 2 verdict (CONFIRM_REVISE / CHANGED, final option)
                 - Why iteration happened (disagreement) and how it resolved.

         (iv) NO third round. Round 2 verdict is binding. If maintainer still
              disagrees → escalate to user under "Open issues" with both rounds
              in evidence package.

   3d. Maintainer применяет verdicts:
         - CONFIRM → option лочится, идёт в ADR.
         - REVISE (where option == maintainer's recommendation, no disagreement)
           → option лочится, идёт в ADR with trader's rationale.
         - REVISE (where option != maintainer's recommendation) → MUST go through
           3c.1 iterative justify loop FIRST. Final option lockd after round 2.
         - DEFER → вопрос → "Open questions → deferred to S{N+1}+" в ADR.
         - EXPAND → re-brainstorm на reframed question → возможен второй round 3a-3c.

   3e. Если trader-expert escalated items → пользователю (1 message с конкретными
       вопросами). Без user-ответа PHASE 3 не начинается.

   3f. ANTI-PATTERN — НИКОГДА не делать в PHASE 2:
         - Задавать user-у scope/architecture вопрос НАПРЯМУЮ без trader-expert
           round 1. (User questions = ТОЛЬКО escalation list из trader's output.)
         - Принимать REVISE с disagreement без round 2 iterative justify loop.
         - Третий round trader-expert (round 2 верdict binding).
         - Skip'ать trader-expert dispatch потому что "очевидно" — все open
           scope/architecture questions ОБЯЗАТЕЛЬНО проходят trader-expert.

4. ADR draft → wiki/project/decisions/NNNN-<slug>.md (status: proposed)
   → каждое решение из шагов 3c-3d попадает в ADR с reference на verdict.
5. User approves → status: accepted

ORCHESTRATION & CONCURRENCY (S8+ scope, ОБЯЗАТЕЛЬНО включить в questionnaire если затронуты):
  - Driver loop ownership (manager.py vs coordinator.bootstrap): кто стартует, кто
    останавливает, кто owns asyncio.Task references.
  - Backpressure: WS event burst → queue bound? drop policy? halt threshold?
  - Concurrency invariants: один coordinator per symbol; FSM transitions serialized
    (single-writer); WS consumer non-blocking (offload sqlite to to_thread).
  - Shutdown sequencing: stop accepting events → flush in-flight → cancel tasks →
    close WS → close DB. Forcible kill = HALT + manual reset on next bootstrap.
  - Supervision: task crash → supervisor restart vs halt? Bounded retry?
  - Если any of above unresolved → trader-expert questionnaire ОБЯЗАТЕЛЬНО.

SPRINT_STATE update:
  phase: 2-brainstorming
  sprint: N
  next_action: "Trader-expert verdict round K" → "ADR NNNN review by user"
```

---

### PHASE 3 — Plan writing

```
1. Skill("writing-plans") [Superpowers L3]
   → bite-sized tasks (2-5 min), TDD structure, YAGNI
   → trace map: sub-decision N → Tasks X,Y,Z (ОБЯЗАТЕЛЬНО)

2. Skill("planning-and-task-breakdown") [Agent Skills L4]
   → acceptance criteria depth

3. wc -c plan.md → > 50KB = split на part-1.md, part-2.md

4. Save: wiki/project/plans/YYYY-MM-DD-sprint-N-<slug>.md

5. git checkout -b feature/sprint-N-<slug>

SPRINT_STATE update:
  phase: 3-planning → 4-execution
  branch: feature/sprint-N-<slug>
  plan: wiki/project/plans/YYYY-MM-DD-sprint-N-<slug>.md
  next_action: "Start Task 1: [description]"
  completed: []
  in_progress: ["Task 1: [description]"]
```

---

### PHASE 4 — Per-task execution loop

#### Model selection (выбери ДО dispatch)

```
haiku  → mechanical: DDL, config, fixtures, README, simple models
sonnet → standard: business logic, FSM, coordinator methods, tests (DEFAULT)
opus   → judgment: Kelly/HMAC/security, multi-file refactor, hard debug

ПРАВИЛО: начни sonnet.
         BLOCKED дважды → escalate opus.
         Pure mechanical после анализа → downgrade haiku.
```

#### Brief construction (перед каждым dispatch)

```
≤ 200 слов, output ≤ 30KB:
  → пиши напрямую

> 200 слов / output > 30KB / critical correctness (Kelly, FSM, security):
  1. Skill("context-engineering") [Agent Skills L4] — как pack context
  2. prompt-master refine [L4b]
  3. Маркер в brief: "DO NOT compress technical specs below: [specs]"
```

#### Dispatch + TDD цикл

```
1. Agent(model=selected, prompt=brief)
   → DONE: переход к review
   → DONE_WITH_CONCERNS: прочитай concerns
   → NEEDS_CONTEXT: предоставь, re-dispatch
   → BLOCKED (1): контекст, re-dispatch sonnet
   → BLOCKED (2): escalate opus

2. TDD strict:
   RED:    failing test → run → confirm FAIL
   GREEN:  minimal code → run → confirm PASS
   COMMIT: conventional commit (feat:/fix:/test:/chore:)

3. Two-stage review:
   spec-reviewer → "matches spec?" → NO: fix loop
   code-quality-reviewer → "well-built?" → NO: fix loop

4. TodoWrite: task DONE
```

#### Parallel dispatch (ОБЯЗАТЕЛЬНО знать)

```
ALWAYS PARALLEL (один message, несколько Agent calls):
  → trading-logic-reviewer + python-reviewer
  → trading-logic-reviewer + quant-stats-reviewer
  → spec-reviewer task N + implementer task N+1
  → два независимых implementer (разные файлы, 0 shared state)

NEVER PARALLEL:
  → implementer → fix → re-review (зависимые)
  → migration runner → tests reading DB
  → task N+1 если импортирует код task N
```

#### SPRINT_STATE update (после каждого DONE task)

```
completed: добавить task
in_progress: убрать task, добавить следующий
next_action: "Task N+1: [конкретное описание]"
             "Run: pytest tests/unit/test_X.py -x"
phase: 4-execution
updated: YYYY-MM-DD
```

---

### PHASE 5 — Domain review (Layer 5, ADR 0017)

#### Trigger cascade

```
src/signalgen/**, src/execution/**, src/risk/**, src/backtest/**:
  → trading-logic-reviewer (sonnet)   ОБЯЗАТЕЛЬНО
  SKIP: pure docs

src/risk/**, src/backtest/**, src/analytics/** (формулы):
  → quant-stats-reviewer (opus)       ОБЯЗАТЕЛЬНО
  SKIP: no formula

migrations/**, src/marketdata/**, src/platform/storage/**:
  → data-integrity-reviewer (sonnet)  ОБЯЗАТЕЛЬНО
  SKIP: no persistence

любой *.py:
  → python-reviewer (sonnet)          если нет domain hit ИЛИ domain cleared
  SKIP: < 100 LoC + только tests + domain cleared

API keys/money/signing/override:
  → + security-and-hardening [Agent Skills L4]
```

#### Review output

```
❌ Blockers → fix loop (новый implementer → re-review)
⚠️ Concerns → SPRINT_STATE.blockers_concerns + defer sprint page
Follow-ups for wiki → wiki update в этом sprint (не defer)
code↔ADR drift → Skill("fact-checker") [L4b]
```

---

### PHASE 6 — Wiki update (continuous)

```
После каждого task DONE:
  Edit wiki/project/components/<name>.md    → что делает теперь
  Edit wiki/project/sprints/sprint-NN.md   → task complete
  Edit wiki/log.md                          → append entry
  Edit wiki/index.md                        → если новая страница

ПРАВИЛО: wiki/components/ — primary reference.
         Raw ADR — только при явном несоответствии.
         Размер страниц < 50KB (иначе split).
```

---

### PHASE 7 — Tests

```
Per-task (TDD внутри Phase 4):
  tests/unit/    → каждый RED→GREEN цикл
  tests/property/→ Hypothesis: FSM, look-ahead, orderLinkId

Gate перед Phase 8:
  pytest tests/unit tests/property -x     ← must be green

Opt-in integration:
  pytest tests/integration -x -m demo    ← если env keys

Stage F (только S6+, venue API):
  scripts/spot_oco_probe_testnet.py --probe B2
  scripts/spot_oco_probe_testnet.py --probe v3-D
  → результаты в sprint page Stage F table
```

---

### PHASE 8 — Finishing branch

```
1. Skill("finishing-a-development-branch") [Superpowers L3]

2. Skill("git-workflow-and-versioning") [Agent Skills L4]
   → atomic commits, conventional format

3. Skill("documentation-and-adrs") [Agent Skills L4]
   → ADR format correct, consequences documented

4. ADR ↔ agent prompt sync:
   Edit ~/.claude/agents/<name>.md (если ADR изменён)
   (PreToolUse hook проверит на push)

5. **HARD-GATE — Sprint page finalize (BLOCKS step 6 if missing):**
   - Verify `wiki/project/sprints/sprint-NN-<slug>.md` exists.
   - If missing → CREATE per `sprint-07-resilience.md` skeleton:
     frontmatter (title, type=sprint, tags, created/updated, status=completed,
     sources=[ADR + plan]) + sections (Overview / Plan-ADR links / Deliverables
     [Schema/FSM/Component sub-sections] / Reason codes / Tests / Wiki updates /
     Open issues для S{N+1}).
   - If exists → finalize Stage F results, review follow-ups, plan drift.
   - Source content: log.md sprint-end entry + commit log + plan trace map.

6. **HARD-GATE — Wiki sync (BLOCKS step 7 if missing):**
   - All new ADRs (этого спринта) added to `wiki/index.md` `## Project — Decisions` section.
   - All new component pages added to `wiki/index.md` `## Project — Components` section.
   - Sprint page added to `wiki/index.md` `## Project — Sprints` section.
   - Verify: `grep "0NNN" llm-wiki/wiki/index.md` returns hit для каждого нового ADR.

7. Merge + tag:
   git merge feature/sprint-N-<slug>
   git tag v0.1.0-alpha.N

8. Push (PreToolUse hook fires):
   git push origin main
   git push origin v0.1.0-alpha.N

ANTI-PATTERN (S8a + S8b violations — fixed pre-S8c per backlog):
  ❌ Tag push без sprint-NN.md (sprint pages для S8a + S8b отсутствовали — created in pre-S8c batch).
  ❌ Tag push без ADR в index.md (ADR 0022 orphan — fixed in pre-S8c batch).
  ❌ Tag skip (tags v0.1.0-alpha.4 + alpha.5 missing — sprint pages говорят "pending PR merge" но never tagged → tag drift).
  Все три = direct symptom отсутствия HARD-GATE — теперь зафиксированы как BLOCKERS.

SPRINT_STATE update:
  sprint: N-complete
  phase: between-sprints
  tag: v0.1.0-alpha.N
  branch: main
  next_action: "Begin Sprint N+1. Start brainstorming."
  completed: [все tasks]
  in_progress: []
  blockers_concerns: [deferred to S(N+1)]
```

---

### PHASE 9 — Session end

**ОБЯЗАТЕЛЬНО перед закрытием приложения:**

```
1. Update SPRINT_STATE.md:
   → Текущий статус (sprint / phase)
   → in_progress → что конкретно осталось
   → next_action → КОНКРЕТНОЕ действие с командой если применимо
   → key_decisions → нетривиальные решения сессии
   → updated: YYYY-MM-DD

2. Append wiki/log.md:
   ## [YYYY-MM-DD] session-end | Sprint N Phase X
   → что сделано, что отложено

3. mcp__ccd_session__mark_chapter "Sprint N — session end"

[AUTO] claude-mem SessionEnd hook:
   → session summary → SQLite + Chroma embedding
   → доступно через mem-search в следующей сессии
```

**Если прерывание (приложение закрылось без phase 9):**  
При следующем старте: SPRINT_STATE.md + `git log --oneline -5` + `git status` дают достаточно контекста.

---

## SPRINT_STATE.md — формат и правила

```markdown
---
title: Sprint State
type: state
updated: YYYY-MM-DD
sprint: N или "N-complete"
phase: between-sprints | 2-brainstorming | 3-planning | 4-execution | 8-finishing
branch: feature/sprint-N-xxx или main
tag: v0.1.0-alpha.N (если tagged)
plan: wiki/project/plans/YYYY-MM-DD-sprint-N-slug.md
---

## Текущий статус
[1 строка: Sprint N — Topic. Phase X.]

## Завершённые задачи
- [x] Task 1: description
- [x] Task 2: description

## В процессе
- [ ] Task 3: description (model: sonnet, N/M RED→GREEN done)

## Следующее действие
[Конкретно. Команда если применимо.]
Run: pytest tests/unit/test_X.py -x

## Ключевые решения последней сессии
- [только нетривиальное, не очевидное из кода]

## Блокеры / concerns (отложены)
- [item] — defer sprint N+1
```

**Правила файла:**
- Размер ≤ 2KB ВСЕГДА (иначе теряется смысл — быстрое чтение)
- "Следующее действие" = конкретный следующий шаг (не "продолжать")
- Обновляй после каждого task DONE и перед закрытием сессии
- Не history — только CURRENT state

---

## Hooks (автоматические)

| Hook | Когда | Action |
|---|---|---|
| SessionStart:compact (claude-mem) | start | inject 50 observations |
| SessionStart:compact (caveman) | start | activate full mode |
| SessionStart:compact (agent-skills) | start | load meta flowchart |
| UserPromptSubmit (claude-mem) | каждый prompt | capture observation |
| UserPromptSubmit (caveman) | каждый prompt | re-assert caveman |
| PostToolUse (claude-mem) | каждый tool result | capture (кроме SKIP_TOOLS) |
| Stop (claude-mem) | каждый мой ответ | capture response |
| SessionEnd (claude-mem) | конец сессии | summary + Chroma embedding |
| PreToolUse → git push | push attempt | ADR-agent sync check |

---

## Одноразовая настройка (выполнить один раз)

```bash
# Compress rule files → ~47% экономия токенов каждую сессию
/caveman:compress ~/.claude/CLAUDE.md
/caveman:compress llm-wiki/CLAUDE.md
/caveman:compress ~/.claude/agents/trading-logic-reviewer.md
/caveman:compress ~/.claude/agents/quant-stats-reviewer.md
# Результат: *.original.md (backup) + compressed main file
# Re-run после значительных обновлений файлов
```

---

## Skip matrix (anti-bloat)

| Шаг | Skip if |
|---|---|
| Phase 1 orient | SPRINT_STATE.phase = "4-execution" (уже в процессе) |
| brainstorming | executing approved ADR |
| process-interviewer | первые 3 ответа чёткие |
| context-engineering для brief | ≤ 200 слов, output ≤ 30KB |
| trading-logic-reviewer | pure docs, 0 logic |
| quant-stats-reviewer | 0 формул |
| data-integrity-reviewer | 0 persistence |
| python-reviewer | domain cleared, < 100 LoC, только tests |
| security-and-hardening | 0 I/O boundary |
| Stage F probes | спринт не касается venue API |
| version-bump skill | git tag уже проставлен |

---

## Parallel dispatch map

```
ВСЕГДА ПАРАЛЛЕЛЬНО (один message):
  trading-logic-reviewer + python-reviewer
  trading-logic-reviewer + quant-stats-reviewer
  spec-reviewer(task N) + implementer(task N+1)
  два независимых implementer (разные файлы)

ВСЕГДА ПОСЛЕДОВАТЕЛЬНО:
  implementer → fix → re-review
  migration → tests reading DB
  task N+1 если импортирует task N код
```

---

## Red flags

| Симптом | Fix |
|---|---|
| Читаю raw ADR без wiki-страницы | wiki/components/ FIRST |
| "Где мы?" — спрашиваю пользователя | Read SPRINT_STATE.md FIRST |
| Sonnet BLOCKED дважды | escalate opus |
| git push заблокирован hook | Edit ~/.claude/agents/<name>.md → retry |
| SPRINT_STATE.md устарел/нет | git log -10 + wiki/log.md tail -20 + mem-search |
| Brief > 200 слов без context-engineering | Skill("context-engineering") СНАЧАЛА |
| Читаю весь план при resume | Read только SPRINT_STATE.md → next_action |
| Ревьюеры последовательно | dispatch параллельно (один message) |

---

## Related

- [[../decisions/0017-review-agent-harness]] — L5 domain reviewers spec
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]] — пример полного цикла
- [[../components/adr-agent-sync-hook]] — PreToolUse hook
- [[../sprints/sprint-06-spot-oco-emulation]] — sprint narrative S6
- [[../SPRINT_STATE]] — живое состояние проекта (читай первым)
- [[migration-plan]] — 10 спринтов v0.1
