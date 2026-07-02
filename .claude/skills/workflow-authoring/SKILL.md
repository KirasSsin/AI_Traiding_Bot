---
name: workflow-authoring
description: Use BEFORE writing or editing any Workflow script (agent dispatch via Workflow tool / StructuredOutput harness). Prevents "Invalid workflow script: Unexpected token" parse failures (151x in S57-64 mega-run) and agent-not-in-registry dispatch fails.
---

# Workflow authoring — parse-safe checklist

Workflow scripts are PLAIN JAVASCRIPT. The parser is NOT TypeScript.

## Rules (each = a real failure class from S57-64)
1. NO TypeScript syntax: no type annotations (`x: string[]`), no generics (`Array<T>`), no `as`, no `interface`/`type`, no non-null `!`.
2. Named schema consts: declare output schema as top-level `const SCHEMA = {...}` and reference it by name. NEVER inline deep-nested object literals at the call site — bracket mismatch is the #1 parse killer.
3. NO nested backticks: never put code fences or backticks inside template literals. Long prompt strings → single-quoted strings joined with `+` or `[...].join()`.
4. No control/zero-width chars in embedded prompt text (harness rejects the command). Build exotic chars via explicit escapes, not pasted literals.
5. Minimal script: smallest thing that dispatches. No abstractions. Visually verify bracket balance before running.
6. Registry check: dispatch only `subagent_type`/`agentType` values present in the agent registry at session start. Freshly created agents are NOT dispatchable until session reload (OQ-5, see `llm-wiki/wiki/project/components/kit-team-agents.md`). Agent created this session → stop, note reload needed instead of retrying (cost of that fail = 0 tokens, instant reject — do not loop).

## On "Unexpected token"
Do NOT retry with random edits. Re-check rules 1→2→3 in order (TS annotation → bracket → nested backtick): all 151 past failures were one of these three.

## Model / agent directive (operator, kit mega-run)
Dispatch project kit agents (architecture-reviewer, security-auditor, kit-auditor, etc.) — pinned fable-5 — via Workflow for the heavy analysis; keep the main loop light. See [[../../../llm-wiki/wiki/project/components/kit-team-agents]].

## Phase-checkpoint persistence (BINDING — operator directive 2026-07-02, limit-kill survival)
Usage-limit can kill a run mid-phase (S-deep-research: 30 panels + synthesize died at once). Two layers of survival:
1. **Journal (free, automatic):** every COMPLETED `agent()` call is journaled; `Workflow({scriptPath, resumeFromRunId})` replays them at zero token cost, re-running only failed/new calls. Resume, never relaunch: relaunch = full re-pay. Do NOT edit any agent() call that already succeeded (prompt/opts change = cache miss for it and everything after).
2. **Disk checkpoint per phase (explicit, add to every multi-phase script):** after each phase barrier, dump the phase result to a repo file via a minimal Write-agent, e.g.:
   `await agent('Write this JSON verbatim to <REPO>/llm-wiki/wiki/project/research-evidence/<run>-<phase>.json (create dirs): ' + JSON.stringify(phaseResult).slice(0, 200000), {label: 'checkpoint:<phase>', effort: 'low'})`
   Cost: один дешёвый вызов на фазу; выигрыш: результат фазы читается с диска даже если журнал недоступен (новая сессия, другой runId) и виден оператору немедленно.
3. **Controller duty:** the moment a workflow returns, FIRST Write the full result to disk (git-tracked), THEN analyze. Result-in-notification is context-volatile; disk is not.
