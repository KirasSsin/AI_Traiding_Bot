---
name: Orphan wiki-link resolution session — mental-map and verification of indicators/strategy/concepts
description: Doc-reviewer scan for orphan pages (zero incoming [[wiki-links]]). Found 1 true orphan (mental-map), verified 7 others had incoming links via full paths. Resolved orphan with bidirectional linking.
type: project
---

## Orphan detection (systematic grep scan)

**Search scope:** `/llm-wiki/wiki/` excluding `plans/` and `queries/`.

**Initial candidates (zero matches for `\[\[(basename)\]\]`):**
- adx, atr, ema, rsi (trading/indicators)
- ema-crossover-adx-rsi (trading/strategies)
- slippage-model (trading/concepts)
- mental-map (project/)
- sprint-metrics (project/)

## Resolution per candidate

### Trading indicators + strategy (links verified via full paths)
- `[[trading/indicators/ema]]` — 5+ incoming links (index.md + sprint-03 + sprint-plans + components/indicators.md + components/strategy.md)
- `[[trading/indicators/adx]]` — 5+ incoming links (same pattern)
- `[[trading/indicators/rsi]]` — 5+ incoming links (same pattern)
- `[[trading/indicators/atr]]` — 5+ incoming links (same pattern)
- `[[trading/strategies/ema-crossover-adx-rsi]]` — 7+ incoming links (index.md + sprint-03 + plans + components)

**Status:** NOT orphans. Index.md entries at lines 16/20-23 provide primary links; secondary links in sprint pages + component pages.

### Trading concept + project metrics (links verified)
- `[[trading/concepts/slippage-model]]` — 2 incoming links (index.md line 33 + execution-timing.md)
- `[[project/sprint-metrics]]` — 1 incoming link (index.md line 50)

**Status:** NOT orphans.

### Orphan found: mental-map
- `[[project/mental-map]]` — 0 incoming links (checked all forms: short/full path)
- Created: 2026-04-25 (S31 as navigation discovery tool)
- Status: stable, used by agents for open-ended queries
- Was UNREFERENCED from index.md (the primary discovery page)

## Resolution actions

**Added bidirectional links:**

1. **index.md (line 42):** Added entry in "Project — Architecture" section:
   ```
   - [[project/mental-map]] — "где искать X" дерево решений для быстрой навигации; первый источник для открытых запросов агентов.
   ```

2. **mental-map.md (lines 204-206):** Added "Связанные документы" section:
   ```markdown
   ## Связанные документы

   - [[../index]] — полный каталог всех wiki-страниц (по разделам)
   - [[../architecture/current-state]] — живые счётчики (текущее число ADRs / спринтов / компонентов)
   ```

## Post-resolution verification

Grep confirms mental-map now has incoming links:
- `index.md:42` (new primary entry)
- `index.md:255` (secondary entry in different section — pre-existing)
- `components/README.md:183` (pre-existing reference)

## Observations

- **Orphan cause:** mental-map was created as a utility/navigation page but never surfaced in index.md catalog.
- **Link format convention:** All wiki links use full `[[path/to/page]]` format (no markdown extension, no short names).
- **Index.md priority:** Primary discovery point for all wiki pages. Must be updated when new navigation/utility pages added.
- **Bidirectional linking pattern:** Pages should link back to index.md or related discovery pages (per ADR 0017 Block 1 ↔ Block 2 sync).

## Future prevention

- Add to sprint-finish checklist (PHASE 8 HARD-GATE): "All new non-plan pages indexed in index.md?"
- Consider adding mental-map scan to adr-index-sync-hook.sh (currently checks ADRs only).

