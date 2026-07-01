#!/usr/bin/env bash
# adr-index-sync-check.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when a `git push` is about to run and the commits being pushed
# include NEW ADR files (wiki/project/decisions/NNNN-*.md), require that
# wiki/index.md references each new ADR. Otherwise block the push.
#
# Defined by: llm-wiki/wiki/project/components/adr-index-sync-hook.md
# Established by: Bucket C6 — pre-S8c process improvement.
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
index_file_rel="llm-wiki/wiki/index.md"
if [ ! -d "$repo_root/$adr_dir_rel" ]; then
    exit 0
fi
if [ ! -f "$repo_root/$index_file_rel" ]; then
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

# Find NEW ADR files added in the range (--diff-filter=A = Added only).
new_adrs="$(git -C "$repo_root" diff --name-only --diff-filter=A "$base"..HEAD -- "$adr_dir_rel" 2>/dev/null | sort -u || true)"

if [ -z "$new_adrs" ]; then
    exit 0
fi

# For each new ADR file, check if wiki/index.md references it.
missing_list=""
while IFS= read -r adr_path; do
    # Extract NNNN-slug.md from the full relative path.
    filename="$(basename "$adr_path")"
    # Extract the NNNN prefix (first 4 chars).
    nnnn="${filename:0:4}"
    # Also check by slug (full stem without .md) for flexibility.
    stem="${filename%.md}"

    # Grep wiki/index.md for any reference to NNNN or the full stem.
    if ! grep -qE "(${nnnn}|${stem})" "$repo_root/$index_file_rel" 2>/dev/null; then
        missing_list="${missing_list}    - ${filename}"$'\n'
    fi
done <<< "$new_adrs"

if [ -n "$missing_list" ]; then
    cat >&2 <<EOF

🚫  ADR ↔ Index sync check FAILED

New ADR file(s) not referenced in wiki/index.md:
${missing_list}
Required action:
  Add entry to wiki/index.md "## Project — Decisions" section.
  Example:
      - [[project/decisions/NNNN-slug]] — One-line summary.

  Then retry push.

(Defined by: llm-wiki/wiki/project/components/adr-index-sync-hook.md
 Policy:     Bucket C6 — pre-S8c process improvement)
EOF
    exit 2
fi

printf '✓ ADR ↔ Index sync OK\n' >&2
exit 0
