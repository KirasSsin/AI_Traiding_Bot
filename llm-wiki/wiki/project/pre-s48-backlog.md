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

### Bug A — EquityChart cursor tooltip всегда +% + динамический баланс (REVISED 2026-05-11)

Tooltip shows "+X.XX%" даже когда total PnL негативный (-13.46 USDT). T14 (S47) hook reads `equity_pct[idx]` напрямую — либо backend emits cumulative-positive only, либо sign logic broken.

**Operator extended scope 2026-05-11:** при наведении на конкретную дату (например 2023, 5 марта) показывать в tooltip:
1. Процент earnings/loss на эту точку (с правильным знаком)
2. **Итоговая сумма USDT** на эту точку (initial_balance × (1 + equity_pct/100)) — динамически обновляется в отдельном месте на странице, аккуратно числом, в стилистике дизайна

**Diagnose:** check actual `equity_curve.equity_pct` payload для FAIL preset. Likely backend computes cumulative starting from 0 с positive bias, не reflecting actual losses.

**Fix scope:** medium (2-3 задачи: tooltip sign fix + dynamic balance display panel)

### Bug B — EquityChart рендерится только на research presets

Chart visible на atr_breakout + volume_breakout (research presets). Legacy WFA path (ema_crossover_s13 / mean_reversion_s15 / mean_reversion_s17_relaxed / donchian_breakout_s35) — chart placeholder "No equity data".

**Root cause:** replay engine (`src/dashboard/backtest_runner.py:1117`) не emits `equity_curve.timestamps` + `equity_pct` arrays. Только research_runner_envelope path emits.

**Fix scope:** medium (2-3 задачи: backend equity_curve emission в replay engine + tests)

### Bug C — TradesTable нет initial/final balance (REVISED 2026-05-11)

Operator wants `$X → $Y` визуализацию.

**Operator extended scope 2026-05-11:** НЕ фиксированные $10000. Подключаемся к Bybit API (умеем уже), запрашиваем текущий баланс оператора, используем как initial balance для backtest. Тестируем стратегию "как будто это 2023 год" но на реальной сумме баланса.

**Реализация:**
1. Backend endpoint `/api/account/balance` → возвращает current Bybit account balance (USDT). Использует existing pybit V5 API integration.
2. Frontend на загрузке формы fetches balance, отображает как initial_balance в форме (read-only OR editable override).
3. POST `/api/backtest` payload включает `initial_balance: <value>` (default = fetched OR override).
4. Envelope `trade_stats` дополняется `initial_balance_quote` + `final_balance_quote` (computed from total_pnl_pct).
5. TradesTable показывает 2 строки: Initial Balance / Final Balance.

**Безопасность:** balance fetch требует bybit API keys (testnet OR mainnet). Per ADR 0017 + security-auditor review при PHASE 6. Read-only operation (GET account info), не money-affecting.

**Fix scope:** medium-large (4-5 задач: backend endpoint + auth handling + frontend fetch + form integration + envelope/render)

### Bug D — Informational criteria (T1/T2/T4/T6) показаны как FAIL chips

Per ADR 0014 + quant-stats-reviewer S47 PHASE 6: T1-T6 informational, gate cascade использует только fold OOS/IS ≥ 0.7 + MC p ≤ 0.05 + optional t5_floor + n_eff_threshold. Operator confused: "почему informational T1=FAIL влияет?" (хоть и не).

**Fix:** visual distinction в MetricsTable:
- Gate-blocking criteria (T5 floor / T6 OOS-IS / DSR / MC): full FAIL/PASS chip с red/green
- Informational criteria (T1/T2/T3/T4): dimmed OR strikethrough OR collapsed-by-default (operator expand если хочет)
- Add UX label "informational only — does NOT affect verdict"

**Fix scope:** small (2 задачи)

### Bug E — Расшифровка warnings + НОВАЯ вкладка Glossary (REVISED 2026-05-11)

Currently warnings shows terse warning code + 1-line message. Operator hard к interpret без знания internals.

Example actual: `mc_noise: MC permutation p=0.756 > 0.10 — returns indistinguishable от random.`

**Operator extended scope 2026-05-11 — основное расширение S48:**

Создать **отдельную новую вкладку "Glossary" / "Расшифровка"** где вынести структурированно ВСЕ аббревиатуры/символы/метрики/значения которые показаны на главной странице. Структура соответствует последовательности блоков на главной странице.

**Вкладка содержит:**
1. Расшифровка верхних аббревиатур (T1, T2, T3, T4, T5, T6, DSR, MC) — что измеряет, как читать значение, что значит PASS/FAIL для оператора
2. Расшифровка финальных метрик (PnL, Win rate, Profit Factor, Avg Win, Avg Loss, Total Commissions) — на русском языке
3. Расшифровка warnings (mc_noise, low_sample, raw_full_period, etc.) — почему возникает, что значит, что делать
4. Расшифровка иконок/символов (▸ ▲ ⚠ ✓ ✗) — что обозначают
5. Любые другие технические значения с главной страницы

**Динамическое поведение (CRITICAL UX feature):**
- При выборе конкретной стратегии в выпадающем списке на главной вкладке → на Glossary вкладке **подсвечиваются (либо выделяются отдельным блоком)** только те параметры которые используются в выбранной стратегии. Остальные dimmed/collapsed.
- Решение по визуализации (подсветка vs separate block) — на frontend-developer agent в дизайн-сессии.

**Связь с Bug F:** этот glossary заменяет "Неизвестный критерий" на FailAnalysisTab. На главной странице оставляем только указание "используется/не используется", детали смотрим в Glossary.

**Fix scope:** large (5-6 задач: новая вкладка + backend dict с расшифровками всех значений + endpoint + dynamic per-strategy filter + frontend GlossaryTab + integration с главной)

### Bug F — Удалить "Неизвестный критерий", использовать/не использует indicator (REVISED 2026-05-11)

S47 T15 BUG: FailAnalysisTab пишет "Неизвестный критерий: t1/t2/...". 3-way ID mismatch (replay path / research walk_forward / frontend dict — все разные ключи).

**Operator decision 2026-05-11:** убрать показ "Неизвестный критерий" полностью. Глубокая расшифровка переехала в новую вкладку Glossary (Bug E).

**На главной странице (FailAnalysisTab):**
- Оставить только короткое указание "используется / не используется" для каждого критерия
- Если оператор хочет узнать детали — открывает Glossary вкладку (там динамическая подсветка под выбранную стратегию)

**Fix scope:** small (2 задачи: backend canonical key alignment + FailAnalysisTab упрощение к "used/not used" indicator)

### Bug G — DocumentationTab убрать misleading triangle icon (REVISED 2026-05-11)

Visual hint (треугольник ▸ смотрит вправо) триггерит ожидание раскрытия, но cards не раскрываются.

**Operator decision 2026-05-11:** НЕ делать раскрытие. Просто убрать треугольник или заменить на нейтральный символ (точка •, тире — , bullet) чтобы визуально не намекало на раскрывающийся элемент. Это просто блок текста, не expandable list.

**Fix scope:** tiny (1 задача — заменить ▸ в DocumentationTab cards)

### Bug H — HistoryTab per-row expand с RU summary (FINALIZED 2026-05-11)

Каждая запись в HistoryTab → click → expand с полным набором данных:
- **Краткая причинно-следственная RU summary** (~2-3 предложения) почему стратегия сработала / не сработала (статический шаблон)
- **Начальный баланс** (initial_balance_quote) + **итоговый баланс** (final_balance_quote)
- **Total PnL** (USDT)
- **Win rate** (%)
- **Lose rate** (%) (= 100 - win_rate)
- **Profit Factor**
- НЕ включать график (избыточно — дублирует main view)
- НЕ включать полный metrics narrative (только числа)

**Implementation:**
- Per-row click handler → toggle expanded state
- Lazy load `/api/runs/{run_id}` on expand (не widening list endpoint, KISS per ESC-2 α)
- RU summary generation = static template: "Стратегия [verdict] потому что [primary failed criterion human-readable] (фактически: [actual] vs порог [threshold])"

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

## Carry-overs from S47 PHASE 6 (deferred к S49 per split decision)

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

## S48 scope estimate (FINAL — split decision applied)

| Блок | Содержимое | Задачи |
|---|---|---|
| **A** Критические функциональные баги | F (FailAnalysisTab упрощение к used/not used) + B (chart на всех стратегиях) + G (убрать треугольник) + H (HistoryTab expand с balance/winrate/PnL) | 6-8 |
| **B** UX баги | A (tooltip знак + динамический баланс) + C (Bybit balance integration) + D (informational vs gate-blocking) + I (RU language enforcement) | 9-11 |
| **C** Glossary вкладка (НОВАЯ — расширение Bug E) | Новая страница + backend dict + dynamic per-strategy filter + frontend GlossaryTab | 5-6 |
| **TOTAL S48** | | **~20-25 задач** |

Косметика + a11y minimum + S47 carry-overs → **S49** (operator buffer).

## Roadmap (FINAL 2026-05-11 evening — operator decision split S48+S49+S50)

- **S48** = 9 жалоб оператора + Bybit balance integration + НОВАЯ Glossary вкладка (~22 задачи)
- **S49** = косметика (цвета/шрифты/spacing/states/a11y minimum) + S47 carry-overs + что добавится после оператора test S48 (гибкий буфер ~10-15 задач)
- **S50** = NEW strategies (Path B activation, deferred 2 sprints от первоначального pivot)

Operator binding: "S49 оставить маленьким, я посмотрю результат S48, добавлю если что-то будет".

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
