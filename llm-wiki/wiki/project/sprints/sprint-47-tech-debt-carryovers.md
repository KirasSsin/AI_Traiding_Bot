---
title: "Sprint 47 — Tech debt + S46 PHASE 6 carry-overs + UI bugs"
type: sprint
tags: [sprint-47, tech-debt, carry-overs, vitest, fail-analysis-tab, bybit-api]
created: 2026-05-11
updated: 2026-05-11
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0017-review-agent-harness.md
  - llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - llm-wiki/wiki/project/plans/2026-05-11-sprint-47-tech-debt-carryovers.md
  - llm-wiki/wiki/project/pre-s47-backlog.md
---

# Sprint 47 — Tech debt + S46 PHASE 6 carry-overs + UI bugs

## Обзор

Технический долг + три группы carry-overs из S46 PHASE 6 + три UI-пункта, выявленных operator'ом в ходе ручной валидации Q7 (2026-05-11). Всего 16 задач в 5 бакетах. Путь B (новые стратегии) исключён из S47 и возвращается в S48 согласно pivot'у оператора 2026-05-11. Архитектурных решений нет (S47 — чисто технический долг и баг-фиксы); новых ADR не создано.

## План + ссылки на ADR

- Plan: [[../plans/2026-05-11-sprint-47-tech-debt-carryovers]]
- Backlog (PHASE 2): [[../pre-s47-backlog]]
- ADR 0014 (acceptance gates): [[../decisions/0014-walk-forward-train2000-test500]]
- ADR 0056 (DSR sigma sourcing): [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]]
- ADR 0017 (review-agent harness): [[../decisions/0017-review-agent-harness]]
- Предыдущий спринт: [[sprint-46-react-migration]]

## Доставленная функциональность

### Код (frontend)

- **Vitest + RTL инфраструктура:** `vitest.config.ts` + `setupTests.ts` (polyfills: `localStorage`, `matchMedia`). Зависимости: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@vitest/coverage-v8`, `@vitest/ui`, `fast-check`.
- **3 unit-теста (React Testing Library):**
  - `computeDrawdown.test.ts` — 7 тестов: property-based с `fast-check` (drawdown ≤ 0, монотонность running min, peak-to-trough semantics)
  - `useWfaFailAck.test.ts` — 7 тестов: state machine localStorage (first-visit, ack-increment, chip downgrade после 3 distinct calendar days)
  - `MetricsTable.test.tsx` — 7 тестов: Bailey 2014 threshold encoding (T5 ≥ 100, missing → FAIL per ≥100 semantics)
- **Playwright E2E активирован:**
  - `backtest-flow.spec.ts` submit→verdict: активирован через `page.route('/api/backtest', ...)` mock (ранее SKIPPED в S46 — нужна была stub-фикстура)
  - `wfa-fail-ack.spec.ts`: 2 теста PASS (preserved из S46)
- **EquityChart + DrawdownSubchart cursor tooltip:** crosshair при наведении с floating label (дата + equity% / DD%). Стиль: Anthropic orange + glass-morphism. Реализован через `setCursor` hook uPlot.
- **FailAnalysisTab — детальный разбор WHY-failed (RU):** отображается только при verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}. Три секции:
  1. Полное описание стратегии (RU, ~150 слов)
  2. Разбор по критериям с формулой, порогом и impact
  3. Таблица per-fold (IS/OOS Sharpe по фолдам)
- **Честная документация в T15:**
  - 6 реальных пресетов в `STRATEGY_PRESETS` (не 11)
  - T1-T6 информационные согласно ADR 0014; каскад gate: fold OOS/IS ≥ 0.7 + MC p ≤ 0.05 + опциональный t5_floor + n_eff_threshold
  - T5_FLOOR=50 согласно S34 ADR 0052 amendment (НЕ 100)
  - MC p_threshold=0.05 согласно S34 ADR 0052 (НЕ 0.10)
  - DSR информационный; пороги ADR 0056 (n<10 INSUFFICIENT, 10≤n<30 UNDERPOWERED, n≥30 GATE_ELIGIBLE)
  - DSR Pearson kurtosis (`fisher=False`), НЕ excess kurtosis

### Код (backend)

- **SPA catch-all маршрут** в `src/dashboard/app.py`: FastAPI route `GET /{full_path:path}` → `FileResponse(dist/index.html)` для поддержки React Router (binding architect S46 MEDIUM).
- **Middleware кеширования HTTP-активов:**
  - `/assets/*` → `Cache-Control: public, max-age=31536000, immutable`
  - остальные → `Cache-Control: no-cache, no-store, must-revalidate`
- **Расширение `trade_stats` для research presets (T13 bug fix):** `research_runner_envelope` (volume_breakout + atr_breakout) обогащает поле `trade_stats` — `n_winners`/`n_losers` выводятся из знаков PnL, `avg_winner`/`avg_loser` из списков. Фикс рендеринга: `fmtMoney(null)` больше не даёт `'— USDT'`.
- **2 новых endpoint'а:**
  - `GET /api/strategy_explanation/{id}` → RU описание стратегии (6 пресетов)
  - `GET /api/wfa_criterion_explanations` → RU описание 8 WFA-критериев (формула + порог + impact)
- **`src/dashboard/strategy_descriptions.py`** — RU текст для 6 реальных пресетов.
- **`src/dashboard/wfa_criterion_explanations.py`** — RU текст для 8 WFA-критериев.

### Код (Bybit API)

- **M1 — retCode taxonomy (+1 код):** `10001 INVALID_PARAM` добавлен в `ReasonCode` enum (`src/risk/reason_codes.py`). Итого: 57 reason codes.
- **M2 — защитные хелперы:**
  - `_safe_extract_list(data, key)` — возвращает `[]` вместо KeyError/TypeError
  - `_or_empty(val)` — normalize None/missing к пустому словарю
  - `BybitAdapterError` — NEW exception class (наследник RuntimeError) для typed error surface
- **M3 — WS isinstance guard:** вместо `drop` при неожиданном типе данных — `wrap+process` семантика. Совместимость с Bybit V3 WebSocket (data может быть dict или list).

### Тесты

| Набор | Количество | Примечания |
|-------|-----------|------------|
| Vitest unit | **23** | smoke 2 + computeDrawdown 7 + useWfaFailAck 7 + MetricsTable 7 |
| Playwright E2E | **4** | 2 backtest-flow (form-render + submit→verdict mock) + 2 wfa-fail-ack |
| pytest | **1014+** | DSR property + n_trials ≥1 + sprint type trio + envelope trade_stats research path + bybit retCode taxonomy + bybit adapter response guards 9 + WS isinstance guard 10 |

### CI/CD

- **`.github/workflows/ci.yml`:** добавлен шаг Vitest перед Playwright. Последовательность: lint → mypy → pytest → **Vitest** → Playwright.

### Wiki

- `llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md` (этот файл)
- `llm-wiki/wiki/project/architecture/current-state.md` — counts reason_codes 56→57, sprint pages 50→51, строка S47 в истории спринтов
- `llm-wiki/wiki/index.md` — запись sprint-47
- `llm-wiki/wiki/log.md` — sprint-end entry S47
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=5-verify, 16/16 done

## MetricsTable T5 bug fix (детали)

**Баг:** vanilla-версия содержала `undefined < 100 → false → PASS` — то есть отсутствующие значения проходили порог T5. Это была намеренно сохранённая visual-parity с legacy.

**Fix:** теперь `n_trades === null || n_trades === undefined || n_trades < 100` → FAIL per Bailey 2014 ≥100 threshold semantics. Добавлен regression test в `MetricsTable.test.tsx`.

## Operator-surfaced bugs (Q7 manual validation 2026-05-11)

### T13 — bug: trade_stats показывал `'— USDT'` для research presets

**Root cause:** `research_runner_envelope` эмитировал минимальный `trade_stats` без `n_winners`/`n_losers`/`avg_winner`/`avg_loser`. Рендеринг: `fmtMoney(null) + ' USDT'` = `'— USDT'`.

**Fix:** `volume_breakout_runner` + `atr_breakout_runner` дополняют `trade_stats` — выводят winners/losers из знаков PnL + graceful render (`fmtUsdtCell` null-guard).

### T14 — feature: cursor crosshair с tooltip на EquityChart + DrawdownSubchart

Crosshair при наведении на график показывает floating label: дата + значение (equity% или DD%). Стиль: Anthropic orange `#cc785c` + glass-morphism blur-panel.

### T15 — feature: FailAnalysisTab — RU детальный разбор WHY-failed

Вкладка видна только при verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}. Три секции: полное RU описание стратегии + разбор каждого критерия (формула, порог, impact, actual vs threshold) + per-fold таблица IS/OOS Sharpe.

## Архитектурные изменения

**NONE.** FSM states/events/transitions без изменений. `ReasonCode` +1 enum member (INVALID_PARAM) — не архитектурное изменение. `BybitAdapterError` — typed exception class без изменений в state machine.

## Тесты / качество

- Python unit: ~1014+ (рост за счёт bybit adapter + WS isinstance + envelope trade_stats + DSR trio)
- Python integration: ~58 (unchanged)
- mypy --strict src/: 0 errors
- Vitest unit: 23
- Playwright E2E: 4 (2 backtest-flow + 2 wfa-fail-ack)
- Canonical: 16 / 30 / 74 / **57** reason_codes (T9 +1 INVALID_PARAM)

## Canonical counts (post-S47)

| Метрика | Значение |
|---------|----------|
| FSM states | **16** |
| FSM events | **30** |
| FSM transitions | **74** |
| Reason codes | **57** (T9 +1 INVALID_PARAM) |
| ADRs | **66** (без изменений — нет новых ADR в S47) |
| Sprint pages | **51** (этот файл) |
| Components | **48** (unchanged) |

## Wiki updates

- `llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md` (NEW — этот файл)
- `llm-wiki/wiki/project/architecture/current-state.md` (reason_codes 56→57 / sprint pages 50→51 / sprint history row S47)
- `llm-wiki/wiki/index.md` (sprint-47 entry)
- `llm-wiki/wiki/log.md` (S47 sprint-end entry append)
- `llm-wiki/wiki/project/SPRINT_STATE.md` (T16 done + phase=5-verify)

## Open issues для S48

- **Новые стратегии (Path B rejoin — operator pivot 2026-05-11)** — основной фокус S48
- Vitest tests #4 (`computeMonthlyData`) + #5 (`VerdictPanel` mapping) — deferred per Q4 ROUND 1
- A11y polish (tablist ARIA + `--color-text-disabled` contrast)
- README npm install note (operator first-time setup)
- F8 block_size constant unification
- MonthlyHeatmap eslint cleanup
- Item #7 RiskSharedDeps shim cleanup + Item #10 DD_MULTIDAY boundary scenarios
- **Permanentно отложено:**
  - Honest close code piece (preset `disabled: bool` + 422) — DROPPED per operator pivot 2026-05-11
  - M4 `__repr__` security redaction — defer к mainnet activation gate
  - 12mo MAINNET-promotion ADR — нет live data до S48+ strategy WFA_PASS
  - Live trade feed widget — YAGNI (0 live trades)

## Key decisions (Q1-Q7 trader verdicts)

- **Q1 CONFIRM:** Vitest + RTL инфраструктура — единственный правильный выбор для React 18 unit тестов
- **Q2 CONFIRM:** SPA catch-all + cache headers middleware — необходимы для production-grade FastAPI + Vite
- **Q3 CONFIRM_REVISE:** `__repr__` security redaction (M4) — defer к mainnet activation gate (Q5 ROUND 2)
- **Q4 CONFIRM:** MetricsTable T5 fix — Bailey 2014 ≥100 threshold, missing → FAIL
- **Q5 CONFIRM_REVISE:** DSR kurtosis fix (fisher=False Pearson vs excess) — confirmed fisher=False correct
- **Q6 CONFIRM:** `BybitAdapterError` typed exception — ясный error boundary для bybit adapter layer
- **Q7 (operator surface):** 3 items — T13 trade_stats bug / T14 cursor tooltip / T15 FailAnalysisTab — все реализованы

## PHASE 6 reviewers (матрица S47)

Согласно backlog-матрице: python-reviewer + trading-logic-reviewer + quant-stats-reviewer + bybit-api-reviewer + security-auditor (M1-M3 only) + frontend-developer + test-engineer + data-integrity + doc-reviewer. Всего 9 из 11 активных L5 reviewer-агентов.

## Связанные

- [[../plans/2026-05-11-sprint-47-tech-debt-carryovers]] — implementation plan (16 tasks)
- [[../pre-s47-backlog]] — PHASE 2 brainstorm trail + operator binding decisions
- [[../decisions/0014-walk-forward-train2000-test500]] — ADR 0014 acceptance gates (T5_FLOOR / MC p / OOS/IS)
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — ADR 0056 DSR sigma sourcing (thresholds INSUFFICIENT/UNDERPOWERED/GATE_ELIGIBLE)
- [[../decisions/0017-review-agent-harness]] — ADR 0017 review-agent harness (9 PHASE 6 reviewers)
- [[../decisions/0066-sprint-46-react-migration]] — S46 ADR (React migration — carry-overs источник)
- [[sprint-46-react-migration]] — предыдущий спринт
