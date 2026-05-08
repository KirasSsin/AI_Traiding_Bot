#!/usr/bin/env bash
# AI Trading Bot — Single launch script.
#
# Default mode: Dashboard UI (backtest comparison via web browser).
# Live mode:    --live flag → δ TESTNET trading (requires S35_DEMO_ACTIVE=true в .env).
#
# Usage:
#   ./scripts/start-bot.sh           # Dashboard UI на http://127.0.0.1:8000/
#   ./scripts/start-bot.sh --live    # Live δ TESTNET trading (per delta-activation-playbook.md)
#   ./scripts/start-bot.sh --help    # Show usage

set -euo pipefail

cd "$(dirname "$0")/.."

# Pre-flight checks
if [ ! -f .venv/bin/python ]; then
    echo "❌ .venv не найден. Setup:"
    echo "   python3.12 -m venv .venv"
    echo "   .venv/bin/pip install -e \".[dev,dashboard]\""
    exit 1
fi

if ! .venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dashboard deps не установлены. Install:"
    echo "   .venv/bin/pip install -e \".[dashboard]\""
    exit 1
fi

# Mode routing
MODE="${1:-dashboard}"

case "$MODE" in
    --help|-h|help)
        echo "AI Trading Bot launcher"
        echo ""
        echo "Modes:"
        echo "  (no args)   Dashboard UI на http://127.0.0.1:8000/ (DEFAULT — recommended)"
        echo "  --live      Live δ TESTNET trading (requires S35_DEMO_ACTIVE=true в .env)"
        echo "  --backfill  Download historical OHLCV bars (advanced)"
        echo "  --help      Show this help"
        echo ""
        echo "Pre-flight (live mode):"
        echo "  Read llm-wiki/wiki/project/components/delta-activation-playbook.md FIRST."
        echo "  Verify .env has S35_DEMO_ACTIVE=true + TESTNET=true."
        ;;

    --live)
        echo "🚀 Live δ TESTNET mode..."
        echo "   ВНИМАНИЕ: бот будет торговать на TESTNET."
        echo "   Verify per delta-activation-playbook.md pre-activation checklist (8 items + S38 NEW gates F4-F7)."
        echo "   .env must have S35_DEMO_ACTIVE=true и TESTNET=true."
        echo ""
        echo "   Press Ctrl+C к stop."
        echo ""
        exec .venv/bin/python -m src run

        ;;

    --backfill)
        shift
        echo "📥 OHLCV backfill mode..."
        exec .venv/bin/python -m src backfill "$@"
        ;;

    dashboard|*)
        echo "🚀 AI Trading Bot Dashboard..."
        echo "   URL: http://127.0.0.1:8000/"
        echo "   Press Ctrl+C к stop."
        echo ""
        exec .venv/bin/python -m src.dashboard.app
        ;;
esac
