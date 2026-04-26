---
title: context-budget-warn.sh — UserPromptSubmit hook warning at 60%/80% transcript size
type: component
tags: [hook, mechanical-enforcement, context-budget, user-prompt-submit, sprint-32d, kit-phase-3]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - ~/.claude/hooks/context-budget-warn.sh
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/SPRINT_STATE.md
---

# context-budget-warn.sh

**TL;DR:** UserPromptSubmit hook (advisory, never blocks). Warns operator если transcript file size exceeds proxy thresholds для context window usage. 🟡 yellow at 800KB (~60%), 🔴 red at 1200KB (~80%).

## Block 1 — Code refs

| Element | Anchor |
|---------|--------|
| Hook script | `~/.claude/hooks/context-budget-warn.sh` (out-of-repo, executable 755) |
| Trigger | Claude Code `UserPromptSubmit` event |
| Established by | ADR 0048 (Sprint 32d Kit Phase 3) |
| Pattern source | Anthropic best practices `/compact` discipline + `/clear` discipline |

## Block 2 — Description

### Назначение

Proactive context usage warning. Preventes session crash from unmanaged context overflow. Advisory only — operator decides action (`/compact` / `/clear` / continue).

Replaces reactive workflow:
- Without hook: operator notices session sluggish → `/compact` после fact (часто слишком late, lose context)
- With hook: hook warns at 60% → operator proactive `/compact` (preserve focus)

### Trigger conditions

Hook fires:
- ON: every `UserPromptSubmit` event (each user message)
- Reads `transcript_path` from stdin JSON
- Measures file size в KB

### Logic

```
1. Parse stdin JSON → extract transcript_path
2. If path missing OR file missing → exit 0 (fail open)
3. Get file size в KB (du -k)
4. If size > URGENT_KB (1200) → emit 🔴 urgent warning к stderr, exit 0
5. If size > WARN_KB (800) → emit 🟡 yellow warning к stderr, exit 0
6. Otherwise → exit 0 silent
```

### Threshold rationale

| Threshold | Size | Approx context % | Action recommended |
|-----------|------|------------------|-------------------|
| WARN_KB | 800KB | ~60% (tuning) | Consider `/compact` soon |
| URGENT_KB | 1200KB | ~80% (tuning) | `/compact <focus>` OR `/clear` immediately |

**Tuning estimate:** 1KB transcript ≈ 1000 tokens (varies 0.5-2.5KB per token depending на content density). Code-heavy sessions = denser (lower KB/token), prose-heavy = lighter. Thresholds conservative — false-positive better than false-negative.

200K context window = ~200KB ideal estimate, но JSONL transcript includes role tags / metadata / tool results = ~2-3× expansion. Empirical: 1.5MB transcripts often hit context limits.

### Tuning thresholds (если нужно)

Edit `~/.claude/hooks/context-budget-warn.sh`:
```bash
WARN_KB=800       # change here
URGENT_KB=1200    # change here
```

Per-project tuning candidate (S32d carry-over): trading work с большим количеством code → could lower WARN к 600KB.

### Fail-open policy

Hook fails OPEN (exit 0 silently) on:
- Missing `transcript_path` field
- Missing transcript file (race condition при new session)
- Python3 missing
- du command failure

NEVER blocks prompt submission. Advisory only.

### Tests (run during creation per ADR 0048 T2)

| Test | Input | Expected |
|------|-------|----------|
| Small file (no warn) | `/etc/hosts` (~1KB) | exit 0, no stderr |
| Yellow warn | 900KB file | exit 0 + 🟡 stderr |
| Red urgent | 1300KB file | exit 0 + 🔴 stderr |
| Missing path | empty JSON | exit 0 (fail open) |

All 4 tests passed S32d Phase 4 T2 verify.

### Configuration

| Setting | Value |
|---------|-------|
| Path | `~/.claude/hooks/context-budget-warn.sh` |
| Permissions | 755 (executable) |
| Hook type | UserPromptSubmit |
| Registered в | `~/.claude/settings.json` `hooks.UserPromptSubmit[0].hooks` (2nd entry, после caveman-mode-tracker.js) |
| Always exits 0 | Advisory only — never blocks |

### Limitations (honest)

1. **Crude proxy** — file size != exact token count. Off by factor of 2-3× depending на content
2. **No per-message accumulation tracking** — relies on transcript file size which Claude Code maintains
3. **No /compact awareness** — after compact, transcript truncated → hook resets warning automatically (✓ side effect)
4. **No model-specific tuning** — 200K vs 1M context windows use same thresholds (TODO: read model from settings.json в future iteration)

### Why MVP version not full token counting?

Full token count requires:
- Parse JSONL transcript message-by-message
- Apply tokenizer (model-specific — Claude tokenizer not publicly documented exactly)
- Track per-message tokens with sliding window

Estimated effort 8-12 hours для MVP token counter. Vs file size proxy = 30 min. Trade-off accepted: proxy "good enough" for advisory warning purpose, exact counting не critical.

## Related

- [[../decisions/0048-sprint-32d-kit-phase-3-improvements]] — этот hook создан здесь
- [[../sprints/sprint-32d-kit-phase-3-improvements]] — S32d (Kit Phase 3 final)
- Anthropic Claude Code best practices `/compact` discipline + `/clear` discipline (S31 ADR 0044 reference)
- [[sprint-state-freshness-hook]] — sister hook (mechanical enforcement pattern, но push-time blocking)
