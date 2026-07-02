#!/usr/bin/env bash
# auto-resume-poller.sh — C2 обёртка для launchd (S58 Auto-Resume).
# Вся логика — в lib/auto_resume_poll.py (правило P1-BASHN). launchd имеет
# минимальный PATH → абсолютные пути и явный поиск python3.
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=/usr/bin/python3
[ -x "$PY" ] || PY="$(command -v python3 || true)"
[ -n "$PY" ] || exit 0

exec "$PY" "$DIR/lib/auto_resume_poll.py"
