#!/usr/bin/env bash
# state-integrity-check.sh — S61 Variant B (KIT-008): валидация + авто-восстановление
# SPRINT_STATE.md. SessionStart (проверка при старте) + PreToolUse push.
# Политика fail-OPEN с авто-восстановлением (PRE-PLAN: не дедлочить auto-resume).
# Логика — во внешнем python (P1-BASHN).
set -u

LIB="$HOME/.claude/hooks/lib/state_integrity.py"
[ -f "$LIB" ] || exit 0

payload="$(cat 2>/dev/null || true)"
# PreToolUse: интересует только push; прочие Bash-команды пропускаем
if [ -n "$payload" ]; then
    cmd=$(printf '%s' "$payload" | python3 -c '
import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")' 2>/dev/null || true)
    case "$cmd" in
        # LOW #7 (security-auditor S61): узкий self-skip по форме вызова скрипта,
        # не по подстроке — иначе `git push ... # state-integrity` самопропускался
        *state-integrity-check.sh*|*state_integrity.py*) exit 0 ;;
        *"git push"*) ;;
        "") ;;  # SessionStart (пустой payload)
        *) exit 0 ;;
    esac
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
python3 "$LIB" "$repo_root" || true
exit 0
