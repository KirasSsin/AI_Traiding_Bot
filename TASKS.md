# TASKS.md — Obsidian Cross-Linking Sweep

**Created:** 2026-05-09
**Project:** AI Trading Bot v0.1
**Goal:** Add [[wiki-links]] between related pages so Obsidian graph is populated.
**Rules:**
- Only add `[[page-name]]` links (no .md extension, no path prefix)
- Do NOT modify existing content — only append/add links
- Do NOT touch: `project/plans/` (37 files) and `queries/` (1 file)
- Add `## Связанные документы` section at end of page if missing
- Verify target file exists before linking

---

## Tasks

- [x] **T1** — architecture-reviewer: ADR ↔ спринты ↔ архитектурные страницы ✓ DONE
  - **Result (Part B):** 14 архитектурных страниц получили ссылки на компоненты (state-machine→FSM, storage→fill-history/trade-history/bar-builder, acceptance-criteria→dsr/mc/walk/wfa, execution-timing→coordinator/bar-poller/bybit-adapter, domain-events→coordinator/runtime-manager/ws-private-consumer, risk-register→halt-gate/circuit-breakers/risk-manager, development-workflow→sprint-flow-ru/kit-overview-ru/tooling-inventory-ru, current-state→execution-state-machine/acceptance-criteria, reason-codes-schema→execution-state-machine/halt-gate, stack-v0.1→config/models/logging, bounded-contexts→coordinator/runtime-manager/bar-builder/risk-manager, edge-cases→halt-gate/data-quality/bar-builder). 20+ компонентных страниц получили обратные ссылки на архитектурные.
- [x] **T2** — doc-reviewer: orphan-страницы без входящих ссылок ✓ DONE
  - **Result:** 1 реальный orphan найден: `mental-map.md` (создан S31, не был в index.md). Исправлен: добавлен `[[project/mental-map]]` в index.md + Связанные в mental-map.md. Все остальные страницы имеют входящие ссылки через index.md.
- [x] **T3** — trader-expert: методология ↔ ADR ↔ спринты ✓ DONE
  - **Result:** 18 backlog файлов обновлены (sprint+ADR ссылки); reverse links в sprint-08c и sprint-12 добавлены; sprint-36/38 plain-text → wiki-links конвертированы. pre-s25 уже имел ссылки — пропущен.
- [x] **T4** — trading-logic-reviewer: компоненты ↔ спринты ↔ ADR + trading/ → компоненты ✓ DONE
  - **Result:** Part C (inter-component): 13 пар двусторонних ссылок (coordinator↔risk-manager, halt-gate↔halt-gate-wireup, backtest↔walk/dsr/mc, strategy↔donchian, bar-builder↔bar-poller, etc.). Part B: 13 trading pages — секции "## Реализация" с ссылками на компоненты. Part A: runtime-manager/risk-override/data-quality/config/logging/kill-switch-cli/trade-history/hooks получили sprint+ADR ссылки; ADRs 0011/12/13/16/21/22/23/28/53/54/55 + sprints 11/35/36 получили обратные ссылки на компоненты.
- [x] **T5a** — обновить index.md + log.md ✓ DONE
  - index.md: mental-map добавлен (T2 сделал); updated date уже 2026-05-09
  - log.md: audit entry appended — ~200+ links, 4 агента
- [x] **T5b** — git commit ✓ DONE

---

## Execution Log

| Task | Agent | Status | Links Added | Notes |
|------|-------|--------|-------------|-------|
| T1 | architecture-reviewer | **DONE** | 50+ (14 arch→comp + 20+ reverse comp→arch links) | Part B complete; ADR↔sprint — частично через T3 |
| T2 | doc-reviewer | **DONE** | 2 ссылки (mental-map↔index + mental-map↔current-state) | 1 orphan resolved |
| T3 | trader-expert | **DONE** | ~40+ (18 backlogs × sprint+ADR + reverse links) | sprint-36/38 plain-text→wiki-links |
| T4 | trading-logic-reviewer | **DONE** | 100+ (13 inter-comp + 13 trading→comp + 10 comp→sprint/ADR + reverse) | Part A/B/C все выполнены |

---

## Autonomous decisions

- Sprint-24 и sprint-26 не существуют — не линковать
- ADR-0049 не существует — не линковать
- plans/ и queries/ исключены согласно правилам
- Если страница уже имеет секцию ## Связанные — добавляем в неё, не дублируем
