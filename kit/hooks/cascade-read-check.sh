#!/usr/bin/env bash
# cascade-read-check.sh — S62 P1-CASCADE: WARN при полном чтении banned/крупных
# файлов (Read-без-limit / cat). Логика — во внешнем python (P1-BASHN).
# WARN-only (fail-OPEN): подсказка offset/grep, не барьер.
set -u

LIB="$HOME/.claude/hooks/lib/cascade_check.py"
[ -f "$LIB" ] || exit 0

payload="$(cat 2>/dev/null || true)"
[ -n "$payload" ] || exit 0
printf '%s' "$payload" | python3 "$LIB" || true
exit 0
