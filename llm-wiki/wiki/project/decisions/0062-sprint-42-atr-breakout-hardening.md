---
title: "0062. Sprint 42 — atr_breakout production hardening (kit retrofit)"
type: decision
tags: [adr, sprint-42, dashboard, atr-breakout, retrofit, contract]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s42-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-42-atr-breakout-hardening.md
---

# 0062. Sprint 42 — atr_breakout production hardening (kit retrofit)

**Status:** accepted
**Date:** 2026-05-10
**Supersedes:** [[0060-sprint-40-atr-breakout-pre-registration]], [[0061-sprint-41-atr-breakout-multi-combo-presets]]

## Контекст

S40 + S41 поставили atr_breakout strategy в dashboard через bypass kit (operator overnight rule "не используй кит"). Operator затем обнаружил три класса проблем:

1. **UI crash:** dashboard.js бросает `Cannot read properties of undefined (reading 'toLocaleString')` при выборе любого atr_breakout preset. Корень: `atr_breakout_runner` returns 8 ключей, dashboard ожидает 17 (replay engine contract). Аналогичный crash для volume_breakout (S39).
2. **UX clutter:** S41 добавил 9 separate presets per (symbol, TF) — 10 entries в dropdown. Операторы недовольны шумом.
3. **Acceptance discipline gap:** atr_breakout bypasses WFA + DSR + MC + T1-T6 acceptance gate. Inflated raw full-period PnL отображается без OOS validation.

## Варианты

(a) **Full WFA retrofit за один sprint** — restore acceptance discipline, fix crash, consolidate presets. Maintainer initial recommendation.

(b) **Crash fix + RAW_FULL_PERIOD honest label, defer WFA к S43** — split в 2 sprints. Acknowledge structural PnL accounting gap (sequential-additive vs Kelly-compounded) перед WFA wrapping. Trader-expert ROUND 1 EXPAND verdict.

(c) Ignore — accept current state с manual UI workarounds.

## Решение

**Option (b) — split в S42 (immediate fix) + S43 (WFA retrofit).**

Rationale: trader-expert ROUND 1 highlighted что atr_breakout_runner uses sequential-additive PnL accounting, while replay engine uses Kelly-sized compounded PnL. Wrapping WFA folds на incompatible PnL accounting = silent contract violation. PASS verdict from such a run = structurally misleading. WFA retrofit MUST resolve underlying gap (atr_breakout_runner.py:6-12 documented gaps) перед wrapping.

S42 scope (THIS ADR):
1. Crash fix — `build_research_runner_envelope()` helper (новый модуль `src/backtest/research_runner_envelope.py`) wraps research runners (atr_breakout, volume_breakout) к dashboard 17-key contract. Returns null sentinels для acceptance_gate / DSR / MC + high-level "raw_full_period" warning chip.
2. Preset consolidation — 10 atr_breakout_* presets → 1 unified `atr_breakout` preset с `supported_combos: list[tuple[str, str]]`. Server-side params lookup в `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)]`.
3. Frontend gates — новый endpoint `GET /api/strategy/{id}/info` exposes `supported_combos`. JS вызывает `applyComboGates()` — greys out invalid (sym, TF) options dynamically.
4. Sub-period robustness chip — N/5 positive periods отображается как warning chip (info/warn/high).
5. Honest label — `RAW_FULL_PERIOD — WFA retrofit pending S43` warning chip + `verdict: "RAW"` (не PASS/FAIL).
6. Same envelope wrap для volume_breakout (S39) — unified contract.
7. Backward compat — full replace 10 preset_ids, no aliases (project в alpha v0.1.0-alpha.x).
8. JS defensive guards — `r.bars_per_year ?? 0`, `r.failed_criteria ?? []`, `r.verdict ?? "—"` — prevent future contract drift crashes.

S43 scope (deferred):
- Resolve atr_breakout_runner.py:6-12 structural PnL accounting gaps (sequential-additive → Kelly-compounded OR refactor replay engine к support both).
- Wrap full WFA folds + DSR + MC permutations + T1-T6 acceptance gate.
- N_trials counter increment (S40+S41+S42 = each combo separate hypothesis vs ensemble).
- Restore epistemic discipline.

## Последствия

**Pros:**
- Crash fixed — operators могут использовать atr_breakout/volume_breakout presets без JS errors.
- UX cleaner — 1 preset вместо 10 в dropdown.
- Honest disclosure (`RAW_FULL_PERIOD` chip + verdict=RAW) prevents over-trust в inflated training PnL.
- Scope contained — single architectural fix S43 covers WFA retrofit для both runners.
- JS defensive coding — prevents future contract drift крушения.

**Cons:**
- Acceptance discipline temporarily skipped для atr_breakout + volume_breakout. S43 must follow within 1-2 sprints to restore.
- Backward compat broken — bookmarked URLs к old preset_ids (10 IDs) → 422. Mitigated: alpha release, не prod.

**Carry-overs к S43:**
- Full WFA retrofit для atr_breakout + volume_breakout runners.
- DSR computation per combo (или ensemble).
- MC permutation tests.
- N_trials counter increment в cross-trial.
- Resolve PnL accounting gap (sequential-additive vs Kelly-compounded).

## Verification

- Unit tests: 946 passed (+41 vs pre-S42 baseline 905). Includes 6 envelope contract + 6 supported_combos endpoint tests.
- Integration tests: 52 passed (+19). Includes 14 dashboard contract + parametrized PnL replication для всех 10 supported combos.
- mypy --strict: 0 errors на 84 source files.
- Canonical counts: 16/30/74/56 (UNCHANGED — pure refactor).
- Manual smoke: dashboard `/api/strategy/atr_breakout/info` возвращает 10 supported_combos. Backtest BTCUSDT 4H возвращает envelope с `verdict: RAW`, `bars_per_year: 2191`, `warnings: [raw_full_period, subperiod_robustness 5/5]`.

## Связанные

- [[../sprints/sprint-42-atr-breakout-hardening]]
- [[../plans/2026-05-10-sprint-42-atr-breakout-hardening]]
- [[../pre-s42-backlog]]
- [[0052-sprint-34-acceptance-criteria-amendment]] (T1-T6 acceptance gate, restored S43)
- [[0060-sprint-40-atr-breakout-pre-registration]] (superseded)
- [[0061-sprint-41-atr-breakout-multi-combo-presets]] (superseded)
- [[../components/atr-breakout-strategy]] (renamed preset_id)
