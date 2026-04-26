# Architecture Reviewer — Persistent Memory

- [Project concurrency model](concurrency-model.md) — sync+threading canonical; RLock Coordinator, Lock Reconciler; WS thread + main tick thread
- [DI wiring patterns S11](di-wiring-s11.md) — _cmd_run DI graph + endpoint bug pattern + MagicMock-in-prod anti-pattern
- [Multi-timeframe + multi-symbol gaps S15](multi-timeframe-multi-symbol-s15.md) — Kelly symbol-filter blocker, rest.py interval_map, heal_max_age coupling, BarSource already multi-TF, dead ws.py
- [Annualization factor hardcoding gap](annualization-factor-gap.md) — sqrt(8760) wrong at 15M (2× underestimate); parameterize via bars_per_year from interval config; quant-stats-reviewer required
- [heal_max_age_seconds interval coupling fix](heal-max-age-pattern.md) — replace seconds constant with heal_max_bars=1 bar-count; derive seconds at bootstrap; ADR required; operator .env migration warning
- [Cheap-test-first sequencing principle](option-a-b-sequencing.md) — confirmed v0.4+v0.5: cheap falsification (1-2 sprint) precedes expensive construction (5-10 sprint); AND-gate frequency floor must be probed offline before committing sprint
- [Parallel interval maps — 4 drift sites](parallel-interval-maps.md) — rest.py intervals + __main__.py bars_per_year_map + interval_seconds_map + argparse choices must be extended ATOMICALLY per new timeframe; partial extension = silent wrong-Sharpe or crash
- [Dashboard Presentation context — S25](dashboard-context-s25.md) — src/dashboard/ = new DDD Presentation context; FastAPI+uvicorn separate process from bot; optional deps group; background thread + Lock for backtest execution
