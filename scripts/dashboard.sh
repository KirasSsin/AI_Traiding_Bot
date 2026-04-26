#!/usr/bin/env bash
# S25 ADR 0039 — Dashboard launcher.
# Usage: ./scripts/dashboard.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .venv/bin/python ]; then
    echo "❌ .venv не найден. Создай venv + install deps:"
    echo "   python3.12 -m venv .venv && .venv/bin/pip install -e \".[dashboard]\""
    exit 1
fi

if ! .venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dashboard deps не установлены. Install:"
    echo "   .venv/bin/pip install -e \".[dashboard]\""
    exit 1
fi

echo "🚀 Starting AI Trading Bot Dashboard..."
echo "   URL: http://127.0.0.1:8000/"
echo "   Press Ctrl+C к stop"
echo ""

exec .venv/bin/python -m src.dashboard.app
