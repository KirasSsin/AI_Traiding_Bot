---
title: Pre-S49 Backlog — carry-overs + post-S48 buffer
type: backlog
tags: [pre-sprint, backlog, s49, carry-overs]
created: 2026-05-11
updated: 2026-05-11
status: draft
sources:
  - llm-wiki/wiki/project/SPRINT_STATE.md
  - llm-wiki/wiki/project/sprints/sprint-48-ui-overhaul.md
  - llm-wiki/wiki/project/pre-s48-backlog.md
---

## Назначение

Carry-overs из S48 PHASE 6 reviews + S47 carry-overs + post-S48 operator feedback buffer. Источник scope для S49 brainstorm.

## Bucket A — S48 PHASE 6 carry-overs (приоритетные)

### A1. T3 verdict semantic — backend vs ADR 0014 mismatch (HIGH, trading-logic BLOCKER B2 deferred)

**Симптом:** `src/dashboard/backtest_runner.py:1027` включает `"t3"` в `failed_criteria` при DD ≥ 25%. ADR 0014 + MetricsTable UI декларируют T3 informational. Verdict logic line 1048 (`verdict = "PASS" if not failed_criteria`) силит T3 как gate-blocking, скрытно противоречит UI представлению.

**Resolution options:**
- (a) Backend exclude T3 из `failed_criteria` computation (matches ADR + UI)
- (b) Update ADR 0014 declaring T3 gate-blocking (matches code)

**Required:** trader-expert ROUND 1 verdict. Pre-existing bug surfaced S48 UI work made it visible.

### A2. `final_balance_quote` additive vs compounded (MEDIUM, data-integrity C1)

`src/dashboard/backtest_runner.py:1142` — `_running_pct` суммирует per-trade `pnl_pct` linearly. Не compounded equity. Для large PnL (e.g. +122%) gap material. Display only — но misleading vs research-path equity curve. Fix: либо compute из replay engine final equity, либо relabel field.

### A3. Bybit balance TTL cache (MEDIUM, bybit-api + security)

`/api/bybit/balance` без rate limit. Frontend manual refresh + mount fetch. Operator может polling — Bybit V5 120 req/min global. Fix: 30s server-side cache.

### A4. RunRecord backward-compat (MEDIUM, data-integrity C3)

Старые cached runs до T7 lack `trade_stats.win_rate`, `initial_balance_quote`, `final_balance_quote`, `equity_curve`. Python callers must `.get()` defaults. Document в `components/backtest-runner.md` OR bump cache version.

### A5. useStrategyContext multi-instance sync (MEDIUM, frontend-developer)

`replaceState` не dispatches `popstate` → multi-mounted hook instances diverge. Current arch safe (только ConfigureBacktest writes, GlossaryTab reads on mount). Latent bug.

### A6. FailAnalysisTab glossary anchor verification (LOW, frontend-developer)

`#glossary-${critId}` anchor consistency depends на backend glossary `term` keys matching `critId` strings (e.g. `t5_floor`). Integration-time assumption.

### A7. App.tsx version string stale (LOW, frontend-developer)

Header показывает `v0.1.0-alpha.46`. Update к `v0.1.0-alpha.48` OR auto-derive.

### A8. GlossaryTab `console.warn` production path (LOW, frontend-developer)

Suppress OR debug-mode only.

### A9. Test coverage gaps LOW (test-engineer)

- GlossaryTab RTL filter/search/empty-query behavior
- BalanceBadge snapshot/RTL
- glossary_data property test (struct invariants)
- `equity_curve` empty-list edge case unit test

## Bucket B — Bug I post-S48 monitoring

Operator surfaced в S48: assistant violates RU language pattern в operator chat (англицизмы). T23 added CLAUDE.md anti-pattern table. Post-S48 verification: проверить compliance в S49 brainstorm responses.

## Bucket C — S47 carry-overs (не закрытые)

Из `pre-s48-backlog.md` Bucket E carries:
- Vitest tests #4-#5 (S47 deferred)
- README npm dashboard section
- F8 wfa_criterion_explanations.py — review naming/structure
- Item #7 + #10 (S47 lower-priority items — needs lookup)
- MonthlyHeatmap eslint cleanup
- Backend typing tightening (BybitAdapterError etc.)

## Bucket D — Cosmetic polish (operator binding S48 brainstorm Q1)

- Color tokens consolidation (`var(--color-success)` etc — verify consistent palette)
- Typography rhythm
- Spacing tokens
- State styles (hover/focus/active)
- A11y minimum (WCAG AA contrast bump для `--color-text-disabled`, tablist ARIA pattern)

## Bucket E — Post-S48 operator feedback buffer

Reserved. Operator добавит items после ручного тестирования S48 ship.

## Open questions для S49 brainstorm

1. A1 T3 verdict — option (a) backend fix OR (b) ADR update? Trader-expert verdict needed.
2. S49 scope size — 10-15 polish tasks OR allow expansion если operator surface больше bugs?
3. A2 final_balance_quote — fix now (S49) OR defer к когда trading goes live (no operator impact UI-only display)?
4. Bucket D a11y — minimum (color contrast + tablist) OR full WCAG AA pass?

## Related

- [[sprints/sprint-48-ui-overhaul]]
- [[pre-s48-backlog]]
- [[SPRINT_STATE]]
- [[decisions/0014-walk-forward-train2000-test500]] (для A1 T3 decision)
