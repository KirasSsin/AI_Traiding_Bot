---
name: autoresearch-iterate
description: Iterative autoresearch loop for trading strategy improvement. Use when user says "запусти autoresearch", "autoresearch N итераций", "research strategy через autoresearch", "improve strategy iteratively". N iterations parametric (default 5). Each iteration = autoresearch run (bypass kit) → if FAIL, identify root cause → fix через formal kit cycle (ADR + sprint, commit к main) → return к autoresearch с new variant. Anti-snooping discipline preserved через held-out test.
---

# Autoresearch Iterate — alternating research-toy + formal-kit workflow

## When to use

Project: AI Trading Bot v0.1. Triggers:
- User says "запусти autoresearch", "autoresearch N итераций", "improve strategy"
- User wants iterative strategy improvement через karpathy-style autoresearch
- After autoresearch run with FAIL verdict — operator decides "fix and retry"

Skip if:
- Operator explicitly wants ONLY one-shot autoresearch (без iteration)
- No clear strategy variant к improve
- Held-out PASS already achieved (move к formal kit promotion)

## Why iterative pattern exists

Single autoresearch run = local optimization within fixed strategy paradigm. If paradigm has fundamental issue (e.g. Donchian без trend filter), no amount of param tuning helps.

Iteration logic:
1. **Research mode** finds best params within current paradigm
2. **Held-out FAIL** reveals paradigm limitation
3. **Formal kit cycle** adds methodology/feature к fix root cause (NEW strategy variant + new ADR)
4. **Return к research mode** runs autoresearch on improved variant
5. Repeat until held-out PASS OR N iterations exhausted OR no fixable cause

This bypasses kit ONLY for autoresearch loop (research toy), but uses formal kit для production-grade fixes between iterations.

## Steps (imperative)

### Step 1: Parse iteration count

User param: N iterations. Default = 5 если не specified.

Examples:
- "запусти autoresearch на 3 итерации" → N=3
- "autoresearch" (no number) → N=5
- "autoresearch 10 итераций" → N=10

Confirm с operator before starting большой N (>10 = 10+ hours).

### Step 2: Identify current strategy variant

From context + `autoresearch_donchian/train_donchian.py` `PARAMS` dict OR new variant. State explicitly:
- Strategy name (e.g. "Donchian breakout S35")
- Current params + ranges
- Iteration counter (i=1 of N)

### Step 3: Iteration loop

```
FOR i in 1..N:
    [3a] AUTORESEARCH RUN (bypass kit)
        - Branch: autoresearch/<strategy>-<date>-iter<i>
        - Run search loop (30-100 trials)
        - Held-out verification
        - Honest verdict (PASS / FAIL / DEGRADE)

    [3b] DECISION POINT
        - If held-out PASS → break loop, escalate к formal kit ROUND 7 brainstorm
        - If FAIL with identifiable root cause → continue to 3c
        - If FAIL без identifiable cause → break loop, declare paradigm dead

    [3c] ROOT CAUSE ANALYSIS
        - dispatch trader-expert: "Why FAIL? What feature missing?"
        - Concrete proposal: NEW variant with 1-2 distinct features
        - Examples: add EMA200 filter / add ADX gate / change exit logic

    [3d] FORMAL KIT FIX (between iterations)
        - PHASE 2 brainstorm: 3-agent consilium на NEW variant
        - PHASE 3 plan: feature spec + acceptance gates
        - PHASE 4 execute: implement variant в src/backtest/indicators.py + new strategy preset
        - PHASE 5-8 standard kit cycle
        - Tag v0.1.0-alpha.<N> ship к main
        - Update autoresearch_donchian/ к accept new variant param

    [3e] RETURN к 3a с new iteration counter
END FOR
```

### Step 4: Final verdict

After loop ends:
- **PASS achieved** (i ≤ N): summarize best variant + held-out metrics + escalation к formal kit ROUND 7 для production validation
- **N exhausted без PASS**: honest discard — strategy paradigm limited beyond current fixes
- **Paradigm dead detected**: stop early, document evidence, suggest different paradigm

## Examples

### Example 1: N=3, Donchian + EMA filter

```
Iteration 1:
  Variant: Donchian (current S35 LOCKED)
  Search: 30 trials lookback/atr/exit/period
  Held-out: FAIL (Sharpe -3.23)
  Root cause: no trend filter → false breakouts in ranging markets

  → FORMAL KIT FIX:
    - ADR 0059: NEW variant `donchian_with_ema200_filter`
    - Implement EMA200 gate в indicators.py donchian branch
    - Tag alpha.39 → main

Iteration 2:
  Variant: Donchian + EMA200 filter
  Search: 30 trials params + EMA period
  Held-out: PASS Sharpe 0.45 (50% of train preserved)
  → BREAK loop, escalate к formal kit ROUND 7

Iteration 3: NOT reached (PASS achieved)
```

### Example 2: N=5, paradigm dead

```
Iteration 1: Donchian baseline → FAIL overfit
Iteration 2: Donchian + EMA filter → FAIL (worse n_trades)
Iteration 3: Donchian + ADX gate → FAIL (similar issue)
Iteration 4: Donchian + ATR percentile filter → FAIL
Iteration 5: Donchian + all 3 filters combined → FAIL

Verdict: Donchian paradigm dead на crypto BTC 4H. Document evidence,
suggest different paradigm (HMM regime-switch / ML XGBoost / pairs arb)
через separate ROUND brainstorm.
```

## Anti-patterns

- ❌ Запускать iteration loop без trader-expert consultation на root cause
- ❌ Skip held-out verification ("результат хорошо на train — давай запустим")
- ❌ Lower acceptance gates чтобы pass верификацию (data snooping)
- ❌ Чистый research toy без formal kit fixes между iterations (= just over-optimizing same paradigm)
- ❌ Запускать N>10 без operator confirm (10+ часов work)
- ❌ Игнорировать "paradigm dead" signal (когда 3+ iterations no improvement = stop)
- ❌ Promote held-out PASS variant к main без formal kit cycle ROUND 7

## Output to user

Per iteration:
- Branch name + iteration counter (i/N)
- Train search summary (best params + score)
- Held-out verdict (PASS / FAIL + numbers)
- Root cause (если FAIL)
- Formal kit fix scope (если applicable)

Final summary:
- Total iterations used (i/N)
- Final variant + best held-out metrics
- Verdict + recommended next action

Не dump full search log — summarize.

## Boundaries

**autoresearch loop = bypass kit** (research toy mode):
- Branch `autoresearch/*` (NOT `feature/sprint-*`)
- NOT promoted к main directly
- NOT counted toward MAINNET promotion review
- NOT incrementing N_trials counter
- NO PHASE workflow

**Between iterations = formal kit cycle**:
- Branch `feature/sprint-N-<slug>`
- PHASE 2-8 standard
- ADR pre-registration
- 3-agent consilium для NEW variant brainstorm
- Tag v0.1.0-alpha.<N> ship к main
- canonical counts sync

## Related kit references

- `autoresearch_donchian/` — first instance of pattern (S35 Donchian iteration 1, FAIL held-out)
- `autoresearch_donchian/program_donchian.md` — single autoresearch run instructions
- `karpathy/autoresearch` upstream — `autoresearch/` cloned reference (LLM training original)
- ADR 0052 (LOCKED acceptance gates — preserved across iterations)
- ADR 0055 SD-8 (12mo MAINNET promotion — autoresearch results NOT counted)
- Bailey & López de Prado 2014 (anti-snooping discipline — held-out test mandatory)
