#!/usr/bin/env bash
# kit-inventory.sh — регенерирует счётчики кита в AUTO-блоках канонов (S57, KIT-006).
# Запуск: из корня репо (Фаза 7 kit-maintenance спринта / sprint-finish).
# Дрейф счётчиков «в доках N, на диске M» исчезает как класс: числа берутся с диска.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SETTINGS="$HOME/.claude/settings.json"

AGENTS=$(ls -1 "$HOME/.claude/agents/"*.md 2>/dev/null | wc -l | tr -d ' ')
SKILLS=$(ls -1d "$REPO_ROOT/.claude/skills/"*/ 2>/dev/null | wc -l | tr -d ' ')
SP=$(ls -1d "$HOME"/.claude/plugins/cache/*/superpowers/*/skills/*/ 2>/dev/null | wc -l | tr -d ' ')
PRE=$(jq '.hooks.PreToolUse[0].hooks | length' "$SETTINGS")
UPS=$(jq '.hooks.UserPromptSubmit[0].hooks | length' "$SETTINGS")
SS=$(jq '.hooks.SessionStart[0].hooks | length' "$SETTINGS")
HOOK_FILES=$(ls -1 "$HOME/.claude/hooks/"*.sh 2>/dev/null | wc -l | tr -d ' ')
# S68 D7-04/SKW-01: ADR/страницы + агент-тиры (де-дрейф канонов, источник — диск)
DECISIONS=$(ls -1 "$REPO_ROOT/llm-wiki/wiki/project/decisions/"*.md 2>/dev/null | wc -l | tr -d ' ')
SPRINTS=$(ls -1 "$REPO_ROOT/llm-wiki/wiki/project/sprints/"*.md 2>/dev/null | wc -l | tr -d ' ')
COMPONENTS=$(ls -1 "$REPO_ROOT/llm-wiki/wiki/project/components/"*.md 2>/dev/null | grep -vc README || true)
OPUS=$(grep -h '^model:' "$REPO_ROOT/kit/agents/"*.md 2>/dev/null | grep -c opus || true)
SONNET=$(grep -h '^model:' "$REPO_ROOT/kit/agents/"*.md 2>/dev/null | grep -c sonnet || true)
HAIKU=$(grep -h '^model:' "$REPO_ROOT/kit/agents/"*.md 2>/dev/null | grep -c haiku || true)
TODAY=$(date +%Y-%m-%d)

BLOCK="<!-- AUTO:kit-inventory (генерируется kit/kit-inventory.sh — НЕ править руками) -->
> **Инвентарь кита (авто, ${TODAY}):** агентов **${AGENTS}** (~/.claude/agents) · проектных скиллов **${SKILLS}** (.claude/skills) · superpowers-скиллов **${SP}** · хуков подключено: PreToolUse(Bash) **${PRE}** + UserPromptSubmit **${UPS}** + SessionStart **${SS}**; sh-файлов хуков на диске **${HOOK_FILES}**.
> ADR **${DECISIONS}** · sprint-страниц **${SPRINTS}** · component-страниц **${COMPONENTS}** · агент-тиры (ADR 0077): opus-4.8 **${OPUS}** / sonnet-5 **${SONNET}** / haiku-4.5 **${HAIKU}**.
<!-- /AUTO:kit-inventory -->"

python3 "$REPO_ROOT/kit/hooks/lib/kit_inventory_update.py" "$BLOCK" \
  "$REPO_ROOT/llm-wiki/wiki/project/architecture/kit-overview-ru.md" \
  "$REPO_ROOT/llm-wiki/wiki/project/architecture/tooling-inventory-ru.md" \
  "$@"

echo "kit-inventory: agents=${AGENTS} skills=${SKILLS} superpowers=${SP} hooks=${PRE}+${UPS}+${SS} (files=${HOOK_FILES}) ADR=${DECISIONS} sprints=${SPRINTS} components=${COMPONENTS} tiers=opus${OPUS}/sonnet${SONNET}/haiku${HAIKU}"

# Drift-guard (S57 review issue #2): зеркало kit/ vs живой ~/.claude — WARN, не блок.
drift=0
diff -rq "$REPO_ROOT/kit/agents" "$HOME/.claude/agents" >/dev/null 2>&1 || drift=1
diff -rq -x '__pycache__' -x '*.pyc' -x 'node_modules' -x 'tests' "$REPO_ROOT/kit/hooks" "$HOME/.claude/hooks" >/dev/null 2>&1 || drift=1
if [ "$drift" -eq 1 ]; then
  echo "WARN: kit/ mirror drifted from live ~/.claude — sync before ship:" >&2
  diff -rq "$REPO_ROOT/kit/agents" "$HOME/.claude/agents" 2>&1 | head -10 >&2 || true
  diff -rq -x '__pycache__' -x '*.pyc' -x 'node_modules' -x 'tests' "$REPO_ROOT/kit/hooks" "$HOME/.claude/hooks" 2>&1 | head -10 >&2 || true
else
  echo "kit-drift: mirror == live (clean)"
fi
