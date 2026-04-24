---
name: hook-test
description: Test PreToolUse hook scripts (adr-agent-sync-check, adr-index-sync-check, future hooks) для AI Trading Bot v0.1 без false-positive triggering. Use ONLY when explicitly invoked via /hook-test (disable-model-invocation=true). Uses bash sandbox env -i isolation чтобы избежать hook chain self-trigger.
disable-model-invocation: true
---

# Hook Test — sandboxed PreToolUse hook invocation

## When to use

**Explicit invocation only** (disable-model-invocation: true) — model не auto-trigger. User invokes via `/hook-test` ИЛИ explicit "test the hook script".

Triggers:
- After editing `~/.claude/hooks/<hook>.sh` script — verify changes work
- After adding new PreToolUse hook (e.g., new sync-check)
- Debugging hook false-positive OR false-negative

## Why explicit invocation

Past pain S8c T11: testing `adr-index-sync-check.sh` triggered `adr-agent-sync-check.sh` (sister hook) одновременно — false-positive cascade. Self-test guard added 2026-04-25 (skip if `$command_str` references hook script paths). But manual invocation still safer — env -i isolation bypasses ALL hooks для clean test.

## Steps (imperative)

### Step 1: Identify hook + payload

```bash
# Hooks live в ~/.claude/hooks/
ls ~/.claude/hooks/*.sh

# Hook receives JSON via stdin per Claude Code protocol:
# {"tool_input": {"command": "..."}, ...}
```

Pick test scenarios:
- Positive case (hook should BLOCK) — e.g., real `git push` с violation
- Negative case (hook should ALLOW) — e.g., non-push command
- Edge case (hook self-test scenario) — verify guard skips

### Step 2: Build JSON payload per scenario

```bash
# Real git push (positive — hook should run check)
PAYLOAD='{"tool_input":{"command":"git push origin main"}}'

# Non-push command (negative — hook should allow exit 0)
PAYLOAD='{"tool_input":{"command":"ls -la"}}'

# Hook self-reference (guard test — should skip exit 0 silently)
PAYLOAD='{"tool_input":{"command":"echo test | bash ~/.claude/hooks/adr-agent-sync-check.sh"}}'
```

### Step 3: Sandboxed invocation (env -i isolation)

```bash
# env -i strips environment → prevents PreToolUse hook chain triggering
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" bash -c "
  cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
  echo '$PAYLOAD' | bash ~/.claude/hooks/<hook-name>.sh
  echo \"EXIT_CODE: \$?\"
"
```

Expected exit codes (per Claude Code hook protocol):
- **0** — allow tool call (success OR skip)
- **2** — block tool call + show stderr к user
- Other — fail-open (Claude Code proceeds)

### Step 4: Verify expected behavior

| Scenario | Expected exit | Expected stderr |
|----------|--------------|-----------------|
| Real `git push` без violation | 0 | (empty OR success message) |
| Real `git push` с violation (e.g., new ADR not in index) | 2 | Block message |
| Non-push command | 0 | (empty — case skips) |
| Hook self-test invocation | 0 | (empty — guard skips) |

If exit code OR stderr deviates → hook bug. Investigate.

### Step 5: Document test result

Per test scenario:
- Date tested
- Hook script + version (git log)
- Payload variant
- Expected vs actual exit code
- Pass / FAIL

Append к `wiki/project/components/<hook-name>.md` "Verification" section.

## Anti-patterns (НЕ делать)

- ❌ Test hook through real `git push` (triggers sister hooks + actual remote push side effects)
- ❌ Test без env -i isolation (PreToolUse hook chain может re-trigger)
- ❌ Modify hook script без test scenarios pass (silent regression risk)
- ❌ Skip negative + edge case tests (positive-only = incomplete coverage)
- ❌ Auto-invoke this skill (disable-model-invocation: true — explicit only)

## Real example (S8c T11 testing)

```bash
# Test adr-index-sync-check.sh с dummy ADR scenario
env -i HOME="$HOME" PATH="/usr/bin:/bin" bash -c '
  cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
  echo "{\"tool_input\":{\"command\":\"git push origin test-branch\"}}" | \
    bash ~/.claude/hooks/adr-index-sync-check.sh
  echo "EXIT: $?"
'
```

Expected: exit 2 (новый ADR на test-branch + не в index.md → blocked).

Real result: exit 0 в test environment (no test-branch ADR diff). Validates hook logic correctly skips pure git push без ADR changes.

## Related kit references

- Hook scripts location: `~/.claude/hooks/*.sh` (user-level, outside repo)
- Hook registration: `~/.claude/settings.json` PreToolUse Bash hooks array
- Wiki documentation:
  - `wiki/project/components/adr-agent-sync-hook.md`
  - `wiki/project/components/adr-index-sync-hook.md`
- Self-test guard added 2026-04-25 — see Caveats section в both hook wiki pages
- Claude Code hook protocol: stdin = JSON, exit 2 = block, other non-zero = fail-open
