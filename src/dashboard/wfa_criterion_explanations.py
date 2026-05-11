"""S47 T15 — RU formula + threshold + impact narrative per WFA criterion.

CRITICAL: Each formula + threshold MUST match actual code semantics. Cross-references:
- ADR 0014 (walk-forward acceptance gates) — T1-T6 thresholds + sharpe_threshold=0.7 + p_threshold=0.05
- ADR 0052 (S34 amendment) — T5 floor (n>=50 raw OOS), n_eff_threshold (Kish 1965)
- ADR 0056 (DSR sigma sourcing) — DSR computation + n_trades thresholds
- Bailey & López de Prado 2014 — DSR formula (eq. 12 + eq. 13)

Code references:
- src/backtest/strategy_metrics.py::compute_t1_t6_metrics (T1-T6 actual implementations)
- src/backtest/walk_forward.py::evaluate_acceptance_gate (gate cascade L1-L4)
- src/analytics/dsr.py::compute_dsr (DSR per Bailey & López de Prado 2014)
- src/backtest/mc_permutation.py::sign_flip_p_value, block_bootstrap_p_value (MC tests)

Read by /api/wfa_criterion_explanations endpoint.
"""

from __future__ import annotations

from typing import TypedDict


class CriterionExplanation(TypedDict):
    name: str
    measures: str
    formula: str
    threshold: str
    impact: str
    related: str
    gate_role: str


WFA_CRITERION_EXPLANATIONS_RU: dict[str, CriterionExplanation] = {
    "t1_sharpe_oos": {
        "name": "T1 · Sharpe Ratio (OOS, annualized)",
        "measures": (
            "Соотношение средней доходности стратегии к её волатильности на out-of-sample "
            "(OOS) фолдах walk-forward analysis. Базовая мера risk-adjusted return."
        ),
        "formula": (
            "T1 = mean(pnl_pct) / std(pnl_pct, ddof=1) × √bars_per_year\n"
            "где pnl_pct — массив per-trade процентных доходностей по всем OOS trades;\n"
            "std с ddof=1 (sample std, N−1 в знаменателе);\n"
            "annualization_factor = √bars_per_year (default 8760 = 1H × 24/7).\n"
            "Источник: src/backtest/strategy_metrics.py:73-75 (compute_t1_t6_metrics)."
        ),
        "threshold": (
            "≥ 1.0 для PASS (acceptance-criteria.md amended footnote S13 PHASE 2). "
            "Significant overfit suspicion при > 3.0. NaN если std(pnl_pct)=0 (все trades идентичны). "
            "Источник: ADR 0014 §T1; Bailey & López de Prado 2014 (Sharpe baseline)."
        ),
        "impact": (
            "Sharpe < 1.0 = стратегия не оправдывает риск. Капитал лучше держать в risk-free "
            "instrument (T-bills) с тем же risk-adjusted profile. Sharpe > 3.0 на честных OOS "
            "практически невозможен — указывает на data leakage, скрытый overfitting или ошибку "
            "в pipeline (look-ahead bias, double-counting trades)."
        ),
        "related": (
            "Связан с T2 (Sortino — асимметричная волатильность) и DSR (deflated Sharpe — "
            "корректирует на multiple-comparisons bias). DSR использует тот же массив pnl_pct, "
            "но добавляет penalty за skewness, kurtosis и n_trials (selection bias)."
        ),
        "gate_role": (
            "Информационная метрика T1-T6 reportED separately от gate cascade. Gate cascade "
            "(per src/backtest/walk_forward.py::evaluate_acceptance_gate) использует "
            "fold_oos_is_sharpe_ratios per-fold gate с порогом 0.7 (см. T6 ниже)."
        ),
    },
    "t2_sortino_oos": {
        "name": "T2 · Sortino Ratio (OOS, annualized)",
        "measures": (
            "Аналог Sharpe, но в знаменателе только downside deviation (волатильность убыточных "
            "движений). Не штрафует за большие положительные отклонения. Caнonical formula per "
            "Sortino & Price 1994."
        ),
        "formula": (
            "downside_dev = √(mean(min(pnl_pct, 0)²))  # over ALL n trades, target=0\n"
            "T2 = mean(pnl_pct) / downside_dev × √bars_per_year\n"
            "NaN если downside_dev = 0 (нет losing trades — undefined denominator).\n"
            "Источник: src/backtest/strategy_metrics.py:84-91. S27 fix: pre-S27 ошибочно "
            "использовала std(losers_subset, ddof=1) что давало ~3.6× inflated Sortino."
        ),
        "threshold": (
            "≥ 1.5 для PASS (acceptance-criteria.md S13 PHASE 2). Источник: ADR 0014 §T2; "
            "Sortino & Price 1994."
        ),
        "impact": (
            "Sortino < 1.5 = стратегия теряет слишком много на убыточных trades относительно "
            "среднего профита. Особенно важна для asymmetric strategies (option selling, "
            "trend-following с большими редкими убытками)."
        ),
        "related": (
            "Sortino ≥ Sharpe всегда (downside_dev ≤ total std). Если Sortino << Sharpe → "
            "стратегия имеет fat upside tail (хорошо). Если Sortino >> Sharpe → fat downside tail (плохо)."
        ),
        "gate_role": (
            "Информационная — не входит в hard acceptance gate. Reported для оценки asymmetry profile."
        ),
    },
    "t3_max_drawdown": {
        "name": "T3 · Max Drawdown (peak-to-trough, OOS)",
        "measures": (
            "Максимальная просадка equity-кривой от пикового значения. Измеряется на equity, "
            "построенной из per-trade pnl_quote с initial_capital=10000."
        ),
        "formula": (
            "equity = [initial_capital] + initial_capital + cumsum(pnl_quote)  # prepend для "
            "корректного измерения первой просадки vs starting balance\n"
            "running_max = max accumulator over equity\n"
            "drawdown = (equity - running_max) / running_max  # negative values\n"
            "T3 = abs(min(drawdown))  # absolute value of worst drawdown\n"
            "Guard: при running_max=0 (total blowout) → -100% (не NaN).\n"
            "Источник: src/backtest/strategy_metrics.py:96-104."
        ),
        "threshold": (
            "< 25% (0.25) для PASS (acceptance-criteria.md S13 PHASE 2). Источник: ADR 0014 §T3."
        ),
        "impact": (
            "MaxDD ≥ 25% означает что в worst-case инвестор пережил бы потерю четверти капитала. "
            "Большинство retail и institutional счетов закрываются (margin call, panic exit) "
            "при DD 20-30%. MaxDD прямо влияет на Calmar Ratio (Sharpe / MaxDD)."
        ),
        "related": (
            "Связан с risk-of-ruin расчётами. Combined с T1 даёт Calmar Ratio. Высокий T1 при "
            "высоком T3 = шумная стратегия (много волатильности обоих типов)."
        ),
        "gate_role": (
            "Информационная — не в hard gate. Operator решение о deployment учитывает T3 "
            "независимо от gate verdict."
        ),
    },
    "t4_win_rate": {
        "name": "T4 · Win Rate + Avg RR (OOS)",
        "measures": (
            "Доля winning trades (T4_WIN_RATE) и average risk-reward отношение (T4_AVG_RR — "
            "mean(winners) / mean(|losers|)). Совместно характеризуют распределение исходов."
        ),
        "formula": (
            "winners = pnl_pct[pnl_pct > 0]\n"
            "losers_abs = abs(pnl_pct[pnl_pct < 0])\n"
            "T4_WIN_RATE = len(winners) / n_trades\n"
            "T4_AVG_RR = mean(winners) / mean(losers_abs)  # NaN если len(winners)=0 OR len(losers_abs)=0\n"
            "Источник: src/backtest/strategy_metrics.py:107-113."
        ),
        "threshold": (
            "PASS = (win_rate ≥ 45% AND RR ≥ 1.5) OR (win_rate ≥ 35% AND RR ≥ 2.0). "
            "Это два альтернативных рабочих профиля: «balanced» (45/1.5) и «high-RR» (35/2.0). "
            "Источник: ADR 0014 §T4."
        ),
        "impact": (
            "Низкий win rate БЕЗ компенсирующего высокого RR = убыточная стратегия. "
            "Профили fail при: WR < 35% независимо от RR, OR WR в [35-45%] и RR < 2.0, "
            "OR WR ≥ 45% но RR < 1.5."
        ),
        "related": (
            "Expectancy = WR × avg_win − (1−WR) × avg_loss. T4 thresholds выведены из требования "
            "expectancy > 0 с margin для transaction costs. RR < 1.0 = «winners < losers по amplitude», "
            "требует WR > 50% для break-even."
        ),
        "gate_role": (
            "Информационная — не в hard gate. Operator проверяет распределение исходов через T4 "
            "перед deployment."
        ),
    },
    "t5_t_stat": {
        "name": "T5 · Mean PnL + t-stat + n_trades (OOS)",
        "measures": (
            "Статистическая значимость средней доходности per trade. T-stat проверяет null hypothesis "
            "«mean(pnl_pct) = 0» (стратегия не отличается от случайного входа). n_trades — sample size."
        ),
        "formula": (
            "T5_MEAN_PNL_PCT = mean(pnl_pct)\n"
            "T5_T_STAT = mean(pnl_pct) / (std(pnl_pct, ddof=1) / √n_trades)  # one-sample t-test vs 0\n"
            "T5_N_TRADES = n  # raw count of OOS trades\n"
            "NaN если n ≤ 1 OR std=0.\n"
            "Источник: src/backtest/strategy_metrics.py:116-120."
        ),
        "threshold": (
            "PASS = (mean > 0) AND (t-stat > 2.0) AND (n ≥ 100 [original] OR ≥ 50 [S34 amended floor]). "
            "T5_FLOOR=50 LOCKED per ADR 0014 §S44 anti-snooping commit (Bailey 2014 small-sample "
            "T-stat unreliability — не negotiable). См. также walk_forward.py L4 gate (n_trades_raw < t5_floor)."
        ),
        "impact": (
            "n < 50 = small-sample T-stat unreliable (Bailey 2014). Стратегия может показать "
            "случайный +mean, но без statistical power подтвердить эдж. T5 fail = стратегия "
            "статистически не отличима от случайной. T-stat > 2.0 ≈ 95% confidence (single-tail). "
            "Без T5 PASS любой positive PnL — anecdotal, не reproducible."
        ),
        "related": (
            "T5_FLOOR — структурная преграда для low-frequency стратегий (4H/1D crypto), которые "
            "fire 5-20 trades в OOS windows vs 50 минимум. См. ADR 0014 §S44 «Trade-frequency derivation»."
        ),
        "gate_role": (
            "L4 acceptance gate (если t5_floor передан): n_trades_raw < t5_floor → failed_criteria "
            "включает 't5_floor'. Hard blocker для overall PASS."
        ),
    },
    "t6_oos_is_sharpe_ratio_mean": {
        "name": "T6 · OOS/IS Sharpe Ratio (per-fold, mean)",
        "measures": (
            "Среднее отношение out-of-sample Sharpe к in-sample Sharpe по K фолдам walk-forward. "
            "Близко к 1 = OOS performance не деградирует относительно IS. Близко к 0 (или негативно) "
            "= overfitting. Это самая важная WFA-метрика."
        ),
        "formula": (
            "fold_oos_is_sharpe = [(OOS_Sharpe_fold_k / IS_Sharpe_fold_k) for k in folds]  # supplied by caller\n"
            "T6 = mean(fold_oos_is_sharpe)\n"
            "NaN если список пустой.\n"
            "Источник: src/backtest/strategy_metrics.py:122-126; per-fold ratios computed в WFA orchestrator."
        ),
        "threshold": (
            "Mean ≥ 0.7 для PASS на acceptance-criteria.md уровне. Per-fold gate (L1) тот же "
            "порог 0.7: каждый fold должен иметь OOS/IS ≥ 0.7 (sharpe_threshold default). "
            "Источник: ADR 0014 §T6 + walk_forward.py:159, 196."
        ),
        "impact": (
            "OOS/IS ratio = 1.0 → IS performance полностью переносится на OOS (идеал). "
            "OOS/IS < 0.7 на каком-либо fold → этот fold failed (failed_folds list). "
            "OOS/IS < 0 → стратегия в OOS теряет деньги при положительном IS (классический overfit signature)."
        ),
        "related": (
            "Связан с DSR (тоже корректирует Sharpe на overfitting risk, но через статистическое "
            "распределение). T6 более прямой operational metric — буквально измеряет drift между "
            "training и deployment."
        ),
        "gate_role": (
            "L1 hard gate (per-fold): любой fold с OOS/IS < 0.7 → sharpe_gate FAIL → overall PASS = False. "
            "Самый строгий и binding gate. См. walk_forward.py:193-198."
        ),
    },
    "dsr": {
        "name": "DSR · Deflated Sharpe Ratio (Bailey & López de Prado 2014)",
        "measures": (
            "Корректирует наблюдаемый Sharpe на: малый sample size, non-normality (skewness + "
            "kurtosis), multiple-testing bias (n_trials). Возвращает probability в (0, 1) что "
            "истинный Sharpe превышает benchmark после поправок."
        ),
        "formula": (
            "1. Compute returns: log(1 + pnl_pct) если use_log=True (default), иначе pnl_pct\n"
            "2. mean = avg(returns), std = sample std (ddof=1, N−1), sharpe = mean / std\n"
            "3. skew, kurt = scipy.stats (kurt = Pearson, fisher=False per Bailey 2014 eq. 13)\n"
            "4. Если n_trials > 1: SR* = benchmark + sigma_SR × ((1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e)))\n"
            "   где γ = 0.5772 (Euler-Mascheroni), Φ⁻¹ — inverse normal CDF.\n"
            "   Иначе SR* = benchmark.\n"
            "5. denom = √(1 − skew·SR + (kurt − 1)/4 · SR²)  # NaN если denom_inner ≤ 0\n"
            "6. z_DSR = (SR − SR*) × √(N − 1) / denom\n"
            "7. DSR = Φ(z_DSR)  # standard normal CDF\n"
            "Источник: src/analytics/dsr.py:54-151 (compute_dsr). Bailey & López de Prado 2014, eq. 12 + 13."
        ),
        "threshold": (
            "≥ 0.95 для PASS на conjoint level (high statistical confidence). Per ADR 0056: "
            "n_trades < 10 → DSR=NaN, status=INSUFFICIENT_TRADES; 10 ≤ n < 30 → status=UNDERPOWERED; "
            "n ≥ 30 → status=GATE_ELIGIBLE. sigma_SR REQUIRED при n_trials > 1 (raises ValueError)."
        ),
        "impact": (
            "DSR = 0.50 = «coin flip» — Sharpe мог быть случайным. DSR > 0.95 = strong evidence "
            "что эдж реален после всех поправок. INSUFFICIENT_TRADES (n<10) делает DSR не вычислимым. "
            "UNDERPOWERED (10≤n<30) — DSR посчитан но cross-trial variance не enough для надёжного n_trials adjustment."
        ),
        "related": (
            "DSR пытается решить ту же проблему overfitting, что и WFA T6. WFA — operational "
            "(walk forward in time). DSR — statistical (penalize Sharpe для multiple testing). "
            "Per ADR 0014 verdict: DSR informational, NOT in gate decision (но reported)."
        ),
        "gate_role": (
            "Informational reporting per ADR 0014. NOT в evaluate_acceptance_gate (см. walk_forward.py "
            "docstring: «DSR is computed and reported (informational) but NOT в gate decision»). "
            "Some конкретные runners (donchian_runner.py) могут использовать DSR threshold локально."
        ),
    },
    "mc_p_value": {
        "name": "MC · Monte Carlo Permutation P-Value",
        "measures": (
            "Probability что наблюдаемая средняя доходность могла появиться случайно из shuffled "
            "trade returns. Тест нулевой гипотезы «нет эджа, mean(returns) = 0»."
        ),
        "formula": (
            "Sign-flip test (sign_flip_p_value):\n"
            "  observed = abs(mean(returns))\n"
            "  for i in 1..n_iterations: signs = random ±1 array; permuted = returns × signs;\n"
            "    count += 1 if abs(mean(permuted)) ≥ observed\n"
            "  p = (count + 1) / (n_iterations + 1)  # +1 prevents p=0 с finite permutations\n\n"
            "Block bootstrap (block_bootstrap_p_value): то же самое но с блочной перестановкой "
            "длины MC_BLOCK_SIZE=20 (preserves autocorrelation в returns series).\n"
            "Источник: src/backtest/mc_permutation.py:28-65 (sign_flip), :70-110 (block bootstrap)."
        ),
        "threshold": (
            "≤ 0.05 для PASS на S34+ (ADR 0052 tightened от 0.10 для v0.7+). "
            "Источник: walk_forward.py:160 (p_threshold=0.05 default); ADR 0015 + ADR 0052. "
            "n_iterations default 2000 (ADR 0015)."
        ),
        "impact": (
            "p > 0.05 = статистически нельзя отвергнуть гипотезу о случайности. p = 0.50 = "
            "результат полностью совместим со случайностью. p = 0.01 = очень сильное evidence эджа. "
            "MC_BLOCK_SIZE=20 важен для крипто 4H+ TFs где autocorrelation обусловлена session "
            "effects (Asia/EU/US overlap)."
        ),
        "related": (
            "Дополняет DSR другим путём: DSR — analytical (Bailey 2014 formulae), MC — empirical "
            "(actual permutation distribution). Если оба согласны (DSR > 0.95 AND MC p < 0.05) — "
            "сильный signal реального эджа. Если конфликтуют — investigate."
        ),
        "gate_role": (
            "L2 hard gate per ADR 0015: mc_p_value > p_threshold → mc_gate FAIL → overall PASS = False. "
            "См. walk_forward.py:199, 216-217."
        ),
    },
}


def get_criterion_explanation(criterion_id: str) -> CriterionExplanation | None:
    """Return RU explanation per criterion; None if unknown."""
    return WFA_CRITERION_EXPLANATIONS_RU.get(criterion_id)


def get_all_criterion_explanations() -> dict[str, CriterionExplanation]:
    """Return full dict (copy) of all criterion explanations for /api endpoint."""
    return WFA_CRITERION_EXPLANATIONS_RU.copy()
