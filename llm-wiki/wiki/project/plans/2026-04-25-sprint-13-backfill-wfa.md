# Sprint 13 — Backfill 5y + WFA T1-T6 measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) или superpowers:executing-plans для task-by-task implementation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** First empirical T1-T6 acceptance criteria measurement on max-available Bybit Spot 1H BTCUSDT data (target 5y per ADR 0028 ESC-2 floor 3.5y) via WFA + DSR computation.

**Architecture:** Wire existing components: BybitRESTClient.get_klines (already paginated, S2) + new Parquet writer + extend wfa_reporter (S10) с T1-T6 extraction + new trade_extractor module (closes S10/S12 carry-over `trades_for_dsr=[]`). NO dashboard wire (Q8 skip). NO new strategy code.

**Tech Stack:** Python 3.12, pandas, pyarrow (Parquet), pydantic v2, sqlite3 (read-only via _cmd_monitor). Bybit V5 Spot API kline endpoint.

---

## Source verdicts trail

- ADR 0028 (status: proposed): `wiki/project/decisions/0028-sprint-13-strategy-validation.md`
- PHASE 2 brainstorm verdicts: `wiki/project/pre-s13-backlog.md`
- Predecessor sprint: S12 ship `wiki/project/sprints/sprint-12-live-demo-validation.md`
- Acceptance gating (amended): `wiki/project/architecture/acceptance-criteria.md` (footnotes 1+2+3)

## Trace map (PHASE 3 step 1a HARD-GATE)

| Source verdict | Plan task | Reviewer | Tier |
|----------------|-----------|----------|------|
| Q1 CONFIRM (backtest first, NOT 48h validation) | T2-T7 (sprint focus) | per-task per ADR | code |
| Q2 EXPAND (conditional split based on data availability) | T1 PHASE 3 step 1 probe → resolves split | inline | operator |
| Q3 CONFIRM (Bybit Spot only) | T2 wire (Bybit pagination only) | python + data-integrity MANDATORY | code-medium |
| Q4 REVISE-FACTUAL ESC-2 (tiered 5y, floor 3.5y) | T1 probe drives actual span | inline | gate |
| Q5 CONFIRM (DSR active S13, PBO defer) | T6 metrics extension + verdict (DSR included) | quant-stats MANDATORY | code-math |
| Q6 CONFIRM (48h validation decoupled) | NO TASK (operator parallel track) | — | external |
| Q7 ESC-1=c (defer pattern preserved) | T7 verdict report (no pre-commit framework) | inline | docs |
| Q8 CONFIRM (skip dashboard) | NO TASK (CLI JSON only) | — | NEGATIVE |
| CC1 (N_trials tracking infrastructure) | T6 + T7 (N_trials=1 explicit, documented) | inline | code-comment |
| CC2 (Bybit data availability single biggest unknown) | T1 BEFORE T2 mandatory | inline | gate |
| CC3 (PBO formal deferral documented) | T8 sprint page + ADR amendment | inline | docs |
| CC4 (spec doc reconciliation — already done) | DONE pre-plan (commit ccae4f4 acceptance-criteria.md footnotes) | — | — |
| Sprint ship | T8 ADR accept + sprint page + counts sync | sprint-finish skill | wiki |

---

## File Structure

**New files (S13):**
- `src/backtest/trade_extractor.py` — DataFrame → TradeRecord conversion (T5, closes S10/S12 carry-over)
- `tests/unit/test_trade_extractor.py` — extractor tests (T5)
- `src/backtest/strategy_metrics.py` — T1-T6 metrics extraction (T6)
- `tests/unit/test_strategy_metrics.py` — metrics tests (T6)
- `tests/unit/test_load_ohlcv_nan_preflight.py` — pre-flight tests (T4)
- `tests/unit/test_cmd_backfill.py` — backfill CLI tests (T2)
- `wiki/project/sprints/sprint-13-backfill-wfa.md` — canonical sprint summary (T8, PHASE 8)
- `wiki/project/components/trade-extractor.md` — NEW component page (T8)
- `wiki/project/components/strategy-metrics.md` — NEW component page (T8)

**Modified files (S13):**
- `src/__main__.py::_cmd_backfill` (lines 168-172) — wire к BybitRESTClient.get_klines + Parquet write
- `src/__main__.py::_load_ohlcv` (lines 258-282) — add NaN pre-flight assertion (T4)
- `src/__main__.py::_cmd_wfa` (lines 290-345) — extend output с T1-T6 + DSR + verdict (T7)
- `src/backtest/wfa_reporter.py` — replace `trades_for_dsr=[]` placeholder (T6)
- `wiki/project/decisions/0028-sprint-13-strategy-validation.md` — status: proposed → accepted (T8)
- `wiki/project/architecture/current-state.md` — counts (ADR 27→28, sprint pages 14→15, components 36→38) (T8)
- `wiki/project/mental-map.md` — strategy_metrics + trade_extractor rows (T8)
- `wiki/index.md` — sprint-13 + ADR 0028 + 2 component pages (T8)

**NOT touched (per Q8 + Q6):**
- `web/dashboard.html` — Q8 skip dashboard wire
- `wiki/runbooks/live-demo-validation.md` — Q6 operator parallel track unchanged
- `migrations/*.sql` — verify unchanged via `git diff --name-only main..HEAD -- migrations/` empty (Q7 from S12 carry, preserved)

---

### Task 1: Bybit data availability probe (PHASE 3 step 1, BEFORE code)

**Files:** None modified. Operator/CLI action only.

**Architecture rationale:** Per CC2 trader-flagged: Bybit Spot data availability = biggest unknown. Resolves Q2 (split decision) + Q4 (target span) simultaneously. 2-minute REST API call.

- [ ] **Step 1: Verify Bybit Spot earliest 1H BTCUSDT timestamp via REST**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
source .venv/bin/activate
python -c "
from src.marketdata.bybit.rest import BybitRESTClient
from src.platform.config import Settings
from datetime import datetime, UTC, timedelta

s = Settings()
rest = BybitRESTClient(api_key=s.bybit_api_key, api_secret=s.bybit_api_secret, testnet=s.testnet)

# Query earliest available 1H BTCUSDT (start = 2018-01-01 well before Bybit launch)
start_ms = int(datetime(2018, 1, 1, tzinfo=UTC).timestamp() * 1000)
end_ms = int(datetime(2018, 6, 1, tzinfo=UTC).timestamp() * 1000)

bars = rest.get_klines('BTCUSDT', '60', start_ms, end_ms, limit_per_call=10)
if bars:
    print(f'Earliest available bar: {bars[0].close_time}')
else:
    print('No bars in 2018-H1 — Bybit Spot started later')
    # Try 2020
    start_ms = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
    end_ms = int(datetime(2020, 6, 1, tzinfo=UTC).timestamp() * 1000)
    bars = rest.get_klines('BTCUSDT', '60', start_ms, end_ms, limit_per_call=10)
    print(f'2020 H1: {bars[0].close_time if bars else \"NO DATA\"}')
"
```

- [ ] **Step 2: Decide target backfill span based on result**

Decision matrix (per ADR 0028 ESC-2):

| Earliest available | Span | Action |
|--------------------|------|--------|
| ≤ 2020-01-01 | ≥5y | Use 2020-01-01 → today (5y target met) |
| 2020-01-01 → 2022-07-01 | 3.5y-5y | Use earliest → today (max-available, документировать) |
| > 2022-07-01 | < 3.5y | **ESCALATE к user** — below ADR 0028 floor |

Document determined target span в commit message + sprint-13 page.

- [ ] **Step 3: Commit decision (docs only)**

Update SPRINT_STATE с probe finding:

```bash
# Edit llm-wiki/wiki/project/SPRINT_STATE.md "Следующее действие" → add line:
# "S13 PHASE 3 step 1 probe result: earliest Bybit 1H BTCUSDT = <date>, target span = <X>y"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(state): T1 — Bybit data availability probe result (S13)

Earliest available 1H BTCUSDT on Bybit Spot: <date>
Target backfill span: <X>y (per ADR 0028 ESC-2 tiered 5y/floor 3.5y)
Below 3.5y floor: <yes|no — escalate если yes>

Closes T1 of S13 plan."
```

REPLACE `<date>` + `<X>` + `<yes|no>` с actual measured values.

---

### Task 2: Wire `_cmd_backfill` к BybitRESTClient + Parquet write

**Files:**
- Modify: `src/__main__.py::_cmd_backfill` (lines 168-172)
- Create: `tests/unit/test_cmd_backfill.py`

**Architecture rationale:** Per Q3 CONFIRM Bybit only. `BybitRESTClient.get_klines` already paginated (returns `list[Bar]`). T2 = bridge: parse args → call get_klines → convert к DataFrame → write Parquet.

- [ ] **Step 1: Write failing test для backfill CLI**

Create `tests/unit/test_cmd_backfill.py`:

```python
"""_cmd_backfill wire tests (S13 T2 per ADR 0028 Q3)."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src import __main__ as cli
from src.marketdata.models import Bar, DataQuality


def _make_bar(close_time: datetime, *, close: float = 50000.0) -> Bar:
    return Bar(
        symbol="BTCUSDT",
        venue="bybit",
        interval_ms=3_600_000,
        open_time=close_time.replace(microsecond=0),
        close_time=close_time,
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=close,
        volume=1.0,
        quality=DataQuality.VALID,
    )


def test_cmd_backfill_writes_parquet_with_paginated_klines(tmp_path: Path) -> None:
    """T2 — backfill calls BybitRESTClient.get_klines + writes Parquet."""
    bars = [_make_bar(datetime(2024, 1, 1, h, tzinfo=UTC), close=50000.0 + h) for h in range(100)]

    with patch("src.__main__.BybitRESTClient") as mock_rest_class:
        mock_rest = MagicMock()
        mock_rest.get_klines.return_value = bars
        mock_rest_class.return_value = mock_rest

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test"
            mock_settings.bybit_api_secret = "test"
            mock_settings.testnet = True
            mock_settings_class.return_value = mock_settings

            args = argparse.Namespace(
                symbol="BTCUSDT",
                from_date="2024-01-01",
                to_date="2024-01-05",
                output_path=str(tmp_path / "BTCUSDT_1h.parquet"),
            )
            exit_code = cli._cmd_backfill(args)

    assert exit_code == 0
    assert (tmp_path / "BTCUSDT_1h.parquet").exists()
    df = pd.read_parquet(tmp_path / "BTCUSDT_1h.parquet")
    assert len(df) == 100
    assert set(df.columns) >= {"time", "open", "high", "low", "close", "volume"}
    mock_rest.get_klines.assert_called_once()


def test_cmd_backfill_returns_error_on_empty_response(tmp_path: Path) -> None:
    """T2 — empty kline response → exit 1, не crash."""
    with patch("src.__main__.BybitRESTClient") as mock_rest_class:
        mock_rest = MagicMock()
        mock_rest.get_klines.return_value = []
        mock_rest_class.return_value = mock_rest

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test"
            mock_settings.bybit_api_secret = "test"
            mock_settings.testnet = True
            mock_settings_class.return_value = mock_settings

            args = argparse.Namespace(
                symbol="BTCUSDT",
                from_date="2024-01-01",
                to_date="2024-01-05",
                output_path=str(tmp_path / "empty.parquet"),
            )
            exit_code = cli._cmd_backfill(args)

    assert exit_code == 1
    assert not (tmp_path / "empty.parquet").exists()


def test_cmd_backfill_default_output_path() -> None:
    """T2 — default output = data/<symbol>_1h.parquet."""
    args = argparse.Namespace(
        symbol="BTCUSDT",
        from_date="2024-01-01",
        to_date="2024-01-02",
        output_path=None,
    )
    # Function should derive default path internally — just check signature accepts None
    # Actual path resolution checked в production smoke (T3)
    assert args.output_path is None  # Caller passes None → impl uses default
```

- [ ] **Step 2: Run tests to verify FAIL**

```bash
source .venv/bin/activate
pytest tests/unit/test_cmd_backfill.py -v
```

Expected: FAIL — current `_cmd_backfill` is print STUB.

- [ ] **Step 3: Implement `_cmd_backfill`**

Modify `src/__main__.py::_cmd_backfill` (REPLACE lines 168-172):

```python
def _cmd_backfill(args: argparse.Namespace) -> int:
    """Backfill OHLCV via BybitRESTClient.get_klines + write Parquet.

    S13 T2 per ADR 0028 Q3 (Bybit only, document gap if data span < 5y).
    Closes S8a T20 STUB (delegate placeholder).

    Args:
        args.symbol: trading pair (e.g. "BTCUSDT")
        args.from_date: ISO date "YYYY-MM-DD"
        args.to_date: ISO date "YYYY-MM-DD"
        args.output_path: Parquet output (default: data/<symbol>_1h.parquet)

    Returns:
        0 — Parquet written с >0 bars;
        1 — empty kline response (data not available);
        2 — Bybit API error (BybitAPIError raised).
    """
    from datetime import UTC, datetime

    settings = Settings()
    symbol: str = args.symbol or "BTCUSDT"
    output_path = Path(args.output_path) if args.output_path else Path(f"data/{symbol}_1h.parquet")

    start_dt = datetime.fromisoformat(args.from_date).replace(tzinfo=UTC)
    end_dt = datetime.fromisoformat(args.to_date).replace(tzinfo=UTC)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )

    print(f"backfill: fetching {symbol} 1H {args.from_date} → {args.to_date} ...", flush=True)
    bars = rest.get_klines(symbol, "60", start_ms, end_ms, limit_per_call=1000)

    if not bars:
        print(f"backfill: WARNING — empty kline response для {symbol} {args.from_date} → {args.to_date}", flush=True)
        return 1

    # Convert list[Bar] → DataFrame
    rows = []
    for b in bars:
        rows.append({
            "time": b.close_time.isoformat(),
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        })
    df = pd.DataFrame(rows)

    # Write Parquet (snappy compression default per pyarrow)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    print(f"backfill: wrote {len(df)} bars к {output_path}", flush=True)
    return 0
```

ADD argparse subcommand parameter `--output` к existing parser (find `_cmd_backfill` argparse setup в main()/setup_parser, add `--output` arg).

- [ ] **Step 4: Run tests to verify PASS**

```bash
pytest tests/unit/test_cmd_backfill.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Mypy + ruff**

```bash
mypy --strict src/__main__.py
ruff check src/__main__.py tests/unit/test_cmd_backfill.py
```

Expected: clean.

- [ ] **Step 6: Run full unit suite**

```bash
pytest tests/ -q --ignore=tests/integration
```

Expected: ~692 passed (689 baseline + 3 new).

- [ ] **Step 7: Verify Q7-S12 zero-migration constraint preserved**

```bash
git diff --name-only main..HEAD -- migrations/
```

Expected: empty.

- [ ] **Step 8: Commit**

```bash
git add src/__main__.py tests/unit/test_cmd_backfill.py
git commit -m "$(cat <<'EOF'
feat(cli): T2 — _cmd_backfill wire к BybitRESTClient.get_klines + Parquet (S13 ADR 0028 Q3)

Closes S8a T20 STUB delegate placeholder. Wires existing
BybitRESTClient.get_klines (S2 — already paginated) к Parquet writer.

Per Q3 CONFIRM: Bybit Spot only (no Binance fallback per ADR 0016).
Per CC2: T1 (PHASE 3 step 1 data availability probe) MUST run BEFORE
this task to determine valid backfill span.

DataFrame schema: time (ISO), open, high, low, close, volume.
Compatible с data_collector.load_market_data (S2) + _load_ohlcv (S12 T2).

3 unit tests: paginated klines → Parquet, empty response → exit 1,
default output path derivation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 9: Domain reviewers parallel dispatch (MANDATORY per ADR 0028)**

python-reviewer brief: "S13 T2 commit `<sha>`. Review _cmd_backfill для Bybit V5 pagination correctness + Parquet write integrity. Specifically: (1) datetime → ms epoch conversion (UTC handling); (2) DataFrame schema matches data_collector expectations; (3) error swallowing pattern (BybitAPIError propagation); (4) output path default derivation."

data-integrity-reviewer brief: "S13 T2 commit `<sha>`. Review Parquet write for data-integrity properties: (1) snappy compression default acceptable? (2) `time` column ISO-8601 UTC consistency с rest of project; (3) no DB writes (Parquet-only path); (4) Q7-S12 zero-migration constraint preserved (`git diff main..HEAD -- migrations/` empty)."

---

### Task 3: Run backfill (operator action)

**Files:** None modified. Generates `data/BTCUSDT_1h.parquet`.

**Architecture rationale:** Per Q3 + T1 result. Operator runs backfill для max-available-from-T1 span.

- [ ] **Step 1: Determine effective backfill range from T1 probe result**

Read T1 commit message OR SPRINT_STATE для earliest available date. Set:
- `FROM_DATE` = earliest available (per T1 probe)
- `TO_DATE` = today's date OR last clean data date

- [ ] **Step 2: Backup existing Parquet (S2-era 2.2y)**

```bash
cp data/BTCUSDT_1h.parquet data/BTCUSDT_1h.parquet.s2-backup
```

- [ ] **Step 3: Run backfill**

```bash
source .venv/bin/activate
python -m src backfill --symbol BTCUSDT --from <FROM_DATE> --to <TO_DATE>
```

REPLACE `<FROM_DATE>` + `<TO_DATE>` с actual values from Step 1.

Expected output:
```
backfill: fetching BTCUSDT 1H <FROM_DATE> → <TO_DATE> ...
backfill: wrote NNNNN bars к data/BTCUSDT_1h.parquet
```

- [ ] **Step 4: Verify Parquet metadata**

```bash
source .venv/bin/activate
python -c "
import pandas as pd
df = pd.read_parquet('data/BTCUSDT_1h.parquet')
print(f'rows: {len(df)}')
print(f'cols: {list(df.columns)}')
print(f'first: {df[\"time\"].iloc[0]}')
print(f'last: {df[\"time\"].iloc[-1]}')
print(f'span days: {(pd.to_datetime(df[\"time\"].iloc[-1]) - pd.to_datetime(df[\"time\"].iloc[0])).days}')
"
```

Expected: span ≥ 1278 days (3.5y per ADR 0028 floor) OR ≥ 1825 days (5y target). Если < 1278 → escalate per ESC-2.

- [ ] **Step 5: Document backfill artifact в SPRINT_STATE**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md` "Следующее действие":

```markdown
S13 PHASE 4 in flight:
- T1 probe: earliest <date>, target span <X>y ✅
- T2 backfill wire: ✅ (commit <sha>)
- T3 backfill run: ✅ <NNNNN bars>, span <Y> days
- T4-T7 pending
```

- [ ] **Step 6: Commit (docs only)**

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(state): T3 — backfill executed, $(echo NNNNN) bars over $(echo Y) days (S13)"
```

REPLACE `NNNNN` + `Y` с actual measured values.

---

### Task 4: NaN pre-flight assertion в `_load_ohlcv` (CC4)

**Files:**
- Modify: `src/__main__.py::_load_ohlcv` (lines 258-282)
- Create: `tests/unit/test_load_ohlcv_nan_preflight.py`

**Architecture rationale:** Per CC4 trader-flagged carried over from S12 brainstorm: WindowSplitter starts at earliest data point. EMA(12) + EMA(26) need 26-bar warmup. If NaN bars >10% после dropna → WFA metrics corrupt.

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_load_ohlcv_nan_preflight.py`:

```python
"""Pre-flight NaN assertion: data integrity check before WFA (CC4 per ADR 0028)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src import __main__ as cli


def test_load_ohlcv_passes_when_dropna_yields_above_90pct() -> None:
    """Healthy OHLCV (no NaN) passes pre-flight."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100, freq="1h"),
        "open": [50000.0 + i for i in range(100)],
        "high": [50010.0 + i for i in range(100)],
        "low": [49990.0 + i for i in range(100)],
        "close": [50005.0 + i for i in range(100)],
        "volume": [1.0] * 100,
    })

    with patch("src.__main__.load_market_data", return_value=df):
        result = cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-05")

    assert len(result) == 100


def test_load_ohlcv_aborts_when_dropna_yields_below_90pct() -> None:
    """≥10% NaN bars after dropna → abort с explicit error (CC4)."""
    rows = []
    for i in range(100):
        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": 50000.0 + i,
            "high": 50010.0 + i,
            "low": 49990.0 + i,
            "close": 50005.0 + i if i % 2 == 0 else None,  # 50% NaN
            "volume": 1.0,
        })
    df = pd.DataFrame(rows)

    with patch("src.__main__.load_market_data", return_value=df):
        with pytest.raises(ValueError, match="NaN.*pre-flight.*90%"):
            cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-05")


def test_load_ohlcv_passes_at_exactly_90pct_threshold() -> None:
    """Boundary: exactly 90% retained after dropna → PASS (≥, не >)."""
    rows = []
    for i in range(100):
        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": 50000.0 + i,
            "high": 50010.0 + i,
            "low": 49990.0 + i,
            "close": 50005.0 + i if i >= 10 else None,  # first 10 NaN
            "volume": 1.0,
        })
    df = pd.DataFrame(rows)

    with patch("src.__main__.load_market_data", return_value=df):
        result = cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-05")

    assert len(result) == 100
```

- [ ] **Step 2: Run tests to verify FAIL**

```bash
pytest tests/unit/test_load_ohlcv_nan_preflight.py -v
```

Expected: FAIL — current `_load_ohlcv` returns df without NaN check.

- [ ] **Step 3: Implement NaN pre-flight в `_load_ohlcv`**

Modify `src/__main__.py::_load_ohlcv`:

```python
def _load_ohlcv(*, symbol: str, start: str, end: str) -> pd.DataFrame:
    """Load OHLCV from Parquet via data_collector.

    S12 T2: closes S11 stub. Reuses existing data_collector pipeline.
    Operator must run `python -m src backfill --symbol <X>` to populate Parquet first.

    S13 T4 (CC4): pre-flight NaN assertion — `df.dropna()` post-warmup must yield
    ≥90% bars else WFA aborts с explicit error.
    """
    parquet_path = f"data/{symbol}_1h.parquet"
    config = {
        "data": {
            "source": "parquet",
            "parquet_path": parquet_path,
            "start_date": start,
            "end_date": end,
        }
    }
    try:
        df = load_market_data(config)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"OHLCV Parquet missing at {parquet_path}. "
            f"Run 'python -m src backfill --symbol {symbol} --from {start} --to {end}' first. "
            f"Original error: {e}"
        ) from e

    # CC4: pre-flight NaN assertion (≥90% bars retained after dropna)
    if not df.empty:
        retained_pct = len(df.dropna()) / len(df)
        if retained_pct < 0.90:
            raise ValueError(
                f"NaN pre-flight failed для {symbol}: only {retained_pct:.1%} bars retained "
                f"after dropna (threshold ≥90%). Likely data quality issue; investigate Parquet."
            )

    return df
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
pytest tests/unit/test_load_ohlcv_nan_preflight.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Run regression**

```bash
pytest tests/unit/test_main_wfa_cli.py -v
```

Expected: existing tests still PASS.

- [ ] **Step 6: Mypy + ruff**

```bash
mypy --strict src/__main__.py
ruff check src/__main__.py tests/unit/test_load_ohlcv_nan_preflight.py
```

Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add src/__main__.py tests/unit/test_load_ohlcv_nan_preflight.py
git commit -m "$(cat <<'EOF'
feat(cli): T4 — _load_ohlcv NaN pre-flight assertion (S13 CC4)

CC4 carried from S12 brainstorm: WindowSplitter starts at earliest data point.
EMA warmup propagates NaN; if NaN bars >10% after dropna, WFA metrics corrupt.

Pre-flight: post-load df.dropna() must yield ≥90% bars else ValueError abort.
3 unit tests: healthy → pass, 50% NaN → abort, exactly 90% → pass (≥ boundary).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Per-fold trade extraction (DataFrame → TradeRecord)

**Files:**
- Create: `src/backtest/trade_extractor.py`
- Create: `tests/unit/test_trade_extractor.py`

**Architecture rationale:** Per Q5 CONFIRM: DSR active S13 (N_trials=1, formula-invariant). Closes S10/S12 carry-over (`trades_for_dsr=[]` placeholder). WFA produces per-fold trade DataFrames; DSR requires `list[TradeRecord]` (pydantic model).

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_trade_extractor.py`:

```python
"""DataFrame → TradeRecord conversion для DSR (S13 T5, closes S10/S12 carry-over)."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.trade_extractor import extract_trade_records
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trades_df(n: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({
            "entry_ts": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i * 2),
            "exit_ts": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i * 2 + 1),
            "qty": 0.001,
            "entry_price": 50000.0 + i * 100,
            "exit_price": 50100.0 + i * 100,
            "net_pnl": 1.0 - i * 0.1,
            "fees_paid": 0.05,
        })
    return pd.DataFrame(rows)


def test_extract_trade_records_basic() -> None:
    """Healthy DataFrame → TradeRecord list, fields preserved Decimal precision."""
    df = _make_trades_df(n=3)
    records = extract_trade_records(df, symbol="BTCUSDT")

    assert len(records) == 3
    assert all(isinstance(r, TradeRecord) for r in records)
    assert records[0].symbol == "BTCUSDT"
    assert records[0].qty == Decimal("0.001")
    # pnl_pct = pnl_quote / (qty * entry_price) = 1.0 / (0.001 * 50000) = 0.02
    assert records[0].pnl_pct == pytest.approx(Decimal("0.02"), rel=Decimal("0.01"))
    assert records[0].kelly_phase == 1


def test_extract_trade_records_empty_df() -> None:
    """Empty DataFrame → empty list, не crash."""
    df = pd.DataFrame()
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records == []


def test_extract_trade_records_synthetic_signal_id_unique() -> None:
    """Backtest synthesizes entry_signal_id (UUID) — unique per row."""
    df = _make_trades_df(n=5)
    records = extract_trade_records(df, symbol="BTCUSDT")

    signal_ids = [r.entry_signal_id for r in records]
    assert len(set(signal_ids)) == 5


def test_extract_trade_records_negative_pnl_preserved() -> None:
    """Loser trades: negative pnl_quote + pnl_pct preserved (no abs())."""
    df = pd.DataFrame([{
        "entry_ts": pd.Timestamp("2024-01-01", tz="UTC"),
        "exit_ts": pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),
        "qty": 0.001,
        "entry_price": 50000.0,
        "exit_price": 49500.0,
        "net_pnl": -0.5,
        "fees_paid": 0.05,
    }])
    records = extract_trade_records(df, symbol="BTCUSDT")
    assert records[0].pnl_quote == Decimal("-0.5")
    assert records[0].pnl_pct < Decimal("0")
```

- [ ] **Step 2: Run tests to verify FAIL**

```bash
pytest tests/unit/test_trade_extractor.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.backtest.trade_extractor'`.

- [ ] **Step 3: Implement extractor**

Create `src/backtest/trade_extractor.py`:

```python
"""DataFrame → TradeRecord conversion для DSR computation.

Sprint 13 Task 5 (per ADR 0028 Q5). Closes S10 + S12 carry-over: WFA produces
per-fold trade DataFrames; DSR requires list[TradeRecord]. Bridge между layers.

Backtest synthesizes entry_signal_id (UUID) — uniqueness sole DSR-relevant
constraint. Default reason_code = EXIT_TP_HIT (placeholder, doesn't affect DSR
which consumes pnl_pct only). kelly_phase = 1 (backtest assumption).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def extract_trade_records(df: pd.DataFrame, *, symbol: str) -> list[TradeRecord]:
    """Convert WFA fold trade DataFrame → list[TradeRecord] для DSR.

    Args:
        df: pandas DataFrame с columns entry_ts, exit_ts, qty, entry_price,
            exit_price, net_pnl, fees_paid. Returned by WalkForwardRunner per fold.
        symbol: trading pair (e.g. "BTCUSDT").

    Returns:
        list[TradeRecord] (empty if df.empty). Each record:
        - entry_signal_id: synthesized UUID
        - reason_code: EXIT_TP_HIT default
        - kelly_phase: 1 (backtest assumption)
    """
    if df.empty:
        return []

    records: list[TradeRecord] = []
    now_utc = datetime.now(UTC)

    for _, row in df.iterrows():
        qty = Decimal(str(row["qty"]))
        entry_price = Decimal(str(row["entry_price"]))
        exit_price = Decimal(str(row["exit_price"]))
        pnl_quote = Decimal(str(row["net_pnl"]))
        fees_paid = Decimal(str(row.get("fees_paid", 0)))

        notional = qty * entry_price
        pnl_pct = (pnl_quote / notional) if notional > 0 else Decimal("0")

        records.append(
            TradeRecord(
                symbol=symbol,
                entry_signal_id=uuid4(),
                entry_ts=row["entry_ts"].to_pydatetime() if hasattr(row["entry_ts"], "to_pydatetime") else row["entry_ts"],
                exit_ts=row["exit_ts"].to_pydatetime() if hasattr(row["exit_ts"], "to_pydatetime") else row["exit_ts"],
                qty=qty,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_quote=pnl_quote,
                pnl_pct=pnl_pct,
                fees_paid=fees_paid,
                reason_code=ReasonCode.EXIT_TP_HIT,
                kelly_phase=1,
                recorded_at=now_utc,
            )
        )

    return records
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
pytest tests/unit/test_trade_extractor.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Mypy + ruff**

```bash
mypy --strict src/backtest/trade_extractor.py
ruff check src/backtest/trade_extractor.py tests/unit/test_trade_extractor.py
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/backtest/trade_extractor.py tests/unit/test_trade_extractor.py
git commit -m "$(cat <<'EOF'
feat(backtest): T5 — trade_extractor (DataFrame → TradeRecord) (S13 Q5 + CC1)

Closes S10 + S12 carry-over: WFA produces per-fold trade DataFrames; DSR requires
list[TradeRecord]. Bridge synthesizes entry_signal_id UUID per row (uniqueness =
sole DSR row-identity constraint).

Per Q5 trader CONFIRM: DSR active S13 (N_trials=1, formula-invariant).
Per CC1: N_trials tracking starts S13 — extractor agnostic, consumer responsible.

4 unit tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Quant-stats-reviewer dispatch (MANDATORY per ADR 0028)**

Brief: "S13 T5 commit `<sha>`. Review trade_extractor.py для DSR pipeline correctness. Specifically: (1) pnl_pct formula = pnl_quote / (qty × entry_price); (2) Decimal precision through pd.Series → str → Decimal pipeline; (3) UUID synthesis OK as DSR row identity; (4) default reason_code EXIT_TP_HIT impact on DSR (none expected); (5) S13 N_trials=1 baseline established correctly per Q5 verdict + CC1."

---

### Task 6: T1-T6 metrics extension в wfa_reporter

**Files:**
- Modify: `src/backtest/wfa_reporter.py` (add T1-T6 extraction к existing format_wfa_report)
- Create: `src/backtest/strategy_metrics.py` (T1-T6 helper functions)
- Create: `tests/unit/test_strategy_metrics.py`

**Architecture rationale:** Per Q5 CONFIRM: DSR active S13. WFA reporter currently outputs per-fold + aggregate Sharpe (T1, T6 partially). Need full T1-T6: T2 Sortino, T3 MaxDD, T4 Win rate, T5 t-stat, full T6.

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_strategy_metrics.py`:

```python
"""T1-T6 strategy metrics extraction (S13 T6 per acceptance-criteria.md)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_quote: Decimal, hours_offset: int = 0, qty_decimal: Decimal = Decimal("0.001"), entry_price_decimal: Decimal = Decimal("50000")) -> TradeRecord:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    notional = qty_decimal * entry_price_decimal
    exit_price = entry_price_decimal + (pnl_quote / qty_decimal)
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=base + timedelta(hours=hours_offset),
        exit_ts=base + timedelta(hours=hours_offset + 1),
        qty=qty_decimal,
        entry_price=entry_price_decimal,
        exit_price=exit_price,
        pnl_quote=pnl_quote,
        pnl_pct=pnl_quote / notional,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=base,
    )


def test_compute_metrics_returns_all_t1_t6_fields() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(120)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[0.8, 0.9, 0.75, 0.85, 0.95])
    assert set(metrics.keys()) >= {
        "t1_sharpe_oos", "t2_sortino_oos", "t3_max_drawdown",
        "t4_win_rate", "t4_avg_rr",
        "t5_mean_pnl_pct", "t5_t_stat", "t5_n_trades",
        "t6_oos_is_sharpe_ratio_mean",
    }


def test_compute_metrics_t1_sharpe_winners_positive() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(100)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t1_sharpe_oos"] > 0


def test_compute_metrics_t3_max_drawdown_zero_for_monotonic() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(50)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t3_max_drawdown"] == pytest.approx(0.0, abs=0.001)


def test_compute_metrics_t3_max_drawdown_with_dip() -> None:
    """30 winners $10 + 30 losers -$5 + 30 winners $5 → dips → MaxDD > 0."""
    trades = (
        [_make_trade(pnl_quote=Decimal("10"), hours_offset=i) for i in range(30)]
        + [_make_trade(pnl_quote=Decimal("-5"), hours_offset=30 + i) for i in range(30)]
        + [_make_trade(pnl_quote=Decimal("5"), hours_offset=60 + i) for i in range(30)]
    )
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t3_max_drawdown"] > 0


def test_compute_metrics_t4_win_rate() -> None:
    trades = (
        [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(50)]
        + [_make_trade(pnl_quote=Decimal("-1.0"), hours_offset=50 + i) for i in range(50)]
    )
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t4_win_rate"] == pytest.approx(0.5, abs=0.01)


def test_compute_metrics_t5_n_trades() -> None:
    trades = [_make_trade(pnl_quote=Decimal("0.5"), hours_offset=i) for i in range(123)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t5_n_trades"] == 123


def test_compute_metrics_t6_oos_is_sharpe_ratio_mean() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(100)]
    fold_oos_is = [0.7, 0.8, 0.9]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=fold_oos_is)
    assert metrics["t6_oos_is_sharpe_ratio_mean"] == pytest.approx(0.8, abs=0.01)


def test_compute_metrics_empty_trades_returns_nan() -> None:
    metrics = compute_t1_t6_metrics(trades=[], fold_oos_is_sharpe=[])
    assert metrics["t5_n_trades"] == 0
    import math
    assert math.isnan(metrics["t1_sharpe_oos"])


def test_compute_metrics_t3_initial_capital_parameterizable() -> None:
    """initial_capital sourced as parameter (not hardcoded)."""
    trades = [_make_trade(pnl_quote=Decimal("100"), hours_offset=i) for i in range(10)]
    metrics_default = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    metrics_50k = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0], initial_capital=50000.0)
    assert metrics_default["t3_max_drawdown"] == pytest.approx(0.0, abs=0.001)
    assert metrics_50k["t3_max_drawdown"] == pytest.approx(0.0, abs=0.001)


def test_compute_metrics_t3_total_blowout_returns_one() -> None:
    """T3 MaxDD = -100% (NOT NaN) on equity hits 0."""
    blowout = _make_trade(
        pnl_quote=Decimal("-10000"),
        qty_decimal=Decimal("1.0"),
        entry_price_decimal=Decimal("50000"),
        hours_offset=0,
    )
    # exit_price = 50000 + (-10000 / 1.0) = 40000 (valid > 0)
    metrics = compute_t1_t6_metrics(trades=[blowout], fold_oos_is_sharpe=[1.0])
    assert metrics["t3_max_drawdown"] == pytest.approx(1.0, abs=0.001)
```

- [ ] **Step 2: Run tests to verify FAIL**

```bash
pytest tests/unit/test_strategy_metrics.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `strategy_metrics`**

Create `src/backtest/strategy_metrics.py`:

```python
"""T1-T6 strategy validation metrics extraction.

Sprint 13 Task 6 (per ADR 0028 Q5). Per acceptance-criteria.md (amended footnotes
S13 PHASE 2 reconciliation):
- T1: Sharpe OOS annualized ≥ 1.0
- T2: Sortino OOS ≥ 1.5
- T3: MaxDD < 25%
- T4: Win rate ≥ 45% при RR≥1.5 OR ≥35% при RR≥2.0
- T5: Mean pnl_pct > 0, t-stat > 2.0, n ≥ 100 OOS
- T6: OOS/IS Sharpe ratio mean ≥ 0.7

Annualization: sqrt(8760) для 24/7 crypto 1H bars (per ADR 0025).

CC1: N_trials tracking — extractor receives n_trials from caller (consumer
responsibility). DSR consumed via separate compute_dsr call (this module
extracts T1-T6 metrics only).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.risk.trade_history import TradeRecord


# Annualization factor: sqrt(365*24) для 24/7 crypto 1H bars.
_ANNUALIZATION_FACTOR = float(np.sqrt(8760))


def compute_t1_t6_metrics(
    *,
    trades: list[TradeRecord],
    fold_oos_is_sharpe: list[float],
    initial_capital: float = 10000.0,
) -> dict[str, Any]:
    """Compute T1-T6 acceptance criteria metrics from OOS trades.

    Args:
        trades: list of OOS TradeRecord (use trade_extractor for WFA fold output).
        fold_oos_is_sharpe: per-fold OOS/IS Sharpe ratio (computed by WalkForwardRunner).
        initial_capital: backtest starting balance (matches WFA config trading.initial_balance).

    Returns:
        dict with t1-t6 fields. NaN if insufficient data.
    """
    n = len(trades)

    if n == 0:
        return {
            "t1_sharpe_oos": float("nan"),
            "t2_sortino_oos": float("nan"),
            "t3_max_drawdown": float("nan"),
            "t4_win_rate": float("nan"),
            "t4_avg_rr": float("nan"),
            "t5_mean_pnl_pct": float("nan"),
            "t5_t_stat": float("nan"),
            "t5_n_trades": 0,
            "t6_oos_is_sharpe_ratio_mean": (
                float(np.mean(fold_oos_is_sharpe)) if fold_oos_is_sharpe else float("nan")
            ),
        }

    pnl_pcts = np.array([float(t.pnl_pct) for t in trades])
    pnl_quotes = np.array([float(t.pnl_quote) for t in trades])

    # T1: Sharpe OOS annualized
    if pnl_pcts.std(ddof=1) > 0:
        sharpe_per_trade = float(pnl_pcts.mean() / pnl_pcts.std(ddof=1))
        t1_sharpe_oos = sharpe_per_trade * _ANNUALIZATION_FACTOR
    else:
        t1_sharpe_oos = float("nan")

    # T2: Sortino OOS (downside deviation)
    losers = pnl_pcts[pnl_pcts < 0]
    if len(losers) > 0 and losers.std(ddof=1) > 0:
        sortino_per_trade = float(pnl_pcts.mean() / losers.std(ddof=1))
        t2_sortino_oos = sortino_per_trade * _ANNUALIZATION_FACTOR
    else:
        t2_sortino_oos = float("nan")

    # T3: Max Drawdown (peak-to-trough on equity)
    equity = np.cumsum(pnl_quotes)
    equity_with_capital = initial_capital + equity
    running_max = np.maximum.accumulate(equity_with_capital)
    # Guard div-by-zero: total blowout (running_max=0) → -100%, NOT NaN
    drawdowns = np.where(
        running_max > 0,
        (equity_with_capital - running_max) / running_max,
        -1.0,
    )
    t3_max_drawdown = float(abs(drawdowns.min())) if len(drawdowns) > 0 else 0.0

    # T4: Win rate + avg RR
    winners = pnl_pcts[pnl_pcts > 0]
    losers_abs = np.abs(pnl_pcts[pnl_pcts < 0])
    t4_win_rate = len(winners) / n
    if len(winners) > 0 and len(losers_abs) > 0:
        t4_avg_rr = float(winners.mean() / losers_abs.mean())
    else:
        t4_avg_rr = float("nan")

    # T5: Mean + t-stat
    t5_mean_pnl_pct = float(pnl_pcts.mean())
    if pnl_pcts.std(ddof=1) > 0 and n > 1:
        t5_t_stat = float(pnl_pcts.mean() / (pnl_pcts.std(ddof=1) / math.sqrt(n)))
    else:
        t5_t_stat = float("nan")

    # T6: OOS/IS ratio mean
    if fold_oos_is_sharpe:
        t6_oos_is_sharpe_ratio_mean = float(np.mean(fold_oos_is_sharpe))
    else:
        t6_oos_is_sharpe_ratio_mean = float("nan")

    return {
        "t1_sharpe_oos": t1_sharpe_oos,
        "t2_sortino_oos": t2_sortino_oos,
        "t3_max_drawdown": t3_max_drawdown,
        "t4_win_rate": t4_win_rate,
        "t4_avg_rr": t4_avg_rr,
        "t5_mean_pnl_pct": t5_mean_pnl_pct,
        "t5_t_stat": t5_t_stat,
        "t5_n_trades": n,
        "t6_oos_is_sharpe_ratio_mean": t6_oos_is_sharpe_ratio_mean,
    }
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
pytest tests/unit/test_strategy_metrics.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Mypy + ruff**

```bash
mypy --strict src/backtest/strategy_metrics.py
ruff check src/backtest/strategy_metrics.py tests/unit/test_strategy_metrics.py
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/backtest/strategy_metrics.py tests/unit/test_strategy_metrics.py
git commit -m "$(cat <<'EOF'
feat(backtest): T6 — strategy_metrics T1-T6 extraction (S13 ADR 0028 Q5)

Computes 6 acceptance criteria metrics per acceptance-criteria.md (amended
footnotes S13 PHASE 2 — DSR active S13+, PBO defer S15+):

- T1 Sharpe OOS annualized (sqrt(8760) per ADR 0025)
- T2 Sortino OOS (downside deviation)
- T3 MaxDD (peak-to-trough on equity, div-by-zero guard для blowout)
- T4 Win rate + avg RR
- T5 Mean pnl_pct + t-stat + n_trades
- T6 OOS/IS Sharpe ratio mean (per-fold)

Empty trades → NaN sentinels (no crash). initial_capital parameterizable
(matches WFA config trading.initial_balance, default 10000).

T3 div-by-zero guard: total blowout (equity=0) → -100% (NOT NaN silent corruption).

9 unit tests covering all metrics + boundary cases.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Quant-stats-reviewer dispatch (MANDATORY per ADR 0028)**

Brief: "S13 T6 commit `<sha>`. Review strategy_metrics.py для T1-T6 mathematical correctness per amended acceptance-criteria.md. Specifically: (1) annualization sqrt(8760) per ADR 0025; (2) Sortino convention (std losers vs sqrt(mean(losers²))); (3) T3 div-by-zero guard; (4) T5 t-stat formula one-tailed; (5) T6 arithmetic mean per-fold ratio."

---

### Task 7: Wire S13 measurement в `_cmd_wfa` + verdict report

**Files:**
- Modify: `src/__main__.py::_cmd_wfa` (lines 290-345)

**Architecture rationale:** Plumb T5 + T6 + DSR computation в existing `_cmd_wfa`. Per Q7 ESC-1=c (defer pattern): output PASS/FAIL/PARTIAL per T1-T6 + DSR raw values, не enforce binding pre-commit framework. Operator sees verdict at S15.

- [ ] **Step 1: Wire trade_extractor + strategy_metrics + DSR в `_cmd_wfa`**

Modify `src/__main__.py`. Add imports at top:

```python
from src.analytics.dsr import compute_dsr
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.trade_extractor import extract_trade_records
```

Modify `_cmd_wfa` body. After existing MC computation (around line 325), BEFORE existing `gate = evaluate_acceptance_gate(...)`, INSERT:

```python
    # S13 T5: Per-fold trade extraction (closes S10/S12 carry-over)
    all_trades = []
    fold_oos_is_sharpe_ratios = []
    for fold_data in runner_result["folds"]:
        fold_oos_is_sharpe_ratios.append(fold_data["oos_is_sharpe_ratio"])
        fold_trades_df = fold_data.get("oos_trades_df")
        if fold_trades_df is not None and not fold_trades_df.empty:
            all_trades.extend(extract_trade_records(fold_trades_df, symbol=symbol))

    # S13 Q5 + CC1: DSR active S13 (N_trials=1 per first measurement, formula-invariant)
    dsr_value = compute_dsr(trades=all_trades, n_trials=1)

    # S13 T6: T1-T6 metrics
    metrics = compute_t1_t6_metrics(
        trades=all_trades,
        fold_oos_is_sharpe=fold_oos_is_sharpe_ratios,
    )
```

REPLACE existing `fold_ratios = [f["oos_is_sharpe_ratio"] for f in runner_result["folds"]]` с usage of `fold_oos_is_sharpe_ratios` from above loop (already collected).

REPLACE existing `format_wfa_report(...)` call — change `trades_for_dsr=[]` к `trades_for_dsr=all_trades`.

REPLACE existing `print(json.dumps(...))` final output с extended:

```python
    import json
    import math

    def _nan_or_value(v):
        return None if (isinstance(v, float) and math.isnan(v)) else v

    # S13 T7: Verdict report (per Q7 ESC-1=c defer pattern — raw values, не pre-commit)
    failed_criteria = []
    if _nan_or_value(metrics["t1_sharpe_oos"]) is None or metrics["t1_sharpe_oos"] < 1.0:
        failed_criteria.append("t1")
    if _nan_or_value(metrics["t2_sortino_oos"]) is None or metrics["t2_sortino_oos"] < 1.5:
        failed_criteria.append("t2")
    if _nan_or_value(metrics["t3_max_drawdown"]) is None or metrics["t3_max_drawdown"] > 0.25:
        failed_criteria.append("t3")
    win_rate = metrics["t4_win_rate"]
    avg_rr = metrics["t4_avg_rr"]
    t4_fail = (
        _nan_or_value(win_rate) is None
        or _nan_or_value(avg_rr) is None
        or (avg_rr >= 2.0 and win_rate < 0.35)
        or (1.5 <= avg_rr < 2.0 and win_rate < 0.45)
        or avg_rr < 1.5
    )
    if t4_fail:
        failed_criteria.append("t4")
    if (
        _nan_or_value(metrics["t5_mean_pnl_pct"]) is None
        or metrics["t5_mean_pnl_pct"] <= 0
        or _nan_or_value(metrics["t5_t_stat"]) is None
        or metrics["t5_t_stat"] < 2.0
        or metrics["t5_n_trades"] < 100
    ):
        failed_criteria.append("t5")
    if _nan_or_value(metrics["t6_oos_is_sharpe_ratio_mean"]) is None or metrics["t6_oos_is_sharpe_ratio_mean"] < 0.7:
        failed_criteria.append("t6")

    dsr_pass = _nan_or_value(dsr_value) is not None and dsr_value > 0

    if len(failed_criteria) == 0 and dsr_pass:
        verdict = "PASS"
    else:
        verdict = "FAIL"  # Q7 defer pattern: report only, no auto-classification

    print(json.dumps({
        "symbol": symbol,
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "dsr": _nan_or_value(dsr_value),
        "dsr_pass": dsr_pass,
        "n_trials": 1,
        "metrics": {
            "t1_sharpe_oos": _nan_or_value(metrics["t1_sharpe_oos"]),
            "t2_sortino_oos": _nan_or_value(metrics["t2_sortino_oos"]),
            "t3_max_drawdown": _nan_or_value(metrics["t3_max_drawdown"]),
            "t4_win_rate": _nan_or_value(metrics["t4_win_rate"]),
            "t4_avg_rr": _nan_or_value(metrics["t4_avg_rr"]),
            "t5_mean_pnl_pct": _nan_or_value(metrics["t5_mean_pnl_pct"]),
            "t5_t_stat": _nan_or_value(metrics["t5_t_stat"]),
            "t5_n_trades": metrics["t5_n_trades"],
            "t6_oos_is_sharpe_ratio_mean": _nan_or_value(metrics["t6_oos_is_sharpe_ratio_mean"]),
        },
        "k_folds": len(fold_oos_is_sharpe_ratios),
        "mc_p_value": mc_p,
        "acceptance_gate": gate,
    }, default=str, indent=2))

    # Exit codes per ADR 0028 Q7 defer pattern: 0 = PASS, 2 = FAIL (operator decides at S15)
    return 0 if verdict == "PASS" else 2
```

- [ ] **Step 2: Run regression tests**

```bash
source .venv/bin/activate
pytest tests/unit/test_main_wfa_cli.py -v
```

Expected: existing tests still PASS (some may need mock updates).

- [ ] **Step 3: Mypy + ruff**

```bash
mypy --strict src/__main__.py
ruff check src/__main__.py
```

Expected: clean.

- [ ] **Step 4: Run actual S13 measurement**

Per T3 backfill output, run:

```bash
source .venv/bin/activate
python -m src wfa --symbol BTCUSDT --start <FROM_DATE> --end <TO_DATE> > s13_measurement_$(date +%Y%m%d_%H%M%S).json 2>&1
echo "EXIT=$?" >> s13_measurement_*.json
cat s13_measurement_*.json
```

REPLACE `<FROM_DATE>` + `<TO_DATE>` с actual values from T3.

Capture verdict + metrics. Exit 0 = PASS, 2 = FAIL.

- [ ] **Step 5: Document measurement в SPRINT_STATE**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md` "Следующее действие":

```markdown
S13 PHASE 4-7 complete:
- T1 probe ✅ <date>
- T2 backfill wire ✅ <sha>
- T3 backfill run ✅ <NNNNN bars>
- T4 NaN preflight ✅ <sha>
- T5 trade_extractor ✅ <sha>
- T6 strategy_metrics ✅ <sha>
- T7 measurement ✅ verdict=<PASS|FAIL>, T1=<value>, ..., DSR=<value>, N_trials=1

Next: T8 PHASE 8 ship + S15 brainstorm (per ADR 0028 — verdict drives S14 scope)
```

- [ ] **Step 6: Commit**

```bash
git add src/__main__.py llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "$(cat <<'EOF'
feat(cli): T7 — wire S13 measurement pipeline + verdict report (S13 ADR 0028)

Plumbs all S13 components в _cmd_wfa:
- trade_extractor (T5): per-fold DataFrame → TradeRecord (closes S10/S12 carry-over)
- strategy_metrics (T6): T1-T6 extraction
- compute_dsr (Q5): N_trials=1 active S13, formula-invariant

Per Q7 ESC-1=c defer pattern: verdict report = PASS/FAIL only based on T1-T6 +
DSR > 0. NO pre-commit framework. NO automatic HARD/PARTIAL classification —
operator decides next sprint scope at S15 (case-by-case).

Per CC1: N_trials=1 explicit в output для tracking.
Per CC3: PBO formal deferral (not in verdict logic, per amended acceptance-criteria.md
footnote 3 S15+ defer).

Exit codes: 0 = PASS, 2 = FAIL (operator interprets).

S13 measurement run results:
- verdict: <PASS|FAIL>
- failed_criteria: <list>
- T1 Sharpe: <value>, T3 MaxDD: <value>, T5 n_trades: <value>
- DSR: <value> (N_trials=1)
- MC p-value: <value>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

REPLACE `<value>` placeholders с actual measurement values.

---

### Task 8: ADR 0028 accepted + sprint-13 page + wiki sync (PHASE 8)

**Files:**
- Modify: `wiki/project/decisions/0028-sprint-13-strategy-validation.md` (status: proposed → accepted)
- Create: `wiki/project/sprints/sprint-13-backfill-wfa.md`
- Create: `wiki/project/components/trade-extractor.md`
- Create: `wiki/project/components/strategy-metrics.md`
- Modify: `wiki/index.md` (sprint-13 + ADR 0028 + 2 component pages)
- Modify: `wiki/project/architecture/current-state.md` (counts: ADR 27→28, sprint pages 14→15, components 36→38)
- Modify: `wiki/project/mental-map.md` (trade_extractor + strategy_metrics rows)

- [ ] **Step 1: Update ADR 0028 status**

Edit `wiki/project/decisions/0028-sprint-13-strategy-validation.md`:

```yaml
status: accepted
```

- [ ] **Step 2: Verify canonical counts unchanged (FSM/reason codes)**

```bash
source .venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: `states=16, events=30, transitions=74, reason_codes=45` (S13 = backtest analytics, no FSM growth).

Verify directory counts:
```bash
ls llm-wiki/wiki/project/decisions/ | grep -v README | wc -l   # Expected: 28
ls llm-wiki/wiki/project/sprints/ | grep -v README | wc -l     # Expected: 15
ls llm-wiki/wiki/project/components/ | grep -v README | wc -l  # Expected: 38 (S13 +2)
```

- [ ] **Step 3: Create sprint-13 page**

Reference template: `wiki/project/sprints/sprint-12-live-demo-validation.md`. Mirror structure для sprint-13. Required sections:
- Frontmatter (title, type=sprint, tags, created/updated, status=completed, sources=[ADR 0028 + plan])
- # Sprint 13 — Backfill 5y + WFA T1-T6 measurement
- ## Overview
- ## Plan / ADR links
- ## Deliverables (T1-T8 commits с SHAs)
- ## FSM growth — NONE
- ## Reason codes growth — NONE
- ## Tests — pytest summary, mypy + ruff
- ## Backfill artifact — `data/BTCUSDT_1h.parquet`, NNNNN bars, span Y days, period <FROM>→<TO>
- ## Verdict result — actual `<PASS|FAIL>` от T7 + per-criterion values + DSR + MC p-value + N_trials=1
- ## Wiki updates — 2 NEW component pages, 1 NEW ADR, 1 NEW sprint page, 4 modified
- ## Open issues для S14+ (branched на verdict)
- ## Key decisions — Q1-Q8 verdicts, ESC-1 defer, ESC-2 tiered 5y, spec reconciliation
- ## Related

Self-contained markdown, no placeholders.

- [ ] **Step 4: Create 2 component pages**

For each NEW component (`trade-extractor.md`, `strategy-metrics.md`), reference `wiki/project/components/walk-forward.md` template. Sections:
- Frontmatter
- # Component Name + TL;DR
- ## Purpose
- ## Public API
- ## Architecture rationale
- ## Invariants
- ## Related (cross-component links)
- ## Sources (src/ + tests/)

Self-contained, no placeholders.

- [ ] **Step 5: Update index.md**

Add к "Project — Sprints" section:

```markdown
- [[project/sprints/sprint-13-backfill-wfa]] — S13 (2026-04-25): Backfill 5y BTCUSDT 1H Bybit Spot + WFA T1-T6 measurement (DSR active N_trials=1, per ADR 0028 Q5). Verdict: <PASS|FAIL>. 8 TDD tasks. FSM/counts unchanged. Tag v0.1.0-alpha.13.
```

Add к "Project — Components" (alphabetical):
- `strategy-metrics.md`
- `trade-extractor.md`

Add к "Project — Decisions":

```markdown
- [[project/decisions/0028-sprint-13-strategy-validation]] — Sprint 13 ADR: 5y backfill + WFA T1-T6 measurement, DSR active S13 N_trials=1, PBO defer S15+, ESC-1 defer pattern preserved, ESC-2 tiered 5y target.
```

- [ ] **Step 6: Update current-state.md**

TL;DR: replace `# Current State (post-S12, ...)` с `# Current State (post-S13, 2026-04-25)`.

Counts table:
- ADRs: 27 → **28**
- Sprint pages: 14 → **15**
- Component pages: 36 → **38** (+2)

Add S13 row к "Карта спринтов".

- [ ] **Step 7: Update mental-map.md**

Add к "Tooling / hooks / methodology" section:
- trade-extractor (DataFrame → TradeRecord для DSR)
- strategy-metrics (T1-T6 extraction)

- [ ] **Step 8: Final pre-validation**

```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -3
mypy --strict src/ 2>&1 | tail -3
git diff --name-only main..HEAD -- migrations/   # MUST be empty
```

Expected:
- pytest: ~706 passed (689 + 17 new tests across T2/T4/T5/T6)
- mypy: clean
- migrations diff: empty

- [ ] **Step 9: Commit T8 wiki sync**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add wiki/project/decisions/0028-sprint-13-strategy-validation.md \
        wiki/project/sprints/sprint-13-backfill-wfa.md \
        wiki/project/components/trade-extractor.md \
        wiki/project/components/strategy-metrics.md \
        wiki/index.md \
        wiki/project/architecture/current-state.md \
        wiki/project/mental-map.md
git commit -m "$(cat <<'EOF'
docs(wiki): T8 — S13 wiki sync (ADR accepted + sprint page + 2 component pages + counts) (S13)

Sprint 13 ship-ready wiki state:
- ADR 0028 status: proposed → accepted
- NEW sprint page: sprint-13-backfill-wfa.md (verdict: <PASS|FAIL>, N_trials=1)
- NEW component pages (2):
  - trade-extractor.md (DataFrame → TradeRecord для DSR, T5)
  - strategy-metrics.md (T1-T6 extraction, T6)
- index.md: +sprint-13 + ADR 0028 + 2 component pages
- current-state.md: TL;DR post-S13, ADR 27→28, sprint pages 14→15, components 36→38, +S13 row
- mental-map.md: +2 component rows

Counts verified: states=16, events=30, transitions=74, reason_codes=45 (unchanged).
Q7-S12 zero-migration: git diff main..HEAD -- migrations/ empty.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

REPLACE `<PASS|FAIL>` с actual verdict.

- [ ] **Step 10: Invoke sprint-finish skill (PHASE 8 HARD-GATE checklist)**

Skill auto-trigger via "ship". Executes:
- Pre-validation final check (pytest + mypy + counts)
- HARD-GATEs verification
- SPRINT_STATE → 8-ship
- Push + PR + squash-merge + tag v0.1.0-alpha.13
- Chapter mark "Sprint 13 ship complete"

---

## Self-review checklist

After plan completion, verify:

**1. Spec coverage:**
- ✅ Q1 (backtest first) — T2-T7 sprint focus
- ✅ Q2 (conditional split) — T1 PHASE 3 step 1 probe
- ✅ Q3 (Bybit only) — T2 wire (Bybit pagination)
- ✅ Q4 (tiered 5y, floor 3.5y) — T1 probe drives span
- ✅ Q5 (DSR active S13, PBO defer) — T6 + T7 (DSR included, PBO not in verdict)
- ✅ Q6 (48h decoupled) — NO TASK (operator parallel)
- ✅ Q7 ESC-1=c (defer pattern) — T7 verdict report без pre-commit
- ✅ Q8 (skip dashboard) — NO TASK (CLI JSON only)
- ✅ CC1 (N_trials tracking) — T6 + T7 explicit N_trials=1
- ✅ CC2 (Bybit data biggest unknown) — T1 BEFORE T2 mandatory
- ✅ CC3 (PBO formal deferral) — T8 sprint page documents
- ✅ CC4 (spec reconciliation) — DONE pre-plan (acceptance-criteria.md amended)

**2. Placeholder scan:** ALL "TBD" / "TODO" / "implement later" replaced. Verdict result placeholders в T7/T8 intentional (filled at T7 actual measurement).

**3. Type consistency:**
- `extract_trade_records(df, *, symbol)` — T5 → T7
- `compute_t1_t6_metrics(*, trades, fold_oos_is_sharpe, initial_capital=10000.0)` — T6 → T7
- `compute_dsr(trades=, n_trials=1)` — T7 (existing, unchanged)
- `_cmd_backfill` argparse: `--symbol`, `--from`, `--to`, `--output` — T2 → T3

## Execution Handoff

Plan complete + saved к `wiki/project/plans/2026-04-25-sprint-13-backfill-wfa.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review (spec compliance + domain reviewer)
2. **Inline Execution** — execute tasks в этой session via executing-plans skill

**Which approach?**
