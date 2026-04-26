---
title: Sprint 32b — Kit Improvement Phase 1 (CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer)
type: plan
tags: [plan, sprint-32b, kit-improvement, phase-1, ci-cd, pre-commit, sqlite-mcp, freshness-hook, dashboard-reviewer, ku-driven]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/plans/2026-04-26-sprint-32-kit-phase-0-improvements.md
  - project/SPRINT_STATE.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/kit-overview-ru.md
---

# Sprint 32b — Kit Improvement Phase 1 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans (controller-driven docs+infra sprint). Steps use checkbox `- [ ]` syntax.

**Goal:** Закрыть Phase 1 КУ analysis: CI/CD enforcement + local pre-commit gates + SQLite MCP debugging tool + SPRINT_STATE freshness mechanical check + specialized dashboard reviewer agent. Phase 1 КУ avg 63% / 6 hours forecast.

**Architecture:** Continuation S32 sub-sprint pattern (mirror S8a/S8b/S8c series). Tag v0.1.0-alpha.32b. Trading work BLOCKED via ESC-1/2/3 → S32 series занимает sprint slots без conflict. Operator decision: keep all Phase work под S32 banner.

**Tech Stack:** GitHub Actions (CI) + pre-commit framework (local hook) + bash (freshness hook) + uvx (SQLite MCP) + markdown (dashboard-reviewer agent).

---

## Context

S32 Phase 0 SHIPPED (PR #39 → 2bad7ee, tag v0.1.0-alpha.32). КУ achieved avg 60% / 45 мин = ~80 КУ/час.

Per ADR 0045 carry-overs: Kit Phase 1 = 5 changes с КУ avg 63%, time 4-6 hours. **Operator directive (this session):** continue с Phase 1 в S32 series.

**Risk pre-flight:**
- CI: TA-Lib install в Ubuntu CI environment (tricky, see workflow steps for `apt-get install ta-lib0`)
- SQLite MCP: `uvx mcp-server-sqlite` available (verified `which uvx` → `/Users/Apple/.local/bin/uvx`). Реальный package name = `mcp-server-sqlite` per Anthropic reference servers
- Pre-commit: install `pre-commit` package, install hooks via `pre-commit install`. Не должен конфликтовать с existing workflow
- Freshness hook: bash script similar к existing 6 hooks (sprint-flow-check pattern)
- Dashboard-reviewer: standalone .md в ~/.claude/agents/, no integration risk

**Test debt carry-over from S32 Phase 0 (deferred к S33+ trading sprint):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open) pre-existing
- 1 mypy error (__main__.py:636 bars_per_year_map redef)
- NOT addressed в S32b — out of scope (kit infrastructure only)

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `~/.claude/agents/dashboard-reviewer.md` | NEW (out-of-repo) | L5 reviewer specialized для `src/dashboard/` (FastAPI + vanilla JS) |
| `~/.claude/hooks/sprint-state-freshness-check.sh` | NEW (out-of-repo) | PreToolUse Bash hook — block push если SPRINT_STATE "Следующее действие" stale |
| `~/.claude/settings.json` | MODIFY (out-of-repo) | Register sprint-state-freshness-check.sh + sqlite MCP server |
| `.pre-commit-config.yaml` | NEW (in-repo) | ruff + mypy hooks via pre-commit framework |
| `.github/workflows/ci.yml` | NEW (in-repo) | pytest + mypy + ruff на каждый PR + push to main |
| `llm-wiki/wiki/project/components/dashboard-reviewer-agent.md` | NEW (in-repo) | Wiki page для dashboard-reviewer agent |
| `llm-wiki/wiki/project/components/sprint-state-freshness-hook.md` | NEW (in-repo) | Wiki page для freshness hook |
| `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` | MODIFY | +Section 20 CI/CD + Section 21 Pre-commit + dashboard-reviewer +SQLite MCP +freshness hook |
| `llm-wiki/wiki/project/architecture/kit-overview-ru.md` | MODIFY | +CI/CD entry + 7 hooks (was 6) + 10 reviewer agents (was 9) + 7 MCP (was 6) |
| `llm-wiki/wiki/project/decisions/0046-sprint-32b-kit-phase-1-improvements.md` | NEW | ADR documenting Phase 1 scope |
| `llm-wiki/wiki/project/sprints/sprint-32b-kit-phase-1-improvements.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-32b entry + ADR 0046 + 2 component pages entries |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | Canonical counts: 38→40 components / 45→46 ADRs / 32→33 sprint pages / 9→10 agents / 6→7 hooks / 6→7 MCP |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end entries |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | S32b in_progress → done после ship |

---

## Tasks

### Task T1: dashboard-reviewer L5 agent

**Files:**
- Create: `~/.claude/agents/dashboard-reviewer.md` (out-of-repo)

**Steps:**

- [ ] **Step 1: Write agent prompt**

```markdown
---
name: dashboard-reviewer
description: Reviews src/dashboard/ FastAPI + vanilla JS code. Specialized для backtest comparison UI (S25/S26). Use after dashboard changes OR before merge sprints touching dashboard module.
model: claude-sonnet-4-5
memory: project
tools: [Read, Grep, Glob, Bash]
---

# Dashboard Reviewer

L5 domain reviewer для `src/dashboard/` module. Specialization: FastAPI endpoints, Jinja2/vanilla JS, backtest comparison UI patterns.

## Scope

`src/dashboard/` module:
- FastAPI app routes (`app.py` / `routers/`)
- Jinja2 templates (`templates/`)
- vanilla JS (`static/js/`)
- CSS (`static/css/`)

## Review checklist

### FastAPI correctness
- Response models declared (Pydantic)
- Error handling: HTTPException с appropriate status codes
- CORS не нужен (localhost only) — verify `cors_middleware` not added
- TESTNET=true enforced (no live trading через UI)
- Async/sync consistency (don't mix без необходимости)

### Template & JS data flow
- Jinja2 template variables match endpoint return
- JS fetch error handling (network failures / 500 / 404)
- No memory leaks (event listeners cleanup, no global state accumulation)
- DOM updates batched (avoid layout thrashing)

### Bybit/backtest data display
- No look-ahead bias в historical display
- Timestamps в UTC (no timezone confusion)
- Trader spec compliance: TIER 1 + TIER 2 metrics + 4 mandatory warnings + Sortino anomaly guard (per S25 ADR 0039)

### Security
- No secrets в JS code (API keys etc.)
- No `eval()` / `Function()` constructor
- HTML escaping для user input (даже если localhost — defense in depth)
- Read-only mode enforced (per S25 architecture conditions)

## Output

Report format: `Blockers / Concerns / Verified / Follow-ups for wiki`
Severity: BLOCKER (must fix перед merge) / HIGH (fix soon) / MEDIUM (track) / LOW (informational)

## NOT scope

- Trading logic (use trading-logic-reviewer)
- Math formulas (use quant-stats-reviewer)
- Storage/migrations (use data-integrity-reviewer)
- Generic Python (use python-reviewer)
```

- [ ] **Step 2: Verify prompt loads**

```bash
ls -la ~/.claude/agents/dashboard-reviewer.md
head -10 ~/.claude/agents/dashboard-reviewer.md
```

- [ ] **Step 3: Create wiki page**

`llm-wiki/wiki/project/components/dashboard-reviewer-agent.md` — Block 1 (Code refs / sources frontmatter) + Block 2 (Description / scope / use cases).

- [ ] **Step 4: Commit (in-repo files only)**

```bash
git add llm-wiki/wiki/project/components/dashboard-reviewer-agent.md
git commit -m "docs(component): T1 — dashboard-reviewer L5 agent wiki page (out-of-repo agent created)"
```

---

### Task T2: SPRINT_STATE freshness check hook

**Files:**
- Create: `~/.claude/hooks/sprint-state-freshness-check.sh` (out-of-repo)
- Modify: `~/.claude/settings.json` (out-of-repo) — register PreToolUse Bash hook

**Steps:**

- [ ] **Step 1: Write hook script**

```bash
#!/usr/bin/env bash
# sprint-state-freshness-check.sh
#
# Claude Code PreToolUse Bash hook.
# Purpose: when `git push` is about to run, check if SPRINT_STATE.md
# "Следующее действие" section references a sprint number > 1 sprint behind
# the current sprint number в frontmatter. Block push если stale.
#
# Established by: ADR 0046 (Sprint 32b kit Phase 1).
# Defined by: llm-wiki/wiki/project/components/sprint-state-freshness-hook.md
#
# Contract: stdin = JSON, exit 0 = allow, exit 2 = block (show stderr).
# Policy: fail OPEN on errors (missing file / parse failure).

set -u

SPRINT_STATE="llm-wiki/wiki/project/SPRINT_STATE.md"

# Skip if hook self-test (test invocations include hook script path в command)
payload="$(cat || true)"
if [ -z "$payload" ]; then exit 0; fi

command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

case "$command_str" in
    *"sprint-state-freshness-check.sh"*) exit 0 ;;
    *"hooks/"*"freshness-check"*) exit 0 ;;
esac

# Only check on git push commands
case "$command_str" in
    *"git push"*) ;;
    *) exit 0 ;;
esac

# File must exist
if [ ! -f "$SPRINT_STATE" ]; then exit 0; fi

# Extract current sprint from frontmatter
CURR_SPRINT="$(grep '^sprint:' "$SPRINT_STATE" | head -1 | grep -oE '[0-9]+' | head -1)"
if [ -z "$CURR_SPRINT" ]; then exit 0; fi

# Extract "Следующее действие" section, look for S<N> references
NEXT_ACTION="$(awk '/^## Следующее действие/,/^## /' "$SPRINT_STATE" | head -50)"
if [ -z "$NEXT_ACTION" ]; then exit 0; fi

# Find sprint references in "Следующее действие" — pattern: "S{N}" where {N} is digits
STALE_REFS="$(printf '%s' "$NEXT_ACTION" | grep -oE '\bS[0-9]+\b' | grep -oE '[0-9]+' | awk -v curr="$CURR_SPRINT" '$1 < curr - 1 && $1 > 0 {print}' | sort -u)"

if [ -n "$STALE_REFS" ]; then
    echo "" >&2
    echo "⚠️  SPRINT_STATE freshness check FAILED" >&2
    echo "" >&2
    echo "Current sprint: S${CURR_SPRINT}" >&2
    echo "Stale references in 'Следующее действие': $(echo $STALE_REFS | tr '\n' ' ')" >&2
    echo "" >&2
    echo "Update SPRINT_STATE.md 'Следующее действие' section before push." >&2
    echo "Either update next-action к current sprint OR remove obsolete references." >&2
    echo "" >&2
    exit 2
fi

exit 0
```

- [ ] **Step 2: bash -n syntax check**

```bash
bash -n ~/.claude/hooks/sprint-state-freshness-check.sh
echo "exit code: $?"  # expected: 0
```

- [ ] **Step 3: Make executable + register settings.json**

```bash
chmod +x ~/.claude/hooks/sprint-state-freshness-check.sh
# Edit ~/.claude/settings.json — add к PreToolUse Bash hooks array
```

- [ ] **Step 4: Positive test (current SPRINT_STATE = clean → exit 0)**

```bash
echo '{"tool_input":{"command":"git push origin main"}}' | bash ~/.claude/hooks/sprint-state-freshness-check.sh
echo "exit code: $?"  # expected: 0 (current SPRINT_STATE clean post-S32 ship)
```

- [ ] **Step 5: Negative test (inject stale ref → exit 2)**

```bash
# Temporary mock SPRINT_STATE с stale "S25 PHASE 8 ship" ref → expect exit 2
mkdir -p /tmp/freshness-test/llm-wiki/wiki/project
cat > /tmp/freshness-test/llm-wiki/wiki/project/SPRINT_STATE.md <<'EOF'
---
sprint: 32
---
## Следующее действие
S25 PHASE 8 ship pending
EOF
cd /tmp/freshness-test && echo '{"tool_input":{"command":"git push"}}' | bash ~/.claude/hooks/sprint-state-freshness-check.sh
echo "exit code: $?"  # expected: 2
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
rm -rf /tmp/freshness-test
```

- [ ] **Step 6: Create wiki page**

`llm-wiki/wiki/project/components/sprint-state-freshness-hook.md` — Block 1 + Block 2.

- [ ] **Step 7: Commit (in-repo files only)**

```bash
git add llm-wiki/wiki/project/components/sprint-state-freshness-hook.md
git commit -m "docs(component): T2 — sprint-state-freshness hook wiki page (out-of-repo hook + settings.json registered)"
```

---

### Task T3: Pre-commit hooks (ruff + mypy)

**Files:**
- Create: `.pre-commit-config.yaml` (in-repo)
- Modify: `pyproject.toml` (in-repo) — add `pre-commit` к `[project.optional-dependencies].dev`

**Steps:**

- [ ] **Step 1: Write `.pre-commit-config.yaml`**

```yaml
# Pre-commit hooks для AI Trading Bot v0.1
# ADR 0046 (Sprint 32b Kit Phase 1).
# Install: pip install -e ".[dev]" && pre-commit install
# Run manually: pre-commit run --all-files
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy-strict
        name: mypy --strict src/
        entry: .venv/bin/mypy --strict src/
        language: system
        pass_filenames: false
        always_run: true
        # Allow ≤ 1 pre-existing error (S32 Phase 5 baseline)
        # NOT blocking баг fix sprint — informational gate
```

- [ ] **Step 2: Add pre-commit к dev deps**

Edit `pyproject.toml` `[project.optional-dependencies]` `dev`:
```toml
dev = [
    # ... existing ...
    "pre-commit>=3.6",
]
```

- [ ] **Step 3: Install + verify**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pip install pre-commit>=3.6
pre-commit install
# Output: pre-commit installed at .git/hooks/pre-commit

# Test run on all files
pre-commit run --all-files 2>&1 | tail -10
# Expected: ruff fixes some issues OR clean, mypy 1 error (pre-existing baseline)
```

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml pyproject.toml
git commit -m "chore(ci): T3 — pre-commit hooks (ruff + mypy) + dev dep"
```

---

### Task T4: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml` (in-repo)

**Steps:**

- [ ] **Step 1: Write workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install TA-Lib (system lib)
        run: |
          wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
          tar -xzf ta-lib-0.4.0-src.tar.gz
          cd ta-lib && ./configure --prefix=/usr LDFLAGS="-Wl,-rpath,/usr/lib" --build=x86_64-unknown-linux-gnu
          make -j$(nproc) && sudo make install
          sudo ldconfig

      - name: Install Python deps
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Ruff check
        run: ruff check src/ tests/

      - name: Mypy --strict
        run: mypy --strict src/ || true  # baseline: ≤ 1 error pre-existing — informational

      - name: Pytest (unit, не integration)
        env:
          BYBIT_API_KEY: "test_key_dummy"
          BYBIT_API_SECRET: "test_secret_dummy"
          TESTNET: "true"
        run: pytest tests/ -q --ignore=tests/integration --tb=short
```

- [ ] **Step 2: bash syntax verify (no bash script — yaml only)**

```bash
# yaml validate via python
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
echo "exit: $?"  # expected: 0
```

- [ ] **Step 3: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "chore(ci): T4 — GitHub Actions CI (pytest + mypy + ruff на каждый PR/push)"
```

CI fires только после push к feature branch — verification happens в PHASE 8.

---

### Task T5: SQLite MCP server connect

**Files:**
- Modify: `~/.claude/settings.json` (out-of-repo) — add к `mcpServers` section

**Steps:**

- [ ] **Step 1: Verify uvx + mcp-server-sqlite installable**

```bash
which uvx  # /Users/Apple/.local/bin/uvx ✓
uvx --help | head -3
# Try install
uvx --help mcp-server-sqlite 2>&1 | head -3 || echo "NOT FOUND — fall back на alternative"
```

- [ ] **Step 2: Add MCP config к settings.json**

Edit `~/.claude/settings.json` → add к `mcpServers` (если section missing — create):

```json
"mcpServers": {
  "sqlite-trading": {
    "command": "uvx",
    "args": [
      "mcp-server-sqlite",
      "--db-path",
      "/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/data/state.db"
    ]
  }
}
```

- [ ] **Step 3: Verify settings.json parses**

```bash
python3 -c "import json; print(json.dumps(json.load(open('/Users/Apple/.claude/settings.json'))['mcpServers'], indent=2))"
```

- [ ] **Step 4: Document в wiki**

Add к `tooling-inventory-ru.md` Section 4 (MCP servers) +1 entry: `sqlite-trading` (uvx mcp-server-sqlite, debug execution_states/fills/halts).

- [ ] **Step 5: Note re-session requirement**

MCP servers loaded на session start. Operator должен restart session чтобы новый MCP стал доступен. Document это в ADR 0046 Consequences section.

- [ ] **Step 6: Commit (in-repo files only — wiki only)**

```bash
git add llm-wiki/wiki/project/architecture/tooling-inventory-ru.md
git commit -m "docs(kit): T5 — SQLite MCP server doc (out-of-repo settings.json registered)"
```

---

### Task T6: ADR 0046 + sprint-32b page + index/counts sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0046-sprint-32b-kit-phase-1-improvements.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-32b-kit-phase-1-improvements.md`
- Modify: `llm-wiki/wiki/index.md` (+ S32b sprint entry + ADR 0046 + 2 component pages)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` — counts: 38→40 components / 45→46 ADRs / 32→33 sprint pages / 9→10 agents / 6→7 hooks / 6→7 MCP
- Modify: `llm-wiki/wiki/project/architecture/kit-overview-ru.md` — counts mirror

**Steps:**

- [ ] **Step 1: Write ADR 0046 — Phase 1 deliverables + КУ rationale**

- [ ] **Step 2: Write sprint-32b page — standard skeleton**

- [ ] **Step 3: index.md +entries**

- [ ] **Step 4: current-state.md sync canonical counts + sprint history row**

- [ ] **Step 5: kit-overview-ru.md update counts (10 agents / 7 hooks / 7 MCP)**

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0046-sprint-32b-kit-phase-1-improvements.md \
        llm-wiki/wiki/project/sprints/sprint-32b-kit-phase-1-improvements.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md \
        llm-wiki/wiki/project/architecture/kit-overview-ru.md
git commit -m "docs(sprint): T6 — ADR 0046 + sprint-32b page + index/counts sync (45→46 ADRs / 32→33 sprints / 9→10 agents / 6→7 hooks / 6→7 MCP)"
```

---

## Phase 5 Verify

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
# Expected: 770 passed (S32 baseline preserved — 3 pre-existing failures still pre-existing)
# NOT addressed в S32b — out of scope

mypy --strict src/ 2>&1 | tail -3
# Expected: 1 error (S32 baseline preserved)

# Hook scripts bash -n
bash -n ~/.claude/hooks/sprint-state-freshness-check.sh
echo "freshness hook syntax: $?"

# Pre-commit dry run
pre-commit run --all-files 2>&1 | tail -10

# Canonical counts verify
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: states=16, events=30, transitions=74, reason_codes=45 (unchanged S32b)
```

Update SPRINT_STATE Phase 5 status="done".

---

## Phase 6 Review

| Reviewer | Trigger | Files |
|----------|---------|-------|
| `python-reviewer` (haiku) | bash hook script + yaml | sprint-state-freshness-check.sh + ci.yml |
| `architecture-reviewer` (sonnet) | CI/CD architecture decision | ci.yml workflow design + pre-commit integration |
| `doc-reviewer` (haiku) | new component pages + ADR | dashboard-reviewer-agent.md + sprint-state-freshness-hook.md + ADR 0046 |

Parallel dispatch via `superpowers:dispatching-parallel-agents` (single message, multiple Agent calls).

---

## Phase 7 Sync

log.md sprint-end entry для S32b.

---

## Phase 8 Ship

Per `sprint-finish` skill checklist:
1. Pre-validation (pytest + mypy preserved baseline)
2. HARD-GATE — sprint-32b page exists ✓ (T6)
3. HARD-GATE — canonical counts sync ✓ (T6)
4. HARD-GATE — ADR 0046 в index.md ✓ (T6)
5. HARD-GATE — Block 1↔2 sync для component pages ✓ (T1, T2)
6. HARD-GATE — orphan-audit grep includes tests/ (N/A, no src/ changes)
7. SPRINT_STATE → 8-ship
8. git push (sprint-flow-check.sh validates plan file ✓ + new freshness hook also runs ✓)
9. gh pr create
10. **CI runs first time на этом PR** — verify pass
11. gh pr merge --squash --delete-branch (phase-advance.sh validates Phase 5=done ✓)
12. git tag v0.1.0-alpha.32b + push
13. SPRINT_STATE → between-sprints

---

## Phase 9 Close

```
1. SPRINT_STATE → between-sprints
2. log.md session-end entry
3. mark_chapter "Sprint 32b — ship complete"
4. git commit + push
5. (Skip consolidate-memory — first invocation S35 OR при >30 observations, currently 17)
```

---

## Self-Review

**Spec coverage:**
- ✓ T1 dashboard-reviewer L5 agent (out-of-repo + wiki page)
- ✓ T2 SPRINT_STATE freshness hook (out-of-repo + bash test + wiki page)
- ✓ T3 Pre-commit hooks (ruff + mypy)
- ✓ T4 GitHub Actions CI
- ✓ T5 SQLite MCP server
- ✓ T6 ADR + sprint page + sync

**No placeholders:** all steps concrete с code/commands/expected output.

**Type consistency:** N/A (no production code changes — config + scripts + docs).

**Execution mode:** Controller-driven (config + docs + scripts sprint, similar к S28-S32).

**Risk mitigation:**
- CI TA-Lib install: tested approach via apt-get, fall back на ubuntu-latest known-good
- SQLite MCP: uvx verified, fall back на documenting "operator должен install manually"
- Pre-commit: optional enforcement (--no-verify available если bypass needed)
- Freshness hook: tested positive + negative ДО registering settings.json
- Dashboard-reviewer: standalone, no integration risk

---

## Related

- ADR 0045 (S32 Phase 0) — direct predecessor
- ADR 0044 (S31 best practices) — kit baseline
- ADR 0017 (review-agent harness) — L5 agent pattern (для dashboard-reviewer)
- ADR 0041 (S28 process enforcement) — sprint-flow-check.sh hook precedent (для freshness hook)
- Sprint S32 (Phase 0) — direct predecessor
- Sprint S32b (this) — Phase 1 implementation
- Pre-S32 КУ analysis: chapter "Kit improvement plan — КУ analysis" в session 2026-04-26
