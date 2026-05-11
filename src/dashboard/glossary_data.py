"""S48 T5 — RU glossary content для GlossaryTab UI page (Bug E core).

Content:
- T1-T6 + DSR + MC criterion explanations (extends wfa_criterion_explanations.py)
- Trade statistics finals (PnL, Win rate, Profit Factor, etc.)
- Warning codes (mc_noise, low_sample, raw_full_period, subperiod_robustness, etc.)
- Symbols (▸ ▲ ⚠ ✓ ✗) UI legend
- Strategy presets short descriptions

STRATEGY_TO_METRICS_MAP — hand-curated (architect C3): explicit per-strategy
applicability instead of auto-sync. 6 presets coverage. Drift OK для small set.

Cross-references:
- ADR 0014 (walk-forward acceptance gates) — T1-T6 thresholds + sharpe_threshold=0.7
- ADR 0052 (S34 amendment) — T5 floor (n>=50 raw OOS), n_eff_threshold (Kish 1965),
                              MC p_threshold tightened к 0.05
- ADR 0056 (DSR sigma sourcing) — DSR computation Pearson kurtosis (fisher=False)
- ADR 0015 — MC permutation block_size=20
- ADR 0008 — Bybit Spot taker commission 0.1% per side
"""

from __future__ import annotations

from typing import TypedDict


class GlossaryEntry(TypedDict):
    section: str
    description_ru: str
    applies_to: list[str]  # Strategy preset IDs OR ["*"] для universal terms
    adr_ref: str | None


SECTIONS: list[str] = [
    "verdict_status",  # 1. Verdicts + symbols
    "gate_blocking_metrics",  # 2. T5_floor, DSR, MC, OOS/IS gate
    "informational_metrics",  # 3. T1-T4, T6 (informational per ADR 0014)
    "trade_statistics",  # 4. PnL, Win rate, Profit Factor, etc.
    "chart_vocabulary",  # 5. Equity, drawdown, monthly heatmap
    "warnings",  # 6. WFA discipline warnings
    "strategy_presets",  # 7. Strategy preset short descriptions
]


GLOSSARY_ENTRIES: dict[str, GlossaryEntry] = {
    # === verdict_status (4 entries) ===
    "verdict_pass": {
        "section": "verdict_status",
        "description_ru": (
            "Стратегия прошла все обязательные acceptance gates (T5_floor + MC + DSR + "
            "fold OOS/IS ≥ 0.7). Pre-registration валиден. Можно использовать для "
            "live/paper trading с пониманием honest validation discipline."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    "verdict_fail": {
        "section": "verdict_status",
        "description_ru": (
            "Стратегия НЕ прошла как минимум один обязательный gate. Использовать в "
            "live trading НЕ рекомендуется. См. блок ▸ ДЕТАЛЬНЫЙ РАЗБОР для причин."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    "verdict_wfa_fail_data": {
        "section": "verdict_status",
        "description_ru": (
            "Walk-forward analysis провалена из-за недостатка данных (n_trades < 50 "
            "OR WFA folds < 5). Не статистически значимый результат — DSR computation "
            "skipped per ADR 0052 §S44 anti-snooping."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "verdict_raw": {
        "section": "verdict_status",
        "description_ru": (
            "Полный full-period backtest без WFA discipline. Подвержен look-ahead bias. "
            "Используется только для exploratory tests. НЕ basis для live decisions."
        ),
        "applies_to": ["atr_breakout", "volume_breakout_iter10"],
        "adr_ref": None,
    },
    # === gate_blocking_metrics (5 entries) ===
    "t5_n_trades": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Количество OOS-сделок. Bailey 2014 minimum для DSR statistical significance: "
            "n ≥ 50 (S34 ADR 0052 amendment, было 100). Если n < 50 — DSR computation "
            "skipped, verdict WFA_FAIL_DATA. Hard blocker L4 gate в walk_forward.py."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "n_eff_threshold": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Effective sample size (Kish 1965) — минимум 50. Учитывает autocorrelation "
            "trades через n_eff = n / (1 + 2·Σρ_k). Hard blocker, независимый от "
            "t5_n_trades raw count. Per ADR 0052 §10 п.2."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "dsr": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Deflated Sharpe Ratio (Bailey & López de Prado 2014). Corrected Sharpe "
            "учитывая multiple comparisons + non-normality (skewness + kurtosis). "
            "Использует Pearson kurtosis (fisher=False) per ADR 0056. Threshold ≥ 0.95 "
            "для PASS (high statistical confidence)."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0056",
    },
    "mc_p_value": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Monte Carlo permutation p-value (sign-flip + block_bootstrap, "
            "MC_BLOCK_SIZE=20 per ADR 0015). Threshold ≤ 0.05 PASS (S34 ADR 0052 "
            "ужесточил с 0.10). Если p > 0.05 — returns indistinguishable от random "
            "walk. n_iterations default 2000."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0015",
    },
    "fold_oos_is_sharpe": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Per-fold Sharpe ratio OOS/IS. Threshold ≥ 0.7 PASS. Если хотя бы 1 fold "
            "не прошёл — стратегия отклоняется (failed_folds). L1 hard gate в "
            "acceptance cascade — самый строгий и binding gate per walk_forward.py:193-198."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    # === informational_metrics (5 entries) ===
    "t1_sharpe_oos": {
        "section": "informational_metrics",
        "description_ru": (
            "Sharpe Ratio (annualized OOS): mean(per-trade returns) / std × √bars_per_year. "
            "Threshold ≥ 1.0 (PASS), > 3.0 OVERFIT suspicion. Информационный per ADR 0014 "
            "— НЕ в hard acceptance gate. Подробности: см. WFA criterion explanations."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    "t2_sortino_oos": {
        "section": "informational_metrics",
        "description_ru": (
            "Sortino Ratio — downside-only volatility вариант Sharpe (Sortino & Price 1994). "
            "Threshold ≥ 1.5 PASS. S27 fix preserved canonical formula (target=0 over всех n "
            "trades). Информационный."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "t3_max_drawdown": {
        "section": "informational_metrics",
        "description_ru": (
            "Максимальная просадка equity curve (peak-to-trough). Threshold < 25% PASS. "
            "Прокси-оценка risk-of-ruin. При DD 20-30% retail/institutional счёт обычно "
            "закрывают (margin call). Информационный."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "t4_win_rate": {
        "section": "informational_metrics",
        "description_ru": (
            "Win rate (доля прибыльных сделок) + Avg RR. Threshold: (WR ≥ 45% AND RR ≥ 1.5) "
            "OR (WR ≥ 35% AND RR ≥ 2.0). Калибровка через payoff ratio — два альтернативных "
            "рабочих профиля. Информационный."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "t6_oos_is_sharpe_ratio": {
        "section": "informational_metrics",
        "description_ru": (
            "Mean(OOS Sharpe / IS Sharpe) по фолдам. Threshold ≥ 0.7 PASS. Overfit "
            "detector — если OOS << IS, стратегия curve-fitted к training period. "
            "Per-fold threshold идентичен mean threshold (L1 gate)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    # === trade_statistics (7 entries) ===
    "total_pnl_pct": {
        "section": "trade_statistics",
        "description_ru": (
            "Cumulative profit-and-loss в процентах от initial balance. Положительное = "
            "profit, отрицательное = loss. Не annualized — сырое накопленное значение."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "total_pnl_quote": {
        "section": "trade_statistics",
        "description_ru": (
            "Cumulative PnL в quote currency (USDT). Доступно для replay engine path; "
            "research presets emit None (нет capital basis)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "win_rate": {
        "section": "trade_statistics",
        "description_ru": (
            "Доля прибыльных сделок (n_winners / n_total). Без context payoff ratio "
            "недостаточен для оценки edge — высокий WR с RR < 1.0 может быть убыточным."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "profit_factor": {
        "section": "trade_statistics",
        "description_ru": (
            "Sum(winners) / |Sum(losers)|. PF > 1 = profitable; PF > 2 strong edge; "
            "PF < 1 losing strategy."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "avg_win_quote": {
        "section": "trade_statistics",
        "description_ru": (
            "Средняя величина winning trade в USDT (mean(winners_quote)). Replay engine "
            "path only — research presets emit None."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "avg_loss_quote": {
        "section": "trade_statistics",
        "description_ru": (
            "Средняя величина losing trade в USDT (mean(|losers_quote|)). Replay engine "
            "path only."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "total_commissions_quote": {
        "section": "trade_statistics",
        "description_ru": (
            "Сумма всех комиссий за сделки в USDT (Bybit Spot taker 0.1% per side, "
            "ADR 0008 spec). Critical для real-world expectancy — отдельная статистика "
            "помогает оценить роль costs."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0008",
    },
    # === chart_vocabulary (3 entries) ===
    "equity_curve": {
        "section": "chart_vocabulary",
        "description_ru": (
            "График кумулятивного equity_pct (% от initial balance) во времени. Точки = "
            "exit_timestamp каждой trade. Показывает trajectory стратегии."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "drawdown_subchart": {
        "section": "chart_vocabulary",
        "description_ru": (
            "Drawdown — % просадка от peak equity. Всегда отрицательное OR 0. Sync "
            "cursor с equity chart (S46 CC2 architect binding)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "monthly_heatmap": {
        "section": "chart_vocabulary",
        "description_ru": (
            "Calendar grid PnL по месяцам. Зелёный = profit, красный = loss, intensity "
            "по magnitude. Помогает визуализировать seasonality + concentration risk."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    # === warnings (5 entries) ===
    "raw_full_period": {
        "section": "warnings",
        "description_ru": (
            "Прогон выполнен на full historical period БЕЗ walk-forward discipline. "
            "Look-ahead bias не контролируется. Не basis для live decisions — только "
            "exploratory."
        ),
        "applies_to": ["atr_breakout", "volume_breakout_iter10"],
        "adr_ref": None,
    },
    "subperiod_robustness": {
        "section": "warnings",
        "description_ru": (
            "Sub-period robustness check — стратегия разбита на N (default 5) chunks по "
            "времени. PASS если PnL положителен в большинстве chunks. Catches concentrated "
            "luck (один счастливый период покрывает все остальные)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "mc_noise": {
        "section": "warnings",
        "description_ru": (
            "Monte Carlo permutation test показал p-value > 0.05 — observed Sharpe не "
            "отличим от random walk на этом sample. Strategy edge не подтверждён "
            "статистически (ADR 0052 tightened threshold)."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0015",
    },
    "low_sample": {
        "section": "warnings",
        "description_ru": (
            "n_trades < 100 (Bailey 2014 traditional threshold) — t-test может быть "
            "ненадёжным. См. n_eff_threshold (Kish 1965) — более строгий effective-sample "
            "check."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "look_ahead_bias_warning": {
        "section": "warnings",
        "description_ru": (
            "Detected potential look-ahead bias в strategy logic OR data preparation. "
            "Strategy не валидна для live execution до устранения."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    # === symbols (5 entries — sorted в verdict_status / warnings sections) ===
    "symbol_triangle_right": {
        "section": "verdict_status",
        "description_ru": (
            "▸ — section heading marker. Выделяет начало основных блоков на странице."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_triangle_warning": {
        "section": "warnings",
        "description_ru": (
            "▲ — warning marker (low severity). Внимание к контекстному предупреждению."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_warning_sign": {
        "section": "warnings",
        "description_ru": (
            "⚠ — high-severity warning. Critical issue требующий внимания оператора."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_check": {
        "section": "verdict_status",
        "description_ru": (
            "✓ — passed indicator. Critical OR informational gate prerequisite met."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_cross": {
        "section": "verdict_status",
        "description_ru": "✗ — failed indicator. Gate prerequisite NOT met.",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    # === strategy_presets (6 entries — all STRATEGY_PRESETS keys) ===
    "preset_ema_crossover_s13": {
        "section": "strategy_presets",
        "description_ru": (
            "EMA Crossover (S13) — trend-following. Long entry на пересечении EMA(12) > "
            "EMA(26) + RSI(14) фильтр < 68 + ATR(14)-based SL/TP (1.5/3.0). Exit on opposite "
            "cross OR ATR-stop."
        ),
        "applies_to": ["ema_crossover_s13"],
        "adr_ref": None,
    },
    "preset_mean_reversion_s15": {
        "section": "strategy_presets",
        "description_ru": (
            "Mean Reversion (S15) — RSI(14) oversold/overbought (30/70) + Bollinger Bands "
            "BB(20, 2σ) extremes. Long на RSI < 30 + price < BB lower. ATR-based exits "
            "(1.5/3.0)."
        ),
        "applies_to": ["mean_reversion_s15"],
        "adr_ref": None,
    },
    "preset_mean_reversion_s17_relaxed": {
        "section": "strategy_presets",
        "description_ru": (
            "Mean Reversion S17 (relaxed thresholds) — RSI(35/65) + BB(20, 1.5σ). Более "
            "частые сигналы чем S15 за счёт менее консервативных порогов."
        ),
        "applies_to": ["mean_reversion_s17_relaxed"],
        "adr_ref": None,
    },
    "preset_donchian_breakout_s35": {
        "section": "strategy_presets",
        "description_ru": (
            "Donchian Breakout (S35) — classic Turtle Traders pattern. Long на close > "
            "20-bar high. Exit на close < 10-bar low OR ATR-trailing."
        ),
        "applies_to": ["donchian_breakout_s35"],
        "adr_ref": None,
    },
    "preset_volume_breakout_iter10": {
        "section": "strategy_presets",
        "description_ru": (
            "Volume Breakout iter10 — Donchian(9) + volume MA filter. Long на breakout с "
            "volume > MA(10) × 1.456 (LOCKED per autoresearch iter #1644 — anti-snooping "
            "preservation)."
        ),
        "applies_to": ["volume_breakout_iter10"],
        "adr_ref": None,
    },
    "preset_atr_breakout": {
        "section": "strategy_presets",
        "description_ru": (
            "ATR Breakout — volatility breakout. Long entry на close > close[-2] + ATR × "
            "mult_breakout. 10 supported combos (period × mult grid)."
        ),
        "applies_to": ["atr_breakout"],
        "adr_ref": None,
    },
}


# Hand-curated per-strategy applicability map (architect C3 BINDING).
# Explicit lists вместо auto-sync — drift OK для small set (6 presets).
STRATEGY_TO_METRICS_MAP: dict[str, list[str]] = {
    "ema_crossover_s13": [
        # Universal gate + informational
        "t5_n_trades",
        "n_eff_threshold",
        "dsr",
        "mc_p_value",
        "fold_oos_is_sharpe",
        "t1_sharpe_oos",
        "t2_sortino_oos",
        "t3_max_drawdown",
        "t4_win_rate",
        "t6_oos_is_sharpe_ratio",
        # Trade stats (replay path → quote available)
        "total_pnl_pct",
        "total_pnl_quote",
        "win_rate",
        "profit_factor",
        "avg_win_quote",
        "avg_loss_quote",
        "total_commissions_quote",
        # Charts + warnings universal
        "equity_curve",
        "drawdown_subchart",
        "monthly_heatmap",
        "subperiod_robustness",
        "mc_noise",
        "low_sample",
        # Verdicts + symbols + preset
        "verdict_pass",
        "verdict_fail",
        "verdict_wfa_fail_data",
        "symbol_triangle_right",
        "symbol_check",
        "symbol_cross",
        "preset_ema_crossover_s13",
    ],
    "mean_reversion_s15": [
        "t5_n_trades",
        "n_eff_threshold",
        "dsr",
        "mc_p_value",
        "fold_oos_is_sharpe",
        "t1_sharpe_oos",
        "t2_sortino_oos",
        "t3_max_drawdown",
        "t4_win_rate",
        "t6_oos_is_sharpe_ratio",
        "total_pnl_pct",
        "total_pnl_quote",
        "win_rate",
        "profit_factor",
        "avg_win_quote",
        "avg_loss_quote",
        "total_commissions_quote",
        "equity_curve",
        "drawdown_subchart",
        "monthly_heatmap",
        "subperiod_robustness",
        "mc_noise",
        "low_sample",
        "verdict_pass",
        "verdict_fail",
        "verdict_wfa_fail_data",
        "symbol_triangle_right",
        "symbol_check",
        "symbol_cross",
        "preset_mean_reversion_s15",
    ],
    "mean_reversion_s17_relaxed": [
        "t5_n_trades",
        "n_eff_threshold",
        "dsr",
        "mc_p_value",
        "fold_oos_is_sharpe",
        "t1_sharpe_oos",
        "t2_sortino_oos",
        "t3_max_drawdown",
        "t4_win_rate",
        "t6_oos_is_sharpe_ratio",
        "total_pnl_pct",
        "total_pnl_quote",
        "win_rate",
        "profit_factor",
        "avg_win_quote",
        "avg_loss_quote",
        "total_commissions_quote",
        "equity_curve",
        "drawdown_subchart",
        "monthly_heatmap",
        "subperiod_robustness",
        "mc_noise",
        "low_sample",
        "verdict_pass",
        "verdict_fail",
        "verdict_wfa_fail_data",
        "symbol_triangle_right",
        "symbol_check",
        "symbol_cross",
        "preset_mean_reversion_s17_relaxed",
    ],
    "donchian_breakout_s35": [
        "t5_n_trades",
        "n_eff_threshold",
        "dsr",
        "mc_p_value",
        "fold_oos_is_sharpe",
        "t1_sharpe_oos",
        "t2_sortino_oos",
        "t3_max_drawdown",
        "t4_win_rate",
        "t6_oos_is_sharpe_ratio",
        "total_pnl_pct",
        "total_pnl_quote",
        "win_rate",
        "profit_factor",
        "avg_win_quote",
        "avg_loss_quote",
        "total_commissions_quote",
        "equity_curve",
        "drawdown_subchart",
        "monthly_heatmap",
        "subperiod_robustness",
        "mc_noise",
        "low_sample",
        "verdict_pass",
        "verdict_fail",
        "verdict_wfa_fail_data",
        "symbol_triangle_right",
        "symbol_check",
        "symbol_cross",
        "preset_donchian_breakout_s35",
    ],
    "volume_breakout_iter10": [
        # Research preset → verdict_raw applicable; нет replay quote stats
        "t5_n_trades",
        "n_eff_threshold",
        "dsr",
        "mc_p_value",
        "t1_sharpe_oos",
        "t3_max_drawdown",
        "win_rate",
        "total_pnl_pct",
        "equity_curve",
        "drawdown_subchart",
        "monthly_heatmap",
        "subperiod_robustness",
        "mc_noise",
        "low_sample",
        "raw_full_period",
        "verdict_raw",
        "verdict_fail",
        "verdict_wfa_fail_data",
        "symbol_triangle_right",
        "symbol_check",
        "symbol_cross",
        "preset_volume_breakout_iter10",
    ],
    "atr_breakout": [
        "t5_n_trades",
        "n_eff_threshold",
        "dsr",
        "mc_p_value",
        "t1_sharpe_oos",
        "t3_max_drawdown",
        "win_rate",
        "total_pnl_pct",
        "equity_curve",
        "drawdown_subchart",
        "monthly_heatmap",
        "subperiod_robustness",
        "mc_noise",
        "low_sample",
        "raw_full_period",
        "verdict_raw",
        "verdict_fail",
        "verdict_wfa_fail_data",
        "symbol_triangle_right",
        "symbol_check",
        "symbol_cross",
        "preset_atr_breakout",
    ],
}


def get_glossary() -> dict[str, object]:
    """Public API — returns full glossary + strategy map для /api/glossary endpoint."""
    return {
        "entries": GLOSSARY_ENTRIES,
        "strategy_to_metrics": STRATEGY_TO_METRICS_MAP,
        "sections": SECTIONS,
    }
