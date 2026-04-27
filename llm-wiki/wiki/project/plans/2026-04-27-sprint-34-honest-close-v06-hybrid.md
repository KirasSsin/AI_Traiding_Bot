---
title: Sprint 34 — 6-th Honest Close v0.6 + Acceptance-Criteria Amendment (hybrid A(a)+A(b))
type: plan
tags: [plan, sprint-34, honest-close-v06, acceptance-criteria-amendment, hybrid, n-eff-gate, t5-floor-amendment, ru]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/pre-s33-backlog.md (S34 direction consilium)
  - project/decisions/0050-sprint-33-trading-restart.md
  - project/sprints/sprint-33-trading-restart.md
  - project/architecture/acceptance-criteria.md
  - data/sprint_33_F_measurement.json
---

# Sprint 34 — Hybrid 6-th Honest Close v0.6 + Acceptance-Criteria Amendment

> **For agentic workers:** Use superpowers:executing-plans (controller-driven hybrid sprint).

**Goal:** Merge A(a) honest close v0.6 + A(b) amended spec ADR per S34 consilium consensus. Both consilium recommendations honored — scientific honesty preserved + forward path locked для future resumption.

**Architecture:** Documentation-heavy sprint + minimal code (n_eff gate enforcement). Tag v0.1.0-alpha.34. NO new measurement run в S34. Pre-check verifies S33 data outcome на amended gates (most likely confirms FAIL).

## Context

Per `pre-s33-backlog.md` S34 Direction Consilium (post-S33 ship):
- 3 agents (trader-expert + trading-logic + quant-stats) consensus: A(b) primary / A(a) fallback
- Operator chose hybrid (merge both)
- Both A(a) + A(b) double-approved consilium

S33 verdict: F BACKTEST FAIL conjoint (T5 raw 66<100 + n_eff 26<<100 + T6 -2.84 + MC 0.52 + DSR 0.919). Pre-committed failure branch (Item #12 ADR 0050) triggered.

**Hybrid scope:**
- Phase 1 (от A(a)): 6-th honest close v0.6 ADR + cross_trial archive + reset
- Phase 2 (от A(b)): Acceptance-criteria amendment ADR + 10-item pre-commit list LOCKED (T5=50, n_eff≥50, MC≤0.05, T6 unchanged, etc)
- Phase 3 (engineering): Pre-check S33 data на amended gates (verify outcome)
- Phase 4 (code): n_eff gate enforcement в evaluate_acceptance_gate() + tests
- Phase 5: Sprint-34 page + index/counts sync

**Estimate:** ~3-4 hours / ~85 LoC + 2 ADRs + sprint page.

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `data/cross_trial_sharpes_v0.6.json` | NEW (archive) | Copy current cross_trial_sharpes.json (3 S33 entries) |
| `data/cross_trial_sharpes.json` | RESET к `{"trials": []}` | mirror S16/S18/S21/S23 honest close pattern |
| `llm-wiki/wiki/project/decisions/0051-sprint-34-honest-close-v06.md` | NEW | 6-th honest close v0.6 ADR (mirror S14 ADR 0029 pattern) |
| `llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md` | NEW | Amended spec ADR с 10-item pre-commit list LOCKED |
| `llm-wiki/wiki/project/architecture/acceptance-criteria.md` | MODIFY | T5 floor 100→50 + n_eff threshold ≥50 + MC ≤0.05 + sample-size discipline section |
| `src/backtest/walk_forward.py` | MODIFY | `evaluate_acceptance_gate()` extended с n_eff parameter + n_eff gate check |
| `tests/unit/test_acceptance_gate_amendment.py` | NEW | n_eff threshold tests + amended T5 + MC threshold tests |
| `llm-wiki/wiki/project/sprints/sprint-34-honest-close-v06-hybrid.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-34 + ADR 0051 + ADR 0052 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | counts: 50→52 ADRs / 37→38 sprint pages + S34 sprint history row + acceptance-criteria amendment note |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end entries |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | S34 phase tracking + Phase 4 task progress |

---

## Tasks

### Task T1 — Engineering pre-check (validate amended gates на S33 data)

**Goal:** Verify outcome когда amended gates applied к S33 measurement data. Most likely STILL FAIL (n_eff=26 << 50). Confirms honest close + amendment justified.

**Files:** Read-only operation + pre-check script output

**Steps:**

- [ ] **Step 1: Compute amended gates на S33 data**

```bash
source .venv/bin/activate && python3 << 'PYEOF'
import json

with open("data/sprint_33_F_measurement.json") as f:
    s33 = json.load(f)

# Amended gates (per consilium 10-item pre-commit list)
T5_FLOOR_NEW = 50
N_EFF_FLOOR_NEW = 50
MC_THRESHOLD_NEW = 0.05  # tightened от 0.10
T6_THRESHOLD = 0.7  # UNCHANGED
DSR_THRESHOLD = 0.95  # UNCHANGED

# S33 actual values
n_raw = s33["aggregate_metrics"]["t5_n_trades_raw"]
n_eff = s33["aggregate_metrics"]["t5_n_trades_effective_n_eff"]
mc_p = s33["aggregate_metrics"]["mc_p_value_aggregate"]
t6 = s33["aggregate_metrics"]["t6_oos_is_sharpe_ratio_mean"]
dsr = s33["dsr"]["value"]

print("="*60)
print("S33 data на AMENDED gates pre-check (per consilium S34 consensus):")
print("="*60)
print(f"T5 raw: {n_raw} vs new floor {T5_FLOOR_NEW} → {'PASS' if n_raw >= T5_FLOOR_NEW else 'FAIL'}")
print(f"T5 n_eff: {n_eff} vs new threshold {N_EFF_FLOOR_NEW} → {'PASS' if n_eff >= N_EFF_FLOOR_NEW else 'FAIL'}")
print(f"MC p: {mc_p} vs new tightened {MC_THRESHOLD_NEW} → {'PASS' if mc_p <= MC_THRESHOLD_NEW else 'FAIL'}")
print(f"T6 OOS/IS: {t6} vs unchanged {T6_THRESHOLD} → {'PASS' if t6 >= T6_THRESHOLD else 'FAIL'}")
print(f"DSR: {dsr} vs unchanged {DSR_THRESHOLD} → {'PASS' if dsr >= DSR_THRESHOLD else 'FAIL'}")
print()
all_pass = (n_raw >= T5_FLOOR_NEW and n_eff >= N_EFF_FLOOR_NEW and mc_p <= MC_THRESHOLD_NEW and t6 >= T6_THRESHOLD and dsr >= DSR_THRESHOLD)
print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
PYEOF
```

**Expected output:** FAIL (n_eff=26 << 50, T6=-2.84 << 0.7, MC=0.52 >> 0.05, DSR=0.919 < 0.95). Confirms amendment alone insufficient — honest close justified.

- [ ] **Step 2: Save outcome к pre-check file**

```bash
# Save в data/sprint_34_amended_gates_precheck.json для record
```

- [ ] **Step 3: Document в S34 sprint page** (T5 task)

---

### Task T2 — ADR 0051 6-th honest close v0.6 + cross_trial archive + reset

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0051-sprint-34-honest-close-v06.md`
- Modify: `data/cross_trial_sharpes.json` (reset к `{"trials": []}`)
- Create: `data/cross_trial_sharpes_v0.6.json` (archive 3 S33 entries)

**Steps:**

- [ ] **Step 1: Archive cross_trial_sharpes.json к v0.6**

```bash
cp data/cross_trial_sharpes.json data/cross_trial_sharpes_v0.6.json
echo '{"trials": []}' > data/cross_trial_sharpes.json
```

- [ ] **Step 2: Write ADR 0051**

Mirror S14 ADR 0029 pattern (honest close documentation):
- Status: accepted
- Context: 6 strategy hypotheses tested, all FAIL conjoint per acceptance-criteria.md
- Decision: 6-th honest close v0.6 (mirror S14/S16/S18/S21/S23 BINDING precedent)
- Falsification record (6 hypotheses table): S13 EMA / S15 multi-symbol 1H / S17 BTC 1H relaxed / S20 BTC 15M / S22 BTC 4H / S33 multi-symbol 4H
- Structural insights binding: T5 single-symbol unreachable + multi-symbol n_eff deflation (rho=0.75)
- v0.7+ direction options (operator decides): pause / spec amendment (S34 amendment ready) / different strategy class / different timeframe
- Consequences: project state preserved, infrastructure mature, amendment locked для future resumption

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0051-sprint-34-honest-close-v06.md \
        data/cross_trial_sharpes.json \
        data/cross_trial_sharpes_v0.6.json
git commit -m "docs(adr): T2 — ADR 0051 6-th honest close v0.6 + cross_trial archive к _v0.6 + reset (mirror S14/S16/S18/S21/S23 pattern)"
```

---

### Task T3 — ADR 0052 acceptance-criteria amendment + 10-item pre-commit list LOCKED

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md`
- Modify: `llm-wiki/wiki/project/architecture/acceptance-criteria.md`

**Steps:**

- [ ] **Step 1: Write ADR 0052**

Sections:
- Status: accepted (LOCKED для future resumption)
- Context: S33 demonstrated multi-symbol expansion path empirically falsified due correlation deflation. T5=100 floor от Bailey 2014 generic, не asset-specific. Hudson & Urquhart 2021 documented crypto small-sample reality.
- Decision: Amend acceptance-criteria.md per consilium 10-item pre-commit list
- 10-item pre-commit list (verbatim per consilium trader-expert binding):
  1. T5 floor 100 → 50 (Hudson & Urquhart 2021 cite)
  2. n_eff threshold ≥ 50 (Kish 1965 design effect mandatory)
  3. MC threshold ≤ 0.05 (tightened от 0.10 — partial compensation для floor relaxation)
  4. T6 OOS/IS ≥ 0.7 UNCHANGED
  5. acceptance_gate.sharpe_gate_passed UNCHANGED
  6. Operator written acknowledgment template
  7. MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED (no new param search)
  8. Backtest data extended through full available OHLCV
  9. Multi-symbol n_eff correction mandatory
  10. n_trials counter starts ≥ 4 (pooling protocol (a))
- Operator written acknowledgment template (verbatim per trader): "Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not evidence of positive edge"
- Pre-check outcome от T1 (S33 data на amended gates STILL FAIL — documents amendment alone insufficient)
- Consequences: amendment LOCKED, future resumption pre-registered (anti-snooping discipline preserved), no measurement run в S34
- Operator action когда resuming: write acknowledgment, run new measurement sprint с amended gates

- [ ] **Step 2: Update acceptance-criteria.md**

Add section "S34 Amendment (LOCKED ADR 0052) — pending operator acknowledgment for v0.7+ resumption":
```markdown
## S34 Amendment (LOCKED ADR 0052 — pending operator acknowledgment for v0.7+ resumption)

Per S34 consilium consensus, acceptance-criteria amended:

| Threshold | v0.5 (original) | v0.7+ (amended LOCKED) |
|-----------|----------------|-----------------------|
| T5 n_trades raw floor | 100 | 50 |
| T5 n_eff threshold (NEW) | N/A | ≥ 50 (Kish 1965 mandatory) |
| MC p-value threshold | ≤ 0.10 | ≤ 0.05 (tightened) |
| T6 OOS/IS Sharpe ratio | ≥ 0.7 | ≥ 0.7 UNCHANGED |
| DSR | ≥ 0.95 | ≥ 0.95 UNCHANGED |
| acceptance_gate.sharpe_gate_passed | per-fold strict | UNCHANGED |

Operator acknowledgment required (per ADR 0052) when resuming.
```

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md \
        llm-wiki/wiki/project/architecture/acceptance-criteria.md
git commit -m "docs(adr): T3 — ADR 0052 acceptance-criteria amendment LOCKED (T5 floor 100→50 / n_eff≥50 NEW / MC≤0.05 tightened / T6+DSR unchanged) + 10-item pre-commit list per consilium"
```

---

### Task T4 — n_eff gate enforcement в evaluate_acceptance_gate()

**Files:**
- Modify: `src/backtest/walk_forward.py` `evaluate_acceptance_gate()`
- Create: `tests/unit/test_acceptance_gate_amendment.py`

**Steps:**

- [ ] **Step 1: Find current `evaluate_acceptance_gate()` signature**

```bash
grep -n "def evaluate_acceptance_gate" src/backtest/walk_forward.py
```

- [ ] **Step 2: Write failing test FIRST (TDD RED)**

```python
# tests/unit/test_acceptance_gate_amendment.py
"""Acceptance gate amendment tests — S34 T4 (per ADR 0052 LOCKED).

Validates n_eff threshold enforcement + amended T5 floor + tightened MC threshold.
"""
from src.backtest.walk_forward import evaluate_acceptance_gate


def test_amended_gates_n_eff_threshold_enforced():
    """n_eff < 50 → FAIL even если raw n ≥ 50 (Kish 1965 deflation)."""
    # S33 actual data: raw=66, n_eff=26 → должен FAIL
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.5, 0.6, 0.7, 0.8, 0.9],  # all > sharpe_gate
        mc_p_value=0.04,  # passes amended ≤ 0.05
        n_trades_raw=66,
        n_trades_n_eff=26,  # FAIL — below new threshold
        n_eff_threshold=50,
        t5_floor=50,
    )
    assert gate["passed"] is False
    assert "n_eff_threshold" in gate.get("failed_criteria", [])


def test_amended_gates_t5_floor_50():
    """T5 floor 50 — n_raw < 50 fails."""
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.5, 0.6, 0.7, 0.8, 0.9],
        mc_p_value=0.04,
        n_trades_raw=45,  # FAIL — below new floor 50
        n_trades_n_eff=45,
        n_eff_threshold=50,
        t5_floor=50,
    )
    assert gate["passed"] is False


def test_amended_gates_mc_threshold_tightened():
    """MC threshold 0.05 — p > 0.05 fails (tightened from 0.10)."""
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.5, 0.6, 0.7, 0.8, 0.9],
        mc_p_value=0.08,  # FAIL — above new 0.05 threshold (was passing 0.10)
        n_trades_raw=60,
        n_trades_n_eff=55,
        n_eff_threshold=50,
        t5_floor=50,
        mc_threshold=0.05,
    )
    assert gate["passed"] is False


def test_amended_gates_pass_all_amended():
    """All amended gates pass = overall PASS."""
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        mc_p_value=0.02,
        n_trades_raw=80,
        n_trades_n_eff=55,
        n_eff_threshold=50,
        t5_floor=50,
        mc_threshold=0.05,
    )
    assert gate["passed"] is True


def test_amended_gates_backward_compat_v05():
    """Without n_eff/threshold args, defaults к v0.5 behavior (T5 floor 100, no n_eff check)."""
    # Backward-compat: existing callers без new args continue working
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        mc_p_value=0.04,
    )
    # No raise, returns gate dict
    assert "passed" in gate
```

- [ ] **Step 3: Run test — verify RED**

```bash
pytest tests/unit/test_acceptance_gate_amendment.py -v
# Expected: FAIL — evaluate_acceptance_gate doesn't support n_eff yet
```

- [ ] **Step 4: Update `evaluate_acceptance_gate()`**

Add optional kwargs:
```python
def evaluate_acceptance_gate(
    *,
    fold_oos_is_sharpe_ratios: list[float],
    mc_p_value: float,
    sharpe_gate: float = 0.7,
    mc_threshold: float = 0.10,  # default v0.5 — overridable per S34 amendment к 0.05
    # S34 ADR 0052 amendment (LOCKED for v0.7+):
    n_trades_raw: int | None = None,
    n_trades_n_eff: int | None = None,
    n_eff_threshold: int | None = None,
    t5_floor: int | None = None,
) -> dict[str, object]:
    # existing logic +
    failed = []
    # n_eff check (S34 amendment)
    if n_trades_n_eff is not None and n_eff_threshold is not None:
        if n_trades_n_eff < n_eff_threshold:
            failed.append("n_eff_threshold")
    # T5 floor (amended)
    if n_trades_raw is not None and t5_floor is not None:
        if n_trades_raw < t5_floor:
            failed.append("t5_floor")
    # MC threshold (overridable per S34)
    if mc_p_value > mc_threshold:
        failed.append("mc_p_value")
    # ... existing sharpe_gate logic ...
    
    return {
        "passed": len(failed) == 0 and existing_pass,
        "failed_criteria": failed,
        ...
    }
```

- [ ] **Step 5: Run test — verify GREEN**

- [ ] **Step 6: Commit**

```bash
git add src/backtest/walk_forward.py tests/unit/test_acceptance_gate_amendment.py
git commit -m "feat(backtest): T4 — evaluate_acceptance_gate() extended с n_eff threshold + amended T5 floor + tightened MC threshold (per ADR 0052 LOCKED)"
```

---

### Task T5 — sprint-34 page + index/counts sync

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-34-honest-close-v06-hybrid.md`
- Modify: `llm-wiki/wiki/index.md` (+ sprint-34 + ADR 0051 + ADR 0052)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts: 50→52 ADRs / 37→38 sprints + S34 row)

**Steps:**

- [ ] **Step 1: Write sprint-34 page**

Sections:
- Overview: Hybrid 6-th honest close v0.6 + amendment (consilium consensus)
- Plan/ADR links (0051 + 0052)
- 5 tasks shipped table
- Pre-check outcome (T1)
- 6-hypothesis falsification record
- Operator decisions matrix для v0.7+
- Phase 5 verify
- Phase 6 review (skipped)

- [ ] **Step 2: index.md +entries**

- [ ] **Step 3: current-state.md sync**

- [ ] **Step 4: Commit batch**

```bash
git add llm-wiki/wiki/project/sprints/sprint-34-honest-close-v06-hybrid.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md
git commit -m "docs(sprint): T5 — sprint-34 page + index/counts sync (50→52 ADRs / 37→38 sprints + S34 sprint history row + amendment note)"
```

---

## Phase 5 Verify

```bash
source .venv/bin/activate
echo "=== pytest ===" && pytest tests/ -q --ignore=tests/integration 2>&1 | tail -3
# Expected: 803 + 5 NEW (T4) = 808 passing, 0 failures
echo "=== mypy ===" && mypy --strict src/ 2>&1 | tail -3
# Expected: 0 errors (strict baseline preserved)
echo "=== canonical ===" && python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: 16/30/74/45 unchanged
echo "=== cross_trial state post-archive ===" && cat data/cross_trial_sharpes.json
# Expected: {"trials": []} (reset)
echo "=== archive preserved ===" && cat data/cross_trial_sharpes_v0.6.json
# Expected: 3 S33 entries
echo "=== amendment в acceptance-criteria.md ===" && grep -A 5 "S34 Amendment" llm-wiki/wiki/project/architecture/acceptance-criteria.md | head -10
# Expected: amendment table visible
```

Update SPRINT_STATE Phase 5 = "done".

---

## Phase 6 Review

Skipped — config + tests + docs sprint, no production trading code logic changes beyond `evaluate_acceptance_gate()` extension (backward-compat default).

---

## Phase 7 Sync

log.md sprint-end entry — 6-th honest close v0.6 + amendment LOCKED.

---

## Phase 8 Ship

Per `sprint-finish` skill HARD-GATE checklist:
1. Pre-validation (pytest 808 + mypy 0)
2. HARD-GATE — sprint-34 page exists ✓
3. HARD-GATE — canonical counts sync ✓
4. HARD-GATE — ADR 0051 + ADR 0052 в index.md ✓
5. SPRINT_STATE → 8-ship
6. git push (all 6 push hooks fire)
7. gh pr create
8. CI runs (6th PR — strict baselines)
9. gh pr merge --squash --delete-branch
10. git tag v0.1.0-alpha.34
11. SPRINT_STATE → between-sprints

---

## Phase 9 Close

```
1. SPRINT_STATE → between-sprints
2. log.md session-end entry — v0.6 chapter end + v0.7+ deferred к operator
3. mark_chapter "Sprint 34 — 6-th honest close v0.6 + amendment LOCKED"
4. git commit + push
```

**v0.7+ direction (operator decision when resumption):**
- (a) Project pause indefinitely (S24 Option E precedent)
- (b) Run new measurement sprint с amended gates (already LOCKED ADR 0052)
- (c) Different strategy class (Donchian / ML / HMM — beyond mean-reversion paradigm, NEW hypothesis)
- (d) Different timeframe (1D с volume gate — but T5 problem worse per consilium)
- (e) Different asset class (uncorrelated instruments — beyond v0.1 scope)

---

## Self-Review

**Spec coverage:**
- ✓ T1 Engineering pre-check (validates amended gates на S33 data)
- ✓ T2 ADR 0051 6-th honest close + cross_trial archive + reset (от A(a))
- ✓ T3 ADR 0052 acceptance-criteria amendment + 10-item pre-commit list LOCKED (от A(b))
- ✓ T4 n_eff gate enforcement в evaluate_acceptance_gate (engineering)
- ✓ T5 sprint-34 page + index/counts sync

**Hybrid honors both consilium recommendations:**
- A(a) honest close: scientific honesty + falsification record + cross_trial archive
- A(b) amendment: forward path locked + 10-item pre-commit list + n_eff gate enforcement

**No placeholders:** all steps concrete с code/commands/expected output.

**Type consistency:** evaluate_acceptance_gate signature backward-compat (optional kwargs).

**Execution mode:** Controller-driven (docs-heavy + minor code, similar к S33 T1-T6 pattern).

**Pre-registration discipline preserved:** ADR 0052 LOCKED ДО future measurement (anti-data-snooping).

---

## Related

- ADR 0014 (WFA defaults — amendment per ADR 0052)
- ADR 0029 (S14 honest close — pattern reference for ADR 0051)
- ADR 0030/0032/0033/0036/0038 (prior 5 honest close ADRs — sequential pattern)
- ADR 0048 (S32d Kit Phase 3 — 8 candidates including A(b) candidate F)
- ADR 0050 (S33 Trading Restart — F BACKTEST FAIL, pre-committed failure branch trigger)
- ADR 0051 (this S34 — 6-th honest close v0.6)
- ADR 0052 (this S34 — acceptance-criteria amendment LOCKED)
- pre-s33-backlog.md S34 Direction Consilium section
- Bailey & López de Prado 2014 (DSR + pre-registration)
- Hudson & Urquhart 2021 (crypto small-sample reality — T5 amendment justification)
- Kish 1965 (design effect для clustered samples — n_eff threshold)
