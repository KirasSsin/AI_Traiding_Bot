# Quant-Stats Reviewer — Memory Index

- [DSR kurtosis convention bug](memory_dsr_kurtosis_convention.md) — Bailey eq.13 requires total (Pearson) kurtosis; Fisher=True (excess) yields wrong denominator by +3 offset
- [DSR eq.12 sigma_SR multiplier](memory_dsr_eq12_sigma_sr.md) — For n_trials>1, sharpe_star must multiply z_combo by sigma_SR (cross-trial Sharpe std); current code omits it
- [Wilder EMA rule](memory_wilder_ema.md) — ADX/RSI/ATR use alpha=1/n, seed=SMA(n); classical EMA alpha=2/(n+1) for crossovers. ADR 0011.
- [Kelly fractional cap rule](memory_kelly_caps.md) — Phase 3 QK cap 3%, Phase 4 HK cap 5%; Wilson CI lower-bound as p (ADR 0018). Decimal hot path rule.
- [MC sign-flip baseline](memory_mc_sign_flip.md) — N=2000, p=(count+1)/(N+1), seeded rng. ADR 0015.
- [trade_extractor pnl_pct convention](memory_trade_extractor_pnl_pct.md) — pnl_pct = pnl_quote/(qty*entry_price) is simple return; DSR consumes via log(1+r) in compute_returns(use_log=True). Convention correct. S13 T5.
- [trade_extractor fees_paid NaN path](memory_trade_extractor_fees_paid_nan.md) — NaN in fees_paid column → Decimal('NaN') → pydantic Field(ge=0) raises ValidationError (finite_number check). Not silent. Non-critical but undocumented. S13 T5.
- [strategy_metrics T3 MaxDD bug + T2 Sortino variant](memory_strategy_metrics_t3_t2_bugs.md) — T3: initial_capital not prepended to equity before running_max.accumulate; first-loss MaxDD understated. T2: std(losers,ddof=1) inflates Sortino ~40-70% vs canonical RMS(losers). S13 T6.
