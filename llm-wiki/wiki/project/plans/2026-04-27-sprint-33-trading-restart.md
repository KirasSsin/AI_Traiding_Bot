---
title: Sprint 33 — Trading Restart (test debt + MC fix + E DSR cross-trial + F multi-symbol BACKTEST measurement)
type: plan
tags: [plan, sprint-33, trading-restart, multi-symbol, mean-reversion, dsr-cross-trial, mc-p-value, pre-registration, ru]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/pre-s33-backlog.md
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/sprints/sprint-22-4h-test.md
  - project/sprints/sprint-27-formula-bug-fixes.md
  - project/architecture/acceptance-criteria.md
---

# Sprint 33 — Trading Restart Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans (controller-driven trading sprint с TDD per code task). Steps use checkbox `- [ ]` syntax.

**Goal:** Trading sprint после 8-sprint S32 series. Multi-symbol BTC+ETH+SOL 4H mean-reversion BACKTEST measurement (S17-relaxed params, WFA train=1000/test=250, ~3.3y OOS). Validate F mathematical hypothesis closes T5 unreachability.

**Architecture:** Backtest-only sprint (zero new live code). Live deployment infrastructure deferred к S34. Pre-registration discipline strict — params + WFA window + acceptance gates ALL locked в S33 ADR ДО measurement run (anti-data-snooping per Bailey & López de Prado 2014).

**Tech Stack:** Python 3.12 + pydantic v2 + pandas + numpy + scipy + Hypothesis (property tests) + pytest + mypy --strict.

---

## Context — 3-agent consilium synthesis (PHASE 2)

Per `pre-s33-backlog.md` ROUND 1 + ROUND 2 verdicts:
- 6 escalation items APPROVED unanimously
- 13 REQUIRED + 2 OPTIONAL NEW items added
- All 3 agents CONFIRM_REVISE final position
- Trading-logic UPGRADED ESC-1/3 vote от REVISE→APPROVE per backtest/live split

**S33 scope synthesis:**
1. Fix Q6 test debt + investigate bars_per_year root cause
2. Fix CC-D MC p-value formula (BOTH `sign_flip_p_value:56` + `block_bootstrap_p_value:96`) + property tests
3. Implement E (DSR cross-trial extension): TrialEntry `symbol: str` field + sigma_SR pooling protocol
4. F backtest measurement: BTC+ETH+SOL 4H mean-reversion S17-relaxed params (RSI 35/65 + BB 1.5σ AND-gated), WFA train=1000/test=250
5. SKIP B (regime filter), C (SL calibration), live multi-symbol infra → S34+

**Critical pre-registration:** Per CC6 (b) consensus — WFA window train=1000/test=250 (4H specific). Per CC-C — S17-relaxed params named constant.

**Pre-committed failure branch:** Если F fails T5 (n<100 aggregate after correlation deflation) OR MC p>0.10 OR DSR<0.95 → S34 honest close v0.6 (mirror S14/S16/S18/S21/S23 BINDING precedent) OR operator-driven spec amendment с explicit statistical-framework override statement.

## Test debt baseline

Pre-S33 баseline (S32d preserved):
- 773 pytest passed (3 pre-existing failures `test_replay_long_only` x2 + `test_replay_next_open` x1)
- 1 mypy error (`src/__main__.py:636 bars_per_year_map redef`)
- ~169 ruff issues (legacy code excluded в pyproject.toml)
- canonical counts: 16/30/74/45 ✓

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `tests/test_replay_long_only.py` | MODIFY | Fix 2 failing tests (root cause: fixture broken by S27 calc change OR test assertions outdated) |
| `tests/test_replay_next_open.py` | MODIFY | Fix 1 failing test |
| `src/__main__.py:636` | MODIFY | Fix mypy `bars_per_year_map` redef (rename `_wfa` suffix OR `# type: ignore[no-redef]`) |
| `tests/test_bars_per_year_integration.py` | NEW | 4H annualization end-to-end test (`bars_per_year("4H") == 2190`) — Item #11 |
| `src/backtest/mc_permutation.py:56` + `:96` | MODIFY | Fix `count/N` → `(count+1)/(N+1)` per ADR 0015 — Item #1 |
| `tests/property/test_mc_invariants.py` | NEW | Hypothesis-based: `mc_p_value > 0` always, `1/(N+1) ≤ p ≤ 1`, monotonic в count_extreme — Item #2 |
| `src/analytics/cross_trial_log.py` | MODIFY | Add `symbol: str` field к `TrialEntry` TypedDict + backfill default `symbol="BTCUSDT"` for legacy entries — Item #9 |
| `src/analytics/dsr.py` | MODIFY | Adjust `sigma_sr()` для multi-symbol pooling (option (a): pool all (sprint, symbol) pairs → n_trials=3 per multi-symbol sprint) — Item #6+#7 |
| `tests/test_cross_trial_log_migration.py` | NEW | Schema migration guard: load legacy entry (no `symbol`), verify backfill, no KeyError |
| `tests/test_dsr_multi_symbol.py` | NEW | Multi-symbol DSR pooling test (n_trials=3 для S33 multi-symbol) |
| `src/backtest/wfa.py` (или wherever WFA orchestrator) | MODIFY | Pre-run validation `len(ohlcv_df) >= (train + test) * n_folds` per symbol — Item #10 |
| `src/signalgen/strategy.py` | MODIFY | Add `MEAN_REVERSION_S17_RELAXED_PARAMS` constant (RSI 35/65, BB 1.5σ, AND-gated) — Item #5 |
| `data/cross_trial_sharpes.json` | ARCHIVE + RESET | Mirror S16/S18/S21/S23 pattern: archive к `_v0.5-final.json` + reset к `[]` для v0.6 (S33 first multi-symbol — clean baseline) |
| `data/formulas_audit_v1.json` | RE-RUN | Optional: re-run audit_formulas.py post CC-D fix для confirmation reason codes diversification preserved |
| `.github/workflows/ci.yml` | MODIFY | Update pytest baseline 773 → new count (post-S33 test additions) — Item #13 |
| `llm-wiki/wiki/project/decisions/0050-sprint-33-trading-restart.md` | NEW | ADR — full pre-registration checklist 9-item locked list + ESC-3 4 binding conditions documented + pre-committed failure branch + S17-relaxed named constant + reviewer dispatch plan |
| `llm-wiki/wiki/project/sprints/sprint-33-trading-restart.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-33 + ADR 0050 + new component pages если applicable |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | counts: 36→37 sprints / 49→50 ADRs + S33 sprint history row |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | S33 in_progress → done после ship |

---

## Tasks

### Task T1 — Fix Q6 test debt + bars_per_year root cause investigation

**Files:**
- Modify: `tests/test_replay_long_only.py` (2 failing tests)
- Modify: `tests/test_replay_next_open.py` (1 failing test)
- Modify: `src/__main__.py:636` (mypy redef)
- Create: `tests/test_bars_per_year_integration.py` (4H annualization end-to-end)

**Steps:**

- [ ] **Step 1: Read failing test tracebacks**
```bash
source .venv/bin/activate
pytest tests/test_replay_long_only.py tests/test_replay_next_open.py -v 2>&1 | head -80
```
Expected: 3 failures с specific assertion messages. Identify root cause:
- Fixture broken by S27 calc change (`bars_per_year` parameterization, RSI/ATR warm-up gating)
- OR test assertions outdated post-S27

- [ ] **Step 2: Investigate calculate_indicators output на synthetic 12-bar fixtures**

Per trading-logic-reviewer hypothesis: `ewm(span=2, adjust=False)` + `shift(1)` → may produce zero `signal=1` events для 12-bar fixture. Verify:
```python
from src.backtest.indicators import calculate_indicators
import pandas as pd
# Reproduce fixture from test
df = pd.DataFrame({...})  # 12-bar synthetic
config = {"strategy": {"indicators": {"ema": {"fast_period": 2, "slow_period": 3}, "rsi": {"period": 2}}}}
result = calculate_indicators(df, config)
print(result["signal"].sum())  # Expected: > 0 if fixture valid
```

- [ ] **Step 3: Fix tests OR adjust fixtures**

Если signal count == 0 → adjust fixture (longer series 30+ bars OR adjust EMA periods).
Если signal count > 0 → assertions outdated, update к match S27-corrected output.

- [ ] **Step 4: Fix mypy `bars_per_year_map` redef**

```python
# src/__main__.py:636 — rename к bars_per_year_map_wfa
# OR add `# type: ignore[no-redef]`
```

- [ ] **Step 5: Create bars_per_year integration test (Item #11)**

```python
# tests/test_bars_per_year_integration.py
"""4H annualization end-to-end verification — S33 T1.

Per quant-stats-reviewer Q6 concern: S27 T1 fix bars_per_year parameterization
must propagate through replay engine sharpe_ratio computation,
not just unit test of function isolation.
"""
import pytest
from src.backtest.replay_engine import run_replay
from src.backtest.strategy_metrics import compute_strategy_metrics


def test_bars_per_year_4h_propagates_through_replay():
    """4H interval → bars_per_year=2190 → sharpe annualized correctly."""
    # Setup minimal 4H replay run
    config = {
        "interval": "4H",
        "bars_per_year": 2190,  # 8760/4
        ...  # fixture params
    }
    result = run_replay(df_4h_fixture, config)
    
    # Assert: sharpe uses correct annualization
    raw_sharpe = result["pnl_pct"].mean() / result["pnl_pct"].std(ddof=1)
    expected_annualized = raw_sharpe * np.sqrt(2190)  # 4H bars/year
    assert abs(result["metrics"]["sharpe_ratio"] - expected_annualized) < 1e-6


def test_bars_per_year_1h_baseline_preserved():
    """1H interval → bars_per_year=8760 (S27 default before fix)."""
    config = {"interval": "1H", "bars_per_year": 8760, ...}
    result = run_replay(df_1h_fixture, config)
    raw_sharpe = result["pnl_pct"].mean() / result["pnl_pct"].std(ddof=1)
    expected = raw_sharpe * np.sqrt(8760)
    assert abs(result["metrics"]["sharpe_ratio"] - expected) < 1e-6
```

- [ ] **Step 6: Run full pytest — verify Q6 baseline cleared**

```bash
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
mypy --strict src/ 2>&1 | tail -3
```

Expected: 0 failures (was 3) + 0 mypy errors (was 1) + new bars_per_year integration tests passing.

- [ ] **Step 7: Commit**

```bash
git add tests/test_replay_long_only.py tests/test_replay_next_open.py \
        tests/test_bars_per_year_integration.py src/__main__.py
git commit -m "fix(test): T1 — fix 3 pre-existing pytest failures + 1 mypy redef + bars_per_year 4H end-to-end integration test (Item #11)"
```

---

### Task T2 — CC-D MC p-value fix (BOTH formulas) + property tests

**Files:**
- Modify: `src/backtest/mc_permutation.py:56` (`sign_flip_p_value`)
- Modify: `src/backtest/mc_permutation.py:96` (`block_bootstrap_p_value`)
- Create: `tests/property/test_mc_invariants.py` (Hypothesis-based)

**Steps:**

- [ ] **Step 1: Read current implementation**

```bash
sed -n '50,100p' src/backtest/mc_permutation.py
```

Identify both lines с buggy `count_extreme / n_iterations`.

- [ ] **Step 2: Write failing property test FIRST (TDD RED)**

```python
# tests/property/test_mc_invariants.py
"""MC p-value invariants property test — S33 T2 (CC-D fix regression guard).

Per quant-stats-reviewer Round 2 Item #2:
- p > 0 always (impossible с finite permutations к get exact 0)
- 1/(N+1) ≤ p ≤ 1
- Monotonic в count_extreme

Catches CC-D regression: pre-fix `count/N` returned 0 when count==0.
"""
import pytest
from hypothesis import given, strategies as st
from src.backtest.mc_permutation import sign_flip_p_value, block_bootstrap_p_value


@given(
    count_extreme=st.integers(min_value=0, max_value=2000),
    n_iterations=st.integers(min_value=10, max_value=2000),
)
def test_sign_flip_p_value_floor(count_extreme, n_iterations):
    """p-value never zero, never exceeds 1.0."""
    if count_extreme > n_iterations:
        return  # invalid input, skip
    
    # Mock returns/permutations s.t. exactly count_extreme exceed observed
    # ... fixture setup ...
    p = sign_flip_p_value(...)
    
    # Invariants
    assert p > 0.0, f"p-value floor violated: count={count_extreme}, N={n_iterations}, got p={p}"
    assert p <= 1.0
    assert abs(p - (count_extreme + 1) / (n_iterations + 1)) < 1e-9


def test_sign_flip_p_value_count_zero_returns_floor():
    """Edge case: count_extreme=0 returns 1/(N+1), NOT 0."""
    p = sign_flip_p_value(...)  # construct fixture с no extreme permutations
    expected = 1 / (n_iterations + 1)
    assert abs(p - expected) < 1e-9


def test_block_bootstrap_p_value_floor():
    """Same invariants для block_bootstrap_p_value."""
    # ... mirror sign_flip test ...
```

- [ ] **Step 3: Run test — verify RED**
```bash
pytest tests/property/test_mc_invariants.py -v
# Expected: FAIL — p=0 returned when count_extreme=0
```

- [ ] **Step 4: Apply fix к BOTH formulas (TDD GREEN)**

```python
# src/backtest/mc_permutation.py:56 (sign_flip_p_value)
# BEFORE:
return float(count_extreme / n_iterations)
# AFTER:
return float((count_extreme + 1) / (n_iterations + 1))

# src/backtest/mc_permutation.py:96 (block_bootstrap_p_value)
# Same fix
```

Add reference comment:
```python
# Per ADR 0015: (count + 1) / (N + 1) per Phipson & Smyth 2010
# Avoids p=0 (logically impossible с finite permutations)
```

- [ ] **Step 5: Run test — verify GREEN**
```bash
pytest tests/property/test_mc_invariants.py -v
# Expected: PASS
```

- [ ] **Step 6: Run full pytest baseline**
```bash
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
```
Expected: All passing. Note: existing MC-using tests may shift ε≤0.001 в reported p-values (negligible at N=2000).

- [ ] **Step 7: Commit**
```bash
git add src/backtest/mc_permutation.py tests/property/test_mc_invariants.py
git commit -m "fix(stats): T2 — CC-D MC p-value formula (count+1)/(N+1) per ADR 0015 in BOTH sign_flip_p_value:56 + block_bootstrap_p_value:96 + Hypothesis property tests (Items #1+#2)"
```

---

### Task T3 — E (DSR cross-trial extension): TrialEntry schema + sigma_SR pooling

**Files:**
- Modify: `src/analytics/cross_trial_log.py` (add `symbol: str` field, backfill default)
- Modify: `src/analytics/dsr.py` (sigma_SR pooling protocol)
- Create: `tests/test_cross_trial_log_migration.py` (schema migration guard)
- Create: `tests/test_dsr_multi_symbol.py` (multi-symbol DSR pooling)
- Modify: `data/cross_trial_sharpes.json` — ARCHIVE + RESET (mirror S16/S18/S21/S23)

**Steps:**

- [ ] **Step 1: Archive existing cross_trial_sharpes.json**

```bash
cp data/cross_trial_sharpes.json data/cross_trial_sharpes_v0.5-final.json
echo "[]" > data/cross_trial_sharpes.json
git add data/cross_trial_sharpes_v0.5-final.json data/cross_trial_sharpes.json
git commit -m "data: archive cross_trial_sharpes к v0.5-final + reset к [] для S33 multi-symbol (mirror S16/S18/S21/S23 honest close pattern)"
```

- [ ] **Step 2: Write failing test для schema migration (TDD RED)**

```python
# tests/test_cross_trial_log_migration.py
"""TrialEntry schema migration guard — S33 T3.

Per trading-logic-reviewer Round 2 Item #2:
Adding symbol: str field to TrialEntry breaks legacy entries (no symbol key).
Loader must backfill default `symbol="BTCUSDT"` для pre-S33 entries.
"""
import pytest
from src.analytics.cross_trial_log import CrossTrialLog, TrialEntry


def test_load_legacy_entry_no_symbol_field_backfills_BTCUSDT():
    """Pre-S33 entries had no symbol field — backfill to BTCUSDT (all prior single-symbol)."""
    legacy_json = '[{"sprint": 22, "oos_sharpe": 0.996}]'  # no symbol
    log = CrossTrialLog.from_json_str(legacy_json)
    assert len(log.entries) == 1
    assert log.entries[0]["symbol"] == "BTCUSDT"  # backfilled
    assert log.entries[0]["sprint"] == 22
    assert log.entries[0]["oos_sharpe"] == 0.996


def test_append_new_entry_requires_symbol():
    """New entries (S33+) MUST include symbol field."""
    log = CrossTrialLog()
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)
    assert len(log.entries) == 3
    assert {e["symbol"] for e in log.entries} == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}


def test_n_trials_counts_all_entries():
    """Per Item #7 decision (a): n_trials = total entries (not unique sprints)."""
    log = CrossTrialLog()
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)
    assert log.n_trials() == 3  # 3 separate trials, не 1 sprint
```

- [ ] **Step 3: Run test — verify RED**
```bash
pytest tests/test_cross_trial_log_migration.py -v
# Expected: FAIL — TrialEntry has no symbol field
```

- [ ] **Step 4: Update TrialEntry TypedDict + backfill loader**

```python
# src/analytics/cross_trial_log.py
from typing import TypedDict


class TrialEntry(TypedDict):
    """Cross-trial log entry per Bailey & López de Prado DSR (2014).
    
    Schema migrated S33 — added `symbol: str` field для multi-symbol DSR (Item #6+#7).
    Pre-S33 entries (no symbol) backfilled to "BTCUSDT" (all prior single-symbol).
    """
    sprint: int
    symbol: str  # NEW S33 — per consilium Round 2 Item #6
    oos_sharpe: float


class CrossTrialLog:
    @classmethod
    def from_json_str(cls, json_str: str) -> "CrossTrialLog":
        """Load с backward compat: missing `symbol` → backfill 'BTCUSDT'."""
        import json
        raw_entries = json.loads(json_str)
        entries = [
            TrialEntry(
                sprint=e["sprint"],
                symbol=e.get("symbol", "BTCUSDT"),  # backfill default
                oos_sharpe=e["oos_sharpe"],
            )
            for e in raw_entries
        ]
        return cls(entries=entries)
    
    def append_trial(self, *, sprint: int, symbol: str, oos_sharpe: float) -> None:
        """Append new trial — symbol REQUIRED (no default)."""
        self.entries.append(TrialEntry(
            sprint=sprint, symbol=symbol, oos_sharpe=oos_sharpe
        ))
    
    def n_trials(self) -> int:
        """Total trials (per (sprint, symbol) pair) per Item #7 decision (a)."""
        return len(self.entries)
```

- [ ] **Step 5: Run test — verify GREEN**
```bash
pytest tests/test_cross_trial_log_migration.py -v
# Expected: PASS
```

- [ ] **Step 6: Update sigma_sr() pooling protocol**

Per Item #6: option (a) — pool ALL (sprint, symbol) pairs as independent trials.

```python
# src/analytics/dsr.py
import statistics
from src.analytics.cross_trial_log import CrossTrialLog


def sigma_sr(log: CrossTrialLog) -> float | None:
    """Pool all (sprint, symbol) pairs — methodologically conservative.
    
    Per consilium S33 Item #6: pooling protocol (a) — all entries treated
    as independent trials. Conservative для multi-symbol (over-penalizes via
    higher cross-trial dispersion when symbols cluster differently — но safe side
    per Bailey & López de Prado eq. 12).
    """
    if log.n_trials() < 2:
        return None  # insufficient data
    sharpes = [e["oos_sharpe"] for e in log.entries]
    return statistics.stdev(sharpes)
```

- [ ] **Step 7: Write multi-symbol DSR test**

```python
# tests/test_dsr_multi_symbol.py
"""Multi-symbol DSR pooling protocol — S33 T3 (Items #6+#7).

Per consilium decision (a): pool all (sprint, symbol) pairs.
S33 multi-symbol → 3 trials per sprint (BTC + ETH + SOL).
"""
from src.analytics.cross_trial_log import CrossTrialLog
from src.analytics.dsr import sigma_sr, compute_dsr


def test_multi_symbol_S33_adds_3_trials():
    """S33 BTC+ETH+SOL → n_trials=3 (не 1 pooled)."""
    log = CrossTrialLog()
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)
    assert log.n_trials() == 3


def test_sigma_sr_pools_across_sprint_and_symbol():
    """Pooling protocol (a): sigma_sr from all entries pooled."""
    log = CrossTrialLog()
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)
    # Pooled stdev across 3 entries
    expected = statistics.stdev([0.85, 0.72, 0.61])
    assert abs(sigma_sr(log) - expected) < 1e-9
```

- [ ] **Step 8: Verify legacy single-symbol DSR computations preserved**

```bash
pytest tests/test_dsr.py -v  # existing DSR tests
# Expected: All passing — backfill default ensures no regression
```

- [ ] **Step 9: Commit**
```bash
git add src/analytics/cross_trial_log.py src/analytics/dsr.py \
        tests/test_cross_trial_log_migration.py tests/test_dsr_multi_symbol.py
git commit -m "feat(analytics): T3 — E DSR cross-trial extension (TrialEntry +symbol field with backfill BTCUSDT + sigma_SR pooling protocol (a) all entries) per consilium Items #6+#7+#9 — closes S14 Q2 carry-over"
```

---

### Task T4 — F backtest preparation (validation + named constants)

**Files:**
- Modify: `src/backtest/wfa.py` (или wherever WFA orchestrator) — pre-run validation
- Modify: `src/signalgen/strategy.py` — add named constant `MEAN_REVERSION_S17_RELAXED_PARAMS`

**Steps:**

- [ ] **Step 1: Find WFA orchestrator**
```bash
grep -rn "def run_wfa\|class WFA\|wfa_orchestrator" src/
```

- [ ] **Step 2: Add WFA fold coverage pre-run validation (Item #10)**

```python
# In WFA orchestrator entry function
def run_wfa(
    df: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    n_folds: int,
    embargo_bars: int = 20,
    symbol: str,
) -> WFAResult:
    """Run WFA с pre-run fold coverage validation."""
    # Per Item #10: assert dataset spans sufficient bars
    required_bars = (train_bars + test_bars) * n_folds + embargo_bars * (n_folds - 1)
    if len(df) < required_bars:
        raise ValueError(
            f"Symbol {symbol}: insufficient data {len(df)} bars, "
            f"WFA needs {required_bars} (train={train_bars} × test={test_bars} "
            f"× folds={n_folds} + embargo={embargo_bars} × {n_folds-1})"
        )
    
    # ... existing WFA logic ...
```

- [ ] **Step 3: Write WFA fold coverage test**

```python
# tests/test_wfa_fold_coverage.py
def test_wfa_raises_on_insufficient_bars():
    """SOL Bybit listing date may give < required bars — pre-run validation prevents silent fold-skip."""
    short_df = pd.DataFrame(...)  # 1000 bars (< required 6250 for K=5)
    with pytest.raises(ValueError, match="insufficient data"):
        run_wfa(short_df, train_bars=1000, test_bars=250, n_folds=5, symbol="SOLUSDT")
```

- [ ] **Step 4: Add S17-relaxed params named constant (Item #5)**

```python
# src/signalgen/strategy.py
"""Mean-reversion strategy с RSI + Bollinger Bands AND-gate.

S33 BACKTEST measurement uses MEAN_REVERSION_S17_RELAXED_PARAMS — see ADR 0050.
DO NOT inherit S15 params (RSI 30/70, BB 2σ) — they produced MC p=0.998 noise
(см. anti-S15-recurrence guard в ADR 0050).
"""

# S17-relaxed params per S33 ADR 0050 pre-registration (anti-data-snooping lock)
# Reference: sprint-17-btc-mean-reversion-relaxed.md PASS partial verdict
MEAN_REVERSION_S17_RELAXED_PARAMS = {
    "rsi_period": 14,
    "rsi_oversold": 35,        # NOT 30 (S15 noise)
    "rsi_overbought": 65,      # NOT 70 (S15 noise)
    "bb_period": 20,
    "bb_std_mult": 1.5,        # NOT 2.0 (S15 noise)
    "and_gate_required": True, # AND (RSI + BB), не OR
}
```

- [ ] **Step 5: Update MeanReversionRsiBBStrategy к use named constant**

Verify constant referenced (not copy-pasted) в strategy class init.

- [ ] **Step 6: Run pytest**
```bash
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
```

- [ ] **Step 7: Commit**
```bash
git add src/backtest/wfa.py src/signalgen/strategy.py tests/test_wfa_fold_coverage.py
git commit -m "feat(backtest): T4 — WFA fold coverage pre-run validation (Item #10) + MEAN_REVERSION_S17_RELAXED_PARAMS named constant (Item #5 anti-S15-recurrence guard)"
```

---

### Task T5 — F BACKTEST measurement run

**Files:** Read-only operations + JSON output
- Output: `data/sprint_33_F_measurement.json` (BTC + ETH + SOL WFA results)
- Output: append к `data/cross_trial_sharpes.json` (3 entries per S33)

**Steps:**

- [ ] **Step 1: Verify Parquet data available**
```bash
ls -la data/{BTCUSDT,ETHUSDT,SOLUSDT}_4h.parquet
# Expected: 3 files exist
```

Если ETH/SOL Parquet отсутствуют:
```bash
python -m src backfill --symbols ETHUSDT,SOLUSDT --start 2023-01-01 --end 2026-04-26 --interval 240
```

- [ ] **Step 2: Run F BACKTEST per pre-registration**

```bash
source .venv/bin/activate
python -m src wfa \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --interval 240 \
  --strategy mean_reversion_rsi_bb \
  --params S17_RELAXED \
  --wfa-train 1000 \
  --wfa-test 250 \
  --wfa-folds 5 \
  --embargo 20 \
  --output data/sprint_33_F_measurement.json \
  2>&1 | tee logs/sprint_33_F_run.log
```

Expected runtime: ~30-90 minutes (3 symbols × 5 folds × WFA computation).

- [ ] **Step 3: Append к cross_trial_sharpes.json (3 entries per Item #7 decision a)**

```python
# scripts/append_s33_trials.py
import json
from src.analytics.cross_trial_log import CrossTrialLog

with open("data/sprint_33_F_measurement.json") as f:
    results = json.load(f)

log = CrossTrialLog.from_json_file("data/cross_trial_sharpes.json")
for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
    log.append_trial(
        sprint=33,
        symbol=symbol,
        oos_sharpe=results[symbol]["oos_sharpe"],
    )
log.to_json_file("data/cross_trial_sharpes.json")
print(f"S33 trials appended. n_trials={log.n_trials()}")
```

- [ ] **Step 4: Compute aggregate metrics с n_eff correction (Item #8)**

```python
# scripts/compute_s33_aggregate.py
from src.backtest.strategy_metrics import compute_strategy_metrics
from src.analytics.dsr import compute_dsr, sigma_sr

# Aggregate trades across 3 symbols
all_trades = pd.concat([results[s]["trades_df"] for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]])
n_raw = len(all_trades)

# n_eff correction per Item #8 (Kish 1965 design effect)
rho_avg = 0.75  # BTC-ETH-SOL average pairwise correlation (empirical estimate)
m = 3
deflation = 1 + (m - 1) * rho_avg
n_eff = int(n_raw / deflation)

print(f"S33 F results:")
print(f"  Raw n_trades: {n_raw}")
print(f"  n_eff (correlation-deflated): {n_eff} (deflation factor {deflation:.2f})")
print(f"  T5 floor 100: raw {'PASS' if n_raw >= 100 else 'FAIL'}, n_eff {'PASS' if n_eff >= 100 else 'FAIL'}")

# Per-symbol DSR
log = CrossTrialLog.from_json_file("data/cross_trial_sharpes.json")
print(f"  n_trials post-S33: {log.n_trials()}")
print(f"  sigma_SR pooled: {sigma_sr(log):.4f}" if log.n_trials() >= 2 else "  sigma_SR: N/A")
```

- [ ] **Step 5: Save measurement output + log**

```bash
git add data/sprint_33_F_measurement.json data/cross_trial_sharpes.json logs/sprint_33_F_run.log
git commit -m "data(measurement): T5 — F BACKTEST run BTC+ETH+SOL 4H mean-reversion S17-relaxed params, WFA train=1000/test=250 K=5 + 3 trials appended к cross_trial_sharpes.json (Items #7+#8 n_eff correction)"
```

---

### Task T6 — ADR 0050 + sprint-33 page + index/counts sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0050-sprint-33-trading-restart.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-33-trading-restart.md`
- Modify: `llm-wiki/wiki/index.md` (+ sprint-33 + ADR 0050)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts: 36→37 sprints / 49→50 ADRs + S33 sprint history row)

**Steps:**

- [ ] **Step 1: Write ADR 0050 — comprehensive**

Sections:
- Status / Context (S32 series mature, 5 honest closes, T5 unreachable BINDING)
- 6 escalation items decisions (CONSENSUS APPROVE per ROUND 2)
- **9-item Pre-registration checklist (LOCKED)** per Item #4:
  1. Param set: `MEAN_REVERSION_S17_RELAXED_PARAMS` (RSI 35/65, BB 1.5σ, AND-gate)
  2. WFA window: train=1000 / test=250 (CC6 (b))
  3. Embargo: 20 bars (ADR 0014 default)
  4. OOS gate: OOS/IS ratio ≥ 0.7 (ADR 0014 default)
  5. Symbols: BTCUSDT + ETHUSDT + SOLUSDT (no additions)
  6. MC p ≤ 0.05 two-tailed
  7. DSR ≥ 0.95
  8. n_trials counting: protocol (a) — pool all (sprint, symbol) pairs
  9. sigma_SR pooling: protocol (a) — pool all entries
- **ESC-3 4 binding conditions для S34 LIVE** (Item #3)
- **Pre-committed failure branch** (Item #12) — S34 honest close v0.6 если F fails
- **Reviewer dispatch plan** (Item #15) — `quant-stats-reviewer` + `trading-logic-reviewer` only (skip 5 dormant agents)
- Implementation refs (T1-T6 commits)
- Consequences / Follow-ups

- [ ] **Step 2: Write sprint-33 page**

Standard skeleton с:
- Overview + 3-agent consilium reference
- Plan/ADR links
- 6 tasks shipped table
- КУ achieved
- Phase 5 verify outcome
- Phase 6 review (parallel quant-stats + trading-logic)
- F measurement results (raw + n_eff + per-symbol Sharpe + MC p + DSR)
- Verdict (PASS / FAIL conjoint)
- Pre-committed branch trigger (если applicable)

- [ ] **Step 3: index.md +entries**

- [ ] **Step 4: current-state.md sync**
- counts: 36→37 sprints / 49→50 ADRs + S33 sprint history row
- Update test/quality state baseline post-S33 test additions

- [ ] **Step 5: Update CI baseline (Item #13)**

```yaml
# .github/workflows/ci.yml
# Update pytest baseline 773 → new count post-S33
```

- [ ] **Step 6: Commit batch**

```bash
git add llm-wiki/wiki/project/decisions/0050-sprint-33-trading-restart.md \
        llm-wiki/wiki/project/sprints/sprint-33-trading-restart.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md \
        .github/workflows/ci.yml
git commit -m "docs(sprint): T6 — ADR 0050 + sprint-33 page + 9-item pre-registration checklist + ESC-3 4 binding conditions + pre-committed failure branch + reviewer dispatch + CI baseline update (Items #3+#4+#12+#13+#15)"
```

---

## Phase 5 Verify

```bash
source .venv/bin/activate
echo "=== pytest ===" && pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
# Expected: 773 + new tests (T1: 2 / T2: 3 / T3: 4 / T4: 1) = ~783 passing, 0 failures

echo "=== mypy ===" && mypy --strict src/ 2>&1 | tail -3
# Expected: 0 errors (S33 T1 fix)

echo "=== canonical ===" && python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: 16/30/74/45 unchanged

echo "=== F measurement output ===" && cat data/sprint_33_F_measurement.json | python3 -m json.tool | head -30
# Verify per-symbol metrics present

echo "=== cross_trial_log post-S33 ===" && cat data/cross_trial_sharpes.json | python3 -m json.tool
# Expected: 3 entries (BTCUSDT, ETHUSDT, SOLUSDT) per Item #7

echo "=== verification-before-completion checklist ===" 
# Use superpowers:verification-before-completion skill
```

Update SPRINT_STATE Phase 5 status="done".

---

## Phase 6 Review

Per Item #15 reviewer dispatch plan: only **`quant-stats-reviewer` + `trading-logic-reviewer`** parallel dispatch (skip 5 dormant agents для pure-stats sprint).

Parallel via `superpowers:dispatching-parallel-agents`:
- `quant-stats-reviewer`: validate CC-D fix correctness + DSR cross-trial impl + MC property tests + n_eff reporting
- `trading-logic-reviewer`: validate WFA fold coverage validation + named constant referenced (не copy-pasted) + schema migration backward compat

Address blockers per `superpowers:receiving-code-review` categorization.

---

## Phase 7 Sync

- log.md sprint-end entry
- Update SPRINT_STATE Phase 7 done

---

## Phase 8 Ship

Per `sprint-finish` skill HARD-GATE checklist:
1. Pre-validation (pytest + mypy)
2. HARD-GATE — sprint-33 page exists ✓
3. HARD-GATE — canonical counts sync ✓
4. HARD-GATE — ADR 0050 в index.md ✓
5. HARD-GATE — orphan-audit grep includes tests/
6. SPRINT_STATE → 8-ship
7. git push (all 6 push hooks fire)
8. gh pr create
9. CI runs (S32b infrastructure 5th PR validation)
10. gh pr merge --squash --delete-branch (phase-advance.sh validates Phase 5=done)
11. git tag v0.1.0-alpha.33
12. SPRINT_STATE → between-sprints

---

## Phase 9 Close

```
1. SPRINT_STATE → between-sprints
2. log.md session-end + F measurement verdict (PASS / FAIL)
3. mark_chapter "Sprint 33 — F measurement <verdict>"
4. git commit + push
5. **IF F FAIL:** trigger pre-committed failure branch per Item #12 — open S34 honest close v0.6 OR await operator override statement
6. **IF F PASS:** S34 = live multi-symbol infrastructure (650-850 LoC: Kelly capital-split + Coordinator orchestration + WAL retry + halt-cascade isolation per ESC-3 4 binding conditions)
```

---

## Self-Review

**Spec coverage:**
- ✓ T1: Test debt fix + bars_per_year integration test (Items Q6 + #11)
- ✓ T2: CC-D MC fix BOTH formulas + property tests (Items #1+#2)
- ✓ T3: E DSR cross-trial impl + schema migration (Items #6+#7+#9)
- ✓ T4: WFA fold coverage validation + S17 named constant (Items #5+#10)
- ✓ T5: F backtest measurement run + n_eff reporting (Item #8)
- ✓ T6: ADR + 9-item pre-registration + ESC-3 binding + failure branch + CI baseline (Items #3+#4+#12+#13+#15)

**Optional NOT in scope (defer):**
- Item #14 file-scoped ruff clean-on-touch — mention в S33 ADR coding standard

**Type consistency:** TrialEntry TypedDict + sigma_SR signature checked.

**Execution mode:** Controller-driven (subagent-driven would over-fragment small TDD tasks).

**Pre-registration discipline:** ALL 9 items LOCKED в S33 ADR ДО measurement run T5. Anti-data-snooping discipline (Bailey & López de Prado 2014).

**Pre-committed failure branch:** S33 ADR explicit clause perед measurement (mirror S17/S22/ADR 0032/0037 BINDING precedent).

---

## Related

- ADR 0014 (WFA train=2000/test=500 default — amended via CC6 (b) для 4H в S33)
- ADR 0015 (MC permutation test — CC-D fix restores compliance)
- ADR 0017 (review-agent harness)
- ADR 0048 (S32d Kit Phase 3 — 8 candidates A-H)
- ADR 0049 (S32e Kit Audit)
- ADR 0050 (this S33)
- Sprint S15 (anti-recurrence reference — S15 params noise)
- Sprint S17 (PASS partial 1H — S17-relaxed params source)
- Sprint S22 (PASS partial 4H — regime-independent edge)
- Sprint S23 (T5=100 unreachable BINDING)
- Sprint S27 (formula bug fixes — bars_per_year + Sortino + RSI/ATR + reason_code + MC seed)
- pre-s33-backlog.md — 3-agent consilium ROUND 1 + ROUND 2 verdicts
- Bailey & López de Prado 2014 (DSR + cross-trial sigma_SR)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique)
- Kish 1965 (design effect для clustered samples — n_eff Item #8)
- Phipson & Smyth 2010 (MC p-value (count+1)/(N+1) — CC-D reference)
