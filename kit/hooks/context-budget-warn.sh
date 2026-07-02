#!/usr/bin/env bash
# context-budget-warn.sh
#
# Claude Code UserPromptSubmit hook.
# Purpose: warn operator если transcript file size exceeds threshold (proxy для context %).
#
# Established by: ADR 0048 (Sprint 32d Kit Phase 3).
# Defined by: llm-wiki/wiki/project/components/context-budget-hook.md
#
# Contract (Claude Code hook protocol):
#   stdin = JSON: { "transcript_path": "...", "user_prompt": "...", ... }
#   exit 0 = always allow (advisory, never block prompt submission)
#   stderr = warning visible к operator
#
# Threshold tuning (transcript file size as token-count proxy):
#   WARN_KB=800  ≈ ~60% of 200K-token context window (1KB/token avg estimate)
#   URGENT_KB=1200 ≈ ~80% — strongly suggest /compact OR /clear
#
# Crude estimate: actual token count varies 0.5-2.5KB per token depending на content
# (code-heavy = denser, prose-heavy = lighter). Threshold tuned conservative.
#
# Policy: fail OPEN on errors (missing file / parse failure / no python3).

set -u

# Thresholds в KB
WARN_KB=800
URGENT_KB=1200

payload="$(cat || true)"
if [ -z "$payload" ]; then exit 0; fi

# Extract transcript_path. Fail open on parse errors.
transcript_path="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("transcript_path", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
    exit 0
fi

# Get file size в KB. macOS + Linux compatible (du -k returns KB on both).
size_kb=$(du -k "$transcript_path" 2>/dev/null | cut -f1 || echo 0)

# Convert к integer (defensive против leading whitespace)
size_kb=$((size_kb + 0))

msg=""
if [ "$size_kb" -gt "$URGENT_KB" ]; then
    msg="🔴 Context URGENT: transcript ${size_kb}KB (>${URGENT_KB}KB ≈ 80% context window).
   Recommend: /compact <focus topic> OR /clear для new task.
   Continued work без compact = risk session crash на next reply."
elif [ "$size_kb" -gt "$WARN_KB" ]; then
    msg="🟡 Context warning: transcript ${size_kb}KB (>${WARN_KB}KB ≈ 60% context window).
   Consider /compact soon если task continues long."
fi

# S69 T2 (D7-01): WARN на stderr (оператор) + additionalContext на stdout (МОДЕЛЬ).
# UserPromptSubmit exit-0 stderr модели невидим — подсказка про /compact была немой.
if [ -n "$msg" ]; then
    printf '\n%s\n\n' "$msg" >&2
    emit_lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/emit_context.py"
    printf '%s' "$msg" | python3 "$emit_lib" UserPromptSubmit 2>/dev/null || true
fi

exit 0
