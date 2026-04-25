---
title: Wiki broken-link sync hook
type: component
tags: [infrastructure, hooks, process, wiki, drift-prevention]
created: 2026-04-25
updated: 2026-04-25
sources: []
status: stable
---

# Wiki broken-link sync hook

**TL;DR:** Claude Code `PreToolUse` hook на Bash. Срабатывает перед `git push`. Если в пушимых коммитах есть changes к `llm-wiki/wiki/**.md` файлам, hook сканирует **только эти changed files** на предмет broken `[[wiki-link]]` refs (target file не существует). Push блокируется если хоть один broken ref. Операционализация Bucket C7 — pre-S9 process improvement.

## Purpose

Wiki — компилированное знание проекта. Broken `[[link]]` refs ломают LLM-RAG retrieval (агент следует ссылке → 404 → читает нерелевантный fallback). Накопленный drift невидим до момента когда агент проваливает task через cyclic stale ref.

Прошлые prevention механизмы (manual review, sprint-finish step 5b orphan-audit) ловят добавленные ссылки на orphans, но не добавленные ссылки на NON-EXISTENT pages. Hook закрывает gap automation (Anthropic best practice: "automation > reminders").

**Scope decision:** scan **только changed files** в pushed commits, не whole wiki. Rationale:
- Whole-wiki scan ловит исторические refs в plan/backlog files (closed archives) → noise blocks unrelated PRs
- Changed-files scan = focused enforcement: "don't introduce new broken refs"
- Historical drift addressed separately (one-time cleanup)

## Files

- Script: `~/.claude/hooks/wiki-broken-link-check.sh` — bash glue (~135 lines), +x.
- **Scan logic:** `~/.claude/hooks/lib/wiki_broken_link_scan.py` — external Python script (~132 lines), +r. Extracted from inline heredoc после S9 ship caught bash bug — triple-backtick (` ``` `) inside `$(... <<'PYEOF' ...)` heredoc fails despite single-quoted delimiter (bash interprets backticks pre-heredoc). External script invocation via `python3 "$SCAN_SCRIPT"` avoids parse collision entirely.
- Registration: `~/.claude/settings.json`, `hooks.PreToolUse[matcher="Bash"].hooks[]` →
  `command="$HOME/.claude/hooks/wiki-broken-link-check.sh"` (третий entry, после adr-agent-sync-check + adr-index-sync-check).
- Watched directory: `llm-wiki/wiki/` (relative to repo root) — opt-in trigger.

**Bash quirk lesson (post-S9):** ALWAYS run `bash -n <script>` after editing hook scripts. Triple-backtick OR complex heredoc patterns can fail despite quoted delimiters. Pattern documented в `~/.claude/CLAUDE.md` section 9b.

## Hook contract

Claude Code передаёт JSON на stdin:

```json
{ "tool_input": { "command": "git push origin feature/sprint-9-X" } }
```

Коды выхода:

| Code | Meaning |
|---|---|
| `0` | allow the tool call |
| `2` | **block** the tool call; stderr shows broken refs list |
| other non-zero | fail open (Claude Code proceeds) |

## Algorithm

```
stdin: tool_input
    ↓
command contains hook script path? (self-test guard)
    → yes → exit 0 (allow — false-positive prevention)
command contains 'git push'?
    → no  → exit 0 (allow)
    → yes ↓
repo has llm-wiki/wiki/?
    → no  → exit 0 (allow — other repo)
    → yes ↓
determine base (upstream or origin/main merge-base)
    → no base → exit 0 (fail open)
    ↓
git diff --name-only base..HEAD -- llm-wiki/wiki/ | grep '\.md$'
    → no changed wiki files → exit 0 (allow)
    → has changed files ↓
python3 scan: parse [[link]] from each changed file
    skip: empty / anchor-only (#section) / NNNN placeholder / TOML [[tool.X]] /
          fenced code blocks / inline-code spans (odd backtick count before)
    resolve target: 3 paths
        (1) relative to source file's dir → check exists
        (2) relative to wiki_root → check exists
        (3) source-relative для cross-repo refs (../../CLAUDE) → check exists
    target unresolvable → broken
broken empty?
    → yes → exit 0 + "✓ Wiki broken-link check OK"
    → no  → exit 2 + block message with broken list
```

## Resolution corpus

- **Scan corpus:** только changed files в `git diff base..HEAD -- llm-wiki/wiki/` filtered к `*.md`
- **Resolution corpus:** ВЕСЬ wiki tree (basename_index built from all `wiki/**.md`) — позволяет unqualified `[[name]]` ссылаться на любую существующую wiki page

## Skip patterns (false-positive prevention)

| Pattern | Why skipped |
|---------|-------------|
| `[[]]` empty | Not a real link |
| `[[#section]]` anchor-only | Same-page navigation |
| `[[...]]` ellipsis | Markdown literal |
| `[[NNNN-slug]]` template placeholder | Documentation example, not real ref |
| `[[tool.mypy.overrides]]` TOML | Inside code blocks (also caught by fenced-block detection) |
| Inside ` ```...``` ` fenced code block | Code, not prose |
| Inside `` `...` `` inline code span | Literal example |
| `[[http://...]]` external URL | Out of scope |

## Fail-open policy

Hook намеренно fail-open:
- `python3` отсутствует или payload malformed.
- Команда не содержит `git push`.
- Текущий рабочий каталог не git repo.
- `llm-wiki/wiki/` не существует (значит, не наш проект).
- Нет changed wiki files.

Fail-CLOSED только когда python detector finds resolved-False ref в changed file.

## Self-test guard

PreToolUse matcher `"Bash"` triggers hook на ANY Bash invocation, включая test commands вида `echo '{"tool_input":{"command":"git push ..."}}' | bash hook.sh`. Substring `"git push"` в test payload ложно triggers hook.

Guard: skip если `$command_str` references hook script paths (`adr-agent-sync-check.sh` / `adr-index-sync-check.sh` / `wiki-broken-link-check.sh` / `hooks/*-check.sh`). Real `git push` не содержит этих paths, так что guard safe. См. `~/.claude/hooks/wiki-broken-link-check.sh:42-49`.

## Test scenarios (env -i sandbox per hook-test skill)

| # | Input | Expected exit | Reason |
|---|-------|---------------|--------|
| 1 | `{"tool_input":{"command":"ls -la"}}` | `0` | Non-git command |
| 2 | Self-test echo piped к hook | `0` | Self-test guard fires |
| 3 | Real `git push` с no wiki changes | `0` | No changed wiki files |
| 4 | Real `git push` с changed wiki + clean refs | `0` + `✓` stderr | All refs resolve |
| 5 | Real `git push` с changed wiki + broken ref | `2` + block message | Detector finds broken |

## Behavior on unresolvable / placeholder targets

- `[[NNNN-slug]]` (uppercase NNNN literal) — allowed via skip pattern (template placeholder)
- Cross-repo refs `[[../../../CLAUDE|llm-wiki/CLAUDE]]` — resolved via path 1 (relative-to-source), if file exists at resolved path → pass
- Wrong number of `..` (e.g. `[[../../CLAUDE]]` from depth-3 source pointing к llm-wiki/CLAUDE.md) — caught as broken (real bug)

## Operator workflow on block

```
🚫  Wiki broken-link check FAILED

3 broken [[link]] ref(s) detected в llm-wiki/wiki/:

    project/components/X.md:42: [[old-name]]
    project/components/Y.md:88: [[../../wrong-path]]
    project/components/Z.md:101: [[non-existent]]

Required action — one of:
  1) Fix each broken ref: rename [[old]] → [[correct-target]] OR create
     missing target page.
  2) If the link is intentional placeholder (deferred page) — change syntax
     к plain markdown text (drop [[ ]]) until target exists.

Then retry push.
```

## Why bash + inline python (not pure bash)

Pure bash regex для `[[wiki-link]]` parsing fragile (escape hell, нет normpath). Inline `python3 <<PYEOF` дешевле + читаем + reliable. Same pattern как adr-index-sync-check.sh (использует python для JSON parse).

## Performance

- 110 wiki files × ~30 link refs avg = 3300 ref resolutions
- Single `os.walk` + `dict` lookup на ref = O(refs) ~ < 100ms на push
- Fail-open на slow path: timeout не enforced (CC hooks не cancel hook script)

## Referenced by

- [[../architecture/development-workflow]] — PHASE 8 step 5c HARD-GATE (Block 1↔Block 2 sync rule includes broken-link prevention)
- [[../../index]] — Project — Components section

## Related

- [[adr-agent-sync-hook]] — sister hook (ADR ↔ agent prompt mtime sync, ADR 0017)
- [[adr-index-sync-hook]] — sister hook (ADR ↔ index.md ref sync, Bucket C6)
- [[../architecture/development-workflow]] — PHASE 8 finishing
- Bucket C7 (this) — pre-S9 process improvement
