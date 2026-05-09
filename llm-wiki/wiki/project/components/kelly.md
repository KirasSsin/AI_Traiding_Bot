---
title: Kelly (4-phase position fraction)
type: component
tags: [risk, kelly, sizing, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources: [src/risk/kelly.py, ADR 0012]
---

# Kelly — 4-phase position fraction

**TL;DR:** Pure functions returning equity-fraction `f` per ADR 0012 phases. Phase 1/2 — fixed caps. Phase 3 — Quarter-Kelly capped. Phase 4 — Half-Kelly capped. Wilson 95% CI lower bound для `p` в phases 3/4 (conservative estimate). No I/O, no state — caller passes `KellyCaps` from `Settings`.

## Публичный API

`src/risk/kelly.py`:

```python
@dataclass(frozen=True)
class KellyCaps:
    phase1: Decimal  # n < 30
    phase2: Decimal  # 30 <= n < 100
    phase3: Decimal  # 100 <= n < 200
    phase4: Decimal  # n >= 200

def phase_from_trade_count(n: int) -> int                 # → 1|2|3|4
def wilson_95_ci(wins: int, total: int) -> tuple[float, float]   # (lower, upper)
def kelly_fraction(p: float, b: float) -> float           # f* = (p*b - q) / b
def phase_adjusted_fraction(phase, p, b, caps) -> Decimal # final f for sizing
```

## Phase rules (ADR 0012)

| Phase | Trade count `n` | Fraction rule | Cap default |
|---|---|---|---|
| 1 | n < 30 | Fixed | `caps.phase1 = 0.01` |
| 2 | 30 ≤ n < 100 | Fixed | `caps.phase2 = 0.02` |
| 3 | 100 ≤ n < 200 | `min(0.25 · f*, caps.phase3)` Quarter-Kelly | `caps.phase3 = 0.03` |
| 4 | n ≥ 200 | `min(0.50 · f*, caps.phase4)` Half-Kelly | `caps.phase4 = 0.05` |

`f* = (p·b − q) / b` где `q = 1 − p`, `b = avg_win / avg_loss`. Returns `0` если `b ≤ 0` или `f* ≤ 0`.

## Wilson 95% CI

Используется Agresti-Coull form. Возвращает `(lower, upper)` floats (не Decimal — это статистика, не money; ADR 0007).

`RiskManager._compute_p_b` использует **lower bound** как conservative `p` для phases 3/4. Это критично: точечная оценка `wins/total` переоценивает edge на малой выборке.

## Numerical contracts

- `p` валидируется в `[0, 1]` (`ValueError` иначе).
- `b ≤ 0` → `kelly_fraction` returns `0` (defensive — avoids div-by-zero и не вызывает sizing).
- `phase_adjusted_fraction` raises `ValueError` для `phase ∉ {1,2,3,4}`.
- Decimal **только** для возвращаемого `f` (monetary fraction). Inputs `p, b` — float64 (statistical).

## Settings binding

```toml
risk_kelly_phase1_cap = "0.01"
risk_kelly_phase2_cap = "0.02"
risk_kelly_phase3_cap = "0.03"
risk_kelly_phase4_cap = "0.05"
```

`RiskManager.__init__` строит `KellyCaps` из этих полей. Магические числа в код запрещены (см. `~/.claude/CLAUDE.md` §3).

## Tests

`tests/unit/test_risk_kelly.py` — 18 cases:
- phase boundaries (n=29/30, 99/100, 199/200)
- Wilson CI sanity (wins=0, wins=total, edge probabilities)
- Kelly formula (p=0.6 b=2 → f*=0.4)
- ValueError для invalid inputs

## Связанные

- [[../decisions/0012-4-phase-kelly-sizing]] — source of truth
- [[../../trading/concepts/kelly-phases]] — formula derivation
- [[risk-manager]] — orchestration
- [[sizing]] — `compute_qty(equity, fraction, atr, price, k)`
