---
title: "Sprint 52 — Kronos ML strategy integration (foundation model, exploratory)"
type: sprint
tags: [sprint-52, kronos, ml-strategy, foundation-model, prediction-cache, pretrain-leakage, exploratory, reason-codes-67, s52]
created: 2026-05-30
updated: 2026-05-30
status: completed
sources:
  - llm-wiki/wiki/project/plans/2026-05-30-sprint-52-kronos.md
  - llm-wiki/wiki/project/decisions/0068-sprint-52-kronos-integration.md
  - llm-wiki/wiki/project/pre-s52-backlog.md
---

# Sprint 52 — Kronos ML strategy integration

## Обзор

Первая ML-стратегия проекта: интеграция Kronos (open-source foundation model для financial K-lines, `NeoQuasar/Kronos-mini` 4.1M, MIT) как exploratory tradeable strategy. Brainstorm PHASE 2 (C1-C7 architecture + V1-V5 trader + ESC-1=A operator). Operator directive «не останавливаться до полного внедрения».

**Baseline (post-S51):** pytest 1449 / mypy 0 / reason_codes 65.
**Post-S52:** pytest **1481** / mypy 0 / reason_codes **67** (+2: ENTRY_LONG_KRONOS + EXIT_FLAT_KRONOS).

## GATE 0 — Pretrain leakage (BLOCKING, T0)

Исследование (T0) установило: Kronos pretrained на 12 млрд K-line records с 45 global exchanges. BTC/USDT явно подтверждён в корпусе. Cutoff date не опубликован; paper date 2025-08-02 → upper bound ~mid-2025. Наши parquet данные (BTC/ETH/SOL 2023-2026) contaminated by pretrain leakage с неизвестной степенью.

**Следствие (LOCKED):** WFA "OOS" backtest = методологически невалиден (in-sample под видом OOS — look-ahead на уровне model weights). Backtest verdict = `RAW_PRETRAIN_LEAKAGE_SUSPECTED` (exploratory, НЕ gate). Формальная hypothesis #11 DEFERRED до forward paper-trade на post-cutoff (~post-2025-08) данных.

## Задачи (T0-T10)

| Задача | Описание | Commit |
|--------|----------|--------|
| **T0** | GATE 0 pretrain leakage investigation → ADR 0068 leakage clause | `72a8178` |
| **T1** | `[ml]` optional dep group (torch>=2.2, transformers, tokenizers, safetensors, einops, huggingface_hub) + torch-isolation AST guard test | — |
| **T2** | `src/ml/kronos_adapter.py` — KronosAdapter Protocol + KronosModelAdapter (lazy torch) + MockKronosAdapter. Decimal boundary C6 | — |
| **T3** | `src/ml/prediction_cache.py` — CacheKey (7 fields), SHA-256 sidecar, median_ensemble, determinism. torch-free | — |
| **T4** | `src/signalgen/kronos_strategy.py` — on_bar cache-consumer, signal rule V3. Reason codes 65→67 | — |
| **T5** | `RAW_PRETRAIN_LEAKAGE_SUSPECTED` verdict в research_runner_envelope.py + glossary + frontend Verdict type | — |
| **T6** | `src/backtest/kronos_runner.py` — run_kronos_exploratory (cache-replay, open[i+1] fill, NO WFA, NO cross-trial) | — |
| **T7** | `scripts/run_kronos_s52.py` — operator-M4 cache-build (RUN_ML=1, 11 combos, mini/mps, dual weights_hash provenance) | — |
| **T8** | Dashboard parametric `kronos` preset, 11 supported_combos, optgroup «ML / Прогноз», cache-absent graceful message | — |
| **T9** | Opt-in RUN_ML integration test, CI mock-isolated (no torch, --ignore=tests/integration) | — |
| **T10** | ADR 0068 accepted + wiki sync (этот файл) | — |

## Ключевые архитектурные решения

### Binding conditions (C1-C7, architecture-reviewer)

| Условие | Суть |
|---------|------|
| **C1** | torch в optional `[ml]` group; lazy import; NO top-level torch вне `src/ml/`. Существующие стратегии + CI работают torch-absent |
| **C2** | Inference за Protocol boundary `KronosAdapter`. NEVER в on_bar / live / FSM-writer path. on_bar = cache lookup only |
| **C3** | predict-CACHE: offline precompute → replay через existing on_bar. НЕ inference-per-bar |
| **C4** | Determinism: torch seed + cache artifact (CacheKey 7 fields) + SHA-256 checksum. MPS non-determinism contained |
| **C5** | Веса gitignored, download-on-demand. CI mocked (no 400MB, no MPS). opt-in RUN_ML integration test |
| **C6** | float32 → `Decimal(str(v))` на `src/ml/` boundary. No tensor crossing к money path |
| **C7** | Thin kronos_runner (не god-object). New component cluster `src/ml/`. New reason codes 65→67. strategy_class "kronos" |

### Trader verdicts (V1-V5)

| Вердикт | Суть |
|---------|------|
| **V1** | GATE 0 cutoff investigation (done — contaminated) → backtest RAW label → forward paper-trade = real gate |
| **V2** | mini first (ctx2048, 25× cheaper cache) |
| **V3** | Signal: pred_close[h=1] > current×(1+threshold≥0.25%), symmetric exit, long-only |
| **V4** | sample_count≥20 + median + seed (NOT sample_count=1) |
| **V5** | Exploratory track, formal hypothesis #11 deferred. cross_trial pool "kronos" empty (INSUFFICIENT_CLASS_HISTORY correct) |

### ESC-1=A (operator decision)

Построить полную инфраструктуру + dropdown NOW как tradeable exploratory стратегию. Backtest=RAW label. Formal hypothesis #11 (N_trials increment + cross_trial pool fill) DEFERRED до forward paper-trade на post-cutoff данных. Эта стратегия может **никогда** не пройти formal gate — принято operator.

## Supported combos (11)

```
BTCUSDT:  5m, 15m, 1h, 4h, 1d
ETHUSDT:  15m, 1h, 4h
SOLUSDT:  15m, 1h, 4h
```

## Gates (post-S52)

| Gate | Результат |
|------|-----------|
| pytest unit | **1481** passed |
| mypy --strict | **0** errors |
| reason_codes | **67** (65→67, +2 S52) |
| torch isolation AST | PASS (torch не импортируется в non-ml модулях) |
| CI (no torch) | PASS (MockKronosAdapter, --ignore=tests/integration) |

## Operator follow-up (M4 cache-build)

Для запуска реального Kronos inference и exploratory backtest:
```bash
RUN_ML=1 python scripts/run_kronos_s52.py  # Mac M4 Pro, device=mps
```
Строит cache для всех 11 combos → `data/kronos_cache/`. После этого: `python -m src.dashboard` → dropdown «ML / Прогноз».

## Deferred

- **Formal hypothesis #11** (forward paper-trade gate): `N_trials++` + cross_trial pool "kronos" fill DEFERRED. Требует: ≥6 мес post-cutoff forward data + собственный pre-registration ADR.
- **Formal ESC-1 answer**: может ли pretrained-модель к live-капиталу? Trader: forward ≥6мес post-cutoff + Sharpe>1.0 + DSR на forward-only пуле (decision при formal ADR).

## Related

- [[../decisions/0068-sprint-52-kronos-integration]] — ADR 0068 (accepted)
- [[../components/kronos-strategy]] — компонент стратегии
- [[../components/kronos-adapter]] — ML inference boundary
- [[../components/prediction-cache]] — детерминированный кэш прогнозов
- [[sprint-51-debt-closing]] — предыдущий спринт (baseline 1449/0/65)
- [[../plans/2026-05-30-sprint-52-kronos]] — план T0-T10
