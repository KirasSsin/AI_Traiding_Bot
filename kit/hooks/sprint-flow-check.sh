#!/usr/bin/env bash
# sprint-flow-check.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when a `git push` is about to run on a feature/sprint-NN-* branch,
# require that a plan file exists in llm-wiki/wiki/project/plans/ matching
# pattern <YYYY-MM-DD>-sprint-NN-<slug>.md. Otherwise block the push.
#
# Defined by: llm-wiki/wiki/project/architecture/sprint-flow-ru.md PHASE 3
# Established by: ADR 0041 (S28 process enforcement) — mechanical PHASE 3 enforcement.
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open
#
# Policy: fail OPEN on unexpected errors (no python3, not in repo, no upstream).
# Fail CLOSED only when conclusively detect drift (sprint branch без plan file).

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
    *"sprint-flow-check.sh"*) exit 0 ;;
    *"hooks/"*"flow-check"*) exit 0 ;;
esac

# Only act on git push
case "$command_str" in
    *"git push"*|*"git  push"*) ;;
    *) exit 0 ;;
esac

# --- locate repo -------------------------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

# Opt-in: only repos that contain wiki/project/plans/
plans_dir_rel="llm-wiki/wiki/project/plans"
if [ ! -d "$repo_root/$plans_dir_rel" ]; then
    exit 0
fi

# --- check current branch matches sprint pattern ----------------------------
current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
if [ -z "$current_branch" ]; then
    exit 0
fi

# Match: feature/sprint-NN-<slug> OR feature/sprint-NNa-<slug> (e.g. sprint-08c)
if [[ ! "$current_branch" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]]; then
    exit 0  # not sprint branch, skip
fi

sprint_num="${BASH_REMATCH[1]}"

# --- check plan file exists --------------------------------------------------
# Pattern: <YYYY-MM-DD>-sprint-NN-<slug>.md
plan_files="$(ls "$repo_root/$plans_dir_rel" 2>/dev/null \
    | grep -E "^[0-9]{4}-[0-9]{2}-[0-9]{2}-sprint-${sprint_num}-.+\.md$" \
    || true)"

if [ -z "$plan_files" ]; then
    cat >&2 <<EOF

🚫  Sprint flow check FAILED

Branch: $current_branch (sprint $sprint_num)
Required: plan file matching pattern в llm-wiki/wiki/project/plans/
  <YYYY-MM-DD>-sprint-${sprint_num}-<slug>.md

Found: NONE

Required action:
  1. Invoke 'superpowers:writing-plans' skill to produce plan file
  2. Place в llm-wiki/wiki/project/plans/
  3. Commit
  4. Retry push

Reason: PHASE 3 (Plan writing) — обязательная фаза kit'а.
12 sprints (S16-S27) drifted без plan files. Per ADR 0041 mechanical
enforcement of PHASE 3.

Полный процесс: llm-wiki/wiki/project/architecture/sprint-flow-ru.md
Tooling catalog: llm-wiki/wiki/project/architecture/tooling-inventory-ru.md

(Defined by: ~/.claude/hooks/sprint-flow-check.sh
 Policy:     wiki/project/decisions/0041-sprint-28-process-enforcement.md)
EOF
    exit 2
fi

printf '✓ Sprint flow check OK (plan: %s)\n' "$plan_files" >&2
exit 0
