#!/usr/bin/env bash
# wiki-broken-link-check.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when a `git push` is about to run and the commits being pushed
# include changes to llm-wiki/wiki/**.md files, scan ALL wiki pages для
# broken `[[wiki-link]]` refs (target file does not exist). Block push if
# any broken ref detected.
#
# Defined by: llm-wiki/wiki/project/components/wiki-broken-link-hook.md
# Established by: Bucket C7 — pre-S9 process improvement (2026-04-25).
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open (Claude Code proceeds with tool call)
#
# Policy: fail OPEN on unexpected errors (missing python3, git not a repo,
# no upstream). We only fail CLOSED when we conclusively detect broken refs.

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

# S69 T8/T9 (KIT-OD-1 + zero-forgery): push-детект по резолвнутому argv
# (lib/op_detect.py). substring '*git push*' false-fire'ил (литерал в тексте команды
# ложно гейтил) и пропускал `git -c x=y push`. Self-skip по имени хука УБРАН (тут был
# особо широкий `*hooks/*-check.sh*` — любой путь с -check.sh разоружал гейт); голый
# `bash <hook>.sh` / hook-test-payload op_detect не примет за push. PARSE_ERROR → substring.
op_lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/op_detect.py"
case "$(printf '%s' "$command_str" | python3 "$op_lib" push 2>/dev/null || echo PARSE_ERROR)" in
    GATE) ;;                                                        # git push — гейтим ниже
    allow|skip) exit 0 ;;                                            # не push
    *) case "$command_str" in *"git push"*|*"git  push"*) ;; *) exit 0 ;; esac ;;  # fallback
esac

# --- locate repo + range -----------------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

# This hook is opt-in: only repos that contain llm-wiki/wiki/ are covered.
wiki_dir_rel="llm-wiki/wiki"
if [ ! -d "$repo_root/$wiki_dir_rel" ]; then
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

# Did pushed commits touch any wiki/**.md file? If not, skip scan entirely.
wiki_changed="$(git -C "$repo_root" diff --name-only "$base"..HEAD -- "$wiki_dir_rel" 2>/dev/null | grep '\.md$' | sort -u || true)"

if [ -z "$wiki_changed" ]; then
    exit 0
fi

# --- scan wiki for broken [[link]] refs -------------------------------------
# Python does the heavy lifting: parse `[[...]]` refs from CHANGED wiki/**.md
# files in pushed commits (tighter scope avoids historical plan noise),
# resolve target paths (relative-to-source OR relative-to-wiki-root OR
# relative-to-repo-root для cross-repo refs like [[../../CLAUDE]]),
# verify existence. Output: lines "FILE:LINE: BROKEN_LINK".

# Pass changed file list to python via env var (newline-delimited).
# Heredoc inside $(...) had bash backtick / triple-backtick parsing issues —
# extracted к external script для clean shell + Python separation.
SCAN_SCRIPT="$HOME/.claude/hooks/lib/wiki_broken_link_scan.py"
if [ ! -f "$SCAN_SCRIPT" ]; then
    # Fail-open if scan script missing — don't block push on infra error
    printf '⚠ wiki-broken-link hook: scan script missing, skipping check\n' >&2
    exit 0
fi
broken_report="$(REPO_ROOT="$repo_root" WIKI_ROOT="$repo_root/$wiki_dir_rel" CHANGED_FILES="$wiki_changed" python3 "$SCAN_SCRIPT" 2>/dev/null || true)"
# Sentinel к prevent unbound variable trap
broken_report="${broken_report:-}"
_LEGACY_HEREDOC_DISABLED=true

if [ -z "$broken_report" ]; then
    printf '✓ Wiki broken-link check OK (no broken [[link]] refs)\n' >&2
    exit 0
fi

# --- report + block ----------------------------------------------------------
broken_count="$(printf '%s\n' "$broken_report" | wc -l | tr -d ' ')"

cat >&2 <<EOF

🚫  Wiki broken-link check FAILED

$broken_count broken [[link]] ref(s) detected в llm-wiki/wiki/:

$(printf '%s\n' "$broken_report" | sed 's|^|    |')

Required action — one of:
  1) Fix each broken ref: rename [[old]] → [[correct-target]] OR create
     missing target page.
  2) If the link is intentional placeholder (deferred page) — change syntax
     к plain markdown text (drop [[ ]]) until target exists.

Then retry push.

(Defined by: llm-wiki/wiki/project/components/wiki-broken-link-hook.md
 Policy:     Bucket C7 — pre-S9 process improvement)
EOF

exit 2
