#!/usr/bin/env bash
# pertask-state-warn.sh — KIT-013 (S59): мягкое напоминание per-task протокола.
#
# Claude Code PreToolUse hook (Bash). Событие: `git commit`, в staged-наборе
# есть src/**, но нет SPRINT_STATE.md → WARN в stderr (exit 0, НЕ блокирует —
# не душим bugfix-флоу; решение о блоке — по итогам наблюдений).
set -u

payload="$(cat || true)"
[ -n "$payload" ] || exit 0

command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

case "$command_str" in
    *"pertask-state-warn"*) exit 0 ;;
esac
case "$command_str" in
    *"git commit"*) ;;
    *) exit 0 ;;
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
[ -f "$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md" ] || exit 0

staged="$(git -C "$repo_root" diff --cached --name-only 2>/dev/null || true)"
echo "$staged" | grep -q '^src/' || exit 0
echo "$staged" | grep -q 'SPRINT_STATE\.md$' && exit 0

cat >&2 <<'EOF'
⚠️  Per-task protocol (KIT-013): коммит меняет src/**, но SPRINT_STATE.md не в staged.
   Правило Фазы 4: обновлять SPRINT_STATE ПОСЛЕ КАЖДОЙ задачи (статус, next_action).
   Это WARN, не блок — но при обрыве сессии несохранённый next_action = потерянный контекст.
EOF
exit 0
