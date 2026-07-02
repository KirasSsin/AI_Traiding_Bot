#!/usr/bin/env bash
# state-backup.sh — S61 Variant B (KIT-008): авто-бэкап SPRINT_STATE перед коммитом.
# PreToolUse Bash: `git commit` со staged SPRINT_STATE.md → cp в
# state/.backup/SPRINT_STATE.<ts>.md (ротация последних 20). fail-OPEN.
set -u

payload="$(cat || true)"
[ -n "$payload" ] || exit 0
cmd=$(printf '%s' "$payload" | python3 -c '
import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")' 2>/dev/null || true)

# S69 T3 (KIT-008 git-нормализация): детект `git commit` по резолвнутому argv
# (lib/op_detect.py) — substring '*git commit*' пропускал `git -c x=y commit` и
# env-prefix, из-за чего SPRINT_STATE молча не бэкапился. Self-skip по имени файла
# УБРАН (S69 T8 zero-forgery): op_detect не примет голый `bash state-backup.sh` за
# commit, зато `git commit -m "…state-backup…"` теперь бэкапится (self-skip глотал).
op_lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/op_detect.py"
case "$(printf '%s' "$cmd" | python3 "$op_lib" commit 2>/dev/null || echo PARSE_ERROR)" in
    GATE) ;;                                                  # git commit — бэкапим ниже
    allow|skip) exit 0 ;;                                     # не commit
    *) case "$cmd" in *"git commit"*) ;; *) exit 0 ;; esac ;; # PARSE_ERROR → substring fallback
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
state="$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md"
[ -f "$state" ] || exit 0

# SPRINT_STATE в staged?
git -C "$repo_root" diff --cached --name-only 2>/dev/null | grep -q 'SPRINT_STATE\.md$' || exit 0

backup_dir="$repo_root/llm-wiki/wiki/project/state/.backup"
mkdir -p "$backup_dir"
# MEDIUM #3 (security-auditor S61): +PID к секундному ts — interactive-сессия и
# auto-resume-опросник могут коммитить в одну секунду; PID разводит имена, чтобы
# одно поколение бэкапа не затёрло другое. (BSD date не умеет %N на macOS.)
ts="$(date +%Y%m%d-%H%M%S)-$$"
cp "$state" "$backup_dir/SPRINT_STATE.$ts.md" 2>/dev/null || true

# Ротация: оставить последние 20
ls -1t "$backup_dir"/SPRINT_STATE.*.md 2>/dev/null | tail -n +21 | while read -r old; do
    rm -f "$old"
done
exit 0
