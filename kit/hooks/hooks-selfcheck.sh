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

# S60 (security LOW-1): дрейф docs/manifest.json vs frontmatter source_files.
# WARN-only (не в fail-CLOSED зоне) — manifest это кэш, а не барьер.
manifest_warn=""
_repo="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$_repo" ] && [ -f "$_repo/docs/manifest.json" ] && [ -f "$_repo/kit/hooks/lib/docs_manifest.py" ]; then
  if ! python3 "$_repo/kit/hooks/lib/docs_manifest.py" "$_repo/docs" --check >/dev/null 2>&1; then
    manifest_warn="docs/manifest.json устарел vs source_files — прогони: python3 kit/hooks/lib/docs_manifest.py docs"
  fi
fi

# S68 D7-02: ancestor-scan — CLAUDE.md на walk-up пути (между parent(repo) и $HOME)
# авто-грузится Claude Code КАЖДУЮ сессию + каждому сабагенту = скрытый boot-tax.
# Прецедент: Desktop/CLAUDE.md 43.8KB мёртвого аудита (~13.3k токенов/сессию).
# WARN-only. repo-root CLAUDE.md и $HOME/.claude/CLAUDE.md НЕ на этом пути — не флагаем.
ancestor_warn=""
if [ -n "$_repo" ]; then
  _d="$(dirname "$_repo")"
  while [ "$_d" != "/" ] && [ "$_d" != "$HOME" ]; do
    if [ -f "$_d/CLAUDE.md" ]; then
      _sz=$(wc -c < "$_d/CLAUDE.md" 2>/dev/null | tr -d ' ' || echo 0)
      ancestor_warn="$ancestor_warn $_d/CLAUDE.md(${_sz}B)"
    fi
    _d="$(dirname "$_d")"
  done
fi

if [ -n "$broken" ]; then
  msg="HOOKS-SELFCHECK: битые хуки (fail-OPEN дыра в обороне):$broken. Прогони bash -n по каждому и почини ДО git push."
  if [ "$is_push" -eq 1 ]; then
    echo "$msg" >&2
    exit 2
  fi
  echo "$msg"
  exit 0
fi
[ -z "$manifest_warn" ] || echo "HOOKS-SELFCHECK WARN: $manifest_warn"
[ -z "$ancestor_warn" ] || echo "HOOKS-SELFCHECK WARN: walk-up CLAUDE.md (boot-tax, грузится каждую сессию):$ancestor_warn — рассмотри архив+удаление с walk-up пути"
exit 0
