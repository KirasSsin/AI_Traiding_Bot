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
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open (Claude Code proceeds with tool call)
#
# Policy: fail OPEN on errors (missing file / parse failure / no python3).
# We only fail CLOSED when we conclusively detect stale references.

set -u

SPRINT_STATE="llm-wiki/wiki/project/SPRINT_STATE.md"

# --- read hook payload -------------------------------------------------------
payload="$(cat || true)"
if [ -z "$payload" ]; then exit 0; fi

# Extract command being proposed. Fail open on parse errors.
command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

# --- skip self-test invocations ----------------------------------------------
# Test invocations include hook script path в command (echo|bash hook.sh).
# Без guard'а каждое test invocation triggers hook ложно.
case "$command_str" in
    *"sprint-state-freshness-check.sh"*) exit 0 ;;
    *"hooks/"*"freshness-check"*) exit 0 ;;
esac

# --- only check on git push commands -----------------------------------------
case "$command_str" in
    *"git push"*) ;;
    *) exit 0 ;;
esac

# --- file must exist (fail open if missing) ----------------------------------
if [ ! -f "$SPRINT_STATE" ]; then exit 0; fi

# --- extract current sprint from frontmatter ---------------------------------
# frontmatter field: `sprint: NN` или `sprint: NNb` (sub-sprint suffix).
# Strip suffix letters → numeric only.
CURR_SPRINT="$(grep '^sprint:' "$SPRINT_STATE" | head -1 | grep -oE '[0-9]+' | head -1)"
if [ -z "$CURR_SPRINT" ]; then exit 0; fi

# --- extract "Следующее действие" section ------------------------------------
# awk: print lines from "## Следующее действие" until next "## " heading.
NEXT_ACTION="$(awk '
    /^## Следующее действие/ {found=1; next}
    found && /^## / {exit}
    found {print}
' "$SPRINT_STATE")"

if [ -z "$NEXT_ACTION" ]; then exit 0; fi

# --- find ACTIONABLE stale sprint references --------------------------------
# Conservative scope: only flag patterns that suggest pending action для old sprint.
# Examples flagged:
#   "S25 PHASE 8 ship pending"   ← stale next-action
#   "S20 in_progress"            ← stale state
#   "S15 ship next"              ← stale pointer
# Examples NOT flagged (context, carry-over historical refs):
#   "closes S14 Q2 carry-over"   ← context
#   "from S12 + S13 backlog"     ← carry-over
#   "trader-expert backlog: S20 multi-symbol"  ← future backlog item
#
# Pattern: S<N> followed (within 30 chars) by action keywords.
ACTIONABLE_PATTERN='S[0-9]+[^A-Za-z0-9].{0,30}(PHASE [0-9]|ship|pending|in_progress|next action|in progress)'

# Find S<N> references matching actionable pattern.
STALE_REFS="$(printf '%s' "$NEXT_ACTION" \
    | grep -oE "$ACTIONABLE_PATTERN" \
    | grep -oE '\bS[0-9]+' \
    | grep -oE '[0-9]+' \
    | awk -v curr="$CURR_SPRINT" '$1 < curr - 1 && $1 > 0 {print}' \
    | sort -un)"

# --- emit error + block если stale -------------------------------------------
if [ -n "$STALE_REFS" ]; then
    echo "" >&2
    echo "⚠️  SPRINT_STATE freshness check FAILED" >&2
    echo "" >&2
    echo "  Current sprint: S${CURR_SPRINT}" >&2
    echo "  Stale references в 'Следующее действие': $(printf '%s' "$STALE_REFS" | tr '\n' ' ')" >&2
    echo "" >&2
    echo "  Update llm-wiki/wiki/project/SPRINT_STATE.md 'Следующее действие' before push." >&2
    echo "  Either update next-action к current sprint OR remove obsolete S<N> references." >&2
    echo "" >&2
    echo "  Note: this is a Claude Code PreToolUse hook, not a git hook." >&2
    echo "  'git push --no-verify' does NOT bypass it (still matches 'git push')." >&2
    echo "" >&2
    exit 2
fi

exit 0
