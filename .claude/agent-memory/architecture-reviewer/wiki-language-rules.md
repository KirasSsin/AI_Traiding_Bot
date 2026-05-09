---
name: Wiki language rules and file locations
description: Canonical file paths for architecture pages + language translation rules applied 2026-05-09
type: project
---

Wiki language translation batch completed 2026-05-09.

**Why:** llm-wiki/CLAUDE.md Language rules (binding) require all wiki pages → Russian narrative + EN code/anchors.

**File location facts (path corrections vs task brief):**
- `mental-map.md` lives at `llm-wiki/wiki/project/mental-map.md` (NOT `architecture/mental-map.md`)
- `delta-activation-playbook.md` lives at `llm-wiki/wiki/project/components/delta-activation-playbook.md` (NOT `architecture/delta-activation-playbook.md`)
- `development-workflow.md`, `current-state.md`, `reason-codes-schema.md` → confirmed at `architecture/`

**How to apply:** When referencing these files in wiki or briefs, use the above paths. Brief may cite wrong path — always verify with `find` before Read.

**Translation invariants:**
- `[[wiki-link]]` anchors use EN filenames regardless of page language (filenames are EN-only per naming convention)
- Code blocks: 100% English preserved
- Frontmatter tags/type/status: English preserved
- Table column headers → Russian when narrative; leave technical identifiers (FSM states, ADR numbers, etc.) as-is
- `updated:` date bumped to translation date on all touched pages
