---
name: CLAUDE.md stale agent-count anti-pattern
description: Repo CLAUDE.md contains hardcoded agent/skill/hook/MCP counts that drift as kit expands; requires periodic audit
type: project
---

**Pattern:** CLAUDE.md Ключевые файлы table row for `tooling-inventory-ru.md` and `~/.claude/agents/<name>.md` contain hardcoded counts (agents, skills, hooks, MCP). These go stale as new agents/hooks/MCP are added via kit sprints.

**Stale state found 2026-05-09 (S39 gap):**
- `tooling-inventory-ru.md` entry showed "9 reviewer agents + 26 skills + 6 MCP + 6 hooks" — actual was 11 agents, 36 skills, 8 MCP, 7+2+1 hooks
- `~/.claude/agents/<name>.md` entry listed 6 agents — actual was 11
- Skills hierarchy L5 block listed 6 reviewers — actual was 11
- "Current state" line was frozen at "Sprint 8c COMPLETE" — actual was S38/S39

**Why:** Agents added at S30 (security-auditor, test-engineer, doc-reviewer), S32b (dashboard-reviewer), S32d (bybit-api-reviewer) — 5 additions across 5 sprints not reflected in CLAUDE.md bootstrap anchor text.

**Fix applied 2026-05-09:** Updated all 4 occurrences (tooling table row + agents table row + Skills hierarchy block + current state line).

**How to apply:** When reviewing wiki-update or sprint-finish tasks, grep for hardcoded agent counts in CLAUDE.md. If kit sprint added new agent/hook/MCP, CLAUDE.md counts MUST be updated same sprint (HARD-GATE candidate).
