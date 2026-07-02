#!/usr/bin/env bash
# kit/auto-resume/install.sh — установка Auto-Resume (S58): скрипты + хук + launchd.
# Использование: install.sh [install|uninstall|status]. Идемпотентен.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
AR_DIR="$CLAUDE_DIR/auto-resume"
BIN_DIR="$AR_DIR/bin"
PLIST_SRC="$KIT_DIR/com.kit.auto-resume.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.kit.auto-resume.plist"
SETTINGS="$CLAUDE_DIR/settings.json"
LABEL="com.kit.auto-resume"
UID_N="$(id -u)"

cmd="${1:-install}"

status() {
  echo "--- auto-resume status"
  [ -f "$PLIST_DST" ] && echo "plist: installed" || echo "plist: NOT installed"
  launchctl print "gui/$UID_N/$LABEL" >/dev/null 2>&1 && echo "launchd: loaded" || echo "launchd: not loaded"
  jq -e '.hooks.StopFailure' "$SETTINGS" >/dev/null 2>&1 && echo "hook StopFailure: registered" || echo "hook StopFailure: NOT registered"
  ls "$AR_DIR"/pending.json 2>/dev/null && echo "marker: PENDING" || echo "marker: none"
  tail -3 "$AR_DIR/log" 2>/dev/null || true
}

uninstall() {
  launchctl bootout "gui/$UID_N/$LABEL" 2>/dev/null || true
  rm -f "$PLIST_DST"
  echo "launchd agent removed (скрипты и хук остаются; хук без поллера безвреден)"
}

install() {
  mkdir -p "$BIN_DIR/lib" "$AR_DIR"
  cp "$KIT_DIR/auto-resume-poller.sh" "$BIN_DIR/"
  cp "$KIT_DIR/lib/auto_resume_poll.py" "$BIN_DIR/lib/"
  chmod +x "$BIN_DIR/auto-resume-poller.sh"

  # C1-хук: зеркало в живые hooks (limit-marker.sh + lib)
  cp "$KIT_DIR/../hooks/limit-marker.sh" "$CLAUDE_DIR/hooks/" 2>/dev/null || true
  cp "$KIT_DIR/../hooks/lib/auto_resume_marker.py" "$CLAUDE_DIR/hooks/lib/" 2>/dev/null || true
  chmod +x "$CLAUDE_DIR/hooks/limit-marker.sh" 2>/dev/null || true

  # Синтаксис-гейт (guard-the-guards, как kit/install.sh)
  bash -n "$BIN_DIR/auto-resume-poller.sh"
  bash -n "$CLAUDE_DIR/hooks/limit-marker.sh"
  python3 -m py_compile "$BIN_DIR/lib/auto_resume_poll.py"

  # Регистрация StopFailure-хука в settings.json (идемпотентно)
  if ! jq -e '.hooks.StopFailure' "$SETTINGS" >/dev/null 2>&1; then
    # tmp на ТОМ ЖЕ томе → атомарный rename (security review LOW-2);
    # rm при провале — никакого secret-bearing собрата (урок S57 .bak)
    tmp="$(mktemp "$CLAUDE_DIR/settings.json.XXXX.tmp")"
    trap 'rm -f "$tmp"' ERR
    jq '.hooks.StopFailure = [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/limit-marker.sh"}]}]' \
      "$SETTINGS" > "$tmp"
    python3 -c "import json,sys; json.load(open('$tmp'))"
    mv "$tmp" "$SETTINGS"
    trap - ERR
    echo "hook StopFailure: registered"
  else
    echo "hook StopFailure: already registered"
  fi

  # launchd
  plutil -lint "$PLIST_SRC" >/dev/null
  mkdir -p "$HOME/Library/LaunchAgents"
  cp "$PLIST_SRC" "$PLIST_DST"
  launchctl bootout "gui/$UID_N/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$UID_N" "$PLIST_DST"
  echo "OK: auto-resume установлен (интервал 600с). Логи: $AR_DIR/log"
}

case "$cmd" in
  install) install ;;
  uninstall) uninstall ;;
  status) status ;;
  *) echo "usage: $0 [install|uninstall|status]" >&2; exit 2 ;;
esac
