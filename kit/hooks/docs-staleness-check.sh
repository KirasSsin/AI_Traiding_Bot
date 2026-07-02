#!/usr/bin/env bash
# docs-staleness-check.sh — KIT-004 (S60): docs/ не отстаёт от src/ и kit/.
#
# Claude Code PreToolUse hook (Bash). Событие: `git push`. Если в диапазоне пуша
# изменён источник (src/** или kit/**), у которого во frontmatter docs-страницы
# (source_files:) есть привязка, а сама страница в ЭТОМ ЖЕ пуше не тронута —
# exit 2 со списком «источник → устаревшая страница».
#
# Escape-люк: [docs-ignore] в сообщении любого коммита диапазона — пропуск
# (тривиальные правки: форматирование, комментарии, тайп-хинты).
#
# Обратный индекс — docs/manifest.json (генерируется kit/hooks/lib/docs_manifest.py).
# Клон механики adr-agent-sync-check (доказана в бою). Policy: fail-OPEN.
set -u

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
    *"docs-staleness-check"*) exit 0 ;;
esac
case "$command_str" in
    *"git push"*|*"git  push"*) ;;
    *) exit 0 ;;
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
manifest="$repo_root/docs/manifest.json"
# review HIGH-2: manifest = кэш; строим СВЕЖИЙ индекс из frontmatter ПЕРЕД
# доверием (иначе изменённый source_files не виден гейту — "hope, not gate").
# Пишем во временный файл, tracked docs/manifest.json НЕ трогаем (без грязи в дереве).
gen="$repo_root/kit/hooks/lib/docs_manifest.py"
if [ -f "$gen" ] && [ -d "$repo_root/docs" ]; then
    fresh_manifest="$(mktemp)"
    if MANIFEST_OUT="$fresh_manifest" python3 - "$gen" "$repo_root/docs" <<'PYEOF' 2>/dev/null
import json, os, runpy, sys
mod = runpy.run_path(sys.argv[1])
root = __import__("pathlib").Path(sys.argv[2])
json.dump(mod["build"](root), open(os.environ["MANIFEST_OUT"], "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
    then
        [ -s "$fresh_manifest" ] && manifest="$fresh_manifest"
    fi
    trap 'rm -f "$fresh_manifest"' EXIT
fi
[ -f "$manifest" ] || exit 0  # нет манифеста — хук неприменим (fail-OPEN)

upstream="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -n "$upstream" ]; then
    base="$(git -C "$repo_root" merge-base HEAD "$upstream" 2>/dev/null || true)"
else
    base="$(git -C "$repo_root" merge-base HEAD origin/main 2>/dev/null || true)"
fi
[ -n "$base" ] || exit 0

changed="$(git -C "$repo_root" -c core.quotepath=false diff --name-only "$base"..HEAD 2>/dev/null || true)"
[ -n "$changed" ] || exit 0

# review HIGH-1: [docs-ignore] действует ПОФАЙЛОВО, а не на весь диапазон.
# Для каждого источника берём коммит, где он последний раз менялся в диапазоне;
# если сообщение ТОГО коммита содержит [docs-ignore] — источник освобождён.
# Список источников с [docs-ignore] → в python как IGNORED (env).
ignored=""
for src in $changed; do
    csha="$(git -C "$repo_root" log -1 --format='%H' "$base"..HEAD -- "$src" 2>/dev/null || true)"
    [ -n "$csha" ] || continue
    if git -C "$repo_root" log -1 --format='%B' "$csha" 2>/dev/null | grep -q '\[docs-ignore\]'; then
        ignored="$ignored$src"$'\n'
    fi
done

# Вся тяжёлая логика — в python (правило P1-BASHN)
report="$(CHANGED="$changed" IGNORED="$ignored" python3 - "$manifest" <<'PYEOF'
import json, os, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
changed = set(os.environ.get("CHANGED", "").split("\n"))
changed.discard("")
ignored = set(os.environ.get("IGNORED", "").split("\n"))
ignored.discard("")
stale = []
for src, pages in manifest.items():
    if src not in changed or src in ignored:
        continue
    for page in pages:
        docs_page = "docs/" + page
        if docs_page not in changed:
            stale.append(f"{src} -> {docs_page}")
for line in stale:
    print(line)
PYEOF
)"

[ -n "$report" ] || exit 0

cat >&2 <<EOF

⚠️  Docs staleness WARN (KIT-004, S60; docs/=WARN per оператор S64)

Источник изменён, а привязанная страница docs/ — нет (устареет):
$(printf '%s\n' "$report" | sed 's/^/    /' | head -20)

Пуш НЕ заблокирован — реши осознанно. Рекомендация — ОДНО из:
  1. Обнови страницы через скилл docs-update (doc-writer → depth → linker),
     закоммить в тот же пуш.
  2. Тривиальная правка (формат/коммент/type hint, docs не нужен) —
     добавь [docs-ignore] в сообщение коммита.

Привязка «источник → страница» — frontmatter source_files: каждой docs-страницы
(кэш docs/manifest.json). Правило Doc-first + Docs-Sync Gate (CLAUDE.md, S64).

(Defined by: ~/.claude/hooks/docs-staleness-check.sh, S60 KIT-004 / S64 WARN)
EOF
exit 0
