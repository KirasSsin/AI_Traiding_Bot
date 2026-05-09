---
title: Development Workflow — Ultimatum SOP v3 (session-persistent)
type: architecture
tags: [workflow, superpowers, agent-skills, claude-mem, caveman, llmwiki, tdd, hooks, mcp, token-economy, sprint-state, session-continuity, v0.1]
created: 2026-04-20
updated: 2026-05-09
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

**TL;DR:** Непрерывность сессий через `SPRINT_STATE.md` (первое чтение каждой сессии). 5 инструментов (llmWiki + Caveman + Agent Skills + Superpowers + claude-mem) покрывают все фазы. Защита от раздувания через model dispatch + trigger cascade. КПД = качество × скорость / токены.

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
| Повторное чтение ADR | Сырой ADR каждую сессию (~8KB) | wiki/components/ (2-3KB, compiled) | 4× меньше |
| Длинные ответы | Prose с вводными | Caveman active (65% сжатие) | 65% меньше output |
| Все задачи на opus | Дорого, медленно | haiku/sonnet/opus dispatch | 10-50× экономия |
| "Решали ли X?" | Перечитываем ADRs | mem-search за секунды | 10× быстрее |
| Ревьюеры последовательно | Ждём каждого | Параллельный dispatch | 2-3× быстрее |
| Пропуск quality gates | "Кажется правильным" | Agent Skills + L5 reviewers | 0 регрессий |

---

## Карта инструментов (что решает каждый)

```
claude-mem     → память между сессиями (автоматически: 7 хуков)
               → явно: mem-search "did we solve X?" Фаза 1

llmWiki        → скомпилированные знания (wiki-first, не сырой ADR)
               → SPRINT_STATE.md = рабочая память между сессиями

Superpowers    → оркестровка процесса (brainstorm→план→код→review→ship)
               → subagent-driven = свежий контекст для каждой задачи

Agent Skills   → depth checklists (TDD, security, context-engineering)
               → context-engineering skill для subagent briefs

Caveman        → сжатие вывода (65% экономия)
               → caveman-compress для CLAUDE.md файлов (47% при старте)

Domain reviewers → корректность торговой логики (ADR 0017)
                → L5: параллельный dispatch, не последовательный
```

---

## Жизненный цикл спринта — 9 фаз

### ФАЗА 0a — Старт сессии (РУЧНОЙ, первые 2 минуты)

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

### ФАЗА 0b — Старт сессии (АВТОМАТИЧЕСКИ, хуки)

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

### ФАЗА 1 — Ориентирование в спринте (если новый спринт или неясно где мы)

**Реализация:** Skill `sprint-orient` (`.claude/skills/sprint-orient/SKILL.md`) — авто-триггер по совпадению описания ("где мы", "ориентируйся", старт сессии, после `/clear`).

**Триггер:** SPRINT_STATE.phase = "between-sprints" ИЛИ неопределённо. Пропустить если already in-progress (продолжить к Фазе 4).

**Что делает skill:**
1. Read `SPRINT_STATE.md` → sprint/phase/branch/tag/next_action
2. Проверить состояние git (ветка + последние коммиты)
3. Read tail `log.md` (offset+limit, файл 51KB запрещён для полного чтения)
4. Read таблицу canonical-counts `current-state.md`
5. Опционально: mem-search для specific concerns
6. mcp__ccd_session__mark_chapter "Sprint N — orient"
7. Опционально: загрузить mental-map.md при открытом запросе

**Не дублировать inline здесь** — skill загружается по требованию (progressive disclosure).

---

### ФАЗА 2 — Брейнштурм + ADR

```
ТРИГГЕР: новый scope (НЕ одобренный ADR)
ПРОПУСТИТЬ: исполнение одобренного ADR → Фаза 3

1. Skill("brainstorming") [Superpowers L3] — initial divergent exploration
2. Escalate: Skill("process-interviewer") если < 3 раунда + impact > 1 sprint [L4b]

3. **Skill `brainstorm-init`** (`.claude/skills/brainstorm-init/SKILL.md`) — auto-triggered when scope/architecture questions surface. Implements binding PHASE 2 protocol: structured questionnaire → trader-expert ROUND 1 → iterative justify ROUND 2 на REVISE-disagreement (CONFIRM_REVISE / CHANGED, BINDING, no round 3) → user escalation only из trader's escalation list → backlog persistence.

   **Полная procedure** (структурированный questionnaire 5-field, dispatch protocol, iterative justify loop, anti-patterns) — см. SKILL.md. Не дублировать inline здесь.

4. ADR draft → wiki/project/decisions/NNNN-<slug>.md (status: proposed) — каждое решение из brainstorm-init verdicts trail.
5. User approves → status: accepted.

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

### ФАЗА 3 — Написание плана

```
1. Skill("writing-plans") [Superpowers L3]
   → bite-sized tasks (2-5 мин), TDD structure, YAGNI
   → trace map: sub-decision N → Tasks X,Y,Z (ОБЯЗАТЕЛЬНО)

1a. **HARD-GATE — Обязательная секция trace map (БЛОКИРУЕТ ФАЗУ 4 если отсутствует):**
   - План ОБЯЗАН содержать секцию `## Trace map` в формате таблицы:
     ```markdown
     ## Trace map
     | Spec / decision | Tasks |
     |-----------------|-------|
     | <ADR sub-decision N OR Bucket X item> | T<N>, T<N+1>, ... |
     | ... | ... |
     ```
   - Отображает каждый ADR sub-decision / требование spec / пункт бэклога → конкретные task ID.
   - Обоснование: writing-plans skill self-review checklist требует trace "spec coverage"; ретроспективно обнаружено, что планы S5/S7/S8b без trace привели к дрейфу вердикта ФАЗЫ 2 (см. план S8c в качестве примера формата).

2. Skill("planning-and-task-breakdown") [Agent Skills L4]
   → глубина acceptance criteria

3. wc -c plan.md → > 50KB = split на part-1.md, part-2.md

4. Сохранить: wiki/project/plans/YYYY-MM-DD-sprint-N-<slug>.md

5. git checkout -b feature/sprint-N-<slug>

Обновление SPRINT_STATE:
  phase: 3-planning → 4-execution
  branch: feature/sprint-N-<slug>
  plan: wiki/project/plans/YYYY-MM-DD-sprint-N-<slug>.md
  next_action: "Начать Task 1: [описание]"
  completed: []
  in_progress: ["Task 1: [описание]"]
```

---

### ФАЗА 4 — Цикл исполнения задач

#### Выбор модели (определить ДО dispatch)

```
haiku  → mechanical: DDL, config, fixtures, README, simple models
sonnet → standard: business logic, FSM, coordinator methods, tests (DEFAULT)
opus   → judgment: Kelly/HMAC/security, multi-file refactor, hard debug

ПРАВИЛО: начни sonnet.
         BLOCKED дважды → escalate opus.
         Pure mechanical после анализа → downgrade haiku.
```

#### Формирование brief (перед каждым dispatch)

```
≤ 200 слов, output ≤ 30KB:
  → пиши напрямую

> 200 слов / output > 30KB / critical correctness (Kelly, FSM, security):
  1. Skill("context-engineering") [Agent Skills L4] — как pack context
  2. prompt-master refine [L4b]
  3. Маркер в brief: "DO NOT compress technical specs below: [specs]"
```

#### Цикл dispatch + TDD

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

#### Параллельный dispatch (ОБЯЗАТЕЛЬНО знать)

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

#### Обновление SPRINT_STATE (после каждого завершённого task)

```
completed: добавить task
in_progress: убрать task, добавить следующий
next_action: "Task N+1: [конкретное описание]"
             "Run: pytest tests/unit/test_X.py -x"
phase: 4-execution
updated: YYYY-MM-DD
```

---

### ФАЗА 5 — Доменный review (Layer 5, ADR 0017)

#### Каскад триггеров

```
src/signalgen/**, src/execution/**, src/risk/**, src/backtest/**:
  → trading-logic-reviewer (sonnet)   ОБЯЗАТЕЛЬНО
  SKIP: чистая документация

src/risk/**, src/backtest/**, src/analytics/** (формулы):
  → quant-stats-reviewer (opus)       ОБЯЗАТЕЛЬНО
  SKIP: нет формул

migrations/**, src/marketdata/**, src/platform/storage/**:
  → data-integrity-reviewer (sonnet)  ОБЯЗАТЕЛЬНО
  SKIP: нет persistence

любой *.py:
  → python-reviewer (sonnet)          если нет domain hit ИЛИ domain cleared
  SKIP: < 100 LoC + только tests + domain cleared

API keys/money/signing/override:
  → + security-and-hardening [Agent Skills L4]
```

#### Результат review

```
Blockers → fix loop (новый implementer → re-review)
Concerns → SPRINT_STATE.blockers_concerns + отложить в sprint page
Follow-ups for wiki → wiki update в этом спринте (не откладывать)
расхождение code↔ADR → Skill("fact-checker") [L4b]
```

---

### ФАЗА 6 — Обновление wiki (непрерывное)

```
После каждого завершённого task:
  Edit wiki/project/components/<name>.md    → что делает теперь
  Edit wiki/project/sprints/sprint-NN.md   → task завершён
  Edit wiki/log.md                          → append entry
  Edit wiki/index.md                        → если новая страница

ПРАВИЛО: wiki/components/ — основной справочник.
         Сырой ADR — только при явном несоответствии.
         Размер страниц < 50KB (иначе split).
```

---

### ФАЗА 7 — Тесты

```
Для каждого task (TDD внутри Фазы 4):
  tests/unit/    → каждый цикл RED→GREEN
  tests/property/→ Hypothesis: FSM, look-ahead, orderLinkId

Gate перед Фазой 8:
  pytest tests/unit tests/property -x     ← must be green

Opt-in интеграционные:
  pytest tests/integration -x -m demo    ← если есть env keys

Stage F (только S6+, venue API):
  scripts/spot_oco_probe_testnet.py --probe B2
  scripts/spot_oco_probe_testnet.py --probe v3-D
  → результаты в таблицу Stage F страницы спринта
```

---

### ФАЗА 8 — Финализация ветки

**Реализация:** Skill `sprint-finish` (`.claude/skills/sprint-finish/SKILL.md`) — авто-триггер при сигнале готовности к ship ("финишируем", "ship", "merge to main", или после завершения пакета subagent-driven-development). Применяет все HARD-GATE (обязательный sprint-NN.md, синхронизация канонических счётчиков, orphan-audit grep включая tests/, синхронизация index.md ADR) перед `superpowers:finishing-a-development-branch`.

**Что делает skill:**
1. Предварительная валидация (pytest + mypy + canonical counts)
2. **HARD-GATE шаг 5:** sprint-NN.md существует ИЛИ СОЗДАТЬ по скелету sprint-07
3. **HARD-GATE шаг 5a:** синхронизация канонических счётчиков (если изменились FSM/reason codes/компоненты)
4. **HARD-GATE шаг 5b:** orphan-audit grep ОБЯЗАТЕЛЬНО включает tests/ (урок CC1 — рекурсивно)
5. **HARD-GATE шаг 5c (синхронизация Block 1↔Block 2, PR-γ 2026-04-25):** для каждой затронутой страницы компонента — Block 1 (ссылки на код: Sources frontmatter + Public API section + столбец Invariants Enforcement с якорями `function::name`) ОБЯЗАН синхронизироваться с Block 2 (Description / Configuration narrative / settings keys / class names / invariant text) **в одном commit**. Расхождение между Block 1 (например, новый метод `request_halt` в code refs) и Block 2 (Description ссылается на старый API) = блокировка HARD-GATE. **Применять к новым component pages с config**; existing pages — парадигма уже неявно реализована через Public API + Description sections, откладывать per-page рефакторинг (anti-bloat). Skill `wiki-update` (`.claude/skills/wiki-update/SKILL.md`) обходит граф зависимостей и автоматически сигнализирует о расхождениях.
6. **HARD-GATE шаг 6 (синхронизация wiki):** новые ADR в index.md, новые компоненты в index.md + кластер components/README.md, новый спринт в index.md + таблицу спринтов current-state.md
7. SPRINT_STATE → 8-ship
8. `superpowers:finishing-a-development-branch` → push + PR + squash-merge + tag
9. Подтверждения hook (обновить mtime trader-expert.md если ADR изменился)
10. Отметка главы "Sprint <N> ship complete"

**Полная процедура** (шаги + антипаттерны + взаимодействие с hooks) — см. SKILL.md. Не дублировать inline здесь.

**Дополнительные skills, применимые в этой фазе:**
- Skill("git-workflow-and-versioning") [Agent Skills L4] — атомарные коммиты, conventional format
- Skill("documentation-and-adrs") [Agent Skills L4] — корректный формат ADR, задокументированные последствия

Обновление SPRINT_STATE:
  sprint: N-complete
  phase: between-sprints
  tag: v0.1.0-alpha.N
  branch: main
  next_action: "Начать Sprint N+1. Запустить брейнштурм."
  completed: [все tasks]
  in_progress: []
  blockers_concerns: [отложено к S(N+1)]
```

---

### ФАЗА 9 — Конец сессии

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

| Hook | Когда | Действие |
|---|---|---|
| SessionStart:compact (claude-mem) | старт | inject 50 observations |
| SessionStart:compact (caveman) | старт | активировать полный режим |
| SessionStart:compact (agent-skills) | старт | загрузить meta-flowchart |
| UserPromptSubmit (claude-mem) | каждый prompt | capture observation |
| UserPromptSubmit (caveman) | каждый prompt | повторно применить caveman |
| PostToolUse (claude-mem) | каждый tool result | capture (кроме SKIP_TOOLS) |
| Stop (claude-mem) | каждый ответ | capture response |
| SessionEnd (claude-mem) | конец сессии | summary + Chroma embedding |
| PreToolUse → git push | попытка push | проверка синхронизации ADR-agent |

---

## Одноразовая настройка (выполнить один раз)

```bash
# Сжать rule files → ~47% экономия токенов каждую сессию
/caveman:compress ~/.claude/CLAUDE.md
/caveman:compress llm-wiki/CLAUDE.md
/caveman:compress ~/.claude/agents/trading-logic-reviewer.md
/caveman:compress ~/.claude/agents/quant-stats-reviewer.md
# Результат: *.original.md (backup) + сжатый основной файл
# Повторить после значительных обновлений файлов
```

---

## Матрица пропусков (anti-bloat)

| Шаг | Пропустить если |
|---|---|
| Фаза 1 orient | SPRINT_STATE.phase = "4-execution" (уже в процессе) |
| brainstorming | исполнение одобренного ADR |
| process-interviewer | первые 3 ответа чёткие |
| context-engineering для brief | ≤ 200 слов, output ≤ 30KB |
| trading-logic-reviewer | чистая документация, 0 логики |
| quant-stats-reviewer | 0 формул |
| data-integrity-reviewer | 0 persistence |
| python-reviewer | domain cleared, < 100 LoC, только tests |
| security-and-hardening | 0 I/O boundary |
| Stage F probes | спринт не касается venue API |
| version-bump skill | git tag уже проставлен |

---

## Карта параллельного dispatch

```
ВСЕГДА ПАРАЛЛЕЛЬНО (один message):
  trading-logic-reviewer + python-reviewer
  trading-logic-reviewer + quant-stats-reviewer
  spec-reviewer(task N) + implementer(task N+1)
  два независимых implementer (разные файлы)

ВСЕГДА ПОСЛЕДОВАТЕЛЬНО:
  implementer → fix → re-review
  migration → tests reading DB
  task N+1 если импортирует код task N
```

---

## Красные флаги

| Симптом | Исправление |
|---|---|
| Читаю сырой ADR без wiki-страницы | wiki/components/ СНАЧАЛА |
| "Где мы?" — спрашиваю пользователя | Read SPRINT_STATE.md СНАЧАЛА |
| Sonnet BLOCKED дважды | escalate opus |
| git push заблокирован hook | Edit ~/.claude/agents/<name>.md → повторить |
| SPRINT_STATE.md устарел/нет | git log -10 + wiki/log.md tail -20 + mem-search |
| Brief > 200 слов без context-engineering | Skill("context-engineering") СНАЧАЛА |
| Читаю весь план при resume | Read только SPRINT_STATE.md → next_action |
| Ревьюеры последовательно | dispatch параллельно (один message) |

---

## Связанное

- [[../decisions/0017-review-agent-harness]] — спецификация L5 domain reviewers
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]] — пример полного цикла
- [[../components/adr-agent-sync-hook]] — PreToolUse hook
- [[../sprints/sprint-06-spot-oco-emulation]] — нарратив спринта S6
- [[../SPRINT_STATE]] — живое состояние проекта (читай первым)
- [[migration-plan]] — 10 спринтов v0.1
