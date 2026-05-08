# autoresearch_donchian

Adapted karpathy/autoresearch paradigm для Donchian breakout trading strategy on BTCUSDT 4H.

## What it is

Autonomous experimentation loop. Agent edits `train_donchian.py` PARAMS dict, runs single backtest, logs result, keep/discard, repeat.

**Goal**: maximize aggregate OOS Sharpe (averaged across K=5 WFA folds на train portion).

**Inspired by**: https://github.com/karpathy/autoresearch (LLM training research). Adapted к trading domain.

## Files

| File | Editable? | Purpose |
|------|-----------|---------|
| `prepare_donchian.py` | NO | Data load + 80/20 train/held-out split + evaluate_metric helper |
| `train_donchian.py` | YES (agent edits) | PARAMS dict + single-experiment runner |
| `program_donchian.md` | NO | Agent instructions (loop semantics) |
| `results.tsv` | YES (agent appends) | Experiment log (commit + metric + status + description) |
| `README.md` | NO | This file |

## Data

- Source: `../data/BTCUSDT_4h.parquet` (7273 bars 2023-01-01 → 2026-04-26)
- Split: 80% train (~5818 bars) / 20% held-out (~1455 bars)
- Held-out **NEVER touched** during search loop. Final verdict only после search complete.

## Quick start

```bash
# 1. Verify data
.venv/bin/python autoresearch_donchian/prepare_donchian.py

# 2. Run baseline (ADR 0054 LOCKED Donchian S35)
.venv/bin/python autoresearch_donchian/train_donchian.py > run.log 2>&1

# 3. Read result
grep "^metric (sharpe):\|^n_trades:\|^status:" run.log

# 4. Loop: edit PARAMS, commit, run, log, keep/discard
```

## Branch convention

Per autoresearch program.md: `autoresearch/donchian-<tag>` (e.g. `autoresearch/donchian-may8`).

## Disclaimer

**Research toy mode.** Bypasses bot project kit cycle. Results NOT promoted к main, NOT applied к δ TESTNET activation, NOT counted toward MAINNET promotion review.

If discovers genuine edge → escalate к formal bot kit cycle (ROUND 7 brainstorm + new ADR + sprint).

## Reference

- Source repo: https://github.com/karpathy/autoresearch
- Bot project ADR 0054 (S35 Donchian LOCKED params baseline)
- Bot project ADR 0052 (acceptance gates LOCKED — informs honest verdict semantics)
