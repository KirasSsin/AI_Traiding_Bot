---
title: Research Evidence — autoresearch artifacts (audit trail)
type: index
tags: [research, autoresearch, evidence, audit-trail, ru]
created: 2026-05-09
status: stable
---

# Research Evidence

Cherry-picked artifacts из autoresearch branches — audit trail для production strategy ADRs. Read-only references.

## Files

- [[FINAL_STRATEGY]] — volume_breakout sweep#1644 spec (S39 ADR 0059 evidence). Held-out S=+9.96 PnL=+20.42% / 3.3y +122.66%
- [[CLOSE]] — autoresearch iter 1-7 falsification record (Donchian raw + EMA filter both FAIL conjoint, 9-th honest close)
- `results.tsv` — full audit trail 4510 sweeps × 10 strategies (213 PASS, 4.51M trials evaluated)

## Usage rules

1. **READ-ONLY** — these files are evidence, не editable specs. Source of truth = autoresearch branches.
2. ADRs ссылаются на эти файлы как primary evidence для pre-registration LOCK decisions.
3. Не cherry-pick дополнительные autoresearch artifacts без operator approval — bloat risk.

## Связанные документы

- [[../decisions/0059-sprint-39-volume-breakout-pre-registration]]
- [[../decisions/0054-sprint-35-donchian-pre-registration]]
- [[../sprints/sprint-39-volume-breakout-tech-debt]]
- [[../components/volume-breakout-strategy]]
