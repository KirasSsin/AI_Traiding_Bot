---
title: Pre-S48 Backlog — UI Overhaul + bug fixes (NEW strategies → S49)
type: backlog
tags: [sprint-48, ui-overhaul, ui-ux-redesign, bug-fixes, dashboard, fail-analysis-tab]
created: 2026-05-11
updated: 2026-05-11
status: active
sources:
  - llm-wiki/wiki/project/SPRINT_STATE.md
  - llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md
---

# Pre-S48 Backlog

## Контекст

S47 SHIPPED (`v0.1.0-alpha.47`). Operator manual UI test 2026-05-11 surfaced 8 bugs/features across dashboard. Ранее operator pivot 2026-05-11 был "S48 = NEW strategies (Path B rejoin)". **Pivot REVISED 2026-05-11 evening:**

- **S48 = UI Overhaul + bug fixes** (this backlog)
- **S49 = NEW strategies** (deferred 1 sprint)

Rationale: working UI = prerequisite для strategy validation. Без него operator blind. NEW strategies deserve good visualization tools.

## Operator-surfaced bugs (8 total)

### Bug A — EquityChart cursor tooltip всегда +%

Tooltip shows "+X.XX%" даже когда total PnL негативный (-13.46 USDT). T14 (S47) hook reads `equity_pct[idx]` напрямую — либо backend emits cumulative-positive only, либо sign logic broken.

**Diagnose:** check actual `equity_curve.equity_pct` payload для FAIL preset. Likely backend computes cumulative starting from 0 with positive bias, не reflecting actual losses. Need verify ground truth.

**Fix scope:** small (1-2 задачи)

### Bug B — EquityChart рендерится только на research presets

Chart visible на atr_breakout + volume_breakout (research presets). Legacy WFA path (ema_crossover_s13 / mean_reversion_s15 / mean_reversion_s17_relaxed / donchian_breakout_s35) — chart placeholder "No equity data".

**Root cause:** replay engine (`src/dashboard/backtest_runner.py:1117`) не emits `equity_curve.timestamps` + `equity_pct` arrays. Только research_runner_envelope path emits.

**Fix scope:** medium (2-3 задачи: backend equity_curve emission в replay engine + tests)

### Bug C — TradesTable нет initial/final balance

Operator wants `$10000 → $X.XX` визуализацию. Сейчас только "Total PnL" в USDT. Не понятно итоговая сумма capital.

**Fix:** envelope add `initial_balance_quote` + `final_balance_quote` fields. TradesTable add 2 rows. Available for both RAW + WFA paths (compute from total_pnl_pct если quote-currency недоступно).

**Fix scope:** small (2 задачи)

### Bug D — Informational criteria (T1/T2/T4/T6) показаны как FAIL chips

Per ADR 0014 + quant-stats-reviewer S47 PHASE 6: T1-T6 informational, gate cascade использует только fold OOS/IS ≥ 0.7 + MC p ≤ 0.05 + optional t5_floor + n_eff_threshold. Operator confused: "почему informational T1=FAIL влияет?" (хоть и не).

**Fix:** visual distinction в MetricsTable:
- Gate-blocking criteria (T5 floor / T6 OOS-IS / DSR / MC): full FAIL/PASS chip с red/green
- Informational criteria (T1/T2/T3/T4): dimmed OR strikethrough OR collapsed-by-default (operator expand если хочет)
- Add UX label "informational only — does NOT affect verdict"

**Fix scope:** small (2 задачи)

### Bug E — WARNINGS block лаконичный, нужна расшифровка

Currently shows terse warning code + 1-line message. Operator hard к interpret без знания internals.

Example actual: `mc_noise: MC permutation p=0.756 > 0.10 — returns indistinguishable от random.`

**Fix:** rich expanded warning panel — per warning code add:
- Что значит
- Что делать оператору
- Cross-reference к criterion explanation если applicable
- Severity icon + color coding

Source contents: NEW `src/dashboard/warning_explanations.py` dict of warning_code → expanded explanation.

**Fix scope:** medium (3 задачи: backend dict + endpoint + frontend rich render)

### Bug F — CRITICAL FailAnalysisTab "Неизвестный критерий: t1"

S47 T15 BUG. `failed_criteria` от backend = `['t1','t2','t4','t5','t6']` (short keys). `wfa_criterion_explanations.py` keys = `t1_sharpe_oos`, `t2_sortino_oos`, `t3_max_drawdown`, etc. Lookup miss → renders "Неизвестный критерий" для every failed criterion. **FailAnalysisTab functionally broken.**

**Fix:** ID mapping. Either:
- (a) Rename criterionMap keys к `t1` / `t2` / etc.
- (b) Add `SHORT_TO_FULL_CRITERION_KEY` mapping в FailAnalysisTab.tsx
- (c) Backend `failed_criteria` array uses long keys (canonical alignment)

Maintainer rec: (c) backend canonical alignment — fix at source. Update WFA gate evaluation к emit long keys.

**Fix scope:** tiny (1 задача — backend rename) OR small (2 задачи если frontend mapping fallback)

### Bug G — DocumentationTab cards не collapsible

Visual hint показывает expandable, но click не работает. Add expand/collapse функционал per card (indicator / multiplier / strategy / methodology).

**Fix:** add useState collapsed boolean per card + onClick handler + CSS transition. Default collapsed после initial render (или operator preference via localStorage).

**Fix scope:** small (1-2 задачи)

### Bug H — HistoryTab per-row expand с RU summary

Operator request: каждая запись в HistoryTab → click → expand с:
- **Краткая причинно-следственная RU summary** (~2-3 sentences) почему стратегия сработала / не сработала
- Initial balance + final balance
- Кол-во сделок
- % winners / % losers
- НЕ включать график (избыточно — дублирует main view)
- НЕ включать full metrics narrative (кратко only)

**Implementation:**
- Per-row click handler → toggle expanded state
- Backend NEW endpoint `/api/runs/{run_id}/summary` OR derive from existing `/api/runs/{run_id}` BacktestResponse
- RU summary generation logic — option (a) static template based on verdict + failed_criteria; option (b) deeper derivation от metrics
- Maintainer rec: (a) — простой template "Стратегия [verdict] потому что [primary failed criterion human-readable] (фактически: [actual] vs порог [threshold])"

**Fix scope:** medium (3-4 задачи)

## UI/UX best-practices redesign (operator request)

В дополнение к bug fixes, complete UI overhaul per dashboard design best practices. Scope items:

1. **Visual hierarchy** — primary verdict / metrics / charts визуально разделены, не "all same weight"
2. **Information density tuning** — dense data tables vs spacious narrative panels
3. **Color semantics consolidation** — `--color-status-pass`, `--color-status-fail`, `--color-status-warn`, `--color-status-info` tokens (S47 PHASE 6 frontend-developer carry-over)
4. **Empty states** — when no data, what shows? Currently mix of "—" / "—" / placeholder messages.
5. **Loading states** — skeleton screens vs spinners
6. **Error states** — API failure, retry UI, error boundary fallback
7. **A11y polish** (S47 PHASE 6 carry):
   - tablist ARIA pattern (role + aria-controls + arrow-key nav)
   - `--color-text-disabled` contrast bumped (current 2.6:1 → ≥4.5:1 WCAG AA)
   - Focus visible outlines
   - Skip-to-main link
8. **Mobile responsive layout** — currently desktop-only, test viewport 320-768px
9. **Spacing / typography polish** — vertical rhythm, line-height consistency, font-size scale

**Fix scope:** medium-large (6-8 задач)

### Bug I — Соблюдение языкового паттерна в чате с оператором (NEW 2026-05-11)

Согласно `CLAUDE.md` "Language rules (BINDING — пересмотрено 2026-05-09)":

| Канал | Язык |
|---|---|
| Чат с оператором (responses, questions, sprint reports) | **Русский** |

Технические термины (file paths, code blocks, error strings, command names, library names) — оставлять как есть без перевода ВНУТРИ русского текста.

**Нарушение зафиксировано 2026-05-11 в брейнштормe S48:** ассистент писал смешанный текст с английскими словами вместо русских эквивалентов даже там, где это не технические термины:

Anti-пример (моё сообщение оператору во время S48 brainstorm):
- "Bucket A" → должно быть "Блок A" / "Группа задач A"
- "scope" → "объём" / "охват"
- "tasks" → "задачи"
- "Recommended" → "Рекомендация"
- "concern" → "замечание"
- "blocker" → "блокер" (можно оставить — устоявшийся термин) ИЛИ "блокирующая проблема"
- "verdict" → "вердикт" (можно оставить — закрепился в проекте)
- "ROUND 2 BINDING" → "РАУНД 2 (обязательный)"

Технические термины оставить:
- `MetricsTable.tsx`, `wfa_criterion_explanations.py`, ADR номера, имена функций, exit codes
- Канонические термины проекта: ADR, PHASE, BLOCKER, WFA, DSR, MC

**Задача:** добавить в `CLAUDE.md` явный список запрещённых англицизмов + русских эквивалентов. Использовать сообщение выше как anti-пример в anti-patterns секции.

**Fix scope:** маленькая (1 задача — обновить CLAUDE.md языковую секцию + добавить в anti-patterns)

## Carry-overs from S47 PHASE 6 (deferred to S48)

- Vitest tests #4 (computeMonthlyData property) + #5 (VerdictPanel mapping)
- README npm install note
- F8 block_size constant unification (quant LOW)
- MonthlyHeatmap eslint cleanup (cosmetic)
- Item #7 RiskSharedDeps shim cleanup
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended boundary scenarios
- BacktestResponse.metrics typing tighten к `Record<string, number | null>`
- mean_reversion S15/S17 LONG-only clarification в strategy_descriptions.py
- BybitAdapterError structured context attribute
- Empty trades_list test pin (data-integrity carry)
- FailAnalysisTab + VerdictPanel RTL render tests
- 5 missing preset descriptions (если 11 expected — verify)
- Wiki narrative cleanup (sprint-47 page lines 71+93+148 ReasonCode attribution)
- onChartReady deprecation comment

## S48 scope estimate

| Bucket | Items | Tasks |
|---|---|---|
| **A** Critical bugs | F (FailAnalysisTab ID broken) + B (chart coverage) + G (Doc collapse) + H (History expand) | 7-8 |
| **B** UX bugs | A (tooltip sign) + C (initial/final balance) + D (informational distinction) + E (warnings expand) | 8-10 |
| **C** UI/UX redesign | hierarchy / colors / a11y / mobile / typography / states | 6-8 |
| **D** S47 carry-overs | tests / typing / cleanup | 4-5 |
| **TOTAL** | | **25-31 tasks** |

**Big sprint.** Could split к S48 (Bucket A+B critical) + S49 mini (Bucket C+D polish), но operator preference unknown. Discuss в brainstorm.

## Roadmap (locked 2026-05-11 evening)

- **S48** = UI Overhaul + bug fixes (this backlog)
- **S49** = NEW strategies (Path B activation, deferred 1 sprint от prior pivot)
- **S50+** = TBD (depends на S49 outcome)

## Brainstorm questions for trader-expert (PHASE 2 trigger)

When operator says "S48 brainstorm" / `brainstorm-init` skill:

- Q1: Bucket priority order — critical bugs first, OR UX redesign first, OR mixed?
- Q2: S48 task count — full 25-31 OR split к S48+S49 (UI critical + UI polish + NEW strategies)?
- Q3: HistoryTab summary generation — static template (cheap, fast) vs LLM-derived (richer, but cost + latency)?
- Q4: Mobile responsive — full implementation OR defer (operator desktop-only currently)?
- Q5: A11y polish — full WCAG AA pass OR minimum (color contrast + tablist ARIA only)?

## Files identified для PHASE 3 plan input

CREATE:
- `src/dashboard/warning_explanations.py` (Bug E backend)
- `src/dashboard_react/src/components/HistoryRowExpand.tsx` (Bug H expand panel)
- `src/dashboard_react/src/components/HistoryRowExpand.module.css`

MODIFY frontend:
- `src/dashboard_react/src/components/EquityChart.tsx` — Bug A (tooltip sign verification)
- `src/dashboard_react/src/components/MetricsTable.tsx` — Bug D (informational distinction)
- `src/dashboard_react/src/components/TradesTable.tsx` — Bug C (initial/final balance rows)
- `src/dashboard_react/src/components/VerdictPanel.tsx` — Bug E (warnings rich render)
- `src/dashboard_react/src/components/FailAnalysisTab.tsx` — Bug F (ID mapping fix OR backend canonical)
- `src/dashboard_react/src/components/DocumentationTab.tsx` — Bug G (collapsible cards)
- `src/dashboard_react/src/components/HistoryTab.tsx` — Bug H (per-row expand wire)
- `src/dashboard_react/src/styles/tokens.css` — color tokens consolidation
- `src/dashboard_react/src/App.module.css` — visual hierarchy + spacing

MODIFY backend:
- `src/dashboard/app.py` — NEW endpoints для warning_explanations + history summary
- `src/dashboard/backtest_runner.py` — Bug B (replay engine equity_curve emission)
- `src/backtest/research_runner_envelope.py` — Bug C (initial/final balance fields)
- `src/dashboard/wfa_criterion_explanations.py` — Bug D (mark informational)
- WFA gate evaluation — Bug F (canonical key alignment if path c)

CREATE wiki:
- `llm-wiki/wiki/project/sprints/sprint-48-ui-overhaul.md` (PHASE 8)

MODIFY wiki:
- `llm-wiki/wiki/project/architecture/current-state.md` — header + counts + sprint history row
- `llm-wiki/wiki/index.md` — sprint-48 entry
- `llm-wiki/wiki/log.md` — S48 sprint-end entry

## Next phase

PHASE 1 orient + PHASE 2 brainstorm — operator triggers с "S48 brainstorm" / `brainstorm-init` skill. Backlog (this file) = input contextual material.
