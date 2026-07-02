# Depth review — equity-chart-and-drawdown.md (CORRECTNESS vs code)

Page: `docs/08-дашборд/equity-chart-and-drawdown.md` (money_core: true)
Reviewer axis: factual correctness against `src/`. Readability owned by another pass.
Date: 2026-06-27

Verdict: **REQUEST_CHANGES** (1 BLOCKER + 2 WARN + 1 DEEP)
Recomputed numbers: 6 worked examples (all exact) + empirical scan of 52 cached run JSONs.

---

## BLOCKER

### B1 — Pitfall #2: "VectorBacktester-путь" inverts which path returns null; names a path that isn't in the flow; misquotes the code comment
Doc lines 214-215 (and TL;DR-adjacent framing in Шаг 1 line 50):
> "Маркеры сделок — только в части бэктестов (replay-путь), не во всех. В текущей реализации поле `trade_markers` приходит как `null` в результатах быстрого бэктеста (**VectorBacktester-путь**). Точки сделок появляются только тогда, когда данные заполнены полностью. (src/dashboard/backtest_runner.py:1436 — `"trade_markers": None` **для vector-пути**)"

Three independent factual errors:

1. **"VectorBacktester-путь" is not part of the dashboard backtest flow at all.**
   `class VectorBacktester` lives in `src/backtest/vector_backtest.py:9` but is imported **nowhere** outside its own file (`grep -rln VectorBacktester src/ --include=*.py` → only `vector_backtest.py`). The word "vector" appears **zero** times in `src/dashboard/backtest_runner.py`. So naming a "VectorBacktester path" as the source of `null` markers is a fabricated entity for this flow.

2. **The attribution is inverted — the null-markers path IS the replay path.**
   The generic dashboard path that hardcodes `"trade_markers": None` (`backtest_runner.py:1436`, inside `_run_backtest_locked` def@937) builds its series from `run_wfa_single_symbol` (`backtest_runner.py:1216`), which internally uses **`replay_engine` / `run_replay`** (`src/backtest/data_loading.py:22,152`). The code's own comment at `backtest_runner.py:1432` literally says: `# ... trade_markers deferred (replay path).` — i.e. the deferral is on the **replay path**, the exact opposite of the doc's "для vector-пути".

3. **The paths that DO populate markers are also replay-based, and are specific research strategies — not a "replay vs vector" dichotomy.**
   `trade_markers` is populated only via `research_runner_envelope.build_research_runner_envelope` (`src/backtest/research_runner_envelope.py:196`), fed by `volume_breakout_runner.py:278-303` and `atr_breakout_runner.py:383-411`. Those dispatch branches ALSO "run full-period **replay**" (`backtest_runner.py:983,1052`). So the real split is *"research-envelope strategies (volume_breakout / atr_breakout) CAN populate markers"* vs *"generic WFA path hardcodes None"* — both are replay-based; neither is "VectorBacktester".

4. **The parenthetical is a misquote.** Doc cites `:1436 — "trade_markers": None для vector-пути`. The adjacent comment (line 1432) says "replay path", not "vector". The `"trade_markers": None` literal at 1436 is correct, but the gloss is wrong.

Empirical corroboration (52 cached run JSONs in `data/runs/`): **0 runs have a populated `trade_markers` dict.** All are `null` or the key is absent (older format) — including every `atr_breakout` run. So in practice markers are essentially never present, which makes the doc's "appear on the replay/full path" claim doubly misleading (a reader is told the opposite of reality about where to expect dots).

Why BLOCKER (not WARN): the directional gist ("markers usually absent") is fine, but the page makes three confidently-stated, code-contradicting claims — a fabricated path name, an inverted attribution, and a misquoted comment — that a non-programmer cannot detect and would internalize as "I'll see trade dots in full/replay backtests" (they generally won't) and "there's a fast VectorBacktester mode" (there isn't, in this flow).

**Fix suggestion:** replace with: markers are populated only for the research-runner strategies (volume_breakout, atr_breakout) via `research_runner_envelope` (`:196`); the generic WFA/replay path hardcodes `trade_markers: None` (`backtest_runner.py:1436`, comment "deferred"), so most presets render no dots. Drop "VectorBacktester" entirely.

---

## WARN

### W1 — Footer pointer to a non-existent component doc
Doc line 241: "За техническими деталями компонента: `llm-wiki/wiki/project/components/dashboard.md`".
`llm-wiki/wiki/project/components/dashboard.md` **does not exist** (`find` → only `dashboard-reviewer-agent.md`, which documents the reviewer agent, not the chart component). Broken pointer. (Navigation defect; other pass owns nav, hence WARN.)

### W2 — "вдвое меньше основного графика" is loose
Doc line 100: DrawdownSubchart default height 140 px described as "(вдвое меньше основного графика)". Main default = 320 (EquityChart.tsx:138). 320/140 = 2.29×, not 2×. Approximate; the exact numbers (140 / 320) are both stated correctly elsewhere, so low harm. Consider "более чем вдвое меньше" or drop the parenthetical.

---

## DEEP

### D1 — CJK characters leaked into Russian prose (garbled token), but factual content is correct
Doc line 78: "Линия между точками отключена (`paths: () => null`) — только**散點图** (scatter plot)." The Chinese "散點图" (= "scatter plot") is embedded with no leading space ("только散點图"). The underlying code claim is correct (`paths: (() => null)` at EquityChart.tsx:80/88 disables line; markers are a scatter series, `points.size: 6` at :81/:89). This is a rendering/quality artifact rather than a code-fact error — flagged so the readability pass catches it; not severity-bearing on the correctness axis.

---

## VERIFIED CORRECT (high-signal — do not re-flag)

Code citations — all exact:
- `_compound_equity_pct` body + range `:383–394`; code block (doc 36-42) byte-matches source 389-394. ✓
- `_compound_balance` `:371–380`; geometric Π(1+pnl). ✓
- `equity_curve` dict `:1433–1436` (timestamps / equity_pct / trade_markers). ✓
- Length-invariant ValueError in `get_run` `:1504–1518` ("при отдаче данных"). ✓
- `TradeMarkers` interface 5 arrays `types.ts:49–55`. ✓
- `EquityChart` def `:138`; defaults height=320, initialBalance=10000. ✓
- Equity stroke `#cc785c` / fill `rgba(204,120,92,0.12)` `:62–63`. ✓
- `buildMarkerSeries` `:27–53`; O(N+M) (comment :28). ✓
- Marker colors green `#00ff88` (pnl>0) / red `#ff3366` (pnl<=0 → "нулевым или отрицательным", code `if (pnl>0) wins else losses` :45-49). ✓
- Point size 6 (`:81,:89`); `paths: () => null` (`:80,:88`). ✓
- Tooltip date `new Date(ts*1000).toISOString().slice(0,10)` `:191`; balance `initialBalance*(1+eq/100)` `:194`; DOM API no innerHTML `:202–215`. ✓
- `DrawdownSubchart` def `:75`; height default 140 (`:78`). ✓
- `computeDrawdown` code block (doc 105-114) byte-matches source `computeDrawdown.ts:5–15`; "always ≤ 0" holds (peak>0 guard, v≤peak). ✓
- DD tooltip `${date} · DD: ${dd.toFixed(2)}%` `:127`. ✓
- DD color `#ff3366` / fill `rgba(255,51,102,0.15)` `:25–26`. ✓
- Sync `{ key: syncKey, setSeries: false }` (EquityChart :109 / Drawdown :46). ✓
- ResizeObserver `newWidth > 0` guard (EquityChart :229–237 / Drawdown :139–147). ✓
- Empty-state placeholder text "No equity data available — legacy WFA preset без envelope" `:250`. ✓
- M1/S49 geometric-compounding provenance (docstrings "M1 (S49)" :374,:386). ✓

Recomputed numeric examples (Bash, `.venv/bin/python`) — all exact:
- Пример 1 (+10%,−5%,+8%) → 10.0 / 4.5 / 12.86. ✓
- 3×(+10%) = 1.1³−1 = 33.1%. ✓
- balance 15.3% → 11530; +12% → 11200. ✓
- drawdown +20%→+8% ≈ −10%; +50%→+35% ≈ −10% (pitfall #3 correctly NOT −15%). ✓

Wikilinks — all 6 resolve (run-backtest-form, metrics-table-tiers, verdict-and-warnings, wfa-methodology, trade-statistics, monthly-heatmap, all in docs/08-дашборд/). ✓
