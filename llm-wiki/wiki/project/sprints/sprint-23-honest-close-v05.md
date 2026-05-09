---
title: Sprint 23 — v0.5 honest close (5 hypotheses tested + T5 100 structurally unreachable insight)
type: sprint
tags: [sprint-23, honest-close-v05, no-edge-conjoint, mvp-incomplete, hypothesis-5-tested, t5-100-structurally-unreachable, regime-independent-edge, n-trials-archival]
created: 2026-04-26
updated: 2026-05-09
status: completed
sources:
  - project/decisions/0038-sprint-23-honest-close-v05.md
  - project/decisions/0037-sprint-22-4h-test.md
  - project/sprints/sprint-22-4h-test.md
  - project/sprints/sprint-21-honest-close-v04.md
---

# Sprint 23 — v0.5 honest close

## Обзор

S23 = предзапланированный honest close per ADR 0037 BINDING (сработал S22 T5 count failthrough). 5-й честный закрытый в проекте (S14+S16+S18+S21+S23). Паттерн: docs-only спринт по прецедентам.

## Вердикт

**HONEST CLOSE v0.5** — 5 гипотез проверено на 4.81y BTC Bybit Spot, все FAIL conjoint согласно acceptance-criteria.md.

### 5 проверенных гипотез

| # | Hypothesis | Sprint | Trades | Verdict |
|---|-----------|--------|--------|---------|
| 1 | EMA crossover 1H | S13 | 20 | FAIL T1+T2+T4+T5 |
| 2 | Mean-reversion multi-symbol 1H | S15 | 108 | FAIL T6+MC+DSR |
| 3 | Mean-reversion BTC-only relaxed 1H | S17 | 59 | FAIL T5 count, **5/6+DSR+MC PASS** |
| 4 | Mean-reversion BTC-only relaxed 15M | S20 | 73 | FAIL T1+T2+T4+T5+T6 |
| 5 | Mean-reversion BTC-only relaxed 4H | S22 | 62 | FAIL T5 count, **5/6+DSR+MC PASS** |

### Критические научные выводы (институциональные знания v0.5)

#### Вывод 1 — T5 100 структурно недостижим для BTC-only mean-reversion

3 timeframes tested = ~60-73 trades all:
- S17 BTC 1H: 59 trades
- S20 BTC 15M: 73 trades
- S22 BTC 4H: 62 trades

**FLAT-only ограничение + AND-gate доминируют над числом сделок, а не raw signal frequency.** T5 100 достижим только через мультисимвольную агрегацию (S15 108 сделок) — вне MVP пользователя.

**Следствие:** Single-symbol BTC mean-reversion + T5 floor 100 = математически несовместимы. Требуется либо поправка scope MVP, либо смена класса стратегии для conjoint pass.

#### Вывод 2 — Edge стратегии режимо-НЕЗАВИСИМЫЙ (S17+S22)

Повторяющийся паттерн 5/6+DSR+MC PASS на 1H И 4H:
- S17 1H: T1=25.99, DSR=1.0, MC p=0.01
- S22 4H: T1=6.17, DSR=0.996, MC p=0.018

Edge стратегии стабилен в диапазоне 1H-4H. НЕ привязан к таймфрейму. Ограничен FLAT-only ограничением, а не качеством сигнала. **Суммарно ~120 сделок** (S17 59 + S22 62) потенциально подходит для small-sample ML (v0.6-A).

#### Вывод 3 — Частичная валидация Hudson & Urquhart 2021

- 15M (S20): деградация (T1=-45.57) — гипотеза Hudson & Urquhart 2021 ПОДТВЕРЖДЕНА для sub-hourly
- 4H (S22): стабильный PASS (T1=6.17, аналогично 1H S17 25.99) — гипотеза "lower frequencies better" НЕ эмпирически поддержана в диапазоне 1H-4H для BTC mean-reversion

#### Вывод 4 — Частотный зонд T0 оправдал себя (archicture-mandated)

Архитектурно обязательный частотный зонд S22 (439 raw triggers) предотвратил обязательство спринта без валидации. Улучшение шаблона архитектурного ревью: включить grep для всех использований `interval_label_map` (5-я карта была пропущена).

## Ссылки на план / ADR

- [[../decisions/0038-sprint-23-honest-close-v05]] — Sprint 23 ADR (v0.5 honest close)
- [[../decisions/0037-sprint-22-4h-test]] — S22 ADR (FAIL trigger)
- [[sprint-22-4h-test]] — predecessor (S22 4H test verdict)
- [[sprint-21-honest-close-v04]] — S21 v0.4 honest close (precedent)
- [[sprint-18-honest-close-v01]] — S18 v0.1 honest close (precedent)
- [[sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent)
- [[sprint-14-honest-close]] — S14 first honest close (precedent pattern)

## Результаты

| Task | Status | Description |
|------|--------|-------------|
| T1 | ✅ DONE | ADR 0038 accepted |
| T2 | ✅ This commit | sprint-23 page |
| T3 | ✅ DONE | cross_trial_sharpes.json → _v0.5-final.json archival + reset к [] для v0.6 (4-th archival) |
| T4 | ✅ This commit | wiki sync |
| T5 | ✅ This commit | log.md sprint-end |
| T6 | ✅ This commit | SPRINT_STATE → between-sprints, tag alpha.23 |
| T7 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.23) |

## Рост FSM

НЕТ. S23 = документация + политика архивирования. Счётчики не изменились: **16/30/74/45**.

## Рост reason codes

НЕТ.

## Тесты / качество

НЕТ изменений кода:
- pytest unit: 732 passed (S22 baseline preserved)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

## Состояние cross-trial DSR (после S22, до архивирования S23)

```json
{"trials": [{"sprint": 22, "oos_sharpe": 2.96}]}
```

S23 T3 archives к `data/cross_trial_sharpes_v0.5-final.json` + resets `data/cross_trial_sharpes.json` к `{"trials": []}` для v0.6 fresh-start (4-th archival, mirrors S16/S18/S21).

## Обновления wiki

- 1 NEW ADR (0038 — accepted)
- 1 NEW sprint page (this — sprint-23-honest-close-v05)
- Modified: current-state.md (TL;DR + S23 row + counts ADR 37→38, sprint pages 24→25), index.md, log.md, SPRINT_STATE
- Archival: data/cross_trial_sharpes.json → data/cross_trial_sharpes_v0.5-final.json + reset

## Опции направления v0.6+ (выбор оператора, без обязательств)

- **(v0.6-A) Hybrid mean-reversion + ML XGBoost** — combined S17+S22 ~120 trades (vs n=59 alone trader-rejected). CPCV viable. 5-10 sprints.
- **(v0.6-B) HMM regime-switch + mean-reversion** — addresses fold concentration. 4-6 sprints.
- **(v0.6-C) Multi-symbol revival post-MVP** — ONLY path к T5 ≥100 conjoint pass per S22 critical insight. Out of MVP per user.
- **(v0.6-D) Different strategy class** (donchian, ATR-bands, regime-detection) — fresh hypothesis space.
- **(v0.6-E) Project pause** — 5 hypotheses + structural insight = strong publishable contribution.
- **(v0.6-F) MVP T5 floor amendment** — operator decides spec amendment justified per empirical evidence (max ~73 trades vs 100 floor = 30% gap). spec amendment к acceptance-criteria.md.

## Перенесённые задачи (S12-S22, 16+ пунктов + новые из S22)

All previous + new from S22:
- T5 100 structural insight (3 timeframes evidence) = institutional knowledge
- S17+S22 combined ~120 trades available для ML training basis
- 4H Bybit backfill API hung issue (root cause unknown, resample workaround used)
- 5th map missed by architecture review template — improvement needed

## Ключевые решения (S23 ADR 0038)

- **Pre-committed honest close** per ADR 0037 BINDING
- **CC1 T5 100 structurally unreachable BINDING** (3 timeframes empirical)
- **CC2 cross_trial_sharpes archival BINDING** (mirror S16/S18/S21)
- **CC3 Repeated 5/6+DSR+MC PASS pattern preserved** (S17+S22 — strategy edge regime-independent)
- **CC4 Hudson & Urquhart 2021 partial-validation** (15M degrades but 4H NOT)
- **CC5 Tag semantics**: alpha.23 = v0.5 marker, NOT MVP DONE
- **CC6 No spec amendment** (T1-T6 preserved)
- **CC7 Multi-symbol + 15M + 4H infrastructure preserved**
- **No code changes**: docs only

## Related

- [[../decisions/0038-sprint-23-honest-close-v05]] — S23 ADR
- [[../decisions/0037-sprint-22-4h-test]] — S22 ADR (FAIL trigger)
- [[sprint-22-4h-test]] — S22 4H test
- [[sprint-21-honest-close-v04]] — S21 v0.4 honest close (precedent)
- [[sprint-18-honest-close-v01]] — S18 v0.1 honest close (precedent)
- [[sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent)
- [[sprint-14-honest-close]] — S14 first honest close (precedent pattern)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
