---
name: kit-conventions
description: Операционные конвенции кита AI Trading Bot — полная справка (progressive disclosure). Грузи когда (1) пишешь operator-facing текст на русском ИЛИ сомневаешься в англицизме → language-rules секция; (2) собираешься делать multi-file Edit, запускать project-Python/pytest/uvicorn, править хук, ИЛИ поймал token-waste ошибку → anti-waste секция. Компактные сводки живут в repo CLAUDE.md; эта справка = единственная ПОЛНАЯ копия деталей.
---

# Kit conventions — полная справка

Repo `CLAUDE.md` держит 3-строчные сводки (always-on поведение). Здесь — детальные таблицы (on-demand). Если сводка и эта справка расходятся — права эта справка (single source of detail); синхронизируй сводку.

---

## 1. Language rules (BINDING)

Канал → язык. Чат/ADR/wiki/sprint-страницы = **русский** (оператор читает напрямую). Inter-agent/код/коммиты = **English**.

| Канал | Язык | Rationale |
|-------|------|-----------|
| **Чат с operator** (responses, questions, sprint reports) | **Русский** | User-facing |
| **ADR** в `llm-wiki/wiki/project/decisions/*.md` | **Русский** | User reads directly |
| **Wiki pages** в `llm-wiki/wiki/` (components, sprints, architecture, strategies) | **Русский** | User-facing knowledge base |
| **Sprint summaries / brainstorm verdicts / plan files** | **Русский** | User reviews |
| **Subagent inter-communication** (briefs, agent prompts/responses) | **English** | Agents trained на English; внутренний канал |
| **Code / identifiers / file paths** | **English** | Tooling convention |
| **Code comments в `src/`** | **English** | Production standard |
| **Code comments в `research/`** | **Russian OK** | Research toy paradigm |
| **Commit messages** | **English** | Conventional Commits standard |
| **Error messages в коде** | **English** | Logging standard |

Технические термины (file paths, code blocks, error strings, command names, library names) — как есть внутри русского текста.

### Запрещённые англицизмы → русские (чат с operator, НЕ inter-agent)

| ❌ Англицизм | ✓ Русский |
|---|---|
| Bucket | Блок / Группа |
| scope | объём / охват |
| tasks | задачи |
| Recommended / Recommendation | Рекомендация |
| concern / concerns | замечание / замечания |
| split | разделение |
| diff | разница |
| review | ревью / проверка |
| feedback | обратная связь |
| backlog | бэклог (можно оставить — устоявшийся) |
| roadmap | дорожная карта / план |

**ОСТАВИТЬ как есть (технические):** ADR, PHASE, BLOCKER, WFA, DSR, MC, FSM, RAW, PASS, FAIL, verdict; file paths (`MetricsTable.tsx`); function/class names (`get_glossary`); library names (React, pybit, FastAPI); error strings exact; commit messages (English); code blocks (English).

**Анти-пример (S48):** ❌ «В рамках S48 у нас 22 tasks across 5 buckets. Critical concerns про X — recommend split.» → ✓ «В рамках S48 у нас 22 задачи в 5 блоках. Критические замечания про X — рекомендую разделение.»

---

## 2. Anti-waste tool patterns (BINDING — CRITICAL)

| Pattern | Rule | Cost on miss |
|---------|------|--------------|
| **Edit-after-Read** | Read × N batch THEN Edit × N batch (never skip STEP 1). **После мутирующего tool (kit-inventory AUTO-regen / ruff --fix / скрипт-правка / hook, тронувшего файл) — re-Read перед Edit** (иначе "modified since read"). | 3× per unread file |
| **Path verification** | `AI_Traiding_Bot` exact spelling (NOT `_Tool`/`_Trader`/`_Trading`). Verify via `pwd` если doubt. Don't-retry on Read miss (max 1 retry → `ls <parent>` OR surface "path missing"). | hallucination compounds |
| **MEMORY.md tolerance** | `.claude/agent-memory/<agent>/MEMORY.md` (**project-local**, NOT `~/.claude/agent-memory/`) may NOT exist (created on first WRITE). Read failure = expected. | wasted Read |
| **Hook bash quirk** | `bash -n <script>` after editing `~/.claude/hooks/*.sh` / `kit/hooks/*.sh`. Triple-backtick inside `<<'PYEOF'` heredoc ломается молча — extract python в `kit/hooks/lib/<name>.py`. | push fails → debug cycle |
| **Uvicorn port collision** | Kill leftover process before `--port 8000 &` start (S47). Pattern ниже. | kill + restart retry |
| **Pre-commit ruff retry** | ruff --fix modifies но не re-stage. First commit fails, second succeeds. Expected 1-retry. | 1 extra commit attempt |
| **Bare `python` exit 127** | `python` не на PATH macOS (только `python3` system OR `.venv/bin/python`). Project code → ALWAYS `.venv/bin/python`; stdlib-only check (yaml/json/regex) → `python3` OK. NEVER bare `python`. | command not found retry |
| **`.pre-commit-config.yaml` unstaged** | Editing pre-commit config → stage BEFORE OR с next commit (framework блокирует ЛЮБОЙ commit с "configuration is unstaged"). | commit blocked retry |
| **Workflow-парс** (S65, 151×) | Plain JS, named schema consts (не inline deep literals), НЕ TS-аннотации/генерики, НЕ вложенные backticks в template (→ `[...].join()`). Гайд: `.claude/skills/workflow-authoring/SKILL.md`. Свежесозданный агент не dispatchable до reload реестра. | весь workflow-запуск падает |
| **Invisible/control chars** (S65) | unicode/regex payload строить через `python3` (chr()/escape) или файл, НЕ literal-paste в Edit `old_string` / Bash command. | Edit "String not found" / Bash reject |
| **Op-detect false-fire** (S65) | Текст с литералом `gh pr merge`/`git push` НЕ передавать через Bash (grep/echo/heredoc/комменты) — использовать Edit/Write/Grep tools. | гейт-блок + разбор |
| **zsh quirks** (S65) | glob без совпадений = fail ("no matches found") → кавычки/`2>/dev/null`; `$N[` парсится как array-math → кавычки или `bash -c`. | retry |
| **git-checkout-clobber** (S65) | НЕ `git checkout -- <file>` / `git checkout <ref> -- <file>` при uncommitted правках — stash/commit сначала (единственный класс с ПОТЕРЕЙ РАБОТЫ). | потеря работы |

**Uvicorn background test pattern (S47):**
```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null || true   # kill leftover
.venv/bin/uvicorn src.dashboard.app:create_app --factory --port 8000 &
APP_PID=$!
sleep 2
# ... curl tests ...
kill $APP_PID 2>/dev/null; wait $APP_PID 2>/dev/null
```
Alternative: `--port 0` (random) + extract from stdout — robust для parallel runs.

**ADR-agent-sync pre-push (S47):** ADR changed → `touch ~/.claude/agents/<reviewer>.md` BEFORE push. See `sprint-finish` Step 6b.

Полная таксономия token-waste (S65, 9 классов): `llm-wiki/wiki/project/components/error-taxonomy.md`.
