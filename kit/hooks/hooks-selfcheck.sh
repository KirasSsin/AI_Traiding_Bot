#!/usr/bin/env bash
# hooks-selfcheck.sh — «сторожа сторожей» (S57, KIT-007, из [CLAUDE P1-BASHN]).
#
# Битый bash-хук в Claude Code падает fail-OPEN — молча снимает барьер.
# Этот хук ловит синтаксически битые хуки (bash -n) и:
#   SessionStart      — печатает баннер в контекст сессии (не блокирует: сессия нужна для фикса)
#   PreToolUse Bash   — на `git push` fail-CLOSED: exit 2, пуш заблокирован
#
# Политика: ЕДИНСТВЕННЫЙ fail-CLOSED хук кита (осознанно, см. ADR-заметку в
# llm-wiki/wiki/project/components/hooks-selfcheck-hook.md).
set -u

HOOKS_DIR="${HOOKS_DIR:-$HOME/.claude/hooks}"

payload="$(cat 2>/dev/null || true)"
is_push=0
cmd=""
if [ -n "$payload" ]; then
  cmd=$(printf '%s' "$payload" | python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception:
    print("")' 2>/dev/null || true)
  # Fallback (security review S57): python3 недоступен/парс упал, но payload
  # похож на push — консервативно считаем push, чтобы единственный fail-CLOSED
  # хук не деградировал в fail-OPEN на инфра-ошибке.
  if [ -z "$cmd" ]; then
    case "$payload" in *"git push"*) is_push=1 ;; esac
  fi
  case "$cmd" in
    *"git push"*) is_push=1 ;;
  esac
  # PreToolUse-событие, но не push — не наша забота
  if [ "$is_push" -eq 0 ] && [ -n "$cmd" ]; then exit 0; fi
fi

broken=""
for h in "$HOOKS_DIR"/*.sh; do
  [ -e "$h" ] || continue
  if ! bash -n "$h" 2>/dev/null; then
    broken="$broken $(basename "$h")"
  fi
done

if [ -n "$broken" ]; then
  msg="HOOKS-SELFCHECK: битые хуки (fail-OPEN дыра в обороне):$broken. Прогони bash -n по каждому и почини ДО git push."
  if [ "$is_push" -eq 1 ]; then
    echo "$msg" >&2
    exit 2
  fi
  echo "$msg"
  exit 0
fi
exit 0
