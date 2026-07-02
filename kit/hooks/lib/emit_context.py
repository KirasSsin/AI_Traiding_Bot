#!/usr/bin/env python3
"""emit_context.py — surface a non-blocking hook's advisory text to the MODEL.

S69 T2 (D7-01). A hook that exits 0 and writes only to stderr is seen by the
USER but NOT by the model — so WARN hooks (context budget, per-task protocol,
docs staleness, cascade-read) were mute to the assistant that needed to act on
them. The Claude Code contract: an exit-0 hook that prints
    {"hookSpecificOutput": {"hookEventName": "<Event>", "additionalContext": "…"}}
to stdout has that text injected into the model's next request (wrapped in a
system reminder). This module builds exactly that object.

Dual-channel by design: hooks keep their stderr WARN (user-visible) AND call
this to reach the model. `additionalContext` is model-visible, user-hidden — the
two channels are complementary, not redundant.

Usage (CLI):   printf '%s' "$warn_text" | python3 emit_context.py <HookEventName>
Usage (import): import emit_context; emit_context.emit("PreToolUse", text)

`hookEventName` must match the firing event exactly (UserPromptSubmit /
PreToolUse / PostToolUse / …). Empty/whitespace text emits nothing. Text over the
10000-char additionalContext limit is truncated with an elision marker. Stdlib
only, so it runs under the system python3 the hooks already invoke.
"""

from __future__ import annotations

import json
import sys
from typing import TextIO

_LIMIT = 10000
_ELISION = "\n…(truncated)"


def emit(event: str, text: str, stream: TextIO | None = None) -> None:
    """Write the additionalContext JSON object for `event` to stdout (or `stream`)."""
    text = (text or "").strip()
    if not text:
        return
    if len(text) > _LIMIT:
        text = text[: _LIMIT - len(_ELISION)] + _ELISION
    obj = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    json.dump(obj, stream or sys.stdout, ensure_ascii=False)


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "PreToolUse"
    emit(event, sys.stdin.read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
