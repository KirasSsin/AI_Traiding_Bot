#!/usr/bin/env bash
# review-gate.sh — KIT-003 (S59): механический барьер Фазы 6 (ревью денежного ядра).
#
# Claude Code PreToolUse hook (Bash). Событие: `gh pr merge` ИЛИ локальный
# `git merge` sprint-ветки. Если diff затрагивает денежные пути
# (src/signalgen|execution|risk|backtest, override.py) — требуем артефакты Фазы 6.
# NB: override матчится только как */override.py (S60: docs-страница про override
# давала ложное срабатывание — money-path обязан быть в src/):
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

# round-5 (bypass-hunt HIGH): НЕТ content-based self-skip. Любой self-skip по
# подстроке имени скрипта позволял `gh pr merge <деньги> # bash review-gate.sh`
# (или `&& bash ./review-gate.sh`) обойти гейт с НУЛЕВОЙ подделкой артефактов —
# self-skip срабатывал раньше детекта операции. Теперь ДЕТЕКТ ОПЕРАЦИИ РЕШАЕТ:
# голый запуск хука не содержит `gh pr merge`/`git merge ` → падает в `*) exit 0`;
# реальный merge гейтится всегда, независимо от упоминания имени хука в комменте.
# Тестировать гейт — прямым вызовом (hook-test), payload через stdin, НЕ inline.

# Событие: gh pr merge ИЛИ git merge (любая форма ссылки — S59 review fix HIGH-1:
# merge по sha/переименованной ветке раньше тихо обходил гейт)
# round-6 (bypass-hunt): нормализуем пробелы/табы + срезаем git-глобалки `-c/-C X`
# перед детектом. `gh   pr   merge` (пробелы), `git -c http.x=y merge` (глобалка
# между git и субкомандой) иначе минули бы подстроку. `gh api .../pulls/N/merge`
# (REST-эндпоинт мерджа) детектим отдельно.
# ОСТАТОК (backlog: kit-op-detect-hardening security-спринт per auditor root-fix
# «classify on resolved argv + key off branch/diff»): inline-alias `git -c
# alias.z=merge z` (z = алиас, не резолвится без git config) и произвольный
# `gh api` через переменную — подстрокой не ловятся. Денежный контур при этом
# защищён diff-детектом review-gate (primary money-path check ниже).
command_norm="$(printf '%s' "$command_str" | tr -s ' \t' ' ')"
command_argv="$(printf '%s' "$command_norm" | sed -E 's/git( -[cC] [^ ]+)+ /git /g')"
is_merge=0
case "$command_argv" in
    *"git merge-base"*|*"git merge-tree"*|*"git merge-file"*) exit 0 ;;  # plumbing ≠ merge
    *"gh pr merge"*|*"git merge "*|*"git merge") is_merge=1 ;;
esac
case "$command_norm" in
    *"gh api"*"pulls/"*"/merge"*|*"gh api"*"/merge"*"pulls/"*) is_merge=1 ;;  # REST-мердж
esac
[ "$is_merge" = "1" ] || exit 0

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || exit 0
sprint_state="$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md"
[ -f "$sprint_state" ] || exit 0

# Ссылка для диффа. Порядок: (1) sprint-ветка в команде; (2) любой токен команды,
# резолвящийся как git-commit (sha / переименованная ветка / тег); (3) текущая
# ветка (gh pr merge). Не определили → ГРОМКИЙ warn + fail-open (не силент).
merge_ref="$(printf '%s' "$command_str" | grep -oE 'feature/sprint-[0-9]+[a-z]?-[A-Za-z0-9._-]+' | head -1 || true)"
# security S62 HIGH #1: grep срезает `origin/` — `git merge origin/feature/sprint-NN`
# давал НЕрезолвящийся локальный ref → diff main...ref падал → money_files пусто →
# силент exit 0, tamper не запускался. Валидируем: не резолвится → пробуем origin/,
# иначе СБРАСЫВАЕМ merge_ref (пусть сработает sha-fallback / current-branch ниже).
if [ -n "$merge_ref" ]; then
    if git -C "$repo_root" rev-parse --verify --quiet "${merge_ref}^{commit}" >/dev/null 2>&1; then
        :
    elif git -C "$repo_root" rev-parse --verify --quiet "origin/${merge_ref}^{commit}" >/dev/null 2>&1; then
        merge_ref="origin/${merge_ref}"
    else
        merge_ref=""
    fi
fi
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
        ""|between-sprints|autoresearch|1|1-*|9|9-*)
            exit 0 ;;  # не активная gated-фаза — merge с main допустим
        *)
            # round-4 (bypass-hunt): fail-CLOSED на неканоничной phase — `4<NBSP>`/
            # zero-width/мусор мимо `[2-8]` тихо снимал M-2 (merge-from-main guard).
            echo "🚫  review-gate: неканоничная SPRINT_STATE.phase='$state_phase' при merge с '$merge_ref' → блок (возможна подмена). Приведи phase к канону." >&2
            exit 2 ;;
    esac
fi

# Денежные пути в диффе main...ref (fail-OPEN если diff не считается).
# NB: база "main" захардкожена под этот репозиторий; в repo с "master" хук
# тихо неприменим (review issue #4 — задокументировано).
money_files="$(git -C "$repo_root" diff --name-only "main...$merge_ref" 2>/dev/null \
    | grep -E '^src/(signalgen|execution|risk|backtest)/|(^|/)override\.py$' || true)"
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
tamper=""
case "$review_status" in
    "done"|"skipped"*) ;;
    *) ok=0 ;;
esac
if [ ! -f "$review_file" ] || ! grep -qiE '^ *\**Blockers\**[: ] *\**0\**' "$review_file"; then
    ok=0
fi
# T2 (S62 KIT-TAMPER, закрывает остаток S59/S61): review-артефакт должен быть
# ЗАКОММИЧЕН в диапазоне мерджа — не просто лежать в рабочем дереве (same-session
# forgery: сессия пишет review-sNN.md без запуска ревьюеров и без коммита-в-range).
# Плюс схема: ≥1 reviewer-строка (architecture/security/domain).
review_rel="llm-wiki/wiki/project/reviews/review-s${sprint_num}.md"
if [ -f "$review_file" ]; then
    if [ -z "$(git -C "$repo_root" log --oneline "main..$merge_ref" -- "$review_rel" 2>/dev/null | head -1)" ]; then
        ok=0; tamper="review-артефакт не закоммичен в диапазоне main..$merge_ref (same-session подделка?)"
    fi
    if ! grep -qiE 'reviewer|architecture|security|Reviewers|ревьюер' "$review_file"; then
        ok=0; tamper="${tamper}${tamper:+; }review-артефакт без строки ревьюера (схема не валидна)"
    fi
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
     со строкой "Blockers: 0" + строкой ревьюера, ЗАКОММИЧЕННЫЙ в диапазоне мерджа
${tamper:+     ⚠️  tamper-evidence: $tamper}

Обоснование: в S55 доменные ревьюеры поймали 2 BLOCKER (unbounded-loss OCO,
testnet/mainnet рассинхрон), прошедшие ручное ревью. Фаза 6 обязательна.

(Defined by: ~/.claude/hooks/review-gate.sh, S59 KIT-003)
EOF
    exit 2
fi

printf '✓ Review gate OK (sprint %s, review-s%s.md Blockers: 0)\n' "$sprint_num" "$sprint_num" >&2
exit 0
