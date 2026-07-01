#!/usr/bin/env bash
# phase-advance.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when `gh pr merge` is about to run on a feature/sprint-NN-* branch,
# require that SPRINT_STATE.md Phase 5 (Verify) status = "done". Block если
# pending — prevents merging unverified sprint per ADR 0043 (S30 process
# enforcement tier 2).
#
# Defined by: llm-wiki/wiki/project/architecture/sprint-flow-ru.md PHASE 5
# Established by: ADR 0043 (S30 tier-2 enforcement).
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open
#
# Policy: fail OPEN on unexpected errors (no python3, not in repo, no SPRINT_STATE).
# Fail CLOSED only when conclusively detect Phase 5 not done.

set -u

# --- read hook payload -------------------------------------------------------
payload="$(cat || true)"
if [ -z "$payload" ]; then
    exit 0
fi

command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

# Skip self-test invocations
case "$command_str" in
    *"phase-advance.sh"*) exit 0 ;;
    *"hooks/"*"phase-advance"*) exit 0 ;;
esac

# Only act on `gh pr merge` (not gh pr create / view / status)
case "$command_str" in
    *"gh pr merge"*) ;;
    *) exit 0 ;;
esac

# --- locate repo + SPRINT_STATE ---------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

sprint_state_path="$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md"
if [ ! -f "$sprint_state_path" ]; then
    exit 0  # No SPRINT_STATE = not a kit-managed repo
fi

# --- check current branch matches sprint pattern ----------------------------
current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
if [ -z "$current_branch" ]; then
    exit 0
fi

if [[ ! "$current_branch" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]]; then
    exit 0  # not sprint branch, skip
fi

sprint_num="${BASH_REMATCH[1]}"

# --- parse Phase 5 status from SPRINT_STATE ---------------------------------
# Looking for table row pattern:
#   | 5 Verify | done | ... |
#   | 5 Verify | pending | ... |
#   | 5 Verify | in_progress | ... |
#   | 5 Verify | skipped (...) | ... |
phase_5_line="$(grep -E '^\| ?5[ \.]?[Vv]erify ?\|' "$sprint_state_path" 2>/dev/null | head -1 || true)"

if [ -z "$phase_5_line" ]; then
    cat >&2 <<EOF

🚫  Phase advance check FAILED

Branch: $current_branch (sprint $sprint_num)
SPRINT_STATE: $sprint_state_path
Phase 5 (Verify) row not found в Phase tracking table.

Required: Phase tracking table must include "| 5 Verify | done | ... |" row.

Per ADR 0043 (S30): SPRINT_STATE phase tracking template (S28+) обязателен.

(Defined by: ~/.claude/hooks/phase-advance.sh)
EOF
    exit 2
fi

# Extract status (2nd column)
status="$(echo "$phase_5_line" | awk -F'|' '{gsub(/^ +| +$/, "", $3); print $3}' || true)"

# Allow: done | skipped (...)
case "$status" in
    "done"|"skipped"*) ;;
    *)
        cat >&2 <<EOF

🚫  Phase advance check FAILED

Branch: $current_branch (sprint $sprint_num)
SPRINT_STATE: $sprint_state_path
Phase 5 (Verify) status: "$status"

Required: Phase 5 must be "done" OR "skipped" before merge.
- "done" — pytest + mypy + canonical counts passed
- "skipped (...)" — explicit skip с reason (e.g., docs-only sprint)

Required action:
  1. Run \`superpowers:verification-before-completion\` checklist:
     - pytest tests/ -q --ignore=tests/integration
     - mypy --strict src/
     - canonical counts python check
     - Edge cases / runtime smoke / docs updated
  2. Update SPRINT_STATE.md Phase 5 row → "done"
  3. (Or если skip valid: "skipped (reason)")
  4. Retry merge

Per ADR 0043 (S30): Mechanical enforcement of Phase 5 (Verify).

(Defined by: ~/.claude/hooks/phase-advance.sh
 Policy:     wiki/project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md)
EOF
        exit 2
        ;;
esac

printf '✓ Phase advance check OK (Phase 5 status: %s)\n' "$status" >&2
exit 0
