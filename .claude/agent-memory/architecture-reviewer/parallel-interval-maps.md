---
name: Parallel hardcoded interval maps — 4 drift sites in src/
description: Four independent interval maps in rest.py + __main__.py must be extended atomically for each new timeframe.
type: project
---

## Pattern observed (S22 brainstorm review, 2026-04-26)

S19 Condition A1 solved interval_map drift WITHIN rest.py (single-dict refactor).
But the bootstrap layer (__main__.py) introduced its own parallel map duplication.

### Four sites that must be extended atomically for each new timeframe:

1. `src/marketdata/bybit/rest.py::get_klines` — `intervals: dict[str, tuple[str, int]]`
   - Controls: paginator domain label + step_ms for pagination math
2. `src/__main__.py` — `bars_per_year_map: dict[str, int]` (line ~610)
   - Controls: annualization factor (Sharpe correctness — silent wrong-result on miss)
3. `src/__main__.py::_resolve_heal_max_age` — `interval_seconds_map: dict[str, int]` (line ~189)
   - Controls: Reconciler heal window (loud KeyError crash on miss)
4. `src/__main__.py` — two `choices=["60", "15"]` in argparse (lines ~785, ~812)
   - Controls: CLI validation gate (argparse rejects unknown interval at CLI level)

### Values for 4H ("240"):
- rest.py: `"240": ("4h", 14_400_000)`
- bars_per_year_map: `"240": 2190` (8760 / 4)
- interval_seconds_map: `"240": 14400`
- choices: add "240" to both wfa + backfill subcommand parsers

**Why:** Partial extension (e.g. only rest.py) causes silent wrong-Sharpe (bars_per_year_map) or loud
crash (interval_seconds_map KeyError). Must be single atomic commit.

**How to apply:** When reviewing any PR that adds a new timeframe — grep for all 4 sites.
Long-term fix: consolidate into single INTERVAL_REGISTRY module with named tuple
(label, step_ms, bars_per_year, step_seconds). Justified at 5+ timeframes, YAGNI at 3.
