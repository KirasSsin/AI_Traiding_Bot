# CLAUDE.md — AI Trading Bot v0.1 (repo root)

Этот файл — bootstrap anchor. Claude Code авто-грузит его при старте сессии в этом репозитории.

## ⚠️ BEFORE ANY SPRINT WORK — kit flow обязателен (BINDING per ADR 0041 + ADR 0042)

**Работа над проектом идёт ТОЛЬКО через спринты (9 фаз).** Ad-hoc правки вне спринта = анти-паттерн. Каждый спринт = идентичный набор фаз; в каждой фазе — одни и те же агенты на одних и тех же моделях/effort. **Кого/на чём звать в фазе N → [`phase-dispatch-ru.md`](llm-wiki/wiki/project/architecture/phase-dispatch-ru.md)** (канон, ADR 0077). Любая работа касающаяся sprint = MUST follow 9 phases. NO shortcuts. NO "очевидно skip". Живой список скиллов: `ls .claude/skills/` (project) + superpowers + agent-skills плагины — не доверяй числам в доках.

| Phase | Primary skill(s) | Optional/sub-skills | HARD-GATE |
|-------|------------------|---------------------|-----------|
| 1 Orient | `sprint-orient` (project) | — | Chapter marked + SPRINT_STATE read |
| 2 Brainstorm | `brainstorm-init` (project) → `trader-expert` | `superpowers:brainstorming` (non-trading scope) | `pre-s{N}-backlog.md` |
| 3 Plan | `superpowers:writing-plans` | `agent-skills:planning-and-task-breakdown` (DEPTH ref) | **Hook `sprint-flow-check.sh` блокирует push без plan file** |
| 4 Execute | `superpowers:subagent-driven-development` (code) OR `superpowers:executing-plans` (docs) + `superpowers:test-driven-development` | `superpowers:systematic-debugging` (bug sub-flow), `superpowers:dispatching-parallel-agents` (parallel reviewers), `agent-skills:context-engineering` (briefs > 200 слов), `ponytail` (минимальный код перед импл, ADR 0072) | Per-task TDD + per-task SPRINT_STATE update |
| 5 Verify | `superpowers:verification-before-completion` | pytest + mypy + canonical counts | All GREEN per checklist + 🔒 **Hook `phase-advance.sh` (S30+) блокирует merge если Phase 5 status != "done"/"skipped"** |
| 6 Review | Domain reviewer (L5: trading-logic / quant-stats / data-integrity / architecture / python) + `superpowers:requesting-code-review` (brief format) + `superpowers:receiving-code-review` (feedback processing) | **`security-auditor` (money/API/override) + `test-engineer` (new modules / coverage gaps) + `doc-reviewer` (post wiki-update)** 🆕 (S30) + `superpowers:dispatching-parallel-agents`, `agent-skills:code-review-and-quality`, `agent-skills:security-and-hardening`, `ponytail-audit` (over-engineering scan, ADR 0072) | Blockers addressed |
| 7 Sync | `wiki-update` (project, llm-wiki RU) | `docs-update` (project, docs/ RU — S56 конвейер doc-writer→depth→linker, затронутые страницы) | Block 1↔Block 2 sync |
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
**Каталог tooling (agents/skills/hooks × phases + cascade):** [`llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`](llm-wiki/wiki/project/architecture/tooling-inventory-ru.md)

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
- ❌ 🆕 (S45 operator decision 2026-05-10) Asking "Subagent-Driven OR Inline Execution?" после `writing-plans` — operator всегда выбирает team. **Auto-invoke `superpowers:subagent-driven-development` БЕЗ asking** (override per `llm-wiki/CLAUDE.md` Autonomous mode overrides table). Skip только если operator EXPLICITLY says "execute inline" перед PHASE 3.
- ❌ 🆕 (S46 operator decision 2026-05-10) Major stack/language/framework migration (e.g. vanilla→React, Python→Rust, REST→GraphQL) БЕЗ `architecture-reviewer` PRE-PLAN validation. **MANDATORY:** dispatch architecture-reviewer ДО plan lock — verdict APPROVE_WITH_CONDITIONS / REQUEST_CHANGES = binding conditions в ADR. Detail: `llm-wiki/CLAUDE.md` Pre-plan validation gates section.
- ❌ 🆕 (S46 post-ship 2026-05-11) **Appending historical sprint sections к SPRINT_STATE.md** — file accumulated 86 KB / 1239 lines с S5-S45 history blocks → exceeded 25k Read tool limit, blocked session-start orient. **BUDGET ≤ 6 KB BINDING.** SPRINT_STATE = current sprint state + roadmap ONLY. History → `wiki/log.md` (chronological journal) + `wiki/project/sprints/sprint-NN-<slug>.md` (canonical per-sprint). PHASE 9 close: trim `Текущий статус` к concise current-sprint bullets, NEVER append "## SN SHIPPED" sections.
- ❌ 🆕 (S48 Bug I 2026-05-11) **Англицизмы в чате с operator** ("Bucket", "scope", "Recommended", "concern") — нарушение Language rules CLAUDE.md section. Использовать русские эквиваленты per Запрещённые англицизмы table (CLAUDE.md). Технические термины (ADR/PHASE/file paths/function names) оставить.

## ПЕРВОЕ ДЕЙСТВИЕ КАЖДОЙ СЕССИИ (обязательно, до всего остального)

```
1. Read: llm-wiki/wiki/project/SPRINT_STATE.md
   → sprint N, phase X, completed tasks, next_action
   (llm-wiki/CLAUDE.md подтянется автоматически как child-memory — НЕ читать отдельно)
2. git branch --show-current && git log --oneline -3
3. mcp__ccd_session__mark_chapter "Sprint N — session resume"
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
| `llm-wiki/wiki/project/SPRINT_STATE.md` | Living sprint state (≤6KB BINDING — current sprint + roadmap only; history → log.md + sprint-NN pages) — FIRST READ |
| **`llm-wiki/wiki/project/architecture/kit-overview-ru.md`** | **Single source of truth gateway (S31) — 1-page TL;DR всех kit settings** |
| `llm-wiki/CLAUDE.md` | Wiki maintainer rules + 5-layer skills hierarchy + trigger cascade |
| `llm-wiki/wiki/project/architecture/development-workflow.md` | MASTER SOP — 9-phase sprint lifecycle |
| `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` | Russian обязательный 9-фаз процесс с per-phase HARD-GATEs (S28 BINDING) |
| `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` | Catalog: agents + skills + MCP + hooks + cascade rule (живые числа — в current-state.md, не тут) |
| `llm-wiki/wiki/index.md` | Wiki catalog (all pages) |
| `llm-wiki/wiki/log.md` | Chronological sprint journal |
| `llm-wiki/wiki/project/decisions/` | ADRs (живой счёт: `ls \| wc -l`) |
| `llm-wiki/wiki/project/components/` | Component docs (wiki-first reads before raw ADR) |
| `llm-wiki/wiki/project/sprints/sprint-NN-<slug>.md` | **Canonical sprint summary** — "что было сделано в спринте N". HARD-GATE creation per dev-workflow.md PHASE 8 step 5. Read для понимания исторического контекста. |
| `llm-wiki/wiki/project/pre-s{N}-backlog.md` | Pre-sprint backlog — gaps + bugs to discharge before brainstorm S{N}. Создаётся когда post-sprint audit находит actionable items. Закрывается → удаляется. |
| `llm-wiki/wiki/project/mental-map.md` | "Where to look for X" decision tree — first-hit для open-ended queries. Заменяет blind grep. |
| `llm-wiki/wiki/project/components/README.md` | 27 components grouped в 9 domain clusters. Reverse lookup ("I'm reading X — what's related?"). |
| `.claude/skills/<name>/SKILL.md` | **Project-level workflow skills** — живой список `ls .claude/skills/`. Auto-trigger по description match; полная процедура в SKILL.md (progressive disclosure), НЕ дублировать inline здесь или в dev-workflow.md. |
| `kit/agents/<name>.md` + зеркало `~/.claude/agents/` | **L5 reviewer agents** (18; живой счёт `ls kit/agents \| wc -l`). ADR 0017 harness; гигиена тел — memory `agent-body-hygiene`. |

## Project constraints (short form)

- **Python**: 3.12 (pyproject.toml). Venv: `.venv/` at repo root.
- **Test cmd**: `pytest -x -q` (unit), `pytest -m integration` (opt-in), `pytest -m property`.
- **Branch**: feature/<sprint-N-slug>. PR to main. Conventional commits.
- **Current state**: ТОЛЬКО из `SPRINT_STATE.md` (single source) — не доверяй снапшоту в любом другом файле.

## Python venv discipline (MANDATORY for all Bash invocations)

System macOS Python = **3.9** → `ImportError: cannot import name 'StrEnum' from 'enum'` on any `src.execution.state_machine` import. Bare `python` does not exist on PATH (exit 127). Project uses `StrEnum`, PEP 604 unions, modern `pydantic-settings` — needs **3.12**.

**Rule for controller AND every subagent brief:**
- ALWAYS prefix Python invocations with venv:
  - `source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate && python -c "..."`
  - OR direct path: `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/python -c "..."`
- Same for tools: `.venv/bin/pytest`, `.venv/bin/mypy`, `.venv/bin/ruff`.
- NEVER bare `python` / `python3` — fails or returns wrong-Python results.
- When dispatching subagent that may run Python — explicitly include venv path in brief.

Same for tools: `.venv/bin/pytest` / `.venv/bin/mypy` / `.venv/bin/ruff` / `.venv/bin/uvicorn`. Stdlib-only validation (yaml/json/regex) → `python3` OK; project code import → MUST `.venv/bin/python`.

## Language rules (BINDING)

**Чат с operator / ADR / wiki / sprint-страницы / plan-файлы = русский** (оператор читает напрямую). **Inter-agent briefs / code / identifiers / commit messages / error strings = English.** `research/` комментарии — Russian OK. Технические термины (пути, code blocks, имена функций/библиотек) — как есть внутри русского.

Полный канал×язык + таблица запрещённых англицизмов (bucket→блок, scope→объём, concern→замечание, …) → скилл `kit-conventions` (грузи перед operator-facing текстом при сомнении).

## Kit cycle MANDATORY (BINDING per ADR 0041 — пересмотрено 2026-05-09)

ВСЕГДА следовать 9-фазовому kit cycle (PHASE 1-9 per `dev-workflow.md`), КРОМЕ:
- Operator explicitly says "**autoresearch**" / "**запусти autoresearch**" / "**autoresearch N итераций**"
- В этом случае — **bypass kit**, follow `research/program.md` autoresearch toy rules
- После autoresearch завершения — **return к kit cycle** для production integration (если PASS found)

**Anti-patterns:**
- ❌ Skip kit потому что "очевидно" / "тривиально" / "быстро"
- ❌ Code на feature/sprint-* branch без plan file (hook `sprint-flow-check.sh` БЛОКИРУЕТ push)
- ❌ Merge sprint без Phase 5 status="done" (hook `phase-advance.sh` БЛОКИРУЕТ)

**Auto-Resume (S58):** упёрся в usage-лимит → хук StopFailure пишет маркер, launchd-опросник возобновляет прогон через `claude -p --resume` при сбросе. НЕ отключать хук StopFailure и не удалять `~/.claude/auto-resume/` — это контур непрерывности. Опора механизма = актуальный `next_action` в SPRINT_STATE (per-task протокол). Детали: `llm-wiki/wiki/project/components/auto-resume.md`; управление: `kit/auto-resume/install.sh status|uninstall`.

## Doc-first + Docs-Sync Gate (BINDING, S60/S64)

**Порядок документации в каждом спринте** (директива оператора 2026-07-02):

1. **Фаза 3 (Plan) — техническая страница llm-wiki ДО кода.** План обязан создать/обновить техстраницу `llm-wiki/wiki/project/**` (components/ или architecture/, на **РУССКОМ** — оператор валидирует) в том же коммите, что plan-файл. Нет техстраницы → Фаза 4 (код) не начинается. Принуждение: `skill-manifest.sh` строка «3b Doc-first» (advisory) + HARD-GATE Фазы 3 в `sprint-flow-ru.md`.
2. **Фаза 7 (Sync) — пользовательские `docs/` ПОСЛЕ кода.** `wiki-update` (llm-wiki/, RU) + `docs-update` (docs/, RU, S56-конвейер doc-writer→depth→linker, только затронутые страницы).
3. **Гейт `docs/` = WARN (не блок, решение оператора S64):**
   - `docs-staleness-check.sh` → git push: источник (`src/**`/`kit/**`) с привязкой `source_files:` изменён, страница нет → **WARN** (список «источник → страница», пуш НЕ блокируется — реши осознанно). Escape `[docs-ignore]` для тривиального.
   - `docs-broken-link-check.sh` → git push: битые `[[ссылки]]` в каноничном корпусе docs/ (00-10) → **БЛОК** (остаётся жёстким — это гигиена, не покрытие).

**Язык:** llm-wiki + docs/ + sprint-страницы = **русский** (валидация оператором). Код/идентификаторы/inter-agent = English. Anti-pattern: «код раньше техстраницы» / «техстраница задним числом в Фазе 7». НЕ вписывать секреты в docs/ (под git).

## Minimum behavior

- Read before edit. TDD strict (RED→GREEN→COMMIT).
- YAGNI, DRY, KISS. No "улучшения" сверх scope.
- Token economy: wiki-first (components/ before raw ADR), mem-search first (`mcp__plugin_claude-mem_mcp-search__smart_search`), parallel reviewers, model dispatch (sonnet default, opus for judgment-heavy, haiku for mechanical).

## Skills hierarchy (5 layers — detail в `llm-wiki/CLAUDE.md`)

```
L5: Domain reviewers (18 агентов — kit/agents/)
L4: Agent Skills + Caveman (depth checklists, compression)
L3: Superpowers (brainstorm → plan → subagent-driven → TDD → finishing)
L2: llm-wiki (source of truth — read THIS BEFORE raw files)
L1: claude-mem + ccd_session (session bookends + chapter marks)
```

## Read tool guard (большие файлы)

Hard-limit ~25k токенов = ~90KB. Если файл > 50KB — `Read` с `offset`+`limit` или `Grep`-first. Полный список banned-from-full-read файлов → `llm-wiki/CLAUDE.md` секция «Read tool guard».

**Universal split pattern (BINDING — operator decision 2026-05-11):** любой wiki/state/ADR file приближающийся к 50KB → split к indexed parts (НЕ truncate, НЕ overwrite-with-loss):

```
<topic>.md          ← index/primary (frontmatter + minimal current state + pointers)
<topic>-part-2.md   ← continuation
<topic>-part-3.md   ← если still grows
```

Existing examples: `tooling-inventory-ru.md` + `tooling-inventory-ru-part-2.md` (S32e split). `SPRINT_STATE.md` + `archive/SPRINT_STATE-archive-part-1/2.md` (S46 post-ship 2026-05-11 — historical preservation).

**Anti-pattern:** REWRITE-with-discard где historical content нигде else не сохранён. ALWAYS archive раньше trim — content recoverable via git, но dedicated archive file даёт zero-friction lookup.

## Anti-waste tool patterns (BINDING — CRITICAL)

Ядро (always-on): **Read×N batch THEN Edit×N batch** (после мутирующего tool — re-Read перед Edit); `.venv/bin/python` never bare `python` (project code); `bash -n` после правки хука; `AI_Traiding_Bot` exact spelling; ADR changed → впиши `ADR NNNN: <суть>` в ТЕЛО ревьюера перед push (S59 content-check; `touch` mtime мёртв).

Полная таблица (13 классов: workflow-парс, op-detect false-fire, zsh-квирки, git-checkout-clobber, uvicorn port-collision, invisible-chars, …) → скилл `kit-conventions` (грузи перед multi-file Edit / запуском project-Python / правкой хука). Таксономия S65: `llm-wiki/wiki/project/components/error-taxonomy.md`.

---

**Полная методология** → `llm-wiki/CLAUDE.md` + `llm-wiki/wiki/project/architecture/development-workflow.md`.
