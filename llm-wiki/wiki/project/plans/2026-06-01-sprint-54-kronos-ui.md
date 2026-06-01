# Sprint 54 — Kronos UI: cached-coverage auto-fill + uncached-TF block

> subagent-driven, sequential. TDD. Dashboard feature (backend manifest v2 + coverage API + React).

**Goal:** When operator picks Kronos + a cached timeframe (1h/5m), the dashboard auto-fills START/END to that combo's cached window (so backtest hits cache → trades + equity render). Uncached timeframes (15m) are blocked with an honest "not built" message.

**Operator asks (binding):**
1. Kronos + 1h → auto-fill period = cached window; render trade chart + all trade params.
2. Kronos + 5m → same.
3. Kronos + 15m → BLOCKED (no cache built).
4. Merge to main to close sprint.

## Design

**Manifest v2 (per-combo self-describing)** — current v1 has single top-level params_hash + no date range; cannot support mixed sample_count across TFs nor expose coverage dates. v2: each `combos[]` entry carries `{symbol, timeframe, model_id, weights_hash, params_hash, device, first_bar_ts, last_bar_ts, n_entries}`. Dispatch picks the matching combo entry → uses ITS key params + exposes its date range. Back-compat: read v1 (top-level params) as fallback.

**Coverage API** — expose per-(symbol,timeframe) cached date range + availability so frontend can auto-fill + gate. Extend `/api/strategies/{id}` (kronos) response with `coverage: [{symbol, timeframe, start_iso, end_iso, n_entries}]`, OR new `/api/kronos/coverage`.

**Frontend (ConfigureBacktest.tsx)** — on strategy=kronos + (symbol,timeframe) change: look up coverage; if combo present → set START/END inputs to its start_iso/end_iso + enable EXECUTE; if absent (15m or uncached) → disable EXECUTE + show "Kronos {tf} не построен — запусти cache-build" note.

## Tasks

### T1 — manifest v2 + script + backfill (backend)
- `scripts/run_kronos_s53.py` `_write_manifest`: write per-combo `{model_id, weights_hash, params_hash, device, first_bar_ts, last_bar_ts, n_entries}` (compute first/last bar_close_ts of the built window). Bump MANIFEST_SCHEMA_VERSION=2. Merge by (symbol,timeframe) preserved.
- One-off backfill: upgrade the existing `data/kronos_cache/_manifest.json` (v1, 5m, 33467 entries) to v2 — compute first/last ts from the 5m parquet's last n_entries bars. (Standalone snippet or a `--rebuild-manifest` flag; keep minimal.)
- Tests: manifest v2 shape; backfill correctness.

### T2 — dispatch per-combo + coverage API (backend)
- `src/dashboard/_kronos_dispatch.py`: read the matching v2 combo entry for (model_id, symbol, timeframe) → use its params_hash/weights_hash/device for CacheKey reconstruction. v1 fallback (top-level) preserved. Add `kronos_coverage(cache_dir) -> list[dict]` helper returning `[{symbol, timeframe, start_iso, end_iso, n_entries}]`.
- `src/dashboard/app.py`: expose coverage — extend `/api/strategies/{id}` for kronos OR add `/api/kronos/coverage`. Return ISO date ranges.
- Tests: dispatch hits cache via per-combo params; coverage endpoint shape.

### T3 — frontend auto-fill + block (React)
- `src/dashboard_react/src/api/` (client.ts + types.ts): fetch coverage type.
- `src/dashboard_react/src/components/forms/ConfigureBacktest.tsx`: on kronos + (symbol,tf) → autofill START/END from coverage, enable EXECUTE; uncached tf → disable EXECUTE + RU "not built" message. 15m specifically blocked (no cache).
- Vitest: autofill + disable logic. tsc + build clean.

### T4 — verify + review + ship
- pytest GREEN, mypy 0, Vitest + tsc + build clean.
- Reviewers: dashboard-reviewer (primary) + python-reviewer + data-integrity (manifest provenance).
- ADR note (manifest v2) + wiki sync. Ship to main, tag v0.1.0-alpha.54.

## Constraints
- Backend Decimal/torch-free in dispatch. Manifest v2 back-compat with v1. Exploratory verdict unchanged (RAW_PRETRAIN_LEAKAGE_SUSPECTED). No look-ahead introduced (display only).
