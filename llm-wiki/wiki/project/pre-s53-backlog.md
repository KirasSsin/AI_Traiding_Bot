---
title: Pre-Sprint 53 Backlog — Kronos real-inference enablement
type: summary
tags: [sprint-53, kronos, ml, enablement, brainstorm, pre-plan]
created: 2026-05-30
updated: 2026-05-30
sources:
  - llm-wiki/wiki/project/decisions/0068-sprint-52-kronos-integration.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
status: stable
---

# Pre-S53 Backlog — Kronos real-inference enablement

**TL;DR:** S52 внедрил Kronos, но real-inference path сломан (speculative wrong import `from kronos`, mini↔tokenizer mismatch, `atr_14=0` баг). S53 = починить real-inference + оба variant (base+mini) + честная adaptation под нашу логику. Backtest остаётся exploratory (operator принял дисциплину после глубокого объяснения leakage).

## Контекст

S52 SHIPPED v0.1.0-alpha.52. Operator хочет полное внедрение Kronos как рабочей стратегии, оба variant. Operator **принял** anti-snooping дисциплину: backtest = exploratory (leakage), live-капитал только после forward paper-trade (месяцы). Variant = **оба** (base + mini).

## PHASE 2 brainstorm — verdicts (trader-expert ROUND 1 + architecture-reviewer PRE-PLAN)

### Q1 — механизм поставки кода Kronos
- **trader:** REVISE → vendor copy (c)
- **architecture (BINDING по механизму, S46 gate):** APPROVE_WITH_CONDITIONS → **(a) git submodule** `third_party/kronos/` pinned sha
- **Финал: (a) git submodule.** pip-from-git ПОДТВЕРЖДЁННО невозможен (нет setup.py/pyproject — empirically `pip install --dry-run` fails). Vendor (c) требует патчить upstream `sys.path.append("../")` hack = mutation. Submodule = zero-mutation, pinned sha, CI-safe. `model/__init__.py` экспортирует классы. sys.path.insert ТОЛЬКО внутри `KronosModelAdapter.__init__` try-block (не module-level, не collection-time). Trader collision-concern (`model` = common name) митигирован scope.
- pinned sha: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (master HEAD — operator verify перед RUN_ML=1).

### Q2 — variant handling (base + mini)
- **trader CONFIRM + architecture CONFIRM (C10):** `KronosVariant` frozen dataclass + named singletons:
  - `KRONOS_BASE` = (NeoQuasar/Kronos-base, NeoQuasar/Kronos-Tokenizer-base, ctx=512)
  - `KRONOS_MINI` = (NeoQuasar/Kronos-mini, NeoQuasar/Kronos-Tokenizer-2k, ctx=2048)
- Tokenizer-context coupling закодирован структурно (нельзя выставить неверно). 2 variants × 11 combos. CacheKey.model_id уже включает variant → cache не конфликтует.

### Q3 — signal logic ("адаптировать под нашу логику")
- **trader EXPAND → 2 трека. Operator ESC-1 решение: V3 locked + только ATR fix.**
- **Track A (S53 BLOCKER):** `KronosStrategy._build_signal` ставит `atr_14=Decimal("0")` → risk_manager bracket sizing = SL на open price ИЛИ div-by-zero. Стратегию нельзя торговать. Фикс: KronosStrategy получает реальный ATR (atr_calculator OR from bar context).
- **Track B (DEFER post-S53):** signal enrichment (predicted high/low → SL/TP, multi-horizon) LOCKED до forward paper-trade. Anti-snooping (ADR 0014 + S50 boundary-winner).

### Q4 — anti-snooping для 2 variants на тех же данных
- **CONFIRM:** оба variant × 11 combos под `RAW_PRETRAIN_LEAKAGE_SUSPECTED`, no N_trials increment, no cross_trial pool. Cherry-pick "лучшего variant/combo по backtest" = ЗАПРЕЩЁН (selection bias). UI warning обязателен.

### Q5 — forward paper-trade harness
- **CONFIRM:** DEFER → S54+. S53 = enablement + backtest only. Forward harness = качественно иная инфра (live-feed, real-time scheduling) = отдельный спринт.

## Architecture binding conditions (ADR 0069)

- **C8:** import fix `from kronos`→`from model` (через submodule path).
- **C9:** git submodule `third_party/kronos/` pinned sha. sys.path.insert только внутри `__init__` try-block.
- **C10:** `KronosVariant` frozen dataclass (KRONOS_BASE + KRONOS_MINI singletons). Adapter takes `variant`.
- **C11:** extract `src/dashboard/_kronos_dispatch.py` ДО добавления variant branching (backtest_runner 1682 LoC > 1500 HARD-GATE).
- **C12:** CI isolation invariants unchanged (torch absent, AST guard passes — submodule под third_party/ не src/). New test: submodule-existence check when RUN_ML=1.
- **C13:** error message two-step (submodule init + pip install ml).

## Cross-cutting (trader CC1-CC5)

- **CC1 (T0-fix):** import bug + mini tokenizer-2k mismatch — оба гарантируют broken/wrong inference.
- **CC2 (Track A):** atr_14=0 функциональный баг.
- **CC3:** verify `predict()` signature против реального API (сейчас только Mock тестируется).
- **CC4:** смена tokenizer → weights_hash меняется → cache rebuild обязателен. Warning в скрипте.
- **CC5:** rename `run_kronos_s52.py` → `run_kronos_s53.py` + variant selector.

## Carry (не S53-specific, но рядом)

- current-state.md split (54KB > 50KB) — делать ДО sprint чтобы не блокировать orient.

## Live counts (на момент brainstorm)

FSM 16/30/74, reason_codes 67 (ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS уже в S52, S53 НЕ добавляет).
