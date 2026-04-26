# Sprint 31 — Kit Revision per Best Practices + Single Tools-Overview File

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans`

**Goal:** (1) Create single source-of-truth file для всех kit settings (kit-overview-ru.md). (2) Audit kit per Anthropic Claude Code best practices — apply pruning, missing patterns (auto mode / sandboxing / plugins / CLI tools / status line / `/btw` / `/rewind` / `--continue` / fan-out / non-interactive mode). (3) Prune CLAUDE.md files (3 files = 61KB / 18.5K tokens loaded каждую session — bloated per best practices).

**Architecture:**
- NEW `kit-overview-ru.md` — 1-page TL;DR с links к detail (single source of truth)
- EXPAND `tooling-inventory-ru.md` — sections 14-19 NEW (auto mode / sandboxing / plugins / CLI tools / status line / token-saver commands)
- PRUNE `llm-wiki/CLAUDE.md` (448→<200 lines target) — extract verbose к wiki pages
- AUDIT `~/.claude/CLAUDE.md` (316→<250 lines)
- AUDIT `CLAUDE.md` (repo, 190 lines OK — minor refs add)

**Tech Stack:** Markdown only. Status line config script (Bash). NO src/ code changes.

---

## Context

Operator directive 2026-04-26 после S30 ship:

> "Все наши используемые инструменты (Все настройки нашего кита) укажем в одном файле. А также проведи по ним ревизию, на основе лучших твоих практик [Claude Code best practices URL provided]."
>
> "А также загляни к себе во внутреннюю кодовую базу и используемые инструменты, и адаптируй наш кит под максимальное качество и в тоже время экономию токенов без деградации результата. Ожидаемый результат — увеличение производительности."
>
> "Если нужно вносить правки в глобальные настройки или настройки проекта, учитывай что мы CLAUDE.md делили на файлы."

### Current state baseline

| File | Lines | Bytes | Tokens (~) | Status |
|------|-------|-------|-----------|--------|
| `CLAUDE.md` (repo) | 190 | 14 KB | 4.2K | OK |
| `llm-wiki/CLAUDE.md` | 448 | 27 KB | 8.2K | **BLOATED** |
| `~/.claude/CLAUDE.md` | 316 | 20 KB | 6.0K | BORDERLINE |
| **Total per-session load** | **954** | **61 KB** | **~18.5K** | — |

Per best practices: "Bloated CLAUDE.md files cause Claude to ignore your actual instructions!" Target reduction = 30-40% без losing critical content.

### Best practices gap analysis

Reading [Anthropic Claude Code best practices](https://docs.claude.com/en/code/best-practices), gaps в нашем kit:

| Best practice | Status | Action |
|---------------|--------|--------|
| Verify work (tests/screenshots) | ✅ Done (test-engineer agent S30) | — |
| Plan Mode (explore→plan→code) | ✅ kit Phase 2-3 | — |
| Specific context в prompts | ⚠️ Partial — controller discipline | Add discipline reference |
| CLAUDE.md разумно короткий | ❌ FAIL — 61KB total | **PRUNE** |
| Auto mode permissions | ❌ Not used | Document + recommend |
| Sandboxing | ❌ Not used | Document + recommend для experiments |
| MCP servers | ✅ 6 servers (claude-mem, ccd_session, etc) | — |
| Hooks | ✅ 6 hooks (S30) | — |
| Skills | ✅ 5 project + 13 superpowers + 21 agent-skills | — |
| Subagents | ✅ 9 reviewer agents (S30) | — |
| Plugins | ⚠️ 4 used, no inventory | Document curated set |
| `/clear` discipline | ⚠️ Mentioned, не enforced | Add к anti-patterns |
| `/btw` для side questions | ❌ Not documented | Add к token economy |
| `/rewind` checkpoints | ❌ Not documented | Add к recovery patterns |
| `--continue` / `--resume` | ❌ Not documented | Add к session discipline |
| Non-interactive `claude -p` | ❌ Not documented | Add для batch ops |
| Fan-out parallel sessions | ❌ Not used | Document для bulk operations |
| Custom subagents (built-in: Explore/Plan/general-purpose) | ⚠️ Implicit | Document explicitly |
| Status line (`/statusline`) | ❌ Not configured | Configure для context tracking |
| CLI tools (gh, etc) | ⚠️ gh used implicitly | Document explicit list |
| Common failure patterns | ✅ Anti-patterns documented | Cross-link к best practices |

---

## File Structure

NEW files:
- `llm-wiki/wiki/project/architecture/kit-overview-ru.md` — TL;DR single source of truth (1-page, links к detail)
- `llm-wiki/wiki/project/decisions/0044-sprint-31-kit-revision-best-practices.md` — ADR
- `llm-wiki/wiki/project/sprints/sprint-31-kit-revision-best-practices.md` — sprint page
- `llm-wiki/wiki/project/plans/2026-04-26-sprint-31-kit-revision-best-practices.md` — этот plan

MODIFY:
- `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` — Sections 14-19 NEW
- `llm-wiki/CLAUDE.md` — PRUNE (448→<200 lines)
- `~/.claude/CLAUDE.md` — AUDIT/PRUNE (316→<250 lines)
- `CLAUDE.md` (repo) — minor reference к kit-overview-ru.md
- `llm-wiki/wiki/index.md` — entries для новых docs
- `llm-wiki/wiki/project/architecture/current-state.md` — sprint history row +S31
- `llm-wiki/wiki/log.md` — sprint-end entry
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase tracking

---

## Best Practices Applied

### 1. Pruning principle
Per best practices: "For each line, ask: Would removing this cause Claude to make mistakes? If not, cut it."

Apply к 3 CLAUDE.md files. Extract verbose explanations к standalone wiki pages.

### 2. Auto mode + sandboxing
Document recommended permission modes:
- **Default** — current state, prompts всё
- **Auto mode** (`--permission-mode auto`) — recommended для long-running iterations
- **Sandboxing** — recommended для experimental code

### 3. Status line (`/statusline`)
Per best practices: "Track context usage continuously with a custom status line."

Configure status line script показать:
- Current sprint / phase
- Branch
- Context fill % (если accessible)

### 4. Plugin curation
Document our 4 plugins explicitly:
- claude-plugins-official:superpowers (5.0.7)
- addy-agent-skills (1.0.0)
- thedotmack:claude-mem (12.3.7)
- caveman (84cc3c14fa1e)

### 5. CLI tools explicit list
- `gh` (GitHub) — PR/issue/merge
- `git` (version control)
- `pytest` (testing)
- `mypy` (type check)
- `ruff` (linter)
- `bash -n` (script syntax check)

### 6. Token-saver commands
- `/btw` — side questions без context pollution
- `/rewind` (Esc+Esc) — checkpoint restore
- `/clear` — reset context between unrelated tasks
- `/compact <instructions>` — controlled context summarization
- `claude --continue` / `--resume` — preserve sessions across breaks

### 7. Fan-out + non-interactive mode
Document:
- `claude -p "<prompt>"` — non-interactive single query
- `claude -p ... --output-format json` — parseable
- Loop pattern: `for file in $(...); do claude -p "..."; done`
- `--allowedTools` для scoped permissions

---

## Task Breakdown

### Task 1: kit-overview-ru.md NEW (1-page single source of truth)

**Files:**
- Create: `llm-wiki/wiki/project/architecture/kit-overview-ru.md`

- [ ] **Step 1:** Write 1-page TL;DR:
  - Quick decision matrix ("что invoke когда")
  - Links к detail (sprint-flow-ru, tooling-inventory-ru, ADRs)
  - Top 10 commands operator должен знать
  - 9 reviewer agents 1-line each
  - 6 hooks 1-line each
  - Top 5 anti-patterns

- [ ] **Step 2:** Commit

```bash
git commit -m "docs(s31-t1): kit-overview-ru.md NEW — 1-page single source of truth"
```

### Task 2: tooling-inventory-ru.md sections 14-19 NEW

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`

- [ ] **Step 1:** Section 14 NEW — Permission modes (default / auto / sandboxing) per best practices
- [ ] **Step 2:** Section 15 NEW — Plugin curation (4 active plugins с versions + rationale)
- [ ] **Step 3:** Section 16 NEW — CLI tools (gh / git / pytest / mypy / ruff / bash -n)
- [ ] **Step 4:** Section 17 NEW — Status line + context tracking
- [ ] **Step 5:** Section 18 NEW — Token-saver commands (`/btw` / `/rewind` / `/clear` / `/compact` / `--continue`)
- [ ] **Step 6:** Section 19 NEW — Non-interactive mode + fan-out patterns
- [ ] **Step 7:** Commit

### Task 3: PRUNE llm-wiki/CLAUDE.md (448→<200 lines)

**Files:**
- Modify: `llm-wiki/CLAUDE.md`

- [ ] **Step 1:** Identify verbose sections suitable для extraction:
  - Anthropic best practices alignment (~70 lines) → kit-overview-ru.md OR new wiki page
  - Trigger cascade table (~30 lines) → tooling-inventory-ru.md decision matrix
  - Curated agent set (~25 lines) → tooling-inventory-ru.md Section 1 уже covers
  - Layer 1 claude-mem table (~15 lines) → tooling-inventory-ru.md Section 5
  - Autonomous mode overrides (~20 lines) → kit-overview-ru.md
- [ ] **Step 2:** Replace verbose с brief reference + link к wiki page
- [ ] **Step 3:** Verify line count < 200
- [ ] **Step 4:** Commit

### Task 4: AUDIT ~/.claude/CLAUDE.md (316→<250 lines)

**Files:**
- Modify: `~/.claude/CLAUDE.md`

- [ ] **Step 1:** Identify obsolete OR overly-verbose sections
- [ ] **Step 2:** Apply "would removing cause mistakes" test
- [ ] **Step 3:** Prune
- [ ] **Step 4:** Verify line count < 250
- [ ] **Step 5:** Commit (out-of-repo, отдельно от repo commits)

### Task 5: Repo CLAUDE.md — minor prune + kit-overview link

**Files:**
- Modify: `CLAUDE.md` (repo)

- [ ] **Step 1:** Add reference к kit-overview-ru.md в "Ключевые файлы" table
- [ ] **Step 2:** Audit existing content — apply prune test
- [ ] **Step 3:** Commit

### Task 6: Status line config + `/btw` discipline + checkpoints

**Files:**
- Optional create: `~/.claude/scripts/statusline.sh` (custom status line)
- Modify: `tooling-inventory-ru.md` Section 17

- [ ] **Step 1:** Write minimal status line script показать sprint+phase+branch
- [ ] **Step 2:** Document configuration (run `/statusline` interactive setup)
- [ ] **Step 3:** Add к anti-patterns "❌ Use main session для side questions — use `/btw`"
- [ ] **Step 4:** Add `/rewind` к recovery patterns
- [ ] **Step 5:** Add `--continue` к session discipline
- [ ] **Step 6:** Commit

### Task 7: ADR 0044 + sprint-31 page + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0044-sprint-31-kit-revision-best-practices.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-31-kit-revision-best-practices.md`
- Modify: `llm-wiki/wiki/index.md`, `current-state.md`, `log.md`

- [ ] **Step 1:** ADR с context (best practices audit), 8 decisions (kit-overview / 6 new sections / pruning), consequences с before/after metrics
- [ ] **Step 2:** Sprint page
- [ ] **Step 3:** index + current-state + log

### Task 8: PHASE 5-8 ship

- [ ] **Step 1:** PHASE 5 verify pytest baseline (no code) + measure post-prune CLAUDE.md sizes
- [ ] **Step 2:** Update SPRINT_STATE Phase 5 → done (для phase-advance hook)
- [ ] **Step 3:** Touch agent prompts (ADR sync hook)
- [ ] **Step 4:** Push branch (test all 4 hooks fire)
- [ ] **Step 5:** PR + merge + tag v0.1.0-alpha.31

---

## Self-Review Checklist

- [x] All best practices gaps identified
- [x] Pruning principle applied (would removing cause mistakes?)
- [x] kit-overview-ru.md ≤ 1 page (300 lines max)
- [x] tooling-inventory-ru.md expansion preserves existing 13 sections
- [x] CLAUDE.md split preserved (repo + llm-wiki + global)
- [x] Backward compat (no breaking changes)

## Execution mode

Controller-driven (docs sprint). 7-8 task commits + 1 ship.

## Expected metrics improvement

- CLAUDE.md total: 61 KB → ~40 KB (-35%)
- Tokens loaded per session: 18.5K → ~12K (-35%)
- Sprint context discoverability: scattered → kit-overview-ru.md (1 file)
- Skill invocation precision: improved through better decision matrix
