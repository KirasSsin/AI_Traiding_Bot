---
title: Live Trade Reporter Component (S36, ADR 0055 SD-6)
type: component
tags: [component, analytics, live-sharpe, dsr, testnet-demo, sprint-36, adr-0055, ru]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - src/analytics/live_trade_reporter.py
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/components/dsr.md
---

# Live Trade Reporter

**TL;DR:** Adapted live-data reporter per ADR 0055 SD-6. Computes live Sharpe (per-trade), calibration ratio (vs S22 synthetic Sharpe=6.17), and MC gating (n>=20 warning / n>=40 gate). N_trials LOCKED at 7 per ADR 0055 SD-7. Entry point: `generate_live_report(trades, settings)`.

## Назначение

Backtest Sharpe computation (DSR + WFA) предназначен для pre-trade hypothesis validation — не для live monitoring. Для δ TESTNET demo нужна adapted methodology:
- Live Sharpe = per-trade annualized Sharpe (NOT fold-based)
- Calibration ratio = live_sharpe / S22_SYNTHETIC_SHARPE (tracks degradation vs synthetic baseline)
- MC gating = Permutation test на live trade PnL series (N_trials=DELTA_N_TRIALS_LOCKED)

## Ключевые константы

| Constant | Value | Source |
|----------|-------|--------|
| `S22_SYNTHETIC_SHARPE` | `6.17` | S22 BTC 4H synthetic result (best known) |
| `DELTA_N_TRIALS_LOCKED` | `7` | ADR 0055 SD-7 FREEZE (S22 hypothesis re-evaluation, no Bailey increment) |
| `MC_WARNING_THRESHOLD` | `20` | Minimum trades for advisory MC |
| `MC_GATE_THRESHOLD` | `40` | Minimum trades for binding MC gate |

## API

```python
def generate_live_report(
    trades: list[TradeRecord],
    settings: Settings,
) -> LiveReport:
    ...

@dataclass
class LiveReport:
    n_trades: int
    live_sharpe: float | None        # None если n < 2
    calibration_ratio: float | None  # None если live_sharpe is None
    mc_p_value: float | None         # None если n < MC_WARNING_THRESHOLD
    mc_status: MCStatus              # INSUFFICIENT / WARNING / GATE_ELIGIBLE
    dsr_status: DSRStatus            # per ADR 0056 thresholds
    notes: list[str]                 # operator-readable messages
```

## DSR n_trades thresholds (ADR 0056)

| n_trades | DSRStatus | Meaning |
|----------|-----------|---------|
| < 10 | `INSUFFICIENT_TRADES` | NaN returned — не gate-eligible |
| 10-29 | `UNDERPOWERED` | Warn — estimates unreliable |
| >= 30 | `GATE_ELIGIBLE` | Normal evaluation |

## MC gating levels

| n_trades | Level | Action |
|----------|-------|--------|
| < 20 | `INSUFFICIENT` | No MC computation |
| 20-39 | `WARNING` | Advisory MC p-value (не binding) |
| >= 40 | `GATE_ELIGIBLE` | Binding MC gate (p <= 0.05 required) |

## Calibration ratio interpretation

- `>= 1.0`: live performance exceeds synthetic baseline (strong)
- `0.5 - 1.0`: expected degradation range (acceptable)
- `< 0.5`: significant degradation below synthetic (investigate)
- `< 0.0`: negative live Sharpe (halt investigation)

## Tests

11 tests в `tests/unit/test_live_trade_reporter.py`:
- Empty trades → LiveReport с None fields
- n < 2 → live_sharpe=None
- n_trades < 10 → DSRStatus.INSUFFICIENT_TRADES
- n_trades 10-29 → DSRStatus.UNDERPOWERED
- n_trades >= 30 → DSRStatus.GATE_ELIGIBLE
- n < MC_WARNING_THRESHOLD → mc_status=INSUFFICIENT
- n 20-39 → mc_status=WARNING
- n >= 40 → mc_status=GATE_ELIGIBLE
- calibration_ratio = live_sharpe / S22_SYNTHETIC_SHARPE
- DELTA_N_TRIALS_LOCKED constant frozen at 7
- notes list non-empty когда warnings present

## Carry-overs к S37+

- **quant-stats C2**: Boundary tests n=10 + n=30 (off-by-one coverage per ADR 0056 thresholds)
- **quant-stats C3**: trial_mean_fold_oos_sharpe vs pooled trade-level Sharpe ADR documentation (semantic distinction formalized)
- MC p-value computation uses same `(count+1)/(N+1)` formula per ADR 0015 + S33 T2 fix

## Related

- [[../decisions/0055-sprint-36-delta-activation]] — SD-6 + SD-7 mandate
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — DSR n_trades thresholds
- [[dsr]] — core DSR module (Bailey & Lopez de Prado)
- [[halt-gate-wireup]] — wire-up component (sibling S36)
- [[strategy-metrics]] — WFA/backtest T1-T6 metrics (NOT для live monitoring)
