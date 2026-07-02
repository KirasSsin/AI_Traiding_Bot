#!/usr/bin/env python3
"""op_detect.py — classify a shell command by its UNQUOTED skeleton, not a raw
substring of the whole command.

S69 KIT-OD-1. The gate hooks detected `git merge` / `gh pr merge` via a substring
match on the ENTIRE command, which false-fired whenever those words appeared
inside a quoted argument (a commit message, a grep pattern, an echo) — blocking
benign work during an active sprint.

Approach: strip the CONTENTS of quoted spans first, then apply the proven
substring floor (whitespace-normalise + strip git/gh global value-flags) to the
remaining skeleton. A quoted literal vanishes → no false-fire; a real op in
command position stays → still gates, INCLUDING after any separator
(`;` `&&` `|` newline `{ }` subshell / backtick), because separators are not
quotes and remain in the skeleton. This is deliberately fail-safe: on ambiguity
it errs toward GATE (over-gating is safe for a money-path gate; under-gating is a
security hole).

`eval "<op>"` and `sh -c "<op>"` execute a QUOTED argument, so when the skeleton
still contains `eval` / `… -c`, the op patterns are re-checked against the RAW
(un-stripped) command — a quoted op there IS executed and must gate.

Usage:  printf '%s' "$command" | python3 op_detect.py <merge|push|commit>
Stdout: GATE | skip | allow   (skip = git merge-base/-tree/-file plumbing only)
Exit:   always 0. This classifier is total (regex-based, no parse step that can
        fail), so it never emits PARSE_ERROR; the hook-level substring fallback
        remains only for the python3-missing case (defence in depth).

Design history (S69 Phase-6 security review): substring-on-whole-command was
bypassable by false-fire suppression needs; pure shlex argv-tokenisation was
bypassable by a separator glued to a word (`echo hi;git merge X`) and by
newline / brace-group / backtick. Quote-strip + floor is robust against the whole
separator class at once — no separator enumeration to keep exhaustive.

Residual (documented): an inline-alias (`git -c alias.z=merge z`), a fully
variable-expanded command (`$CMD`), or an op-literal as a *bare* (unquoted)
non-command argument (`echo git merge`) gate conservatively. All err toward
gating — safe for money-path.

Stdlib only (re, sys) — runs on the system python3 the hooks already use.
"""

from __future__ import annotations

import re
import sys


def _strip_quoted(command: str) -> str:
    """Remove the contents of '...'/"..." spans, keeping unquoted text.

    Unbalanced quote → return the original command (conservative: never hide a
    possible op behind a stray/escaped quote).
    """
    out: list[str] = []
    quote: str | None = None
    for c in command:
        if quote:
            if c == quote:
                quote = None
        elif c in ("'", '"'):
            quote = c
        else:
            out.append(c)
    if quote is not None:
        return command
    return "".join(out)


_WS = re.compile(r"\s+")
# git / gh global value-flags that sit between the program and its subcommand.
_GIT_GLOBALS = re.compile(
    r"\bgit(?:\s+-[cC]\s+\S+|\s+--(?:git-dir|work-tree|namespace|exec-path)(?:=\S+|\s+\S+))+\s"
)
_GH_GLOBALS = re.compile(r"\bgh(?:\s+-R\s+\S+|\s+--repo(?:=\S+|\s+\S+))+\s")


def _normalize(text: str) -> str:
    """Collapse whitespace (incl. newlines/tabs) and strip git/gh global flags."""
    text = _WS.sub(" ", text)
    prev = ""
    while prev != text:  # repeat for `git -c a -c b merge` style chains
        prev = text
        text = _GIT_GLOBALS.sub("git ", text)
        text = _GH_GLOBALS.sub("gh ", text)
    return text


# `git merge` (not merge-base/-tree/-file) | `gh pr merge` | `gh api …/pulls/N/merge`
_MERGE = re.compile(r"\bgit merge\b(?!-)|\bgh pr merge\b|pulls/[^/\s]+/merge\b")
_MERGE_PLUMBING = re.compile(r"\bgit merge-(?:base|tree|file)\b")
_PUSH = re.compile(r"\bgit push\b")
_COMMIT = re.compile(r"\bgit commit\b(?!-)")  # not commit-tree
# `-[A-Za-z]*c` matches a combined short-flag cluster (`-lc`, `-ec`, `-xc`, `-ic`)
# as well as a standalone `-c` — all execute the following argument (S69 review B).
_EVAL_OR_SHC = re.compile(r"\beval\b|\b(?:ba|z|k|da)?sh\s+(?:-\S+\s+)*-[A-Za-z]*c\b")


def _match(text: str, op: str) -> str:
    if op == "merge":
        if _MERGE.search(text):
            return "GATE"
        if _MERGE_PLUMBING.search(text):
            return "skip"
        return "allow"
    if op == "push":
        return "GATE" if _PUSH.search(text) else "allow"
    if op == "commit":
        return "GATE" if _COMMIT.search(text) else "allow"
    return "allow"


def classify(command: str, op: str) -> str:
    """Classify a whole (possibly compound) command → GATE / skip / allow."""
    skel = _normalize(_strip_quoted(command))
    verdict = _match(skel, op)
    if verdict == "GATE":
        return "GATE"
    # eval / sh -c execute a quoted body → re-check the raw command for the op.
    if _EVAL_OR_SHC.search(skel) and _match(_normalize(command), op) == "GATE":
        return "GATE"
    return verdict


def main() -> int:
    op = sys.argv[1] if len(sys.argv) > 1 else "merge"
    print(classify(sys.stdin.read(), op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
