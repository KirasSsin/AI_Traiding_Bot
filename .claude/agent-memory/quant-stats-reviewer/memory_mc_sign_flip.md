---
name: MC sign-flip permutation baseline (ADR 0015)
description: N=2000 sign-flip permutations, p-value formula (count+1)/(N+1), reproducibility via np.random.default_rng(seed)
type: project
---

ADR 0015 binding rules:
- Primary test: N=2000 sign-flip permutations (flip return signs randomly, recompute Sharpe/metric each iteration).
- p-value: (count_at_least_as_extreme + 1) / (N + 1) -- Laplace smoothing, avoids p=0.
- Secondary test: block-bootstrap, block length L in [20,50] bars (preserves 1H autocorrelation).
- Reproducibility: np.random.default_rng(seed) -- never module-level np.random.*. Seed captured in experiment metadata.

**How to apply:** Any MC review -- verify N, p-value formula, and rng constructor.
