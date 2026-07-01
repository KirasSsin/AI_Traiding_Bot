#!/usr/bin/env bash
# adr-agent-sync-check.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when a `git push` is about to run and the commits being pushed
# include changes to wiki/project/decisions/NNNN-*.md (an ADR), require that
# at least one prompt in ~/.claude/agents/*.md has been modified at or after
# the latest ADR commit time. Otherwise block the push.
#
# Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md
# Established by: ADR 0017 (review-agent harness).
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open (Claude Code proceeds with tool call)
#
# Policy: fail OPEN on unexpected errors (missing python3, git not a repo,
# no upstream). We only fail CLOSED when we conclusively detect drift.

set -u

AGENTS_DIR="$HOME/.claude/agents"

# --- read hook payload -------------------------------------------------------
payload="$(cat || true)"
if [ -z "$payload" ]; then
    exit 0
fi

# Extract the bash command being proposed. Fail open if python3 missing or
# payload malformed.
command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

# Skip if this is a hook self-test invocation (echo/printf JSON piped к hook
# script для testing). Real `git push` commands don't reference hook script
# paths. Без этого guard'а каждое test invocation ($ echo '...git push...' |
# bash hook.sh) ложно triggers hook через PreToolUse Bash matcher.
case "$command_str" in
    *"adr-agent-sync-check.sh"*|*"adr-index-sync-check.sh"*) exit 0 ;;
    *"hooks/"*"sync-check"*) exit 0 ;;
esac

# Only act on git push. Allow any other command through.
case "$command_str" in
    *"git push"*|*"git  push"*) ;;
    *) exit 0 ;;
esac

# --- locate repo + range -----------------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

# This hook is opt-in: only repos that contain wiki/project/decisions/ are
# covered. Any other repo is unaffected.
adr_dir_rel="llm-wiki/wiki/project/decisions"
if [ ! -d "$repo_root/$adr_dir_rel" ]; then
    exit 0
fi

# Determine commit range. Prefer tracked upstream, fallback to origin/main.
upstream="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -n "$upstream" ]; then
    base="$(git -C "$repo_root" merge-base HEAD "$upstream" 2>/dev/null || true)"
else
    base="$(git -C "$repo_root" merge-base HEAD origin/main 2>/dev/null || true)"
fi

if [ -z "$base" ]; then
    exit 0
fi

# Was any ADR touched in the range? `git log` respects path filtering.
adr_changed="$(git -C "$repo_root" log "$base"..HEAD --name-only --pretty=format: -- "$adr_dir_rel" 2>/dev/null | sed '/^$/d' | sort -u || true)"

if [ -z "$adr_changed" ]; then
    exit 0
fi

# Latest ADR commit time in the range (unix epoch seconds).
latest_adr_ts="$(git -C "$repo_root" log -1 --format='%ct' "$base"..HEAD -- "$adr_dir_rel" 2>/dev/null || true)"
if [ -z "$latest_adr_ts" ]; then
    exit 0
fi

# Latest mtime of any agent prompt.
if [ ! -d "$AGENTS_DIR" ]; then
    cat >&2 <<EOF

🚫  ADR ↔ Agent prompt sync check FAILED

ADR files changed in commits being pushed:
$(printf '%s\n' "$adr_changed" | sed 's/^/    - /')

But $AGENTS_DIR does not exist. Create the directory and the
corresponding reviewer prompt(s), or touch an existing prompt to acknowledge
that no agent update is needed.

(Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md)
EOF
    exit 2
fi

# macOS `stat -f '%m'` is seconds since epoch. Linux would need `stat -c '%Y'`.
# We detect BSD vs GNU stat via uname.
if [ "$(uname)" = "Darwin" ]; then
    latest_agent_mtime="$(find "$AGENTS_DIR" -type f -name '*.md' -exec stat -f '%m' {} + 2>/dev/null | sort -nr | head -1)"
else
    latest_agent_mtime="$(find "$AGENTS_DIR" -type f -name '*.md' -printf '%T@\n' 2>/dev/null | cut -d. -f1 | sort -nr | head -1)"
fi

if [ -z "$latest_agent_mtime" ]; then
    cat >&2 <<EOF

🚫  ADR ↔ Agent prompt sync check FAILED

ADR files changed but no agent prompts exist in $AGENTS_DIR.

$(printf '%s\n' "$adr_changed" | sed 's/^/    - /')

(Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md)
EOF
    exit 2
fi

if [ "$latest_agent_mtime" -lt "$latest_adr_ts" ]; then
    # Format timestamps for the message.
    if [ "$(uname)" = "Darwin" ]; then
        adr_time_h="$(date -r "$latest_adr_ts" '+%Y-%m-%d %H:%M:%S %Z')"
        agent_time_h="$(date -r "$latest_agent_mtime" '+%Y-%m-%d %H:%M:%S %Z')"
    else
        adr_time_h="$(date -d "@$latest_adr_ts" '+%Y-%m-%d %H:%M:%S %Z')"
        agent_time_h="$(date -d "@$latest_agent_mtime" '+%Y-%m-%d %H:%M:%S %Z')"
    fi

    cat >&2 <<EOF

🚫  ADR ↔ Agent prompt sync check FAILED

ADR files changed in commits being pushed:
$(printf '%s\n' "$adr_changed" | sed 's/^/    - /')

Latest ADR commit time:    $adr_time_h
Latest agent prompt mtime: $agent_time_h

Agent prompts in $AGENTS_DIR have not been updated since the ADR change.

Required action — one of:
  1) Update the relevant reviewer prompt(s) under $AGENTS_DIR so they
     reflect the new ADR (e.g. new Kelly phases, new reason codes,
     changed walk-forward params), then retry push.
  2) If the ADR change does not affect any agent prompt, acknowledge by
     touching any prompt to advance its mtime:
         touch $AGENTS_DIR/trading-logic-reviewer.md
     then retry push.

(Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md
 Policy:     ADR 0017 — review-agent harness)
EOF
    exit 2
fi

exit 0
