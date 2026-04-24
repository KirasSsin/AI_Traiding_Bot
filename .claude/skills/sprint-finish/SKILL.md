---
name: sprint-finish
description: Run PHASE 8 finishing HARD-GATE checklist для AI Trading Bot v0.1 sprint shipment. Use proactively when user says "ship sprint", "финишируем", "merge to main", "tag release", or after subagent-driven-development completes all tasks. Enforces mandatory sprint-NN.md page + canonical counts sync + index.md ADR sync + orphan-audit grep includes tests/.
---

# Sprint Finish — PHASE 8 HARD-GATE checklist

## When to use

Project: AI Trading Bot v0.1 (Bybit Spot, llm-wiki pattern). Triggers:
- All sprint tasks committed, ready к ship
- User explicitly says "финишируем спринт", "ship", "merge"
- After `superpowers:subagent-driven-development` completes all batch tasks
- Before invoking `superpowers:finishing-a-development-branch`

## Why HARD-GATEs exist

Past sprints shipped без sprint-NN.md (S8a + S8b — found post-hoc в pre-S8c batch), без index.md ADR entry (ADR 0022 orphan), без canonical counts sync (D1+D3 drift). Each gap = future session reads stale facts → bad decisions. HARD-GATEs prevent recurrence.

## Steps (imperative)

### Step 1: Pre-validation

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
mypy --strict src/ 2>&1 | tail -3
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: pytest 0 new failures, mypy ≤ baseline (S8c baseline = 44 errors), counts current.

If pytest fails OR new mypy regress → STOP, fix before proceeding.

### Step 2: HARD-GATE — Sprint page exists

```bash
ls llm-wiki/wiki/project/sprints/sprint-<NN>-<slug>.md
```

If missing → CREATE per `sprint-07-resilience.md` skeleton:
- frontmatter (title, type=sprint, tags, created/updated, status=completed, sources=[ADR + plan])
- Sections: Overview / Plan-ADR links / Deliverables (Code/Schema/FSM/Tests/Wiki sub-sections) / FSM growth / Reason codes / Tests / Wiki updates / Open issues для S{N+1} / Key decisions / Related

Source content: log.md sprint-end entry + commit log via `git log --oneline main..HEAD` + plan trace map.

**BLOCKS step 6 если missing.**

### Step 3: HARD-GATE — Canonical counts sync (per dev-workflow.md PHASE 8 step 5a)

Если FSM transitions / events / states / reason codes / components count changed:
- Update `llm-wiki/wiki/project/components/execution-state-machine.md` TL;DR + footer "Last sync: Sprint N (count = X)"
- Update `llm-wiki/wiki/project/architecture/current-state.md` canonical-counts table + sprint history row
- Update `llm-wiki/wiki/project/architecture/reason-codes-schema.md` если reason codes changed
- Update `~/.claude/agents/trader-expert.md` если domain priors hardcode counts (lazy-load pattern preferred — link к current-state.md)

**Anti-pattern:** stale TL;DR / hardcoded counts в trader prompt → trader gives stale verdicts → bad sprint decisions.

### Step 4: HARD-GATE — Wiki sync (per dev-workflow.md PHASE 8 step 5b)

```bash
# Orphan-audit grep MUST include tests/
grep -rn "from src.<changed_module>" src/ tests/
```

For новые ADRs:
```bash
# Verify each new ADR в index.md
for adr in $(git diff --name-only --diff-filter=A main..HEAD -- 'llm-wiki/wiki/project/decisions/*.md'); do
  num=$(basename $adr | grep -oE '^[0-9]+')
  grep "$num" llm-wiki/wiki/index.md || echo "MISSING from index.md: $adr"
done
```

For new component pages:
- Add к `wiki/index.md` "## Project — Components" section (alphabetical)
- Add к `wiki/project/components/README.md` cluster (если applicable)

For new sprint page:
- Add к `wiki/index.md` "## Project — Sprints" section
- Add к `wiki/project/architecture/current-state.md` "Карта спринтов" table

**adr-index-sync-check.sh hook will block push если new ADR не в index.md.**

### Step 5: Update SPRINT_STATE → 8-ship

```yaml
sprint: <N>
phase: 8-ship
branch: feature/sprint-<N>-<slug>
tag: v0.1.0-alpha.<N>
```

### Step 6: Commit + ship

Use `superpowers:finishing-a-development-branch` skill → push branch + gh pr create + squash-merge + tag.

After merge:
- `git checkout main && git fetch origin && git reset --hard origin/main`
- `git tag -a v0.1.0-alpha.<N> -m "<title>" <merge-sha> && git push origin v0.1.0-alpha.<N>`
- Update SPRINT_STATE → between-sprints

### Step 7: Chapter mark

```
mcp__ccd_session__mark_chapter "Sprint <N> ship complete"
```

## Hook interactions (ожидать)

- **adr-agent-sync-check.sh** fires при push: если ADR changed → MUST `touch ~/.claude/agents/trading-logic-reviewer.md` если ADR не affects agents (acknowledge)
- **adr-index-sync-check.sh** fires при push: если new ADR не в index.md → BLOCKS

Pre-emptively touch reviewer prompt + verify index sync ДО push чтобы не loop через hook errors.

## Anti-patterns

- ❌ Tag push без sprint-NN.md (S8a/S8b violations)
- ❌ Tag push без ADR в index.md (ADR 0022 orphan)
- ❌ Tag skip (S4/S5 alpha.4/alpha.5 never created → drift)
- ❌ Skipping canonical counts sync (D1+D3 drift)
- ❌ Orphan-audit grep только src/ (CC1 lesson — MUST include tests/)
- ❌ Forgetting touch agent prompt before push (adr-agent-sync hook blocks)

## Related kit references

- Master SOP: `llm-wiki/wiki/project/architecture/development-workflow.md` PHASE 8 (steps 5/5a/5b/6)
- ADR 0017 (review-agent harness) + amendment 2026-04-25
- Hooks documentation: `wiki/project/components/adr-agent-sync-hook.md` + `adr-index-sync-hook.md`
- Backlog patterns: `wiki/project/pre-s{N}-backlog.md`
