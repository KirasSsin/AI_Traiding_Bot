#!/usr/bin/env bash
# docs-broken-link-check.sh — KIT-016 (S60): битые [[ссылки]] в docs/ блокируют push.
#
# Claude Code PreToolUse hook (Bash). Событие: `git push`, если тронуты docs/**.
# Запускает lib/docs_broken_link_scan.py по каноничному корпусу (docs/0X-*/, 10-*);
# при битых навигационных ссылках — exit 2. Клон wiki-broken-link-check.
# Не-каноничные (KIT.md, _навигация/, superpowers/) вне скана — не пользовательская
# навигация. Policy: fail-OPEN если скрипт отсутствует.
set -u

SCAN="$HOME/.claude/hooks/lib/docs_broken_link_scan.py"

payload="$(cat || true)"
[ -n "$payload" ] || exit 0
command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

case "$command_str" in
    *"docs-broken-link-check"*) exit 0 ;;
esac
case "$command_str" in
    *"git push"*|*"git  push"*) ;;
    *) exit 0 ;;
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
[ -d "$repo_root/docs" ] || exit 0
[ -f "$SCAN" ] || exit 0

# Тронуты ли docs/ в диапазоне пуша?
upstream="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -n "$upstream" ]; then
    base="$(git -C "$repo_root" merge-base HEAD "$upstream" 2>/dev/null || true)"
else
    base="$(git -C "$repo_root" merge-base HEAD origin/main 2>/dev/null || true)"
fi
if [ -n "$base" ]; then
    git -C "$repo_root" -c core.quotepath=false diff --name-only "$base"..HEAD 2>/dev/null | grep -q '^docs/' || exit 0
fi

# Скан каноничного корпуса (00-10 разделы), исключая KIT.md/_навигация/superpowers
broken="$(cd "$repo_root/docs" && python3 "$SCAN" . 2>/dev/null | grep -E '^(0[0-9]|10)-' || true)"
[ -z "$broken" ] || {
    cat >&2 <<EOF

🚫  Docs broken-link check FAILED (KIT-016, S60)

Битые [[навигационные ссылки]] в каноничном корпусе docs/ (разделы 00-10):
$(printf '%s\n' "$broken" | sed 's/^/    /' | head -25)

Required action:
  Почини через скилл docs-update (doc-linker) ИЛИ вручную: переименуй [[old]] на
  существующий слаг, либо сними [[ ]] если целевой страницы нет.
  Проверка: cd docs && python3 ~/.claude/hooks/lib/docs_broken_link_scan.py .

(Defined by: ~/.claude/hooks/docs-broken-link-check.sh, S60 KIT-016)
EOF
    exit 2
}
exit 0
