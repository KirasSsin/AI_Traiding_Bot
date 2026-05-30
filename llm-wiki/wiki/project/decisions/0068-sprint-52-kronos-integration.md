---
title: "0068. Sprint 52 — Kronos ML foundation-model strategy integration"
type: decision
tags: [decision, adr, s52, kronos, ml-strategy, foundation-model, data-leakage, pretrain-cutoff, exploratory]
created: 2026-05-30
updated: 2026-05-30
status: accepted
sources:
  - https://github.com/shiyu-coder/Kronos
  - https://huggingface.co/NeoQuasar/Kronos-base
  - https://arxiv.org/abs/2508.02739
  - llm-wiki/wiki/project/pre-s52-backlog.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md
---

# 0068. Sprint 52 — Kronos ML foundation-model strategy integration

**Status:** accepted
**Date:** 2026-05-30

## Контекст

Operator request: интегрировать Kronos (open-source foundation model для financial K-lines, `NeoQuasar/Kronos-base` 102M / `Kronos-mini` 4.1M, MIT) как новую торговую стратегию в dropdown, адаптированную под все наши (symbol, timeframe) parquet combos. Major change: первый ML/torch dep в проекте + ML inference path (бот = pure streaming on_bar).

PHASE 2 brainstorm: architecture-reviewer PRE-PLAN APPROVE_WITH_CONDITIONS (C1-C7) + trader-expert (V1-V5 + ESC-1). ESC-1 RESOLVED operator = **(A)**.

## GATE 0 — Pretrain leakage clause (LOCKED, T0 finding)

**Установленные факты (HF model card + GitHub + arXiv 2508.02739):**
- Kronos pretrained на **12 млрд K-line records с 45 global exchanges**.
- **BTC/USDT ЯВНО подтверждён** в корпусе (live demo + примеры).
- **Cutoff date НЕ опубликован** нигде (model card / README / paper page). Paper published **2025-08-02** → worst-case data cutoff ≈ mid-2025 (upper bound; actual может быть раньше).
- 45 exchanges глобально → почти наверняка incl. крупные крипто-биржи (Binance/Bybit) → наши ETH/SOL вероятно тоже contaminated.

**LOCKED assumption:** наши parquet данные (BTC/ETH/SOL 2023-2026) **CONTAMINATED by pretrain leakage** с неизвестной степенью. BTC — точно. Единственная потенциально leakage-free зона = bars **после ~2025-08** (и то paper-date — верхняя граница, не гарантия).

**Следствие:** WFA "OOS" backtest на наших данных = **методологически невалиден** (in-sample под видом OOS — look-ahead на уровне model weights, тысячи баров). Это новый класс риска НЕ покрытый ADR 0059/0067 anti-snooping templates.

## Решение

Интегрировать Kronos как **exploratory tradeable strategy** (ESC-1 = A):
- Build full infra (adapter + cache + on_bar strategy + dropdown presets) — все 11 combos.
- Backtest verdict = **RAW_PRETRAIN_LEAKAGE_SUSPECTED** (новый класс, mirror ADR 0062 RAW_FULL_PERIOD) — exploratory, НЕ gate, НЕ WFA_PASS/FAIL.
- **Formal hypothesis #11 + N_trials increment + cross_trial pool fill = DEFERRED** до forward paper-trade на post-cutoff (~post-2025-08) данных. Отдельный future pre-registration ADR.
- **ЭТОТ ADR — НЕ pre-registration ADR** (в отличие 0059/0067). Фиксирует архитектуру; формальная регистрация позже.

### LOCKED spec
| Параметр | Значение | Источник |
|---|---|---|
| Model | Kronos-mini (4.1M, ctx2048) first | V2 |
| Pairs × TF | 11 combos: BTC {5m,15m,1h,4h,1d} + ETH/SOL {15m,1h,4h} | operator expanded |
| Signal rule | predicted_close[h=1] > current×(1+threshold) → LONG; symmetric exit | V3 |
| Threshold | LOCKED ≥0.60% (2× round-trip cost: комиссия 0.10%/сторона + проскальзывание 0.05%/сторона = 0.30% round-trip → 0.60%; поправка PHASE 6 — исходные 0.25% были арифметической ошибкой, ниже break-even) | V3, PHASE 6 |
| Inference params | T=1.0, top_p=0.9, sample_count≥20 + median + seed | V4 |
| Compute | Mac M4 Pro MPS (dev/CI mocked) | operator |
| Backtest verdict | RAW_PRETRAIN_LEAKAGE_SUSPECTED (exploratory) | V1+CC1 |

## Binding conditions (architecture C1-C7)

- **C1:** torch+HF в optional `[ml]` group, lazy import, NO top-level torch вне `src/ml/`. 6 existing strategies + backtest + pytest run torch-absent (CI verify).
- **C2:** inference за `src/ml/kronos_adapter.py` Protocol boundary. NEVER on live-tick/FSM-writer path. on_bar = cache-LOOKUP only. Cache-miss → None (no block).
- **C3:** predict-CACHE — backtest precompute offline → replay через existing on_bar + run_research_wfa parity infra. НЕ inference-per-bar.
- **C4:** determinism — torch seed + cache artifact = canonical source. Cache key `(model_id, weights_hash, symbol, tf, bar_ts, params_hash, device)` + SHA-256 checksum. MPS non-determinism contained (cache, не live re-inference).
- **C5:** weights gitignored download-on-demand. CI mocked (no 400MB, no MPS). opt-in RUN_ML integration test (operator M4).
- **C6:** float32 → `Decimal(str(v))` at `src/ml/` boundary. No tensor crosses к money path.
- **C7:** не растить backtest god-object — thin kronos_runner. New component cluster `src/ml/`. New reason codes ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS (65→67). strategy_class "kronos" (S51 D5 pool).

## Trader V1-V5

- **V1** (validation): GATE 0 cutoff investigation (done — contaminated) → backtest RAW label → forward paper-trade = real gate.
- **V2** (variant): mini first (ctx2048, 25× cheaper cache).
- **V3** (signal): predicted_close[h=1] > current×(1+threshold), symmetric exit, long-only.
- **V4** (determinism): sample_count≥20 + median + seed (NOT sample_count=1).
- **V5** (defer): exploratory track, formal hypothesis #11 deferred to forward gate. cross_trial pool "kronos" empty (INSUFFICIENT_CLASS_HISTORY fallback correct).

## Последствия

### Положительные
- Reusable ML infra (adapter boundary + predict-cache + determinism pattern) для любых будущих ML стратегий.
- Честная разметка (RAW_PRETRAIN_LEAKAGE_SUSPECTED) — методологическая целостность сохранена.
- 11 combos в dropdown — operator может визуально исследовать Kronos прогнозы.

### Риски
- Kronos может НИКОГДА не пройти formal gate (backtest contaminated by design; forward paper-trade = месяцы). Принято operator (ESC-1 = A).
- torch dep ~2GB install (optional, не трогает core).
- MPS non-determinism — contained cache pattern.

### Открытые (escalation к operator, BINDING product decision позже)
- **ESC-1 deep:** может ли pretrained-модель ВООБЩЕ к live-капиталу? Trader рек: forward ≥6мес post-cutoff + Sharpe>1.0 + DSR на forward-only пуле. Решается при formal registration ADR (не сейчас).

## Поправка PHASE 6 (PHASE 6 R1, 2026-05-30)

Исправления по результатам ревью PHASE 6 (reviewer: quant, security, data-integrity):

1. **Порог 0.60% (FIX 1):** исходный порог 0.25% был арифметической ошибкой — ниже break-even (round-trip cost 0.30%). Исправлен до 0.60% (2× 0.30%). Изменены: `src/signalgen/kronos_strategy.py` (DEFAULT_THRESHOLD), `src/backtest/kronos_runner.py` (fallback), `scripts/run_kronos_s52.py` (run_params threshold).

2. **Аннуализация Sharpe по таймфрейму (FIX 2):** `_BARS_PER_YEAR_1H = 8766` было хардкодировано для всех 11 комбо. Заменено на `_bars_per_year(timeframe)` — вычисляет `31_557_600 / tf_seconds` (365.25-дневный год). 5m → 105192, 1h → 8766, 1d → 365.25.

3. **Bar.interval по таймфрейму (FIX 3):** `_build_bar_from_row` передавал `interval="1h"` для всех таймфреймов. Исправлено: `interval=timeframe`.

4. **Порядок вычисления weights_hash (FIX 4):** `_compute_weights_hash()` вызывался ДО инстанциирования `KronosModelAdapter` → fallback hash на первом запуске (файлы ещё не скачаны). Исправлено: `KronosModelAdapter(...)` создаётся ПЕРВЫМ (скачивает веса), затем `_compute_weights_hash()`.

5. **Пин ревизии модели (FIX 5, SECURITY):** добавлен параметр `revision: str | None = None` в `KronosModelAdapter.__init__()`, пробрасывается в `Kronos.from_pretrained(model_id, revision=revision)` и `KronosTokenizer.from_pretrained(tokenizer_id, revision=revision)`. Добавлена константа `KRONOS_REVISION: str | None = None` в `scripts/run_kronos_s52.py`. **Оператор ОБЯЗАН** установить `KRONOS_REVISION` в верифицированный commit SHA перед любым запуском `RUN_ML=1` — `from_pretrained` десериализует непроверенные чекпоинты (torch.load pickle = ACE). `weights_hash` — это post-download provenance, НЕ защита от ACE.

6. **Манифест sidecar (B2 HIGH, архитектурное):** `scripts/run_kronos_s52.py` пишет `data/kronos_cache/_manifest.json` (схема: `schema_version`, `model_id`, `weights_hash`, `params_hash`, `device`, `combos[]`). `src/dashboard/backtest_runner.py` читает манифест перед построением `CacheKey` при воспроизведении Kronos-пресета. **Инвариант: dashboard ОБЯЗАН читать key-параметры из `_manifest.json`, НИКОГДА не захардкоживать дефолты** — иначе 100% cache miss (именно этот баг был устранён). Отсутствие манифеста = кэш не построен; присутствие манифеста + bar-level miss = легитимный промах (данного бара в кэше нет). Подробности → [[../components/prediction-cache#манифест-dashboard-replay]].

## Related
- [[../pre-s52-backlog]] (полный brainstorm trail C1-C7 + V1-V5)
- [[../plans/2026-05-30-sprint-52-kronos]] (T0-T10)
- [[0062-sprint-42-atr-breakout-hardening]] (RAW_FULL_PERIOD verdict precedent)
- [[0014-walk-forward-train2000-test500]] (WFA gates — почему backtest невалиден здесь)
- [[0056-sprint-36-dsr-sigma-sr-amendment]] (cross_trial pool strategy_class)
