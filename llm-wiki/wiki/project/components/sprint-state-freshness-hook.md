---
title: sprint-state-freshness-check.sh — pre-push hook detecting stale "Следующее действие" references
type: component
tags: [hook, mechanical-enforcement, sprint-state, freshness, pre-push, sprint-32b]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - ~/.claude/hooks/sprint-state-freshness-check.sh
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/SPRINT_STATE.md
---

# sprint-state-freshness-check.sh

**TL;DR:** Pre-push Bash hook. Blocks `git push` если SPRINT_STATE.md "Следующее действие" section ссылается на sprint > 1 sprint behind current. Conservative regex — flags только actionable patterns (`S<N> PHASE X ship`, `S<N> in_progress`, `S<N> next`), пропускает carry-over context (`closes S14 Q2`, `from S12+S13 backlog`).

## Block 1 — Code refs

| Element | Anchor |
|---------|--------|
| Hook script | `~/.claude/hooks/sprint-state-freshness-check.sh` (out-of-repo, executable, 644 → 755) |
| Trigger | Claude Code `PreToolUse` Bash matcher (settings.json registered) |
| Established by | ADR 0046 (Sprint 32b Kit Phase 1) |
| Related to | ADR 0045 (S32 Phase 0) — root cause: SPRINT_STATE staleness wasted 4-12K tokens/sprint pre-fix |

## Block 2 — Description

### Назначение

Mechanical prevention of P0 SPRINT_STATE staleness recurrence. Pre-S32 review revealed "Следующее действие" = "S27 PHASE 8 ship" при S31 between-sprints (4 спринта drift). Cost = 4-12K tokens/sprint в orient confusion. This hook = mechanical guard preventing repeat.

### Trigger conditions

Hook fires:
- ON: `git push` (any variant — `git push origin main`, `git push -u origin <branch>`, etc.)
- OFF: any other Bash command (`pwd`, `ls`, `pytest`, ...)
- OFF: hook self-test invocations (echo|bash hook.sh)

### Logic

```
1. Parse SPRINT_STATE.md frontmatter → CURR_SPRINT (digit only, strip 'b' suffix)
2. Extract "## Следующее действие" section content (awk: heading-bounded)
3. Find ACTIONABLE patterns:
   regex: S[0-9]+[^A-Za-z0-9].{0,30}(PHASE [0-9]|ship|pending|in_progress|next action|in progress)
4. Filter stale: N < CURR_SPRINT - 1 AND N > 0
5. If any stale → exit 2 (block) с helpful error
6. Else → exit 0 (allow)
```

### Conservative scope (false-positive prevention)

**Flagged (true stale):**
- `S25 PHASE 8 ship pending`
- `S20 in_progress`
- `S15 PHASE 4 next action`

**NOT flagged (legitimate context):**
- `closes S14 Q2 carry-over`
- `from S12 + S13 backlog (10+ items)`
- `trader-expert backlog: S20 multi-symbol`
- `S22 honest close pattern reference`

### Fail-open policy

Hook fails OPEN (exit 0) on:
- SPRINT_STATE.md missing
- Frontmatter parse failure
- Python3 missing
- Empty "Следующее действие" section

Fails CLOSED (exit 2) ONLY on conclusive stale-actionable detection.

### Bypass

Last resort: `git push --no-verify` (bypasses ALL pre-push hooks, не just этот). Operator должен document почему bypass обоснован.

### Tests

Tests run при hook creation per ADR 0046 T2:

| Test | Input | Expected |
|------|-------|----------|
| Positive | Current SPRINT_STATE clean (post-S32 ship) | exit 0 |
| Negative | `S25 PHASE 8 ship pending` injected | exit 2 + error message |
| Skip self-test | `echo ... | bash sprint-state-freshness-check.sh` | exit 0 (self-test guard) |
| Skip non-push | `pytest`, `ls`, `pwd` | exit 0 (only git push triggers) |

### Configuration

| Setting | Value |
|---------|-------|
| Path | `~/.claude/hooks/sprint-state-freshness-check.sh` |
| Permissions | 755 (executable) |
| Hook type | PreToolUse |
| Matcher | Bash |
| Registered в | `~/.claude/settings.json` `hooks.PreToolUse[0].hooks` |
| Position | 6th hook (after adr-agent-sync / adr-index-sync / wiki-broken-link / sprint-flow-check / phase-advance) |

### Active hooks count

Post-S32b: **7 active hooks** (was 6 post-S30):
1. adr-agent-sync-check.sh (S17 / ADR 0017)
2. adr-index-sync-check.sh (S8c / pre-S8c-backlog)
3. wiki-broken-link-check.sh (?)
4. sprint-flow-check.sh (S28 / ADR 0041)
5. phase-advance.sh (S30 / ADR 0043)
6. **sprint-state-freshness-check.sh (S32b / ADR 0046)** 🆕
7. caveman-* (session lifecycle, not push-related — counted separately)

## Related

- [[../decisions/0045-sprint-32-kit-phase-0-improvements]] — root cause (P0 staleness pre-S32)
- [[../decisions/0046-sprint-32b-kit-phase-1-improvements]] — этот hook создан здесь
- [[../decisions/0041-sprint-28-process-enforcement]] — sprint-flow-check.sh predecessor pattern
- [[../decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge]] — phase-advance.sh predecessor pattern
- [[../sprints/sprint-32-kit-phase-0-improvements]] — Phase 0 (P0 fixes)
- [[../sprints/sprint-32b-kit-phase-1-improvements]] — Phase 1 (этот hook + 4 other improvements)
- [[adr-agent-sync-hook]] — sister hook (ADR↔agents sync)
- [[adr-index-sync-hook]] — sister hook (ADR↔index sync)
