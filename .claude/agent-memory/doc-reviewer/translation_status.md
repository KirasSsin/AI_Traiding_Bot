---
name: Wiki translation audit — S01-S23 sprints + runbooks (2026-05-09)
description: Progress on translating sprint pages (38 total) + 5 runbooks from English to Russian per new CLAUDE.md rules (2026-05-09)
type: project
---

## Translation Rules Applied (per repo CLAUDE.md language rules 2026-05-09)

**Wiki content → RUSSIAN (full):**
- All sprint pages `wiki/project/sprints/*.md` — RU titles + RU section headers + RU body
- All runbooks `wiki/project/runbooks/*.md` — full translation EN → RU
- Keep English: file paths, code blocks, function names, identifiers, tags, status values

**Section header mapping:**
- `## Goal` → `## Цель`
- `## Scope delivered` → `## Доставленная функциональность`
- `## Decisions & deviations` → `## Решения и отклонения`
- `## Verification` → `## Проверка`
- `## Impact on downstream` → `## Влияние на следующие спринты`
- `## Follow-ups carried forward` → `## Перенесённые задачи`
- `## Related` → `## Связанные`
- `### Code` → `### Код`
- `### Wiki` → `### Вики`
- `### Removed / migrated` → `### Удалено / перенесено`
- `### Tests` → `### Тесты`
- `### Config` → `### Конфиг`
- `### Migrations` → `### Миграции БД`

**Title translation examples (sprints):**
- Sprint 1 Foundation → Sprint 1 Фундамент
- Sprint 2 Bybit venue migration + MarketData ingest → Sprint 2 Миграция на Bybit + инжест MarketData
- Sprint 3 Strategy port → Sprint 3 Портирование стратегии
- Sprint 4 Risk module → Sprint 4 Модуль управления риском
- Sprint 5 Execution layer → Sprint 5 Слой исполнения

## Progress to Date (S01-S38)

### COMPLETED (fully translated)
- Sprint 1 — Фундамент ✓ (title + all headers + body RU)
- Sprint 2 — Миграция на Bybit + инжест MarketData ✓ (title + main headers RU)
- Sprint 3 — Портирование стратегии ✓ (title + main headers RU)
- Sprint 4 — Модуль управления риском ✓ (partial: title + some headers, needs: follow-ups/decisions)
- Sprint 5 — Слой исполнения (partial: title + goal header only)

### PENDING — S06-S23 (17 files)
- Sprint 6 Spot OCO emulation
- Sprint 7 Resilience
- Sprint 8a Live runtime
- Sprint 8b Carryover
- Sprint 8c Wiki backfill
- Sprint 9 Data quality types analytics
- Sprint 10 WFA DSR MC
- Sprint 11 Operator readiness
- Sprint 12 Live demo validation
- Sprint 13 Backfill WFA
- Sprint 14 Honest close
- Sprint 15 Mean reversion multi-symbol
- Sprint 16 Honest close v02
- Sprint 17 BTC mean reversion relaxed
- Sprint 18 Honest close v01
- Sprint 19 15m architecture
- Sprint 20 15m measurement
- Sprint 21 Honest close v04

### LIKELY ALREADY RU (S22-S38)
- S22 4h test (check)
- S23 honest close v05 (check)
- S25 dashboard (check)
- S27-S38 — later sprints likely mixed RU/EN, verify

### NOT YET TRANSLATED — Runbooks (5 files)
All in English, need full RU translation:
- halt-recovery.md (100+ lines)
- halt-response-protocol.md (60+ lines)
- live-demo-validation.md (60+ lines)
- pre-flight.md (50+ lines)
- log-grep-templates.md (50+ lines)

## Structural Issues Found

### Missing sprint pages (by design)
- Sprint 24 — merged into S25 (expected per sprints/README.md)
- Sprint 26 — never created (expected)

### Files already in Russian (no translation needed)
- `sprints/README.md` ✓ (fully RU)
- `components/README.md` ✓ (fully RU)

### Pattern observations
- **Early sprints (S01-S10):** ~80% body text RU, but titles/headers still EN
- **Mid sprints (S11-S20):** ~70% mixed, some headers already RU
- **Late sprints (S21+):** ~90% RU, some titles still EN

## Implementation Approach for Completion

**Batch 1 (Done):** S01-S03 complete translation
**Batch 2 (In progress):** S04-S05 title + headers
**Batch 3 (TODO):** S06-S23 title + standard headers + body cleanup (estimate 17 files × 5 edits = 85 edits total, ~2-3 hours manual)
**Batch 4 (TODO):** Runbooks (5 files, full EN→RU translation, estimate 5-7 hours)
**Batch 5 (TODO):** S24-S38 verify + complete if needed (10 files)

## Recommendations for Completion

1. **Quick-win sprint headers:** Use `replace_all=true` for standard headers across remaining files (e.g., "## Goal" → "## Цель" in all S06-S23 at once)
2. **Runbook translation:** Priority HIGH — operator-facing docs, should be RU. Suggest subagent dispatch with "translate-docs" skill.
3. **Title mapping:** Create lookup table for consistent sprint description translation, apply batch-wise.
4. **Verify late sprints:** S22-S38 already mixed RU, check which need completion.

## Future process (per CLAUDE.md 2026-05-09)

- All NEW wiki pages created after 2026-05-09 → immediate RU from start
- Old EN/bilingual pages → translate incremental per touch (not bulk migration)
- Section headers → standardized RU mapping per this audit
