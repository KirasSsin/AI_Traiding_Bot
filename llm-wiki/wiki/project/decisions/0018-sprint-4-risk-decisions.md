---
title: 0018. Sprint 4 risk decisions — R:R, reason codes mapping, Wilson lower bound, L0 naming, reason-codes count
type: decision
tags: [adr, risk, kelly, circuit-breakers, reason-codes, sprint-4]
created: 2026-04-23
updated: 2026-04-23
sources: [src/risk/manager.py, src/risk/kelly.py, src/risk/reason_codes.py]
status: accepted
---

# 0018. Sprint 4 risk decisions

**Status:** accepted
**Date:** 2026-04-23
**Supersedes:** none
**Amends:** [[0012-4-phase-kelly-sizing]] (sub-decision 3 — Wilson lower bound contract); [[../../trading/concepts/reason-codes]] (sub-decision 5 — wiki count typo).

## Context

Sprint 4 имплементировал risk-модуль (Kelly + CB + RiskManager). По ходу разработки возникли 5 субдецизий, не покрытых ранее существующими ADR (0012, 0013, 0017). Они влияют на API контракт и аудит-инвариант, поэтому фиксируются явно.

## Sub-decision 1 — R:R = 2:1 default

**Question:** Какие SL/TP multiplier'ы по умолчанию?

**Decision:**
- `risk_sl_atr_multiplier = 1.5` (k для `compute_qty` И SL placement: `entry − 1.5·ATR`).
- `risk_tp_atr_multiplier = 3.0` (TP placement: `entry + 3.0·ATR`).
- Risk:Reward = 2:1 на каждый сетап.

**Rationale:** Walk-forward тесты Mimo bot (reference) показывали стабильный edge при R:R 2:1 на 1H BTCUSDT EMA-cross стратегии. Phase 1 (n<30 trades) — фиксированная 1% позиция; даже при 50% win-rate ожидаемый PnL положительный (`0.5·(+2R) − 0.5·(−1R) = +0.5R`).

**Configurable:** Оба значения в `Settings`, не в коде. ADR не меняется при тюнинге значений; меняется только при смене **формулы** (например, переход на ATR-on-entry vs trailing).

## Sub-decision 2 — REJECT_INVALID_SIGNAL и REJECT_ZERO_QTY НЕ распаковываются

**Question:** В prompt-spec было предложено добавить `REJECT_INVALID_SIGNAL` и `REJECT_ZERO_QTY` как отдельные коды. Делать?

**Decision:** Нет (для v0.1). Использовать существующие:
- "Invalid signal" → `REJECT_DUPLICATE_SIGNAL` (когда signal приходит повторно для одного бара) — это единственный realistic invalid case в S4. Strategy layer (S3) уже фильтрует out-of-order и not-closed bars; до Risk модуля невалидные signals не доходят.
- "Zero qty" после quantize → `REJECT_MIN_NOTIONAL` (семантически точнее: qty=0 значит позиция меньше минимального notional, который exchange примет).

**Rationale:** Reason codes immutable (см. правила в [[../../trading/concepts/reason-codes]] §3 — новые коды только через ADR). Перед добавлением кодов хотим увидеть реальные audit-log distributions из backtests S7. Если "zero qty" окажется частым отдельным класом (не от MIN_NOTIONAL, а от floating-point degenerate input) — добавим в S5/S7.

**Re-evaluate:** Sprint 5 (executor) — если venue filter rejects распадаются на distinct categories (FILTER_PRICE vs MIN_NOTIONAL vs LOT_SIZE), пересмотреть.

## Sub-decision 3 — Wilson 95% CI lower bound для Kelly phases 3/4

**Question:** В `RiskManager._compute_p_b` для phases 3/4 — использовать точечную оценку `wins/total` или Wilson lower bound?

**Decision:** **Wilson 95% CI lower bound** (`wilson_95_ci(wins, total)[0]`).

**Rationale:** Точечная оценка `p_hat = wins/total` системно переоценивает edge на малой выборке. Пример: 30 wins / 50 trades → `p_hat = 0.6`, но Wilson 95% lower = `0.45`. Если мы используем Half-Kelly формулу с завышенным `p`, получаем over-betting и blow-up при первой просадке. Lower bound — conservative estimate, потеря edge на upside, но защита от ruin на downside (Kelly criterion is symmetric in wrong direction — over-betting губительно).

**Amends ADR 0012:** Добавляет явный contract: phases 3/4 _compute_p_b возвращает `wilson_95_ci(...)[0]`, не `wins/total`. Code: `src/risk/manager.py:223`.

**Test coverage:** `tests/unit/test_risk_kelly.py::test_wilson_95_ci_*` + `tests/unit/test_risk_manager.py` (через mock trade history).

## Sub-decision 4 — `HaltState.L0` explicit naming (NOT null/None)

**Question:** "No halt active" представляется как `HaltState.L0` или `None`?

**Decision:** Explicit `HaltState.L0` enum value.

**Rationale:**
1. Pydantic v2 strict mode: `Optional[HaltState]` требует extra null-check на каждом сравнении.
2. State persistence: `state` table storing JSON, null vs string инконсистентно сериализуется (особенно при roundtrip через SQLite TEXT).
3. Severity ordering таблица (`_halt_severity`) — `L0=0` естественно работает, `None` сломал бы `if new > current`.
4. Audit-log queries: `SELECT * FROM events WHERE halt_state='L0'` чище чем `WHERE halt_state IS NULL OR halt_state='L0'`.

**Implementation:** `src/risk/models.py::HaltState` — `L0|L1|L2|L3|FLASH`. Default value of `current_halt` field — `HaltState.L0`.

## Sub-decision 5 — Reason codes count fix (28 → 29)

**Question:** Wiki header `Reason Codes (28)` и `6+7+8+7=28`, но при перечислении: exits=8 codes, halts=7. Какое истинное число?

**Decision:** **29** (`6 + 8 + 8 + 7`). Wiki header был неверен.

**Rationale:** `src/risk/reason_codes.py::ReasonCode` enum (immutable per concept page §2) всегда содержал 29 элементов. Wiki header arithmetic ошибочен в исходной странице (создана 2026-04-19) — section names "(7)" и "(6)" не соответствовали bullet-counts.

**Action taken:**
- `wiki/trading/concepts/reason-codes.md` обновлён: title, TL;DR, секция-headers, total → 29.
- `src/risk/reason_codes.py` docstring уже содержал correct note (см. lines 22-26).
- Никаких code изменений не требовалось (enum уже был 29).

**Forward-only:** ADR изменяет wiki header, не enum. Enum codes immutable per concept page §2 правило.

## Consequences

**Positive:**
- Wilson lower bound защищает от over-betting на early Kelly phases.
- Explicit L0 упрощает persistence и severity ordering.
- Wiki ↔ code reconciliation устраняет DRY violation (29 в код, 28 в wiki).
- Reason code mapping (sub-decision 2) предотвращает enum bloat без data evidence.

**Negative:**
- Wilson lower bound теряет ~10-20% edge upside на phases 3/4 (intentional trade-off).
- `REJECT_MIN_NOTIONAL` сейчас несёт две семантики (true filter violation + zero-qty after quantize). Audit-log queries должны учитывать.

**Neutral:**
- R:R 2:1 — стартовый default; Sprint 7 (backtest) может предложить тюнинг.

## References

- [[0012-4-phase-kelly-sizing]] — Kelly base ADR, amended sub-decision 3.
- [[0013-circuit-breakers-l1-l2-l3-flash]] — CB base ADR, no changes.
- [[../components/risk-manager]] — implementation reference.
- [[../../trading/concepts/reason-codes]] — wiki page updated by sub-decision 5.
- `src/risk/manager.py`, `src/risk/kelly.py`, `src/risk/reason_codes.py`.
