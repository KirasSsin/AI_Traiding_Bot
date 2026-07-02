#!/usr/bin/env bash
# review-gate.sh — KIT-003 (S59): механический барьер Фазы 6 (ревью денежного ядра).
#
# Claude Code PreToolUse hook (Bash). Событие: `gh pr merge` ИЛИ локальный
# `git merge` sprint-ветки. Если diff затрагивает денежные пути
# (src/signalgen|execution|risk|backtest, override) — требуем артефакты Фазы 6:
#   1) строка "| 6 Review | done |" в SPRINT_STATE.md
#   2) файл llm-wiki/wiki/project/reviews/review-sNN.md со строкой "Blockers: 0"
# Иначе exit 2. Обоснование: S55 — доменные ревьюеры поймали 2 BLOCKER
# (unbounded-loss OCO), которые прошли ручное ревью; фаза не имела гейта.
#
# Policy: fail OPEN на инфра-ошибках; fail CLOSED только при доказанном пропуске.
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

# Skip self-test — УЗКИЙ матч только на явный запуск скрипта (security M-3:
# голая подстрока позволяла дописать "# per review-gate.sh" к merge и скипнуться)
case "$command_str" in
    *"hooks/review-gate.sh"*|*"bash "*"review-gate.sh"*) exit 0 ;;
esac

# Событие: gh pr merge ИЛИ git merge (любая форма ссылки — S59 review fix HIGH-1:
# merge по sha/переименованной ветке раньше тихо обходил гейт)
is_merge=0
case "$command_str" in
    *"gh pr merge"*|*"git merge"*) is_merge=1 ;;
    *) exit 0 ;;
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
sprint_state="$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md"
[ -f "$sprint_state" ] || exit 0

# Ссылка для диффа. Порядок: (1) sprint-ветка в команде; (2) любой токен команды,
# резолвящийся как git-commit (sha / переименованная ветка / тег); (3) текущая
# ветка (gh pr merge). Не определили → ГРОМКИЙ warn + fail-open (не силент).
merge_ref="$(printf '%s' "$command_str" | grep -oE 'feature/sprint-[0-9]+[a-z]?-[A-Za-z0-9._-]+' | head -1 || true)"
if [ -z "$merge_ref" ]; then
    case "$command_str" in
        *"git merge"*)
            for tok in $command_str; do
                case "$tok" in
                    git|merge|-*|\"*|\'*) continue ;;
                esac
                if git -C "$repo_root" rev-parse --verify --quiet "${tok}^{commit}" >/dev/null 2>&1; then
                    merge_ref="$tok"
                    break
                fi
            done
            ;;
        *)
            merge_ref="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
            ;;
    esac
fi
if [ -z "$merge_ref" ]; then
    echo "⚠️  review-gate: не смог определить merge-ref из команды — гейт ПРОПУЩЕН (fail-open, но громко). Проверь Фазу 6 вручную." >&2
    exit 0
fi

# security M-2: `gh pr merge` с main → diff main...main пуст → пустой обход.
# При активном спринте merge выполняется со sprint-ветки.
if [ "$merge_ref" = "main" ] || [ "$merge_ref" = "master" ]; then
    state_phase="$(grep -m1 '^phase:' "$sprint_state" 2>/dev/null \
        | sed 's/^phase:[[:space:]]*//;s/[[:space:]]*#.*$//;s/[[:space:]]*$//' || true)"
    case "$state_phase" in
        [2-8]|[2-8]-*)
            echo "🚫  review-gate: merge с '$merge_ref' при активном спринте (phase=$state_phase). Запусти merge со sprint-ветки (или укажи её/sha в команде)." >&2
            exit 2 ;;
        *) exit 0 ;;
    esac
fi

# Денежные пути в диффе main...ref (fail-OPEN если diff не считается).
# NB: база "main" захардкожена под этот репозиторий; в repo с "master" хук
# тихо неприменим (review issue #4 — задокументировано).
money_files="$(git -C "$repo_root" diff --name-only "main...$merge_ref" 2>/dev/null \
    | grep -E '^src/(signalgen|execution|risk|backtest)/|override' || true)"
[ -n "$money_files" ] || exit 0  # денежное ядро не тронуто — гейт не нужен

# Номер спринта: из ветки, иначе из SPRINT_STATE
sprint_num=""
if [[ "$merge_ref" =~ sprint-([0-9]+[a-z]?)- ]]; then
    sprint_num="${BASH_REMATCH[1]}"
else
    sprint_num="$(grep -m1 '^sprint:' "$sprint_state" | grep -oE '[0-9]+[a-z]?' | head -1 || true)"
fi

# security M-4: строка Фазы 6 засчитывается только если SPRINT_STATE ведёт ЭТОТ спринт
state_sprint="$(grep -m1 '^sprint:' "$sprint_state" 2>/dev/null | grep -oE '[0-9]+[a-z]?' | head -1 || true)"
if [ -n "$sprint_num" ] && [ -n "$state_sprint" ] && [ "$state_sprint" != "$sprint_num" ]; then
    review_line=""  # таблица от другого спринта — не считается
else
review_line="$(grep -E '^\| ?6[ .]?[Rr]eview ?\|' "$sprint_state" 2>/dev/null | head -1 || true)"
fi
review_status="$(echo "$review_line" | awk -F'|' '{gsub(/^ +| +$/, "", $3); print $3}' || true)"
review_file="$repo_root/llm-wiki/wiki/project/reviews/review-s${sprint_num}.md"

ok=1
case "$review_status" in
    "done"|"skipped"*) ;;
    *) ok=0 ;;
esac
if [ ! -f "$review_file" ] || ! grep -qiE '^ *\**Blockers\**[: ] *\**0\**' "$review_file"; then
    ok=0
fi

if [ "$ok" -eq 0 ]; then
    cat >&2 <<EOF

🚫  Review gate FAILED (KIT-003, S59) — денежное ядро без артефактов Фазы 6

Merge ref: $merge_ref (sprint $sprint_num)
Затронуты денежные пути:
$(echo "$money_files" | sed 's/^/    /' | head -10)

Требуется ОБА артефакта:
  1. SPRINT_STATE.md: строка "| 6 Review | done | ... |"   (сейчас: "${review_status:-нет строки}")
  2. $review_file
     со строкой "Blockers: 0" (список ревьюеров + вердикты)

Обоснование: в S55 доменные ревьюеры поймали 2 BLOCKER (unbounded-loss OCO,
testnet/mainnet рассинхрон), прошедшие ручное ревью. Фаза 6 обязательна.

(Defined by: ~/.claude/hooks/review-gate.sh, S59 KIT-003)
EOF
    exit 2
fi

printf '✓ Review gate OK (sprint %s, review-s%s.md Blockers: 0)\n' "$sprint_num" "$sprint_num" >&2
exit 0
