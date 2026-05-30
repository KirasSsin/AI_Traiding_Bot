# Sprint 52 — Kronos ML Strategy Integration Implementation Plan

> **For agentic workers:** subagent-driven-development, SEQUENTIAL dispatch (one task at a time — shared-branch parallel caused churn in S50/S51). TDD strict. Per-task commit + SPRINT_STATE update.

**Goal:** Integrate Kronos foundation model (K-line forecasting transformer) as a new ML trading strategy in the dashboard dropdown, adapted to all our (symbol, timeframe) parquet combos, with honest pretrain-leakage disclosure.

**Architecture (binding C1-C7 + trader V1-V5, ESC-1=A):** Kronos = offline predict→cache→replay through existing `on_bar`. torch behind optional `[ml]` dep + `src/ml/` adapter boundary. NEVER inference-in-on_bar. Backtest = exploratory RAW_PRETRAIN_LEAKAGE_SUSPECTED (not a gate). Formal hypothesis #11 / N_trials DEFERRED to forward paper-trade.

**Tech Stack:** Python 3.12, torch (optional [ml], device mps on operator M4), HuggingFace transformers/tokenizers, pandas, pytest. Branch `feature/sprint-52-kronos`.

**Compute constraint:** real Kronos inference = operator Mac M4 Pro (MPS). CI + this dev env = mocked adapter (C5). Infra is complete + mock-tested here; operator runs actual cache-build + exploratory backtest via `RUN_ML=1` script.

**Combos (11):** BTCUSDT {5m,15m,1h,4h,1d} · ETHUSDT {15m,1h,4h} · SOLUSDT {15m,1h,4h}.

---

## Task T0: GATE 0 — pretrain cutoff investigation (BLOCKING, opus)

**Files:** Create `llm-wiki/wiki/project/decisions/0068-sprint-52-kronos-integration.md` (ADR draft, "Pretrain leakage clause" section).

- [ ] **Step 1:** Investigate Kronos pretrain data cutoff + assets. Sources: HF model card `NeoQuasar/Kronos-base` + `Kronos-mini`, weights `last_modified` upload date (HF API), GitHub README/paper. Establish: (a) what assets pretrained on, (b) latest data date (cutoff). If unpublished → worst-case = weights upload date; everything before = potentially contaminated.
- [ ] **Step 2:** Record LOCKED assumption in ADR 0068 "Pretrain leakage clause": cutoff date (or worst-case upload date), → which of our parquet date ranges are post-cutoff (leakage-free for forward eval) vs pre-cutoff (contaminated, backtest=exploratory only).
- [ ] **Step 3:** Commit ADR draft `docs(s52): ADR 0068 Kronos integration — GATE 0 pretrain cutoff clause (T0)`. SPRINT_STATE T0 done.

## Task T1: [ml] optional dep group + lazy-import scaffolding (sonnet)

**Files:** Modify `pyproject.toml`. Test `tests/unit/test_ml_optional_dep.py`.

- [ ] **Step 1: Failing test** — importing `src.signalgen` + all 6 existing strategies + `src.dashboard.backtest_runner` succeeds with torch ABSENT (simulate via import-guard). Assert no top-level torch import outside `src/ml/`.
- [ ] **Step 2:** Add `[project.optional-dependencies] ml = ["torch>=2.2", "transformers>=4.40", "tokenizers", "safetensors", "einops", "huggingface_hub"]` mirroring `[dashboard]`.
- [ ] **Step 3:** Run → existing suite GREEN (torch not installed in dev/CI = baseline). Commit `feat(s52): [ml] optional dep group (C1 lazy isolation T1)`. SPRINT_STATE T1.

## Task T2: src/ml/kronos_adapter.py — torch boundary Protocol (opus)

**Files:** Create `src/ml/__init__.py`, `src/ml/kronos_adapter.py`. Test `tests/unit/test_kronos_adapter.py`.

- [ ] **Step 1: Failing test** — `KronosAdapter` Protocol: `predict(ohlcv_df, lookback, horizon) -> list[Decimal]` (predicted closes). Mock the torch/KronosPredictor internals; assert adapter returns Decimal (not float/tensor), handles MPS device param, raises clean ImportError if torch absent ("pip install .[ml]").
- [ ] **Step 2:** Implement adapter — ONLY file importing torch (lazy, inside methods). Wraps `KronosPredictor(model, tokenizer, device="mps", max_context)`. `predict()` → cast `Decimal(str(x))` at boundary (C6). Protocol + concrete `KronosModelAdapter` + `MockKronosAdapter` (deterministic fake for tests/CI).
- [ ] **Step 3:** Run GREEN (mock). mypy strict. Commit `feat(s52): kronos_adapter torch boundary + Decimal cast + mock (C2+C6 T2)`. SPRINT_STATE T2.

## Task T3: predict-cache infra + determinism (opus)

**Files:** Create `src/ml/prediction_cache.py`. Test `tests/unit/test_prediction_cache.py`.

- [ ] **Step 1: Failing test** — cache key = `(model_id, weights_hash, symbol, timeframe, bar_close_ts, params_hash, device)`. `get(key)` hit/miss; `put(key, prediction)`; SHA-256 checksum sidecar (S51 D2 pattern); key mismatch → miss (never stale/foreign-device reuse, C4 data-integrity). Determinism: same input+seed → same cached value.
- [ ] **Step 2:** Implement cache (JSON/parquet artifact keyed). torch seed + sample_count≥20 + median ensemble (V4) computed at cache-build, stored deterministic. Checksum verify on read.
- [ ] **Step 3:** Run GREEN. Commit `feat(s52): prediction-cache + determinism (seed+median+checksum) (C3+C4+V4 T3)`. SPRINT_STATE T3.

## Task T4: src/signalgen/kronos_strategy.py — on_bar consumer (opus)

**Files:** Create `src/signalgen/kronos_strategy.py`. Modify `src/risk/reason_codes.py` (+2). Test `tests/unit/test_kronos_strategy.py`.

- [ ] **Step 1: reason codes** — `ENTRY_LONG_KRONOS` + `EXIT_FLAT_KRONOS` (canonical enum 65→67). Test count 67.
- [ ] **Step 2: Failing tests** — `KronosStrategy.on_bar(bar)` does cache-LOOKUP (no torch import in this file), signal rule V3: predicted_close[horizon=1] > current_close × (1+threshold) → ENTRY_LONG_KRONOS; predicted_close < current → EXIT_FLAT_KRONOS. LOCKED threshold (≥0.25% = 2× round-trip cost). Cache-miss → None (no trade, no block). is_closed gate, generated_at≥bar_close, long-only.
- [ ] **Step 3:** Implement. NO torch import (depends on adapter+cache only). Append-before-compute, look-ahead-safe.
- [ ] **Step 4:** Run GREEN. mypy. Commit `feat(s52): KronosStrategy on_bar cache-consumer + 2 reason codes (V3+C7 T4)`. SPRINT_STATE T4.

## Task T5: RAW_PRETRAIN_LEAKAGE_SUSPECTED verdict class (sonnet)

**Files:** Modify verdict enum/handling (grep `RAW_FULL_PERIOD` — mirror ADR 0062 pattern). Test.

- [ ] **Step 1: Failing test** — new verdict `RAW_PRETRAIN_LEAKAGE_SUSPECTED` exists, distinct from WFA_PASS/FAIL/RAW_FULL_PERIOD; carries honest explanation string.
- [ ] **Step 2:** Add verdict where RAW_FULL_PERIOD defined. Honest label: "Kronos pretrained on history possibly overlapping backtest period — WFA OOS invalid, exploratory only, NOT a gate."
- [ ] **Step 3:** Commit `feat(s52): RAW_PRETRAIN_LEAKAGE_SUSPECTED verdict class (CC1 T5)`. SPRINT_STATE T5.

## Task T6: kronos_runner exploratory backtest (research path, sonnet)

**Files:** Create `src/backtest/kronos_runner.py` (exploratory — NOT run_research_wfa formal, per V5). Test `tests/unit/test_kronos_runner.py`.

- [ ] **Step 1: Failing test** — `run_kronos_exploratory(symbol, timeframe, params)` replays prediction-cache through backtest, returns dict verdict=RAW_PRETRAIN_LEAKAGE_SUSPECTED. Does NOT call `run_research_wfa`, does NOT append cross_trial_sharpes (V5 — no formal N_trials). Uses mock adapter in test.
- [ ] **Step 2:** Implement — cache-replay backtest kernel, open[i+1] fill (S50/S51 look-ahead lesson), exploratory verdict.
- [ ] **Step 3:** Run GREEN. Commit `feat(s52): kronos_runner exploratory backtest (cache-replay, no formal N_trials) (V5 T6)`. SPRINT_STATE T6.

## Task T7: cache-build + exploratory backtest script (operator M4, sonnet)

**Files:** Create `scripts/run_kronos_s52.py` (operator runs with RUN_ML=1 on M4 MPS).

- [ ] **Step 1:** Script: for each of 11 combos — load parquet, build prediction-cache via real KronosModelAdapter (mini, mps), run kronos_runner exploratory, write results JSON. Guarded `if not RUN_ML: skip` (no torch in CI).
- [ ] **Step 2:** Document in script header: operator runs `RUN_ML=1 .venv/bin/python scripts/run_kronos_s52.py` on M4 after `pip install .[ml]`. Cache artifacts → gitignored `data/kronos_cache/`.
- [ ] **Step 3:** Commit `feat(s52): run_kronos_s52 cache-build + exploratory script (operator M4 MPS) (T7)`. SPRINT_STATE T7.

## Task T8: dashboard presets — Kronos per combo, RAW label (sonnet)

**Files:** Modify `src/dashboard/backtest_runner.py` STRATEGY_PRESETS + dispatch. Test.

- [ ] **Step 1: Failing test** — 11 Kronos presets in STRATEGY_PRESETS (one per combo OR one parametric `kronos` with supported_combos = all 11). type=kronos, RU description with honest RAW_PRETRAIN_LEAKAGE_SUSPECTED note, optgroup "ML / Прогноз". /api/strategies includes kronos.
- [ ] **Step 2:** Add preset(s). Dispatch branch `type==kronos` → kronos_runner exploratory (mock if no cache; honest "run cache-build first" message if cache absent). Mirror existing preset schema.
- [ ] **Step 3:** Run GREEN + frontend build. Commit `feat(s52): Kronos dashboard presets (11 combos, dropdown, RAW label) (T8)`. SPRINT_STATE T8.

## Task T9: CI mock + opt-in integration test (sonnet)

**Files:** `tests/integration/test_kronos_ml.py` (opt-in RUN_ML). CI workflow note.

- [ ] **Step 1:** Mock-based unit coverage already in T2-T6. Add `@pytest.mark.integration` real-inference test gated `RUN_ML=1` (operator M4). Default pytest skips. CI = no torch/weights/MPS.
- [ ] **Step 2:** Commit `test(s52): opt-in RUN_ML integration test + CI mock isolation (C5 T9)`. SPRINT_STATE T9.

## Task T10: ADR 0068 finalize + wiki sync (sonnet)

**Files:** Finalize ADR 0068, `src/ml/` component cluster, sprint-52 page, index, log, current-state, mental-map.

- [ ] **Step 1:** ADR 0068 full (C1-C7 + V1-V5 + ESC-1=A + expanded multi-combo + pretrain clause). status accepted.
- [ ] **Step 2:** Component pages kronos-strategy + kronos-adapter + prediction-cache. New `src/ml/` cluster in components/README.md + mental-map. current-state: reason codes 65→67, +[ml] stack, sprint pages +1, flip "XGBPredictor src/ml/ deferred" line. sprint-52 page. index ADR 0068 + sprint. log entry.
- [ ] **Step 3:** Commit `docs(s52): ADR 0068 accepted + wiki sync (T10)`. SPRINT_STATE phase=5-verify.

---

## PHASE 5 gates
pytest GREEN (mock, no torch) + mypy --strict 0 + reason codes 67 + frontend build + CI mock-isolation verified (suite passes torch-absent).

## PHASE 6 reviewers (parallel)
architecture (C1-C7 met) + quant-stats (C3/C4 determinism + leakage honesty) + trading-logic (signal rule + look-ahead + cache-miss FSM safety) + data-integrity (cache provenance C4) + python + test-engineer + bybit-api (n/a) + security (weights download path) + doc.

## PHASE 8 ship
tag v0.1.0-alpha.52. Operator runs cache-build on M4 post-merge → exploratory results → (future) forward paper-trade → formal hypothesis #11 ADR.

## Self-Review
- C1-C7 → T1(C1)/T2(C2,C6)/T3(C3,C4)/T4(C7)/T9(C5). V1-V5 → T0(V1 cutoff)/T2(V2 mini)/T4(V3 signal)/T3(V4 determinism)/T6(V5 exploratory). ESC-1=A → T5+T6 (RAW, no formal N_trials). Expanded scope → T7+T8 (11 combos).
- Compute constraint honored: all dev/CI mocked, real inference = operator M4 script (T7).
- Sequential dispatch (S50/S51 lesson). torch never in hot path / CI.
