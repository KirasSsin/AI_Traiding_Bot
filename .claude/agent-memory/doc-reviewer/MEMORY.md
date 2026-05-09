---
name: Doc-reviewer memory index (persistent)
description: Orphan linking / frontmatter consistency / link integrity / Block 1↔2 sync patterns
type: reference
---

- [Orphan wiki-link resolution session](orphan_linking_session.md) — mental-map found + resolved 2026-05-09. Verified indicators/strategy/concepts already linked via full paths.
- [S36 T1 ADR pre-registration + canonical count drift tracking](MEMORY.md#s36-t1-pattern) — paired ADRs 0055 + 0056 analysis.

---

**S36 T1 pattern (paired ADRs 0055 + 0056, pure doc commit ce38eab):**
- Pure doc commit (no src/ changes)
- Both ADRs exist, frontmatter complete (title/type/tags/created/updated/status=accepted/sources)
- Anti-snooping discipline explicit в Status sections ("implemented в S36" / "Paired ADR")
- Sources references all exist:
  - 0055 → 0052, 0053, pre-s36-backlog ✓ all exist
  - 0056 → 0052, 0055, sprint-35, pre-s36-backlog ✓ all exist
- No broken wiki-links detected
- Cross-references OK: 0055 SD-7 forward reference `DELTA_N_TRIALS_LOCKED` = acceptable (will exist T7)

**Canonical counts drift post-T1:**
- index.md: **MISSING entries** для 0055 + 0056 (index.md tail截at line 240 shows 0050-0054 entries, no 0055/0056 visible)
- current-state.md: file does NOT exist (renamed OR moved), cannot verify "ADRs: 54→56" line
- Sprint pages: 0055/0056 reference "v0.1.0-alpha.36" tag future (correct per S36 plan)

**Concerns (track для T8 wiki-update):**
- index.md "Project — Decisions" section (lines 185-240) shows ADR index but 0055/0056 missing (post-T1 addition required)
- Canonical counts table (current-state.md) path not found — cannot verify drift, may be scheduled for separate update
- S36 plan file (`wiki/project/plans/2026-04-27-sprint-36-delta-activation.md`) referenced in 0055 Implementation section — needs verification exists

**Format consistency:**
- Both ADRs use "Status BEFORE data inspection" + "Consequences positive/negative/neutral" pattern ✓
- Section headings match preceding ADR pattern (0050-0054) ✓
- Verbatim trader/quant text preserved (SD-1 Hybrid H option, sigma_SR hierarchy) ✓

**Follow-ups for T8 (wiki-update phase, HARD-GATE per ADR 0043 cascade rule):**
- Add 0055 entry in index.md ADRs section (after 0054 line, before "## Queries")
- Add 0056 entry in index.md ADRs section (after 0055)
- Verify current-state.md exists + update "ADRs:" count line (54→56)
- Verify sprint-36-delta-activation.md plan file exists
- MEMORY observation: S35 T3 pattern (0052/0053/0054) repeated в S36 T1 (0055/0056) — pre-commit phase pure-docs → code phase T2-T7 → wiki-sync T8. Index/counts drift is expected, per prior cycles.
