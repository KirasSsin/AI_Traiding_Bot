#!/usr/bin/env bash
# sprint-flow-check.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when a `git push` is about to run on a feature/sprint-NN-* branch,
# require that a plan file exists in llm-wiki/wiki/project/plans/ matching
# pattern <YYYY-MM-DD>-sprint-NN-<slug>.md. Otherwise block the push.
#
# Defined by: llm-wiki/wiki/project/architecture/sprint-flow-ru.md PHASE 3
# Established by: ADR 0041 (S28 process enforcement) — mechanical PHASE 3 enforcement.
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open
#
# Policy: fail OPEN on unexpected errors (no python3, not in repo, no upstream).
# Fail CLOSED only when conclusively detect drift (sprint branch без plan file).

set -u

# --- read hook payload -------------------------------------------------------
payload="$(cat || true)"
if [ -z "$payload" ]; then
    exit 0
fi

command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

# round-5 (bypass-hunt MEDIUM): НЕТ content-based self-skip. Голая подстрока
# `*sprint-flow-check.sh*` позволяла `git push ... # sprint-flow-check.sh` обойти
# plan-file гейт с нулевой подделкой. Детект операции решает: голый запуск хука
# не содержит `git push` → `*) exit 0`; реальный push гейтится всегда.

# Only act on git push
# S69 T9 (KIT-OD-1): push-детект по резолвнутому argv (lib/op_detect.py) — заменяет
# tr+sed+substring. substring false-fire'ил на литерале 'git push' в тексте команды
# (grep/echo/commit-msg ложно гейтились); op_detect токенизирует с учётом кавычек,
# ловит `git -c x=y push`/env-prefix и игнорит литерал в кавычках. Self-skip уже снят
# в round-5. PARSE_ERROR → substring fallback.
op_lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/op_detect.py"
case "$(printf '%s' "$command_str" | python3 "$op_lib" push 2>/dev/null || echo PARSE_ERROR)" in
    GATE) ;;                                                        # git push — гейтим ниже
    allow|skip) exit 0 ;;                                            # не push
    *) case "$command_str" in *"git push"*|*"git  push"*) ;; *) exit 0 ;; esac ;;  # fallback
esac

# --- locate repo -------------------------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

# Opt-in: only repos that contain wiki/project/plans/
plans_dir_rel="llm-wiki/wiki/project/plans"
if [ ! -d "$repo_root/$plans_dir_rel" ]; then
    exit 0
fi

# --- check current branch matches sprint pattern ----------------------------
current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
if [ -z "$current_branch" ]; then
    exit 0
fi

# Match: feature/sprint-NN-<slug> OR feature/sprint-NNa-<slug> (e.g. sprint-08c)
if [[ ! "$current_branch" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]]; then
    # KIT-002 (S59): источник истины «идёт ли спринт» — SPRINT_STATE.phase, не имя ветки.
    # Активная фаза 2..8 на не-sprint ветке = обход гейтов (прецедент S56 на chore/*) → БЛОК.
    state_phase="$(grep -m1 '^phase:' "$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md" 2>/dev/null \
        | sed 's/^phase:[[:space:]]*//;s/[[:space:]]*#.*$//;s/[[:space:]]*$//' || true)"
    case "$state_phase" in
        [2-8]|[2-8]-*)
            cat >&2 <<EOF

🚫  Sprint flow check FAILED (KIT-002 branch-bypass guard, S59)

Branch: $current_branch — НЕ sprint-ветка,
но SPRINT_STATE.phase = "$state_phase" → спринт активен.

Гейты кита работают только на ветках feature/sprint-NN-<slug>.
Прецедент: S56 целиком прошёл на chore/* мимо всех гейтов.

Required action — ОДНО из:
  1. Перенеси работу: git branch -m $current_branch feature/sprint-NN-<slug>
  2. Если спринт реально закрыт — обнови SPRINT_STATE.md: phase: between-sprints
  3. Если это autoresearch — phase: autoresearch

(Defined by: ~/.claude/hooks/sprint-flow-check.sh, S59 KIT-002)
EOF
            exit 2 ;;
        ""|between-sprints|autoresearch|1|1-*|9|9-*)
            exit 0 ;;  # не активная gated-фаза (или нет файла) — пропуск
        *)
            # round-4 (bypass-hunt): НЕ открывать гейт на неканоничной phase.
            # `4<NBSP>`/zero-width/мусор мимо `[2-8]` тихо падал в exit 0 (fail-open),
            # обходя KIT-002. Гейт САМ валидирует phase (repairer-хук — параллельный
            # side-channel, не барьер; cold-net его не спасает). Fail-CLOSED.
            echo "🚫  sprint-flow-check: неканоничная SPRINT_STATE.phase='$state_phase' на не-sprint ветке → блок (возможна подмена unicode/zero-width). Приведи phase к канону." >&2
            exit 2 ;;
    esac
fi

sprint_num="${BASH_REMATCH[1]}"

# --- check plan file exists --------------------------------------------------
# Pattern: <YYYY-MM-DD>-sprint-NN-<slug>.md
plan_files="$(ls "$repo_root/$plans_dir_rel" 2>/dev/null \
    | grep -E "^[0-9]{4}-[0-9]{2}-[0-9]{2}-sprint-${sprint_num}-.+\.md$" \
    || true)"

if [ -z "$plan_files" ]; then
    cat >&2 <<EOF

🚫  Sprint flow check FAILED

Branch: $current_branch (sprint $sprint_num)
Required: plan file matching pattern в llm-wiki/wiki/project/plans/
  <YYYY-MM-DD>-sprint-${sprint_num}-<slug>.md

Found: NONE

Required action:
  1. Invoke 'superpowers:writing-plans' skill to produce plan file
  2. Place в llm-wiki/wiki/project/plans/
  3. Commit
  4. Retry push

Reason: PHASE 3 (Plan writing) — обязательная фаза kit'а.
12 sprints (S16-S27) drifted без plan files. Per ADR 0041 mechanical
enforcement of PHASE 3.

Полный процесс: llm-wiki/wiki/project/architecture/sprint-flow-ru.md
Tooling catalog: llm-wiki/wiki/project/architecture/tooling-inventory-ru.md

(Defined by: ~/.claude/hooks/sprint-flow-check.sh
 Policy:     wiki/project/decisions/0041-sprint-28-process-enforcement.md)
EOF
    exit 2
fi

printf '✓ Sprint flow check OK (plan: %s)\n' "$plan_files" >&2
exit 0
