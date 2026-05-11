---
name: wiki-update
description: After src/ change, identify wiki pages requiring sync для AI Trading Bot v0.1. Use proactively after editing src/ files OR finishing TDD task. Walks code → docs dependency graph (component pages, ADRs, current-state.md, mental-map.md, Invariants tables) and flags drift. Per Block 1↔Block 2 sync rule.
---

# Wiki Update — code → docs sync after edits

## When to use

Project: AI Trading Bot v0.1 (llm-wiki pattern, code = canonical, docs follow). Triggers:
- After editing any `src/*.py` file (especially `src/execution/`, `src/risk/`, `src/runtime/`)
- After completing TDD task (RED → GREEN → COMMIT) before next task
- Before sprint finish (PHASE 8 step 5a HARD-GATE)
- When user says "update wiki", "sync docs", "что обновить в вики"

## Why this matters

llm-wiki Karpathy pattern: code = source of truth, wiki = compiled summary. Drift = LLM reads stale facts → bad decisions. Pre-S8c discovered TIER 3 invariants tables drift (line numbers, test names) — verification pass was needed. PHASE 8 step 5a HARD-GATE prevents recurrence.

Block 1 (Code refs) и Block 2 (Description) MUST sync в same commit. Edit Block 2 settings → MUST verify Block 1 code path correct.

## Steps (imperative)

### Step 1: List changed src/ files

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git diff --name-only HEAD~1..HEAD -- 'src/*.py' 'src/**/*.py'
git status --short -- 'src/*.py' 'src/**/*.py'
```

Если pure src/ rename — also note для broader wiki refs scan.

### Step 2: For each src/ file, find dependent wiki pages

```bash
for f in <changed src files>; do
  echo "=== $f ==="
  # Find component pages mentioning file
  grep -l "$f" llm-wiki/wiki/project/components/*.md
  # Find ADRs mentioning file
  grep -l "$f" llm-wiki/wiki/project/decisions/*.md
  # Find sprint pages mentioning file
  grep -l "$f" llm-wiki/wiki/project/sprints/*.md
  # Find architecture pages mentioning file
  grep -l "$f" llm-wiki/wiki/project/architecture/*.md
done
```

### Step 3: Per dependent page, verify drift dimensions

For each dependent page, check 4 drift dimensions:

| Dimension | Check |
|-----------|-------|
| **Block 1 (Code refs)** — Sources frontmatter + Public API section + Invariants Enforcement column | Грep `function::name` anchors — still exist в code? Renamed? |
| **Block 2 (Description)** — settings keys + class names + invariant text | Still accurate vs current code? |
| **Canonical counts** (current-state.md) | FSM/reason codes/components count changed? |
| **Mental-map / cluster index** | New domain → add к mental-map.md decision tree? Cluster reassignment? |

### Step 4: Apply targeted updates

Per drift found:
- **Renamed function:** Edit Block 1 anchor (`function::name`)
- **Renamed setting:** Edit Block 2 key + Block 1 source location
- **New invariant:** Add row к Invariants table (canonical 4-column format)
- **Removed invariant:** Strike-through OR delete row (audit trail)
- **Changed FSM count:** Update execution-state-machine.md TL;DR + current-state.md canonical-counts table
- **New reason code:** Update reason-codes-schema.md + current-state.md canonical-counts table + reason_codes.py block comment
- **New component page needed:** Create per template, add к index.md + components/README.md cluster + mental-map.md если new domain

### Step 5: Verify counts match live code

```bash
source .venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Verify output matches current-state.md canonical-counts table values.

### Step 5b: ADR slug resolution before writing links (prevents wiki-broken-link-check.sh failures)

Before writing any `[[../decisions/NNNN-*]]` cross-link в новых sprint/component pages — resolve actual slug:

```bash
# Resolve correct ADR slug (prevents guessing wrong filename)
.claude/scripts/resolve-adr-slug.sh <NNNN>
# Returns: "NNNN-actual-slug-from-filesystem"
# Use exact output as link target
```

Example:
```bash
.claude/scripts/resolve-adr-slug.sh 0014
# → 0014-walk-forward-train2000-test500
# Link: [[../decisions/0014-walk-forward-train2000-test500]]
```

Anti-pattern: guessing slug from memory → `0014-walk-forward` (truncated) → `wiki-broken-link-check.sh` blocks push.

### Step 6: Touch agent prompt если ADR changed

```bash
# Если editing wiki/project/decisions/NNNN-*.md
touch ~/.claude/agents/trading-logic-reviewer.md
```

Acknowledges adr-agent-sync-check hook (per ADR 0017).

### Step 7: Commit с conventional message

```bash
git add llm-wiki/
git commit -m "docs(wiki): sync <component-name> after <change-summary>

- Updated Block 1 anchors (renamed: <old> → <new>)
- Updated Block 2 settings (<key>: <old-value> → <new-value>)
- Added Invariant row #N: <invariant text>
- Updated current-state.md canonical-counts table (<metric> N → M)"
```

## Output to user

Concise list:
- Changed src files: <list>
- Wiki pages requiring sync: <list>
- Drift dimensions detected: <list>
- Updates applied: <count>
- Live counts verify: <output>

Если drift не найден — explicit "No wiki sync needed."

## Anti-patterns

- ❌ Updating wiki ДО code commit (wiki = compiled summary, не source)
- ❌ Skipping canonical counts check (D1+D3 drift root cause)
- ❌ Editing only Block 2 без verifying Block 1 anchor still exists (broken refs)
- ❌ Not touching agent prompt после ADR change (adr-agent-sync hook blocks push)
- ❌ Renaming src function без updating ALL dependent wiki anchors (PR-A verification pass purpose)
- ❌ Guessing ADR slugs in cross-links (wiki-broken-link-check.sh blocks push) — always use `resolve-adr-slug.sh <N>` first

## Related kit references

- Master SOP: `llm-wiki/wiki/project/architecture/development-workflow.md` PHASE 8 step 5a (canonical counts HARD-GATE)
- Block 1/2 paradigm: `llm-wiki/CLAUDE.md` Block 1/Block 2 sync rule (когда documented после PR-B)
- Hook policies: `wiki/project/components/adr-agent-sync-hook.md`
- Wiki maintenance pattern: `llm-wiki/CLAUDE.md` (Karpathy llm-wiki pattern)
- Verification pass methodology: future PR-A
