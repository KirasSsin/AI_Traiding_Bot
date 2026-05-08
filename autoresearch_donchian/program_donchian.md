# autoresearch_donchian

Адаптация karpathy/autoresearch paradigm для торговой стратегии Donchian breakout.

**ВАЖНО**: This bypasses bot project kit cycle (no PHASE workflow, no consilium ROUNDs, no LOCKED ADR). Pure research toy. Results NOT promoted к production main, NOT counted toward MAINNET promotion review. Anti-snooping discipline ВНУТРИ autoresearch (held-out test set), но overall = research mode.

## Setup

To set up a new experiment:

1. **Run tag**: today's date (e.g. `may8`). Branch `autoresearch/donchian-may8` already created.
2. **Read in-scope files**:
   - `prepare_donchian.py` — data load + train/held-out 80/20 split + evaluate_metric helper. **DO NOT MODIFY.**
   - `train_donchian.py` — single experiment runner. PARAMS dict on top. **AGENT MODIFIES THIS.**
   - `README.md` — context.
3. **Verify data**: `data/BTCUSDT_4h.parquet` must exist (7273 bars). Run setup check:
   ```bash
   .venv/bin/python autoresearch_donchian/prepare_donchian.py
   ```
4. **Initialize results.tsv**: Create header row:
   ```
   commit	metric	n_trades	mc_p	status	description
   ```
5. **Confirm and go**.

## Experimentation

Each experiment runs single backtest на train portion (~5818 bars). WFA K=5 / train=2000 / test=500 / embargo=20.

**Time budget**: ~30-90 sec per experiment (depends on params + n_trades). NOT 5 min like LLM training.

**Launch**: `.venv/bin/python autoresearch_donchian/train_donchian.py > run.log 2>&1`

**What you CAN do:**
- Modify `PARAMS` dict в `train_donchian.py`. ALL keys editable:
  - `lookback_n` — Donchian channel entry window (currently 20)
  - `exit_lookback_n` — Donchian channel exit window (currently 10)
  - `atr_period` — ATR smoothing period (currently 14)
  - `atr_stop_mult` — ATR multiplier для stop (currently 2.0)
- Add new param keys IF supported by `src/backtest/indicators.py` donchian branch.

**What you CANNOT do:**
- Modify `prepare_donchian.py` — fixed evaluation harness.
- Touch `data/BTCUSDT_4h.parquet`.
- Look at held-out portion (last 20% of data). NEVER referenced in search loop.
- Modify acceptance gates (Sharpe / DSR / MC thresholds — those locked в bot ADR 0052).
- Promote results к production (no PR к main, no δ TESTNET activation).

**The goal**: maximize `metric` (aggregate OOS Sharpe averaged across K=5 WFA folds).

**Constraints**:
- n_trades >= 10 минимум (otherwise NaN или meaningless metric)
- mc_p reported informationally (NOT gate)
- Higher metric = better. Negative = strategy lose money in train.

## Output format

Script prints summary like:

```
---
metric (sharpe):  X.XXXX
n_trades:         N
mc_p:             X.XXXX
fold_sharpes:     [X.XX, X.XX, X.XX, X.XX, X.XX]
status:           ok
seconds_total:    XX.X
```

Extract metric:
```bash
grep "^metric (sharpe):" run.log
```

## Logging results

When experiment done, append к `results.tsv` (TAB-separated):

| Column | Description |
|--------|-------------|
| commit | git commit hash (short, 7 chars) |
| metric | aggregate Sharpe (e.g. 1.234567) — `nan` для crashes |
| n_trades | n trades |
| mc_p | MC permutation p-value |
| status | `keep` / `discard` / `crash` |
| description | short text — what experiment tried |

Example:

```
commit	metric	n_trades	mc_p	status	description
a1b2c3d	-0.95	21	0.28	keep	baseline ADR 0054 LOCKED
b2c3d4e	1.20	35	0.05	keep	lookback=15
c3d4e5f	-0.40	12	0.50	discard	lookback=40 (too rare signals)
d4e5f6g	nan	0	nan	crash	atr_period=0 (div by zero)
```

DO NOT commit results.tsv (leave untracked per autoresearch convention).

## The experiment loop

LOOP:

1. Look at git state: current branch + commit
2. Edit `PARAMS` в `train_donchian.py` с experimental idea
3. `git add train_donchian.py && git commit -m "experiment: <description>"`
4. Run: `.venv/bin/python autoresearch_donchian/train_donchian.py > run.log 2>&1`
5. Read result: `grep "^metric (sharpe):\|^n_trades:\|^status:" run.log`
6. If empty → crash. Read `tail -50 run.log` для traceback.
7. Append к `results.tsv`
8. If metric improved → keep commit, advance branch
9. If metric worse OR equal → `git reset --hard HEAD~1` к previous commit

**Timeout**: kill any experiment > 5 min wall clock. Treat as crash.

**Crashes**: typo / silly bug → fix + re-run. Idea fundamentally broken → log "crash" + skip.

**NEVER STOP** (per autoresearch original): once loop begins, continue indefinitely. Operator wakes → many experiments logged. Stop only when manually interrupted.

## Held-out evaluation (POST-loop)

After search loop completes (operator interrupts OR fixed budget reached):

1. Pick best commit from `results.tsv` (highest metric)
2. Checkout that commit
3. Run held-out evaluation:
   ```bash
   .venv/bin/python -c "
   from autoresearch_donchian.prepare_donchian import load_split, evaluate_metric
   from autoresearch_donchian.train_donchian import PARAMS
   split = load_split()
   result = evaluate_metric(df=split.heldout_df, params=PARAMS, use_wfa=False)
   print('HELD-OUT:', result)
   "
   ```
4. **Honest verdict**:
   - Если held-out Sharpe ≥ train Sharpe (или близко) → genuine edge, может escalate к bot project ROUND 7 brainstorm для pre-registered formal eval
   - Если held-out Sharpe << train Sharpe → overfit, expected outcome, log в `verdict.md`
   - Если held-out Sharpe negative AT ALL → discard

5. Operator decides: discard branch OR open separate PR к bot project с proper ADR.

## Search space (recommendations)

Reasonable ranges to explore:

| Param | Default | Range | Note |
|-------|---------|-------|------|
| `lookback_n` | 20 | 5-100 | Lower = more signals (noisier) / higher = rare strong breakouts |
| `exit_lookback_n` | 10 | 3-50 | Should be < lookback_n |
| `atr_period` | 14 | 7-30 | Smoothing for ATR-based stop |
| `atr_stop_mult` | 2.0 | 0.5-5.0 | Lower = tight stops (frequent exits) / higher = wide stops |

Combinations to try:
- Tight breakout + tight stop: lookback=10, exit=5, atr_mult=1.0
- Wide breakout + wide stop: lookback=40, exit=20, atr_mult=3.0
- Faber 2007 classic Turtle: lookback=20, exit=10, atr_mult=2.0 (= baseline)
- Aggressive trend: lookback=15, exit=8, atr_mult=1.5
- Conservative: lookback=50, exit=25, atr_mult=2.5

## Disclaimer

This is **research toy** mode. NOT statistical validation per Bailey 2014 (data snooping risk). Results inadmissible для:
- δ TESTNET activation (bot project ADR 0055 binding)
- MAINNET promotion (bot project ADR 0055 SD-8 deferred к pre-registered ADR)
- N_trials counter (bot project sigma_SR pooling)

Если discovers genuine edge — formal verification REQUIRED through bot project kit (ROUND 7 brainstorm + ADR + S40+ sprint).
