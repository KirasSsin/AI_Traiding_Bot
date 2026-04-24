---
name: sprint-orient
description: Run PHASE 1 orient sequence for AI Trading Bot v0.1 sprint resumption. Use proactively at session start, when user says "ориентируйся", "где мы", "что в работе", "let's start", "resume sprint", or after `/clear`. Loads SPRINT_STATE + log.md tail + canonical counts + mental-map в правильном порядке для минимизации orientation tokens.
---

# Sprint Orient — PHASE 1 sequence

## When to use

Project: AI Trading Bot v0.1 (Bybit Spot, llm-wiki pattern). Triggers:
- Session start ("где мы остановились", "что в работе", "resume")
- After `/clear` ("ориентируйся заново")
- Switching context between sprints
- Когда maintainer asks "what's the current state?"

Skip если уже в-session с current orientation (don't re-orient on every prompt).

## Why this sequence

Reading raw plan files (50-117KB each) blows context window. SPRINT_STATE (≤2KB) + log tail + canonical counts table — compiled summary, ~10× меньше tokens чем reading plans.

Order matters: SPRINT_STATE first (gives sprint+phase+branch+tag в 30 lines), then log.md tail (recent decisions in chronological context), then current-state.md (canonical counts + sprint history table), then mental-map.md only если user has specific topic query.

## Steps (imperative)

1. **Read SPRINT_STATE.md (≤2KB):**
   ```
   Read /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/llm-wiki/wiki/project/SPRINT_STATE.md
   ```
   Extract: sprint number, phase, branch, tag, "Следующее действие" section.

2. **Verify git state matches SPRINT_STATE:**
   ```bash
   git branch --show-current && git log --oneline -3
   ```
   If branch != SPRINT_STATE branch → flag mismatch.

3. **Read log.md tail (last ~80 lines, NOT full file — 51KB banned-from-full-read):**
   ```
   wc -l llm-wiki/wiki/log.md  # find total
   Read offset=(total-80), limit=80
   ```
   Surface recent sprint events, ADR amendments, carry-overs.

4. **Read canonical counts table:**
   ```
   Read /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/llm-wiki/wiki/project/architecture/current-state.md
   ```
   Get live FSM/reason codes/components/sprints counts (canonical-counts table near top).

5. **mem-search для prior decisions если user has specific concern:**
   ```
   mcp__plugin_claude-mem_mcp-search__smart_search "<topic>"
   ```
   Skip если orient general (не нужен mem-search lookup).

6. **Mark chapter:**
   ```
   mcp__ccd_session__mark_chapter "Sprint <N> — orient"
   ```

7. **(Optional) Load mental-map.md** если user has open-ended query "where is X?":
   ```
   Read /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/llm-wiki/wiki/project/mental-map.md
   ```

## Output to user

Concise summary (≤ 8 bullets):
- Sprint N, phase X, branch Y, tag Z
- Last commit + git status
- Recent log events (top 3)
- Canonical counts (states/events/transitions/reason_codes)
- Carry-overs если есть
- Next action (из SPRINT_STATE "Следующее действие")

Не dump file contents. Synthesize.

## Anti-patterns (НЕ делать)

- ❌ Reading plan files (50-117KB) — use sprint-NN.md sprint page instead (~5KB)
- ❌ Reading log.md полностью (51KB) — use offset/tail only
- ❌ Skipping git verify — mismatch SPRINT_STATE vs actual branch = bug surface
- ❌ Re-orienting каждый prompt — once per session OR after `/clear`
- ❌ Dumping raw file contents — synthesize bullets

## Related kit references

- Master SOP: `llm-wiki/wiki/project/architecture/development-workflow.md` PHASE 1
- 5-layer skills hierarchy: `llm-wiki/CLAUDE.md` Skills hierarchy section
- Banned-from-full-read list: `~/.claude/CLAUDE.md` section 9 + `llm-wiki/CLAUDE.md` Read tool guard
