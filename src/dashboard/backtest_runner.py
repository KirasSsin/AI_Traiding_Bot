"""Dashboard backtest runner — wraps _run_wfa_single_symbol с caching + result schema.

S25 ADR 0039: dashboard-internal helper. NO new measurement code — pure adapter
к existing WFA pipeline (`src/__main__._run_wfa_single_symbol`).

Caching: results stored к `data/runs/<run_id>.json` где run_id = hash of
(strategy, symbol, interval, start, end). Reuse cached если same params re-requested.
Disk-based, no DB schema change.

Concurrency: 1 backtest at-a-time per architecture verdict. Simple threading.Lock.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.analytics.dsr import compute_dsr
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.walk_forward import evaluate_acceptance_gate

# S25: strategy presets. Operator can extend.
# S38 T8 dashboard extension: explicit sprint markers в labels + S35 α Donchian added.
# Latest sprint marker `[Sxx LATEST]` помогает operator distinguish recent additions.
STRATEGY_PRESETS: dict[str, dict[str, Any]] = {
    "ema_crossover_s13": {
        "label": "Тренд EMA 12/26 + ADX фильтр",
        "optgroup": "Тренд-следование",
        "description": (
            "<p><strong>Подход:</strong> классическая трендовая стратегия на пересечении "
            "быстрой EMA(12) и медленной EMA(26) с фильтром силы тренда ADX и подтверждением "
            "не-перекупленности RSI(14).</p>"
            "<p><strong>Вход long:</strong> EMA12 пересекает EMA26 снизу вверх + ADX > 25 + "
            "RSI < 70.</p>"
            "<p><strong>Выход:</strong> обратное пересечение EMA либо ADX падает ниже 20.</p>"
            "<p><strong>Подходит для:</strong> сильно-трендовых режимов (бычий или медвежий импульс). "
            "Плохо работает в боковике — много ложных пересечений (whipsaw).</p>"
            "<p><strong>Вердикт S13:</strong> FAIL conjoint (T1=−44.46 OOS Sharpe).</p>"
        ),
        "sprint": "S13",
        "verdict": "FAIL conjoint (T1=-44.46 на BTC 1H)",
        "type": "ema_crossover",
        "indicators": {
            "ema": {"fast_period": 12, "slow_period": 26},
            "rsi": {"period": 14, "overbought": 68},
            "atr": {"period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        },
    },
    "mean_reversion_s15": {
        "label": "Возврат к среднему RSI/Bollinger (классика)",
        "optgroup": "Возврат к среднему",
        "description": (
            "<p><strong>Подход:</strong> классический mean-reversion на экстремумах RSI(14) "
            "с подтверждением через Bollinger Bands (20, 2.0σ). Логика: перепроданность ⇒ возврат вверх, "
            "перекупленность ⇒ возврат вниз.</p>"
            "<p><strong>Вход long:</strong> RSI < 30 AND цена ниже нижней BB.</p>"
            "<p><strong>Выход:</strong> RSI пересекает 50 либо цена возвращается к средней BB.</p>"
            "<p><strong>Подходит для:</strong> боковиков и низковолатильных режимов. "
            "Опасно в трендах — перепроданность может углубляться.</p>"
            "<p><strong>Вердикт S15:</strong> FAIL conjoint (MC p=0.998 — неотличимо от шума).</p>"
        ),
        "sprint": "S15",
        "verdict": "FAIL conjoint (MC p=0.998 noise)",
        "type": "mean_reversion",
        "indicators": {
            "rsi": {"period": 14, "oversold": 30, "overbought": 70},
            "bb": {"period": 20, "k": 2.0},
            "atr": {"period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        },
    },
    "mean_reversion_s17_relaxed": {
        "label": "Возврат к среднему RSI/Bollinger (мягкий)",
        "optgroup": "Возврат к среднему",
        "description": (
            "<p><strong>Подход:</strong> релакс-версия классического mean-reversion с "
            "более чувствительными порогами RSI(35/65) и узкими Bollinger Bands (20, 1.5σ). "
            "Больше сигналов чем S15.</p>"
            "<p><strong>Вход long:</strong> RSI < 35 AND цена ниже нижней BB(1.5σ).</p>"
            "<p><strong>Выход:</strong> RSI > 50 либо возврат к средней BB.</p>"
            "<p><strong>Подходит для:</strong> умеренных боковиков, ETH/SOL чаще чем BTC.</p>"
            "<p><strong>Вердикт S17:</strong> 5/6 + DSR + MC PASS, но T5 floor (n≥100) недостижим.</p>"
        ),
        "sprint": "S17",
        "verdict": "PARTIAL PASS 5/6+DSR+MC (S22 4H DSR=0.996, MC p=0.018) — T5 floor unreachable",
        "type": "mean_reversion",
        "indicators": {
            "rsi": {"period": 14, "oversold": 35, "overbought": 65},
            "bb": {"period": 20, "k": 1.5},
            "atr": {"period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        },
    },
    "donchian_breakout_s35": {
        "label": "Канал Дончиана пробой",
        "optgroup": "Прорывы",
        "description": (
            "<p><strong>Подход:</strong> long-only пробой 20-периодного канала Дончиана "
            "(максимум за N баров) с trailing-stop через ATR×2.0.</p>"
            "<p><strong>Вход long:</strong> close > max(high) за последние 20 баров.</p>"
            "<p><strong>Выход:</strong> close < min(low) за последние 10 баров либо ATR-stop.</p>"
            "<p><strong>Подходит для:</strong> начала сильных трендов. Хорошо ловит крупные движения, "
            "но проигрывает в боковиках.</p>"
            "<p><strong>Вердикт S35:</strong> FAIL conjoint (n=21 << 50, α CLOSED per ADR 0054).</p>"
        ),
        "sprint": "S35",
        "verdict": "FAIL conjoint (n=21<<50, aggregate Sharpe=-0.95) — α direction CLOSED per ADR 0054",
        "type": "donchian",
        "indicators": {
            "donchian": {"lookback_n": 20, "exit_lookback_n": 10},
            "atr": {"period": 14, "sl_atr_mult": 2.0, "tp_atr_mult": 1000000.0},
        },
    },
    "volume_breakout_iter10": {
        "label": "Прорыв с подтверждением объёма",
        "optgroup": "Прорывы",
        "description": (
            "<p><strong>Подход:</strong> Donchian-пробой с подтверждением через всплеск объёма. "
            "Сигнал валиден только если объём бара > среднего × множитель.</p>"
            "<p><strong>Вход long:</strong> close > max(high, lookback=9) AND volume > MA(volume, 10) × 1.456.</p>"
            "<p><strong>Выход:</strong> close < min(low, exit_lookback=8) либо ATR(9) × 2.97 stop.</p>"
            "<p><strong>Подходит для:</strong> BTCUSDT 4H, начала тренда с институциональным объёмом. "
            "LOCKED params (autoresearch sweep #1644). Только эта пара/TF.</p>"
            "<p><strong>Вердикт S44 (WFA retrofit):</strong> "
            "WFA_FAIL под default gates (n=38 trades в OOS < 50 floor; DSR=0.00; MC p=0.20). "
            "Pre-S44 +122.66% RAW headline не survives WFA OOS validation. "
            "См. ADR 0064.</p>"
        ),
        "sprint": "S39",
        "verdict": "PASS held-out 8mo Sharpe=+9.96 PnL=+20.42% / 3.3y +122.66%; Gate 2 forward N≥10 PENDING",
        "type": "volume_breakout",
        "locked_symbol": "BTCUSDT",
        "locked_interval": "240",
        "indicators": {
            "volume_breakout": {
                "lookback_n": 9,
                "exit_lookback_n": 8,
                "vol_window": 10,
                "vol_mult": 1.4563,
                "atr_period": 9,
                "atr_stop_mult": 2.9663,
            },
        },
    },
    # S42 T4 — Single unified atr_breakout preset (replaces S40 + S41 10 separate presets per ADR 0062)
    # Server-side params lookup от ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)].
    # Frontend introspects supported_combos via /api/strategy/atr_breakout/info → greys out invalid combos.
    "atr_breakout": {
        "label": "ATR-адаптивный пробой (multi-combo)",
        "optgroup": "Прорывы",
        "description": (
            "<p><strong>Подход:</strong> long-only пробой адаптивного ATR-канала. Уровень входа "
            "= close + ATR × множитель. Стоп тоже ATR-based, отдельный период и множитель.</p>"
            "<p><strong>Вход long:</strong> close > close[−2] + ATR(period_main) × mult_breakout.</p>"
            "<p><strong>Выход:</strong> ATR(period_stop) × mult_stop trailing-stop либо обратный сигнал.</p>"
            "<p><strong>Подходит для:</strong> 10 (symbol, timeframe) комбинаций — каждая с независимыми LOCKED "
            "параметрами от autoresearch endless. Лучший: BTCUSDT 4H +819.81% за 8.7 года, 5/5 "
            "положительных под-периодов.</p>"
            "<p><strong>Вердикт S44 (WFA retrofit):</strong> "
            "ВСЕ 10 комбинаций WFA_FAIL под default WFA gates (n≥50 floor по T5). "
            "Корень: low trade frequency в OOS windows (5-20 trades vs 50 floor). "
            "Pre-S44 RAW verdict (+819% headline) hid OOS validation failure. "
            "См. ADR 0064 для full per-combo table. BTCUSDT 1D = WFA_FAIL_DATA (1212 bars < 4520 default min).</p>"
        ),
        "sprint": "S42",
        "verdict": "RAW (acceptance gate skipped — WFA retrofit pending S43)",
        "type": "atr_breakout",
        "supported_combos": [
            ("BTCUSDT", "15"),
            ("BTCUSDT", "60"),
            ("BTCUSDT", "240"),
            ("BTCUSDT", "D"),
            ("ETHUSDT", "15"),
            ("ETHUSDT", "60"),
            ("ETHUSDT", "240"),
            ("SOLUSDT", "15"),
            ("SOLUSDT", "60"),
            ("SOLUSDT", "240"),
        ],
        # Per-combo locked params live в src/signalgen/atr_breakout_strategy.py::ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.
        # Dispatch performs server-side lookup; preset.indicators is intentionally absent.
        "indicators": {},
    },
}

# Supported intervals (per src/marketdata/bybit/rest.py registry + Bar.interval Literal).
# 30M (30) и 2H (120) skipped в dashboard MVP — Bar.interval Literal не supports их
# (pydantic ValidationError при backfill). Future enhancement: extend Bar model.
INTERVAL_LABELS: dict[str, str] = {
    "5": "5 minutes",
    "15": "15 minutes",
    "60": "1 hour",
    "240": "4 hours",
    "D": "1 day",
}

INTERVAL_FILE_LABEL: dict[str, str] = {
    "5": "5m",
    "15": "15m",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}

BARS_PER_YEAR: dict[str, int] = {
    "5": 105120,
    "15": 35040,
    "60": 8760,
    "240": 2190,
    "D": 365,
}

_lock = threading.Lock()
_RUNS_DIR = Path("data/runs")

# H1 (S49) — run_id is ALWAYS sha256[:16] (lowercase hex) generated in BacktestRequest.run_id().
# Validate user-supplied run_id against this exact shape BEFORE any path join to prevent
# path traversal (../, %2e%2e%2f) reading arbitrary .json files.
_RUN_ID_RE = re.compile(r"[a-f0-9]{16}")


def _is_valid_run_id(run_id: str) -> bool:
    """Return True iff run_id matches the sha256[:16] shape (16 lowercase hex chars)."""
    return bool(_RUN_ID_RE.fullmatch(run_id))


# S49 BATCH 5 (H8+H10) — gate-blocking criterion floors. T1/T2/T3/T4/T6 are
# informational (display-only) per trader-expert BINDING verdict — они НЕ влияют на verdict.
_N_TRADES_FLOOR = 50
_N_EFF_FLOOR = 50


def _compute_verdict(
    n_trades: int,
    dsr_pass: bool,
    mc_pass: bool,
    failed_folds: list[int],
    n_eff: int,
) -> tuple[list[str], str]:
    """Compute (failed_criteria, verdict) from gate-blocking criteria ONLY.

    trader-expert BINDING verdict (S49): verdict определяется ИСКЛЮЧИТЕЛЬНО
    gate-blocking критериями:
      - T5 n_trades floor (>= 50)        → "t5_floor"
      - per-fold OOS/IS Sharpe (>= 0.7)  → "sharpe_gate" (failed_folds non-empty)
      - MC permutation (p <= 0.05)       → "mc_gate" (mc_pass False)
      - DSR (>= 0.95)                    → "dsr_threshold" (dsr_pass False)
      - n_eff (>= 50)                    → "n_eff_threshold"

    T1/T2/T3/T4/T6 — informational (отображаются в UI, НЕ блокируют verdict).
    Criterion keys match FailAnalysisTab ALL_CRITERIA gate-blocking entries.
    """
    failed_criteria: list[str] = []
    if n_trades < _N_TRADES_FLOOR:
        failed_criteria.append("t5_floor")
    if failed_folds:
        failed_criteria.append("sharpe_gate")
    if not mc_pass:
        failed_criteria.append("mc_gate")
    if not dsr_pass:
        failed_criteria.append("dsr_threshold")
    if n_eff < _N_EFF_FLOOR:
        failed_criteria.append("n_eff_threshold")
    verdict = "PASS" if not failed_criteria else "FAIL"
    return failed_criteria, verdict


def _compound_balance(initial_balance: float, pnl_pcts: list[float]) -> float:
    """Geometric compounding: initial × Π(1 + pnl_pct_i).

    M1 (S49): per-trade fractional pnl_pct (e.g. 0.10 = +10%) compounds
    multiplicatively, NOT additively. 3×(+10%) → ×1.331, not ×1.30.
    """
    equity = initial_balance
    for pnl_pct in pnl_pcts:
        equity *= 1.0 + pnl_pct
    return equity


def _compound_equity_pct(pnl_pcts: list[float]) -> list[float]:
    """Cumulative compounded return series (percent from initial capital).

    M1 (S49): equity_pct[i] = (Π_{j<=i}(1 + pnl_pct_j) - 1) × 100.
    Replaces additive running sum which understated cumulative return.
    """
    series: list[float] = []
    cumulative = 1.0
    for pnl_pct in pnl_pcts:
        cumulative *= 1.0 + pnl_pct
        series.append((cumulative - 1.0) * 100.0)
    return series


def _autoscale_wfa_params(total_bars: int) -> dict[str, int]:
    """S38 dashboard extension: auto-scale WFA params для small data ranges.

    ADR 0014 default: train=2000 / test=500 / k_folds=5 / embargo=20 = 4520 bars min.
    Operator may select short date range (e.g. 1Q on 1D = ~90 bars) where defaults fail.

    Auto-scale rule (preserves WFA shape):
      - total >= 4520: use ADR 0014 defaults (best statistical validity)
      - 1000-4520: scale linearly (train ~ 40%, test ~ 10%, k_folds=5)
      - 300-1000: k_folds=3, train ~ 50%, test ~ 10%
      - 100-300: k_folds=2, train ~ 60%, test ~ 15%, embargo=5
      - <100: BLOCKED (insufficient even для smallest WFA)

    Trade-off: smaller train = less indicator warm-up margin, smaller test = noisier OOS metrics.
    UI displays actual WFA params used so operator sees scale impact.

    Returns dict с keys: train_bars / test_bars / k_folds / embargo_bars.
    """
    if total_bars >= 4520:
        return {"train_bars": 2000, "test_bars": 500, "k_folds": 5, "embargo_bars": 20}
    if total_bars >= 1000:
        # Scale: target = (train + embargo + k×test) <= total
        # Solve для k=5: train ≈ 0.4*total, test ≈ 0.1*total
        train = int(total_bars * 0.40)
        test = int(total_bars * 0.10)
        return {
            "train_bars": max(200, train),
            "test_bars": max(50, test),
            "k_folds": 5,
            "embargo_bars": 20,
        }
    if total_bars >= 300:
        # k_folds=3 для smaller window
        train = int(total_bars * 0.50)
        test = int(total_bars * 0.10)
        return {
            "train_bars": max(100, train),
            "test_bars": max(30, test),
            "k_folds": 3,
            "embargo_bars": 10,
        }
    if total_bars >= 100:
        # k_folds=2 minimum
        train = int(total_bars * 0.60)
        test = int(total_bars * 0.15)
        return {
            "train_bars": max(50, train),
            "test_bars": max(15, test),
            "k_folds": 2,
            "embargo_bars": 5,
        }
    # < 100 bars — too small even с k_folds=2
    raise ValueError(
        f"Insufficient data: {total_bars} bars. Minimum 100 bars required для WFA "
        f"(extend date range OR pick finer interval — 5M/15M produce more bars per same period)."
    )


# S26: educational docs для UI Documentation tab.
# Indicator descriptions (technical analysis primer для operators).
INDICATORS_DOC: list[dict[str, Any]] = [
    {
        "id": "rsi",
        "name": "RSI",
        "full_name": "Relative Strength Index",
        "author": "J. Welles Wilder Jr. (1978)",
        "category": "Momentum oscillator",
        "formula": "RSI = 100 − [100 / (1 + RS)] где RS = avg_gain / avg_loss за period",
        "range": "0 — 100",
        "description": (
            "Oscillator момента, измеряющий силу и направление недавних price changes. "
            "В нашем боте используется Wilder smoothing (α=1/n), не classical EMA. "
            "Стандартный period = 14 баров."
        ),
        "interpretation": [
            "RSI < 30 — oversold (потенциальный buy signal mean-reversion)",
            "RSI > 70 — overbought (потенциальный sell/exit signal)",
            "RSI 30–70 — neutral zone",
            "Threshold relaxation (35/65) даёт больше signals но noisier",
        ],
        "params_in_strategies": {
            "period": "14 (Wilder default)",
            "oversold": "30 (S15) или 35 (S17 relaxed)",
            "overbought": "65 (S17) или 68 (EMA crossover) или 70 (S15)",
        },
        "source": "Wilder, J.W. (1978) New Concepts in Technical Trading Systems",
    },
    {
        "id": "bb",
        "name": "BB",
        "full_name": "Bollinger Bands",
        "author": "John Bollinger (1980s)",
        "category": "Volatility envelope",
        "formula": "middle = SMA(close, period); upper = middle + k×stdev_pop; lower = middle − k×stdev_pop",
        "range": "Зависит от price",
        "description": (
            "Volatility-based envelope вокруг moving average. Population standard deviation "
            "(ddof=0 per Bollinger original spec). Прорыв нижней band = сигнал mean-reversion entry, "
            "прорыв верхней = exit или overbought condition."
        ),
        "interpretation": [
            "close < lower_BB — price extended below average (oversold extreme)",
            "close > upper_BB — price extended above average (overbought extreme)",
            "Band width = volatility proxy (squeeze = low vol, expansion = high vol)",
            "k=2.0 (S15) — strict bands, fewer breaches",
            "k=1.5 (S17 relaxed) — narrower bands, more breaches (~1.47× rate vs 2.0σ)",
        ],
        "params_in_strategies": {
            "period": "20 bars (Bollinger default)",
            "k (stdev multiplier)": "2.0 (S15) или 1.5 (S17 relaxed)",
        },
        "source": "Bollinger, J. (2001) Bollinger on Bollinger Bands",
    },
    {
        "id": "ema",
        "name": "EMA",
        "full_name": "Exponential Moving Average",
        "author": "Classical (1960s)",
        "category": "Trend / smoothing",
        "formula": "EMA[t] = α × close[t] + (1−α) × EMA[t−1]; classical α=2/(n+1)",
        "range": "Зависит от price",
        "description": (
            "Weighted moving average даёт больший вес recent prices. Classical version "
            "(α=2/(n+1)) используется для crossover signals; Wilder version (α=1/n) — "
            "для smoothing других indicators (RSI, ATR per ADR 0011)."
        ),
        "interpretation": [
            "EMA(fast) crosses ABOVE EMA(slow) — bullish trend signal",
            "EMA(fast) crosses BELOW EMA(slow) — bearish trend signal",
            "Faster EMA = more responsive, more whipsaws",
            "Slower EMA = lag, but cleaner signals",
        ],
        "params_in_strategies": {
            "fast_period": "12 (S13)",
            "slow_period": "26 (S13)",
        },
        "source": "Classical TA literature; Wilder variant ADR 0011",
    },
    {
        "id": "atr",
        "name": "ATR",
        "full_name": "Average True Range",
        "author": "J. Welles Wilder Jr. (1978)",
        "category": "Volatility",
        "formula": "TR = max(high−low, |high−prev_close|, |low−prev_close|); ATR = Wilder-smooth(TR, period)",
        "range": "≥ 0",
        "description": (
            "Measure of volatility учитывающий gaps между bars. NOT directional. "
            "Используется для position sizing (risk-adjusted) + stop-loss placement (SL = entry − k × ATR)."
        ),
        "interpretation": [
            "Higher ATR = more volatile market (wider stops needed)",
            "Lower ATR = quieter market (tighter stops viable)",
            "SL multiplier (sl_atr_mult) defines risk distance: 1.5 = mid-tight",
            "TP multiplier (tp_atr_mult) defines reward target: 3.0 = 2:1 RR vs SL",
        ],
        "params_in_strategies": {
            "period": "14 (Wilder default)",
            "sl_atr_mult": "1.5 (stop-loss = entry − 1.5 × ATR)",
            "tp_atr_mult": "3.0 (take-profit = entry + 3.0 × ATR)",
        },
        "source": "Wilder, J.W. (1978) New Concepts in Technical Trading Systems",
    },
    {
        "id": "adx",
        "name": "ADX",
        "full_name": "Average Directional Index",
        "author": "J. Welles Wilder Jr. (1978)",
        "category": "Trend strength (NOT directional)",
        "formula": "ADX = Wilder-smooth(DX, period); DX = 100 × |+DI − −DI| / (+DI + −DI)",
        "range": "0 — 100",
        "description": (
            "Measures trend STRENGTH без направления. Используется как filter: "
            "trade only когда trend сильный. +DI и −DI определяют direction."
        ),
        "interpretation": [
            "ADX < 20 — weak/no trend (avoid trend-following)",
            "ADX 20–25 — emerging trend",
            "ADX > 25 — strong trend (S13 EMA crossover threshold)",
            "+DI > −DI — bullish direction",
            "−DI > +DI — bearish direction",
        ],
        "params_in_strategies": {
            "period": "14 (Wilder default)",
            "threshold": "25 (S13 — only enter в strong trend)",
        },
        "source": "Wilder, J.W. (1978) New Concepts in Technical Trading Systems",
    },
]

# Multipliers / params explanation
MULTIPLIERS_DOC: list[dict[str, Any]] = [
    {
        "id": "sl_atr_mult",
        "name": "SL multiplier (Stop Loss)",
        "default": 1.5,
        "description": (
            "Position closed automatically когда price moves AGAINST entry на k × ATR(14) units. "
            "Lower multiplier (1.0–1.5) = tight stops, frequent exits, smaller per-trade losses. "
            "Higher (2.0–3.0) = wide stops, fewer stops out, larger losses but trend-friendly."
        ),
        "tradeoff": "Tight = many small losses. Wide = few large losses.",
    },
    {
        "id": "tp_atr_mult",
        "name": "TP multiplier (Take Profit)",
        "default": 3.0,
        "description": (
            "Position closed automatically когда price moves IN FAVOR на k × ATR(14) units. "
            "Combined с SL multiplier defines RR (Risk-Reward ratio): "
            "TP=3.0 + SL=1.5 = RR 2:1. Higher TP = wait for bigger moves but lower hit rate."
        ),
        "tradeoff": "High RR (3+) = низкий win rate но bigger wins. Low RR (<1.5) = high win rate необходим.",
    },
    {
        "id": "position_size_pct",
        "name": "Position size %",
        "default": 10.0,
        "description": (
            "Каждая сделка использует X% доступного balance. 10% = умеренный risk per trade. "
            "Combined с Kelly phase ceiling (1%/2%/3%/5%) даёт final position size."
        ),
        "tradeoff": "Higher = больше profit per win, faster drawdown при losses",
    },
    {
        "id": "commission_taker",
        "name": "Commission rate (taker)",
        "default": 0.001,
        "description": (
            "Bybit Spot taker fee = 0.1% (0.001). Применяется к каждому fill (entry + exit). "
            "Учитывается при backtest для realistic PnL. На демо аккаунте = same fee schedule."
        ),
        "tradeoff": "Не настраивается оператором — exchange-defined",
    },
    {
        "id": "slippage",
        "name": "Slippage allowance",
        "default": 0.0005,
        "description": (
            "Predicted price impact when executing market orders. 0.05% = optimistic для BTC/ETH/SOL. "
            "Real Mainnet slippage может быть higher при low liquidity OR high volatility moments."
        ),
        "tradeoff": "Higher slippage assumption = более консервативная backtest results",
    },
    {
        "id": "max_drawdown_pct",
        "name": "Max drawdown halt",
        "default": 50.0,
        "description": (
            "Backtest aborted если cumulative drawdown exceeds X%. Live bot имеет 3-tier circuit breakers "
            "(L1 5% / L2 10% / L3 15% per ADR 0024) которые triggers HALT cascade на FSM."
        ),
        "tradeoff": "Backtest cap = sanity check; live halts = capital protection",
    },
]

# Strategy descriptions (long-form, для UI Documentation tab).
STRATEGIES_DOC: list[dict[str, Any]] = [
    {
        "id": "ema_crossover_s13",
        "name": "EMA crossover (S13 baseline)",
        "category": "Trend-following",
        "tagline": "Classic 12/26 crossover с ADX filter и RSI guard.",
        "entry_logic": (
            "LONG entry когда EMA(12) crosses ABOVE EMA(26) AND ADX(14) > 25 (strong trend) "
            "AND +DI > −DI (bullish direction) AND RSI(14) < 68 (not overbought)."
        ),
        "exit_logic": (
            "EXIT когда EMA(12) crosses BELOW EMA(26) AND −DI > +DI (signal flip). "
            "OR ATR-based stop hit (SL = entry − 1.5 × ATR; TP = entry + 3.0 × ATR)."
        ),
        "indicators_used": ["EMA 12/26", "ADX(14)", "+DI/−DI", "RSI(14)", "ATR(14)"],
        "key_params": {
            "ema_fast": 12,
            "ema_slow": 26,
            "adx_threshold": 25,
            "rsi_overbought": 68,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 3.0,
        },
        "historical_results": (
            "S13 BTCUSDT 1H 4.81y: 20 OOS trades, T1=-44.46, FAIL T1+T2+T4+T5. "
            "Frequency structural limit ~1 trade per 5-10 days = T5 floor 100 unreachable."
        ),
        "best_for": "Strong directional markets с low noise. NOT recommended для choppy / ranging conditions.",
        "academic_reference": "Lo & MacKinlay (1990); Hudson & Urquhart (2021)",
    },
    {
        "id": "mean_reversion_s15",
        "name": "Mean-reversion S15 original (RSI 30/70 + BB 2.0σ)",
        "category": "Mean-reversion",
        "tagline": "Strict mean-reversion — buy oversold extremes, exit overbought OR upper BB.",
        "entry_logic": (
            "LONG entry когда RSI(14) < 30 (extremely oversold) AND close < lower_BB(20, 2.0σ) "
            "(price extended below volatility envelope). AND-gated trigger — оба условия required."
        ),
        "exit_logic": (
            "EXIT когда RSI(14) > 70 (overbought) OR close > upper_BB(20, 2.0σ) (extended above envelope) "
            "OR ATR-based stop hit. FLAT-only strategy — no inverse positions."
        ),
        "indicators_used": ["RSI(14)", "BB(20, 2.0σ)", "ATR(14)"],
        "key_params": {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "bb_period": 20,
            "bb_k": 2.0,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 3.0,
        },
        "historical_results": (
            "S15 multi-symbol (BTC+ETH+SOL) 1H: 108 OOS trades aggregate (T5 PASSED), но T6 -12.38, "
            "MC p=0.998 random-equivalent. FAIL T6+MC+DSR. Strict thresholds = редкие но noisy signals."
        ),
        "best_for": "Sideways / mean-reverting markets с extreme overshoots. AVOID strong trends (will get crushed на trend continuation).",
        "academic_reference": "Lo & MacKinlay (1990); De Bondt & Thaler (1985); Bollinger (2001)",
    },
    {
        "id": "mean_reversion_s17_relaxed",
        "name": "Mean-reversion S17 relaxed (RSI 35/65 + BB 1.5σ)",
        "category": "Mean-reversion (relaxed thresholds)",
        "tagline": "Relaxed mean-reversion — больше signals чем S15, регистрировал stat-sig signal.",
        "entry_logic": (
            "LONG entry когда RSI(14) < 35 AND close < lower_BB(20, 1.5σ). Relaxed thresholds vs S15 "
            "дают ~1.34× signal frequency на BTC."
        ),
        "exit_logic": "EXIT когда RSI(14) > 65 OR close > upper_BB(20, 1.5σ) OR ATR-based stop hit.",
        "indicators_used": ["RSI(14)", "BB(20, 1.5σ)", "ATR(14)"],
        "key_params": {
            "rsi_period": 14,
            "rsi_oversold": 35,
            "rsi_overbought": 65,
            "bb_period": 20,
            "bb_k": 1.5,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 3.0,
        },
        "historical_results": (
            "S17 BTC 1H: 59 trades, T1=25.99 (small-sample artifact warning), DSR=1.0, "
            "MC p=0.01 STAT-SIGNIFICANT, 5/6 + DSR + MC PASS. ТОЛЬКО T5 count fail (sample <100). "
            "S22 BTC 4H: 62 trades, similar pattern (DSR 0.996, MC p=0.018) — strategy edge "
            "REGIME-INDEPENDENT (works на 1H AND 4H equally). T5 100 структурно недостижим на BTC-only."
        ),
        "best_for": (
            "Best observed strategy в проекте по DSR/MC (но T5 sample limit blocks MVP DONE). "
            "Подходит для exploring whether ML filter мог бы capture regime-specific signal "
            "(combined ~120 trades S17+S22 = small-sample ML viable per architecture)."
        ),
        "academic_reference": "Bailey & López de Prado (2014) — DSR; López de Prado AFML Ch.7 — purged CV",
    },
]

# WFA + statistical methodology docs
METHODOLOGY_DOC: list[dict[str, Any]] = [
    {
        "id": "wfa",
        "name": "Walk-Forward Analysis (WFA)",
        "purpose": "Robust backtest evaluation preventing overfit к single training window",
        "params": "K=5 folds, train=2000 bars, test=500 bars, embargo=20 bars (per ADR 0014)",
        "description": (
            "Data разбит на K=5 sequential train+test windows. На каждом fold strategy runs "
            "с train-window params на out-of-sample test window. Embargo gap prevents lookahead "
            "bias из train к test. Aggregated trades across все folds дают OOS metrics."
        ),
        "source": "Pardo (1992) Design, Testing, and Optimization of Trading Systems",
    },
    {
        "id": "dsr",
        "name": "Deflated Sharpe Ratio (DSR)",
        "purpose": "Multi-testing penalty — учитывает inflated Sharpe из repeated backtests",
        "formula": "DSR = Φ((SR − E[max SR_n]) × √(n−1) / √(1 − γ_3·SR + (γ_4−1)/4·SR²))",
        "description": (
            "Bailey & López de Prado (2014) eq. 13. Adjusts Sharpe Ratio for selection bias. "
            "Higher N_trials (testing more strategies) → harsher penalty. DSR > 0 = signal "
            "credible after multi-testing correction."
        ),
        "source": "Bailey, D.H. & López de Prado, M. (2014) The Deflated Sharpe Ratio, JPM 40(5)",
    },
    {
        "id": "mc",
        "name": "MC Permutation Test (sign-flip)",
        "purpose": "Statistical significance test — distinguishes signal от random noise",
        "description": (
            "Sign-flip permutation: randomly multiply trade returns by ±1, recompute Sharpe, "
            "repeat 2000× с seed=42. P-value = fraction of permutations с Sharpe ≥ observed. "
            "p < 0.05 = strategy returns significantly better than random."
        ),
        "interpretation": [
            "p < 0.05 — statistically significant edge",
            "p ≥ 0.05 — cannot reject random-equivalent hypothesis",
            "p > 0.10 — strong evidence strategy is noise (warning trigger)",
        ],
        "source": "Halls-Moore (2015) Successful Algorithmic Trading; Bailey 2014",
    },
    {
        "id": "acceptance_criteria",
        "name": "Acceptance Criteria T1-T6",
        "purpose": "Pre-registered gating thresholds — strategy must pass ALL conjointly для MVP DONE",
        "criteria": [
            {
                "id": "T1",
                "metric": "Sharpe OOS (annualized)",
                "threshold": "≥ 1.0",
                "note": "> 3.0 = почти наверняка overfit",
            },
            {
                "id": "T2",
                "metric": "Sortino OOS",
                "threshold": "≥ 1.5",
                "note": "Trend-following с positive skew должен иметь Sortino > Sharpe",
            },
            {
                "id": "T3",
                "metric": "Max Drawdown",
                "threshold": "< 25%",
                "note": "< 10% suspicious; trend-following BTC historically 15–30%",
            },
            {
                "id": "T4",
                "metric": "Win rate × RR",
                "threshold": "≥45%@RR≥1.5 OR ≥35%@RR≥2.0",
                "note": "Trend-following 35–50%; > 65% suspicious",
            },
            {
                "id": "T5",
                "metric": "Mean expectancy + t-stat",
                "threshold": "> 0 + t-stat > 2.0 + n ≥ 100",
                "note": "n ≥ 100 = sample-size minimum для t-test validity (Bailey 2014)",
            },
            {
                "id": "T6",
                "metric": "OOS/IS Sharpe ratio",
                "threshold": "≥ 0.7",
                "note": "Primary overfit detector — degradation > 30% red flag",
            },
        ],
        "source": "wiki/project/architecture/acceptance-criteria.md (immutable per ADR pattern)",
    },
]


def get_documentation() -> dict[str, Any]:
    """Return structured documentation для UI Documentation tab."""
    return {
        "indicators": INDICATORS_DOC,
        "multipliers": MULTIPLIERS_DOC,
        "strategies": STRATEGIES_DOC,
        "methodology": METHODOLOGY_DOC,
    }


@dataclass(frozen=True)
class BacktestRequest:
    strategy_id: str
    symbol: str
    interval: str
    start: str  # YYYY-MM-DD
    end: str

    def run_id(self) -> str:
        s = f"{self.strategy_id}|{self.symbol}|{self.interval}|{self.start}|{self.end}"
        return hashlib.sha256(s.encode()).hexdigest()[:16]


def list_data_availability() -> dict[str, dict[str, Any]]:
    """Scan data/ directory для available parquet files. Returns per-symbol coverage."""
    import pandas as pd

    out: dict[str, dict[str, Any]] = {}
    data_dir = Path("data")
    for parquet in sorted(data_dir.glob("*USDT_*.parquet")):
        name = parquet.stem  # e.g. BTCUSDT_1h
        if name.endswith(".s2-backup"):
            continue
        try:
            symbol, label = name.rsplit("_", 1)
        except ValueError:
            continue
        # Map label → interval
        label_to_interval = {v: k for k, v in INTERVAL_FILE_LABEL.items()}
        interval = label_to_interval.get(label)
        if interval is None:
            continue
        try:
            df = pd.read_parquet(parquet)
            if "time" not in df.columns:
                continue
            ts = pd.to_datetime(df["time"])
            sym_dict = out.setdefault(symbol, {})
            sym_dict[interval] = {
                "interval": interval,
                "label": INTERVAL_LABELS.get(interval, interval),
                "bars": len(df),
                "start": str(ts.iloc[0]),
                "end": str(ts.iloc[-1]),
                "file": str(parquet),
            }
        except Exception:  # noqa: BLE001
            continue
    return out


def run_backtest(
    req: BacktestRequest, *, force: bool = False, initial_balance: float = 10000.0
) -> dict[str, Any]:
    """Run WFA на given request. Cached to disk by run_id.

    Args:
        req: BacktestRequest specification
        force: bypass cache, re-run

    Returns:
        Dict с full WFA result + warnings + metadata.

    Raises:
        ValueError: invalid strategy/interval
        FileNotFoundError: missing parquet for (symbol, interval)
    """
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = req.run_id()
    cache_path = _RUNS_DIR / f"{run_id}.json"
    if not force and cache_path.exists():
        result: dict[str, Any] = json.loads(cache_path.read_text())
        result["cached"] = True
        return result

    if req.strategy_id not in STRATEGY_PRESETS:
        raise ValueError(
            f"Unknown strategy '{req.strategy_id}'. "
            f"Supported: {sorted(STRATEGY_PRESETS.keys())}"
        )
    if req.interval not in BARS_PER_YEAR:
        raise ValueError(
            f"Unknown interval '{req.interval}'. " f"Supported: {sorted(BARS_PER_YEAR.keys())}"
        )
    preset = STRATEGY_PRESETS[req.strategy_id]

    # S42 T4 — volume_breakout dispatch: envelope merge from runner (per T3).
    if preset.get("type") == "volume_breakout":
        from datetime import date as _date

        from src.backtest.research_runner_envelope import build_research_runner_envelope
        from src.backtest.volume_breakout_runner import (
            _run_volume_breakout_wfa,
            run_volume_breakout_backtest,
        )

        # S44 T5 — try WFA first; fall back to RAW envelope on data limit OR ValueError
        wfa_result: dict[str, Any] | None = None
        try:
            wfa_result = _run_volume_breakout_wfa(
                symbol=req.symbol,
                interval=req.interval,
                start_date=_date.fromisoformat(req.start),
                end_date=_date.fromisoformat(req.end),
            )
        except (ValueError, FileNotFoundError):
            wfa_result = None

        # Always also run full-period replay for equity_curve + headline metrics
        vb_raw = run_volume_breakout_backtest(
            symbol=req.symbol,
            interval=req.interval,
            start_date=_date.fromisoformat(req.start),
            end_date=_date.fromisoformat(req.end),
        )

        # Build envelope with wfa_result merged
        vb_envelope = build_research_runner_envelope(
            runner_name="volume_breakout_runner",
            symbol=req.symbol,
            interval=req.interval,
            n_trades=int(vb_raw.get("n_trades", 0)),
            sharpe=float(vb_raw.get("sharpe", 0.0)),
            win_rate=float(vb_raw.get("win_rate", 0.0)),
            total_pnl_pct=float(vb_raw.get("total_pnl_pct", 0.0)),
            bars_per_year=int(vb_raw.get("bars_per_year", 2191)),
            equity_curve=vb_raw.get("equity_curve", {}).get("equity_pct", []),
            equity_timestamps=vb_raw.get("equity_curve", {}).get("timestamps", []),
            runner_label=f"Volume breakout {req.interval} {req.symbol} (LOCKED — S39)",
            start=req.start,
            end=req.end,
            wfa_result=wfa_result,
        )

        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = _RUNS_DIR / f"{run_id}.json"

        result_vb: dict[str, Any] = dict(vb_envelope)
        result_vb["run_id"] = run_id
        result_vb["cached"] = False
        result_vb["request"] = {
            "strategy_id": req.strategy_id,
            "strategy_label": preset["label"],
            "strategy_config": preset,
            "symbol": req.symbol,
            "interval": req.interval,
            "interval_label": INTERVAL_LABELS.get(req.interval, req.interval),
            "start": req.start,
            "end": req.end,
        }
        cache_path.write_text(json.dumps(result_vb, default=str, indent=2))
        return result_vb

    # S42 T4 — atr_breakout dispatch: envelope merge from runner.
    # S44 T5 — WFA retrofit: try WFA first; fall back to RAW envelope on data limit OR ValueError.
    # Per-combo params resolved server-side от ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)].
    if preset.get("type") == "atr_breakout":
        from datetime import date as _date

        from src.backtest.atr_breakout_runner import (
            _run_atr_breakout_wfa,
            run_atr_breakout_backtest,
        )
        from src.backtest.research_runner_envelope import build_research_runner_envelope

        # S44 T5 — try WFA first; fall back to RAW envelope on data limit OR ValueError
        wfa_result_ab: dict[str, Any] | None = None
        try:
            wfa_result_ab = _run_atr_breakout_wfa(
                symbol=req.symbol,
                interval=req.interval,
                start_date=_date.fromisoformat(req.start),
                end_date=_date.fromisoformat(req.end),
            )
        except (ValueError, FileNotFoundError):
            wfa_result_ab = None

        # Always also run full-period replay for equity_curve + headline metrics.
        # Pass params=None — runner falls back к ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)].
        # If combo not in locked dict, runner raises ValueError (caught by run_backtest caller).
        ab_raw = run_atr_breakout_backtest(
            symbol=req.symbol,
            interval=req.interval,
            start_date=_date.fromisoformat(req.start),
            end_date=_date.fromisoformat(req.end),
            params=None,
        )

        # Build envelope with wfa_result merged
        ab_envelope = build_research_runner_envelope(
            runner_name="atr_breakout_runner",
            symbol=req.symbol,
            interval=req.interval,
            n_trades=int(ab_raw.get("n_trades", 0)),
            sharpe=float(ab_raw.get("sharpe", 0.0)),
            win_rate=float(ab_raw.get("win_rate", 0.0)),
            total_pnl_pct=float(ab_raw.get("total_pnl_pct", 0.0)),
            bars_per_year=int(ab_raw.get("bars_per_year", 2191)),
            equity_curve=ab_raw.get("equity_curve", {}).get("equity_pct", []),
            equity_timestamps=ab_raw.get("equity_curve", {}).get("timestamps", []),
            runner_label=f"ATR breakout {req.interval} {req.symbol} (LOCKED)",
            start=req.start,
            end=req.end,
            wfa_result=wfa_result_ab,
        )

        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = _RUNS_DIR / f"{run_id}.json"

        # Merge envelope (base) + dashboard overlays (run_id, cached, dashboard-preferred request).
        result_ab: dict[str, Any] = dict(ab_envelope)
        result_ab["run_id"] = run_id
        result_ab["cached"] = False
        result_ab["request"] = {
            "strategy_id": req.strategy_id,
            "strategy_label": preset["label"],
            "strategy_config": preset,
            "symbol": req.symbol,
            "interval": req.interval,
            "interval_label": INTERVAL_LABELS.get(req.interval, req.interval),
            "start": req.start,
            "end": req.end,
        }
        cache_path.write_text(json.dumps(result_ab, default=str, indent=2))
        return result_ab

    with _lock:
        # Lazy import к keep dashboard module loadable без main module side effects
        from src.__main__ import _load_ohlcv, _run_wfa_single_symbol

        df = _load_ohlcv(symbol=req.symbol, start=req.start, end=req.end, interval=req.interval)
        if df.empty:
            raise FileNotFoundError(
                f"No OHLCV data для {req.symbol} {req.interval} в {req.start}..{req.end}"
            )

        # S38 dashboard extension: auto-scale WFA params для small data ranges
        # (operator может select short period где ADR 0014 defaults 4520 bars fail).
        wfa_params = _autoscale_wfa_params(len(df))

        # S25: build full WFA config from preset
        # S27 T1: bars_per_year passed к replay_engine для timeframe-correct annualization
        strategy_config: dict[str, object] = {
            "trading": {
                "initial_balance": initial_balance,
                "commission_taker": 0.001,
                "slippage": 0.0005,
                "position_size_pct": 10.0,
                "max_drawdown_pct": 50.0,
                "long_only": True,
            },
            "strategy": {
                "type": preset["type"],
                "indicators": preset["indicators"],
            },
            "bars_per_year": BARS_PER_YEAR[req.interval],
        }
        from typing import cast

        from src.risk.trade_history import TradeRecord

        _sym_trades_raw, sym_fold_sharpes, sym_runner_result, sym_mc_p = _run_wfa_single_symbol(
            symbol=req.symbol,
            df=df,
            strategy_config=strategy_config,
            train_bars=wfa_params["train_bars"],
            test_bars=wfa_params["test_bars"],
            k_folds=wfa_params["k_folds"],
            embargo_bars=wfa_params["embargo_bars"],
        )
        sym_trades: list[TradeRecord] = cast(list[TradeRecord], _sym_trades_raw)

    bars_per_year = BARS_PER_YEAR[req.interval]
    metrics = compute_t1_t6_metrics(
        trades=list(sym_trades),
        fold_oos_is_sharpe=sym_fold_sharpes,
        bars_per_year=bars_per_year,
    )
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=sym_fold_sharpes,
        mc_p_value=sym_mc_p,
    )
    dsr_value = compute_dsr(trades=list(sym_trades), n_trials=1) if sym_trades else float("nan")

    def nan_safe(v: Any) -> Any:
        return None if (isinstance(v, float) and math.isnan(v)) else v

    # Apply CC4 hard requirement (Sortino anomaly guard, trader spec)
    sortino_raw = nan_safe(metrics["t2_sortino_oos"])
    n_trades = metrics["t5_n_trades"]
    sortino_display: Any
    sortino_warning: bool
    if isinstance(sortino_raw, int | float) and abs(sortino_raw) > 50 and n_trades < 100:
        sortino_display = None
        sortino_warning = True
    else:
        sortino_display = sortino_raw
        sortino_warning = False

    # Compute Tier 2 trade-level stats from sym_trades
    n_winners = sum(1 for t in sym_trades if float(t.pnl_quote) > 0)
    n_losers = sum(1 for t in sym_trades if float(t.pnl_quote) < 0)
    total_commissions = sum(float(t.fees_paid) for t in sym_trades)
    avg_win_quote = (
        sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) > 0) / n_winners
        if n_winners > 0
        else 0.0
    )
    avg_loss_quote = (
        sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) < 0) / n_losers
        if n_losers > 0
        else 0.0
    )
    gross_profit = sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) > 0)
    gross_loss = abs(sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    total_pnl = sum(float(t.pnl_quote) for t in sym_trades)

    # S27: per-trade dump для formula audit (trader-expert optimization)
    trades_dump: list[dict[str, Any]] = []
    for t in sym_trades:
        trades_dump.append(
            {
                "symbol": t.symbol,
                "entry_ts": str(t.entry_ts),
                "exit_ts": str(t.exit_ts),
                "qty": float(t.qty),
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price),
                "pnl_quote": float(t.pnl_quote),
                "pnl_pct": float(t.pnl_pct),
                "fees_paid": float(t.fees_paid),
                "reason_code": str(t.reason_code),
                "kelly_phase": int(t.kelly_phase),
            }
        )
    # S48 T2 (Bug B fix) — emit equity_curve parallel arrays для frontend chart support.
    # Cumulative equity_pct relative to initial capital (consistent with research_runner_envelope).
    # TradeRecord.pnl_pct is fractional (e.g. 0.012 = +1.2%); multiply ×100 for display.
    # TradeRecord.exit_ts is AwareDatetime — convert to unix seconds for frontend timestamps.
    # M1 (S49): compound geometrically — additive sum understated cumulative return.
    _eq_timestamps = [int(_t.exit_ts.timestamp()) for _t in sym_trades]
    _pnl_pcts = [float(_t.pnl_pct) for _t in sym_trades]
    _eq_pct = _compound_equity_pct(_pnl_pcts)

    # Informational metric values (T1/T2/T3/T4/T6) — displayed in UI, NOT gate-blocking.
    # Per trader-expert BINDING verdict (S49 H8+H10): verdict определяется ИСКЛЮЧИТЕЛЬНО
    # gate-blocking критериями (T5 floor / sharpe_gate / mc_gate / dsr / n_eff) — см. _compute_verdict.
    t1 = nan_safe(metrics["t1_sharpe_oos"])
    t3 = nan_safe(metrics["t3_max_drawdown"])
    t4_win = nan_safe(metrics["t4_win_rate"])
    t4_rr = nan_safe(metrics["t4_avg_rr"])
    t5_t = nan_safe(metrics["t5_t_stat"])
    t5_mean = nan_safe(metrics["t5_mean_pnl_pct"])
    t6 = nan_safe(metrics["t6_oos_is_sharpe_ratio_mean"])

    # Verdict — gate-blocking criteria ONLY (DSR uses existing dashboard semantic dsr_value > 0).
    dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0
    mc_pass = bool(gate.get("mc_gate_passed", False))
    n_eff = gate.get("n_trades_n_eff")
    n_eff_value = n_trades if n_eff is None else int(n_eff)
    failed_criteria, verdict = _compute_verdict(
        n_trades=n_trades,
        dsr_pass=dsr_pass,
        mc_pass=mc_pass,
        failed_folds=list(gate.get("failed_folds", [])),
        n_eff=n_eff_value,
    )

    # Risk warnings (trader spec, 4 mandatory)
    warnings: list[dict[str, str]] = []
    if isinstance(t1, int | float) and t1 > 3.0:
        warnings.append(
            {
                "level": "high",
                "code": "overfit_sharpe",
                "message": f"T1 Sharpe={t1:.2f} > 3.0 — почти наверняка overfit (Hudson & Urquhart 2021).",
            }
        )
    fold_max = max(sym_fold_sharpes) if sym_fold_sharpes else 0.0
    positive_folds = [s for s in sym_fold_sharpes if s > 0]
    fold_median_pos = sorted(positive_folds)[len(positive_folds) // 2] if positive_folds else 0.0
    if fold_max > 5 or (positive_folds and fold_max > 2 * fold_median_pos):
        warnings.append(
            {
                "level": "high",
                "code": "regime_concentration",
                "message": f"Fold с Sharpe={fold_max:.2f} drives aggregate — regime-specific signal.",
            }
        )
    if isinstance(sym_mc_p, int | float) and sym_mc_p > 0.10:
        warnings.append(
            {
                "level": "high",
                "code": "mc_noise",
                "message": f"MC permutation p={sym_mc_p:.3f} > 0.10 — returns indistinguishable от random.",
            }
        )
    if isinstance(dsr_value, int | float) and not math.isnan(dsr_value) and dsr_value <= 0:
        warnings.append(
            {
                "level": "high",
                "code": "dsr_penalty",
                "message": f"DSR={dsr_value:.3f} ≤ 0 — claimed edge не credible after multi-testing adjustment.",
            }
        )
    if sortino_warning:
        warnings.append(
            {
                "level": "info",
                "code": "sortino_anomaly",
                "message": "Sortino > 50 + n_trades < 100 = small-sample artifact (отображено как N/A).",
            }
        )
    if n_trades < 100:
        warnings.append(
            {
                "level": "warn",
                "code": "low_sample",
                "message": f"n_trades={n_trades} < 100 — недостаточно для t-test validity.",
            }
        )

    result = {
        "run_id": run_id,
        "request": {
            "strategy_id": req.strategy_id,
            "strategy_label": preset["label"],
            "strategy_config": preset,
            "symbol": req.symbol,
            "interval": req.interval,
            "interval_label": INTERVAL_LABELS.get(req.interval, req.interval),
            "start": req.start,
            "end": req.end,
        },
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "metrics": {
            "t1_sharpe_oos": t1,
            "t2_sortino_oos": sortino_display,
            "t2_sortino_raw": sortino_raw,
            "t2_sortino_anomaly_guard": sortino_warning,
            "t3_max_drawdown": t3,
            "t4_win_rate": t4_win,
            "t4_avg_rr": t4_rr,
            "t5_mean_pnl_pct": t5_mean,
            "t5_t_stat": t5_t,
            "t5_n_trades": n_trades,
            "t6_oos_is_sharpe_ratio_mean": t6,
        },
        "trade_stats": {
            "n_winners": n_winners,
            "n_losers": n_losers,
            "total_commissions_quote": total_commissions,
            "avg_win_quote": avg_win_quote,
            "avg_loss_quote": avg_loss_quote,
            "profit_factor": profit_factor,
            "total_pnl_quote": total_pnl,
            # S48 T7 (Bug H prereq) — win_rate + balance fields для HistoryTab expand
            "win_rate": t4_win,
            "initial_balance_quote": initial_balance,
            # M1 (S49): geometric compounding Π(1 + pnl_pct_i), not additive sum.
            "final_balance_quote": _compound_balance(initial_balance, _pnl_pcts),
        },
        "fold_sharpe_ratios": sym_fold_sharpes,
        "failed_folds": gate.get("failed_folds", []),
        "dsr": nan_safe(dsr_value),
        "dsr_pass": dsr_pass,
        "mc_p_value": sym_mc_p,
        "acceptance_gate": gate,
        "bars_per_year": bars_per_year,
        "wfa_params": wfa_params,  # S38: auto-scaled per data range
        "wfa_total_bars": len(df),
        "warnings": warnings,
        "trades_dump": trades_dump,  # S27 audit
        "cached": False,
        # S48 T2 (Bug B) — equity_curve parallel arrays for frontend EquityChart.
        # Cumulative pct from initial capital. trade_markers deferred (replay path).
        "equity_curve": {
            "timestamps": _eq_timestamps,
            "equity_pct": _eq_pct,
            "trade_markers": None,
        },
    }

    # S38 dashboard: warn если auto-scaled below ADR 0014 defaults
    if wfa_params["train_bars"] < 2000:
        warnings.append(
            {
                "level": "warn",
                "code": "wfa_autoscale",
                "message": (
                    f"WFA auto-scaled (data {len(df)} bars < 4520 ADR 0014 default): "
                    f"train={wfa_params['train_bars']} / test={wfa_params['test_bars']} / "
                    f"k_folds={wfa_params['k_folds']} / embargo={wfa_params['embargo_bars']}. "
                    "Smaller windows = noisier OOS metrics. Extend date range OR pick finer interval (5M/15M)."
                ),
            }
        )

    # Cache к disk
    cache_path.write_text(json.dumps(result, default=str, indent=2))

    # S27: refresh aggregated audit doc (best-effort, non-blocking)
    try:
        from scripts.audit_formulas import rebuild_audit

        rebuild_audit()
    except Exception:  # noqa: BLE001 — audit refresh не critical для backtest result
        pass

    return result


def list_runs() -> list[dict[str, Any]]:
    """List previously cached runs (newest first)."""
    if not _RUNS_DIR.exists():
        return []
    entries: list[dict[str, Any]] = []
    for p in sorted(_RUNS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            entries.append(
                {
                    "run_id": data.get("run_id"),
                    "request": data.get("request", {}),
                    "verdict": data.get("verdict"),
                    "metrics": data.get("metrics", {}),
                    "warnings_count": len(data.get("warnings", [])),
                    "mtime": p.stat().st_mtime,
                }
            )
        except Exception:  # noqa: BLE001
            continue
    return entries


def get_run(run_id: str) -> dict[str, Any] | None:
    """Fetch full run by run_id.

    H1 (S49) — validate run_id shape (16 lowercase hex) BEFORE path join.
    Rejects traversal payloads (../, %2e%2e%2f, abc/../../etc) → returns None.
    """
    if not _is_valid_run_id(run_id):
        return None
    p = _RUNS_DIR / f"{run_id}.json"
    if not p.exists():
        return None
    data: dict[str, Any] = json.loads(p.read_text())
    # M6 (S49): assert equity_curve parallel-array length invariant (timestamps vs equity_pct).
    equity_curve = data.get("equity_curve")
    if isinstance(equity_curve, dict):
        _timestamps = equity_curve.get("timestamps")
        _equity_pct = equity_curve.get("equity_pct")
        if isinstance(_timestamps, list) and isinstance(_equity_pct, list):
            assert len(_timestamps) == len(_equity_pct), (
                f"equity_curve parallel arrays length mismatch for run {run_id}: "
                f"timestamps={len(_timestamps)} vs equity_pct={len(_equity_pct)}"
            )
    return data
