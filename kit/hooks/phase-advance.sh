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

# Only act on `gh pr merge` (not gh pr create / view / status)
# round-6: нормализуем пробелы/табы + ловим REST-эндпоинт `gh api .../pulls/N/merge`.
# ОСТАТОК (backlog kit-op-detect-hardening): произвольный gh api через переменную.
command_norm="$(printf '%s' "$command_str" | tr -s ' \t' ' ')"
case "$command_norm" in
    *"gh pr merge"*) ;;
    *"gh api"*"pulls/"*"/merge"*|*"gh api"*"/merge"*"pulls/"*) ;;
    *) exit 0 ;;
esac

# --- locate repo + SPRINT_STATE ---------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

sprint_state_path="$repo_root/llm-wiki/wiki/project/SPRINT_STATE.md"
if [ ! -f "$sprint_state_path" ]; then
    exit 0  # No SPRINT_STATE = not a kit-managed repo
fi

# --- check current branch matches sprint pattern ----------------------------
current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
if [ -z "$current_branch" ]; then
    exit 0
fi

if [[ ! "$current_branch" =~ ^feature/sprint-([0-9]+[a-z]?)-.+$ ]]; then
    # KIT-002 (S59): активный спринт (phase 2..8) на не-sprint ветке → merge заблокирован.
    state_phase="$(grep -m1 '^phase:' "$sprint_state_path" 2>/dev/null \
        | sed 's/^phase:[[:space:]]*//;s/[[:space:]]*#.*$//;s/[[:space:]]*$//' || true)"
    case "$state_phase" in
        [2-8]|[2-8]-*)
            cat >&2 <<EOF

🚫  Phase advance check FAILED (KIT-002 branch-bypass guard, S59)

Branch: $current_branch — НЕ sprint-ветка, но SPRINT_STATE.phase = "$state_phase".
Merge при активном спринте разрешён только с feature/sprint-NN-* веток.
Действия: переименуй ветку ИЛИ закрой спринт (phase: between-sprints).

(Defined by: ~/.claude/hooks/phase-advance.sh, S59 KIT-002)
EOF
            exit 2 ;;
        ""|between-sprints|autoresearch|1|1-*|9|9-*)
            exit 0 ;;  # не активная gated-фаза (или нет файла) — пропуск
        *)
            # round-4 (bypass-hunt): fail-CLOSED на неканоничной phase — `4<NBSP>`/
            # zero-width/мусор мимо `[2-8]` тихо открывал merge (обход KIT-002).
            echo "🚫  phase-advance: неканоничная SPRINT_STATE.phase='$state_phase' на не-sprint ветке → блок merge (возможна подмена). Приведи phase к канону." >&2
            exit 2 ;;
    esac
fi

sprint_num="${BASH_REMATCH[1]}"

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

# Extract status (2nd column)
status="$(echo "$phase_5_line" | awk -F'|' '{gsub(/^ +| +$/, "", $3); print $3}' || true)"

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
