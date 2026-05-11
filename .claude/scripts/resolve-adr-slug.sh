#!/usr/bin/env bash
# resolve-adr-slug.sh
# Usage: resolve-adr-slug.sh <NNNN>
# Returns full slug without .md extension, e.g. "0014-walk-forward-train2000-test500"
# Exit 1 if not found.
#
# Purpose: prevent wiki-broken-link-check.sh hook failures caused by guessed ADR slugs.
# Run before writing [[../decisions/NNNN-*]] links in sprint pages / component pages.

set -e

NUM="${1:-}"
if [ -z "$NUM" ]; then
    echo "Usage: $0 <ADR-number> (e.g. 0014 or 14)" >&2
    exit 1
fi

# Normalize to 4-digit zero-padded
NUM_PADDED=$(printf '%04d' "$NUM" 2>/dev/null || echo "$NUM")

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
ADR_DIR="$REPO_ROOT/llm-wiki/wiki/project/decisions"

SLUG=$(ls "$ADR_DIR" 2>/dev/null | grep "^${NUM_PADDED}-" | head -1 | sed 's/\.md$//')

if [ -z "$SLUG" ]; then
    echo "ERROR: No ADR matching '${NUM_PADDED}' in $ADR_DIR" >&2
    echo "Available ADRs:" >&2
    ls "$ADR_DIR" 2>/dev/null | grep "^${NUM_PADDED}" | head -5 >&2 || echo "  (none)" >&2
    exit 1
fi

echo "$SLUG"
