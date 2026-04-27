---
title: Tooling Inventory (RU) — Part 2 (Sections 14-24)
type: architecture
tags: [tooling, kit, inventory, ru, permission-modes, plugin-curation, cli-tools, status-line, token-saver, non-interactive, corpus-scheme, schedule-wire, corpus-research]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - tooling-inventory-ru.md (part 1, Sections 1-13)
  - project/decisions/0044-sprint-31-kit-revision-best-practices.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0047-sprint-32c-kit-phase-2-improvements.md
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/decisions/0049-sprint-32e-kit-audit-doc-sync.md
  - https://docs.claude.com/en/code/best-practices
---

# Tooling Inventory (RU) — Part 2

> **Continuation of [[tooling-inventory-ru]]** (Sections 1-13). Split в S32e per CLAUDE.md sec 9 size threshold (50KB).
>
> **Part 1** (Sections 1-13): Domain agents / Project skills / Superpowers / Agent-Skills / Claude-Mem / Caveman / MCP / Hooks / Token economy / Curated rationale / Anti-patterns / Skills × Phase / Cascade rule.
>
> **Part 2 (this file)** (Sections 14-24): Permission modes / Plugin curation / CLI tools / Status line / Token-saver / Non-interactive + fan-out / Corpus scheme / Schedule wire / Corpus bridges research.

## 14. Permission modes (per Anthropic best practices)

3 режима permissions для balance interruptions vs safety:

| Mode | Trigger | Когда использовать |
|------|---------|-------------------|
| **default** | каждое write/Bash/MCP — prompt | Default — careful operations, real money paths |
| **auto** (`--permission-mode auto`) | classifier reviews → blocks risky | Long-running tasks, trusted general direction (e.g. `claude --permission-mode auto -p "fix all lint errors"`) |
| **acceptEdits** | auto-accept file edits + common Bash | Mid-execution iterations |
| **dontAsk** | auto-deny prompts (allowed tools работают) | Strict scope enforcement |
| **bypassPermissions** | skip all prompts | DANGEROUS — use very carefully |
| **plan** | read-only exploration | Plan Mode для exploration |

### Sandboxing (`/sandbox`)
OS-level isolation restricts filesystem + network access. Allow Claude work freely в bounded space. Use для:
- Sandbox experiments (corpus indexing test, etc)
- Untrusted code review

Detail: https://docs.claude.com/en/permission-modes + /en/sandboxing

### Permission allowlists (`/permissions`)
Permit specific tools known safe (e.g. `npm run lint`, `git commit`, `pytest`). Reduces interruptions без auto mode.

### Recommendation для нашего kit

| Workflow | Mode | Reason |
|----------|------|--------|
| Sprint code work | **default** | Trade money paths — careful |
| Sprint docs/wiki sprint (S28-S31) | **acceptEdits** | Doc edits безопасны |
| Long-running batch (audit_formulas.py sweep) | **auto** | Background ops, classifier blocks risky |
| Mainnet integration changes | **default** + security-auditor mandatory | Money risk |

## 15. Plugin curation (4 active)

Все plugins установлены через official marketplace. Versions tracked.

| Plugin | Version | Skills count | Rationale |
|--------|---------|--------------|-----------|
| **superpowers** | 5.0.7 | 13 | Process layer — brainstorm/plan/execute/ship. Full integration S29. |
| **addy-agent-skills** | 1.0.0 | 21 | Discipline checklists — TDD/security/perf/code-review. DEPTH refs. |
| **claude-mem** | 12.3.7 | 7 | Memory continuity — mem-search/version-bump. Cascade STEP 2. |
| **caveman** | 84cc3c14fa1e | 5 | Mode/compress utility — token economy ~47% saving (CLAUDE.md compress). |

### Rejected plugins
См. [[methodology-rejected]] для полного списка considered-and-rejected packages.

### Plugin install (reproducibility)
```bash
/plugin install superpowers@claude-plugins-official
/plugin install addy-agent-skills
/plugin install claude-mem
/plugin install caveman
```

### Plugin discovery
- `/plugin` — browse marketplace
- `/plugin list` — installed plugins
- `/agents` — list subagents (включая plugin-provided)

## 16. CLI tools (explicit list)

Per best practices: "CLI tools = most context-efficient way to interact с external services."

| Tool | Использование |
|------|--------------|
| `gh` | GitHub: PR create/merge/view, issues, releases. ALWAYS prefer над unauthenticated GitHub API (rate limits). |
| `git` | Version control: branch / commit / push / log / diff |
| `pytest` | Testing: `pytest tests/unit -x -q`, `--cov`, `-m property`, `-m integration` |
| `mypy --strict` | Type checking |
| `ruff` | Linter (replaces flake8/black/isort) |
| `bash -n <script>` | Syntax check после editing `~/.claude/hooks/*.sh` (MANDATORY per CLAUDE.md anti-patterns) |
| `wc -l <file>` | Line count check для CLAUDE.md size discipline |
| `python3 -m scripts.<module>` | Run script с virtualenv |
| `source .venv/bin/activate` | Activate venv (Python 3.12 required per pyproject.toml) |

### Trading-specific scripts
- `python scripts/audit_formulas.py --sweep` — comprehensive formula audit (30 experiments)
- `python -m src wfa --symbols BTCUSDT --start 2023-01-01 --end 2026-04-26 --interval 60` — single WFA run
- `python -m src backfill --symbols BTCUSDT --start 2023-01-01 --end 2026-04-26 --interval 60` — backfill OHLCV

### Discovery pattern (per best practices)
```
"Use 'foo-cli-tool --help' to learn about foo tool, then use it to solve A, B, C."
```
Claude эффективно учит CLI tools которые не знает.

## 17. Status line + context tracking (`/statusline`)

Per best practices: "Track context usage continuously with a custom status line. Context window = #1 constraint."

### Configure (interactive)
```
/statusline
```
Auto-generates Bash script отображать metrics в terminal status line.

### Recommended displayed fields
- Sprint number / phase (read SPRINT_STATE.md)
- Current branch (`git branch --show-current`)
- Last commit SHA (`git log --oneline -1`)
- Context fill % (если accessible через CLI hooks)

### Manual config
Edit `~/.claude/settings.json` или create `~/.claude/scripts/statusline.sh`. Reference: https://docs.claude.com/en/statusline

### Skill для config: `statusline-setup` (built-in)
Automatically invoked when `/statusline` runs.

## 18. Token-saver commands (BINDING — best practices)

Per best practices: "Context window = most important resource to manage. Performance degrades as context fills."

| Command | Когда использовать | Что делает |
|---------|-------------------|-----------|
| **`/btw <question>`** | Side question не относящийся к main task | Answer в dismissible overlay — НЕ enters conversation history |
| **`/rewind` (Esc+Esc)** | Wrong direction / experimental approach | Restore previous conversation+code state OR summarize from message |
| **`/clear`** | Switching между unrelated tasks | Reset context window entirely |
| **`/compact <instructions>`** | Approaching context limit | Controlled summarization preserving critical info |
| **Esc** | Stop Claude mid-action | Preserves context, redirect |
| **`claude --continue`** | Resume последнюю session | Load conversation state |
| **`claude --resume`** | Choose из recent sessions | Interactive session picker |
| **`/rename <name>`** | Sessions span days | Descriptive name для later find |

### Discipline (BINDING)
- `/clear` ОБЯЗАТЕЛЕН между unrelated tasks (kitchen sink session anti-pattern)
- `/btw` для quick lookups (вместо full Read)
- `/rewind` для experimental approaches вместо careful planning каждый шаг
- `claude --continue` для multi-session sprints (preserve state across breaks)

### Anti-patterns (token waste)
- ❌ Long session с irrelevant accumulation (kitchen sink)
- ❌ Correcting same issue 3+ times — `/clear` + better prompt лучше
- ❌ Read full file где Grep + offset Read достаточно
- ❌ Side question в main thread — pollutes context

## 19. Non-interactive mode + fan-out patterns

Per best practices: "Once effective с one Claude, multiply output с parallel sessions, non-interactive mode, fan-out."

### Non-interactive mode (`claude -p`)

```bash
# One-off query
claude -p "Explain what this project does"

# Structured output (parseable)
claude -p "List all API endpoints" --output-format json

# Streaming для real-time processing
claude -p "Analyze this log file" --output-format stream-json
```

Useful для:
- CI/CD pipelines
- Pre-commit hooks
- Automated workflows
- Batch operations

### Fan-out across files

Pattern для bulk operations (migrations, audits):

```bash
# 1. Generate task list
claude -p "list all 200 files needing migration" > files.txt

# 2. Loop с scoped permissions
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)"
done

# 3. Test on few files first → refine prompt → run at scale
```

### `--allowedTools` flag
Restrict tools для batch operations. Critical для unattended runs:

```bash
--allowedTools "Read,Grep,Bash(pytest *)"
```

### `--verbose` flag
Debugging during development. Off в production.

### Pipe data input

```bash
cat error.log | claude -p "Find root cause"
```

### Combined с auto mode (long-running)

```bash
claude --permission-mode auto -p "fix all lint errors"
```
Auto mode classifier reviews commands в background. Aborts если repeatedly blocked (no fallback в non-interactive).

### Multiple parallel sessions

3 ways:
1. **Claude Code desktop app** — manage multiple local sessions visually (each isolated worktree)
2. **Claude Code on the web** — Anthropic cloud VMs
3. **Agent teams** — coordinated multi-session с shared tasks/messaging/team lead

### Writer/Reviewer pattern (parallel sessions)
| Session A (Writer) | Session B (Reviewer) |
|--------------------|---------------------|
| Implement rate limiter | (waits) |
| (waits) | Review @src/middleware/rateLimiter.ts. Look for edge cases, race conditions. |
| Address review feedback | (done) |

Fresh context в Session B = unbiased review.

## 22. Memory corpus categorization scheme (S32c — partial bridge 4 design)

**Status:** Documentation-only design. Implementation script deferred к S32d (research carry-over from S30 + S31 bridges 2-4).

### Problem

claude-mem MCP corpus (currently ~17 observations) flat — no semantic partitioning. mem-search returns noisy results когда обрабатывая queries spanning multiple domains (trading vs process vs debug).

Cascade STEP 2 (`mem-search`) текущая precision low когда:
- Query "did we solve formula bug" → returns mix of formula + process + debug observations
- Query "trader verdict ESC" → returns mix of trading-decisions + general kit observations

После 5-10 спринтов = corpus 50+ observations → noise compounding.

### Proposed scheme — 4 partitions

| Partition | What goes here | Source frontmatter tags |
|-----------|----------------|-------------------------|
| **trading-decisions** | Strategy verdicts (trader-expert), ESC items, ADR rationale, hypothesis test outcomes, MVP acceptance criteria changes | `trading`, `strategy`, `hypothesis`, `esc`, `trader-verdict`, `mvp`, `acceptance-criteria`, `regime`, `dsr-trial` |
| **formula-knowledge** | Math correctness (DSR, Sortino, Kelly, MC, Sharpe), audit findings, formula bug fixes | `formula`, `dsr`, `kelly`, `mc`, `sortino`, `sharpe`, `math`, `audit`, `bug-fix-formula`, `wfa` |
| **process-patterns** | Kit violations, HARD-GATE learnings, sprint-flow improvements, hook bug fixes | `process`, `kit`, `hard-gate`, `sprint-flow`, `hook`, `violation`, `lesson`, `phase-advance` |
| **debug-knowledge** | Past bug → fix patterns, debugging session outputs, error → solution mappings | `debug`, `bug`, `fix`, `error`, `troubleshoot`, `ci-fix`, `regression` |

Орхans (no matching tag) → `uncategorized` partition (fallback).

### Frontmatter tag → partition mapping (pseudo-code)

claude-mem ingest hook должен read frontmatter tags из committed wiki/sprint pages и categorize observations по primary tag intersect.

```python
# pseudo-code (S32d implementation candidate)
PARTITION_MAP = {
    "trading-decisions": {
        "trading", "strategy", "hypothesis", "esc", "trader-verdict",
        "mvp", "acceptance-criteria", "regime", "dsr-trial"
    },
    "formula-knowledge": {
        "formula", "dsr", "kelly", "mc", "sortino", "sharpe",
        "math", "audit", "bug-fix-formula", "wfa"
    },
    "process-patterns": {
        "process", "kit", "hard-gate", "sprint-flow", "hook",
        "violation", "lesson", "phase-advance"
    },
    "debug-knowledge": {
        "debug", "bug", "fix", "error", "troubleshoot",
        "ci-fix", "regression"
    },
}

def categorize(observation_frontmatter: dict) -> str:
    """Return partition name for observation based on frontmatter tags.

    Uses primary intersect — first partition с non-empty tag overlap wins.
    Order matters: trading > formula > process > debug (most specific to least).
    """
    tags = set(observation_frontmatter.get("tags", []))
    for partition in ["trading-decisions", "formula-knowledge",
                      "process-patterns", "debug-knowledge"]:
        if tags & PARTITION_MAP[partition]:
            return partition
    return "uncategorized"
```

### Cascade STEP 2 enhanced (post-implementation)

After bridge 4 implemented, cascade STEP 2 mem-search supports `category:` filter:

```
STEP 2: mem-search                          ← current S32: flat search (noisy)
   ↓ AFTER S32d bridge 4
STEP 2: mem-search category:trading-decisions  ← scoped search, 3-5× higher precision
```

Forecast precision improvement:
- Flat search: ~30% relevant results in top 5
- Categorized search: ~80% relevant results in top 5 (3× improvement)

### Bridges 2-4 status (S30 deferred → S32d candidate)

- **Bridge 2 (corpus periodic sync)** — auto-rebuild corpus от wiki/log.md новых entries
- **Bridge 3 (chapter mark auto-link)** — `mark_chapter` MCP tool creates linked log.md entry
- **Bridge 4 (frontmatter tags → partition)** — этот scheme implemented as ingest hook

### Why scheme docs S32c но script S32d?

- **Scheme** = stable design choice (partition labels + tag mappings) — committable now, no implementation risk
- **Implementation** = needs claude-mem internal API research (ingest hook framework, corpus partition support, search filter syntax) — research scope + new infrastructure dependency
- Splitting scheme ↔ script allows operator review tag mapping before lock-in
- S32c locks scheme в wiki = future implementation has clear target

### How operator can validate scheme

Test scheme manually на existing 17 observations:
```bash
mcp__plugin_claude-mem_mcp-search__list_corpora
# Read each observation's frontmatter
# Manually map к partition per PARTITION_MAP
# Verify majority match expected partition (no orphans за 30%)
```

## 23. anthropic-skills:schedule wire к audit_formulas.py (S32d)

**Status:** Operator setup procedure documented. Schedule registration happens at session level через `mcp__scheduled-tasks__create_scheduled_task` MCP tool — НЕ committable к repo (session-state).

### Goal

Auto-run `scripts/audit_formulas.py` on schedule (weekly OR monthly) → produce `data/formulas_audit_v1.json` snapshot. Operator/Claude can review changes без manual invocation.

### Prerequisites

1. `scripts/audit_formulas.py` runs successfully manually (verified S27)
2. `.venv/` setup at repo root (Python 3.12)
3. `mcp__scheduled-tasks` MCP enabled (✓ default)

### Setup procedure (operator action — ONE-TIME)

```python
# Pseudo-code для invocation в Claude Code session
mcp__scheduled-tasks__create_scheduled_task({
  "name": "audit_formulas_weekly",
  "schedule": "0 9 * * MON",  # cron: Monday 09:00 UTC
  "command": "cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && source .venv/bin/activate && python scripts/audit_formulas.py",
  "output_path": "data/formulas_audit_v1.json"
})
```

### Frequency recommendations

| Phase | Recommended frequency | Rationale |
|-------|----------------------|-----------|
| Active development (S27-style) | Weekly Monday 09:00 UTC | Catch formula regressions early |
| Stable maintenance | Monthly | Reduce noise если formulas not changing |
| Pre-release validation | Daily (temporary) | Confidence в final state |

### Output snapshot pattern

Each run overwrites `data/formulas_audit_v1.json`. Manual snapshot для significant runs:
```bash
cp data/formulas_audit_v1.json data/formulas_audit_v1_$(date +%Y%m%d).json
git add data/formulas_audit_v1_*.json
git commit -m "data: snapshot formulas audit YYYY-MM-DD"
```

### Verification

After schedule registered:
```bash
mcp__scheduled-tasks__list_scheduled_tasks
# Verify "audit_formulas_weekly" present + next_run timestamp
```

### Wire к sprint workflow

Optional integration (S33+ kit work): PostToolUse hook on `mcp__scheduled-tasks__create_scheduled_task` invocation auto-appends к `wiki/log.md` schedule registry.

## 24. Memory corpus bridges 2-4 — feasibility research notes (S32d)

**Status:** Research notes only. Implementation BLOCKED on claude-mem internal API constraints. Не shippable until plugin upstream supports OR fork.

### Bridge 2 — corpus periodic sync (auto-rebuild от wiki/log.md)

**Goal:** mem-search corpus auto-rebuilds when wiki/log.md gets new entries (chronological journal).

**API check:**
- claude-mem MCP exposes: `build_corpus`, `prime_corpus`, `rebuild_corpus`, `list_corpora`, `reprime_corpus`
- ✅ Build/rebuild API exists
- ❌ No "watch directory" / "trigger on file change" мechanism в plugin
- Workaround: Cron-based via anthropic-skills:schedule (Section 23 pattern)

**Implementation cost:** LOW если cron acceptable. Use `mcp__scheduled-tasks__create_scheduled_task` daily 03:00 UTC to invoke `mcp__plugin_claude-mem_mcp-search__rebuild_corpus`.

**Decision:** SHIPPABLE via cron. Operator setup task (not in-repo). S33+ candidate.

### Bridge 3 — chapter mark auto-link к log.md

**Goal:** When `mark_chapter` MCP called, append linked entry к `llm-wiki/wiki/log.md` automatically.

**API check:**
- ccd_session MCP `mark_chapter` tool — does NOT support post-call hooks (one-shot operation)
- ❌ No webhook / callback mechanism в MCP server itself
- Workaround: Claude Code PostToolUse hook fired on `mcp__ccd_session__mark_chapter` invocation

**Implementation cost:** MEDIUM. Need PostToolUse hook script that:
1. Parses chapter title + summary from tool_input JSON
2. Appends к `llm-wiki/wiki/log.md`: `## [YYYY-MM-DD] chapter | <title>\n<summary>`
3. Atomic file write (avoid race conditions, use lockfile или mv-after-write)

**Decision:** SHIPPABLE via PostToolUse hook. Defer к S33+ kit work если operator wants OR skip if redundant с manual log.md updates (current S32 series practice).

### Bridge 4 — frontmatter tags → corpus partition (S32c scheme implementation)

**Goal:** When wiki page committed, parse frontmatter tags + categorize observation into 4 partitions (per S32c Section 22 scheme).

**API check:**
- claude-mem MCP exposes: corpus management API но **NO partition support** в current version
- corpora are flat topical (set via `prime_corpus(corpus_name)`)
- ❌ Cannot create sub-partitions within corpus
- Workaround: Create 4 SEPARATE corpora — `trading-decisions`, `formula-knowledge`, `process-patterns`, `debug-knowledge` (vs partitions inside one corpus)
- Then `mem-search` queries specific corpus instead of "category:" filter

**Implementation cost:** HIGH. Requires:
1. Create 4 corpora via `mcp__plugin_claude-mem_mcp-search__build_corpus(<name>)`
2. PostToolUse OR PreCompact hook that parses frontmatter, calls `mcp__plugin_claude-mem_mcp-search__prime_corpus(<partition>)` then writes observation
3. Cascade STEP 2 syntax change в kit-overview-ru.md + sprint-flow-ru.md: `mem-search corpus:trading-decisions`
4. Existing 17 observations need re-categorization (manual OR script)
5. Update `~/.claude/CLAUDE.md` cascade section

**Decision:** **NOT RECOMMENDED** этот sprint OR next. High effort vs marginal benefit:
- Current 17 observations small — flat search precision adequate
- Bridge 4 implementation = 6-10 hours focused work + possible regression risk
- Re-evaluate когда corpus > 100 observations (likely S40+)

**Alternative (LOW cost, HIGH value):** Operator manually validate scheme на existing observations per S32c Section 22 procedure. If precision noticeably degrades after S40+, revisit Bridge 4.

### Honest recommendation summary

| Bridge | Cost | Value | Recommendation |
|--------|------|-------|----------------|
| Bridge 2 (cron rebuild) | LOW | MEDIUM | ✅ SHIP via operator setup S33+ |
| Bridge 3 (chapter auto-link) | MEDIUM | LOW (manual log practice works) | ⏸️ DEFER unless operator chooses |
| Bridge 4 (partition impl) | HIGH | LOW currently (corpus small) | ❌ NOT recommended until corpus > 100 obs |

### What S32c scheme docs (Section 22) provide despite no impl?

- ✅ Lock partition labels в stable contract (4 names won't change retrospectively)
- ✅ Tag mapping pseudo-code ready для future implementation
- ✅ Operator can manually validate scheme на existing observations (Section 22 procedure)
- ✅ Future kit sprint has clear target если priorities change

**S32 series kit improvement COMPLETE per ADR 0048.** Next kit work — only if specific blocker identified OR operator-prioritized.

## Связанные документы

- [[tooling-inventory-ru]] — Part 1 (Sections 1-13)
- [[kit-overview-ru]] — single source of truth gateway (S31)
- [[sprint-flow-ru]] — обязательный sprint процесс (9 фаз)
- [[kit-audit-2026-04-27]] — Kit audit findings post-S32 series (S32e)
- [[../decisions/0017-review-agent-harness]] — review agents matrix policy
- [[../decisions/0041-sprint-28-process-enforcement]] — process enforcement ADR
- [[../decisions/0042-sprint-29-superpowers-integration]] — full superpowers integration ADR (S29)
- [[../decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge]] — tier-2 agents + cascade ADR (S30) — bridges 2-4 origin
- [[../decisions/0044-sprint-31-kit-revision-best-practices]] — best practices revision (S31)
- [[../decisions/0045-sprint-32-kit-phase-0-improvements]] — Kit Phase 0 (S32)
- [[../decisions/0046-sprint-32b-kit-phase-1-improvements]] — Kit Phase 1 (S32b)
- [[../decisions/0047-sprint-32c-kit-phase-2-improvements]] — Kit Phase 2 (S32c — corpus scheme)
- [[../decisions/0048-sprint-32d-kit-phase-3-improvements]] — Kit Phase 3 final (S32d — corpus research notes)
- [[../decisions/0049-sprint-32e-kit-audit-doc-sync]] — Kit audit + doc sync (S32e — этот split)
- [[methodology-rejected]] — rejected packages + cleanup
- `llm-wiki/CLAUDE.md` — Skills hierarchy & integration
- `~/.claude/CLAUDE.md` — global rules + token economy
- https://docs.claude.com/en/code/best-practices — Anthropic Claude Code best practices
- https://github.com/obra/superpowers — superpowers skills source repo
- https://github.com/thedotmack/claude-mem — claude-mem source repo
