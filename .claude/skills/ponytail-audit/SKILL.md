---
name: ponytail-audit
description: Use when reviewing a diff or repository for over-engineering (NOT correctness) — before merge, or at PHASE 5/6 verify/review. Flags removable code across 5 axes (delete/stdlib/native/yagni/shrink) with per-line findings and an impact-ranked summary. Orthogonal to the correctness-focused code-review command and domain reviewers.
---

# Ponytail audit — over-engineering scan

Ported from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) v4.8.4 (MIT) — `/ponytail-review` + `/ponytail-audit`.

Scope: **over-engineering ONLY, not correctness.** Correctness stays with domain reviewers (trading-logic / quant-stats / …) and the `code-review` command. This skill is the missing over-engineering axis.

## Two modes

- **Diff review** (default): scan the current diff / staged changes.
- **Repo audit**: scan the whole repo (or a given path), rank findings by impact.

## The 5 tags

- `delete` — code removable entirely (unused / unreachable / speculative)
- `stdlib` — reinvents something the standard library already provides
- `native` — reinvents a native platform / framework feature
- `yagni` — abstraction / flexibility / config not required by any current caller
- `shrink` — works but can be materially shorter (collapse, inline, one-line)

## Per-finding format

```
<path>:L<line>: <tag> <what to cut>. <replacement>.
```

## Summary line

End with net impact:

- `"N lines and M dependencies removable"` — when findings exist
- `"Lean already. Ship."` — when clean

## Guardrails

Do NOT flag correctness bugs, style nits, or anything explicitly requested. Never propose removing input validation, error handling, or security. Rank by impact (biggest removals first) in repo-audit mode.
