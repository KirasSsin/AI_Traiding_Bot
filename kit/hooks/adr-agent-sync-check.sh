#!/usr/bin/env bash
# adr-agent-sync-check.sh
#
# Claude Code PreToolUse hook for Bash.
# Purpose: when a `git push` is about to run and the commits being pushed
# include changes to wiki/project/decisions/NNNN-*.md (an ADR), require that
# at least one prompt in ~/.claude/agents/*.md has been modified at or after
# the latest ADR commit time. Otherwise block the push.
#
# Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md
# Established by: ADR 0017 (review-agent harness).
#
# Contract (Claude Code hook protocol):
#   stdin  — JSON: { "tool_input": { "command": "..." }, ... }
#   exit 0 — allow the tool call
#   exit 2 — block the tool call and show stderr to the user
#   any other non-zero — fail open (Claude Code proceeds with tool call)
#
# Policy: fail OPEN on unexpected errors (missing python3, git not a repo,
# no upstream). We only fail CLOSED when we conclusively detect drift.

set -u

AGENTS_DIR="$HOME/.claude/agents"

# --- read hook payload -------------------------------------------------------
payload="$(cat || true)"
if [ -z "$payload" ]; then
    exit 0
fi

# Extract the bash command being proposed. Fail open if python3 missing or
# payload malformed.
command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

# Skip if this is a hook self-test invocation (echo/printf JSON piped к hook
# script для testing). Real `git push` commands don't reference hook script
# paths. Без этого guard'а каждое test invocation ($ echo '...git push...' |
# bash hook.sh) ложно triggers hook через PreToolUse Bash matcher.
case "$command_str" in
    *"adr-agent-sync-check.sh"*|*"adr-index-sync-check.sh"*) exit 0 ;;
    *"hooks/"*"sync-check"*) exit 0 ;;
esac

# Only act on git push. Allow any other command through.
case "$command_str" in
    *"git push"*|*"git  push"*) ;;
    *) exit 0 ;;
esac

# --- locate repo + range -----------------------------------------------------
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
    exit 0
fi

# This hook is opt-in: only repos that contain wiki/project/decisions/ are
# covered. Any other repo is unaffected.
adr_dir_rel="llm-wiki/wiki/project/decisions"
if [ ! -d "$repo_root/$adr_dir_rel" ]; then
    exit 0
fi

# Determine commit range. Prefer tracked upstream, fallback to origin/main.
upstream="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -n "$upstream" ]; then
    base="$(git -C "$repo_root" merge-base HEAD "$upstream" 2>/dev/null || true)"
else
    base="$(git -C "$repo_root" merge-base HEAD origin/main 2>/dev/null || true)"
fi

if [ -z "$base" ]; then
    exit 0
fi

# Was any ADR touched in the range? `git log` respects path filtering.
adr_changed="$(git -C "$repo_root" log "$base"..HEAD --name-only --pretty=format: -- "$adr_dir_rel" 2>/dev/null | sed '/^$/d' | sort -u || true)"

if [ -z "$adr_changed" ]; then
    exit 0
fi

# KIT-009 (S59): содержательная проверка вместо mtime. `touch` больше НЕ обходит:
# номер каждого изменённого ADR (NNNN из имени файла) обязан встречаться в теле
# хотя бы одного агент-промпта (осознанное подтверждение «агент знает про ADR»).
# Обоснование: A2-анализ — 58 из 75 исторических блоков этого хука были
# touch-ритуалом без реального обновления знаний агентов (чистый шум).
if [ ! -d "$AGENTS_DIR" ]; then
    cat >&2 <<EOF

🚫  ADR ↔ Agent prompt sync check FAILED

ADR files changed but $AGENTS_DIR does not exist.
$(printf '%s\n' "$adr_changed" | sed 's/^/    - /')

(Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md)
EOF
    exit 2
fi

missing=""
for adr_path in $adr_changed; do
    # Пропуск ADR, отсутствующих в HEAD (add-then-delete в одном диапазоне;
    # review issue #5 — diff base..HEAD такой файл не показывает вовсе)
    if ! git -C "$repo_root" cat-file -e "HEAD:$adr_path" 2>/dev/null; then
        continue
    fi
    adr_base="$(basename "$adr_path")"
    adr_num="$(printf '%s' "$adr_base" | grep -oE '^[0-9]{4}' || true)"
    [ -n "$adr_num" ] || continue
    # Анкерованный матч "ADR 0071"/"ADR-0071"/"ADR0071" (review issue #2:
    # голое 4-значное число ловит случайные совпадения — 108 цифровых серий
    # уже живут в телах агентов; нужен осознанный маркер)
    if ! grep -rlqE "ADR[[:space:]-]*${adr_num}" "$AGENTS_DIR"/*.md 2>/dev/null; then
        missing="$missing $adr_base"
    fi
done

if [ -n "$missing" ]; then
    cat >&2 <<EOF

🚫  ADR ↔ Agent prompt sync check FAILED (KIT-009 content-check, S59)

ADR в пуше, чей номер НЕ упомянут ни в одном агент-промпте ($AGENTS_DIR):
$(printf '%s\n' $missing | sed 's/^/    - /')

Required action:
  Впиши в релевантного ревьюера (напр. trading-logic-reviewer.md) строку
  в форме "ADR NNNN" (именно с префиксом ADR), например:
      "ADR NNNN: <одна строка сути решения>"
  Голое число без префикса ADR не засчитывается (анти-совпадение).
  Просто touch файла НЕ проходит (mtime-обход закрыт в S59).
  Не знаешь, какой агент релевантен? Правило: деньги→security-auditor,
  торговая логика→trading-logic-reviewer, математика→quant-stats-reviewer,
  данные→data-integrity-reviewer, архитектура→architecture-reviewer.

(Defined by: llm-wiki/wiki/project/components/adr-agent-sync-hook.md
 Policy:     ADR 0017 + S59 KIT-009)
EOF
    exit 2
fi

exit 0
