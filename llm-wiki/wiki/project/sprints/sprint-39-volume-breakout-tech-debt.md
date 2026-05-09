---
title: Sprint 39 — volume_breakout production integration + tech debt
type: sprint
tags: [sprint-39, volume-breakout, autoresearch-integration, pre-registration, tech-debt, bybit-api, rate-limit, shim-removal, ru]
created: 2026-05-09
updated: 2026-05-09
status: completed
sources:
  - project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
  - project/research-evidence/FINAL_STRATEGY.md
  - project/research-evidence/CLOSE.md
  - project/pre-s39-backlog.md
  - project/plans/2026-05-09-sprint-39-volume-breakout-tech-debt.md
---

# Sprint 39 — volume_breakout production integration + tech debt

## Обзор

**Цель:** Интеграция volume_breakout стратегии из autoresearch iter 10 в production + критический tech debt перед TESTNET активацией.

Tag v0.1.0-alpha.39. **Profit invariant:** production runner реплицирует baseline в пределах ±0.5% (8mo held-out +20.42% n=17 / 3.3y +122.66%) — VERIFIED PASS post-T5b.

### Brainstorm verdicts (Q1-Q9)

| Q# | Вопрос | Вердикт |
|----|--------|---------|
| Q1 | Параметры verbatim vs округление | CONFIRM verbatim sweep#1644 |
| Q2 | Gate 2 paper-trade | CONFIRM после tag alpha.39 |
| Q3 | M3+M4 bybit-api | CONFIRM IN, M1+M2+MAINNET ADR DEFER к S40+ |
| Q4 | llm-wiki/CLAUDE.md pruning | DEFER |
| Q5 | Kelly sizing disclosure | 0.25× cap + mandatory 4-point disclosure section |
| Q6 | Held-out vs full backtest PRIMARY | REVISE → 8mo held-out PRIMARY, 3.3y SECONDARY с contamination label |
| Q7 | Dashboard UI enforce | CONFIRM ENFORCE 4H+BTCUSDT (422 на other combos) |
| Q8 | Cherry-pick research-evidence | CONFIRM (DONE T6) |
| Q9 | ATR filter augmentation | EXPAND → Option A baseline LOCK now, ATR filter → S40+ |

### Структура треков (14 задач)

- **Track A** — volume_breakout core (A0-A6 + T5b: 7 задач)
- **Track B** — критический tech debt перед TESTNET (B1-B3: 3 задачи)
- **Track C** — cleanup (C1-C2: 2 задачи)
- **Track E** — bybit-api M3+M4 (E1-E2: 2 задачи)

## Доставленная функциональность

### Track A — volume_breakout core

| Задача | Тип | Описание |
|--------|-----|----------|
| A0 ADR-0059 LOCKED pre-commit | Wiki ADR | Anti-snooping pre-commit per Q1+Q2+Q5+Q6+Q9 |
| A1 ReasonCodes +3 | Code | `ENTRY_LONG_VOLUME_BREAKOUT` / `EXIT_FLAT_VOLUME_CHANNEL` / `EXIT_FLAT_ATR_STOP_VB` (50→53) |
| A2 compute_volume_breakout_signals | Code + tests | Helper в `src/signalgen/indicators.py` |
| A3 VolumeBreakoutStrategy | Code + tests | `src/signalgen/volume_breakout_strategy.py` LOCKED params |
| A4 Dashboard preset ENFORCE | Code | `volume_breakout_iter10` preset: 4H+BTCUSDT ENFORCE (backend 422) |
| A5 Phase 5 baseline floor test | Test | `tests/integration/test_volume_breakout_baseline_floor.py` signal-fidelity |
| T5b BLOCKER fix | Code + test | `src/backtest/volume_breakout_runner.py` — port research execution model, replicates baseline ±0.5% |
| A6 Research-evidence cherry-pick | Wiki | `wiki/project/research-evidence/FINAL_STRATEGY.md` + `CLOSE.md` |

### Track B — критический tech debt

| Задача | Тип | Описание |
|--------|-----|----------|
| B1 H1 rate-limit backoff | Code + tests | 6 retCodes + idempotency safety; BLOCKER+HIGH fixes |
| B2 H2 WS reconnect re-probe | Code + tests | Verification gap закрыт |
| B3 Item#10 boundary tests | Tests | DD_MULTIDAY + NO_TRADE_TIMEOUT параметризованные сценарии |

### Track C — cleanup

| Задача | Тип | Описание |
|--------|-----|----------|
| C1 Item#7 RiskSharedDeps shim removal | Code + tests | 22 caller'а мигрированы, backward-compat shim удалён |
| C2 F8 MC_BLOCK_SIZE unification | Code | Single source = 20; константа вынесена |

### Track E — bybit-api hardening

| Задача | Тип | Описание |
|--------|-----|----------|
| E1 M3 isinstance shape guard | Code + tests | 3 WS handler'а защищены от неожиданного типа данных |
| E2 M4 `__repr__` secret redaction | Code + tests | WS consumer не логирует credentials |

## Решения и отклонения

| Решение | Обоснование |
|---------|-------------|
| Verbatim sweep#1644 параметры | Post-observation tuning = anti-snooping нарушение |
| 8mo held-out PRIMARY evidence | Bailey 2014 champion-bias: 4510 implicit comparisons загрязняют 3.3y backtest |
| ATR filter → S40+ | Option A (baseline LOCK first, augmentation = отдельная гипотеза) |
| M1+M2+MAINNET ADR → S40+ | Scope control: M3+M4 уже в S39, M1+M2 = менее критичные |
| Gate 2 BLOCKING к real capital | N≥10 live trades обязательны для Kelly fraction пересмотра |

## Проверка (Phase 5)

- **pytest unit:** 905 → 915+ passed (+10+ новых тестов)
- **pytest integration:** baseline floor PASS (production runner ±0.5% vs research baseline)
- **mypy --strict src/:** 0 ошибок
- **Canonical counts:** 16/30/74/**53** (reason_codes +3)
- **Profit invariant:** VERIFIED — 8mo held-out +20.42% n=17 / 3.3y +122.66%

## Влияние на следующие спринты

**Gate 2 (следующий шаг оператора):**
- Активировать `volume_breakout_iter10` preset на δ TESTNET
- Мониторинг N≥10 signals; live Sharpe через `generate_live_report()`
- IF FAIL → S40 honest close ADR обязателен ДО любого MAINNET-promotion

**S40+ кандидаты:**
- ATR filter augmentation (Q9 Option A: baseline established, ATR filter = отдельная гипотеза → новый ADR)
- M1 retCode taxonomy gaps + M2 pybit response-shape (из bybit-api-reviewer)
- 12mo MAINNET-promotion ADR (trigger: n=10 first non-NaN DSR)
- llm-wiki/CLAUDE.md pruning (Q4 DEFER)

## Перенесённые задачи

| Задача | Целевой спринт | Обоснование |
|--------|---------------|-------------|
| ATR filter augmentation | S40+ | Q9 Option A: требует отдельного ADR + pre-registration |
| M1 retCode taxonomy + M2 pybit shape | S40+ | Q3 partial: M3+M4 DONE, M1+M2 менее критичны |
| MAINNET-promotion ADR draft | n=10 trigger | anti-snooping: только после накопления live data |
| Q4 llm-wiki/CLAUDE.md pruning | S40+ | scope control |

## Связанные документы

- [[../decisions/0059-sprint-39-volume-breakout-pre-registration]] — ADR 0059 LOCKED params + evidence + Gate 2
- [[../components/volume-breakout-strategy]] — компонент страница VolumeBreakoutStrategy
- [[../research-evidence/FINAL_STRATEGY]] — sweep#1644 held-out OOS evidence
- [[../research-evidence/CLOSE]] — autoresearch iter falsification record
- [[../decisions/0054-sprint-35-donchian-pre-registration]] — предыдущая pre-registration LOCKED (модель)
- [[../decisions/0055-sprint-36-delta-activation]] — δ TESTNET activation (Gate 2 target)
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — DSR sizing disclosure rationale
- [[../components/delta-activation-playbook]] — оператор playbook (Gate 2 шаги)
- [[../sprints/sprint-38-delta-parallel-hardening]] — предыдущий спринт (bybit-api-reviewer findings источник)
