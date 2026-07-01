#!/usr/bin/env bash
# kit/install.sh — разворачивает кит из репозитория в ~/.claude (S57, KIT-005).
# Идемпотентен. Бэкапит существующие файлы в ~/.claude/.kit-backup/<timestamp>/.
# settings.example.json копируется в ~/.claude/settings.json ТОЛЬКО если его там нет
# (никогда не перетирает живой конфиг — в нём могут быть локальные правки).
set -euo pipefail

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_DIR/.kit-backup/$STAMP"

echo "kit install: $KIT_DIR -> $CLAUDE_DIR"
mkdir -p "$CLAUDE_DIR/agents" "$CLAUDE_DIR/hooks" "$BACKUP_DIR"

# Бэкап текущего состояния (только то, что заменяем)
cp -R "$CLAUDE_DIR/agents" "$BACKUP_DIR/agents" 2>/dev/null || true
cp -R "$CLAUDE_DIR/hooks"  "$BACKUP_DIR/hooks"  2>/dev/null || true

# Агенты и хуки — из репо в живую систему
cp "$KIT_DIR/agents/"*.md "$CLAUDE_DIR/agents/"
cp -R "$KIT_DIR/hooks/." "$CLAUDE_DIR/hooks/"

# Синтаксис-проверка хуков сразу после установки (guard-the-guards)
broken=0
for h in "$CLAUDE_DIR/hooks/"*.sh; do
  bash -n "$h" || { echo "BROKEN: $h" >&2; broken=1; }
done
if [ "$broken" -ne 0 ]; then
  # Откат живой системы из бэкапа (security review S57, Concern 1)
  cp -R "$BACKUP_DIR/hooks/."  "$CLAUDE_DIR/hooks/"  2>/dev/null || true
  cp -R "$BACKUP_DIR/agents/." "$CLAUDE_DIR/agents/" 2>/dev/null || true
  echo "install ABORTED: битые хуки; живая система восстановлена из $BACKUP_DIR" >&2
  exit 2
fi

# settings: только если отсутствует (шаблон без секретов)
if [ ! -f "$CLAUDE_DIR/settings.json" ]; then
  cp "$KIT_DIR/settings.example.json" "$CLAUDE_DIR/settings.json"
  echo "settings.json создан из шаблона (секреты добавь через Keychain/env)"
else
  echo "settings.json существует — не трогаю (шаблон: kit/settings.example.json)"
fi

echo "OK: kit установлен. Бэкап: $BACKUP_DIR"
