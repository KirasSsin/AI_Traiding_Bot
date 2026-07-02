#!/usr/bin/env bash
# phase-advance.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when `gh pr merge` is about to run on a feature/sprint-NN-* branch,
# require that SPRINT_STATE.md Phase 5 (Verify) status = "done". Block если
# pending — prevents merging unverified sprint per ADR 0043 (S30 process
# enforcement tier 2).
#
# Defined by: llm-wiki/wiki/project/architecture/sprint-flow-ru.md PHASE 5
# Established by: ADR 0043 (S30 tier-2 enforcement).
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open
#
# Policy: fail OPEN on unexpected errors (no python3, not in repo, no SPRINT_STATE).
# Fail CLOSED only when conclusively detect Phase 5 not done.

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
# `*phase-advance.sh*` позволяла `gh pr merge <ветка> # phase-advance.sh` обойти
# Phase-5-verify гейт с нулевой подделкой. Детект операции решает: голый запуск
# хука не содержит `gh pr merge` → `*) exit 0`; реальный merge гейтится всегда.

# S69 D1-01: детект gh pr merge И локального git merge — наш реальный ship-путь
# `git merge --squash feature/sprint-N` с main Phase-5-verify раньше молча минул
# (phase-advance ловил ТОЛЬКО gh pr merge).
# S69 T9 (KIT-OD-1) root-fix: детект по РЕЗОЛВНУТОМУ argv (lib/op_detect.py, shlex),
# не по подстроке — раньше 'git merge'/'gh pr merge' в тексте команды (сообщение
# коммита, grep-паттерн, echo) ложно срабатывали и блокировали безобидную команду.
# op_detect печатает GATE/skip/allow; непарсимый ввод → PARSE_ERROR → откат на
# консервативный substring-детект (money-path floor не опускаем).
op_lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/op_detect.py"
op_verdict="$(printf '%s' "$command_str" | python3 "$op_lib" merge 2>/dev/null || echo PARSE_ERROR)"
is_merge=0
case "$op_verdict" in
    GATE)  is_merge=1 ;;
    skip)  exit 0 ;;                 # git merge-base/-tree/-file — plumbing, не merge
    allow) exit 0 ;;                 # операции merge нет
    *)  # PARSE_ERROR / нет python3 — откат на substring (S65, консервативно)
        command_norm="$(printf '%s' "$command_str" | tr -s ' \t' ' ')"
        command_argv="$(printf '%s' "$command_norm" | sed -E 's/git( -[cC] [^ ]+)+ /git /g')"
        case "$command_argv" in
            *"git merge-base"*|*"git merge-tree"*|*"git merge-file"*) exit 0 ;;
            *"gh pr merge"*|*"git merge "*|*"git merge") is_merge=1 ;;
        esac
        case "$command_norm" in
            *"gh api"*"pulls/"*"/merge"*|*"gh api"*"/merge"*"pulls/"*) is_merge=1 ;;
        esac
        ;;
esac
[ "$is_merge" = "1" ] || exit 0

# --- locate repo + SPRINT_STATE ---------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

# S69 T7 (LOG9-02 split-brain): worktrees + 2-й клон = несколько ПАРАЛЛЕЛЬНЫХ
# SPRINT_STATE; гейт обязан сверять Phase-5 с КАНОНИЧНЫМ (main checkout), а не с
# локальным worktree-чекаутом (иначе стейл-worktree со своим SPRINT_STATE слепо
# минует/ложно блокирует). git-common-dir → общий .git; его родитель = main root.
# В main repo common-dir=".git" → canon_root==repo_root (0 изменений поведения).
# git branch/merge-ref остаются на repo_root — merge физически идёт там.
canon_root="$repo_root"
common_dir="$(git -C "$repo_root" rev-parse --git-common-dir 2>/dev/null || true)"
if [ -n "$common_dir" ]; then
    case "$common_dir" in /*) ;; *) common_dir="$repo_root/$common_dir" ;; esac
    _cr="$(cd "$(dirname "$common_dir")" 2>/dev/null && pwd -P || true)"
    [ -n "$_cr" ] && canon_root="$_cr"
fi

sprint_state_path="$canon_root/llm-wiki/wiki/project/SPRINT_STATE.md"
if [ ! -f "$sprint_state_path" ]; then
    exit 0  # No SPRINT_STATE = not a kit-managed repo
fi

# --- определить спринт: merge-ref из команды (локальный merge с main) ИЛИ -------
# current_branch (gh pr merge со sprint-ветки). Порядок mirror review-gate.
# S69 D1-01: локальный `git merge --squash feature/sprint-N` идёт С main →
# current_branch=main; спринт берём из МЕРДЖ-ветки в команде.
current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
merge_ref="$(printf '%s' "$command_str" | grep -oE 'feature/sprint-[0-9]+[a-z]?-[A-Za-z0-9._-]+' | head -1 || true)"
sprint_num=""
if [[ "$merge_ref" =~ sprint-([0-9]+[a-z]?)- ]]; then
    sprint_num="${BASH_REMATCH[1]}"
elif [[ "$current_branch" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]]; then
    sprint_num="${BASH_REMATCH[1]}"
fi

# Ни merge-ref, ни current_branch спринт не дали → KIT-002 branch-bypass guard
# (активный спринт мерджится без явной sprint-ссылки / с не-sprint ветки).
if [ -z "$sprint_num" ]; then
    state_phase="$(grep -m1 '^phase:' "$sprint_state_path" 2>/dev/null \
        | sed 's/^phase:[[:space:]]*//;s/[[:space:]]*#.*$//;s/[[:space:]]*$//' || true)"
    case "$state_phase" in
        [2-8]|[2-8]-*)
            cat >&2 <<EOF

🚫  Phase advance check FAILED (KIT-002 branch-bypass guard, S59+S69)

Merge при активном спринте (phase=$state_phase), но спринт НЕ определён ни из
merge-ref команды, ни из ветки '$current_branch'. Укажи feature/sprint-NN-* в
команде merge ИЛИ закрой спринт (phase: between-sprints).

(Defined by: ~/.claude/hooks/phase-advance.sh, S59 KIT-002 + S69 D1-01)
EOF
            exit 2 ;;
        ""|between-sprints|autoresearch|1|1-*|9|9-*)
            exit 0 ;;  # не активная gated-фаза (или нет файла) — пропуск
        *)
            # round-4 (bypass-hunt): fail-CLOSED на неканоничной phase (zero-width/мусор).
            echo "🚫  phase-advance: неканоничная SPRINT_STATE.phase='$state_phase' → блок merge (возможна подмена). Приведи phase к канону." >&2
            exit 2 ;;
    esac
fi

# M-4 sprint-binding (S69 D1-04, mirror review-gate): Phase-5-строка засчитывается
# ТОЛЬКО если SPRINT_STATE ведёт ЭТОТ спринт — иначе стейл-таблица прошлого спринта
# (Phase 5=done от S68) ложно разрешила бы merge S69.
state_sprint="$(grep -m1 '^sprint:' "$sprint_state_path" 2>/dev/null | grep -oE '[0-9]+[a-z]?' | head -1 || true)"
if [ -n "$state_sprint" ] && [ "$state_sprint" != "$sprint_num" ]; then
    cat >&2 <<EOF

🚫  Phase advance check FAILED (M-4 sprint-binding, S69)

Merge спринта $sprint_num, но SPRINT_STATE ведёт спринт $state_sprint — стейл-таблица
прошлого спринта не засчитывается. Обнови SPRINT_STATE к спринту $sprint_num (Phase 5 → done).

(Defined by: ~/.claude/hooks/phase-advance.sh, S69 D1-04)
EOF
    exit 2
fi

# --- parse Phase 5 status from SPRINT_STATE ---------------------------------
# Looking for table row pattern:
#   | 5 Verify | done | ... |
#   | 5 Verify | pending | ... |
#   | 5 Verify | in_progress | ... |
#   | 5 Verify | skipped (...) | ... |
phase_5_line="$(grep -E '^\| ?5[ \.]?[Vv]erify ?\|' "$sprint_state_path" 2>/dev/null | head -1 || true)"

if [ -z "$phase_5_line" ]; then
    cat >&2 <<EOF

🚫  Phase advance check FAILED

Branch: $current_branch (sprint $sprint_num)
SPRINT_STATE: $sprint_state_path
Phase 5 (Verify) row not found в Phase tracking table.

Required: Phase tracking table must include "| 5 Verify | done | ... |" row.

Per ADR 0043 (S30): SPRINT_STATE phase tracking template (S28+) обязателен.

(Defined by: ~/.claude/hooks/phase-advance.sh)
EOF
    exit 2
fi

# Extract status (2nd column). S69 design-hole: markdown-tolerance — `**done**`
# (bold в таблице) должно засчитываться, иначе ложный блок. Срезаем `*`.
status="$(echo "$phase_5_line" | awk -F'|' '{gsub(/^ +| +$/, "", $3); gsub(/\*/, "", $3); print $3}' || true)"

# Allow: done | skipped (...)
case "$status" in
    "done"|"skipped"*) ;;
    *)
        cat >&2 <<EOF

🚫  Phase advance check FAILED

Branch: $current_branch (sprint $sprint_num)
SPRINT_STATE: $sprint_state_path
Phase 5 (Verify) status: "$status"

Если это FALSE-FIRE (литерал 'gh pr merge' в тексте команды, а не реальный merge —
напр. python/echo/grep со строкой) — перепиши команду через Edit/Write/Grep tools
без литерала. Это op-detect substring (S65 known; root fix → KIT-OD-1 backlog).

Required: Phase 5 must be "done" OR "skipped" before merge.
- "done" — pytest + mypy + canonical counts passed
- "skipped (...)" — explicit skip с reason (e.g., docs-only sprint)

Required action:
  1. Run \`superpowers:verification-before-completion\` checklist:
     - pytest tests/ -q --ignore=tests/integration
     - mypy --strict src/
     - canonical counts python check
     - Edge cases / runtime smoke / docs updated
  2. Update SPRINT_STATE.md Phase 5 row → "done"
  3. (Or если skip valid: "skipped (reason)")
  4. Retry merge

Per ADR 0043 (S30): Mechanical enforcement of Phase 5 (Verify).

(Defined by: ~/.claude/hooks/phase-advance.sh
 Policy:     wiki/project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md)
EOF
        exit 2
        ;;
esac

printf '✓ Phase advance check OK (Phase 5 status: %s)\n' "$status" >&2
exit 0
