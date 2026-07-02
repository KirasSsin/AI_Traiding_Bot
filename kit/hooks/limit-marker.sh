#!/usr/bin/env bash
# limit-marker.sh — C1 детектор Auto-Resume (S58, план 2026-07-02-sprint-58-auto-resume).
#
# Claude Code hook: StopFailure. Ход оборвался по API-ошибке; если это
# rate_limit/overloaded — пишем маркер ~/.claude/auto-resume/pending.json,
# который подберёт launchd-опросник auto-resume-poller.sh.
#
# Политика: fail-OPEN (детектор комфорта, не барьер). Логика — во внешнем
# python-файле lib/auto_resume_marker.py (правило P1-BASHN: не heredoc).
set -u

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/auto_resume_marker.py"
[ -f "$LIB" ] || exit 0
python3 "$LIB" || true
exit 0
