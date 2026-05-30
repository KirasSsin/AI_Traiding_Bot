---
title: Pre-S52 Backlog — Kronos ML foundation-model strategy
type: backlog
tags: [pre-sprint, backlog, s52, kronos, ml-strategy, data-leakage, foundation-model]
created: 2026-05-30
updated: 2026-05-30
status: draft
sources:
  - https://github.com/shiyu-coder/Kronos
  - https://huggingface.co/NeoQuasar/Kronos-base
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
---

## Назначение

S52 = интеграция Kronos (HuggingFace foundation model, K-line forecasting transformer) как новой ML торговой стратегии (operator request). PHASE 2 brainstorm complete: architecture-reviewer PRE-PLAN (C1-C7) + trader-expert (V1-V5 + ESC-1).

## Kronos scouted facts

- Decoder-only AR transformer, прогноз future OHLCV. `NeoQuasar/Kronos-base` 102M / `Kronos-mini` 4.1M. Separate tokenizer. Sampling (sample_count, T, top_p). MIT.
- Deps: torch, einops, huggingface_hub, safetensors, numpy, pandas, tqdm (no version pins). Python 3.10+.
- API: `KronosPredictor(model, tokenizer, device, max_context).predict(df, x_timestamp, y_timestamp, pred_len, T, top_p, sample_count)`.
- Compute: operator Mac M4 Pro → torch device "mps". README не упоминает MPS explicitly (риск C6).
- **Pretrain cutoff/assets НЕ опубликованы** в README — критично для validity (V1 GATE 0).

## Architecture-reviewer PRE-PLAN (APPROVE_WITH_CONDITIONS) — binding C1-C7

- **C1 (HIGH):** torch+HF в optional `[ml]` dep group. kronos_strategy.py NO top-level torch import (lazy, ImportError→"pip install .[ml]"). HARD GATE: 6 existing strategies + backtest run с torch absent. CI assertion.
- **C2 (HIGH):** inference за adapter boundary `src/ml/kronos_adapter.py` (mirror account_service) — returns plain Python/Decimal, NO torch types leak. Strategy depends on adapter, unit-testable с mock.
- **C3 (BLOCKER-class):** predict-CACHE architecture. Backtest precomputes predictions offline → cache artifact (keyed timestamp+model+params); vectorized kernel + on_bar read cache (dict lookup, NOT inference). Live: predict-once-per-bar + cache by timestamp; halt-safe fallback if inference > bar interval (never block). НЕ inference-per-bar inline.
- **C4 (BLOCKER-class):** determinism. torch manual seed + cache artifact = canonical input (parity tests read same cache → same signals). cache checksum (S51 D2 sidecar pattern). Document MPS float32 non-determinism — cache, NOT live re-inference, = backtest source of truth.
- **C5 (HIGH):** weights gitignored, download-on-demand к local cache. CI mocked adapter (no 400MB download, no MPS). 1 opt-in `@pytest.mark.integration RUN_ML=1` real-inference test (operator M4). Default pytest passes zero-ML zero-network.
- **C6 (MEDIUM):** Kronos float32 → `Decimal(str(v))` at adapter boundary. MPS float64-unsupported ops stay inside adapter. No tensor crosses boundary.
- **C7 (MEDIUM):** kronos-strategy + kronos-adapter component pages. New ReasonCode ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS (canonical enum). Kronos = new strategy_class "kronos" (S51 D5 pool). Hypothesis #11 (но N_trials defer — see V5).

## Trader-expert (V1-V5 binding + ESC-1)

- **V1 — Q1 REVISE (validation):** (e-amended) три уровня. **GATE 0 (BLOCKING first task):** установить pretrain cutoff эмпирически (HF model card + weights upload date = верхняя граница; если недоступно → worst-case = download date, вся 2023-2026 contaminated). Зафиксировать в ADR LOCKED assumption. **Exploratory backtest:** WFA с label `RAW_PRETRAIN_LEAKAGE_SUSPECTED` (новый verdict класс, mirror RAW_FULL_PERIOD ADR 0062) — НЕ WFA_PASS/FAIL. **REAL gate:** forward paper-trade ТОЛЬКО на post-cutoff барах (leakage-free, месяцы накопления). Residual risk: режимы автокоррелируют через cutoff — forward = generalization не полная независимость.
- **V2 — Q2 CONFIRM:** mini first (4.1M, ctx2048). 25× дешевле cache-build, 4× контекст (2048 баров=85д vs 21д), валидирует pipeline дёшево. base только если forward-signal promising.
- **V3 — Q3 CONFIRM (signal rule a + уточнения):** `predicted_close[h] > current_close×(1+threshold) → LONG, exit on symmetric flip`. **LOCKED:** horizon h pre-registered (рек h=12 баров 1H), threshold ≥2× round-trip cost (Bybit taker 0.1%×2+slippage → ≥0.25%), exit symmetric, long-only (Spot). Pure function of cached prediction (C3 parity).
- **V4 — Q4 REVISE (determinism):** LOCK params (T=1.0, top_p=0.9) — НО **sample_count≥20 + median + LOCKED seed**, NOT sample_count=1 (=один случайный сэмпл, не детерминизм). Median ensemble = устойчивый детерминированный (при seed) сигнал. Cache амортизирует cost (offline once). NO param sweep.
- **V5 — Q5 CONFIRM (defer formal registration):** S52 = build infra (C1-C7) + exploratory backtest (RAW label) + signal extraction. **Formal hypothesis #11 + N_trials increment + cross_trial pool fill = ТОЛЬКО после forward paper-trade OOS на post-cutoff данных.** До тех пор Kronos = exploratory track (mirror autoresearch toy mode, bypass formal counter). cross_trial pool класс "kronos" создаётся пустым (INSUFFICIENT_CLASS_HISTORY fallback корректен).

### Cross-cutting (trader)
- **CC1:** RAW_PRETRAIN_LEAKAGE_SUSPECTED новый verdict класс (mirror ADR 0062 RAW_FULL_PERIOD) — verdict enum + dashboard label + honest explanation. Центральный артефакт честности S52.
- **CC2:** determinism цепочка (C4 + V4): seed + sample_count≥20 + median + cache-checksum — все 4 вместе или parity-тест (S50 T5 класс) не пройдёт.
- **CC3:** GATE 0 cutoff investigation = первая задача, блокирует всё.

## ESC-1 → operator (risk-appetite, BINDING product decision)

**Может ли pretrained-модель ВООБЩЕ быть допущена к live-капиталу под нашей дисциплиной?** Даже идеальный forward paper-trade слабее WFA на genuinely-unseen данных (cutoff неточен, режимы автокоррелируют, мы не контролируем pretrain content). Operator решает: принимает ли более слабую гарантию для ML-стратегий чем для 10 self-built гипотез? Если НЕТ → Kronos навсегда exploratory-only. Если ДА → сколько месяцев forward + какой Sharpe порог. Trader рек: forward ≥6мес post-cutoff + Sharpe>1.0 + DSR на forward-only пуле перед live.

## S52 execution order (post-ESC-1)

1. GATE 0 — pretrain cutoff investigation (BLOCKING)
2. `[ml]` dep group + `src/ml/kronos_adapter.py` (lazy torch, C1+C2)
3. predict-cache infra (C3) + determinism seed+median+checksum (C4)
4. `src/signalgen/kronos_strategy.py` (on_bar, signal rule V3, mock-testable)
5. RAW_PRETRAIN_LEAKAGE_SUSPECTED verdict class (CC1)
6. reason codes ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS (C7)
7. exploratory backtest (cache-build mini + WFA RAW label)
8. CI mock adapter + opt-in integration test (C5)
9. dashboard preset (RAW label) + component pages + wiki sync

## Related
- [[decisions/0014-walk-forward-train2000-test500]]
- [[decisions/0059-sprint-39-volume-breakout-pre-registration]]
- [[decisions/0062-sprint-42-atr-breakout-hardening]] (RAW_FULL_PERIOD precedent)
- [[sprints/sprint-50-supertrend]] (most recent strategy-add precedent)
