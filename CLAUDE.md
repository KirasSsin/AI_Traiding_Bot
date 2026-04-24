# CLAUDE.md — AI Trading Bot v0.1 (repo root)

Этот файл — bootstrap anchor. Claude Code авто-грузит его при старте сессии в этом репозитории.

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
| `llm-wiki/CLAUDE.md` | Wiki maintainer rules + 5-layer skills hierarchy + trigger cascade |
| `llm-wiki/wiki/project/architecture/development-workflow.md` | MASTER SOP — 9-phase sprint lifecycle |
| `llm-wiki/wiki/index.md` | Wiki catalog (all pages) |
| `llm-wiki/wiki/log.md` | Chronological sprint journal |
| `llm-wiki/wiki/project/decisions/` | ADRs (0001-0023) |
| `llm-wiki/wiki/project/components/` | Component docs (wiki-first reads before raw ADR) |
| `llm-wiki/wiki/project/sprints/sprint-NN-<slug>.md` | **Canonical sprint summary** — "что было сделано в спринте N". HARD-GATE creation per dev-workflow.md PHASE 8 step 5. Read для понимания исторического контекста. |
| `llm-wiki/wiki/project/pre-s{N}-backlog.md` | Pre-sprint backlog — gaps + bugs to discharge before brainstorm S{N}. Создаётся когда post-sprint audit находит actionable items. Закрывается → удаляется. |

## Project constraints (short form)

- **Python**: 3.12 (pyproject.toml). Venv: `.venv/` at repo root.
- **Test cmd**: `pytest -x -q` (unit), `pytest -m integration` (opt-in), `pytest -m property`.
- **Branch**: feature/<sprint-N-slug>. PR to main. Conventional commits.
- **Current state**: Sprint 8b COMPLETE (tag `v0.1.0-alpha.8b`). Between sprints. Next = S8c brainstorm.

## Brainstorming flow (PHASE 2) — BINDING protocol

**Rule of thumb:** controller (главный Claude) НИКОГДА не задаёт user-у scope/architecture вопросы напрямую в PHASE 2. Все open questions ОБЯЗАТЕЛЬНО проходят через trader-expert subagent. User видит только escalation list из trader's output ИЛИ финальный design на approval.

**Pipeline (per `llm-wiki/wiki/project/architecture/development-workflow.md` PHASE 2 step 3a-3f):**

1. Maintainer собирает structured questionnaire — per question: text + recommended option + alternatives + reasoning + risk.
2. Dispatch trader-expert subagent (round 1) с questionnaire.
3. Trader returns per-question CONFIRM / REVISE / DEFER / EXPAND.
4. **Iterative justify loop (round 2)** — для каждого REVISE где chosen option != maintainer's recommended:
   - Maintainer dispatch'ит trader-expert РЕ-РАЗ с brief: "Why <X> over <Y>? Re-evaluate, deeper analysis."
   - Trader выполняет re-investigation, side-by-side compare table, fresh research.
   - Trader returns FINAL: **CONFIRM_REVISE** (round-1 stands, deeper rationale) ИЛИ **CHANGED** (new evidence flipped verdict).
   - Round 2 verdict BINDING. NO round 3.
5. Maintainer logs BOTH rounds в ADR "Decision rationale" (round 1 verdict + round 2 verdict + почему iteration + how resolved).
6. Если trader returned escalation list (product/regulatory/business questions) → user 1 message с конкретными вопросами.

**Anti-patterns — НИКОГДА:**
- Задать user-у вопрос в round 1 brainstorming без trader-expert (S8b violation).
- Принять REVISE-disagreement без round 2 (S8b violation — была ad-hoc accept).
- Третий round trader (round 2 binding).
- Skip trader-expert dispatch потому что "очевидно" — все scope/architecture questions ОБЯЗАТЕЛЬНО проходят trader.

**Acknowledgment trigger:** при старте PHASE 2 в любом sprint — сделать TodoWrite с явным item "Trader-expert round 1 dispatch" + "Trader-expert round 2 dispatch (if any REVISE-disagreement)" чтобы не забыть iterative loop.

## Python venv discipline (MANDATORY for all Bash invocations)

System macOS Python = **3.9** → `ImportError: cannot import name 'StrEnum' from 'enum'` on any `src.execution.state_machine` import. Bare `python` does not exist on PATH (exit 127). Project uses `StrEnum`, PEP 604 unions, modern `pydantic-settings` — needs **3.12**.

**Rule for controller AND every subagent brief:**
- ALWAYS prefix Python invocations with venv:
  - `source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate && python -c "..."`
  - OR direct path: `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/python -c "..."`
- Same for tools: `.venv/bin/pytest`, `.venv/bin/mypy`, `.venv/bin/ruff`.
- NEVER bare `python` / `python3` — fails or returns wrong-Python results.
- When dispatching subagent that may run Python — explicitly include venv path in brief.

## Minimum behavior (overrides по запросу)

- **Все ответы пользователю → русский язык.** Технические термины, file paths, code blocks, error strings, commit messages — оставлять как есть (без перевода).
- Code/identifiers/files → **English**.
- Comments/discussion → **Russian**.
- Read before edit. TDD strict (RED→GREEN→COMMIT).
- YAGNI, DRY, KISS. No "улучшения" сверх scope.
- Token economy: wiki-first (components/ before raw ADR), mem-search first (`mcp__plugin_claude-mem_mcp-search__smart_search`), parallel reviewers, model dispatch (sonnet default, opus for judgment-heavy, haiku for mechanical).

## Skills hierarchy (5 layers — detail в `llm-wiki/CLAUDE.md`)

```
L5: Domain reviewers     (trading-logic / quant-stats / data-integrity / python-reviewer)
L4: Agent Skills + Caveman (depth checklists, compression)
L3: Superpowers          (brainstorm → plan → subagent-driven → TDD → finishing)
L2: llm-wiki             (source of truth — read THIS BEFORE raw files)
L1: claude-mem + ccd_session (session bookends + chapter marks)
```

## Read tool guard (большие файлы)

Hard-limit ~25k токенов = ~90KB. Если файл > 50KB — `Read` с `offset`+`limit` или `Grep`-first. Полный список banned-from-full-read файлов → `~/.claude/CLAUDE.md` секция 9.

---

**Полная методология** → `llm-wiki/CLAUDE.md` + `llm-wiki/wiki/project/architecture/development-workflow.md`.
